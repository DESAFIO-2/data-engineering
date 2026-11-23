"""Publish the approved v8 package after Jhiovana's explicit calcium correction review."""

from __future__ import annotations

import json
from datetime import date
from hashlib import sha256
from pathlib import Path

from scripts.ingest.publish_consolidated_release import digest, encoded, lines, read_lines, verify
from scripts.archive.releases.v8.validate_v8_calcium_review import V8_REVIEW, validate

ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT / "data/releases/corpus-consolidado-v8-calcio-corrigido-2026-11-11"
VERSION = "corpus-consolidado-v8-aprovado-2026-11-11"
DESTINATION = ROOT / "data/releases" / VERSION
EXPECTED_CANDIDATE_SHA256 = "8cd04703e8e6f7d9048004a40f66075465a9ecd23efeae3d481371aa362049f4"
SCOPE = (
    "Indexação e recuperação de presença documental de medicamentos, apresentações e insumos "
    "nas edições congeladas F01 (RENAME 2024), F03 (REME-DF 2026) e F04 "
    "(Farmácia Popular 2026), com proveniência e limites da fonte."
)


def approve() -> dict:
    raw_manifest = (SOURCE / "release.json").read_bytes()
    if digest(raw_manifest) != EXPECTED_CANDIDATE_SHA256:
        raise ValueError("Candidato v8 diferente do revisado")
    prior = verify(SOURCE)
    if prior["status"] != "pending_review":
        raise ValueError("Candidato v8 não está pendente")
    review = validate(V8_REVIEW)
    if review["errors"] or review["prior_approved_carried"] != 118:
        raise ValueError("Revisão humana da correção incompleta")
    files = {name: (SOURCE / name).read_bytes() for name in prior["files"]}
    evidence = read_lines(files["evidencias.jsonl"])
    for row in evidence:
        row["review_status"] = "approved"
    files["evidencias.jsonl"] = lines(evidence)
    quality = json.loads(files["quality_report.json"])
    quality["release_version"] = VERSION
    quality["validation"] = (
        "Linha F03 194 corrigida conforme PDF e aprovada por Jhiovana em 11/11/2026; "
        "escopo restrito à presença documental."
    )
    quality["limitations"][0] = (
        "Aprovação de Jhiovana restrita à indexação e recuperação de presença documental "
        "nas fontes F01/F03/F04 congeladas."
    )
    files["quality_report.json"] = encoded(quality)
    decision = {
        "decision": "approved",
        "date": date(2026, 11, 11).isoformat(),
        "reviewer": "Jhiovana",
        "reviewer_role": "responsável pelo projeto",
        "reviewer_function": "engenharia de dados",
        "authorization": (
            "Instrução explícita da usuária nesta conversa após conferir o PDF REME: "
            "'pode aprovar no meu nome. acabei de conferir e está de acordo com o pdf reme'"
        ),
        "scope": SCOPE,
        "limitations": quality["limitations"],
        "clinical_credentials_verified": False,
        "source_release_version": prior["release_version"],
        "source_release_manifest_sha256": digest(raw_manifest),
        "prior_review_sha256": review["prior_review_sha256"],
        "correction_review_sha256": review["correction_review_sha256"],
        "release_version": VERSION,
        "evidence_sha256": digest(files["evidencias.jsonl"]),
    }
    files["domain_review.json"] = encoded(decision)
    manifest = {
        **prior,
        "release_version": VERSION,
        "status": "approved",
        "approval_scope": SCOPE,
        "domain_review_reference": "domain_review.json",
        "source_release": {
            "version": prior["release_version"],
            "manifest_sha256": digest(raw_manifest),
        },
        "review_reference": {
            "path": "docs/reports/v8/v8-calcium-correction-review.xlsx",
            "sha256": review["correction_review_sha256"],
            "scope": (
                "118 decisões v7 herdadas por identidade; aprovação humana da correção C-F03-003."
            ),
        },
    }
    manifest["corpus_fingerprint"] = sha256(
        files["catalog.jsonl"] + files["occurrences.jsonl"] + files["evidencias.jsonl"]
    ).hexdigest()
    manifest["files"] = {
        name: {
            "sha256": digest(data),
            "bytes": len(data),
            **({"records": len(read_lines(data))} if name.endswith(".jsonl") else {}),
        }
        for name, data in files.items()
    }
    DESTINATION.mkdir(exist_ok=False)
    for name, data in files.items():
        (DESTINATION / name).write_bytes(data)
    (DESTINATION / "release.json").write_bytes(encoded(manifest))
    verify(DESTINATION)
    return manifest


if __name__ == "__main__":
    result = approve()
    print(json.dumps({"release": VERSION, "fingerprint": result["corpus_fingerprint"]}))
