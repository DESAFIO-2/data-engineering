"""Deterministic chunks, retrieval and resumable vectors for consolidated releases."""

from __future__ import annotations

import json
import math
import re
import time
import unicodedata
from collections import Counter
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any


def digest(raw: bytes) -> str:
    return sha256(raw).hexdigest()


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()


def jsonl_bytes(rows: list[dict[str, Any]]) -> bytes:
    return b"".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True).encode() + b"\n" for row in rows
    )


def rows(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_bytes().splitlines() if line.strip()]


@dataclass(frozen=True)
class ConsolidatedRelease:
    folder: Path
    manifest: dict[str, Any]
    catalog: list[dict[str, Any]]
    occurrences: list[dict[str, Any]]
    evidence: list[dict[str, Any]]
    fingerprint: str

    @classmethod
    def load(cls, folder: Path) -> ConsolidatedRelease:
        folder = folder.resolve()
        manifest_raw = (folder / "release.json").read_bytes()
        manifest = json.loads(manifest_raw)
        if (
            manifest.get("schema_version") != "consolidated-release-v2"
            or manifest.get("status") != "approved"
        ):
            raise ValueError("Release consolidado não aprovado")
        expected = {
            "catalog.jsonl",
            "occurrences.jsonl",
            "evidencias.jsonl",
            "exclusions.jsonl",
            "f03_descriptions.json",
            "quality_report.json",
            "domain_review.json",
        }
        if set(manifest["files"]) != expected:
            raise ValueError("Arquivos do release incompletos")
        for name, info in manifest["files"].items():
            if Path(name).name != name:
                raise ValueError("Nome de arquivo inválido")
            raw = (folder / name).read_bytes()
            if digest(raw) != info["sha256"] or len(raw) != info["bytes"]:
                raise ValueError(f"Hash divergente: {name}")
            if name.endswith(".jsonl") and len(rows(folder / name)) != info["records"]:
                raise ValueError(f"Contagem divergente: {name}")
        review = json.loads((folder / "domain_review.json").read_bytes())
        if (
            review.get("decision") != "approved"
            or review.get("evidence_sha256") != manifest["files"]["evidencias.jsonl"]["sha256"]
            or not manifest.get("approval_scope")
        ):
            raise ValueError("Aprovação divergente")
        catalog = rows(folder / "catalog.jsonl")
        occurrences = rows(folder / "occurrences.jsonl")
        evidence = rows(folder / "evidencias.jsonl")
        mids = {m["medicine_id"] for m in catalog}
        oids = {o["occurrence_id"] for o in occurrences}
        eids = {e["evidence_id"] for e in evidence}
        if len(mids) != len(catalog) or len(oids) != len(occurrences) or len(eids) != len(evidence):
            raise ValueError("IDs duplicados")
        by_occ = {o["occurrence_id"]: o for o in occurrences}
        if len(evidence) != len(occurrences):
            raise ValueError("Evidências sem correspondência 1:1")
        for item in catalog:
            if not item["occurrence_ids"] or any(
                by_occ.get(oid, {}).get("medicine_id") != item["medicine_id"]
                for oid in item["occurrence_ids"]
            ):
                raise ValueError("Vínculo do catálogo inválido")
        for ev in evidence:
            occ = by_occ.get(ev["occurrence_id"])
            if (
                occ is None
                or ev["text"] != occ["raw_text"]
                or ev["medicine_id"] != occ.get("medicine_id")
                or ev["source"] != occ["source"]
                or ev.get("review_status") != "approved"
            ):
                raise ValueError("Evidência divergente da ocorrência")
            if occ["item_type"] == "medicine" and occ["medicine_id"] not in mids:
                raise ValueError("Medicamento fora do catálogo")
            if occ["item_type"] == "supply" and (
                occ.get("medicine_id") is not None or ev.get("supply_id") != occ.get("supply_id")
            ):
                raise ValueError("Insumo inválido")
        if any(e["occurrence_id"] == "occ-dd3666cce6867d6246aae72f" for e in evidence):
            raise ValueError("Linha em branco publicada")
        return cls(folder, manifest, catalog, occurrences, evidence, digest(manifest_raw))


