"""The next holdout is traceable to the approved human review."""

from __future__ import annotations

import json
import sys
from collections import Counter

import pytest

from rag.config import ROOT
from rag.consolidated import normalize

pytestmark = pytest.mark.dvc

sys.path.insert(0, str(ROOT / "scripts"))
from prepare_v9_next_test_candidate import prepare  # noqa: E402
from promote_v9_next_test import promote  # noqa: E402


def test_candidate_has_traceable_evidence_and_declared_f04_reuse() -> None:
    cases = prepare()
    prior = [
        json.loads(line)
        for name in ("consolidated_v8_reviewed.jsonl", "consolidated_v9_reviewed.jsonl")
        for line in (ROOT / "evals/datasets" / name).read_text(encoding="utf-8").splitlines()
    ]
    old_families = {normalize(case["family_id"]) for case in prior}
    current_families = {
        normalize(case["family_id"])
        for case in prior
        if case["release_fingerprint"] == cases[0]["release_fingerprint"]
    }
    assert len(cases) == len({case["id"] for case in cases}) == 28
    assert Counter(case["source_id"] for case in cases) == {"F01": 12, "F03": 12, "F04": 4}
    assert Counter(case["expected_status"] for case in cases) == {
        "matched": 24,
        "not_in_scope": 4,
    }
    assert all(
        case["family_id"] not in old_families for case in cases if case["source_id"] != "F04"
    )
    assert all(case["family_id"] not in current_families for case in cases)
    assert all(case["family_reused_from_v8"] == (case["source_id"] == "F04") for case in cases)
    assert all(
        {ref["evidence_id"] for ref in case["expected_references"]} == set(case["relevant_ids"])
        for case in cases
    )


def test_candidate_promotion_matches_approved_review() -> None:
    cases = promote()
    assert len(cases) == 120
    assert sum(case["split"] == "test" for case in cases) == 28
    assert all(
        case["review_status"] == "reviewed" and case["reviewer"] == "Jhiovana"
        for case in cases
        if case["split"] == "test"
    )
