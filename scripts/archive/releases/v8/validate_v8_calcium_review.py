"""Validate the single changed v8 case while carrying unchanged v7 human decisions."""

from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
from datetime import date
from hashlib import sha256
from pathlib import Path
from zipfile import ZipFile

from scripts.archive.releases.v7.validate_v7_retrieval_review import NS, read_sheet
from scripts.archive.releases.v7.validate_v7_retrieval_review import WORKBOOK as V7_REVIEW

ROOT = Path(__file__).resolve().parents[4]
V7_DATASET = ROOT / "evals/datasets/consolidated_v7_agent_reviewed.jsonl"
V8_DATASET = ROOT / "evals/datasets/consolidated_v8_agent_reviewed.jsonl"
V8_REVIEW = ROOT / "docs/reports/v8/v8-calcium-correction-review.xlsx"
CHANGED = "C-F03-003"
HEADERS = [
    "case_id",
    "prior_question",
    "corrected_question",
    "old_strength",
    "corrected_strength",
    "source_id",
    "source_version",
    "page",
    "source_row_number",
    "evidence_id",
    "decision",
    "reviewer",
    "review_date",
]


def _cells(path: Path) -> list[list[str]]:
    with ZipFile(path) as archive:
        strings = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            strings = ["".join(t.text or "" for t in item.findall(".//x:t", NS)) for item in root]
        sheet = ET.fromstring(archive.read("xl/worksheets/sheet1.xml"))
    output = []
    for row in sheet.findall(".//x:sheetData/x:row", NS):
        values = [""] * len(HEADERS)
        for cell in row.findall("x:c", NS):
            match = re.match(r"([A-Z]+)", cell.attrib["r"])
            if not match:
                continue
            index = 0
            for letter in match.group(1):
                index = index * 26 + ord(letter) - 64
            if index > len(values):
                continue
            raw = cell.find("x:v", NS)
            inline = cell.find("x:is", NS)
            value = raw.text if raw is not None and raw.text is not None else ""
            if cell.attrib.get("t") == "s" and value:
                value = strings[int(value)]
            elif cell.attrib.get("t") == "inlineStr" and inline is not None:
                value = "".join(t.text or "" for t in inline.findall(".//x:t", NS))
            values[index - 1] = value
        output.append(values)
    return output


def validate(path: Path = V8_REVIEW) -> dict:
    prior = read_sheet(V7_REVIEW)
    if len(prior) != 119 or any(
        row["reviewer"] != "Jhiovana"
        or row["decision"] != ("rejeitar" if row["case_id"] == CHANGED else "aprovar")
        for row in prior
    ):
        raise ValueError("Revisão humana v7 diferente do histórico esperado")
    old = {
        row["id"]: row
        for row in (json.loads(x) for x in V7_DATASET.read_text(encoding="utf-8").splitlines())
    }
    new = {
        row["id"]: row
        for row in (json.loads(x) for x in V8_DATASET.read_text(encoding="utf-8").splitlines())
    }
    if len(old) != 119 or set(old) != set(new):
        raise ValueError("Gabarito v8 incompleto")
    for case_id in old:
        if case_id == CHANGED:
            continue
        before = {
            k: v
            for k, v in old[case_id].items()
            if k
            not in {"release_fingerprint", "review_status", "reviewer", "review_reference_sha256"}
        }
        after = {
            k: v
            for k, v in new[case_id].items()
            if k
            not in {"release_fingerprint", "review_status", "reviewer", "review_reference_sha256"}
        }
        if before != after:
            raise ValueError(f"Caso anteriormente aprovado foi alterado: {case_id}")
    rows = _cells(path)
    if len(rows) < 2 or rows[0] != HEADERS or rows[1][0] != CHANGED:
        raise ValueError("Planilha v8 divergente")
    case = new[CHANGED]
    ref = case["expected_references"][0]
    expected = [
        CHANGED,
        old[CHANGED]["question"],
        case["question"],
        old[CHANGED]["expected_references"][0]["strength"],
        ref["strength"],
        ref["source_id"],
        ref["source_version"],
        str(ref["page"]),
        str(ref["source_row_number"]),
        ref["evidence_id"],
    ]
    if rows[1][:10] != expected:
        raise ValueError("Campos de referência da revisão v8 alterados")
    decision, reviewer, reviewed_at = (x.strip() for x in rows[1][10:13])
    errors = []
    if decision != "aprovar":
        errors.append("C-F03-003: aprovação da correção pendente")
    if reviewer != "Jhiovana":
        errors.append("C-F03-003: reviewer deve ser Jhiovana")
    try:
        date.fromisoformat(reviewed_at)
    except ValueError:
        errors.append("C-F03-003: review_date deve ser AAAA-MM-DD")
    return {
        "prior_approved_carried": 118,
        "corrected_case_approved": not errors,
        "errors": errors,
        "prior_review_sha256": sha256(V7_REVIEW.read_bytes()).hexdigest(),
        "correction_review_sha256": sha256(path.read_bytes()).hexdigest(),
    }


if __name__ == "__main__":
    result = validate()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(bool(result["errors"]))
