"""The v9 development migration must not reopen the historical v8 test."""

from __future__ import annotations

import pytest

from rag.config import ROOT
from rag.consolidated import ConsolidatedRelease, load_chunks, search
from rag.consolidated_evaluation import _preflight
from scripts.archive.releases.v9.prepare_v9_retrieval_dev import CLARITHROMYCIN_EVIDENCE, prepare
from scripts.archive.releases.v9.prepare_v9_test_candidate import (
    prepare as prepare_independent_test,
)
from scripts.archive.releases.v9.promote_v9_test import promote

pytestmark = pytest.mark.dvc

RELEASE = ROOT / "data/releases/corpus-consolidado-v9-aprovado-2026-11-12"
CHUNKS = ROOT / "data/derived/chunks/corpus-consolidado-v9-aprovado-2026-11-12"


def test_v9_clarithromycin_expected_evidence_and_dev_split() -> None:
    cases = prepare()
    case = next(item for item in cases if item["id"] == "C-F03-005")
    assert case["split"] == "dev"
    assert set(case["relevant_ids"]) == CLARITHROMYCIN_EVIDENCE
    assert {ref["evidence_id"] for ref in case["expected_references"]} == CLARITHROMYCIN_EVIDENCE
    assert {ref["page"] for ref in case["expected_references"]} == {21, 22}
    assert {ref["source_row_number"] for ref in case["expected_references"]} == {247, 248, 249}
    assert all(item["review_status"] == "agent_reviewed" for item in cases)
    assert sum(item["split"] == "dev" for item in cases) == 92


def test_v9_historical_test_is_closed() -> None:
    release = ConsolidatedRelease.load(RELEASE)
    with pytest.raises(ValueError, match="Teste fechado"):
        _preflight(prepare(), release, "test", None)


def test_new_test_candidate_excludes_all_historical_families() -> None:
    historical = {item["family_id"] for item in prepare()}
    candidate = prepare_independent_test()
    assert len(candidate) == 28
    assert {item["family_id"] for item in candidate}.isdisjoint(historical)
    assert sum(item["expected_status"] == "matched" for item in candidate) == 24
    assert all(item["review_status"] == "agent_reviewed" for item in candidate)
    negatives = [item for item in candidate if item["expected_status"] == "not_in_scope"]
    assert {item["source_id"] for item in negatives} == {"F01", "F03", "F04"}
    assert all("99999" not in item["question"] for item in candidate)
    assert all("nesta apresentação" not in item["question"] for item in candidate)


def test_new_test_promotion_matches_human_review() -> None:
    cases = promote()
    assert len(cases) == 120
    assert sum(item["split"] == "dev" for item in cases) == 92
    test_cases = [item for item in cases if item["split"] == "test"]
    assert len(test_cases) == 28
    assert all(item["review_status"] == "reviewed" for item in test_cases)
    assert all(item["reviewer"] == "Jhiovana" for item in test_cases)


@pytest.mark.parametrize("strategy", ["exact", "lexical"])
def test_v9_clarithromycin_stays_in_one_documentary_presentation(strategy: str) -> None:
    release = ConsolidatedRelease.load(RELEASE)
    chunks, _ = load_chunks(release, CHUNKS)
    result = search(
        "claritromicina 500mg comprimido consta na REME DF?",
        release,
        chunks,
        strategy=strategy,
    )
    assert result["status"] == "matched"
    assert {item["evidence_id"] for item in result["evidence"]} == CLARITHROMYCIN_EVIDENCE
    assert len({item["medicine_id"] for item in result["evidence"]}) == 1
    assert {item["source"]["source_id"] for item in result["evidence"]} == {"F03"}