CHUNK_RECIPE = "one-evidence-v1:structured-fields;F03-description-cell;F04-indication;no-old-chunks"


def chunk_for(ev: dict[str, Any], release_version: str) -> dict[str, Any]:
    form = ev["form"] if ev["form"] != "-" else "não informada"
    strength = ev["strength"] if ev["strength"] != "-" else "não informada"
    parts = [
        f"Tipo: {'insumo' if ev['item_type'] == 'supply' else 'medicamento'}",
        f"Princípio ativo ou item: {ev['active_ingredient']}",
        f"Concentração ou apresentação: {strength}",
        f"Forma: {form}",
    ]
    if ev.get("release_characteristic"):
        parts.append(f"Liberação: {ev['release_characteristic']}")
    if ev["source"]["source_id"] == "F03":
        parts.append(f"Descrição na REME-DF: {ev['description_cell']}")
    if ev["source"]["source_id"] == "F04":
        parts.append(f"Indicação no elenco: {ev['indication']}")
    parts.append(f"Consta na lista {ev['source']['source_id']} ({ev['source']['version']}).")
    text = "\n".join(parts)
    return {
        "chunk_id": "chunk-" + ev["evidence_id"].removeprefix("evidence-"),
        "evidence_id": ev["evidence_id"],
        "occurrence_id": ev["occurrence_id"],
        "medicine_id": ev["medicine_id"],
        "supply_id": ev.get("supply_id"),
        "item_type": ev["item_type"],
        "source": ev["source"],
        "release_version": release_version,
        "text": text,
        "literal_text": ev["text"],
    }


def build_chunks(release: ConsolidatedRelease, output: Path) -> dict[str, Any]:
    chunks = [chunk_for(e, release.manifest["release_version"]) for e in release.evidence]
    if len({c["chunk_id"] for c in chunks}) != len(chunks) or any(
        not c["text"].strip() for c in chunks
    ):
        raise ValueError("Chunks duplicados ou vazios")
    payload = jsonl_bytes(chunks)
    recipe_hash = digest(CHUNK_RECIPE.encode())
    manifest = {
        "schema_version": "consolidated-chunks-v1",
        "release_version": release.manifest["release_version"],
        "release_fingerprint": release.fingerprint,
        "recipe": CHUNK_RECIPE,
        "recipe_sha256": recipe_hash,
        "files": {
            "chunks.jsonl": {
                "sha256": digest(payload),
                "bytes": len(payload),
                "records": len(chunks),
            }
        },
    }
    output.mkdir(parents=False, exist_ok=False)
    (output / "chunks.jsonl").write_bytes(payload)
    (output / "manifest.json").write_bytes(json_bytes(manifest))
    load_chunks(release, output)
    return manifest


def load_chunks(
    release: ConsolidatedRelease, folder: Path
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    manifest = json.loads((folder / "manifest.json").read_bytes())
    info = manifest.get("files", {}).get("chunks.jsonl", {})
    raw = (folder / "chunks.jsonl").read_bytes()
    chunks = rows(folder / "chunks.jsonl")
    if (
        manifest.get("schema_version") != "consolidated-chunks-v1"
        or manifest.get("release_fingerprint") != release.fingerprint
        or manifest.get("recipe_sha256") != digest(CHUNK_RECIPE.encode())
        or info.get("sha256") != digest(raw)
        or info.get("bytes") != len(raw)
        or info.get("records") != len(chunks)
    ):
        raise ValueError("Manifesto de chunks divergente")
    expected = [chunk_for(e, release.manifest["release_version"]) for e in release.evidence]
    if chunks != expected:
        raise ValueError("Chunks não correspondem ao release aprovado")
    return chunks, manifest


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
                },
            )
            for c in batch
        ]
        for attempt in range(6):
            try:
                store.add_documents(docs, ids=[c["chunk_id"] for c in batch])
                break
            except Exception as exc:
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


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKD", value.casefold())
    value = "".join(c for c in value if not unicodedata.combining(c))
    value = re.sub(r"(?<=\d)\s*(?=(?:mcg|mg|ml|ui)\b)", " ", value)
    return " ".join(value.split())


