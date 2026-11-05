"""Entrada simples para os comandos do RAG no terminal."""

from __future__ import annotations

import sys
from importlib import import_module
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

if __name__ == "__main__":
    raise SystemExit(import_module("rag.cli").main())
