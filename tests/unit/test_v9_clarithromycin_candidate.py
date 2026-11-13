"""Source-backed clarithromycin normalization without altering frozen v8."""

from __future__ import annotations

import json
import sys
from hashlib import sha256
from pathlib import Path

import pytest

from rag.config import ROOT
from rag.consolidated import ConsolidatedRelease, load_chunks

pytestmark = pytest.mark.dvc

sys.path.insert(0, str(ROOT / "scripts"))
from approve_v9_release import DESTINATION as APPROVED_DESTINATION  # noqa: E402
from publish_consolidated_release import read_lines, verify  # noqa: E402
from publish_v9_clarithromycin import (  # noqa: E402
    CANONICAL_MEDICINE_ID,
    DESTINATION,
    OCCURRENCE_ID,
    OLD_MEDICINE_ID,
    SOURCE,
    SOURCE_MANIFEST_SHA256,
    build,
)


def test_candidate_has_one_normalized_occurrence_and_one_merged_catalog_entry() -> None:
    prior = verify(SOURCE)
    candidate = verify(DESTINATION)
    assert prior["status"] == "approved"
    assert candidate["status"] == "pending_review"
    assert candidate["source_release"]["manifest_sha256"] == SOURCE_MANIFEST_SHA256
    assert candidate["files"]["catalog.jsonl"]["records"] == 1859
    assert candidate["files"]["occurrences.jsonl"]["records"] == 2114
    assert candidate["files"]["evidencias.jsonl"]["records"] == 2114
    payload, rebuilt = build()
    assert rebuilt["corpus_fingerprint"] == candidate["corpus_fingerprint"]
    assert payload["occurrences.jsonl"] == (DESTINATION / "occurrences.jsonl").read_bytes()
    old = {r["occurrence_id"]: r for r in read_lines((SOURCE / "occurrences.jsonl").read_bytes())}
    new = {r["occurrence_id"]: r for r in read_lines(payload["occurrences.jsonl"])}
    assert old.keys() == new.keys()
    changed = {oid: {k for k in old[oid] if old[oid][k] != new[oid][k]} for oid in old}
    assert {oid: fields for oid, fields in changed.items() if fields} == {
        OCCURRENCE_ID: {"strength", "medicine_id"}
    }
    row = new[OCCURRENCE_ID]
    assert row["strength"] == "500 mg"
    assert row["medicine_id"] == CANONICAL_MEDICINE_ID
    assert row["source_code"] == "MSE8831"
    assert row["channel"] == old[OCCURRENCE_ID]["channel"]
    assert "500mg" in row["raw_text"]


def test_catalog_merge_keeps_all_occurrences_and_source_provenance() -> None:
    catalog = read_lines((DESTINATION / "catalog.jsonl").read_bytes())
    assert not any(m["medicine_id"] == OLD_MEDICINE_ID for m in catalog)
    med = next(m for m in catalog if m["medicine_id"] == CANONICAL_MEDICINE_ID)
    assert len(med["occurrence_ids"]) == 4
    assert OCCURRENCE_ID in med["occurrence_ids"]
    assert med["source_ids"] == ["F01", "F03"]
    evidence = read_lines((DESTINATION / "evidencias.jsonl").read_bytes())
    linked = next(e for e in evidence if e["occurrence_id"] == OCCURRENCE_ID)
    assert linked["medicine_id"] == CANONICAL_MEDICINE_ID
    assert linked["strength"] == "500 mg"
    assert linked["source"]["page"] == 22
    assert linked["source_row_number"] == 249
    assert linked["review_status"] == "pending_review"


def test_frozen_source_pdf_and_v8_manifest_still_match() -> None:
    prior = json.loads((SOURCE / "release.json").read_text(encoding="utf-8"))
    pdf = ROOT / "data/raw/F03-reme-df/reme-df-2026-10-29.pdf"
    assert sha256(pdf.read_bytes()).hexdigest() == prior["sources"]["F03"]["sha256"]
    assert sha256((SOURCE / "release.json").read_bytes()).hexdigest() == SOURCE_MANIFEST_SHA256
    assert Path(DESTINATION / "domain_review.json").exists() is False


def test_approved_v9_has_recorded_decision_and_canonical_chunks() -> None:
    manifest = verify(APPROVED_DESTINATION)
    assert manifest["status"] == "approved"
    assert manifest["files"]["catalog.jsonl"]["records"] == 1859
    assert (
        manifest["source_release"]["manifest_sha256"]
        == sha256((DESTINATION / "release.json").read_bytes()).hexdigest()
    )
    review = json.loads((APPROVED_DESTINATION / "domain_review.json").read_text(encoding="utf-8"))
    assert review["reviewer"] == "Jhiovana"
    assert review["decision"] == "approved"
    release = ConsolidatedRelease.load(APPROVED_DESTINATION)
    chunks, chunk_manifest = load_chunks(
        release, ROOT / "data/derived/chunks/corpus-consolidado-v9-aprovado-2026-11-12"
    )
    assert len(chunks) == 2114
    assert chunk_manifest["release_fingerprint"] == release.fingerprint
    item = next(c for c in chunks if c["occurrence_id"] == OCCURRENCE_ID)
    assert item["medicine_id"] == CANONICAL_MEDICINE_ID
    assert "500mg" in item["literal_text"]
    assert "500 mg" in item["text"]
