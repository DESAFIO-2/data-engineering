"""Publish a pending v8 candidate correcting F03 row 194 after human rejection."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path

from publish_consolidated_release import digest, encoded, evidence_for, lines, read_lines, verify
from validate_v7_retrieval_review import read_sheet

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/releases/corpus-consolidado-v7-aprovado-2026-11-11"
VERSION = "corpus-consolidado-v8-calcio-corrigido-2026-11-11"
DESTINATION = ROOT / "data/releases" / VERSION
REVIEW = ROOT / "docs/reports/v7-retrieval-review.xlsx"
SOURCE_MANIFEST_SHA256 = "8399f37f6664f474c18622d912ad9795f04ec199102724cfafbe6e295eeab20b"
OCCURRENCE_ID = "occ-bc5acf38f4260802e843100c"
MEDICINE_ID = "med-00aabf5466ef008e27b6fbab"
OLD = "500 mg a 600 mg cálcio elementar + 400 UI vit. D"
NEW = "equivalente a 500 ou 600 mg de cálcio + colecalciferol 400 UI"


def replace_one(rows: list[dict], key: str, identifier: str, field: str = "strength") -> None:
    matches = [row for row in rows if row[key] == identifier]
    if len(matches) != 1 or matches[0][field] != OLD:
        raise ValueError(f"Registro original divergente: {key}={identifier}")
    matches[0][field] = NEW


def build() -> tuple[dict[str, bytes], dict]:
    original = (SOURCE / "release.json").read_bytes()
    if digest(original) != SOURCE_MANIFEST_SHA256:
        raise ValueError("Manifesto v7 diferente do revisado")
    prior = verify(SOURCE)
    review_rows = read_sheet(REVIEW)
    reviewed = [r for r in review_rows if r["case_id"] == "C-F03-003"]
    if (
        len(reviewed) != 1
        or reviewed[0]["decision"] != "rejeitar"
        or reviewed[0]["reviewer"] != "Jhiovana"
    ):
        raise ValueError("Rejeição humana C-F03-003 ausente")
    payload = {
        name: (SOURCE / name).read_bytes()
        for name in prior["files"]
        if name != "domain_review.json"
    }
    occurrences = read_lines(payload["occurrences.jsonl"])
    catalog = read_lines(payload["catalog.jsonl"])
    audit = read_lines(payload["audit_log.jsonl"])
    replace_one(occurrences, "occurrence_id", OCCURRENCE_ID)
    replace_one(catalog, "medicine_id", MEDICINE_ID)
    matches = [row for row in audit if row["occurrence_id"] == OCCURRENCE_ID]
    if len(matches) != 1 or matches[0]["fields_verified"]["strength"] != OLD:
        raise ValueError("Log de auditoria v7 divergente")
    matches[0]["fields_verified"]["strength"] = NEW
    matches[0]["verification_result"] = "corrected_after_v7_retrieval_review"
    matches[0]["notes_and_limitations"] = (
        "REME-DF p. 19, linha 194: 'equivalente a 500 ou 600 mg de cálcio'; "
        "rejeição humana C-F03-003 em v7-retrieval-review.xlsx. Aprovação do novo release pendente."
    )
    payload["occurrences.jsonl"] = lines(occurrences)
    payload["catalog.jsonl"] = lines(catalog)
    payload["audit_log.jsonl"] = lines(audit)
    descriptions = json.loads(payload["f03_descriptions.json"])
    evidence = [evidence_for(row, descriptions) for row in occurrences]
    payload["evidencias.jsonl"] = lines(evidence)
    quality = json.loads(payload["quality_report.json"])
    quality["release_version"] = VERSION
    quality["validation"] = (
        "Correção de concentração da linha F03 194 após rejeição humana C-F03-003; "
        "aprovação do novo release pendente."
    )
    quality["corrections_applied"].append(
        {
            "occurrence_id": OCCURRENCE_ID,
            "source_id": "F03",
            "field": "strength",
            "before": OLD,
            "after": NEW,
        }
    )
    quality["limitations"][0] = "Aprovação de domínio deste novo release pendente."
    payload["quality_report.json"] = encoded(quality)
    manifest = {
        key: value
        for key, value in prior.items()
        if key not in {"approval_scope", "domain_review_reference"}
    }
    manifest["release_version"] = VERSION
    manifest["status"] = "pending_review"
    manifest["generated_at_utc"] = datetime.now(UTC).isoformat()
    manifest["source_release"] = {
        "version": prior["release_version"],
        "manifest_sha256": digest(original),
    }
    manifest["review_reference"] = {
        "path": "docs/reports/v7-retrieval-review.xlsx",
        "sha256": digest(REVIEW.read_bytes()),
        "scope": "Rejeição humana de C-F03-003; não equivale à aprovação do candidato v8.",
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
                "fingerprint": manifest["corpus_fingerprint"],
            }
        )
    )


if __name__ == "__main__":
    main()
