"""Publish immutable approved v10 after explicit human review decision."""

from __future__ import annotations

import json
from datetime import date
from hashlib import sha256
from pathlib import Path
from typing import Any

from publish_consolidated_release import digest, encoded, lines, read_lines, verify

from rag.consolidated import CHUNK_RECIPE_V2, ConsolidatedRelease, build_chunks

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/releases/corpus-consolidado-v10-reconciliada-2026-11-16"
VERSION = "corpus-consolidado-v10-aprovado-2026-11-16"
DESTINATION = ROOT / "data/releases" / VERSION
CHUNKS_DESTINATION = ROOT / "data/derived/chunks" / VERSION
REVIEW = ROOT / "docs/reports/v10/revisao-reconciliacao-v10-jhiovana.md"
SCOPE = (
    "Indexação e recuperação de presença documental de medicamentos, apresentações e insumos "
    "nas edições congeladas F01 (RENAME 2024), F03 (REME-DF 2026) e F04 "
    "(Farmácia Popular 2026), com catálogo deduplicado para 1.779 apresentações e chunks v2."
)


def approve(expected_candidate_sha256: str) -> dict[str, Any]:
    """Promote verified pending_review v10 candidate to immutable approved release + v2 chunks."""
    candidate_bytes = (SOURCE / "release.json").read_bytes()
    if digest(candidate_bytes) != expected_candidate_sha256:
        raise ValueError("Candidato v10 diferente do revisado")
    prior = verify(SOURCE)
    if prior["status"] != "pending_review" or prior["files"]["catalog.jsonl"]["records"] != 1779:
        raise ValueError("Candidato v10 inválido")
    review_text = REVIEW.read_text(encoding="utf-8")
    if "pode aprovar a revisao" not in review_text or expected_candidate_sha256 not in review_text:
        raise ValueError("Registro de aprovação humana incompleto")

    files = {name: (SOURCE / name).read_bytes() for name in prior["files"]}
    evidence = read_lines(files["evidencias.jsonl"])
    for row in evidence:
        row["review_status"] = "approved"
    files["evidencias.jsonl"] = lines(evidence)

    quality = json.loads(files["quality_report.json"])
    quality["release_version"] = VERSION
    quality["limitations"][0] = (
        "Aprovação humana restrita à presença documental nas fontes F01/F03/F04 congeladas; "
        "desempenho da recuperação permanece sujeito ao gate de avaliação."
    )
    files["quality_report.json"] = encoded(quality)

    review_hash = digest(REVIEW.read_bytes())
    domain_review = {
        "decision": "approved",
        "date": date.today().isoformat(),
        "reviewer": "Jhiovana",
        "reviewer_role": "responsável pelo projeto",
        "reviewer_function": "engenharia de dados",
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

    manifest: dict[str, Any] = {
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
            "path": "docs/reports/v10/revisao-reconciliacao-v10-jhiovana.md",
            "sha256": review_hash,
            "scope": (
                "Aprovação humana da reconciliação dos 80 pares de colisão; gate RAG separado."
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
    release = ConsolidatedRelease.load(DESTINATION)
    build_chunks(release, CHUNKS_DESTINATION, recipe=CHUNK_RECIPE_V2)
    return manifest


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-sha256", required=True)
    args = parser.parse_args()
    result = approve(args.candidate_sha256)
    print(json.dumps({"release": VERSION, "fingerprint": result["corpus_fingerprint"]}))
