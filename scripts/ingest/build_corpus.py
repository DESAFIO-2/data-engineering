"""Build the isolated experimental corpus: python -m scripts.build_corpus."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from rag.corpus import build_corpus  # noqa: E402


def main() -> None:
    report = build_corpus(ROOT)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
