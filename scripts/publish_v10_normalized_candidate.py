"""Publish the pending v10 normalized candidate from the approved v9 release.

Preserves all literal source fields from v9 (except audited F01 parser fixes
recorded in ``audit_log.jsonl``), attaches additive ``normalized`` fields,
recomputes catalog identity from canonical fields, emits ``normalization.json``
and ``id_map_v9_v10.json``, and verifies ``CHUNK_RECIPE_V3`` invariants.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

from publish_consolidated_release import digest, encoded, evidence_for, lines, read_lines, verify

from rag.consolidated import (
    CHUNK_RECIPE_V3,
    chunk_for,
)
from rag.normalization import (
    identity_key,
    load_vocabulary,
    normalize_occurrence,
    vocabulary_bundle,
)

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/releases/corpus-consolidado-v9-aprovado-2026-11-12"
VOCAB_DIR = ROOT / "data/vocab"
VERSION = "corpus-consolidado-v10-normalizada-2026-11-17"
DESTINATION = ROOT / "data/releases" / VERSION
SOURCE_MANIFEST_SHA256 = "ea72d7705cccf7a14c359bd67d60807ce5e994ecd541810f1a6d066d33f01a84"

_LITERAL_FIELDS = (
    "raw_text",
    "active_ingredient",
    "strength",
    "form",
    "channel",
    "source_code",
    "atc",
    "release_characteristic",
    "component",
)


def _apply_f01_parser_fixes(
    occurrences: list[dict[str, Any]],
    audit_by_occ: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Apply only the documented F01 parser fixes (53 null components + 0/ ,3 mg/mL)."""
    corrections: list[dict[str, Any]] = []
    for occ in occurrences:
        oid = occ["occurrence_id"]
        if occ["source"]["source_id"] == "F01" and occ.get("component") is None:
            parts = [part.strip() for part in occ["raw_text"].split("|")]
            if len(parts) < 5 or not parts[3]:
                raise ValueError(f"Componente F01 ausente em raw_text inválido: {oid}")
            occ["component"] = parts[3]
            corrections.append(
                {
                    "scope": "corrected_v10_parser",
                    "occurrence_id": oid,
                    "source_id": "F01",
                    "field": "component",
                    "before": None,
                    "after": parts[3],
                }
            )
            if oid in audit_by_occ:
                audit = audit_by_occ[oid]
                audit["prior_verification_result"] = audit.get("verification_result")
                audit["verification_result"] = "corrected_v10_parser"
                audit.setdefault("fields_verified", {})["component"] = parts[3]
                audit["notes_and_limitations"] = (
                    "Componente extraído da coluna 4 do raw_text F01 (parser omitira); "
                    "conferido contra o texto literal da linha."
                )
        if occ["source"]["source_id"] == "F01" and "0/ ,3 mg/mL" in (occ.get("strength") or ""):
            before = occ["strength"]
            after = before.replace("0/ ,3 mg/mL", "0,3 mg/mL")
            occ["strength"] = after
            corrections.append(
                {
                    "scope": "corrected_v10_parser",
                    "occurrence_id": oid,
                    "source_id": "F01",
                    "field": "strength",
                    "before": before,
                    "after": after,
                }
            )
            if oid in audit_by_occ:
                audit = audit_by_occ[oid]
                audit["prior_verification_result"] = audit.get("verification_result")
                audit["verification_result"] = "corrected_v10_parser"
                audit.setdefault("fields_verified", {})["strength"] = after
                audit["notes_and_limitations"] = (
                    "Artefato de quebra de linha PDF ('0/ ,3 mg/mL' -> '0,3 mg/mL') "
                    "conferido na p. 41 de rename-2024-2ed.pdf."
                )
    return corrections


def _catalog_rank(entry: dict[str, Any]) -> tuple[int, int, str]:
    return (
        0 if "F01" in entry.get("source_ids", []) else 1,
        -len(entry.get("occurrence_ids", [])),
        entry["medicine_id"],
    )


def _format_label(norm: dict[str, Any]) -> str:
    form = norm.get("form") or norm.get("specification") or "-"
    pkg = f" ({norm['package']})" if norm.get("package") else ""
    rel = f" | {norm['release']}" if norm.get("release") else ""
    return f"{norm['active_ingredient']} | {norm.get('strength') or '-'} | {form}{pkg}{rel}"


