"""Publish an immutable approved v7 package from the reviewed pending candidate."""

from __future__ import annotations

import json
from datetime import date
from hashlib import sha256
from pathlib import Path

from publish_consolidated_release import digest, encoded, lines, read_lines, verify

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/releases/corpus-consolidado-v7-codigos-corrigidos-2026-11-11"
VERSION = "corpus-consolidado-v7-aprovado-2026-11-11"
DESTINATION = ROOT / "data/releases" / VERSION
EXPECTED_FINGERPRINT = "6140447dc4ccc34f933199a9463e9d9634753eaf6714bc13df76f6b4d34eb066"
SCOPE = (
    "Indexação e recuperação de presença documental de medicamentos, apresentações e insumos "
    "nas edições congeladas F01 (RENAME 2024), F03 (REME-DF 2026) e F04 "
    "(Farmácia Popular 2026), com proveniência e limites da fonte."
)


def approve() -> dict:
    prior = verify(SOURCE)
    if prior["status"] != "pending_review" or prior["corpus_fingerprint"] != EXPECTED_FINGERPRINT:
        raise ValueError("Candidato v7 diferente do aprovado pela usuária")
    files = {name: (SOURCE / name).read_bytes() for name in prior["files"]}
    evidence = read_lines(files["evidencias.jsonl"])
    for row in evidence:
        row["review_status"] = "approved"
    files["evidencias.jsonl"] = lines(evidence)
    quality = json.loads(files["quality_report.json"])
    quality["release_version"] = VERSION
    quality["limitations"][0] = (
        "Aprovação de Jhiovana restrita à indexação e recuperação de presença documental "
        "nas fontes F01/F03/F04 congeladas."
    )
    files["quality_report.json"] = encoded(quality)
    limitations = quality["limitations"]
    review = {
        "decision": "approved",
        "date": date(2026, 11, 11).isoformat(),
        "reviewer": "Jhiovana",
        "reviewer_role": "responsável pelo projeto",
        "reviewer_function": "engenharia de dados",
        "authorization": (
            "Instrução explícita da usuária nesta conversa: "
            "'certo, então eu aprovo. Fecho o gate da v7. pode registrar pra mim no "
            "documento de revisão [revisao-v6-jhiovana.md] ... e pode iniciar a proxima etapada.'"
        ),
        "scope": SCOPE,
        "limitations": limitations,
        "clinical_credentials_verified": False,
        "source_release_version": prior["release_version"],
        "source_release_manifest_sha256": digest((SOURCE / "release.json").read_bytes()),
        "release_version": VERSION,
        "evidence_sha256": digest(files["evidencias.jsonl"]),
    }
    files["domain_review.json"] = encoded(review)
    manifest = {
        **prior,
        "release_version": VERSION,
        "status": "approved",
        "approval_scope": SCOPE,
        "domain_review_reference": "domain_review.json",
        "source_release": {
            "version": prior["release_version"],
            "manifest_sha256": review["source_release_manifest_sha256"],
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
