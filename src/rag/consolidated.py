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
        base_sets = (expected, expected | {"audit_log.jsonl"})
        if not any(
            files == base or files == (base | NORMALIZED_RELEASE_FILES) for base in base_sets
        ):
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
        if NORMALIZED_RELEASE_FILES <= files:
            norm_bundle = json.loads((folder / "normalization.json").read_bytes())
            if not norm_bundle.get("schema_version") or "files" not in norm_bundle:
                raise ValueError("normalization.json inválido")
            for ev in evidence:
                occ = by_occ[ev["occurrence_id"]]
                if (
                    not isinstance(occ.get("normalized"), dict)
                    or ev.get("normalized") != occ["normalized"]
                ):
                    raise ValueError("Campos normalizados ausentes ou divergentes")
                if (
                    ev.get("component") != occ.get("component")
                    or ev.get("source_code") != occ.get("source_code")
                    or ev.get("atc") != occ.get("atc")
                    or ev.get("channel") != occ.get("channel")
                    or ev.get("channel_text") != occ["normalized"].get("channel_text")
                    or ev.get("channel_codes") != occ["normalized"].get("channel_codes")
                ):
                    raise ValueError("Campos de proveniência da evidência divergentes")
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
CHUNK_RECIPE_V3 = (
    "one-evidence-v3:normalized-fields;literal-spelling;F03-description-cell;F03-channel-code;"
    "F01-component-atc;F04-indication;source-provenance;no-old-chunks"
)
_SUPPORTED_CHUNK_RECIPES = {
    CHUNK_RECIPE_V1: digest(CHUNK_RECIPE_V1.encode()),
    CHUNK_RECIPE_V2: digest(CHUNK_RECIPE_V2.encode()),
    CHUNK_RECIPE_V3: digest(CHUNK_RECIPE_V3.encode()),
}
CHUNK_NOTE_MAX_CHARS = 200
NORMALIZED_RELEASE_FILES = frozenset({"normalization.json", "id_map_v9_v10.json"})


def default_chunk_recipe(release: ConsolidatedRelease) -> str:
    """v3 for releases carrying the normalization bundle; v2 otherwise."""
    return CHUNK_RECIPE_V3 if "normalization.json" in release.manifest["files"] else CHUNK_RECIPE_V2


def _provenance_line(ev: dict[str, Any]) -> str:
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
    return f"Proveniência: {src['source_id']} ({', '.join(loc_parts)})."


def _chunk_parts_v3(ev: dict[str, Any]) -> list[str]:
    norm = ev["normalized"]
    source_id = ev["source"]["source_id"]
    form = norm.get("form") or norm.get("package") or norm.get("specification") or "não informada"
    parts = [
        f"Tipo: {'insumo' if ev['item_type'] == 'supply' else 'medicamento'}",
        f"Princípio ativo ou item: {norm['active_ingredient']}",
    ]
    if normalize(ev["active_ingredient"]) != normalize(norm["active_ingredient"]):
        parts.append(f"Grafia na fonte: {ev['active_ingredient']}")
    parts.append(f"Concentração ou apresentação: {norm.get('strength') or 'não informada'}")
    parts.append(f"Forma: {form}")
    if norm.get("form") and norm.get("package"):
        parts.append(f"Embalagem: {norm['package']}")
    if norm.get("release"):
        parts.append(f"Liberação: {norm['release']}")
    if source_id == "F03":
        parts.append(f"Descrição na REME-DF: {ev['description_cell']}")
        if norm.get("channel_text"):
            parts.append(f"Onde é disponibilizado (REME-DF): {norm['channel_text']}")
        if norm.get("channel_notes"):
            note = "; ".join(norm["channel_notes"])
            if len(note) > CHUNK_NOTE_MAX_CHARS:
                note = note[: CHUNK_NOTE_MAX_CHARS - 1].rstrip() + "…"
            parts.append(f"Observação da fonte: {note}")
        if ev.get("source_code"):
            parts.append(f"Código REME-DF: {ev['source_code']}")
    if source_id == "F01":
        if ev.get("component"):
            parts.append(f"Componente RENAME: {ev['component']}")
        atc_codes = norm.get("atc", {}).get("codes") or []
        if atc_codes:
            parts.append(f"ATC: {', '.join(atc_codes)}")
    if source_id == "F04":
        parts.append(f"Indicação no elenco: {ev['indication']}")
    parts.append(f"Consta na lista {source_id} ({ev['source']['version']}).")
    parts.append(_provenance_line(ev))
    return parts


