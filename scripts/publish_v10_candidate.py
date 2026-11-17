"""Publish a pending v10 candidate reconciling all 80 normalized catalog collisions."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

from publish_consolidated_release import digest, encoded, evidence_for, lines, read_lines, verify

from rag.consolidated import (
    CHUNK_RECIPE_V2,
    chunk_for,
    ingredient_key,
    normalize,
)

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/releases/corpus-consolidado-v9-aprovado-2026-11-12"
VERSION = "corpus-consolidado-v10-reconciliada-2026-11-16"
DESTINATION = ROOT / "data/releases" / VERSION
SOURCE_MANIFEST_SHA256 = "ea72d7705cccf7a14c359bd67d60807ce5e994ecd541810f1a6d066d33f01a84"

_SPACED_UNIT_RE = re.compile(r"\d\s+(?:mcg|mg|g|ml|ui|%)", re.IGNORECASE)


def canonical_key(row: dict[str, Any]) -> tuple[str, str, str, str]:
    """Return the normalized identity key for catalog presentation deduplication."""
    return (
        ingredient_key(row["active_ingredient"]),
        normalize(row["strength"]),
        normalize(row["form"]),
        normalize(row.get("release_characteristic") or ""),
    )


def _canonical_rank(row: dict[str, Any]) -> tuple[int, int, int, int, str]:
    has_f01 = 0 if "F01" in row.get("source_ids", []) else 1
    has_spaced_unit = 0 if _SPACED_UNIT_RE.search(row["strength"]) else 1
    non_ascii_chars = sum(not ch.isascii() for ch in row["active_ingredient"])
    occ_count = len(row.get("occurrence_ids", []))
    return (has_f01, has_spaced_unit, -non_ascii_chars, -occ_count, row["medicine_id"])


def reconcile_catalog(
    catalog: list[dict[str, Any]],
    occurrences: list[dict[str, Any]],
    audit_log: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Merge colliding catalog entries and remap occurrences and audit records deterministically."""
    groups: dict[tuple[str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    catalog_copy = [json.loads(json.dumps(row)) for row in catalog]
    occurrences_copy = [json.loads(json.dumps(row)) for row in occurrences]
    audit_copy = [json.loads(json.dumps(row)) for row in audit_log]

    for row in catalog_copy:
        groups[canonical_key(row)].append(row)

    merged_catalog: list[dict[str, Any]] = []
    remap_by_old_id: dict[str, dict[str, Any]] = {}
    merge_records: list[dict[str, Any]] = []

    for row in catalog_copy:
        key = canonical_key(row)
        group = groups[key]
        ranked = sorted(group, key=_canonical_rank)
        canonical = ranked[0]
        if row["medicine_id"] != canonical["medicine_id"]:
            remap_by_old_id[row["medicine_id"]] = canonical
            continue
        for duplicate in ranked[1:]:
            for oid in duplicate["occurrence_ids"]:
                if oid not in canonical["occurrence_ids"]:
                    canonical["occurrence_ids"].append(oid)
            canonical["source_ids"] = sorted(
                set(canonical["source_ids"]) | set(duplicate["source_ids"])
            )
            merge_records.append(
                {
                    "canonical_medicine_id": canonical["medicine_id"],
                    "merged_medicine_id": duplicate["medicine_id"],
                    "canonical_label": (
                        f"{canonical['active_ingredient']} | "
                        f"{canonical['strength']} | {canonical['form']}"
                    ),
                    "before_label": (
                        f"{duplicate['active_ingredient']} | "
                        f"{duplicate['strength']} | {duplicate['form']}"
                    ),
                    "occurrence_ids": list(duplicate["occurrence_ids"]),
                }
            )
        merged_catalog.append(canonical)

    occ_to_merge: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {}
    for occ in occurrences_copy:
        old_id = occ.get("medicine_id")
        if old_id in remap_by_old_id:
            canonical = remap_by_old_id[old_id]
            before = {
                "medicine_id": old_id,
                "active_ingredient": occ["active_ingredient"],
                "strength": occ["strength"],
                "form": occ["form"],
            }
            occ["medicine_id"] = canonical["medicine_id"]
            occ["active_ingredient"] = canonical["active_ingredient"]
            occ["strength"] = canonical["strength"]
            occ["form"] = canonical["form"]
            occ_to_merge[occ["occurrence_id"]] = (before, canonical)

    for entry in audit_copy:
        oid = entry.get("occurrence_id")
        if oid in occ_to_merge:
            before, canonical = occ_to_merge[oid]
            verified = entry.setdefault("fields_verified", {})
            verified["active_ingredient"] = canonical["active_ingredient"]
            verified["strength"] = canonical["strength"]
            verified["form"] = canonical["form"]
            entry["verification_result"] = "reconciled_v10_identity_normalization"
            entry["notes_and_limitations"] = (
                f"Reconciliado de {before['medicine_id']} "
                f"({before['active_ingredient']} | {before['strength']}) "
                f"para {canonical['medicine_id']} "
                f"({canonical['active_ingredient']} | {canonical['strength']}); "
                "raw_text, códigos e canais mantidos literais por ocorrência. "
                "Aprovação de domínio do novo release pendente."
            )

    remaining_groups: dict[tuple[str, str, str, str], int] = defaultdict(int)
    for row in merged_catalog:
        remaining_groups[canonical_key(row)] += 1
    if any(count != 1 for count in remaining_groups.values()):
        raise ValueError("Colisões de identidade ainda presentes após reconciliação v10")

    return merged_catalog, occurrences_copy, audit_copy, merge_records


def build(source: Path = SOURCE, version: str = VERSION) -> tuple[dict[str, bytes], dict[str, Any]]:
    """Build deterministic v10 candidate artifacts in memory from verified v9."""
    original = (source / "release.json").read_bytes()
    if source == SOURCE and digest(original) != SOURCE_MANIFEST_SHA256:
        raise ValueError("Manifesto v9 diferente do auditado")
    prior = verify(source)
    payload = {
        name: (source / name).read_bytes()
        for name in prior["files"]
        if name != "domain_review.json"
    }
    catalog = read_lines(payload["catalog.jsonl"])
    occurrences = read_lines(payload["occurrences.jsonl"])
    audit_log = read_lines(payload["audit_log.jsonl"])
    descriptions: dict[str, Any] = json.loads(payload["f03_descriptions.json"])

    merged_catalog, updated_occurrences, updated_audit, merge_records = reconcile_catalog(
        catalog, occurrences, audit_log
    )
    evidence = [evidence_for(row, descriptions) for row in updated_occurrences]

    v2_texts = {chunk_for(ev, version, recipe=CHUNK_RECIPE_V2)["text"] for ev in evidence}
    if len(v2_texts) != len(evidence):
        raise ValueError("Receita one-evidence-v2 ainda gera textos duplicados no candidato v10")

    payload["catalog.jsonl"] = lines(merged_catalog)
    payload["occurrences.jsonl"] = lines(updated_occurrences)
    payload["audit_log.jsonl"] = lines(updated_audit)
    payload["evidencias.jsonl"] = lines(evidence)

    quality = json.loads(payload["quality_report.json"])
    quality["release_version"] = version
    quality["catalog_presentations"] = len(merged_catalog)
    quality["exact_presentations_supported"] = sum(
        row["exact_presentation_supported"] for row in merged_catalog
    )
    quality["validation"] = (
        f"Reconciliados {len(merge_records)} pares de colisão de identidade no catálogo "
        f"({len(catalog)} -> {len(merged_catalog)} apresentações) usando normalização "
        "canônica e preservação integral do raw_text; zero chunks duplicados em one-evidence-v2. "
        "Aprovação de domínio do novo release pendente."
    )
    quality.setdefault("corrections_applied", []).append(
        {
            "scope": "v10_catalog_reconciliation",
            "merged_pairs": len(merge_records),
            "catalog_before": len(catalog),
            "catalog_after": len(merged_catalog),
            "chunk_recipe_verified": CHUNK_RECIPE_V2,
        }
    )
    quality["limitations"][0] = "Aprovação de domínio deste novo release pendente."
    payload["quality_report.json"] = encoded(quality)

    manifest: dict[str, Any] = {
        key: value
        for key, value in prior.items()
        if key not in {"approval_scope", "domain_review_reference"}
    }
    manifest["release_version"] = version
    manifest["status"] = "pending_review"
    manifest["generated_at_utc"] = datetime.now(UTC).isoformat()
    manifest["source_release"] = {
        "version": prior["release_version"],
        "manifest_sha256": digest(original),
    }
    manifest["review_reference"] = {
        "path": "docs/reports/v9/diagnostico-colisoes-v9-para-v10.md",
        "sha256": digest(
            (ROOT / "docs/reports/v9/diagnostico-colisoes-v9-para-v10.md").read_bytes()
        ),
        "scope": "Inventário determinístico das 80 colisões reconciliadas nesta build.",
    }
    manifest["corpus_fingerprint"] = sha256(
        payload["catalog.jsonl"] + payload["occurrences.jsonl"] + payload["evidencias.jsonl"]
    ).hexdigest()
    manifest["files"] = {
        name: {
            "sha256": digest(data),
            "bytes": len(data),
            **({"records": len(read_lines(data))} if name.endswith(".jsonl") else {}),
        }
        for name, data in payload.items()
    }
    return payload, manifest


def main() -> None:
    payload, manifest = build()
    DESTINATION.mkdir(exist_ok=False)
    for name, data in payload.items():
        (DESTINATION / name).write_bytes(data)
    (DESTINATION / "release.json").write_bytes(encoded(manifest))
    verify(DESTINATION)
    print(
        json.dumps(
            {
                "release": VERSION,
                "status": manifest["status"],
                "manifest_sha256": digest((DESTINATION / "release.json").read_bytes()),
                "fingerprint": manifest["corpus_fingerprint"],
                "catalog_presentations": manifest["files"]["catalog.jsonl"]["records"],
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
