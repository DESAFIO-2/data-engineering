"""Tests for audited release corpus-consolidado-v6-auditado-2026-11-11 and real defects fixed."""

from __future__ import annotations

import json
from typing import Any

import pytest

from rag.config import ROOT
from rag.consolidated import ConsolidatedRelease, load_chunks, search

V6_DIR = ROOT / "data/releases/corpus-consolidado-v6-auditado-2026-11-11"
V6_CHUNK_DIR = ROOT / "data/derived/chunks/corpus-consolidado-v6-auditado-2026-11-11"


@pytest.fixture(scope="module")
def v6_corpus() -> tuple[ConsolidatedRelease, list[dict[str, Any]], dict[str, Any]]:
    rel = ConsolidatedRelease.load(V6_DIR)
    chunks, manifest = load_chunks(rel, V6_CHUNK_DIR)
    return rel, chunks, manifest


def test_v6_release_integrity_and_counts(
    v6_corpus: tuple[ConsolidatedRelease, list[dict[str, Any]], dict[str, Any]],
) -> None:
    rel, chunks, manifest = v6_corpus
    assert rel.manifest["release_version"] == "corpus-consolidado-v6-auditado-2026-11-11"
    assert rel.manifest["status"] == "approved"
    assert len(rel.catalog) == 1860
    assert len(rel.occurrences) == 2114
    assert len(rel.evidence) == 2114
    assert len(chunks) == 2114

    # Quality report checks
    qr = json.loads((V6_DIR / "quality_report.json").read_bytes())
    assert qr["catalog_presentations"] == 1860
    assert qr["exact_presentations_supported"] == 1781
    assert qr["partial_presentations_supported"] == 79
    assert qr["occurrences"] == 2114
    assert qr["supplies"] == 29
    assert qr["excluded_source_rows"] == 1
    assert qr["legacy_chunk_references_remaining"] == 0
    assert qr["total_audited_records"] == 2115


def test_v6_audit_log_complete_coverage() -> None:
    audit_file = V6_DIR / "audit_log.jsonl"
    records = [
        json.loads(line)
        for line in audit_file.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(records) == 2115

    # Check 1 exclusion
    exclusions = [r for r in records if r["verification_result"] == "excluded_source_blank"]
    assert len(exclusions) == 1
    assert exclusions[0]["source_row_number"] == 987
    assert exclusions[0]["source_id"] == "F03"

    # Check legitimate absences documented
    absent = [r for r in records if r["verification_result"] == "legitimate_absence_documented"]
    assert len(absent) >= 79

    # Check that every record has verification method and agent verdict
    for r in records:
        assert r["verification_method"] in {
            "automated_table_geometry_reconciliation",
            "agent_cell_inspection",
            "agent_inspection_and_correction",
        }
        assert (
            "tecnicamente" in r["agent_audit_verdict"] or "confirmada" in r["agent_audit_verdict"]
        )


def test_no_legacy_chunks_in_v6(
    v6_corpus: tuple[ConsolidatedRelease, list[dict[str, Any]], dict[str, Any]],
) -> None:
    rel, _, _ = v6_corpus
    for occ in rel.occurrences:
        assert "chunk_ids" in occ
        for cid in occ["chunk_ids"]:
            assert not cid.startswith("ev-"), (
                f"Found legacy chunk ID {cid} in {occ['occurrence_id']}"
            )
            assert cid.startswith("chunk-"), f"Invalid chunk ID format: {cid}"
        if "context" in occ and "page_chunk_ids" in occ["context"]:
            assert occ["context"]["page_chunk_ids"] == [], (
                f"Found page_chunk_ids in {occ['occurrence_id']}"
            )


def test_defect_fix_fenoximetilpenicilina(
    v6_corpus: tuple[ConsolidatedRelease, list[dict[str, Any]], dict[str, Any]],
) -> None:
    rel, chunks, _ = v6_corpus
    occ = next(o for o in rel.occurrences if o["occurrence_id"] == "occ-ef6f34aca6aebf7145e278f7")
    assert occ["active_ingredient"] == "fenoximetilpenicilina potássica"
    assert "fenoximetilpenicili- na" not in occ["active_ingredient"]
    assert "fenoximetilpenicili- na" not in occ["raw_text"]

    # Search works with corrected name
    res = search(
        "fenoximetilpenicilina potássica 80.000 UI/mL pó para solução oral RENAME",
        rel,
        chunks,
        strategy="lexical",
    )
    assert res["status"] == "matched"
    assert res["medicine"]["active_ingredient"] == "fenoximetilpenicilina potássica"


def test_defect_fix_mikania_no_guaco_in_row_695(
    v6_corpus: tuple[ConsolidatedRelease, list[dict[str, Any]], dict[str, Any]],
) -> None:
    rel, chunks, _ = v6_corpus
    occ = next(o for o in rel.occurrences if o["occurrence_id"] == "occ-be1655419eff7210901c7689")
    assert occ["active_ingredient"] == "mikania glomerata spreng"
    assert "(guaco)" not in occ["active_ingredient"]

    res = search(
        "mikania glomerata spreng frasco 100 mL xarope REME DF", rel, chunks, strategy="lexical"
    )
    assert res["status"] == "matched"
    assert res["medicine"]["active_ingredient"] == "mikania glomerata spreng"


def test_defect_fix_f03_descriptions_unscrambled() -> None:
    descs = json.loads((V6_DIR / "f03_descriptions.json").read_bytes())
    # Row 401 enoxaparina
    assert descs["occ-5f7997b117b91bc5116af411"]["description"] == (
        "enoxaparina sódica solução injetável 100 mg seringa preenchida 1 mL"
        " (exclusivo cardiologia)"
    )
    # Row 513 gonadotropina
    assert descs["occ-af1624a4b969c7919f5679a8"]["description"] == (
        "gonadotropina corionica humana (HCG) altamente purificada injetável 5.000 UI"
        " frasco-ampola ou ampola"
    )
    # Row 537 idarrubicina
    assert descs["occ-b879a83bc8d1df5f6782d4c0"]["description"] == (
        "idarrubicina (cloridrato) pó liofilizado para solução injetável 10 mg frasco-am- pola"
    )
    # Row 549 imunoglobulina hepatite B
    assert descs["occ-a596d31c38478c8ac04c63ca"]["description"] == (
        "imunoglobulina humana anti-hepatite B solução injetável 1000 UI"
        " ampola ou frasco - hepatite B"
    )
    # Row 945 simeticona
    assert (
        descs["occ-949c15370770ba5bc47c6b8f"]["description"]
        == "simeticona emulsao ou solução ou suspensão oral gotas 75 mg/mL frasco 10mL a 15mL"
    )


def test_creme_routing_does_not_hijack_to_f03(
    v6_corpus: tuple[ConsolidatedRelease, list[dict[str, Any]], dict[str, Any]],
) -> None:
    rel, chunks, _ = v6_corpus
    # 'creme' contains 'reme' as a substring; word boundary ensures it routes to F01 (RENAME)
    res = search("imiquimode 50 mg/g creme consta na RENAME?", rel, chunks, strategy="lexical")
    assert res["status"] == "matched"
    assert res["medicine"]["source_ids"] == ["F01"]
    assert res["evidence"][0]["source"]["source_id"] == "F01"