def reconcile_and_normalize(
    catalog: list[dict[str, Any]],
    occurrences: list[dict[str, Any]],
    audit_log: list[dict[str, Any]],
    vocab_dir: Path,
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    dict[str, Any],
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    """Normalize occurrences additively and recompute catalog identity."""
    catalog_copy = [json.loads(json.dumps(row)) for row in catalog]
    occ_copy = [json.loads(json.dumps(row)) for row in occurrences]
    audit_copy = [json.loads(json.dumps(row)) for row in audit_log]

    before_by_occ = {o["occurrence_id"]: json.loads(json.dumps(o)) for o in occurrences}
    audit_by_occ = {a["occurrence_id"]: a for a in audit_copy if a.get("occurrence_id")}

    parser_corrections = _apply_f01_parser_fixes(occ_copy, audit_by_occ)
    parser_fixed_fields = {(c["occurrence_id"], c["field"]) for c in parser_corrections}

    vocab = load_vocabulary(vocab_dir)
    for occ in occ_copy:
        occ["normalized"] = normalize_occurrence(occ, vocab)

    for oid, occ in ((o["occurrence_id"], o) for o in occ_copy):
        orig = before_by_occ[oid]
        for field in _LITERAL_FIELDS:
            if (oid, field) not in parser_fixed_fields and occ.get(field) != orig.get(field):
                raise AssertionError(f"Campo literal alterado indevidamente: {oid}.{field}")

    occ_by_id = {o["occurrence_id"]: o for o in occ_copy}
    groups: dict[tuple[str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for med in catalog_copy:
        keys = {
            identity_key(occ_by_id[oid]["normalized"], med["source_ids"])
            for oid in med["occurrence_ids"]
        }
        if len(keys) != 1:
            raise ValueError(f"Apresentação v9 dividida na normalização: {med['medicine_id']}")
        groups[next(iter(keys))].append(med)

    new_catalog: list[dict[str, Any]] = []
    id_map_all: dict[str, str] = {}
    merge_records: list[dict[str, Any]] = []
    remap_old_to_new: dict[str, str] = {}

    for med in catalog_copy:
        key = identity_key(occ_by_id[med["occurrence_ids"][0]]["normalized"], med["source_ids"])
        ranked = sorted(groups[key], key=_catalog_rank)
        canonical = ranked[0]
        if med["medicine_id"] != canonical["medicine_id"]:
            id_map_all[med["medicine_id"]] = canonical["medicine_id"]
            remap_old_to_new[med["medicine_id"]] = canonical["medicine_id"]
            continue

        all_occ_ids: list[str] = []
        for member in ranked:
            for oid in member["occurrence_ids"]:
                if oid not in all_occ_ids:
                    all_occ_ids.append(oid)
        rep_occ = sorted(
            (occ_by_id[oid] for oid in all_occ_ids),
            key=lambda o: (0 if o["source"]["source_id"] == "F01" else 1, o["occurrence_id"]),
        )[0]
        rep_norm = rep_occ["normalized"]
        source_ids = sorted({s for member in ranked for s in member["source_ids"]})
        aliases = sorted({occ_by_id[oid]["active_ingredient"] for oid in all_occ_ids})
        literal_forms = sorted({occ_by_id[oid]["form"] for oid in all_occ_ids})
        exact_supported = all(
            occ_by_id[oid]["normalized"]["form_kind"] != "absent"
            and occ_by_id[oid]["normalized"]["strength_kind"] != "absent"
            for oid in all_occ_ids
        )

        new_entry = {
            "medicine_id": canonical["medicine_id"],
            "active_ingredient": rep_norm["active_ingredient"],
            "strength": rep_norm["strength"] or "-",
            "form": rep_norm["form"] or "-",
            "package": rep_norm["package"],
            "specification": rep_norm["specification"],
            "form_kind": rep_norm["form_kind"],
            "release_characteristic": rep_norm["release"],
            "normalized_label": _format_label(rep_norm),
            "aliases": aliases,
            "literal_forms": literal_forms,
            "occurrence_ids": all_occ_ids,
            "source_ids": source_ids,
            "exact_presentation_supported": exact_supported,
            "review_status": "approved",
        }
        new_catalog.append(new_entry)
        id_map_all[canonical["medicine_id"]] = canonical["medicine_id"]

        for dup in ranked[1:]:
            merge_records.append(
                {
                    "canonical_medicine_id": canonical["medicine_id"],
                    "merged_medicine_id": dup["medicine_id"],
                    "canonical_label": new_entry["normalized_label"],
                    "before_label": (
                        f"{dup['active_ingredient']} | {dup['strength']} | {dup['form']}"
                    ),
                    "before_sources": dup["source_ids"],
                    "canonical_sources": source_ids,
                    "occurrence_ids": list(dup["occurrence_ids"]),
                }
            )

    for occ in occ_copy:
        old_mid = occ.get("medicine_id")
        if old_mid in remap_old_to_new:
            new_mid = remap_old_to_new[old_mid]
            occ["medicine_id"] = new_mid
            oid = occ["occurrence_id"]
            if (
                oid in audit_by_occ
                and audit_by_occ[oid].get("verification_result") != "corrected_v10_parser"
            ):
                audit = audit_by_occ[oid]
                audit["prior_verification_result"] = audit.get("verification_result")
                audit["verification_result"] = "reconciled_v10_identity_normalization"
                audit["notes_and_limitations"] = (
                    f"Reconciliado de {old_mid} para {new_mid} via normalização aditiva v10; "
                    "campos literais preservados na ocorrência. Aprovação de domínio pendente."
                )

    seen_keys = {
        identity_key(occ_by_id[m["occurrence_ids"][0]]["normalized"], m["source_ids"])
        for m in new_catalog
    }
    if len(seen_keys) != len(new_catalog):
        raise ValueError("Colisões de identidade ainda presentes após normalização v10")

    id_map = {
        "schema_version": "consolidated-id-map-v1",
        "mappings": id_map_all,
        "merged": merge_records,
        "counts": {
            "before": len(catalog_copy),
            "after": len(new_catalog),
            "absorbed": len(merge_records),
        },
    }
    return new_catalog, occ_copy, audit_copy, id_map, merge_records, parser_corrections


def build(
    source: Path = SOURCE,
    vocab_dir: Path = VOCAB_DIR,
    version: str = VERSION,
    expected_source_sha256: str | None = SOURCE_MANIFEST_SHA256,
    generated_at_utc: str | None = None,
) -> tuple[dict[str, bytes], dict[str, Any]]:
    """Build deterministic v10 normalized candidate artifacts in memory from an approved release."""
    original = (source / "release.json").read_bytes()
    if expected_source_sha256 is not None and digest(original) != expected_source_sha256:
        raise ValueError("Manifesto de origem diferente do auditado")
    prior = verify(source)
    payload: dict[str, bytes] = {
        name: (source / name).read_bytes()
        for name in prior["files"]
        if name != "domain_review.json"
    }
    catalog = read_lines(payload["catalog.jsonl"])
    occurrences = read_lines(payload["occurrences.jsonl"])
    audit_log = read_lines(payload["audit_log.jsonl"]) if "audit_log.jsonl" in payload else []
    descriptions: dict[str, Any] = json.loads(payload["f03_descriptions.json"])

    (
        new_catalog,
        new_occurrences,
        new_audit,
        id_map,
        merge_records,
        parser_corrections,
    ) = reconcile_and_normalize(catalog, occurrences, audit_log, vocab_dir)

    id_map["source_release"] = prior["release_version"]
    id_map["target_release"] = version
    norm_bundle = vocabulary_bundle(vocab_dir)
    evidence = [evidence_for(row, descriptions) for row in new_occurrences]

    v3_chunks = [chunk_for(ev, version, recipe=CHUNK_RECIPE_V3) for ev in evidence]
    if len({c["text"] for c in v3_chunks}) != len(v3_chunks):
        raise ValueError("Receita one-evidence-v3 gerou textos duplicados")
    occ_by_id = {o["occurrence_id"]: o for o in new_occurrences}
    for chunk in v3_chunks:
        occ = occ_by_id[chunk["occurrence_id"]]
        if occ["source"]["source_id"] == "F03":
            ct = occ["normalized"].get("channel_text")
            if ct and ct not in chunk["text"]:
                raise ValueError(f"Chunk F03 sem canal: {chunk['chunk_id']}")
            if occ.get("source_code") and occ["source_code"] not in chunk["text"]:
                raise ValueError(f"Chunk F03 sem código: {chunk['chunk_id']}")
        if occ["source"]["source_id"] == "F01" and occ.get("component"):
            if occ["component"] not in chunk["text"]:
                raise ValueError(f"Chunk F01 sem componente: {chunk['chunk_id']}")

    payload["catalog.jsonl"] = lines(new_catalog)
    payload["occurrences.jsonl"] = lines(new_occurrences)
    payload["evidencias.jsonl"] = lines(evidence)
    if "audit_log.jsonl" in payload:
        payload["audit_log.jsonl"] = lines(new_audit)
    payload["normalization.json"] = encoded(norm_bundle)
    payload["id_map_v9_v10.json"] = encoded(id_map)

    lengths = sorted(len(c["text"]) for c in v3_chunks)
    p95 = lengths[int(0.95 * (len(lengths) - 1))] if lengths else 0
    quality = json.loads(payload["quality_report.json"])
    quality["release_version"] = version
    quality["catalog_presentations"] = len(new_catalog)
    quality["exact_presentations_supported"] = sum(
        row["exact_presentation_supported"] for row in new_catalog
    )
    quality["partial_presentations_supported"] = sum(
        not row["exact_presentation_supported"] for row in new_catalog
    )
    quality["normalization_summary"] = {
        "schema_version": norm_bundle["schema_version"],
        "vocab_sha256": {name: info["sha256"] for name, info in norm_bundle["files"].items()},
        "catalog_before": len(catalog),
        "catalog_after": len(new_catalog),
        "merged_entries": len(merge_records),
        "parser_corrections": len(parser_corrections),
        "distinct_canonical_ingredients": len(
            {o["normalized"]["active_ingredient"] for o in new_occurrences}
        ),
        "distinct_canonical_forms": len(
            {o["normalized"]["form"] for o in new_occurrences if o["normalized"]["form"]}
        ),
        "f03_channels_with_codes": sum(
            bool(o["normalized"]["channel_codes"])
            for o in new_occurrences
            if o["source"]["source_id"] == "F03"
        ),
        "f03_occurrences": sum(o["source"]["source_id"] == "F03" for o in new_occurrences),
        "chunk_recipe": CHUNK_RECIPE_V3,
        "chunk_unique_texts": len({c["text"] for c in v3_chunks}),
        "chunk_p50_chars": lengths[len(lengths) // 2] if lengths else 0,
        "chunk_p95_chars": p95,
        "chunk_max_chars": lengths[-1] if lengths else 0,
    }
    quality["validation"] = (
        f"Normalização aditiva v10 concluída: {len(catalog)} -> {len(new_catalog)} apresentações "
        f"({len(merge_records)} absorções), {len(parser_corrections)} correções de parser F01 e "
        f"{len(v3_chunks)} chunks únicos em one-evidence-v3. Aprovação de domínio pendente."
    )
    quality.setdefault("corrections_applied", []).extend(parser_corrections)
    quality["corrections_applied"].append(
        {
            "scope": "v10_normalized_catalog",
            "merged_entries": len(merge_records),
            "catalog_before": len(catalog),
            "catalog_after": len(new_catalog),
            "chunk_recipe_verified": CHUNK_RECIPE_V3,
        }
    )
    if quality.get("limitations"):
        quality["limitations"][0] = "Aprovação de domínio deste novo release pendente."
    payload["quality_report.json"] = encoded(quality)

    manifest: dict[str, Any] = {
        key: value
        for key, value in prior.items()
        if key not in {"approval_scope", "domain_review_reference"}
    }
    manifest["release_version"] = version
    manifest["status"] = "pending_review"
    manifest["generated_at_utc"] = generated_at_utc or datetime.now(UTC).isoformat()
    manifest["source_release"] = {
        "version": prior["release_version"],
        "manifest_sha256": digest(original),
    }
    doc_ref = ROOT / "docs/reports/v10/README.md"
    manifest["review_reference"] = {
        "path": "docs/reports/v10/README.md",
        "sha256": digest(doc_ref.read_bytes()) if doc_ref.exists() else "",
        "scope": "Normalização aditiva v10, vocabulários embutidos e chunks v3 (F8 pendente).",
    }
    manifest["corpus_fingerprint"] = sha256(
        payload["catalog.jsonl"]
        + payload["occurrences.jsonl"]
        + payload["evidencias.jsonl"]
        + payload["normalization.json"]
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


def write_candidate(
    source: Path = SOURCE,
    vocab_dir: Path = VOCAB_DIR,
    destination: Path = DESTINATION,
    expected_source_sha256: str | None = SOURCE_MANIFEST_SHA256,
    overwrite: bool = False,
) -> dict[str, Any]:
    payload, manifest = build(
        source=source,
        vocab_dir=vocab_dir,
        version=destination.name,
        expected_source_sha256=expected_source_sha256,
    )
    if destination.exists() and overwrite:
        import shutil

        shutil.rmtree(destination)
    destination.mkdir(parents=False, exist_ok=False)
    for name, data in payload.items():
        (destination / name).write_bytes(data)
    (destination / "release.json").write_bytes(encoded(manifest))
    return verify(destination)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--vocab-dir", type=Path, default=VOCAB_DIR)
    parser.add_argument("--destination", type=Path, default=DESTINATION)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    expected = SOURCE_MANIFEST_SHA256 if args.source == SOURCE else None
    manifest = write_candidate(
        source=args.source,
        vocab_dir=args.vocab_dir,
        destination=args.destination,
        expected_source_sha256=expected,
        overwrite=args.overwrite,
    )
    print(
        json.dumps(
            {
                "release": manifest["release_version"],
                "status": manifest["status"],
                "manifest_sha256": digest((args.destination / "release.json").read_bytes()),
                "fingerprint": manifest["corpus_fingerprint"],
                "catalog_presentations": manifest["files"]["catalog.jsonl"]["records"],
                "occurrences": manifest["files"]["occurrences.jsonl"]["records"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
