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
        files = set(manifest["files"])
        if not (files == expected or files == (expected | {"audit_log.jsonl"})):
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
        exclusions = rows(folder / "exclusions.jsonl")
        excluded_ids = {item["occurrence_id"] for item in exclusions if item.get("occurrence_id")}
        for ev in evidence:
            text_stripped = str(ev.get("text") or "").strip()
            if (
                ev["occurrence_id"] in excluded_ids
                or not text_stripped
                or re.fullmatch(r"\d+\.?", text_stripped)
            ):
                raise ValueError("Linha em branco ou excluída publicada")
        return cls(folder, manifest, catalog, occurrences, evidence, digest(manifest_raw))


CHUNK_RECIPE = "one-evidence-v1:structured-fields;F03-description-cell;F04-indication;no-old-chunks"
CHUNK_RECIPE_V1 = CHUNK_RECIPE
CHUNK_RECIPE_V2 = (
    "one-evidence-v2:structured-fields;F03-description-cell;F04-indication;"
    "source-provenance;no-old-chunks"
)
_SUPPORTED_CHUNK_RECIPES = {
    CHUNK_RECIPE_V1: digest(CHUNK_RECIPE_V1.encode()),
    CHUNK_RECIPE_V2: digest(CHUNK_RECIPE_V2.encode()),
}


def chunk_for(
    ev: dict[str, Any], release_version: str, recipe: str = CHUNK_RECIPE_V1
) -> dict[str, Any]:
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
    if recipe == CHUNK_RECIPE_V2:
        src = ev["source"]
        loc_parts = [f"p. {src['page']}"]
        if ev.get("source_row_number") is not None:
            loc_parts.append(f"item {ev['source_row_number']}")
        elif ev.get("line_start") is not None:
            ls = ev["line_start"]
            le = ev.get("line_end")
            loc_parts.append(f"linhas {ls}-{le}" if le and le != ls else f"linha {ls}")
        else:
            loc_parts.append(ev["occurrence_id"])
        parts.append(f"Proveniência: {src['source_id']} ({', '.join(loc_parts)}).")
    elif recipe != CHUNK_RECIPE_V1:
        raise ValueError(f"Receita de chunk desconhecida: {recipe}")
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


