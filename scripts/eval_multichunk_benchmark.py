"""Evaluate multi-chunk ranking strategies with bootstrap CIs and paired McNemar tests."""

from __future__ import annotations

import argparse
import json
import math
import random
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from rag.config import ROOT, get_settings
from rag.consolidated import (
    ConsolidatedRelease,
    ingredient_key,
    load_chunks,
    normalize,
    open_index,
    search,
)
from rag.providers import google_embeddings

DEFAULT_RELEASE = ROOT / "data/releases/corpus-consolidado-v9-aprovado-2026-11-12"
DEFAULT_DATASET = ROOT / "evals/datasets/multichunk_v9_benchmark.jsonl"
DEFAULT_OUTPUT = ROOT / "evals/results/multichunk_v9_offline.json"


def _pres_key(ev: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        ingredient_key(ev["active_ingredient"]),
        normalize(ev["strength"]),
        normalize(ev["form"]),
        normalize(ev.get("release_characteristic") or ""),
    )


def percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    point = (len(ordered) - 1) * q
    low = int(point)
    return round(
        ordered[low] + (ordered[min(low + 1, len(ordered) - 1)] - ordered[low]) * (point - low), 3
    )


def bootstrap_ci(
    values: list[float], *, resamples: int = 2000, seed: int = 42
) -> dict[str, float] | None:
    """Compute deterministic percentile 95% bootstrap confidence interval for the mean."""
    if not values:
        return None
    rng = random.Random(seed)
    n = len(values)
    means: list[float] = []
    for _ in range(resamples):
        sample = [values[rng.randrange(n)] for _ in range(n)]
        means.append(sum(sample) / n)
    means.sort()
    low_idx = int(0.025 * (resamples - 1))
    high_idx = int(0.975 * (resamples - 1))
    return {
        "mean": round(sum(values) / n, 4),
        "ci95_low": round(means[low_idx], 4),
        "ci95_high": round(means[high_idx], 4),
    }


def exact_mcnemar_pvalue(wins: int, losses: int) -> float:
    """Exact two-sided binomial sign/McNemar test p-value on discordant pairs."""
    n = wins + losses
    if n == 0:
        return 1.0
    k = min(wins, losses)
    tail = float(sum(math.comb(n, i) for i in range(k + 1))) / float(2**n)
    return float(round(min(1.0, 2.0 * tail), 6))


def paired_hit1_comparison(
    candidate_hits: list[float], baseline_hits: list[float]
) -> dict[str, Any]:
    """Compare two paired binary Hit@1 series via exact McNemar and bootstrap delta CI."""
    wins = sum(1 for a, b in zip(candidate_hits, baseline_hits, strict=True) if a > b)
    losses = sum(1 for a, b in zip(candidate_hits, baseline_hits, strict=True) if a < b)
    ties = len(candidate_hits) - wins - losses
    deltas = [a - b for a, b in zip(candidate_hits, baseline_hits, strict=True)]
    return {
        "wins": wins,
        "losses": losses,
        "ties": ties,
        "mcnemar_p_value": exact_mcnemar_pvalue(wins, losses),
        "hit1_delta": bootstrap_ci(deltas),
    }


def summarize_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    hit1 = [1.0 if r["first_relevant_rank"] == 1 else 0.0 for r in records]
    hit3 = [
        1.0 if r["first_relevant_rank"] and r["first_relevant_rank"] <= 3 else 0.0 for r in records
    ]
    hit5 = [
        1.0 if r["first_relevant_rank"] and r["first_relevant_rank"] <= 5 else 0.0 for r in records
    ]
    mrr = [1.0 / r["first_relevant_rank"] if r["first_relevant_rank"] else 0.0 for r in records]
    latencies = [float(r["latency_ms"]) for r in records]
    return {
        "cases": len(records),
        "min_candidate_chunk_count": min(r["candidate_chunk_count"] for r in records)
        if records
        else 0,
        "hit_at_1": bootstrap_ci(hit1),
        "hit_at_3": round(sum(hit3) / len(hit3), 4) if hit3 else None,
        "hit_at_5": round(sum(hit5) / len(hit5), 4) if hit5 else None,
        "mrr_at_5": bootstrap_ci(mrr),
        "critical_confusions": sum(1 for r in records if r["critical_confusion"]),
        "latency_p50_ms": percentile(latencies, 0.5),
        "latency_p95_ms": percentile(latencies, 0.95),
    }


