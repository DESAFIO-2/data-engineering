"""Construção determinística e verificação de chunks versionados (receitas v1/v2/v3)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .matching import normalize
from .release import ConsolidatedRelease, digest, json_bytes, jsonl_bytes, rows

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
