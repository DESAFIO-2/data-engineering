"""Synthetic-only evaluation with reviewable JSONL artifacts and offline CLI."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import time
from collections.abc import Callable
from importlib.metadata import version
from pathlib import Path
from typing import Any

from rag.core.metrics import percentile, retrieval_metrics, text_metrics

STATUSES = {"matched", "ambiguous", "blocked", "unsupported", "not_in_scope", "insufficient"}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8-sig").splitlines()
        if line.strip()
    ]


def dataset_hash(cases: list[dict[str, Any]]) -> str:
    """Canonical UTF-8 JSON hash, preserving case/list order; not raw file SHA256."""
    return hashlib.sha256(
        json.dumps(
            cases, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False
        ).encode()
    ).hexdigest()


def validate_cases(cases: list[dict[str, Any]]) -> None:
    if not cases:
        raise ValueError("Empty golden set")
    seen: set[str] = set()
    families: dict[str, str] = {}
    for case in cases:
        for field in ("id", "family_id", "question", "reference_answer"):
            if not isinstance(case.get(field), str) or not case[field].strip():
                raise ValueError(f"Missing/non-text {field}")
        if case.get("synthetic") is not True:
            raise ValueError("Only explicitly synthetic cases are accepted")
        if case.get("evaluable", True) is not True or case.get("placeholder", False):
            raise ValueError("Pending placeholders are not evaluable")
        if case.get("review_status") not in ("draft", "reviewed"):
            raise ValueError("review_status must be draft or reviewed")
        if case["review_status"] == "reviewed":
            review = case.get("review", {})
            if not isinstance(review, dict) or any(
                not isinstance(review.get(key), str) or not review[key].strip()
                for key in ("reviewer", "reviewed_at", "record_id")
            ):
                raise ValueError("Reviewed cases require reviewer, reviewed_at and record_id")
        if case.get("split") not in ("dev", "test"):
            raise ValueError("split must be dev or test")
        expected = case.get("expected_status", "matched")
        if expected not in STATUSES:
            raise ValueError("Invalid expected_status")
        ids = case.get("relevant_ids")
        if (
            not isinstance(ids, list)
            or any(not isinstance(eid, str) or not eid.strip() for eid in ids)
            or (expected == "matched" and not ids)
        ):
            raise ValueError("Answerable cases need evidence IDs; behavior cases may use []")
        if case["id"] in seen:
            raise ValueError("Duplicate case ID")
        seen.add(case["id"])
        family = case["family_id"]
        if families.setdefault(family, case["split"]) != case["split"]:
            raise ValueError("Family leakage between dev and test")


def _mean(values: list[Any]) -> float | None:
    known = [value for value in values if value is not None]
    return sum(known) / len(known) if known else None


def artifact_paths(output: Path) -> tuple[Path, Path, Path]:
    if output.suffix.lower() != ".jsonl":
        raise ValueError("Output must use .jsonl extension")
    return output, output.with_suffix(".csv"), output.with_suffix(".md")


def write_artifacts(output: Path, records: list[dict[str, Any]], summary: dict[str, Any]) -> None:
    """Exclusive-create JSONL plus flat CSV and Markdown summary; no overwrite."""
    paths = artifact_paths(output)
    for path in paths:
        if path.exists():
            raise FileExistsError(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as stream:
        for record in [*records, summary]:
            stream.write(json.dumps(record, ensure_ascii=False, allow_nan=False) + "\n")
    with paths[1].open("x", encoding="utf-8", newline="") as stream:
        keys = list(dict.fromkeys(key for row in [*records, summary] for key in row))
        writer = csv.DictWriter(stream, fieldnames=keys)
        writer.writeheader()
        for row in [*records, summary]:
            # Prevent synthetic text from being interpreted as spreadsheet formulas.
            safe = {}
            for key, value in row.items():
                if isinstance(value, (dict, list)):
                    value = json.dumps(value, ensure_ascii=False)
                if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
                    value = "'" + value
                safe[key] = value
            writer.writerow(safe)
    with paths[2].open("x", encoding="utf-8") as stream:
        stream.write("# Avaliação RAG sintética\n\n")
        stream.write("Métricas automáticas não constituem aprovação factual humana.\n\n")
        stream.write("| Medida | Valor |\n|---|---|\n")
        for key, value in summary.items():
            cell = json.dumps(value, ensure_ascii=False).replace("|", "\\|").replace("\n", " ")
            stream.write(f"| {key} | {cell} |\n")


RUBRIC_FIELDS = (
    "factual_accuracy",
    "fidelity",
    "completeness",
    "citation_support",
    "critical_error",
    "abstention_correct",
)


def report_human_reviews(run: Path, reviews: Path, output: Path) -> dict[str, Any]:
    """Aggregate explicit human judgments bound to exact case/repetition response hashes.

    Values are booleans or null (not applicable/unrated). No inferred ratings.
    Dataset approval and response review are separate workflows.
    """
    run_rows = read_jsonl(run)
    records = [row for row in run_rows if row.get("record_type") == "case"]
    by_key = {(row["id"], row["repeat_index"]): row for row in records}
    if (
        not records
        or len(by_key) != len(records)
        or any(row.get("synthetic") is not True for row in records)
    ):
        raise ValueError("Expected a synthetic benchmark artifact with unique cases/repeats")
    judgments = read_jsonl(reviews)
    seen = set()
    for row in judgments:
        key = (row.get("id"), row.get("repeat_index"))
        if key not in by_key or key in seen:
            raise ValueError("Unknown/duplicate human review target")
        seen.add(key)
        if any(
            not isinstance(row.get(field), str) or not row[field].strip()
            for field in ("reviewer", "reviewed_at", "record_id")
        ):
            raise ValueError("Human review attribution is required")
        if not row.get("response_sha256") or (
            row["response_sha256"] != by_key[key].get("response_sha256")
        ):
            raise ValueError("Human review response hash mismatch")
        for field in RUBRIC_FIELDS:
            if field not in row or (row[field] is not None and type(row[field]) is not bool):
                raise ValueError(f"Human rubric {field} must be boolean or null")
        if any(row[field] is not None for field in RUBRIC_FIELDS) and not row.get("rationale"):
            raise ValueError("Human ratings require a rationale")
    summary: dict[str, Any] = {
        "record_type": "human_summary",
        "synthetic": True,
        "total": len(records),
        "reviewed_responses": len(judgments),
        "pending_responses": len(records) - len(judgments),
        "review_method": "human_supplied_not_automatically_verified",
        "run_sha256": hashlib.sha256(run.read_bytes()).hexdigest(),
    }
    for field in RUBRIC_FIELDS:
        known = [row[field] for row in judgments if row[field] is not None]
        summary[field] = _mean(known)
        summary[f"{field}_rated"] = len(known)
    write_artifacts(output, judgments, summary)
    return summary


def run_benchmark(
    cases: list[dict[str, Any]],
    runner: Callable[[dict[str, Any]], dict[str, Any]],
    output: Path,
    *,
    split: str = "dev",
    allow_draft: bool = False,
    repeat: int = 1,
    mode: str = "end-to-end",
    frozen_dataset_sha256: str | None = None,
    run_metadata: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Validate before API calls. Caller selects retrieval/fixed-context generation pipeline.

    Only synthetic questions/answers/references/ranks and explicit metrics are saved;
    never arbitrary response metadata, exception messages or personal query logs.
    """
    validate_cases(cases)
    if split not in ("dev", "test") or mode not in ("retrieval", "generation", "end-to-end"):
        raise ValueError("Invalid split/mode")
    if type(repeat) is not int or repeat < 1:
        raise ValueError("repeat must be a positive integer")
    selected = [case for case in cases if case["split"] == split]
    if not selected:
        raise ValueError("Selected split is empty")
    digest = dataset_hash(cases)
    drafts = any(case["review_status"] == "draft" for case in selected)
    if drafts and (not allow_draft or split == "test"):
        raise ValueError("Drafts require --allow-draft and are restricted to dev")
    if split == "test" and frozen_dataset_sha256 != digest:
        raise ValueError("Final test requires matching frozen_dataset_sha256")
    if frozen_dataset_sha256 is not None and frozen_dataset_sha256 != digest:
        raise ValueError("Frozen dataset hash mismatch")
    for path in artifact_paths(output):
        if path.exists():
            raise FileExistsError(path)
    json.dumps(run_metadata or {}, allow_nan=False)
    text_metrics([], [])
    records: list[dict[str, Any]] = []
    answers, references = [], []
    benchmark_start = time.perf_counter()
    for run_index, case in ((index, case) for index in range(repeat) for case in selected):
        start = time.perf_counter()
        error = None
        answer, ranked, usage, status = "", [], {}, "error"
        timings: dict[str, float | None] = {}
        try:
            response = runner(case)
            answer = response.get("answer", "")
            ranked = response.get("ranked_ids", response.get("semantic_ids", []))
            status = response["status"]
            if (
                not isinstance(answer, str)
                or not isinstance(ranked, list)
                or any(not isinstance(eid, str) or not eid for eid in ranked)
                or status not in STATUSES
            ):
                raise ValueError("Invalid answer, ranks or status")
            for key in ("latency_ms", "retrieval_ms", "generation_ms"):
                value = response.get(key)
                if value is not None and (
                    isinstance(value, bool)
                    or not isinstance(value, (float, int))
                    or not math.isfinite(value)
                    or value < 0
                ):
                    raise ValueError("Invalid timing")
                timings[key] = value
            usage = response.get("usage", {})
            if not isinstance(usage, dict):
                raise ValueError("Invalid usage")
            for key in ("input_tokens", "output_tokens"):
                value = usage.get(key)
                if value is not None and (type(value) is not int or value < 0):
                    raise ValueError("Invalid token usage")
        except Exception as exc:
            error = type(exc).__name__
            answer, ranked, usage, status, timings = "", [], {}, "error", {}
        measured = (time.perf_counter() - start) * 1000
        expected = case.get("expected_status", "matched")
        factual = expected == "matched"
        metrics = retrieval_metrics(
            ranked, case["relevant_ids"] if factual and mode != "generation" else []
        )
        records.append(
            {
                "record_type": "case",
                "id": case["id"],
                "split": split,
                "repeat_index": run_index,
                "synthetic": True,
                "error": error,
                "category": case.get("category"),
                "family_id": case["family_id"],
                "review_status": case["review_status"],
                "factual_review": "pending",
                "question": case["question"],
                "answer": answer,
                "response_sha256": dataset_hash(
                    [
                        {
                            "id": case["id"],
                            "repeat_index": run_index,
                            "question": case["question"],
                            "answer": answer,
                            "ranked_ids": ranked,
                            "status": status,
                            "dataset_sha256": digest,
                        }
                    ]
                ),
                "reference_answer": case["reference_answer"],
                "ranked_ids": ranked,
                "relevant_ids": case["relevant_ids"],
                "status": status,
                "expected_status": expected,
                "behavior_correct": float(status == expected) if not factual else None,
                "assertions": case.get("assertions", []),
                "required_facts": case.get("required_facts", []),
                "forbidden_claims": case.get("forbidden_claims", []),
                "sources": case.get("sources", []),
                "critical": case.get("critical", expected == "blocked"),
                "latency_ms": timings.get("latency_ms")
                if timings.get("latency_ms") is not None
                else measured,
                "latency_source": "reported"
                if timings.get("latency_ms") is not None
                else "measured",
                "retrieval_ms": timings.get("retrieval_ms"),
                "generation_ms": timings.get("generation_ms"),
                "input_tokens": usage.get("input_tokens"),
                "output_tokens": usage.get("output_tokens"),
                **metrics,
            }
        )
        if factual and mode != "retrieval":
            answers.append(answer)
            references.append(case["reference_answer"])
    elapsed_seconds = time.perf_counter() - benchmark_start
    count = len(records)
    summary = {
        "record_type": "summary",
        "schema_version": 1,
        "synthetic": True,
        "review_status": "draft" if drafts else "reviewed",
        "split": split,
        "mode": mode,
        "total": count,
        "unique_cases": len(selected),
        "repeat": repeat,
        "elapsed_seconds": elapsed_seconds,
        "throughput_cases_per_second": count / elapsed_seconds if elapsed_seconds else None,
        "successful_cases_per_second": sum(row["error"] is None for row in records)
        / elapsed_seconds
        if elapsed_seconds
        else None,
        "errors": sum(row["error"] is not None for row in records),
        "dataset_sha256": digest,
        "frozen_dataset_sha256": frozen_dataset_sha256,
        "metadata": run_metadata or {},
        "text_scored_cases": len(answers),
        "retrieval_scored_cases": sum(row["mrr"] is not None for row in records),
        "behavior_scored_cases": sum(row["behavior_correct"] is not None for row in records),
        "behavior_accuracy": _mean([row["behavior_correct"] for row in records]),
        "factual_accuracy": None,
        "factual_review": "pending",
        "dependencies": {name: version(name) for name in ("sacrebleu", "rouge-score")},
        **text_metrics(answers, references),
    }
    summary["error_rate"] = summary["errors"] / count
    for key in retrieval_metrics([], []):
        summary[key] = _mean([row[key] for row in records])
    for key in ("latency_ms", "retrieval_ms", "generation_ms"):
        known = [row[key] for row in records if row[key] is not None]
        summary[f"{key.removesuffix('_ms')}_p50_ms"] = percentile(known, 50)
        summary[f"{key.removesuffix('_ms')}_p95_ms"] = percentile(known, 95)
        summary[f"{key}_known_cases"] = len(known)
    for key in ("input_tokens", "output_tokens"):
        known = [row[key] for row in records if row[key] is not None]
        summary[key] = sum(known) if known else None
        summary[f"{key}_known_cases"] = len(known)
    complete_usage = [
        row
        for row in records
        if row["input_tokens"] is not None and row["output_tokens"] is not None
    ]
    summary["total_tokens_known_cases"] = len(complete_usage)
    summary["total_tokens"] = (
        sum(row["input_tokens"] + row["output_tokens"] for row in complete_usage)
        if complete_usage
        else None
    )
    write_artifacts(output, records, summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path)
    parser.add_argument("--predictions", type=Path)
    parser.add_argument("--review-run", type=Path)
    parser.add_argument("--human-reviews", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--split", choices=("dev", "test"), default="dev")
    parser.add_argument("--allow-draft", action="store_true")
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument(
        "--mode", choices=("retrieval", "generation", "end-to-end"), default="end-to-end"
    )
    parser.add_argument("--frozen-dataset-sha256")
    args = parser.parse_args()
    if args.review_run is not None:
        if args.human_reviews is None:
            parser.error("--review-run requires --human-reviews")
        print(json.dumps(report_human_reviews(args.review_run, args.human_reviews, args.output)))
        return
    if args.dataset is None or args.predictions is None:
        parser.error("Benchmark requires --dataset and --predictions")
    rows = read_jsonl(args.predictions)
    predictions = {row["id"]: row for row in rows}
    if len(predictions) != len(rows):
        raise ValueError("Duplicate prediction IDs")
    cases = read_jsonl(args.dataset)
    if set(predictions) - {case["id"] for case in cases}:
        raise ValueError("Unknown prediction IDs")
    summary = run_benchmark(
        cases,
        lambda case: predictions[case["id"]],
        args.output,
        split=args.split,
        allow_draft=args.allow_draft,
        repeat=args.repeat,
        mode=args.mode,
        frozen_dataset_sha256=args.frozen_dataset_sha256,
        run_metadata={"execution": "offline_predictions"},
    )
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