def bm25_rank(question: str, chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Rank only already compatible candidates; never choose an identity by score."""
    query = set(re.findall(r"\w+", normalize(question)))
    documents = [Counter(re.findall(r"\w+", normalize(c["text"]))) for c in chunks]
    average = sum(sum(doc.values()) for doc in documents) / len(documents)
    scores = []
    for chunk, doc in zip(chunks, documents, strict=True):
        length = sum(doc.values())
        score = 0.0
        for term in query:
            frequency = doc[term]
            if not frequency:
                continue
            found = sum(term in other for other in documents)
            idf = math.log(1 + (len(documents) - found + 0.5) / (found + 0.5))
            score += (
                idf * frequency * 2.5 / (frequency + 1.5 * (1 - 0.75 + 0.75 * length / average))
            )
        scores.append((score, chunk))
    return [chunk for _, chunk in sorted(scores, key=lambda x: (-x[0], x[1]["chunk_id"]))]


def search(
    question: str,
    release: ConsolidatedRelease,
    chunks: list[dict[str, Any]],
    store: Any = None,
    strategy: str = "hybrid",
    top_k: int = 5,
) -> dict[str, Any]:
    if strategy not in {"exact", "lexical", "vector", "hybrid"} or not 1 <= top_k <= 20:
        raise ValueError("Estratégia ou top_k inválido")
    query = normalize(question)
    if any(
        re.search(r"\b" + re.escape(x) + r"\b", query)
        for x in (
            "estoque",
            "disponibilidade",
            "hoje",
            "documentos",
            "receita",
            "lme",
            "exame",
            "jejum",
            "posso tomar",
            "quanto tomar",
            "substituir",
            "diagnostico",
        )
    ):
        return {
            "status": "unsupported",
            "evidence": [],
            "message": (
                "Este release informa somente presença nas listas, sem estoque, "
                "elegibilidade ou orientação clínica."
            ),
        }
    source_filter = None
    if "reme" in query or "f03" in query:
        source_filter = "F03"
    elif "farmacia popular" in query or "f04" in query:
        source_filter = "F04"
    elif "rename" in query or "f01" in query:
        source_filter = "F01"
    if "insumo" in query:
        supplies = [
            o
            for o in release.occurrences
            if o["item_type"] == "supply"
            and normalize(o["active_ingredient"]) in query
            and (o["strength"] == "-" or normalize(o["strength"]) in query)
        ]
        if source_filter:
            supplies = [o for o in supplies if o["source"]["source_id"] == source_filter]
        if len(supplies) != 1:
            return {
                "status": "ambiguous" if supplies else "not_in_scope",
                "evidence": [],
                "message": "Informe o insumo e sua apresentação exata.",
            }
        item = supplies[0]
        ev = next(e for e in release.evidence if e["occurrence_id"] == item["occurrence_id"])
        return {
            "status": "matched",
            "evidence": [ev],
            "message": (
                f"{item['active_ingredient']} consta como insumo em "
                f"{item['source']['source_id']}. Presença em lista não confirma disponibilidade."
            ),
        }
    names = [
        m for m in release.catalog
        if normalize(m["active_ingredient"]) in query
        and (not source_filter or source_filter in m["source_ids"])
    ]
    if names:
        longest_name = max(len(normalize(m["active_ingredient"])) for m in names)
        names = [m for m in names if len(normalize(m["active_ingredient"])) == longest_name]
    if names:
        strengths = [m for m in names if m["strength"] == "-" or normalize(m["strength"]) in query]
        if not strengths:
            return {
                "status": "not_in_scope",
                "evidence": [],
                "message": (
                    "Concentração não localizada para este princípio ativo nas listas consultadas."
                ),
            }
        matches = [m for m in strengths if m["form"] == "-" or normalize(m["form"]) in query]
        if matches:
            longest_strength = max(len(normalize(m["strength"])) for m in matches)
            matches = [m for m in matches if len(normalize(m["strength"])) == longest_strength]
            longest_form = max(
                len(normalize(m["form"])) if m["form"] != "-" else 0 for m in matches
            )
            matches = [
                m
                for m in matches
                if (len(normalize(m["form"])) if m["form"] != "-" else 0) == longest_form
            ]
    else:
        matches = []
    if not matches:
        supplies = [
            o
            for o in release.occurrences
            if o["item_type"] == "supply"
            and normalize(o["active_ingredient"]) in query
            and (o["strength"] == "-" or normalize(o["strength"]) in query)
        ]
        if source_filter:
            supplies = [o for o in supplies if o["source"]["source_id"] == source_filter]
        if len(supplies) == 1:
            item = supplies[0]
            ev = next(e for e in release.evidence if e["occurrence_id"] == item["occurrence_id"])
            return {
                "status": "matched",
                "evidence": [ev],
                "message": (
                    f"{item['active_ingredient']} consta como insumo em "
                    f"{item['source']['source_id']}. "
                    "Presença em lista não confirma disponibilidade."
                ),
            }
    if len(matches) != 1 and (
        not matches
        or len(
            {
                (
                    normalize(m["active_ingredient"]),
                    normalize(m["strength"]),
                    normalize(m["form"]),
                    normalize(m.get("release_characteristic") or ""),
                )
                for m in matches
            }
        )
        != 1
    ):
        return {
            "status": "ambiguous" if matches else "not_in_scope",
            "evidence": [],
            "message": (
                "Informe apresentação exata: princípio ativo, concentração e forma "
                "quando documentadas."
            ),
        }
    med = matches[0]
    match_ids = {m["medicine_id"] for m in matches}
    selected = [c for c in chunks if c["medicine_id"] in match_ids]
    if source_filter:
        selected = [c for c in selected if c["source"]["source_id"] == source_filter]
    if not selected:
        return {
            "status": "not_in_scope",
            "evidence": [],
            "message": "Esta apresentação não consta na fonte solicitada.",
        }
    lexical = bm25_rank(question, selected)
    if strategy in {"vector", "hybrid"} and store is not None:
        docs = []
        for mid in sorted(match_ids):
            docs.extend(
                store.similarity_search(
                    question, k=min(max(top_k * 3, 10), len(selected)), filter={"medicine_id": mid}
                )
            )
        allowed = {c["chunk_id"] for c in selected}
        docs = [d for d in docs if d.metadata.get("chunk_id") in allowed]
        ranks = {d.metadata["chunk_id"]: i for i, d in enumerate(docs)}
        if strategy == "vector":
            selected = sorted(selected, key=lambda c: ranks.get(c["chunk_id"], 10**6))
        else:
            lrank = {c["chunk_id"]: i for i, c in enumerate(lexical)}
            selected = sorted(
                selected,
                key=lambda c: (
                    1 / (60 + lrank[c["chunk_id"]])
                    + (1 / (60 + ranks[c["chunk_id"]]) if c["chunk_id"] in ranks else 0)
                ),
                reverse=True,
            )
    else:
        selected = lexical
    evidence_by_id = {e["evidence_id"]: e for e in release.evidence}
    sources = sorted({c["source"]["source_id"] for c in selected})
    return {
        "status": "matched",
        "medicine": med,
        "equivalent_medicine_ids": sorted(match_ids),
        "evidence": [evidence_by_id[c["evidence_id"]] for c in selected[:top_k]],
        "message": (
            f"{med['active_ingredient']} {med['strength']} ({med['form']}) consta nas fontes: "
            f"{', '.join(sources)}. Presença em lista não confirma estoque."
        ),
    }
