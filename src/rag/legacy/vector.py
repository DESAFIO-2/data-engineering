"""Índice Chroma persistente, isolado por release e modelo de embeddings."""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from typing import Any

from rag.legacy.release import Release


def index_location(base: Path, release: Release, embedding_model: str) -> Path:
    key = sha256(f"{release.fingerprint}|{embedding_model}".encode()).hexdigest()[:16]
    return base.expanduser().resolve() / key


def _vectorstore(location: Path, embeddings: Any) -> Any:
    from langchain_chroma import Chroma

    return Chroma(
        collection_name="sus_cidadao_evidencias",
        embedding_function=embeddings,
        persist_directory=str(location),
    )


def build_index(release: Release, base: Path, embedding_model: str, embeddings: Any) -> Path:
    from langchain_core.documents import Document

    location = index_location(base, release, embedding_model)
    marker = location / "index.json"
    expected = {
        "release_version": release.manifest["release_version"],
        "release_fingerprint": release.fingerprint,
        "embedding_model": embedding_model,
        "evidence_count": len(release.evidence),
    }
    if marker.exists():
        if json.loads(marker.read_text(encoding="utf-8")) != expected:
            raise ValueError("Índice existente pertence a outro release ou modelo")
        store = _vectorstore(location, embeddings)
        indexed = store.get(ids=[e["evidence_id"] for e in release.evidence])["ids"]
        if len(indexed) != len(release.evidence):
            raise ValueError("Índice Chroma incompleto; remova somente esta pasta e reindexe")
        return location
    location.mkdir(parents=True, exist_ok=True)
    store = _vectorstore(location, embeddings)
    documents = [
        Document(
            page_content=e["text"],
            metadata={
                "evidence_id": e["evidence_id"],
                "medicine_id": e["medicine_id"],
                "source_id": e["source"]["source_id"],
                "page": e["source"]["page"],
                "source_url": e["source"]["url"],
                "source_version": e["source"]["version"],
                "topic": e["topic"],
                "territory": e["territory"],
            },
        )
        for e in release.evidence
    ]
    store.add_documents(documents, ids=[e["evidence_id"] for e in release.evidence])
    indexed = store.get(ids=[e["evidence_id"] for e in release.evidence])["ids"]
    if len(indexed) != len(release.evidence):
        raise ValueError("Indexação incompleta; marcador não foi publicado")
    temporary = marker.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(expected, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    temporary.replace(marker)
    return location


def open_index(release: Release, base: Path, embedding_model: str, embeddings: Any) -> Any:
    location = index_location(base, release, embedding_model)
    marker = location / "index.json"
    if not marker.exists():
        raise FileNotFoundError("Índice ausente. Execute: uv run python app.py index")
    expected = json.loads(marker.read_text(encoding="utf-8"))
    if (
        expected.get("release_fingerprint") != release.fingerprint
        or expected.get("embedding_model") != embedding_model
        or expected.get("evidence_count") != len(release.evidence)
    ):
        raise ValueError("Índice incompatível com o release aprovado")
    store = _vectorstore(location, embeddings)
    indexed = store.get(ids=[e["evidence_id"] for e in release.evidence])["ids"]
    if len(indexed) != len(release.evidence):
        raise ValueError("Índice Chroma incompleto; execute novamente o comando index")
    return store
