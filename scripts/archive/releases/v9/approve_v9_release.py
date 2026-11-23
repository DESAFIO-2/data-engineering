"""Publish immutable approved v9 after the explicit clarithromycin decision."""

from __future__ import annotations

import json
from datetime import date
from hashlib import sha256
from pathlib import Path

from scripts.ingest.publish_consolidated_release import digest, encoded, lines, read_lines, verify

ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT / "data/releases/corpus-consolidado-v9-claritromicina-normalizada-2026-11-12"
VERSION = "corpus-consolidado-v9-aprovado-2026-11-12"
DESTINATION = ROOT / "data/releases" / VERSION
REVIEW = ROOT / "docs/reports/v9/revisao-claritromicina-v9-jhiovana.md"
EXPECTED_CANDIDATE_SHA256 = "60e8218b7968103940894ed513b062f988b085b0e7b01bcdd65a464442f34614"
SCOPE = (
    "Indexação e recuperação de presença documental de medicamentos, apresentações e insumos "
    "nas edições congeladas F01 (RENAME 2024), F03 (REME-DF 2026) e F04 "
    "(Farmácia Popular 2026), com proveniência e limites da fonte."
)


def approve() -> dict:
    candidate_bytes = (SOURCE / "release.json").read_bytes()
    if digest(candidate_bytes) != EXPECTED_CANDIDATE_SHA256:
        raise ValueError("Candidato v9 diferente do revisado")
    prior = verify(SOURCE)
    if prior["status"] != "pending_review" or prior["files"]["catalog.jsonl"]["records"] != 1859:
        raise ValueError("Candidato v9 inválido")
    review_text = REVIEW.read_text(encoding="utf-8")
    if (
        "pode aprovar a revisao" not in review_text
        or EXPECTED_CANDIDATE_SHA256 not in review_text
        or "12/11/2026" not in review_text
    ):
        raise ValueError("Registro de aprovação humana incompleto")
    files = {name: (SOURCE / name).read_bytes() for name in prior["files"]}
    evidence = read_lines(files["evidencias.jsonl"])
    for row in evidence:
        row["review_status"] = "approved"
    files["evidencias.jsonl"] = lines(evidence)
    quality = json.loads(files["quality_report.json"])
    quality["release_version"] = VERSION
    quality["validation"] = (
        "Claritromicina 500mg/500 mg reconciliada nas linhas F03 247–249 e aprovada "
        "por Jhiovana em 12/11/2026; 78 pares normalizados restantes fora desta decisão."
    )
    quality["limitations"][0] = (
        "Aprovação de Jhiovana restrita à presença documental nas fontes F01/F03/F04 "
        "congeladas; desempenho da recuperação não aprovado."
    )
    files["quality_report.json"] = encoded(quality)
    review_hash = digest(REVIEW.read_bytes())
    domain_review = {
        "decision": "approved",
        "date": date(2026, 11, 12).isoformat(),
        "reviewer": "Jhiovana",
        "reviewer_role": "responsável pelo projeto",
        "reviewer_function": "engenharia de dados",
        "authorization": (
            "Instrução explícita da usuária nesta conversa: 'pode aprovar a revisao', "
            "após a apresentação do candidato v9 de claritromicina."
        ),
        "scope": SCOPE,
        "limitations": quality["limitations"],
        "clinical_credentials_verified": False,
        "source_release_version": prior["release_version"],
        "source_release_manifest_sha256": digest(candidate_bytes),
        "review_reference_sha256": review_hash,
        "release_version": VERSION,
        "evidence_sha256": digest(files["evidencias.jsonl"]),
    }
    files["domain_review.json"] = encoded(domain_review)
    manifest = {
        **prior,
        "release_version": VERSION,
        "status": "approved",
        "approval_scope": SCOPE,
        "domain_review_reference": "domain_review.json",
        "source_release": {
            "version": prior["release_version"],
            "manifest_sha256": digest(candidate_bytes),
        },
        "review_reference": {
            "path": "docs/reports/v9/revisao-claritromicina-v9-jhiovana.md",
            "sha256": review_hash,
            "scope": "Aprovação humana da normalização da linha F03 249; gate RAG separado.",
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
