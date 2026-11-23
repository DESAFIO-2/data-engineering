"""Generate data/vocab/ingredients.json (variant -> canonical spelling) from the approved v9.

The output is a reviewable vocabulary (F8, ``ingredient_variants.csv``). It is derived
deterministically from the literal names in the frozen release; re-running it on the
same release produces the same file. Use ``--check`` to fail if the file is stale.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from rag.normalization import build_ingredient_map

ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT / "data/releases/corpus-consolidado-v9-aprovado-2026-11-12"
OUTPUT = ROOT / "data/vocab/ingredients.json"


def render(source: Path = SOURCE) -> bytes:
    rows = [
        json.loads(line)
        for line in (source / "occurrences.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    names = [(row["active_ingredient"], row["source"]["source_id"]) for row in rows]
    payload = {
        "schema_version": "vocab-ingredients-v1",
        "description": (
            "Grafia canônica de princípio ativo (preferência: grafia da RENAME/DCB em F01, "
            "depois acentuação). Gerado por scripts/build_v10_vocab.py a partir do release "
            "aprovado; revisão humana na F8 (ingredient_variants.csv)."
        ),
        "source_release": source.name,
        "mappings": build_ingredient_map(names),
    }
    return (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check", action="store_true", help="falha se o arquivo estiver desatualizado"
    )
    args = parser.parse_args()
    data = render()
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_bytes() != data:
            print(f"Vocabulário desatualizado: {OUTPUT.relative_to(ROOT)}", file=sys.stderr)
            return 1
        print("Vocabulário de princípios ativos atualizado.")
        return 0
    OUTPUT.write_bytes(data)
    mappings = json.loads(data)["mappings"]
    print(
        json.dumps(
            {"output": str(OUTPUT.relative_to(ROOT)), "mappings": len(mappings)}, ensure_ascii=False
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
