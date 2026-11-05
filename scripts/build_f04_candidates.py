"""Gera candidatos do elenco F04 sem promover linhas não revisadas ao RAG."""

from __future__ import annotations

import json
import re
from hashlib import sha256
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data/manifests/coleta-inicial-pdfs-2026-11-03.json"
OUTPUT = ROOT / "data/curation/f04_catalogo_candidatos.jsonl"


def main() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    source = next(row for row in manifest["sources"] if row["source_id"] == "F04")
    silver = ROOT / "data/silver/F04" / f"{source['sha256']}.jsonl"
    page = json.loads(silver.read_text(encoding="utf-8").splitlines()[0])
    if page["content_sha256"] != source["sha256"] or page["page"] != 1:
        raise ValueError("F04 Silver não corresponde ao manifesto")
    raw = ROOT / "data" / source["path"]
    if sha256(raw.read_bytes()).hexdigest() != source["sha256"]:
        raise ValueError("PDF F04 não corresponde ao manifesto")

    rows = []
    for line in page["text"].splitlines():
        line = " ".join(line.split())
        if not re.search(r"\d\s*(?:mg|mcg|ui/ml)", line, re.IGNORECASE):
            continue
        # O PDF não fornece forma farmacêutica de modo confiável para todas as linhas.
        # Guardamos a linha integral; o revisor confirmará apresentação e notas em F01/F03.
        candidate_id = "f04-" + sha256(line.casefold().encode()).hexdigest()[:16]
        rows.append(
            {
                "candidate_id": candidate_id,
                "source_id": "F04",
                "source_version": "Farmácia Popular 31/08/2026",
                "source_sha256": source["sha256"],
                "source_url": source["source_url"],
                "page": 1,
                "raw_line": line,
                "review_status": "pending",
                "form": None,
                "notes": (
                    "Linha extraída; forma, identidade e cruzamento entre listas "
                    "ainda não revisados."
                ),
            }
        )
    if len(rows) != 39 or len({r["candidate_id"] for r in rows}) != 39:
        raise ValueError(f"F04 esperado: 39 linhas únicas; encontrado: {len(rows)}")
    OUTPUT.write_text(
        "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows),
        encoding="utf-8",
    )
    print(f"{len(rows)} candidatos F04 em {OUTPUT}")


if __name__ == "__main__":
    main()
