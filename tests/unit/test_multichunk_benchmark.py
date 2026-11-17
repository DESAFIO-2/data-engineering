"""Tests for the multi-chunk ranking benchmark and statistical evaluators."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from rag.config import ROOT

sys.path.insert(0, str(ROOT / "scripts"))
from eval_multichunk_benchmark import (  # noqa: E402
    bootstrap_ci,
    evaluate_multichunk,
    exact_mcnemar_pvalue,
    paired_hit1_comparison,
)


def test_paired_significance_helpers_compute_exact_bounds() -> None:
    ci = bootstrap_ci([1.0, 0.0, 1.0, 1.0], resamples=500, seed=42)
    assert ci is not None
    assert 0.0 <= ci["ci95_low"] <= ci["mean"] <= ci["ci95_high"] <= 1.0
    assert exact_mcnemar_pvalue(0, 0) == 1.0
    assert exact_mcnemar_pvalue(10, 0) < 0.005
    comp = paired_hit1_comparison([1.0, 1.0, 1.0, 0.0], [0.0, 0.0, 1.0, 0.0])
    assert comp["wins"] == 2
    assert comp["losses"] == 0
    assert comp["ties"] == 2


@pytest.mark.dvc
def test_multichunk_benchmark_dataset_has_disjoint_families_and_min_three_chunks() -> None:
    dataset = ROOT / "evals/datasets/multichunk_v9_benchmark.jsonl"
    rows = [
        json.loads(line)
        for line in dataset.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(rows) >= 60
    dev_families = {row["family_id"] for row in rows if row["split"] == "dev"}
    test_families = {row["family_id"] for row in rows if row["split"] == "test"}
    assert dev_families and test_families
    assert dev_families & test_families == set()
    assert all(row["candidate_chunk_count_verified"] >= 3 for row in rows)

    report = evaluate_multichunk(
        release_dir=ROOT / "data/releases/corpus-consolidado-v9-aprovado-2026-11-12",
        dataset_path=dataset,
        strategies=("exact", "lexical"),
        split="all",
    )
    assert report["summaries"]["exact"]["cases"] == len(rows)
    assert report["summaries"]["lexical"]["cases"] == len(rows)
    assert report["summaries"]["exact"]["min_candidate_chunk_count"] >= 3
    assert report["summaries"]["lexical"]["critical_confusions"] == 0
    assert (
        report["summaries"]["lexical"]["hit_at_1"]["mean"]
        > report["summaries"]["exact"]["hit_at_1"]["mean"]
    )


@pytest.mark.dvc
def test_multichunk_evaluator_supports_mock_vector_and_hybrid(tmp_path: Path) -> None:
    dataset = ROOT / "evals/datasets/multichunk_v9_benchmark.jsonl"

    first = json.loads(dataset.read_text(encoding="utf-8").splitlines()[0])
    subset = tmp_path / "subset.jsonl"
    subset.write_text(json.dumps(first, ensure_ascii=False) + "\n", encoding="utf-8")

    class FakeStore:
        def similarity_search_with_score(
            self, _question: str, *, k: int, filter: dict[str, Any]
        ) -> list[tuple[SimpleNamespace, float]]:
            assert k >= 3
            assert filter["medicine_id"]
            chunk_id = "chunk-" + first["relevant_ids"][0].removeprefix("evidence-")
            return [(SimpleNamespace(metadata={"chunk_id": chunk_id}), 0.01)]

    report = evaluate_multichunk(
        release_dir=ROOT / "data/releases/corpus-consolidado-v9-aprovado-2026-11-12",
        dataset_path=subset,
        strategies=("lexical", "vector", "hybrid"),
        split="all",
        store=FakeStore(),
    )
    assert report["summaries"]["vector"]["hit_at_1"]["mean"] == 1.0
    assert report["summaries"]["hybrid"]["hit_at_1"]["mean"] == 1.0