def chunk_for(
    ev: dict[str, Any], release_version: str, recipe: str = CHUNK_RECIPE_V1
) -> dict[str, Any]:
    if recipe == CHUNK_RECIPE_V3:
        chunk = _chunk_dict(ev, release_version, "\n".join(_chunk_parts_v3(ev)))
        chunk["channel_codes"] = list(ev["normalized"].get("channel_codes") or [])
        return chunk
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
        parts.append(_provenance_line(ev))
    elif recipe != CHUNK_RECIPE_V1:
        raise ValueError(f"Receita de chunk desconhecida: {recipe}")
    return _chunk_dict(ev, release_version, "\n".join(parts))


def _chunk_dict(ev: dict[str, Any], release_version: str, text: str) -> dict[str, Any]:
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
    release: ConsolidatedRelease, output: Path, recipe: str | None = None
) -> dict[str, Any]:
    recipe = recipe or default_chunk_recipe(release)
    if recipe not in _SUPPORTED_CHUNK_RECIPES:
        raise ValueError(f"Receita de chunk desconhecida: {recipe}")
    chunks = [
        chunk_for(e, release.manifest["release_version"], recipe=recipe) for e in release.evidence
    ]
    has_dup_texts = recipe in (CHUNK_RECIPE_V2, CHUNK_RECIPE_V3) and len(
        {c["text"] for c in chunks}
    ) != len(chunks)
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


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKD", value.casefold())
    value = "".join(c for c in value if not unicodedata.combining(c))
    value = re.sub(r"(?<=\d)\s*(?=(?:mcg|mg|g|ml|meq|ui|u|l)\b|%)", " ", value)
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


def is_form_absent(item: dict[str, Any]) -> bool:
    """True only when the source declares neither form nor package/specification."""
    return item.get("form") == "-" and not item.get("package") and not item.get("specification")


def item_form_label(item: dict[str, Any]) -> str:
    """Best single label for matching and length comparison across v5-v10 schemas."""
    form = item.get("form")
    if form not in (None, "", "-"):
        return str(form)
    return str(item.get("package") or item.get("specification") or "-")


def item_form_display(item: dict[str, Any]) -> str:
    """Human-readable form/package label preserving legacy text when no package exists."""
    form = item.get("form")
    package = item.get("package")
    specification = item.get("specification")
    if form not in (None, "", "-"):
        return f"{form} ({package})" if package else str(form)
    if package:
        return str(package)
    if specification:
        return str(specification)
    return "forma não informada"


def item_name_matches(query: str, item: dict[str, Any]) -> bool:
    if name_matches(query, item["active_ingredient"]):
        return True
    return any(name_matches(query, alias) for alias in item.get("aliases") or ())


def _package_matches(query: str, package: str) -> bool:
    q_norm = re.sub(r"\s*-\s*", " ", normalize(query))
    p_norm = re.sub(r"\s*-\s*", " ", normalize(package))
    candidates = [p_norm]
    if " ou " in p_norm:
        candidates.extend(part.strip() for part in p_norm.split(" ou ") if part.strip())
    return any(re.search(r"(?<!\w)" + re.escape(cand) + r"(?!\w)", q_norm) for cand in candidates)


def _presentation_form_matches(query: str, item: dict[str, Any]) -> bool:
    if is_form_absent(item):
        return True
    form = item.get("form")
    package = item.get("package")
    specification = item.get("specification")
    if form not in (None, "", "-"):
        matched = _form_matches(query, str(form)) or any(
            _form_matches(query, lit) for lit in item.get("literal_forms") or ()
        )
        if not matched:
            return False
        if (
            package
            and item.get("strength") == "-"
            and re.fullmatch(r"\d+(?:,\d+)?\s*m?l", str(package), re.I)
        ):
            return _package_matches(query, str(package))
        return True
    if package:
        return _package_matches(query, str(package))
    if specification:
        return _textual_presentation(str(specification)) in _textual_presentation(query)
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
    if any(item_name_matches(query, m) for m in catalog):
        return None
    names: dict[str, str] = {}
    for m in catalog:
        for candidate in (m["active_ingredient"], *(m.get("aliases") or ())):
            norm = normalize(candidate)
            if re.fullmatch(r"[a-z]{6,}", norm):
                names.setdefault(norm, candidate)
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
    "minha dose diaria",
    "sua dose diaria",
    "dose diaria maxima",
    "dose diaria minima",
    "dose diaria recomendada",
    "dose diaria indicada",
    "dose diaria segura",
    "dose diaria ideal",
    "dose maxima",
    "dose minima recomendada",
    "dose minima eficaz",
    "dose minima efetiva",
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
    re.compile(
        r"\b(?:tomar|usar|prescrever|indicar|recomendar|aumentar|diminuir|"
        r"dobrar|reduzir|alterar|exceder)\b.{0,25}\bdose (?:diaria|minima)\b"
    ),
    re.compile(r"(?<!\()\bdose diaria\s+(?:de|para)\b"),
    re.compile(r"\bdose minima\b(?!\s+(?:mortal|necrosante)\b)"),
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


