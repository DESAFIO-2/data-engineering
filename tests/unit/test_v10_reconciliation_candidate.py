"""Deterministic v10 catalog collision reconciliation and unit normalization tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from rag.consolidated import (
    CHUNK_RECIPE_V2,
    chunk_for,
    ingredient_key,
    normalize,
)
from scripts.archive.releases.v10.publish_v10_candidate import (
    DESTINATION,
    SOURCE,
    SOURCE_MANIFEST_SHA256,
    build,
    canonical_key,
    reconcile_catalog,
)
from scripts.ingest.publish_consolidated_release import read_lines, verify


def test_normalize_handles_grams_percent_without_breaking_words() -> None:
    assert normalize("1g") == normalize("1 g") == "1 g"
    assert normalize("70%") == normalize("70 %") == "70 %"
    assert normalize("50mg/g") == normalize("50 mg/g") == "50 mg/g"
    assert normalize("10 gotas") == "10 gotas"


def test_reconcile_catalog_merges_colliding_entries_and_remaps_audit_offline() -> None:
    catalog: list[dict[str, Any]] = [
        {
            "medicine_id": "med-f01",
            "active_ingredient": "ceftriaxona",
            "strength": "1 g",
            "form": "pó para solução injetável",
            "release_characteristic": None,
            "source_ids": ["F01"],
            "occurrence_ids": ["occ-1"],
            "exact_presentation_supported": True,
        },
        {
            "medicine_id": "med-f03",
            "active_ingredient": "ceftriaxona",
            "strength": "1g",
            "form": "pó para solução injetável",
            "release_characteristic": None,
            "source_ids": ["F03"],
            "occurrence_ids": ["occ-2"],
            "exact_presentation_supported": True,
        },
        {
            "medicine_id": "med-met-f01",
            "active_ingredient": "cloridrato de metformina",
            "strength": "850 mg",
            "form": "comprimido",
            "release_characteristic": None,
            "source_ids": ["F01"],
            "occurrence_ids": ["occ-3"],
            "exact_presentation_supported": True,
        },
        {
            "medicine_id": "med-met-f03",
            "active_ingredient": "metformina (cloridrato)",
            "strength": "850 mg",
            "form": "comprimido",
            "release_characteristic": None,
            "source_ids": ["F03"],
            "occurrence_ids": ["occ-4"],
            "exact_presentation_supported": True,
        },
    ]
    occurrences: list[dict[str, Any]] = [
        {
            "occurrence_id": "occ-1",
            "medicine_id": "med-f01",
            "active_ingredient": "ceftriaxona",
            "strength": "1 g",
            "form": "pó para solução injetável",
            "raw_text": "ceftriaxona 1 g",
        },
        {
            "occurrence_id": "occ-2",
            "medicine_id": "med-f03",
            "active_ingredient": "ceftriaxona",
            "strength": "1g",
            "form": "pó para solução injetável",
            "raw_text": "ceftriaxona pó 1g literal",
        },
        {
            "occurrence_id": "occ-3",
            "medicine_id": "med-met-f01",
            "active_ingredient": "cloridrato de metformina",
            "strength": "850 mg",
            "form": "comprimido",
            "raw_text": "cloridrato de metformina 850 mg",
        },
        {
            "occurrence_id": "occ-4",
            "medicine_id": "med-met-f03",
            "active_ingredient": "metformina (cloridrato)",
            "strength": "850 mg",
            "form": "comprimido",
            "raw_text": "metformina (cloridrato) 850mg literal",
        },
    ]
    audit_log: list[dict[str, Any]] = [
        {
            "occurrence_id": "occ-2",
            "fields_verified": {"strength": "1g", "active_ingredient": "ceftriaxona"},
            "verification_result": "verified",
        }
    ]
    merged, updated_occ, updated_audit, records = reconcile_catalog(catalog, occurrences, audit_log)
    assert len(merged) == 2
    assert len(records) == 2
    assert {r["medicine_id"] for r in merged} == {"med-f01", "med-met-f01"}
    cef = next(r for r in merged if r["medicine_id"] == "med-f01")
    assert cef["occurrence_ids"] == ["occ-1", "occ-2"]
    assert cef["source_ids"] == ["F01", "F03"]

    occ2 = next(o for o in updated_occ if o["occurrence_id"] == "occ-2")
    assert occ2["medicine_id"] == "med-f01"
    assert occ2["strength"] == "1 g"
    assert occ2["raw_text"] == "ceftriaxona pó 1g literal"

    occ4 = next(o for o in updated_occ if o["occurrence_id"] == "occ-4")
    assert occ4["medicine_id"] == "med-met-f01"
    assert occ4["active_ingredient"] == "cloridrato de metformina"
    assert occ4["raw_text"] == "metformina (cloridrato) 850mg literal"

    assert updated_audit[0]["verification_result"] == "reconciled_v10_identity_normalization"
    assert updated_audit[0]["fields_verified"]["strength"] == "1 g"


@pytest.mark.dvc
def test_v10_candidate_eliminates_all_80_collisions_and_has_zero_duplicate_v2_chunks() -> None:
    prior = verify(SOURCE)
    candidate = verify(DESTINATION)
    assert prior["status"] == "approved"
    assert candidate["status"] == "pending_review"
    assert candidate["source_release"]["manifest_sha256"] == SOURCE_MANIFEST_SHA256
    assert candidate["files"]["catalog.jsonl"]["records"] == 1779
    assert candidate["files"]["occurrences.jsonl"]["records"] == 2114
    assert candidate["files"]["evidencias.jsonl"]["records"] == 2114

    payload, rebuilt = build()
    assert rebuilt["corpus_fingerprint"] == candidate["corpus_fingerprint"]
    assert payload["catalog.jsonl"] == (DESTINATION / "catalog.jsonl").read_bytes()

    catalog = read_lines(payload["catalog.jsonl"])
    keys = [
        (
            ingredient_key(m["active_ingredient"]),
            normalize(m["strength"]),
            normalize(m["form"]),
            normalize(m.get("release_characteristic") or ""),
        )
        for m in catalog
    ]
    assert len(set(keys)) == len(catalog) == 1779
    assert canonical_key(catalog[0]) == keys[0]

    evidence = read_lines(payload["evidencias.jsonl"])
    v2_chunks = [
        chunk_for(ev, candidate["release_version"], recipe=CHUNK_RECIPE_V2) for ev in evidence
    ]
    assert len({c["text"] for c in v2_chunks}) == len(v2_chunks) == 2114
    assert Path(DESTINATION / "domain_review.json").exists() is False
    quality = json.loads(payload["quality_report.json"])
    assert quality["corrections_applied"][-1]["merged_pairs"] == 80
