"""Reproducible paired Week 3 comparison on synthetic consolidated cases."""

from __future__ import annotations

import argparse
import json
import platform
import subprocess
import time
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

from rag.answer import SYSTEM, synthesize
from rag.config import ROOT, get_settings
from rag.consolidated import ConsolidatedRelease, load_chunks, open_index, search
from rag.providers import google_chat, google_embeddings

STRATEGIES = ("exact", "lexical", "vector", "hybrid")
MODES = ("llm_only", "lexical_documental", "lexical_llm", "best_llm")


class MeasuredModel:
    def __init__(self, model: Any) -> None:
        self.model = model
        self.last_usage: Any = None

    def invoke(self, messages: Any) -> Any:
        response = self.model.invoke(messages)
        self.last_usage = getattr(response, "usage_metadata", None)
        return response


def percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    point = (len(ordered) - 1) * q
    low = int(point)
    return ordered[low] + (ordered[min(low + 1, len(ordered) - 1)] - ordered[low]) * (point - low)


def text_content(response: Any) -> str:
    content = response.content
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        return "\n".join(
            part["text"]
            for part in content
            if isinstance(part, dict) and isinstance(part.get("text"), str)
        ).strip()
    return ""


def run(args: argparse.Namespace) -> dict[str, Any]:
    settings = get_settings()
    release = ConsolidatedRelease.load(args.release)
    chunks, manifest = load_chunks(
        release, ROOT / "data/derived/chunks" / release.manifest["release_version"]
    )
    raw = args.dataset.read_bytes()
    cases = [json.loads(line) for line in raw.splitlines() if line.strip()]
    if not cases or len({case["id"] for case in cases}) != len(cases):
        raise ValueError("Dataset vazio ou com IDs duplicados")
    if any(case.get("split") != args.split for case in cases):
        raise ValueError("O dataset desta execução deve conter somente o split solicitado")
    review_sha256 = None
    if args.split == "test":
        if not args.frozen_dataset_sha256 or sha256(raw).hexdigest() != args.frozen_dataset_sha256:
            raise ValueError("Teste fechado: hash congelado do dataset ausente ou divergente")
        if args.review_record is None or not args.review_record.is_file():
            raise ValueError("Teste fechado: registro de revisão humana ausente")
        review_sha256 = sha256(args.review_record.read_bytes()).hexdigest()
        if any(
            case.get("review_status") != "reviewed"
            or not case.get("reviewer")
            or not case.get("reviewed_at")
            or case.get("review_record_sha256") != review_sha256
            for case in cases
        ):
            raise ValueError("Teste fechado: casos sem revisão humana vinculada")
    evidence_by_id = {item["evidence_id"]: item for item in release.evidence}
    for case in cases:
        if (
            case.get("synthetic") is not True
            or case.get("release_fingerprint") != release.fingerprint
        ):
            raise ValueError(f"Caso inválido ou release divergente: {case['id']}")
        if any(eid not in evidence_by_id for eid in case["relevant_ids"]):
            raise ValueError(f"Evidência ausente: {case['id']}")
    if args.output.exists():
        raise FileExistsError(args.output)
    available = STRATEGIES if args.matrix == "retrieval" else MODES
    variants = tuple(args.variants.split(",")) if args.variants else available
    if len(set(variants)) != len(variants) or any(item not in available for item in variants):
        raise ValueError("Lista de cenários inválida")
    needs_vector = (
        args.matrix == "retrieval" and any(item in {"vector", "hybrid"} for item in variants)
    ) or (
        args.matrix == "response"
        and "best_llm" in variants
        and args.best_strategy in {"vector", "hybrid"}
    )
    store = None
    if needs_vector:
        embeddings = google_embeddings(settings.rag_embedding_model, settings.google_api_key)
        store = open_index(
            release,
            chunks,
            manifest,
            ROOT / settings.rag_vector_dir,
            settings.rag_embedding_model,
            embeddings,
        )
    llm = None
    if args.matrix == "response":
        llm = MeasuredModel(google_chat(settings.rag_chat_model, settings.google_api_key))
    records: list[dict[str, Any]] = []
    for variant in variants:
        for case in cases:
            started = time.perf_counter()
            retrieval_ms = None
            generation_ms = None
            usage = None
            error = None
            result: dict[str, Any] | None = None
            answer = None
            try:
                if variant != "llm_only":
                    strategy = (
                        variant
                        if args.matrix == "retrieval"
                        else (args.best_strategy if variant == "best_llm" else "lexical")
                    )
                    began = time.perf_counter()
                    result = search(
                        case["question"], release, chunks, store=store, strategy=strategy, top_k=5
                    )
                    retrieval_ms = round((time.perf_counter() - began) * 1000, 3)
                if args.matrix == "response":
                    assert llm is not None
                    if variant == "llm_only":
                        began = time.perf_counter()
                        response = llm.invoke(
                            [
                                ("system", SYSTEM),
                                (
                                    "human",
                                    "Responda à pergunta sem consultar fontes. Se não puder "
                                    "verificar a informação, diga isso claramente. Pergunta: "
                                    + case["question"],
                                ),
                            ]
                        )
                        answer = text_content(response)
                        usage = getattr(response, "usage_metadata", None)
                        generation_ms = round((time.perf_counter() - began) * 1000, 3)
                    elif variant == "lexical_documental" or (
                        result is not None and result["status"] != "matched"
                    ):
                        assert result is not None
                        answer = result["message"] + "".join(
                            "\n- " + item["text"] for item in result["evidence"]
                        )
                    else:
                        assert result is not None
                        began = time.perf_counter()
                        answer = synthesize(case["question"], result, llm)
                        usage = llm.last_usage
                        generation_ms = round((time.perf_counter() - began) * 1000, 3)
            except Exception as exc:
                error = type(exc).__name__
            found = result.get("evidence", []) if result else []
            ids = [item["evidence_id"] for item in found]
            relevant = set(case["relevant_ids"])
            rank = next((i for i, eid in enumerate(ids, 1) if eid in relevant), None)
            expected_mids = {evidence_by_id[eid]["medicine_id"] for eid in relevant}
            found_mids = {item["medicine_id"] for item in found}
            citation_checks = [
                evidence_by_id.get(item["evidence_id"]) == item
                and bool(item["source"].get("url"))
                and item["source"].get("page") is not None
                for item in found
            ]
            records.append(
                {
                    "variant": variant,
                    "id": case["id"],
                    "question": case["question"],
                    "source_id": case.get("source_id"),
                    "expected_status": case["expected_status"],
                    "status": result["status"] if result else None,
                    "answer": answer,
                    "evidence_ids": ids,
                    "ranked_chunk_ids": result.get("ranked_chunk_ids", []) if result else [],
                    "expected_evidence_ids": case["relevant_ids"],
                    "first_relevant_rank": rank,
                    "status_correct": result["status"] == case["expected_status"]
                    if result
                    else None,
                    "critical_confusion": bool(
                        result
                        and result["status"] == "matched"
                        and (case["expected_status"] != "matched" or found_mids != expected_mids)
                    ),
                    "citation_checks": citation_checks,
                    "retrieval_ms": retrieval_ms,
                    "generation_ms": generation_ms,
                    "total_ms": round((time.perf_counter() - started) * 1000, 3),
                    "usage": usage,
                    "error": error,
                    "human_review": "pending",
                }
            )
    summaries = {}
    for variant in variants:
        group = [row for row in records if row["variant"] == variant]
        positive = [row for row in group if row["expected_status"] == "matched"]
        citations = [ok for row in group for ok in row["citation_checks"]]
        summaries[variant] = {
            "cases": len(group),
            "positive_cases": len(positive),
            "hit_at_1": sum(row["first_relevant_rank"] == 1 for row in positive) / len(positive)
            if positive
            else None,
            "hit_at_3": sum(
                row["first_relevant_rank"] is not None and row["first_relevant_rank"] <= 3
                for row in positive
            )
            / len(positive)
            if positive
            else None,
            "hit_at_5": sum(
                row["first_relevant_rank"] is not None and row["first_relevant_rank"] <= 5
                for row in positive
            )
            / len(positive)
            if positive
            else None,
            "mrr_at_5": sum(
                1 / row["first_relevant_rank"] if row["first_relevant_rank"] else 0
                for row in positive
            )
            / len(positive)
            if positive
            else None,
            "status_accuracy": sum(row["status_correct"] is True for row in group) / len(group),
            "critical_confusions": sum(row["critical_confusion"] for row in group),
            "citation_precision": sum(citations) / len(citations) if citations else None,
            "errors": sum(row["error"] is not None for row in group),
            "usage_coverage": sum(isinstance(row["usage"], dict) for row in group),
            "input_tokens_known": sum(
                row["usage"].get("input_tokens", 0)
                for row in group
                if isinstance(row["usage"], dict)
                and isinstance(row["usage"].get("input_tokens"), int)
            ),
            "output_tokens_known": sum(
                row["usage"].get("output_tokens", 0)
                for row in group
                if isinstance(row["usage"], dict)
                and isinstance(row["usage"].get("output_tokens"), int)
            ),
            "latency_p50_ms": percentile([row["total_ms"] for row in group], 0.5),
            "latency_p95_ms": percentile([row["total_ms"] for row in group], 0.95),
            "human_review": "pending" if args.matrix == "response" else "not_applicable",
            "by_source": {
                source: {
                    "cases": len(subgroup),
                    "positive_cases": len(pos),
                    "hit_at_5": (
                        sum(
                            row["first_relevant_rank"] is not None
                            and row["first_relevant_rank"] <= 5
                            for row in pos
                        )
                        / len(pos)
                        if pos
                        else None
                    ),
                    "critical_confusions": sum(row["critical_confusion"] for row in subgroup),
                }
                for source in ("F01", "F03", "F04")
                if (subgroup := [row for row in group if row["source_id"] == source])
                for pos in [[row for row in subgroup if row["expected_status"] == "matched"]]
            },
        }
        if variant == "llm_only":
            for metric in ("hit_at_1", "hit_at_3", "hit_at_5", "mrr_at_5", "status_accuracy"):
                summaries[variant][metric] = None
            for source_metrics in summaries[variant]["by_source"].values():
                source_metrics["hit_at_5"] = None
        if summaries[variant]["usage_coverage"] == 0:
            summaries[variant]["input_tokens_known"] = None
            summaries[variant]["output_tokens_known"] = None
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True, check=False
    ).stdout.strip()
    dirty = bool(
        subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=no"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        ).stdout.strip()
    )
    code_hashes = {
        str(path.relative_to(ROOT)): sha256(path.read_bytes()).hexdigest()
        for path in (
            ROOT / "src/rag/consolidated.py",
            ROOT / "src/rag/answer.py",
            ROOT / "src/rag/providers.py",
            ROOT / "scripts/week3_compare.py",
        )
    }
    report = {
        "schema_version": "week3-comparison-v1",
        "executed_at_utc": datetime.now(UTC).isoformat(),
        "matrix": args.matrix,
        "dataset_sha256": sha256(raw).hexdigest(),
        "split": args.split,
        "review_sha256": review_sha256,
        "release_fingerprint": release.fingerprint,
        "chunks_sha256": manifest["files"]["chunks.jsonl"]["sha256"],
        "chat_model": settings.rag_chat_model if llm else None,
        "embedding_model": settings.rag_embedding_model if store else None,
        "best_strategy": args.best_strategy if args.matrix == "response" else None,
        "top_k": 5,
        "python_version": platform.python_version(),
        "git_commit": commit,
        "git_dirty": dirty,
        "code_sha256": code_hashes,
        "summaries": summaries,
        "records": records,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8"
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix", choices=("retrieval", "response"), required=True)
    parser.add_argument("--release", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--best-strategy", choices=STRATEGIES, default="lexical")
    parser.add_argument("--variants", help="Cenários separados por vírgula; padrão: matriz inteira")
    parser.add_argument("--split", choices=("dev", "test"), default="dev")
    parser.add_argument("--frozen-dataset-sha256")
    parser.add_argument("--review-record", type=Path)
    report = run(parser.parse_args())
    print(json.dumps(report["summaries"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
