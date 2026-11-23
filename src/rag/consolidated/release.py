"""Carregamento e validação de integridade de releases consolidados aprovados."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

NORMALIZED_RELEASE_FILES = frozenset({"normalization.json", "id_map_v9_v10.json"})


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