def build_chunks(
    release: ConsolidatedRelease, output: Path, recipe: str = CHUNK_RECIPE_V2
) -> dict[str, Any]:
    if recipe not in _SUPPORTED_CHUNK_RECIPES:
        raise ValueError(f"Receita de chunk desconhecida: {recipe}")
    chunks = [
        chunk_for(e, release.manifest["release_version"], recipe=recipe) for e in release.evidence
    ]
    has_dup_texts = recipe == CHUNK_RECIPE_V2 and len({c["text"] for c in chunks}) != len(chunks)
    if (
        len({c["chunk_id"] for c in chunks}) != len(chunks)
        or has_dup_texts
        or any(not c["text"].strip() for c in chunks)
    ):
        raise ValueError("Chunks duplicados ou vazios")
    payload = jsonl_bytes(chunks)
    recipe_hash = _SUPPORTED_CHUNK_RECIPES[recipe]
    manifest = {
        "schema_version": "consolidated-chunks-v1",
        "release_version": release.manifest["release_version"],
        "release_fingerprint": release.fingerprint,
        "recipe": recipe,
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
    recipe = manifest.get("recipe")
    expected_recipe_hash = _SUPPORTED_CHUNK_RECIPES.get(recipe) if isinstance(recipe, str) else None
    if (
        manifest.get("schema_version") != "consolidated-chunks-v1"
        or manifest.get("release_fingerprint") != release.fingerprint
        or expected_recipe_hash is None
        or manifest.get("recipe_sha256") != expected_recipe_hash
        or info.get("sha256") != digest(raw)
        or info.get("bytes") != len(raw)
        or info.get("records") != len(chunks)
    ):
        raise ValueError("Manifesto de chunks divergente")
    assert isinstance(recipe, str)
    expected = [
        chunk_for(e, release.manifest["release_version"], recipe=recipe) for e in release.evidence
    ]
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


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKD", value.casefold())
    value = "".join(c for c in value if not unicodedata.combining(c))
    value = re.sub(r"(?<=\d)\s*(?=(?:mcg|mg|ml|ui)\b)", " ", value)
    value = re.sub(r"\s*/\s*", "/", value)
    return " ".join(value.split())


def strength_core(value: str) -> str:
    """Separate a documented device/package suffix, never chemical equivalence."""
    return re.sub(
        r"\s*\((?:sistema de aplicacao|apresentacoes? de|frasco|ampola|caneta)\b[^)]*\)$",
        "",
        normalize(value),
    )


def _textual_presentation(value: str) -> str:
    """Ignore an optional article in the documented homeopathic descriptor."""
    return normalize(value).replace("conforme a farmacopeia", "conforme farmacopeia")


def _form_matches(query: str, form: str) -> bool:
    documented = _textual_presentation(form)
    requested = _textual_presentation(query)
    if documented in requested:
        return True
    if documented == "solucao injetavel":
        return bool(re.search(r"\binjetavel\b", requested))
    if documented.startswith("comprimido de liberacao "):
        return bool(re.search(r"\bcomprimido\b", requested))
    return False


def _interleaved_association_matches(query: str, strength: str, name: str | None) -> bool:
    if not name or " + " not in normalize(name) or " + " not in normalize(strength):
        return False
    components = normalize(name).split(" + ")
    doses = normalize(strength).split(" + ")
    if len(components) != len(doses):
        return False
    pattern = (
        r"(?<!\w)"
        + r"\s*\+\s*".join(
            re.escape(component) + r"\s+" + re.escape(dose)
            for component, dose in zip(components, doses, strict=True)
        )
        + r"(?![\w/,])"
    )
    return bool(re.search(pattern, query))


def strength_matches(query: str, strength: str, name: str | None = None) -> bool:
    stored = normalize(strength)
    core = strength_core(stored)
    if stored.startswith("de ") and " frasco" in stored:
        core = stored.split(" frasco", 1)[0]
    elif stored.startswith("bolsa ou frasco "):
        volume = re.search(r"\b\d+(?:[.,]\d+)?\s*ml\b", stored)
        core = volume.group() if volume else core
    comparison_query = _textual_presentation(query)
    comparison_core = _textual_presentation(core)
    literal = re.search(
        r"(?<![\w.,/])" + re.escape(comparison_core) + r"(?![\w./]|,\d)",
        comparison_query,
    )
    # Parentheses in a natural question may group a documented strength without
    # changing its units, alternatives or ingredient order.
    flat_query = _textual_presentation(re.sub(r"[()]", " ", query))
    flat_core = _textual_presentation(re.sub(r"[()]", " ", core))
    grouped = re.search(r"(?<![\w.,/])" + re.escape(flat_core) + r"(?![\w./]|,\d)", flat_query)
    if not (literal or grouped or _interleaved_association_matches(query, strength, name)):
        return False
    requested_packages = set(re.findall(r"\b(?:bolsa|frasco|ampola|seringa)\b", query))
    stored_packages = set(re.findall(r"\b(?:bolsa|frasco|ampola|seringa)\b", stored))
    if stored_packages and requested_packages - stored_packages:
        return False
    if "sistema fechado" in query and "sistema fechado" not in stored:
        return False
    requested_device = re.search(r"sistema de aplicacao\s+(\d+(?:[.,]\d+)?)\s*ml", query)
    if requested_device:
        stored_device = re.search(r"sistema de aplicacao\s+(\d+(?:[.,]\d+)?)\s*ml", stored)
        if not stored_device or requested_device.group(1) != stored_device.group(1):
            return False
    return True


def name_suggestion(question: str, catalog: list[dict[str, Any]]) -> tuple[str, str] | None:
    """Suggest a unique one-character typo; never silently select a medicine."""
    query = normalize(question)
    if any(name_matches(query, m["active_ingredient"]) for m in catalog):
        return None
    names = {
        normalize(m["active_ingredient"]): m["active_ingredient"]
        for m in catalog
        if re.fullmatch(r"[a-z]{6,}", normalize(m["active_ingredient"]))
    }
    suggestions = set()
    for token in re.findall(r"\b[a-z]{6,}\b", query):
        for name in names:
            if abs(len(token) - len(name)) > 1:
                continue
            if len(token) == len(name):
                different = [i for i, (a, b) in enumerate(zip(token, name, strict=True)) if a != b]
                close = len(different) == 1 or (
                    len(different) == 2
                    and different[1] == different[0] + 1
                    and token[different[0]] == name[different[1]]
                    and token[different[1]] == name[different[0]]
                )
            else:
                shorter, longer = sorted((token, name), key=len)
                close = any(longer[:i] + longer[i + 1 :] == shorter for i in range(len(longer)))
            if close:
                corrected = re.sub(r"\b" + re.escape(token) + r"\b", name, query)
                suggestions.add((names[name], corrected))
    return next(iter(suggestions)) if len(suggestions) == 1 else None


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


CLINICAL_BLOCKED_TERMS: tuple[str, ...] = (
    "posso tomar",
    "quanto tomar",
    "como tomar",
    "como devo tomar",
    "como usar",
    "como devo usar",
    "qual dose",
    "qual a dose",
    "qual e a dose",
    "que dose",
    "minha dose",
    "devo tomar",
    "dosagem",
    "posologia",
    "superdosagem",
    "dose diaria",
    "dose maxima",
    "dose minima",
    "dose recomendada",
    "substituir",
    "substituicao terapeutica",
    "posso trocar",
    "trocar pela",
    "trocar por",
    "trocar esse medicamento",
    "trocar meu medicamento",
    "alterar a dose",
    "aumentar a dose",
    "diminuir a dose",
    "dobrar a dose",
    "reduzir a dose",
    "indicar dose",
    "recomendar dose",
    "dose infantil",
    "dose pediatrica",
    "dose para crianca",
    "quantos comprimidos",
    "quantas gotas",
    "quantas vezes ao dia",
    "de quantas em quantas horas",
    "partir o comprimido",
    "cortar o comprimido",
    "suspender o medicamento",
    "parar de tomar",
    "esqueci de tomar",
    "overdose",
    "prescreva",
    "prescrever",
    "receitar",
    "me receite",
    "equivalencia",
    "equivalencias",
    "equivalente terapeutico",
    "equivalentes terapeuticos",
    "medicamento equivalente",
    "medicamentos equivalentes",
    "tem equivalente",
    "qual o equivalente",
    "qual e o equivalente",
    "e equivalente",
    "sao equivalentes",
    "mesmo efeito",
    "mesma eficacia",
    "diagnostico",
    "indicado para mim",
    "indicada para mim",
    "serve para o meu caso",
    "tenho direito",
    "sou elegivel",
    "posso usar",
    "posso receber",
    "posso misturar",
    "tomar com alcool",
    "misturar com alcool",
    "beber alcool",
    "ingerir alcool",
    "efeito colateral",
    "efeitos colaterais",
    "reacao adversa",
    "reacoes adversas",
    "contraindicacao",
    "contraindicacoes",
    "gravidez",
    "gravida",
    "gravidas",
    "gestacao",
    "gestante",
    "gestantes",
    "amamentacao",
    "amamentando",
    "lactante",
    "interacao medicamentosa",
    "interacoes medicamentosas",
    "interage com",
    "interacao com",
)

CLINICAL_BLOCKED_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(?:trocar|substituir)\b.{1,40}\bpor\b"),
    re.compile(r"\b(?:qual|que|recomende|indique|calcule|ajuste)\b.{0,25}\bdose\b"),
    re.compile(r"\b(?:devo|posso|preciso)\s+(?:tomar|usar|aplicar|suspender|interromper)\b"),
)

