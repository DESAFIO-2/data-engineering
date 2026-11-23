"""Freeze the next independent v9 holdout after 28 human approvals."""

from __future__ import annotations

import json
import re
import sys
from hashlib import sha256
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "src"))

from scripts.archive.releases.v9.prepare_v9_next_test_candidate import presentation_for_review  # noqa: E402

from rag.consolidated import ConsolidatedRelease, jsonl_bytes  # noqa: E402
from rag.consolidated_evaluation import _preflight  # noqa: E402

DEV = ROOT / "evals/datasets/consolidated_v9_reviewed.jsonl"
CANDIDATE = ROOT / "evals/datasets/consolidated_v9_next_test_candidate_unreviewed.jsonl"
REVIEW = ROOT / "docs/reports/v9/v9-next-independent-test-review.md"
TARGET = ROOT / "evals/datasets/consolidated_v9_next_reviewed.jsonl"
RELEASE = ROOT / "data/releases/corpus-consolidado-v9-aprovado-2026-11-12"


def promote() -> list[dict]:
    candidate = [
        json.loads(line) for line in CANDIDATE.read_text(encoding="utf-8").splitlines() if line
    ]
    if len(candidate) != 28:
        raise ValueError("Teste fechado: candidato exige 28 casos")
    rows = [
        [cell.strip() for cell in line.strip().strip("|").split("|")]
        for line in REVIEW.read_text(encoding="utf-8").splitlines()
        if re.match(r"^\| V9-R2-\d{3} \|", line) and line.count("|") == 10
    ]
    if len(rows) != 28 or len({row[0] for row in rows}) != 28:
        raise ValueError("Teste fechado: revisão exige 28 linhas únicas")
    by_id = {row[0]: row for row in rows}
    review_hash = sha256(REVIEW.read_bytes()).hexdigest()
    for case in candidate:
        row = by_id.get(case["id"])
        refs = "; ".join(
            f"{ref['evidence_id']} p.{ref['page']} linha {ref['source_row_number']}"
            for ref in case["expected_references"]
        ) or "—"
        if row is None or len(row) != 9:
            raise ValueError(f"Teste fechado: linha inválida: {case['id']}")
        if row[1:6] != [
            case["source_id"],
            case["question"],
            case["expected_status"],
            presentation_for_review(case),
            refs,
        ]:
            raise ValueError(f"Teste fechado: revisão diverge do candidato: {case['id']}")
        if row[6].casefold() != "aprovado" or not re.fullmatch(
            r"Jhiovana\s+\d{4}-\d{2}-\d{2}", row[7]
        ):
            raise ValueError(f"Teste fechado: aprovação humana pendente: {case['id']}")
        if row[8] not in {"—", "-", ""}:
            raise ValueError(f"Teste fechado: justificativa de rejeição em aprovação: {case['id']}")
        case["review_status"] = "reviewed"
        case["reviewer"] = "Jhiovana"
        case["review_date"] = row[7].split()[-1]
        case["review_reference_sha256"] = review_hash
    old = [json.loads(line) for line in DEV.read_text(encoding="utf-8").splitlines() if line]
    cases = [case for case in old if case["split"] == "dev"] + candidate
    release = ConsolidatedRelease.load(RELEASE)
    _preflight(cases, release, "test", REVIEW)
    return cases


def main() -> None:
    if TARGET.exists():
        raise ValueError("Teste já congelado; não sobrescrever")
    cases = promote()
    TARGET.write_bytes(jsonl_bytes(cases))
    print(f"{len(cases)} casos congelados; 28 no teste")


if __name__ == "__main__":
    main()
