"""Create an immutable, scope-limited approved release from a verified review package."""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from scripts.ingest.publish_consolidated_release import ROOT, digest, encoded, lines, read_lines, verify

SOURCE = ROOT / "data/releases/corpus-consolidado-v4-revisao-2026-11-10"
DEST = ROOT / "data/releases/corpus-consolidado-v5-aprovado-2026-11-10"


def approve(source: Path = SOURCE, destination: Path = DEST) -> dict:
    prior = verify(source)
    if prior["status"] != "pending_review":
        raise ValueError("O pacote de origem precisa estar em revisão")
    files = {name: (source / name).read_bytes() for name in prior["files"]}
    evidence = read_lines(files["evidencias.jsonl"])
    for row in evidence:
        row["review_status"] = "approved"
    files["evidencias.jsonl"] = lines(evidence)
    quality = json.loads(files["quality_report.json"])
    quality["limitations"] = [
        "Aprovação do responsável pelo projeto restrita à recuperação de presença nas listas F01/F03/F04.",
        "Não comprova estoque, elegibilidade, dispensação por unidade, indicação clínica individual ou equivalência terapêutica.",
        "Chunks antigos e 108 chunks complementares não incluídos.",
        "A linha 987 da F03 está somente no registro de exclusões.",
    ]
    files["quality_report.json"] = encoded(quality)
    review = {
        "decision": "approved",
        "date": date(2026, 11, 10).isoformat(),
        "reviewer": "usuário responsável pelo projeto (identidade civil não informada)",
        "reviewer_role": "responsável pelo projeto",
        "authorization": "Instrução explícita do usuário nesta conversa: 'ent pode aceitar do dominio .'",
        "scope": "Consulta de presença de apresentações e insumos nas edições F01, F03 e F04, com proveniência e evidência literal.",
        "limitations": quality["limitations"],
        "clinical_credentials_verified": False,
        "source_release_version": prior["release_version"],
        "source_release_manifest_sha256": digest((source / "release.json").read_bytes()),
        "release_version": destination.name,
        "evidence_sha256": digest(files["evidencias.jsonl"]),
    }
    files["domain_review.json"] = encoded(review)
    manifest = {**prior,
        "release_version": destination.name,
        "status": "approved",
        "approval_scope": review["scope"],
        "domain_review_reference": "domain_review.json",
        "source_release": {
            "version": prior["release_version"],
            "manifest_sha256": review["source_release_manifest_sha256"],
        },
        "files": {
            name: {
                "sha256": digest(data), "bytes": len(data),
                **({"records": len(read_lines(data))} if name.endswith(".jsonl") else {}),
            }
            for name, data in files.items()
        },
    }
    destination.mkdir(parents=False, exist_ok=False)
    for name, data in files.items():
        (destination / name).write_bytes(data)
    (destination / "release.json").write_bytes(encoded(manifest))
    verify(destination)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--output", type=Path, default=DEST)
    args = parser.parse_args()
    result = approve(args.source, args.output)
    print(json.dumps({"release_version": result["release_version"], "status": result["status"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
