"""Freeze validated occurrences and derive reviewable evidence without old chunks."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "corpus-consolidado-v4-revisao-2026-11-10"
FILES = ("catalog.jsonl", "occurrences.jsonl", "evidencias.jsonl", "exclusions.jsonl", "f03_descriptions.json", "quality_report.json")
BLANK_OID = "occ-dd3666cce6867d6246aae72f"


def digest(data: bytes) -> str:
    return sha256(data).hexdigest()


def encoded(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()


def lines(rows: list[dict]) -> bytes:
    return b"".join(json.dumps(row, ensure_ascii=False, sort_keys=True).encode() + b"\n" for row in rows)


def read_lines(data: bytes) -> list[dict]:
    return [json.loads(line) for line in data.splitlines() if line.strip()]


def required(value: object, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Campo obrigatório vazio: {label}")


def evidence_for(occ: dict, descriptions: dict | None = None) -> dict:
    oid = occ["occurrence_id"]
    source = occ["source"]
    for key in ("source_id", "version", "url", "sha256"):
        required(source.get(key), f"{oid}.source.{key}")
    if not isinstance(source.get("page"), int) or source["page"] < 1:
        raise ValueError(f"Página inválida: {oid}")
    required(occ.get("raw_text"), f"{oid}.raw_text")
    for key in ("active_ingredient", "strength", "form"):
        required(occ.get(key), f"{oid}.{key}")
    if occ.get("review_status") != "approved" or occ.get("uncertainties"):
        raise ValueError(f"Ocorrência pendente: {oid}")
    evidence = {
        "evidence_id": "evidence-" + oid.removeprefix("occ-"),
        "occurrence_id": oid,
        "medicine_id": occ.get("medicine_id"),
        "item_type": occ["item_type"],
        "text": occ["raw_text"],
        "source": source,
        "source_row_number": occ.get("source_row_number"),
        "line_start": occ.get("line_start"),
        "line_end": occ.get("line_end"),
        "active_ingredient": occ["active_ingredient"],
        "strength": occ["strength"],
        "form": occ["form"],
        "release_characteristic": occ.get("release_characteristic"),
        "review_status": "pending_review",
    }
    if descriptions is not None:
        if occ["item_type"] == "supply":
            evidence["supply_id"] = occ["supply_id"]
        if source["source_id"] == "F03":
            detail = descriptions.get(oid)
            if not detail or not detail["description"].strip() or detail["page"] != source["page"] or detail["source_row_number"] != occ["source_row_number"] or detail["pdf_sha256"] != source["sha256"]:
                raise ValueError(f"Descrição da célula F03 ausente/divergente: {oid}")
            evidence["description_cell"] = detail["description"]
            evidence["description_provenance"] = {
                "column": detail["column"], "x0": detail["x0"], "x1": detail["x1"]
            }
        if source["source_id"] == "F04":
            indication = occ.get("context", {}).get("indication")
            if not isinstance(indication, str) or not indication.strip():
                raise ValueError(f"Indicação F04 ausente: {oid}")
            evidence["indication"] = indication
    return evidence


def unique(rows: list[dict], field: str) -> set[str]:
    values = [row[field] for row in rows]
    if len(values) != len(set(values)):
        raise ValueError(f"IDs duplicados: {field}")
    return set(values)


def prepare(root: Path) -> tuple[dict[str, bytes], dict]:
    corpus = root / "data/corpus"
    original = (corpus / "manifest.json").read_bytes()
    source_manifest = json.loads(original)
    source_payload = {}
    for name, metadata in source_manifest["files"].items():
        data = (corpus / name).read_bytes()
        if digest(data) != metadata["sha256"] or len(data) != metadata["bytes"]:
            raise ValueError(f"Hash/tamanho do corpus divergente: {name}")
        if "records" in metadata and len(read_lines(data)) != metadata["records"]:
            raise ValueError(f"Contagem do corpus divergente: {name}")
        source_payload[name] = data
    catalog = read_lines(source_payload["catalog.jsonl"])
    all_occurrences = read_lines(source_payload["occurrences.jsonl"])
    exclusions = [o for o in all_occurrences if o.get("item_type") == "source_blank"]
    if len(exclusions) != 1 or exclusions[0]["occurrence_id"] != BLANK_OID:
        raise ValueError("Registro da linha vazia F03 inesperado")
    occurrences = [o for o in all_occurrences if o.get("item_type") != "source_blank"]
    medicine_ids = unique(catalog, "medicine_id")
    occurrence_ids = unique(occurrences, "occurrence_id")
    occurrence_by_id = {o["occurrence_id"]: o for o in occurrences}
    references = set()
    for med in catalog:
        if med.get("review_status") != "approved" or not med.get("occurrence_ids"):
            raise ValueError(f"Apresentação sem revisão ou ocorrência: {med['medicine_id']}")
        if len(med["occurrence_ids"]) != len(set(med["occurrence_ids"])):
            raise ValueError(f"Ocorrência duplicada na apresentação: {med['medicine_id']}")
        for oid in med["occurrence_ids"]:
            if oid not in occurrence_by_id or occurrence_by_id[oid].get("medicine_id") != med["medicine_id"]:
                raise ValueError(f"Vínculo incorreto: {med['medicine_id']} / {oid}")
        references.update(med["occurrence_ids"])
    if references != {o["occurrence_id"] for o in occurrences if o.get("medicine_id")}:
        raise ValueError("Vínculos catálogo/ocorrências divergentes")
    for occ in occurrences:
        if occ.get("medicine_id") is not None and occ["medicine_id"] not in medicine_ids:
            raise ValueError(f"Medicamento ausente: {occ['occurrence_id']}")
        if occ.get("medicine_id") is None and occ.get("item_type") != "supply":
            raise ValueError(f"Medicamento sem ID: {occ['occurrence_id']}")
        if occ["item_type"] == "supply" and (occ.get("medicine_id") is not None or not occ.get("supply_id")):
            raise ValueError(f"Insumo sem identificador próprio: {occ['occurrence_id']}")
    descriptions_path = root / "data/curation/f03-descricoes-coluna-pdf.json"
    descriptions_bytes = descriptions_path.read_bytes()
    descriptions = json.loads(descriptions_bytes)
    if set(descriptions) != {o["occurrence_id"] for o in all_occurrences if o["source"]["source_id"] == "F03"}:
        raise ValueError("Recorte da coluna F03 incompleto")
    evidence = [evidence_for(occ, descriptions) for occ in occurrences]
    unique(evidence, "evidence_id")
    assert len(occurrence_ids) == len(evidence)
    collected = json.loads((root / "data/manifests/coleta-inicial-pdfs-2026-11-03.json").read_bytes())
    sources = {}
    for record in collected["sources"]:
        sid = record["source_id"]
        if sid not in {"F01", "F03", "F04"}:
            continue
        raw = root / "data" / record["path"]
        if digest(raw.read_bytes()) != record["sha256"]:
            raise ValueError(f"PDF original alterado: {sid}")
        sources[sid] = {"path": record["path"], "sha256": record["sha256"], "pages": record["pages"]}
    if set(sources) != {"F01", "F03", "F04"}:
        raise ValueError("Fontes originais incompletas")
    for occ in occurrences:
        src = occ["source"]
        sid = src["source_id"]
        if sid not in sources or src["sha256"] != sources[sid]["sha256"] or src["page"] > sources[sid]["pages"]:
            raise ValueError(f"Proveniência divergente: {occ['occurrence_id']}")
    by_source = Counter(o["source"]["source_id"] for o in occurrences)
    by_type = Counter(o["item_type"] for o in occurrences)
    quality = {
        "catalog_presentations": len(catalog),
        "occurrences": len(occurrences),
        "evidence": len(evidence),
        "occurrences_by_source": dict(sorted(by_source.items())),
        "occurrences_by_type": dict(sorted(by_type.items())),
        "supplies": sum(o["item_type"] == "supply" for o in occurrences),
        "excluded_source_rows": len(exclusions),
        "validation": "IDs, campos obrigatórios, vínculos, proveniência e hashes conferidos",
        "limitations": [
            "Evidências derivadas de ocorrências estruturadas; revisão das evidências do release pendente.",
            "Chunks antigos e 108 chunks complementares não incluídos.",
            "A linha 987 da F03 foi preservada apenas no registro de exclusões.",
            "Presença em lista não comprova estoque, elegibilidade ou dispensação em unidade específica.",
        ],
    }
    payload = {
        "catalog.jsonl": source_payload["catalog.jsonl"],
        "occurrences.jsonl": lines(occurrences),
        "evidencias.jsonl": lines(evidence),
        "exclusions.jsonl": lines([{
            "occurrence_id": row["occurrence_id"], "source": row["source"],
            "source_row_number": row["source_row_number"], "raw_text": row["raw_text"],
            "reason": "Linha numerada sem item na célula DESCRIÇÃO; excluída da publicação",
        } for row in exclusions]),
        "f03_descriptions.json": descriptions_bytes,
        "quality_report.json": encoded(quality),
    }
    manifest = {
        "schema_version": "consolidated-release-v2",
        "release_version": VERSION,
        "status": "pending_review",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "corpus_fingerprint": json.loads((corpus / "report.json").read_bytes())["corpus_fingerprint"],
        "input_manifest_sha256": digest(original),
        "f03_description_extract_sha256": digest(descriptions_bytes),
        "supply_type_review": {
            "path": "data/curation/revisao-tipo-itens-f01-v4.json",
            "sha256": digest((root / "data/curation/revisao-tipo-itens-f01-v4.json").read_bytes()),
        },
        "review_reference": {
            "path": "data/corpus/review-log.jsonl",
            "sha256": source_manifest["files"]["review-log.jsonl"]["sha256"],
            "scope": "revisão das ocorrências; evidências deste release aguardam revisão",
        },
        "sources": sources,
        "files": {
            name: {
                "sha256": digest(data),
                "bytes": len(data),
                **({"records": len(read_lines(data))} if name.endswith(".jsonl") else {}),
            }
            for name, data in payload.items()
        },
    }
    return payload, manifest


def verify(folder: Path) -> dict:
    manifest = json.loads((folder / "release.json").read_bytes())
    schema = manifest.get("schema_version")
    expected = set(FILES if schema == "consolidated-release-v2" else ("catalog.jsonl", "occurrences.jsonl", "evidencias.jsonl", "quality_report.json"))
    if manifest.get("status") == "approved":
        expected.add("domain_review.json")
    if "audit_log.jsonl" in manifest.get("files", {}):
        expected.add("audit_log.jsonl")
    if schema not in {"consolidated-release-v1", "consolidated-release-v2"} or set(manifest["files"]) != expected:
        raise ValueError("Manifesto inválido")
    if manifest.get("status") not in {"pending_review", "approved"}:
        raise ValueError("Status de release inválido")
    for name, metadata in manifest["files"].items():
        data = (folder / name).read_bytes()
        if digest(data) != metadata["sha256"] or len(data) != metadata["bytes"]:
            raise ValueError(f"Arquivo alterado: {name}")
        if name.endswith(".jsonl") and len(read_lines(data)) != metadata["records"]:
            raise ValueError(f"Contagem divergente: {name}")
    occurrences = read_lines((folder / "occurrences.jsonl").read_bytes())
    evidence = read_lines((folder / "evidencias.jsonl").read_bytes())
    if schema == "consolidated-release-v2":
        descriptions_bytes = (folder / "f03_descriptions.json").read_bytes()
        if digest(descriptions_bytes) != manifest.get("f03_description_extract_sha256"):
            raise ValueError("Recorte F03 alterado após publicação")
        descriptions = json.loads(descriptions_bytes)
        exclusions = read_lines((folder / "exclusions.jsonl").read_bytes())
        if len(exclusions) != 1 or exclusions[0]["occurrence_id"] != BLANK_OID or any(o["occurrence_id"] == BLANK_OID for o in occurrences):
            raise ValueError("Exclusão da linha vazia F03 divergente")
        expected_evidence = [evidence_for(occ, descriptions) for occ in occurrences]
    else:
        expected_evidence = [evidence_for(occ) for occ in occurrences]
    if manifest["status"] == "approved":
        review = json.loads((folder / "domain_review.json").read_bytes())
        if (
            review.get("decision") != "approved"
            or review.get("release_version") != manifest.get("release_version")
            or review.get("reviewer_role") != "responsável pelo projeto"
            or not review.get("date")
            or not review.get("scope")
            or review.get("evidence_sha256") != manifest["files"]["evidencias.jsonl"]["sha256"]
            or not manifest.get("approval_scope")
        ):
            raise ValueError("Aprovação de domínio ausente ou divergente")
        for row in expected_evidence:
            row["review_status"] = "approved"
    if evidence != expected_evidence:
        raise ValueError("Evidências não correspondem às ocorrências")
    return manifest


def publish(root: Path, output: Path, release_version: str | None = None) -> dict:
    payload, manifest = prepare(root)
    manifest["release_version"] = release_version or output.name
    output.mkdir(parents=False, exist_ok=False)
    for name, data in payload.items():
        (output / name).write_bytes(data)
    (output / "release.json").write_bytes(encoded(manifest))
    verify(output)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / "data/releases" / VERSION)
    parser.add_argument("--release-version", type=str, default=None)
    args = parser.parse_args()
    result = verify(args.verify) if args.verify else publish(ROOT, args.output, args.release_version)
    print(json.dumps({"release_version": result["release_version"], "status": result["status"], "files": result["files"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
