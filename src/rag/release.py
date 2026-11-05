"""Leitura auditável do release de engenharia de dados."""

from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any


def _rows(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


@dataclass(frozen=True)
class Release:
    folder: Path
    manifest: dict[str, Any]
    medicines: list[dict[str, Any]]
    evidence: list[dict[str, Any]]
    rules: list[dict[str, Any]]
    fingerprint: str

    @classmethod
    def load(cls, folder: Path) -> Release:
        folder = folder.expanduser().resolve()
        manifest_path = folder / "release.json"
        raw_manifest = manifest_path.read_bytes()
        manifest = json.loads(raw_manifest)
        if manifest.get("status") != "approved":
            raise ValueError("O release não está aprovado para indexação")
        review = manifest.get("review", {})
        review_path = folder.parents[2] / review.get("record_path", "")
        if (
            not review.get("reviewer")
            or not review.get("review_date")
            or not review_path.is_file()
            or sha256(review_path.read_bytes()).hexdigest() != review.get("record_sha256")
        ):
            raise ValueError("Registro de aprovação ausente ou divergente")
        files = manifest.get("files", {})
        names = ("medicamentos.jsonl", "evidencias.jsonl", "regras_acesso.jsonl")
        if set(files) != set(names):
            raise ValueError("Lista de arquivos do release incompleta")
        contents: dict[str, list[dict[str, Any]]] = {}
        for name in names:
            path = folder / name
            if sha256(path.read_bytes()).hexdigest() != files[name]["sha256"]:
                raise ValueError(f"Hash divergente: {name}")
            contents[name] = _rows(path)
            if len(contents[name]) != files[name]["records"]:
                raise ValueError(f"Contagem divergente: {name}")
            if any(row.get("review_status") != "approved" for row in contents[name]):
                raise ValueError(f"Registro não aprovado: {name}")
        medicines = contents["medicamentos.jsonl"]
        evidence = contents["evidencias.jsonl"]
        rules = contents["regras_acesso.jsonl"]
        ids = {e["evidence_id"] for e in evidence}
        if len(ids) != len(evidence):
            raise ValueError("IDs de evidência duplicados")
        for medicine in medicines:
            if any(item["evidence_id"] not in ids for item in medicine["lists"].values()):
                raise ValueError("Medicamento com evidência ausente")
        if any(rule["evidence_id"] not in ids for rule in rules):
            raise ValueError("Regra com evidência ausente")
        fingerprint_input = {
            "release_version": manifest["release_version"],
            "files": files,
            "review_sha256": review["record_sha256"],
        }
        fingerprint = sha256(json.dumps(fingerprint_input, sort_keys=True).encode()).hexdigest()
        return cls(folder, manifest, medicines, evidence, rules, fingerprint)
