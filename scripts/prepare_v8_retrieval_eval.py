"""Migrate the v7 technical gabarito to the pending v8 calcium correction."""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

from publish_consolidated_release import read_lines, verify

ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "data/releases/corpus-consolidado-v8-calcio-corrigido-2026-11-11"
SOURCE = ROOT / "evals/datasets/consolidated_v7_agent_reviewed.jsonl"
TARGET = ROOT / "evals/datasets/consolidated_v8_agent_reviewed.jsonl"
CASE_ID = "C-F03-003"
QUESTION = (
    "carbonato de cálcio (equivalente a 500 ou 600 mg de cálcio) + "
    "colecalciferol 400 UI comprimido consta na REME-DF?"
)


def prepare() -> list[dict]:
    release = verify(RELEASE)
    if release["status"] != "pending_review":
        raise ValueError("Esperado candidato v8 pendente")
    evidence = {
        row["evidence_id"]: row for row in read_lines((RELEASE / "evidencias.jsonl").read_bytes())
    }
    cases = [json.loads(line) for line in SOURCE.read_text(encoding="utf-8").splitlines() if line]
    if len(cases) != 119 or len({case["id"] for case in cases}) != 119:
        raise ValueError("Conjunto v7 incompleto")
    fingerprint = sha256((RELEASE / "release.json").read_bytes()).hexdigest()
    corrected = 0
    for case in cases:
        case["release_fingerprint"] = fingerprint
        case["review_status"] = "agent_reviewed"
        case["reviewer"] = "agent_technical_audit"
        case.pop("review_reference_sha256", None)
        if case["id"] == CASE_ID:
            corrected += 1
            case["question"] = QUESTION
            case["migration_note"] = (
                "Rejeição humana na revisão v7: fonte F03 p. 19, linha 194, diz "
                "'500 ou 600 mg', não '500 mg a 600 mg'."
            )
        for ref in case["expected_references"]:
            ev = evidence[ref["evidence_id"]]
            if ev["source"]["source_id"] != ref["source_id"] or ev["source"]["page"] != ref["page"]:
                raise ValueError(f"Fonte/página divergente: {case['id']}")
            if case["id"] != CASE_ID and ref["strength"] != ev["strength"]:
                raise ValueError(f"Outra apresentação alterada: {case['id']}")
            ref["strength"] = ev["strength"]
    if corrected != 1:
        raise ValueError("Caso rejeitado ausente")
    return cases


def main() -> None:
    cases = prepare()
    TARGET.write_text(
        "".join(json.dumps(case, ensure_ascii=False, sort_keys=True) + "\n" for case in cases),
        encoding="utf-8",
    )
    print(f"{len(cases)} casos v8; SHA-256 {sha256(TARGET.read_bytes()).hexdigest()}")


if __name__ == "__main__":
    main()