PROMPT_INJECTION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"\b(?:ignore|desconsidere|esqueca|anule)\b.{0,30}"
        r"\b(?:instrucoes|regras|restricoes|limites|diretrizes|sistema)\b"
    ),
    re.compile(
        r"\b(?:system prompt|prompt do sistema|instrucoes internas|"
        r"instrucoes do sistema|regras internas|jailbreak|dan mode|modo desenvolvedor)\b"
    ),
    re.compile(
        r"\b(?:atue|finja|aja|comporte-se|responda)\s+como\s+(?:um|uma)?\s*"
        r"(?:medico|medica|farmaceutico|farmaceutica|prescritor|especialista clinico)\b"
    ),
    re.compile(
        r"\b(?:diga|responda|afirme|garanta|invente)\s+que\s+"
        r"(?:tem|ha|existe|esta)\s+(?:disponivel\s+)?(?:em\s+)?estoque\b"
    ),
    re.compile(r"(?:^|\n)\s*(?:system|developer|assistant)\s*:", re.IGNORECASE),
)

DOCUMENTAL_ONLY_BLOCKED_TERMS: tuple[str, ...] = (
    "estoque",
    "disponibilidade",
    "hoje",
    "documentos",
    "receita",
    "lme",
    "exame",
    "jejum",
)


def matches_clinical_guardrail(question: str) -> bool:
    """Detect out-of-scope clinical, dosing, pregnancy, or eligibility queries via lexical rules."""
    query = normalize(question)
    return any(
        re.search(r"\b" + re.escape(term) + r"\b", query) for term in CLINICAL_BLOCKED_TERMS
    ) or any(pattern.search(query) for pattern in CLINICAL_BLOCKED_PATTERNS)


