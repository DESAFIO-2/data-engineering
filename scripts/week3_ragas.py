# /// script
# requires-python = ">=3.12,<3.13"
# dependencies = ["ragas==0.4.3", "langchain-community==0.3.31", "langchain-google-genai==2.1.12"]
# ///
"""Measure frozen Week 3 answers with official RAGAS; resume completed scores."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import math
import os
import statistics
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.environ["RAGAS_DO_NOT_TRACK"] = "true"


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()


async def run(args):
    from langchain_core.callbacks import AsyncCallbackHandler
    from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
    from ragas import SingleTurnSample
    from ragas.embeddings import LangchainEmbeddingsWrapper
    from ragas.llms import LangchainLLMWrapper
    from ragas.metrics import (
        Faithfulness,
        LLMContextPrecisionWithReference,
        LLMContextRecall,
        ResponseRelevancy,
    )
    from ragas.run_config import RunConfig

    from rag.config import get_settings
    from rag.providers import error_detail

    settings = get_settings()
    source = ROOT / args.source
    release = ROOT / args.release
    data = json.loads(source.read_text(encoding="utf-8"))
    evidence = {
        e["evidence_id"]: e
        for e in map(
            json.loads, (release / "evidencias.jsonl").read_text(encoding="utf-8").splitlines()
        )
    }

    def context(eid):
        e = evidence[eid]
        return (
            f"[{eid}] {e['text']} (fonte {e['source']['source_id']} "
            f"{e['source']['version']}, página {e['source']['page']})"
        )

    protocol = {
        "ragas_version": "0.4.3",
        "judge": args.judge,
        "embedding_model": settings.rag_embedding_model,
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "evidence_file_sha256": hashlib.sha256(
            (release / "evidencias.jsonl").read_bytes()
        ).hexdigest(),
        "dataset_sha256": data["dataset_sha256"],
        "release_fingerprint": data["release_fingerprint"],
        "reference_kind": (
            "source excerpts from approved expected_evidence_ids; "
            "not human-written reference answers"
        ),
        "scope": (
            "positive cases; generation errors excluded from faithfulness/relevancy; "
            "context metrics independent of generation"
        ),
        "strictness": 3,
        "temperature": "provider default (fixed sampling model)",
        "dependencies": {"langchain-community": "0.3.31", "langchain-google-genai": "2.1.12"},
    }
    output = ROOT / args.output
    state = {
        "protocol": protocol,
        "protocol_sha256": digest(protocol),
        "scores": {},
        "records": [],
        "summaries": {},
    }
    if output.exists():
        state = json.loads(output.read_text(encoding="utf-8"))
        if state["protocol_sha256"] != digest(protocol):
            raise ValueError("Existing output belongs to a different protocol")

    config = RunConfig(timeout=90, max_retries=1, max_workers=1)

    class PaceJudge(AsyncCallbackHandler):
        """Keep calls below the observed 15 requests/minute free tier limit."""

        def __init__(self):
            self.lock = asyncio.Lock()
            self.next_call = 0.0

        async def on_chat_model_start(self, serialized, messages, **kwargs):
            async with self.lock:
                await asyncio.sleep(max(0.0, self.next_call - time.monotonic()))
                self.next_call = time.monotonic() + 7.0

    ragas_api_key = (
        settings.google_api_keys[0] if settings.google_api_keys else settings.google_api_key
    )
    llm = LangchainLLMWrapper(
        ChatGoogleGenerativeAI(
            model=args.judge,
            google_api_key=ragas_api_key,
            max_retries=0,
            timeout=60,
            callbacks=[PaceJudge()],
        ),
        run_config=config,
        bypass_temperature=True,
        bypass_n=True,
    )
    embeddings = LangchainEmbeddingsWrapper(
        GoogleGenerativeAIEmbeddings(
            model=settings.rag_embedding_model, google_api_key=ragas_api_key
        ),
        run_config=config,
    )
    metrics = {
        "context_recall": LLMContextRecall(llm=llm),
        "context_precision": LLMContextPrecisionWithReference(llm=llm),
        "faithfulness": Faithfulness(llm=llm),
        "answer_relevancy": ResponseRelevancy(llm=llm, embeddings=embeddings, strictness=3),
    }
    for metric in metrics.values():
        metric.init(config)

    state.setdefault("execution_history", []).append(
        {
            "started_at_utc": datetime.now(UTC).isoformat(),
            "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "multiple_candidates": "three separate requests for relevancy",
            "judge_call_spacing_seconds": 7,
        }
    )

    def save():
        state["updated_at_utc"] = datetime.now(UTC).isoformat()
        summaries = {}
        for variant in sorted({r["variant"] for r in state["records"]}):
            summaries[variant] = {}
            for name in metrics:
                rows = [
                    r
                    for r in state["records"]
                    if r["variant"] == variant and name in r["score_keys"]
                ]
                values = [
                    state["scores"][r["score_keys"][name]]["value"]
                    for r in rows
                    if r["score_keys"][name] in state["scores"]
                    and state["scores"][r["score_keys"][name]]["value"] is not None
                ]
                summaries[variant][name] = {
                    "mean": statistics.mean(values) if values else None,
                    "scored": len(values),
                    "eligible": len(rows),
                }
        state["summaries"] = summaries
        output.parent.mkdir(parents=True, exist_ok=True)
        temp = output.with_suffix(".tmp")
        temp.write_text(
            json.dumps(state, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
            encoding="utf-8",
        )
        temp.replace(output)

    state["records"] = []
    tasks = {}
    for r in data["records"]:
        row = {
            "id": r["id"],
            "variant": r["variant"],
            "generation_error": r["error"],
            "score_keys": {},
        }
        state["records"].append(row)
        if r["expected_status"] != "matched":
            row["excluded_reason"] = (
                "negative, ambiguous or clinical guardrail; outside positive RAGAS scope"
            )
            continue
        sample = {
            "user_input": r["question"],
            "response": r["answer"] or "",
            "retrieved_contexts": [context(eid) for eid in r["evidence_ids"]],
            "reference": "\n".join(context(eid) for eid in r["expected_evidence_ids"]),
        }
        for name in metrics:
            if name != "answer_relevancy" and not sample["retrieved_contexts"]:
                continue
            if name in {"faithfulness", "answer_relevancy"} and (r["error"] or not r["answer"]):
                continue
            fields = (
                {"user_input", "retrieved_contexts", "reference"}
                if name.startswith("context_")
                else {"user_input", "response", "retrieved_contexts"}
                if name == "faithfulness"
                else {"user_input", "response"}
            )
            payload = {k: v for k, v in sample.items() if k in fields}
            key = digest({"metric": name, "sample": payload})
            row["score_keys"][name] = key
            tasks[key] = (name, payload)
    save()

    async def score_with_minute_retry(metric, payload):
        for attempt in range(4):
            try:
                return await metric.single_turn_ascore(SingleTurnSample(**payload), timeout=90)
            except Exception as exc:
                detail = error_detail(exc)
                if attempt == 3 or not any(
                    t in detail.lower() for t in ("per minute", "perminute")
                ):
                    raise
                state.setdefault("provider_retries", []).append(
                    {
                        "at_utc": datetime.now(UTC).isoformat(),
                        "error": detail,
                        "wait_seconds": 45,
                    }
                )
                save()
                print("Minute quota: waiting 45 seconds before resuming.", flush=True)
                await asyncio.sleep(45)

    for key, (name, payload) in tasks.items():
        if key in state["scores"] and state["scores"][key]["value"] is not None:
            continue
        started = time.monotonic()
        value, error = None, None
        try:
            result = await score_with_minute_retry(metrics[name], payload)
            value = float(result) if math.isfinite(result) else None
            if value is None:
                error = "RAGAS returned a non-finite score"
        except Exception as exc:
            error = error_detail(exc)
        state["scores"][key] = {
            "metric": name,
            "input": payload,
            "value": value,
            "error": error,
            "elapsed_seconds": round(time.monotonic() - started, 3),
        }
        save()
        print(name, key[:10], value, error or "ok", flush=True)
        if error and any(x in error.lower() for x in ["429", "quota", "resourceexhausted"]):
            print("Stopped on provider quota; rerun the same command to resume.", flush=True)
            return
    print(json.dumps(state["summaries"], ensure_ascii=False), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--judge", default="gemini-3.5-flash-lite")
    parser.add_argument("--source", default="evals/results/week3_v9_response_test.json")
    parser.add_argument(
        "--release", default="data/releases/corpus-consolidado-v9-aprovado-2026-11-12"
    )
    parser.add_argument("--output", default="evals/results/week3_v9_ragas_test.json")
    asyncio.run(run(parser.parse_args()))
