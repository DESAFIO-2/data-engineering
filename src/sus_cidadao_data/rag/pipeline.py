from __future__ import annotations

import hashlib
import json
import math
import re
import unicodedata
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TypedDict, cast

from pypdf import PdfReader

TOKEN_PATTERN = re.compile(r"[a-z0-9]+", re.IGNORECASE)


class SourceConfig(TypedDict):
    source_id: str
    document_id: str
    title: str
    version: str
    document_date: str | None
    territory: str
    content_type: str
    path: str
    enabled: bool


class RagConfig(TypedDict):
    schema_version: int
    chunk_size_words: int
    chunk_overlap_words: int
    sources: list[SourceConfig]


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    text: str
    source_id: str
    document_id: str
    title: str
    version: str
    document_date: str | None
    territory: str
    content_type: str
    page: int
    chunk_index_on_page: int


@dataclass(frozen=True)
class SearchResult:
    score: float
    chunk: Chunk


@dataclass(frozen=True)
class BuildSummary:
    corpus_path: str
    index_path: str
    manifest_path: str
    document_count: int
    page_count: int
    chunk_count: int
    extraction_warnings: list[str]
    corpus_sha256: str


@dataclass(frozen=True)
class SparseIndex:
    idf: dict[str, float]
    vectors: dict[str, dict[str, float]]


def repository_root() -> Path:
    return Path(__file__).resolve().parents[3]


def load_config(path: Path) -> RagConfig:
    raw = cast(dict[str, object], json.loads(path.read_text(encoding="utf-8")))
    required = {"schema_version", "chunk_size_words", "chunk_overlap_words", "sources"}
    missing = required - raw.keys()
    if missing:
        raise ValueError(f"Configuração incompleta; campos ausentes: {sorted(missing)}")
    config = cast(RagConfig, raw)
    if config["chunk_size_words"] <= 0:
        raise ValueError("chunk_size_words deve ser maior que zero")
    if not 0 <= config["chunk_overlap_words"] < config["chunk_size_words"]:
        raise ValueError("chunk_overlap_words deve ser menor que chunk_size_words")
    return config


def normalize_text(text: str) -> str:
    text = text.replace("\u00ad", "").replace("\x00", " ")
    return re.sub(r"\s+", " ", text).strip()


def chunk_page(
    text: str,
    *,
    source: SourceConfig,
    page: int,
    chunk_size_words: int,
    overlap_words: int,
) -> list[Chunk]:
    words = normalize_text(text).split()
    if not words:
        return []
    step = chunk_size_words - overlap_words
    chunks: list[Chunk] = []
    for index, start in enumerate(range(0, len(words), step)):
        selected = words[start : start + chunk_size_words]
        if not selected:
            break
        text_value = " ".join(selected)
        identity = f"{source['document_id']}|{page}|{index}|{text_value}".encode()
        chunk_id = hashlib.sha256(identity).hexdigest()[:20]
        chunks.append(
            Chunk(
                chunk_id=chunk_id,
                text=text_value,
                source_id=source["source_id"],
                document_id=source["document_id"],
                title=source["title"],
                version=source["version"],
                document_date=source["document_date"],
                territory=source["territory"],
                content_type=source["content_type"],
                page=page,
                chunk_index_on_page=index,
            )
        )
        if start + chunk_size_words >= len(words):
            break
    return chunks


def extract_source(
    source: SourceConfig,
    *,
    root: Path,
    chunk_size_words: int,
    overlap_words: int,
) -> tuple[list[Chunk], int, list[str]]:
    path = root / source["path"]
    if not path.is_file():
        raise FileNotFoundError(f"Fonte não encontrada: {path}")
    reader = PdfReader(path)
    chunks: list[Chunk] = []
    warnings: list[str] = []
    for page_number, pdf_page in enumerate(reader.pages, start=1):
        try:
            text = pdf_page.extract_text() or ""
        except Exception as exc:  # pypdf pode falhar em uma página sem invalidar o documento
            warnings.append(f"{source['document_id']} página {page_number}: {exc}")
            continue
        page_chunks = chunk_page(
            text,
            source=source,
            page=page_number,
            chunk_size_words=chunk_size_words,
            overlap_words=overlap_words,
        )
        if not page_chunks:
            warnings.append(f"{source['document_id']} página {page_number}: sem texto extraído")
        chunks.extend(page_chunks)
    return chunks, len(reader.pages), warnings


def _normalized_tokens(text: str) -> list[str]:
    normalized = unicodedata.normalize("NFKD", text.casefold())
    ascii_text = "".join(char for char in normalized if not unicodedata.combining(char))
    words = TOKEN_PATTERN.findall(ascii_text)
    bigrams = [f"{left}__{right}" for left, right in zip(words, words[1:], strict=False)]
    return words + bigrams


def _l2_normalize(weights: dict[str, float]) -> dict[str, float]:
    norm = math.sqrt(sum(value * value for value in weights.values()))
    if norm == 0:
        return {}
    return {term: value / norm for term, value in weights.items()}


def build_sparse_index(chunks: list[Chunk]) -> SparseIndex:
    document_frequency: defaultdict[str, int] = defaultdict(int)
    term_frequencies: dict[str, Counter[str]] = {}
    for chunk in chunks:
        frequencies = Counter(_normalized_tokens(chunk.text))
        term_frequencies[chunk.chunk_id] = frequencies
        for term in frequencies:
            document_frequency[term] += 1
    total = len(chunks)
    idf = {
        term: math.log((1 + total) / (1 + frequency)) + 1
        for term, frequency in document_frequency.items()
    }
    vectors: dict[str, dict[str, float]] = {}
    for chunk_id, frequencies in term_frequencies.items():
        raw_weights = {
            term: (1 + math.log(count)) * idf[term] for term, count in frequencies.items()
        }
        vectors[chunk_id] = _l2_normalize(raw_weights)
    return SparseIndex(idf=idf, vectors=vectors)


