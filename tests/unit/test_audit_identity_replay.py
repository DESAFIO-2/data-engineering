"""Reexecução de regressões conhecidas no release v9 aprovado."""

import json
from pathlib import Path

import pytest

from rag.consolidated import ConsolidatedRelease, load_chunks, search

ROOT = Path(__file__).resolve().parents[2]
VERSION = "corpus-consolidado-v9-aprovado-2026-11-12"


@pytest.mark.dvc
@pytest.mark.parametrize(
    "case_id",
    [
        "C-F03-005",
        "V9-NEW-006",
        "V9-NEW-009",
        "V9-NEW-017",
        "V9-NEW-018",
        "V9-NEW-023",
    ],
)
def test_replay_identity_with_v9_references(case_id: str) -> None:
    release = ConsolidatedRelease.load(ROOT / "data/releases" / VERSION)
    chunks, _ = load_chunks(release, ROOT / "data/derived/chunks" / VERSION)
    dataset = ROOT / "evals/datasets/consolidated_v9_reviewed.jsonl"
    case = next(c for c in map(json.loads, dataset.read_text().splitlines()) if c["id"] == case_id)
    result = search(case["question"], release, chunks, strategy="lexical")
    assert result["status"] == "matched", case_id
    assert {e["evidence_id"] for e in result["evidence"]} == set(case["relevant_ids"])
    if case_id == "V9-NEW-009":
        mixed = case["question"] + " Qual dose devo tomar?"
        assert search(mixed, release, chunks, strategy="lexical")["status"] == "unsupported"
