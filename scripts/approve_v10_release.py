"""Publish immutable approved v10 after explicit human review decision."""

from __future__ import annotations

import json
from datetime import date
from hashlib import sha256
from pathlib import Path
from typing import Any

from publish_consolidated_release import digest, encoded, lines, read_lines, verify

from rag.consolidated import (
    CHUNK_RECIPE_V3,
    ConsolidatedRelease,
    build_chunks,
    default_chunk_recipe,
)

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/releases/corpus-consolidado-v10-normalizada-2026-11-17"
VERSION = "corpus-consolidado-v10-aprovado-2026-11-17"
DESTINATION = ROOT / "data/releases" / VERSION
CHUNKS_DESTINATION = ROOT / "data/derived/chunks" / VERSION
REVIEW = ROOT / "docs/reports/v10/revisao-v10-normalizada-jhiovana.md"


def approve(
    expected_candidate_sha256: str,
    *,
    source: Path = SOURCE,
    destination: Path = DESTINATION,
    chunks_destination: Path = CHUNKS_DESTINATION,
    review_path: Path = REVIEW,
    version: str | None = None,
) -> dict[str, Any]:
    """Promote verified pending_review v10 candidate to immutable approved release + v3 chunks."""
    target_version = version or destination.name
    candidate_bytes = (source / "release.json").read_bytes()
    if digest(candidate_bytes) != expected_candidate_sha256:
        raise ValueError("Candidato v10 diferente do revisado")
    prior = verify(source)
    catalog_count = prior["files"]["catalog.jsonl"]["records"]
    if prior["status"] != "pending_review" or catalog_count < 1:
        raise ValueError("Candidato v10 inválido")
    review_text = review_path.read_text(encoding="utf-8")
    if "pode aprovar a revisao" not in review_text or expected_candidate_sha256 not in review_text:
        raise ValueError("Registro de aprovação humana incompleto")

    scope = (
        "Indexação e recuperação de presença documental de medicamentos, apresentações e insumos "
        "nas edições congeladas F01 (RENAME 2024), F03 (REME-DF 2026) e F04 "
        f"(Farmácia Popular 2026), com normalização aditiva, {catalog_count} apresentações "
        "e chunks one-evidence-v3."
    )

    files = {name: (source / name).read_bytes() for name in prior["files"]}
    evidence = read_lines(files["evidencias.jsonl"])
    for row in evidence:
        row["review_status"] = "approved"
    files["evidencias.jsonl"] = lines(evidence)

    quality = json.loads(files["quality_report.json"])
    quality["release_version"] = target_version
    if quality.get("limitations"):
        quality["limitations"][0] = (
            "Aprovação humana restrita à presença documental nas fontes F01/F03/F04 congeladas; "
            "desempenho da recuperação permanece sujeito ao gate de avaliação."
        )
    files["quality_report.json"] = encoded(quality)

    review_hash = digest(review_path.read_bytes())
    review_rel = (
        str(review_path.relative_to(ROOT)) if review_path.is_relative_to(ROOT) else review_path.name
    )
    domain_review = {
        "decision": "approved",
        "date": date.today().isoformat(),
        "reviewer": "Jhiovana",
        "reviewer_role": "responsável pelo projeto",
        "reviewer_function": "engenharia de dados",
        "scope": scope,
        "limitations": quality.get("limitations", []),
        "clinical_credentials_verified": False,
        "source_release_version": prior["release_version"],
        "source_release_manifest_sha256": digest(candidate_bytes),
        "review_reference_sha256": review_hash,
        "release_version": target_version,
        "evidence_sha256": digest(files["evidencias.jsonl"]),
    }
    files["domain_review.json"] = encoded(domain_review)

    manifest: dict[str, Any] = {
        **prior,
        "release_version": target_version,
        "status": "approved",
        "approval_scope": scope,
        "domain_review_reference": "domain_review.json",
        "source_release": {
            "version": prior["release_version"],
            "manifest_sha256": digest(candidate_bytes),
        },
        "review_reference": {
            "path": review_rel,
            "sha256": review_hash,
            "scope": (
                "Aprovação humana da normalização aditiva, vocabulários, reconciliação de "
                "catálogo e correções de parser F01; gate RAG separado."
            ),
        },
    }
    fp_inputs = files["catalog.jsonl"] + files["occurrences.jsonl"] + files["evidencias.jsonl"]
    if "normalization.json" in files:
        fp_inputs += files["normalization.json"]
    manifest["corpus_fingerprint"] = sha256(fp_inputs).hexdigest()
    manifest["files"] = {
        name: {
            "sha256": digest(data),
            "bytes": len(data),
            **({"records": len(read_lines(data))} if name.endswith(".jsonl") else {}),
        }
        for name, data in files.items()
    }
    destination.mkdir(exist_ok=False)
    for name, data in files.items():
        (destination / name).write_bytes(data)
    (destination / "release.json").write_bytes(encoded(manifest))
    verify(destination)
    release = ConsolidatedRelease.load(destination)
    recipe = default_chunk_recipe(release)
    build_chunks(release, chunks_destination, recipe=recipe)
    assert recipe == CHUNK_RECIPE_V3 or "normalization.json" not in files
    return manifest


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-sha256", required=True)
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--destination", type=Path, default=DESTINATION)
    parser.add_argument("--chunks-destination", type=Path, default=CHUNKS_DESTINATION)
    parser.add_argument("--review", type=Path, default=REVIEW)
    args = parser.parse_args()
    result = approve(
        args.candidate_sha256,
        source=args.source,
        destination=args.destination,
        chunks_destination=args.chunks_destination,
        review_path=args.review,
    )
    print(
        json.dumps(
            {"release": result["release_version"], "fingerprint": result["corpus_fingerprint"]}
        )
    )
