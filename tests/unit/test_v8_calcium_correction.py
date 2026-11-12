"""The F03 calcium correction is traceable and cannot silently approve v8."""

from __future__ import annotations

import json
import sys

from rag.config import ROOT
from rag.consolidated import ConsolidatedRelease, load_chunks, search
from rag.consolidated_evaluation import _preflight

sys.path.insert(0, str(ROOT / "scripts"))
from prepare_v8_retrieval_eval import prepare  # noqa: E402
from publish_consolidated_release import verify  # noqa: E402
from publish_v8_calcium_correction import (  # noqa: E402
    DESTINATION,
    MEDICINE_ID,
    NEW,
    OCCURRENCE_ID,
    SOURCE,
    SOURCE_MANIFEST_SHA256,
    build,
)
from validate_v8_calcium_review import validate  # noqa: E402


def test_v8_release_corrects_one_source_record_and_remains_pending() -> None:
    prior = verify(SOURCE)
    candidate = verify(DESTINATION)
    assert prior["status"] == "approved"
    assert candidate["status"] == "pending_review"
    assert candidate["source_release"]["manifest_sha256"] == SOURCE_MANIFEST_SHA256
    payload, rebuilt = build()
    assert rebuilt["corpus_fingerprint"] == candidate["corpus_fingerprint"]
    assert payload["occurrences.jsonl"] == (DESTINATION / "occurrences.jsonl").read_bytes()
    occurrences = [json.loads(line) for line in payload["occurrences.jsonl"].splitlines()]
    catalog = [json.loads(line) for line in payload["catalog.jsonl"].splitlines()]
    assert next(x for x in occurrences if x["occurrence_id"] == OCCURRENCE_ID)["strength"] == NEW
    assert next(x for x in catalog if x["medicine_id"] == MEDICINE_ID)["strength"] == NEW


def test_v8_gabarito_changes_only_rejected_case() -> None:
    cases = prepare()
    assert len(cases) == 119
    case = next(x for x in cases if x["id"] == "C-F03-003")
    assert "500 ou 600 mg" in case["question"]
    assert case["expected_references"][0]["strength"] == NEW
    assert case["review_status"] == "agent_reviewed"


def test_v8_human_review_and_approved_release() -> None:
    result = validate()
    assert result["prior_approved_carried"] == 118
    assert result["corrected_case_approved"]
    assert not result["errors"]
    release = ConsolidatedRelease.load(
        ROOT / "data/releases/corpus-consolidado-v8-aprovado-2026-11-11"
    )
    chunks, manifest = load_chunks(
        release, ROOT / "data/derived/chunks/corpus-consolidado-v8-aprovado-2026-11-11"
    )
    assert len(chunks) == 2114
    assert manifest["release_fingerprint"] == release.fingerprint
    cases = [
        json.loads(line)
        for line in (ROOT / "evals/datasets/consolidated_v8_reviewed.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    _preflight(
        cases,
        release,
        "test",
        ROOT / "docs/reports/v8/v8-calcium-correction-review.xlsx",
        ROOT / "docs/reports/v7/v7-retrieval-review.xlsx",
    )


def test_v8_alternative_strength_is_retrieved_without_range_equivalence() -> None:
    release = ConsolidatedRelease.load(
        ROOT / "data/releases/corpus-consolidado-v8-aprovado-2026-11-11"
    )
    chunks, _ = load_chunks(
        release, ROOT / "data/derived/chunks/corpus-consolidado-v8-aprovado-2026-11-11"
    )
    documented = search(
        "carbonato de cálcio (equivalente a 500 ou 600 mg de cálcio) + "
        "colecalciferol 400 UI comprimido consta na REME-DF?",
        release,
        chunks,
        strategy="exact",
    )
    assert documented["status"] == "matched"
    assert [e["evidence_id"] for e in documented["evidence"]] == [
        "evidence-bc5acf38f4260802e843100c"
    ]
    wrong_range = search(
        "carbonato de cálcio (equivalente a 500 a 600 mg de cálcio) + "
        "colecalciferol 400 UI comprimido consta na REME-DF?",
        release,
        chunks,
        strategy="exact",
    )
    assert wrong_range["status"] != "matched"
