"""Validate Jhiovana's XLSX review before opening the frozen v7 test split."""

from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from hashlib import sha256
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[4]
DATASET = ROOT / "evals/datasets/consolidated_v7_agent_reviewed.jsonl"
WORKBOOK = ROOT / "docs/reports/v7/v7-retrieval-review.xlsx"
NS = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
COLUMNS = [
    "case_id",
    "split",
    "source_id",
    "family_id",
    "question",
    "expected_status",
    "expected_evidence_ids",
    "active_ingredient",
    "strength",
    "form",
    "release_characteristic",
    "page",
    "source_version",
    "migration_note",
    "decision",
    "corrected_status",
    "corrected_evidence_ids",
    "reviewer",
    "review_date",
    "notes",
]


def read_sheet(path: Path) -> list[dict[str, str]]:
    with ZipFile(path) as archive:
        strings = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            strings = ["".join(t.text or "" for t in si.findall(".//x:t", NS)) for si in root]
        root = ET.fromstring(archive.read("xl/worksheets/sheet1.xml"))
    output = []
    for row in root.findall(".//x:sheetData/x:row", NS):
        values = {}
        for cell in row.findall("x:c", NS):
            column = re.match(r"[A-Z]+", cell.attrib["r"])
            if column is None:
                continue
            value = cell.find("x:v", NS)
            inline = cell.find("x:is", NS)
            text = value.text if value is not None and value.text is not None else ""
            if cell.attrib.get("t") == "s" and text:
                text = strings[int(text)]
            elif cell.attrib.get("t") == "inlineStr" and inline is not None:
                text = "".join(t.text or "" for t in inline.findall(".//x:t", NS))
            values[column.group()] = text
        output.append(values)
    if not output or [output[0].get(_column(i)) for i in range(len(COLUMNS))] != COLUMNS:
        raise ValueError("Cabeçalhos da planilha divergentes")
    return [{name: row.get(_column(i), "") for i, name in enumerate(COLUMNS)} for row in output[1:]]


def _column(index: int) -> str:
    name = ""
    while index >= 0:
        name = chr(65 + index % 26) + name
        index = index // 26 - 1
    return name


def validate(path: Path = WORKBOOK, dataset: Path = DATASET) -> dict:
    cases = [json.loads(line) for line in dataset.read_text(encoding="utf-8").splitlines() if line]
    rows = read_sheet(path)
    if len(cases) != 119 or len(rows) != len(cases):
        raise ValueError("A revisão deve conter as 119 linhas do conjunto v7")
    errors = []
    approved = 0
    for case, row in zip(cases, rows, strict=True):
        ref = case["expected_references"][0] if case["expected_references"] else {}
        immutable = {
            "case_id": case["id"],
            "split": case["split"],
            "source_id": case.get("source_id") or "",
            "family_id": case["family_id"],
            "question": case["question"],
            "expected_status": case["expected_status"],
            "expected_evidence_ids": "; ".join(case["relevant_ids"]),
            "active_ingredient": ref.get("active_ingredient") or "",
            "strength": ref.get("strength") or "",
            "form": ref.get("form") or "",
            "release_characteristic": ref.get("release_characteristic") or "",
            "page": str(ref.get("page") or ""),
            "source_version": ref.get("source_version") or "",
            "migration_note": case.get("migration_note") or "",
        }
        for field, expected in immutable.items():
            if row[field] != expected:
                errors.append(f"{case['id']}: campo protegido alterado: {field}")
        decision = row["decision"].strip().lower()
        if decision not in {"aprovar", "rejeitar"}:
            errors.append(f"{case['id']}: decisão ausente ou inválida")
        elif decision == "rejeitar":
            errors.append(f"{case['id']}: rejeitado; corrigir caso e emitir nova planilha")
        else:
            approved += 1
        if row["reviewer"].strip().casefold() != "jhiovana":
            errors.append(f"{case['id']}: reviewer deve ser Jhiovana")
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", row["review_date"].strip()):
            errors.append(f"{case['id']}: review_date deve ser AAAA-MM-DD")
        if decision == "rejeitar" and not row["notes"].strip():
            errors.append(f"{case['id']}: rejeição precisa de justificativa")
    return {
        "cases": len(cases),
        "approved": approved,
        "errors": errors,
        "dataset_sha256": sha256(dataset.read_bytes()).hexdigest(),
        "review_sha256": sha256(path.read_bytes()).hexdigest(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review", type=Path, default=WORKBOOK)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = validate(args.review)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["errors"]:
        return 1
    if args.output:
        cases = [json.loads(x) for x in DATASET.read_text(encoding="utf-8").splitlines() if x]
        for case in cases:
            case["review_status"] = "reviewed"
            case["reviewer"] = "Jhiovana"
            case["review_reference_sha256"] = result["review_sha256"]
        args.output.write_text(
            "".join(json.dumps(c, ensure_ascii=False, sort_keys=True) + "\n" for c in cases),
            encoding="utf-8",
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