def search_index(
    query: str,
    *,
    chunks: list[Chunk],
    index: SparseIndex,
    top_k: int = 5,
) -> list[SearchResult]:
    if top_k <= 0:
        raise ValueError("top_k deve ser maior que zero")
    query_counts = Counter(_normalized_tokens(query))
    query_weights = {
        term: (1 + math.log(count)) * index.idf[term]
        for term, count in query_counts.items()
        if term in index.idf
    }
    query_vector = _l2_normalize(query_weights)
    if not query_vector:
        return []
    chunk_by_id = {chunk.chunk_id: chunk for chunk in chunks}
    scored: list[SearchResult] = []
    for chunk_id, vector in index.vectors.items():
        score = sum(weight * vector.get(term, 0.0) for term, weight in query_vector.items())
        if score > 0:
            scored.append(SearchResult(score=score, chunk=chunk_by_id[chunk_id]))
    scored.sort(key=lambda result: (-result.score, result.chunk.chunk_id))
    return scored[:top_k]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_jsonl(path: Path, chunks: list[Chunk]) -> None:
    with path.open("w", encoding="utf-8") as file:
        for chunk in chunks:
            file.write(json.dumps(asdict(chunk), ensure_ascii=False, sort_keys=True) + "\n")


def _read_jsonl(path: Path) -> list[Chunk]:
    chunks: list[Chunk] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            raw = cast(dict[str, object], json.loads(line))
            chunks.append(
                Chunk(
                    chunk_id=str(raw["chunk_id"]),
                    text=str(raw["text"]),
                    source_id=str(raw["source_id"]),
                    document_id=str(raw["document_id"]),
                    title=str(raw["title"]),
                    version=str(raw["version"]),
                    document_date=(
                        str(raw["document_date"]) if raw.get("document_date") is not None else None
                    ),
                    territory=str(raw["territory"]),
                    content_type=str(raw["content_type"]),
                    page=int(cast(int, raw["page"])),
                    chunk_index_on_page=int(cast(int, raw["chunk_index_on_page"])),
                )
            )
    return chunks


def build_pipeline(config_path: Path, output_dir: Path) -> BuildSummary:
    config = load_config(config_path)
    root = repository_root()
    output_dir.mkdir(parents=True, exist_ok=True)
    all_chunks: list[Chunk] = []
    warnings: list[str] = []
    page_count = 0
    enabled_sources = [source for source in config["sources"] if source["enabled"]]
    if not enabled_sources:
        raise ValueError("Nenhuma fonte habilitada na configuração")
    source_manifest: list[dict[str, object]] = []
    for source in enabled_sources:
        source_path = root / source["path"]
        chunks, pages, source_warnings = extract_source(
            source,
            root=root,
            chunk_size_words=config["chunk_size_words"],
            overlap_words=config["chunk_overlap_words"],
        )
        all_chunks.extend(chunks)
        warnings.extend(source_warnings)
        page_count += pages
        source_manifest.append(
            {
                "source_id": source["source_id"],
                "document_id": source["document_id"],
                "path": source["path"],
                "sha256": _sha256(source_path),
                "pages": pages,
                "chunks": len(chunks),
            }
        )
    if not all_chunks:
        raise ValueError("Nenhum trecho foi extraído das fontes habilitadas")

    corpus_path = output_dir / "corpus.jsonl"
    index_path = output_dir / "tfidf-index.json"
    manifest_path = output_dir / "build-manifest.json"
    _write_jsonl(corpus_path, all_chunks)
    index = build_sparse_index(all_chunks)
    index_path.write_text(
        json.dumps(asdict(index), ensure_ascii=False, sort_keys=True), encoding="utf-8"
    )
    corpus_hash = _sha256(corpus_path)
    manifest = {
        "schema_version": 1,
        "built_at_utc": datetime.now(UTC).isoformat(),
        "retrieval_method": "tfidf-unigram-bigram-cosine",
        "config_path": str(config_path),
        "config_sha256": _sha256(config_path),
        "corpus_sha256": corpus_hash,
        "chunk_size_words": config["chunk_size_words"],
        "chunk_overlap_words": config["chunk_overlap_words"],
        "documents": source_manifest,
        "document_count": len(enabled_sources),
        "page_count": page_count,
        "chunk_count": len(all_chunks),
        "warnings": warnings,
    }
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return BuildSummary(
        corpus_path=str(corpus_path),
        index_path=str(index_path),
        manifest_path=str(manifest_path),
        document_count=len(enabled_sources),
        page_count=page_count,
        chunk_count=len(all_chunks),
        extraction_warnings=warnings,
        corpus_sha256=corpus_hash,
    )


def load_built_index(output_dir: Path) -> tuple[list[Chunk], SparseIndex]:
    corpus_path = output_dir / "corpus.jsonl"
    index_path = output_dir / "tfidf-index.json"
    if not corpus_path.is_file() or not index_path.is_file():
        raise FileNotFoundError("Índice ausente. Execute o comando build primeiro.")
    chunks = _read_jsonl(corpus_path)
    raw_index = cast(dict[str, object], json.loads(index_path.read_text(encoding="utf-8")))
    index = SparseIndex(
        idf=cast(dict[str, float], raw_index["idf"]),
        vectors=cast(dict[str, dict[str, float]], raw_index["vectors"]),
    )
    return chunks, index