def evaluate_multichunk(
    *,
    release_dir: Path,
    dataset_path: Path,
    strategies: tuple[str, ...],
    split: str = "all",
    store: Any = None,
) -> dict[str, Any]:
    """Run multi-chunk ranking evaluation and return full structured metrics."""
    release = ConsolidatedRelease.load(release_dir)
    chunks, _ = load_chunks(
        release, ROOT / "data/derived/chunks" / release.manifest["release_version"]
    )
    all_cases = [
        json.loads(line)
        for line in dataset_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    cases = all_cases if split == "all" else [c for c in all_cases if c["split"] == split]
    if not cases:
        raise ValueError(f"Nenhum caso encontrado para split={split}")

    evidence_by_id = {ev["evidence_id"]: ev for ev in release.evidence}
    per_strategy: dict[str, list[dict[str, Any]]] = {s: [] for s in strategies}

    for strategy in strategies:
        for case in cases:
            started = time.perf_counter()
            res = search(case["question"], release, chunks, store=store, strategy=strategy, top_k=5)
            elapsed_ms = round((time.perf_counter() - started) * 1000, 3)
            found = res.get("evidence", [])
            ids = [ev["evidence_id"] for ev in found]
            relevant = set(case["relevant_ids"])
            rank = next((i for i, eid in enumerate(ids, 1) if eid in relevant), None)
            cand_count = int(res.get("candidate_chunk_count") or 0)
            if cand_count < 3:
                raise ValueError(
                    f"Caso {case['id']} caiu abaixo de 3 chunks candidatos ({cand_count})"
                )
            expected_pres = {_pres_key(evidence_by_id[eid]) for eid in relevant}
            found_pres = {_pres_key(ev) for ev in found}
            per_strategy[strategy].append(
                {
                    "id": case["id"],
                    "split": case["split"],
                    "clue_kind": case["clue_kind"],
                    "candidate_chunk_count": cand_count,
                    "status": res["status"],
                    "first_relevant_rank": rank,
                    "returned_evidence_ids": ids,
                    "expected_evidence_ids": case["relevant_ids"],
                    "critical_confusion": res["status"] != "matched" or found_pres != expected_pres,
                    "latency_ms": elapsed_ms,
                }
            )

    summaries: dict[str, Any] = {}
    for strategy, recs in per_strategy.items():
        by_kind = {
            kind: summarize_records([r for r in recs if r["clue_kind"] == kind])
            for kind in sorted({r["clue_kind"] for r in recs})
        }
        summaries[strategy] = {
            **summarize_records(recs),
            "by_clue_kind": by_kind,
        }

    comparisons: dict[str, Any] = {}
    if "lexical" in per_strategy:
        lex_hits = [1.0 if r["first_relevant_rank"] == 1 else 0.0 for r in per_strategy["lexical"]]
        for strategy in strategies:
            if strategy == "lexical":
                continue
            cand_hits = [
                1.0 if r["first_relevant_rank"] == 1 else 0.0 for r in per_strategy[strategy]
            ]
            comparisons[f"{strategy}_vs_lexical"] = paired_hit1_comparison(cand_hits, lex_hits)
    if "hybrid" in per_strategy and "vector" in per_strategy:
        hyb_hits = [1.0 if r["first_relevant_rank"] == 1 else 0.0 for r in per_strategy["hybrid"]]
        vec_hits = [1.0 if r["first_relevant_rank"] == 1 else 0.0 for r in per_strategy["vector"]]
        comparisons["hybrid_vs_vector"] = paired_hit1_comparison(hyb_hits, vec_hits)

    return {
        "schema_version": "multichunk-benchmark-v1",
        "executed_at_utc": datetime.now(UTC).isoformat(),
        "release_version": release.manifest["release_version"],
        "release_fingerprint": release.fingerprint,
        "split": split,
        "strategies": list(strategies),
        "summaries": summaries,
        "paired_comparisons": comparisons,
        "records": per_strategy,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release", type=Path, default=DEFAULT_RELEASE)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--split", choices=("dev", "test", "all"), default="all")
    parser.add_argument("--strategies", default="exact,lexical")
    parser.add_argument("--include-vector", action="store_true")
    args = parser.parse_args()

    strategies = tuple(s.strip() for s in args.strategies.split(",") if s.strip())
    store = None
    if args.include_vector or any(s in {"vector", "hybrid"} for s in strategies):
        settings = get_settings()
        release = ConsolidatedRelease.load(args.release)
        chunks, manifest = load_chunks(
            release, ROOT / "data/derived/chunks" / release.manifest["release_version"]
        )
        embeddings = google_embeddings(settings.rag_embedding_model, settings.google_api_keys)
        store = open_index(
            release,
            chunks,
            manifest,
            ROOT / settings.rag_vector_dir,
            settings.rag_embedding_model,
            embeddings,
        )

    report = evaluate_multichunk(
        release_dir=args.release,
        dataset_path=args.dataset,
        strategies=strategies,
        split=args.split,
        store=store,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "summaries": report["summaries"],
                "paired_comparisons": report["paired_comparisons"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
