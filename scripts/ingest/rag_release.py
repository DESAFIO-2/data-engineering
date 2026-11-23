"""Publica um lote pequeno e auditável para busca tabular e recuperação RAG."""

from __future__ import annotations

import json
import re
from collections import Counter
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
VERSION = "rag-lote-1-aprovado-2026-11-05"
SOURCE_VERSIONS = {
    "F01": "RENAME 2024, 2ª edição",
    "F03": "REME-DF 29/10/2026",
    "F04": "Farmácia Popular 31/08/2026",
}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
        newline="\n",
    )


def _fingerprint(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()[:16]


def _source_ref(source: dict[str, Any], page: int) -> dict[str, Any]:
    return {
        "source_id": source["source_id"],
        "version": SOURCE_VERSIONS[source["source_id"]],
        "url": source["source_url"],
        "sha256": source["sha256"],
        "page": page,
    }


def build_release(root: Path = ROOT) -> dict[str, Any]:
    manifest = json.loads(
        (root / "data/manifests/coleta-inicial-pdfs-2026-11-03.json").read_text(encoding="utf-8")
    )
    curation = json.loads((root / "data/curation/rag_lote_1.json").read_text(encoding="utf-8"))
    review_path = root / "data/curation/rag_lote_1_review.json"
    review_bytes = review_path.read_bytes().replace(b"\r\n", b"\n")
    review = json.loads(review_bytes)
    sources = {s["source_id"]: s for s in manifest["sources"] if s["source_id"] in SOURCE_VERSIONS}
    identities = {f"{item['name']}|{item['strength']}|{item['form']}" for item in curation["items"]}
    channel_identities = {
        f"{item['name']}|{item['strength']}|{item['form']}|{item['channel']}"
        for item in curation["items"]
    }
    if (
        review.get("decision") != "approved"
        or not review.get("reviewer")
        or not review.get("review_date")
        or review.get("reservations") != []
        or set(review.get("approved_medicines", [])) != identities
        or set(review.get("approved_channels", [])) != channel_identities
        or len(review.get("approved_medicines", [])) != len(identities)
        or len(review.get("approved_channels", [])) != len(channel_identities)
        or review.get("source_hashes") != {sid: source["sha256"] for sid, source in sources.items()}
    ):
        raise ValueError(
            "A revisão humana não aprova exatamente a curadoria e as fontes deste lote"
        )
    pages: dict[str, dict[int, str]] = {}
    for source_id, source in sources.items():
        raw = root / "data" / source["path"]
        if sha256(raw.read_bytes()).hexdigest() != source["sha256"]:
            raise ValueError(f"Hash do original divergente: {source_id}")
        silver = root / "data/silver" / source_id / f"{source['sha256']}.jsonl"
        records = _read_jsonl(silver)
        if len(records) != source["pages"] or any(
            r["content_sha256"] != source["sha256"] for r in records
        ):
            raise ValueError(f"Silver incompatível com o manifesto: {source_id}")
        pages[source_id] = {r["page"]: r["text"] for r in records}

    medicines: list[dict[str, Any]] = []
    evidence: list[dict[str, Any]] = []
    rules: list[dict[str, Any]] = []
    for item in curation["items"]:
        name, strength, form = item["name"], item["strength"], item["form"]
        identity = f"{name}|{strength}|{form}"
        mid = "med-" + _fingerprint(identity)
        checks = [
            ("F04", 1, item["f04"]),
            ("F01", item["f01_page"], item["f01"]),
            ("F03", item["f03_page"], item["f03"]),
        ]
        refs = []
        for sid, page, excerpt in checks:
            source_text = pages[sid][page]
            if excerpt not in source_text or (
                sid == "F01" and item.get("f01_context") and item["f01_context"] not in source_text
            ):
                raise ValueError(f"Trecho não encontrado: {identity} {sid} página {page}")
            if sid == "F03":
                row_match = re.search(
                    rf"(?m)^\d+\.\s+{re.escape(item['f03_code'])}\s+", source_text
                )
                if (
                    row_match is None
                    or source_text.find(excerpt, row_match.start()) > row_match.start() + 150
                ):
                    raise ValueError(f"Código REME não corresponde à linha: {identity}")
                next_row = re.search(r"(?m)^\d+\.\s+\S+", source_text[row_match.end() :])
                end = row_match.end() + next_row.start() if next_row else len(source_text)
                row_text = " ".join(source_text[row_match.start() : end].split())
                if item["channel"] not in row_text:
                    raise ValueError(f"Canal não comprovado na linha REME: {identity}")
                text = row_text
            elif sid == "F01":
                text = f"{name}: {excerpt}"
            else:
                text = f"Elenco Farmácia Popular: {excerpt}"
            eid = "ev-" + _fingerprint(f"{sid}|{page}|{identity}")
            evidence.append(
                {
                    "evidence_id": eid,
                    "medicine_id": mid,
                    "topic": "medicamento_em_lista"
                    if sid != "F03"
                    else "medicamento_e_canal_na_reme",
                    "text": text,
                    "territory": "Brasil" if sid != "F03" else "Distrito Federal",
                    "service": "Farmácia Popular"
                    if sid == "F04"
                    else ("SES-DF" if sid == "F03" else "RENAME"),
                    "source": _source_ref(sources[sid], page),
                    "review_status": "approved",
                }
            )
            refs.append(eid)
        medicines.append(
            {
                "medicine_id": mid,
                "active_ingredient": name,
                "aliases": [item["alias_f03"]] if item.get("alias_f03") else [],
                "strength": strength,
                "form": form,
                "release_type": "não informada",
                "stock_status": "não consultado",
                "lists": {
                    sid: {
                        "status": "consta_na_versao_consultada",
                        "evidence_id": eid,
                        "version": SOURCE_VERSIONS[sid],
                    }
                    for sid, eid in zip(("F04", "F01", "F03"), refs, strict=True)
                },
                "review_status": "approved",
            }
        )
        rules.append(
            {
                "rule_id": "rule-" + _fingerprint(identity + "|UBS"),
                "medicine_id": mid,
                "channel": item["channel"],
                "claim": (
                    f"A apresentação {name} {strength} {form} consta na REME-DF "
                    f"com canal {item['channel']}."
                ),
                "required_documents": "não verificados",
                "eligibility": "não verificada",
                "stock_status": "não consultado",
                "evidence_id": refs[2],
                "review_status": "approved",
            }
        )

    output = root / "data/releases" / VERSION
    output.mkdir(parents=True, exist_ok=True)
    files = {
        "medicamentos.jsonl": medicines,
        "evidencias.jsonl": evidence,
        "regras_acesso.jsonl": rules,
    }
    for filename, rows in files.items():
        _write_jsonl(output / filename, rows)
    file_info = {
        name: {
            "sha256": sha256((output / name).read_bytes().replace(b"\r\n", b"\n")).hexdigest(),
            "records": len(rows),
        }
        for name, rows in files.items()
    }
    quality = {
        "release_version": VERSION,
        "review_method": curation["review_method"],
        "f04_lines_with_dose_or_strength": sum(
            bool(re.search(r"\d\s*(?:mg|mcg|ui)", line, re.IGNORECASE))
            for line in pages["F04"][1].splitlines()
        ),
        "f04_lines_not_in_release": sum(
            bool(re.search(r"\d\s*(?:mg|mcg|ui)", line, re.IGNORECASE))
            for line in pages["F04"][1].splitlines()
        )
        - len(medicines),
        "f04_non_medicine_supplies_not_in_release": 2,
        "technical_verified_medicines": len(medicines),
        "evidence_by_source": dict(
            sorted(Counter(e["source"]["source_id"] for e in evidence).items())
        ),
        "human_domain_review": "approved",
        "reviewer": review["reviewer"],
        "review_date": review["review_date"],
        "review_record": "data/curation/rag_lote_1_review.json",
        "review_record_sha256": sha256(review_bytes).hexdigest(),
        "pending_scope": [
            "Demais linhas do Farmácia Popular",
            "Regras documentais F05-F09",
            "Nomes comerciais",
            "Preparo de exames",
            "Estoque e unidades específicas",
        ],
        "rejected_records": 0,
        "excluded_sources": [
            "F11: dicionário, não cadastro de medicamentos",
            "F12: sem preparo específico aprovado",
            "SISREG: fonte não coletada neste repositório",
        ],
    }
    (output / "quality_report.json").write_text(
        json.dumps(quality, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    release = {
        "release_version": VERSION,
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "status": "approved",
        "review": {
            "reviewer": review["reviewer"],
            "review_date": review["review_date"],
            "record_path": "data/curation/rag_lote_1_review.json",
            "record_sha256": sha256(review_bytes).hexdigest(),
            "scope": "Seis medicamentos e seis vínculos de canal",
        },
        "files": file_info,
        "sources": [
            {
                key: value
                for key, value in (
                    _source_ref(sources[sid], 1) | {"raw_path": sources[sid]["path"]}
                ).items()
                if key != "page"
            }
            for sid in sorted(sources)
        ],
        "quality_report": "quality_report.json",
        "coverage": (
            "Seis apresentações verificadas nas edições F01, F03 e F04; "
            "não cobre estoque, documentos, elegibilidade ou exames."
        ),
    }
    (output / "release.json").write_text(
        json.dumps(release, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return release


if __name__ == "__main__":
    print(json.dumps(build_release(), ensure_ascii=False, indent=2))
