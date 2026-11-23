"""Construção retomável, validação e ranqueamento no índice vetorial ChromaDB."""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

from .release import ConsolidatedRelease, digest, json_bytes


def index_location(
    base: Path, release: ConsolidatedRelease, chunk_manifest: dict[str, Any], model: str
) -> Path:
    key = digest(
        f"{release.fingerprint}|{chunk_manifest['files']['chunks.jsonl']['sha256']}|{model}|langchain_google_genai.embed_documents".encode()
    )[:24]
    return base / "consolidated" / key


def _store(location: Path, embeddings: Any) -> Any:
    from langchain_chroma import Chroma

    return Chroma(
        collection_name="sus_cidadao_consolidado",
        embedding_function=embeddings,
        persist_directory=str(location),
    )


def build_index(
    release: ConsolidatedRelease,
    chunks: list[dict[str, Any]],
    chunk_manifest: dict[str, Any],
    base: Path,
    model: str,
    embeddings: Any,
    batch_size: int = 32,
    requests_per_minute: int = 80,
) -> Path:
    from langchain_core.documents import Document

    if not 1 <= batch_size <= 128:
        raise ValueError("batch_size inválido")
    if not 1 <= requests_per_minute <= 1000:
        raise ValueError("requests_per_minute inválido")
    location = index_location(base, release, chunk_manifest, model)
    location.mkdir(parents=True, exist_ok=True)
    marker = location / "index.json"
    expected_marker = {
        "release_fingerprint": release.fingerprint,
        "chunks_sha256": chunk_manifest["files"]["chunks.jsonl"]["sha256"],
        "embedding_model": model,
        "embedding_api": "langchain_google_genai.embed_documents",
        "count": len(chunks),
    }
    if marker.exists() and any(
        json.loads(marker.read_bytes()).get(k) != v for k, v in expected_marker.items()
    ):
        raise ValueError("Índice existente incompatível")
    store = _store(location, embeddings)
    current = store.get(include=["documents"])
    expected = {c["chunk_id"]: c["text"] for c in chunks}
    if any(
        cid not in expected or text != expected[cid]
        for cid, text in zip(current["ids"], current["documents"], strict=True)
    ):
        raise ValueError("Índice contém IDs ou textos divergentes")
    present = set(current["ids"])
    pending = [c for c in chunks if c["chunk_id"] not in present]
    for start in range(0, len(pending), batch_size):
        batch_started = time.monotonic()
        batch = pending[start : start + batch_size]
        docs = [
            Document(
                page_content=c["text"],
                metadata={
                    "chunk_id": c["chunk_id"],
                    "evidence_id": c["evidence_id"],
                    "occurrence_id": c["occurrence_id"],
                    "medicine_id": c["medicine_id"] or "",
                    "supply_id": c["supply_id"] or "",
                    "item_type": c["item_type"],
                    "source_id": c["source"]["source_id"],
                    "page": c["source"]["page"],
                    "release_version": c["release_version"],
                    **(
                        {"channel_codes": "|".join(c["channel_codes"])}
                        if "channel_codes" in c
                        else {}
                    ),
                },
            )
            for c in batch
        ]
        for attempt in range(6):
            try:
                store.add_documents(docs, ids=[c["chunk_id"] for c in batch])
                break
            except Exception as exc:
                if re.search(
                    r"(?:per day limit exceeded|daily quota|requests per day)", str(exc), re.I
                ):
                    raise RuntimeError(
                        "Cota diária de embeddings esgotada; "
                        "índice parcial preservado para retomada"
                    ) from exc
                if attempt == 5 or not re.search(
                    r"429|RESOURCE_EXHAUSTED|503|UNAVAILABLE|500|INTERNAL", str(exc), re.I
                ):
                    raise
                retry = re.search(r"retry in ([\d.]+)s", str(exc), re.I)
                delay = float(retry.group(1)) + 3 if retry else 10 * 2**attempt
                time.sleep(min(90, max(5, delay)))
        print(
            f"Embeddings indexados: {len(present) + start + len(batch)}/{len(chunks)}", flush=True
        )
        minimum_seconds = 60 * len(batch) / requests_per_minute
        remaining = minimum_seconds - (time.monotonic() - batch_started)
        if remaining > 0 and start + len(batch) < len(pending):
            time.sleep(remaining)
    indexed = store.get(include=["documents"])
    if {
        cid: text for cid, text in zip(indexed["ids"], indexed["documents"], strict=True)
    } != expected:
        raise ValueError("Índice incompleto ou divergente")
    vectors = store.get(include=["embeddings"])["embeddings"]
    dimensions = {len(v) for v in vectors}
    if len(dimensions) != 1 or next(iter(dimensions)) < 1:
        raise ValueError("Dimensões dos embeddings inconsistentes")
    expected_marker["embedding_dimension"] = next(iter(dimensions))
    temp = location / "index.tmp"
    temp.write_bytes(json_bytes(expected_marker))
    temp.replace(marker)
    return location


def open_index(
    release: ConsolidatedRelease,
    chunks: list[dict[str, Any]],
    chunk_manifest: dict[str, Any],
    base: Path,
    model: str,
    embeddings: Any,
) -> Any:
    location = index_location(base, release, chunk_manifest, model)
    marker = location / "index.json"
    if not marker.exists():
        raise FileNotFoundError("Índice consolidado não construído")
    store = _store(location, embeddings)
    indexed = store.get(include=["documents"])
    expected = {c["chunk_id"]: c["text"] for c in chunks}
    if {
        cid: text for cid, text in zip(indexed["ids"], indexed["documents"], strict=True)
    } != expected:
        raise ValueError("Índice incompleto ou alterado")
    expected_marker = {
        "release_fingerprint": release.fingerprint,
        "chunks_sha256": chunk_manifest["files"]["chunks.jsonl"]["sha256"],
        "embedding_model": model,
        "embedding_api": "langchain_google_genai.embed_documents",
        "count": len(chunks),
    }
    saved = json.loads(marker.read_bytes())
    if any(saved.get(k) != v for k, v in expected_marker.items()):
        raise ValueError("Marcador de índice divergente")
    vectors = store.get(include=["embeddings"])["embeddings"]
    if any(len(v) != saved.get("embedding_dimension") for v in vectors):
        raise ValueError("Dimensão do índice divergente")
    return store


def _vector_ranks(
    question: str,
    store: Any,
    match_ids: set[str],
    allowed: set[str],
    vec_k: int,
) -> dict[str, int]:
    """Rank allowed chunk IDs by vector distance, sorting globally across colliding IDs."""
    if hasattr(store, "similarity_search_with_score"):
        scored_docs: list[tuple[Any, float]] = []
        for mid in sorted(match_ids):
            scored_docs.extend(
                store.similarity_search_with_score(question, k=vec_k, filter={"medicine_id": mid})
            )
        filtered = [
            (doc, float(score))
            for doc, score in scored_docs
            if doc.metadata.get("chunk_id") in allowed
        ]
        # Chroma scores represent distance (lower is closer).
        filtered.sort(key=lambda item: item[1])
        docs = [doc for doc, _score in filtered]
    else:
        docs = []
        for mid in sorted(match_ids):
            docs.extend(store.similarity_search(question, k=vec_k, filter={"medicine_id": mid}))
        docs = [doc for doc in docs if doc.metadata.get("chunk_id") in allowed]
    ranks: dict[str, int] = {}
    for doc in docs:
        chunk_id = doc.metadata["chunk_id"]
        if chunk_id not in ranks:
            ranks[chunk_id] = len(ranks)
    return ranks