def matches_clinical_guardrail(question: str, release: ConsolidatedRelease | None = None) -> bool:
    """Detect out-of-scope clinical, dosing, pregnancy, or eligibility queries via lexical rules."""
    query = normalize(question)
    if release and "(dose diaria)" in query:
        listing = re.fullmatch(r"na (rename|reme-df), ha registro de (.+)\?", query)
        if listing:
            source_id = {"rename": "F01", "reme-df": "F03"}[listing[1]]
            for item in release.catalog:
                if source_id not in item["source_ids"]:
                    continue
                forms = [item["form"], *(item.get("literal_forms") or ())]
                if item.get("release_characteristic") and item["form"] != "-":
                    forms.extend(
                        [
                            f"{item['form']} de {item['release_characteristic']}",
                            f"{item['form']} {item['release_characteristic']}",
                        ]
                    )
                if any(
                    listing[2] == normalize(f"{name} {item['strength']} {form}")
                    for name in (item["active_ingredient"], *(item.get("aliases") or ()))
                    for form in forms
                ):
                    return False
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


def matches_documental_scope_block(
    question: str, release: ConsolidatedRelease | None = None
) -> bool:
    """Detect queries outside the frozen list-presence scope (clinical, stock, or documents)."""
    query = normalize(question)
    if matches_clinical_guardrail(query, release):
        return True
    return any(
        re.search(r"\b" + re.escape(term) + r"\b", query) for term in DOCUMENTAL_ONLY_BLOCKED_TERMS
    )


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
    if matches_documental_scope_block(query, release) or matches_prompt_injection(question):
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
        if item_name_matches(query, m) and (not source_filter or source_filter in m["source_ids"])
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
            or any(
                strength_matches(query, m["strength"], candidate)
                for candidate in (m["active_ingredient"], *(m.get("aliases") or ()))
            )
        ]
        if not strengths:
            if not re.search(r"\d+(?:[.,]\d+)?\s*(?:mg|mcg|g|ui|ml)\b", query):
                options = sorted(
                    names,
                    key=lambda m: (
                        normalize(m["strength"]),
                        normalize(item_form_label(m)),
                        normalize(m.get("release_characteristic") or ""),
                        m["medicine_id"],
                    ),
                )
                refs: dict[str, list[str]] = {m["medicine_id"]: [] for m in options}
                cited = []
                for ev in release.evidence:
                    source = ev["source"]
                    mid = ev["medicine_id"]
                    if mid in refs and (not source_filter or source["source_id"] == source_filter):
                        refs[mid].append(
                            f"{source['source_id']} ({source['version']}), "
                            f"página {source['page']} [{ev['evidence_id']}]"
                        )
                        cited.append(ev)
                return {
                    "status": "ambiguous",
                    "evidence": cited,
                    "candidate_presentations": options,
                    "message": "Apresentações documentadas: "
                    + "; ".join(
                        f"{m['strength']} — {item_form_display(m)}"
                        + (
                            f" — {m['release_characteristic']}"
                            if m.get("release_characteristic")
                            else ""
                        )
                        + f" ({'; '.join(refs[m['medicine_id']])})"
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
        matches = [m for m in strengths if _presentation_form_matches(query, m)]
        missing_volume = not matches and any(
            m["form"] != "-"
            and m.get("package")
            and m["strength"] == "-"
            and _form_matches(query, m["form"])
            for m in strengths
        )
        known_form_mentioned = any(
            normalize(lbl) in query
            for m in release.catalog
            if not is_form_absent(m)
            for lbl in (item_form_label(m), *(m.get("literal_forms") or ()))
        )
        if not matches and (missing_volume or not known_form_mentioned):
            return {
                "status": "ambiguous",
                "evidence": [],
                "message": "Informe a forma farmacêutica. Formas disponíveis: "
                + ", ".join(sorted({item_form_display(m) for m in strengths}))
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
                len(normalize(item_form_label(m))) if not is_form_absent(m) else 0 for m in matches
            )
            matches = [
                m
                for m in matches
                if (len(normalize(item_form_label(m))) if not is_form_absent(m) else 0)
                == longest_form
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
                    normalize(item_form_label(m)),
                    normalize(m.get("package") or ""),
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
        allowed = {c["chunk_id"] for c in selected}
        vec_k = min(max(top_k * 3, 10), len(selected))
        ranks = _vector_ranks(question, store, match_ids, allowed, vec_k)
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
            f"({item_form_display(med)}"
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
