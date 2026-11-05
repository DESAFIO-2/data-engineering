"""Configuração local do protótipo RAG."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _env() -> dict[str, str]:
    values: dict[str, str] = {}
    path = ROOT / ".env"
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                key, value = line.split("=", 1)
                values[key.strip()] = value.strip().strip('"').strip("'")
    return values | dict(os.environ)


@dataclass(frozen=True)
class Settings:
    google_api_key: str
    rag_chat_model: str
    rag_embedding_model: str
    rag_release_dir: Path
    rag_vector_dir: Path
    rag_top_k: int


def get_settings() -> Settings:
    env = _env()
    return Settings(
        google_api_key=env.get("APP_GOOGLE_API_KEY", ""),
        rag_chat_model=env.get("APP_RAG_CHAT_MODEL", "gemini-2.5-flash"),
        rag_embedding_model=env.get("APP_RAG_EMBEDDING_MODEL", "models/gemini-embedding-001"),
        rag_release_dir=Path(
            env.get("APP_RAG_RELEASE_DIR", "data/releases/rag-lote-1-aprovado-2026-11-05")
        ),
        rag_vector_dir=Path(env.get("APP_RAG_VECTOR_DIR", "data/vectorstore/chroma")),
        rag_top_k=int(env.get("APP_RAG_TOP_K", "5")),
    )
