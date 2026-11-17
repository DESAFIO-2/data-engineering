"""Configuração local e padrões canônicos do RAG SUS Cidadão."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

DEFAULT_CHAT_MODEL = "gemini-3.5-flash"
DEFAULT_EMBEDDING_MODEL = "models/gemini-embedding-2"
DEFAULT_RELEASE_DIR = "data/releases/corpus-consolidado-v5-aprovado-2026-11-10"
DEFAULT_VECTOR_DIR = "data/vectorstore/chroma"
DEFAULT_TOP_K = 5


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
    google_api_key_fallback_1: str = ""
    google_api_key_fallback_2: str = ""

    @property
    def google_api_keys(self) -> tuple[str, ...]:
        """Return unique non-empty API keys in priority order (primary, then fallbacks)."""
        keys: list[str] = []
        for raw in (
            self.google_api_key,
            self.google_api_key_fallback_1,
            self.google_api_key_fallback_2,
        ):
            cleaned = raw.strip()
            if cleaned and cleaned not in keys:
                keys.append(cleaned)
        return tuple(keys)

    @property
    def has_google_api_key(self) -> bool:
        """Return True when at least one primary or fallback API key is configured."""
        return bool(self.google_api_keys)


def get_settings() -> Settings:
    env = _env()
    return Settings(
        google_api_key=env.get("APP_GOOGLE_API_KEY", ""),
        rag_chat_model=env.get("APP_RAG_CHAT_MODEL", DEFAULT_CHAT_MODEL),
        rag_embedding_model=env.get("APP_RAG_EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL),
        rag_release_dir=Path(env.get("APP_RAG_RELEASE_DIR", DEFAULT_RELEASE_DIR)),
        rag_vector_dir=Path(env.get("APP_RAG_VECTOR_DIR", DEFAULT_VECTOR_DIR)),
        rag_top_k=int(env.get("APP_RAG_TOP_K", str(DEFAULT_TOP_K))),
        google_api_key_fallback_1=env.get("APP_GOOGLE_API_KEY_FALLBACK_1", ""),
        google_api_key_fallback_2=env.get("APP_GOOGLE_API_KEY_FALLBACK_2", ""),
    )
