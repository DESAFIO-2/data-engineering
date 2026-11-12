"""Publish a pending v7 candidate from the four reviewed F03 code corrections.

The approved v6 directory is read-only. A separate domain decision is required
before this candidate can be used for indexing or retrieval.
"""

from __future__ import annotations

import csv
import json
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path

from publish_consolidated_release import digest, encoded, lines, read_lines, verify
from validate_v6_review import validate

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/releases/corpus-consolidado-v6-auditado-2026-11-11"
VERSION = "corpus-consolidado-v7-codigos-corrigidos-2026-11-11"
OUTPUT = ROOT / "data/releases" / VERSION
FINDINGS = ROOT / "docs/reports/v6-source-alignment-findings.json"
REVIEW = ROOT / "docs/reports/v6-source-alignment-review.csv"


def reviewed_corrections() -> dict[str, tuple[str, str]]:
    counts = validate(FINDINGS, REVIEW)
    if counts != {"aceitar_normalizacao": 205, "corrigir_release": 4, "manter_pendente": 0}:
        raise ValueError(f"Decisões inesperadas: {counts}")
    with REVIEW.open(encoding="utf-8-sig", newline="") as handle:
        decisions = list(csv.DictReader(handle))
    result = {}
    for row in decisions:
        if row["decision"] != "corrigir_release":
            continue
        if row["field"] != "source_code" or row["source"] != "F03":
            raise ValueError("Somente códigos F03 revisados podem ser corrigidos por este script")
        old, new = row["published"], row["extracted"]
        if len(new.split(", ")) < 2 or "".join(new.split(", ")) != old:
            raise ValueError(f"Separação de códigos inválida: {row['occurrence_id']}")
        result[row["occurrence_id"]] = old, new
    if len(result) != 4:
        raise ValueError("Esperadas quatro correções distintas")
    return result


def build() -> tuple[dict[str, bytes], dict]:
    corrections = reviewed_corrections()
    original_manifest_bytes = (SOURCE / "release.json").read_bytes()
    source_manifest = verify(SOURCE)
    payload = {
        name: (SOURCE / name).read_bytes()
        for name in source_manifest["files"]
        if name != "domain_review.json"
    }
    occurrences = read_lines(payload["occurrences.jsonl"])
    audit = read_lines(payload["audit_log.jsonl"])
    seen = set()
    for row in occurrences:
        oid = row["occurrence_id"]
        if oid in corrections:
            old, new = corrections[oid]
            if row["source_code"] != old:
                raise ValueError(f"Código original divergente: {oid}")
            row["source_code"] = new
            seen.add(oid)
    if seen != set(corrections):
        raise ValueError("Correções não encontradas nas ocorrências")
    for row in audit:
        oid = row["occurrence_id"]
        if oid in corrections:
            old, new = corrections[oid]
            if row["fields_verified"]["source_code"] != old:
                raise ValueError(f"Código do log divergente: {oid}")
            row["fields_verified"]["source_code"] = new
            row["verification_result"] = "corrected_from_source_alignment_review"
            row["notes_and_limitations"] = (
                "Separadores dos códigos F03 corrigidos conforme extração do PDF e decisão "
                "na planilha v6-source-alignment-review.csv; decisão final de domínio pendente."
            )
    payload["occurrences.jsonl"] = lines(occurrences)
    payload["audit_log.jsonl"] = lines(audit)
    evidence = read_lines(payload["evidencias.jsonl"])
    for row in evidence:
        row["review_status"] = "pending_review"
    payload["evidencias.jsonl"] = lines(evidence)
    quality = json.loads(payload["quality_report.json"])
    quality["release_version"] = VERSION
    quality["validation"] = (
        "2.115 entradas cobertas; 209 diferenças revisadas na planilha v6: "
        "205 normalizações aceitas, quatro códigos F03 corrigidos. Decisão final pendente."
    )
    quality["corrections_applied"].extend(
        {
            "occurrence_id": oid,
            "source_id": "F03",
            "field": "source_code",
            "before": old,
            "after": new,
        }
        for oid, (old, new) in corrections.items()
    )
    quality["limitations"][0] = "Decisão final de domínio e aprovação para indexação pendentes."
    payload["quality_report.json"] = encoded(quality)

    manifest = {
        key: value
        for key, value in source_manifest.items()
        if key not in {"approval_scope", "domain_review_reference"}
    }
    manifest["release_version"] = VERSION
    manifest["status"] = "pending_review"
    manifest["generated_at_utc"] = datetime.now(UTC).isoformat()
    manifest["source_release"] = {
        "version": source_manifest["release_version"],
        "manifest_sha256": digest(original_manifest_bytes),
    }
    manifest["review_reference"] = {
        "path": "docs/reports/v6-source-alignment-review.csv",
        "sha256": digest(REVIEW.read_bytes()),
        "scope": "209 decisões por campo; aprovação final da v7 pendente.",
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
    OUTPUT.mkdir(exist_ok=False)
    for name, data in payload.items():
        (OUTPUT / name).write_bytes(data)
    (OUTPUT / "release.json").write_bytes(encoded(manifest))
    verify(OUTPUT)
    print(
        json.dumps(
            {
                "release": VERSION,
                "status": manifest["status"],
                "fingerprint": manifest["corpus_fingerprint"],
            }
        )
    )


if __name__ == "__main__":
    main()
