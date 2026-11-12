"""Publish a pending v9 candidate merging the documented clarithromycin presentation."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path

from publish_consolidated_release import digest, encoded, evidence_for, lines, read_lines, verify

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/releases/corpus-consolidado-v8-aprovado-2026-11-11"
VERSION = "corpus-consolidado-v9-claritromicina-normalizada-2026-11-12"
DESTINATION = ROOT / "data/releases" / VERSION
SOURCE_MANIFEST_SHA256 = "d634a75817ff3d16031c45fa664b9075ec426c1b3482581c0ca93f490906cba7"
OCCURRENCE_ID = "occ-83202f34ce2ffbeed05ea49d"
OLD_MEDICINE_ID = "med-018ed18f2ec7fd073407f4e4"
CANONICAL_MEDICINE_ID = "med-3801ddc7d957468e0916fed0"


def build() -> tuple[dict[str, bytes], dict]:
    original = (SOURCE / "release.json").read_bytes()
    if digest(original) != SOURCE_MANIFEST_SHA256:
        raise ValueError("Manifesto v8 diferente do auditado")
    prior = verify(SOURCE)
    payload = {
        name: (SOURCE / name).read_bytes()
        for name in prior["files"]
        if name != "domain_review.json"
    }
    occurrences = read_lines(payload["occurrences.jsonl"])
    matches = [row for row in occurrences if row["occurrence_id"] == OCCURRENCE_ID]
    if len(matches) != 1:
        raise ValueError("Linha 249 F03 ausente ou duplicada")
    item = matches[0]
    if (
        item["source"]["source_id"] != "F03"
        or item["source"]["page"] != 22
        or item["source_row_number"] != 249
        or item["source_code"] != "MSE8831"
        or item["active_ingredient"] != "claritromicina"
        or item["strength"] != "500mg"
        or item["form"] != "comprimido"
        or item["medicine_id"] != OLD_MEDICINE_ID
        or "claritromicina comprimido 500mg" not in item["raw_text"]
    ):
        raise ValueError("Linha 249 F03 diferente da fonte auditada")
    item["strength"] = "500 mg"
    item["medicine_id"] = CANONICAL_MEDICINE_ID
    catalog = read_lines(payload["catalog.jsonl"])
    old = [row for row in catalog if row["medicine_id"] == OLD_MEDICINE_ID]
    canonical = [row for row in catalog if row["medicine_id"] == CANONICAL_MEDICINE_ID]
    if (
        len(old) != 1
        or len(canonical) != 1
        or old[0]["occurrence_ids"] != [OCCURRENCE_ID]
        or canonical[0]["active_ingredient"] != "claritromicina"
        or canonical[0]["strength"] != "500 mg"
        or canonical[0]["form"] != "comprimido"
        or OCCURRENCE_ID in canonical[0]["occurrence_ids"]
    ):
        raise ValueError("Entradas de catálogo da claritromicina divergentes")
    canonical[0]["occurrence_ids"].append(OCCURRENCE_ID)
    catalog = [row for row in catalog if row["medicine_id"] != OLD_MEDICINE_ID]
    audit = read_lines(payload["audit_log.jsonl"])
    audited = [row for row in audit if row["occurrence_id"] == OCCURRENCE_ID]
    if len(audited) != 1 or audited[0]["fields_verified"]["strength"] != "500mg":
        raise ValueError("Log de auditoria da linha 249 divergente")
    audited[0]["fields_verified"]["strength"] = "500 mg"
    audited[0]["verification_result"] = "normalized_unit_spacing_after_v8_retrieval_audit"
    audited[0]["notes_and_limitations"] = (
        "A fonte F03 p. 22, linha 249, escreve '500mg'. Espaço antes de mg normalizado "
        "para a mesma apresentação das linhas 247–248 (p. 21); códigos e canais "
        "mantidos por ocorrência. Aprovação de domínio do novo release pendente."
    )
    payload["catalog.jsonl"] = lines(catalog)
    payload["occurrences.jsonl"] = lines(occurrences)
    payload["audit_log.jsonl"] = lines(audit)
    descriptions = json.loads(payload["f03_descriptions.json"])
    payload["evidencias.jsonl"] = lines([evidence_for(row, descriptions) for row in occurrences])
    quality = json.loads(payload["quality_report.json"])
    quality["release_version"] = VERSION
    quality["catalog_presentations"] = len(catalog)
    quality["exact_presentations_supported"] = sum(
        row["exact_presentation_supported"] for row in catalog
    )
    quality["validation"] = (
        "Claritromicina 500mg/500 mg reconciliada nas linhas F03 247–249; "
        "79 pares de identidade normalizada identificados no catálogo v8, "
        "somente este par corrigido. Aprovação do novo release pendente."
    )
    quality["corrections_applied"].append(
        {
            "occurrence_id": OCCURRENCE_ID,
            "source_id": "F03",
            "field": "strength, medicine_id",
            "before": "500mg; " + OLD_MEDICINE_ID,
            "after": "500 mg; " + CANONICAL_MEDICINE_ID,
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
        "path": "docs/reports/v8/validacao-recuperacao-v8-test.md",
        "sha256": digest((ROOT / "docs/reports/v8/validacao-recuperacao-v8-test.md").read_bytes()),
        "scope": "Diagnóstico pós-teste; não equivale à revisão humana nem a novo gate.",
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
                "catalog_presentations": manifest["files"]["catalog.jsonl"]["records"],
            }
        )
    )


if __name__ == "__main__":
    main()
