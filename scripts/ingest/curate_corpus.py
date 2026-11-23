"""Export pending reviews or publish explicitly approved evidence."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from rag.curation import export_review, publish  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    export = commands.add_parser("export")
    export.add_argument("--corpus", type=Path, required=True)
    export.add_argument("--supplement", type=Path)
    export.add_argument("--output", type=Path, required=True)
    release = commands.add_parser("publish")
    release.add_argument("--review", type=Path, required=True)
    release.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "export":
            review = export_review(args.corpus, args.supplement, args.output)
            print(f"{len(review['entries'])} evidências pendentes; nenhuma aprovação criada.")
        else:
            print(publish(args.review, args.output))
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.exit(1, f"Curadoria recusada: {exc}\n")


if __name__ == "__main__":
    main()