def matches_prompt_injection(question: str) -> bool:
    """Detect prompt-override, role-impersonation, or fabricated-stock injection attempts."""
    query = normalize(question)
    return any(
        pattern.search(question if ":\\s*" in pattern.pattern else query)
        for pattern in PROMPT_INJECTION_PATTERNS
    )


def matches_documental_scope_block(question: str) -> bool:
    """Detect queries outside the frozen list-presence scope (clinical, stock, or documents)."""
    query = normalize(question)
    if matches_clinical_guardrail(query):
        return True
    return any(
        re.search(r"\b" + re.escape(term) + r"\b", query) for term in DOCUMENTAL_ONLY_BLOCKED_TERMS
    )


def search(
    question: str,
    release: ConsolidatedRelease,
    chunks: list[dict[str, Any]],
    store: Any = None,
    strategy: str = "lexical",
    top_k: int = 5,
) -> dict[str, Any]:
    if strategy not in {"exact", "lexical", "vector", "hybrid"} or not 1 <= top_k <= 20:
        raise ValueError("Estratégia ou top_k inválido")
    if strategy in {"vector", "hybrid"} and store is None:
        raise ValueError(
            f"Estratégia '{strategy}' exige índice vetorial carregado (store); "
            "execute 'index' ou use 'lexical'/'exact'."
        )
    query = normalize(question)
    if matches_documental_scope_block(query) or matches_prompt_injection(question):
        return {
            "status": "unsupported",
            "evidence": [],
            "message": (
                "Este release informa somente presença nas listas, sem estoque, "
                "elegibilidade ou orientação clínica."
            ),
        }
    source_filter = None
    if re.search(r"\b(?:reme|reme-df)\b", query) or re.search(r"\bf03\b", query):
        source_filter = "F03"
    elif "farmacia popular" in query or re.search(r"\bf04\b", query):
        source_filter = "F04"
    elif re.search(r"\brename\b", query) or re.search(r"\bf01\b", query):
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
        m
        for m in release.catalog
        if name_matches(query, m["active_ingredient"])
        and (not source_filter or source_filter in m["source_ids"])
    ]
    if names:
        identities = {ingredient_key(m["active_ingredient"]) for m in names}
        longest_identity = max(identities, key=len)
        if any(identity not in longest_identity for identity in identities):
            return {
                "status": "ambiguous",
                "evidence": [],
                "message": "Informe um princípio ativo ou uma associação documentada por pergunta.",
            }
        longest_name = max(len(normalize(m["active_ingredient"])) for m in names)
        names = [m for m in names if len(normalize(m["active_ingredient"])) == longest_name]
    if names:
        strengths = [
            m
            for m in names
            if m["strength"] == "-"
            or strength_matches(query, m["strength"], m["active_ingredient"])
        ]
        if not strengths:
            if not re.search(r"\d+(?:[.,]\d+)?\s*(?:mg|mcg|g|ui|ml)\b", query):
                options = sorted(
                    names,
                    key=lambda m: (
                        normalize(m["strength"]),
                        normalize(m["form"]),
                        normalize(m.get("release_characteristic") or ""),
                        m["medicine_id"],
                    ),
                )
                return {
                    "status": "ambiguous",
                    "evidence": [],
                    "candidate_presentations": options,
                    "message": "Apresentações documentadas: "
                    + "; ".join(
                        f"{m['strength']} — {m['form']}"
                        + (
                            f" — {m['release_characteristic']}"
                            if m.get("release_characteristic")
                            else ""
                        )
                        + f" ({', '.join(m['source_ids'])})"
                        for m in options
                    )
                    + ". Qual concentração ou forma você procura?",
                }
            return {
                "status": "not_in_scope",
                "evidence": [],
                "message": (
                    "Concentração não localizada para este princípio ativo nas listas consultadas."
                ),
            }
        matches = [m for m in strengths if m["form"] == "-" or _form_matches(query, m["form"])]
        if not matches and not any(
            normalize(m["form"]) in query for m in release.catalog if m["form"] != "-"
        ):
            return {
                "status": "ambiguous",
                "evidence": [],
                "message": "Informe a forma farmacêutica. Formas disponíveis: "
                + ", ".join(sorted({m["form"] for m in strengths}))
                + ".",
            }
        prolonged = "prolongada" in query
        delayed = "retardada" in query
        if prolonged and not any(
            "prolongada" in normalize(m.get("release_characteristic") or "") for m in matches
        ):
            return {
                "status": "not_in_scope",
                "evidence": [],
                "message": (
                    "Ação prolongada não documentada para esta apresentação na fonte solicitada."
                ),
            }
        if any(m.get("release_characteristic") for m in matches):
            explicit_regular = "convencional" in query or "imediata" in query
            if prolonged or delayed or explicit_regular:
                requested_characteristic = (
                    "prolongada" if prolonged else "retardada" if delayed else None
                )
                matches = [
                    m
                    for m in matches
                    if (
                        requested_characteristic in normalize(m.get("release_characteristic") or "")
                        if requested_characteristic
                        else not m.get("release_characteristic")
                    )
                ]
            elif len({m.get("release_characteristic") for m in matches}) > 1:
                return {
                    "status": "ambiguous",
                    "evidence": [],
                    "message": (
                        "Informe a característica de liberação: convencional ou ação prolongada. "
                        "Não são consideradas equivalentes."
                    ),
                }
        if matches:
            if (
                len({normalize(m["strength"]) for m in matches}) > 1
                and len({strength_core(m["strength"]) for m in matches}) == 1
            ):
                return {
                    "status": "ambiguous",
                    "evidence": [],
                    "message": "Há mais de um dispositivo documentado. Informe qual: "
                    + "; ".join(sorted({m["strength"] for m in matches}))
                    + ".",
                }
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
    if not names and not matches:
        if suggestion := name_suggestion(question, release.catalog):
            return {
                "status": "ambiguous",
                "evidence": [],
                "message": f"Você quis dizer {suggestion[0]}? Confirme o nome antes da consulta.",
                "suggested_question": suggestion[1],
            }
    if len(matches) != 1 and (
        not matches
        or len(
            {
                (
                    ingredient_key(m["active_ingredient"]),
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
    if strategy in {"vector", "hybrid"}:
        if store is None:
            raise ValueError(
                f"Estratégia '{strategy}' exige índice vetorial carregado (store); "
                "execute 'index' ou use 'lexical'/'exact'."
            )
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
    elif strategy == "exact":
        selected = sorted(
            selected,
            key=lambda c: (
                c["source"]["source_id"],
                c["source"]["page"],
                c["evidence_id"],
            ),
        )
    else:
        selected = lexical
    evidence_by_id = {e["evidence_id"]: e for e in release.evidence}
    sources = sorted({c["source"]["source_id"] for c in selected[:top_k]})
    return {
        "status": "matched",
        "medicine": med,
        "equivalent_medicine_ids": sorted(match_ids),
        "candidate_presentation_ids": sorted(match_ids),
        "candidate_chunk_count": len(selected),
        "ranked_chunk_ids": [c["chunk_id"] for c in selected[:top_k]],
        "evidence": [evidence_by_id[c["evidence_id"]] for c in selected[:top_k]],
        "message": (
            f"{med['active_ingredient']} {med['strength']} "
            f"({med['form'] if med['form'] != '-' else 'forma não informada'}"
            f"{'; ' + med['release_characteristic'] if med.get('release_characteristic') else ''}) "
            "consta nas fontes: "
            f"{', '.join(sources)}. Presença em lista não confirma estoque."
        ),
    }


def name_matches(query: str, name: str) -> bool:
    """Explicit ingredient alias; never infers therapeutic equivalence."""
    normalized = normalize(name)
    aliases = [normalized]
    if normalized in {"cloridrato de metformina", "metformina (cloridrato)"}:
        aliases.append("metformina")
    if any(re.search(r"(?<!\w)" + re.escape(alias) + r"(?!\w)", query) for alias in aliases):
        return True
    if " + " in normalized:
        components = normalized.split(" + ")
        pattern = r"(?<!\w)" + re.escape(components[0])
        for component in components[1:]:
            pattern += r"\s*(?:\([^)]*\)\s*)?\+\s*" + re.escape(component)
        if re.search(pattern + r"(?!\w)", query):
            return True
        dose = r"\s+\d+(?:[.,]\d+)?\s*(?:mg|mcg|g|ui)(?:/(?:ml|g))?"
        interleaved = r"(?<!\w)" + r"\s*\+\s*".join(
            re.escape(component) + dose for component in components
        )
        return bool(re.search(interleaved + r"(?!\w)", query))
    return False


def ingredient_key(name: str) -> str:
    normalized = normalize(name)
    return "cloridrato de metformina" if normalized == "metformina (cloridrato)" else normalized
