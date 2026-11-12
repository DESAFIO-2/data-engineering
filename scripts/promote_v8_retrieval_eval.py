"""Freeze the human-reviewed v8 gabarito after the corrected release is approved."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from validate_v8_calcium_review import V8_REVIEW, validate

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from rag.consolidated import ConsolidatedRelease, jsonl_bytes  # noqa: E402

RELEASE = ROOT / "data/releases/corpus-consolidado-v8-aprovado-2026-11-11"
SOURCE = ROOT / "evals/datasets/consolidated_v8_agent_reviewed.jsonl"
TARGET = ROOT / "evals/datasets/consolidated_v8_reviewed.jsonl"


def promote() -> list[dict]:
    review = validate(V8_REVIEW)
    if review["errors"]:
        raise ValueError("Correção v8 não aprovada por Jhiovana")
    release = ConsolidatedRelease.load(RELEASE)
    cases = [json.loads(x) for x in SOURCE.read_text(encoding="utf-8").splitlines() if x]
    evidence = {ev["evidence_id"]: ev for ev in release.evidence}
    if len(cases) != 119 or len({case["id"] for case in cases}) != 119:
        raise ValueError("Gabarito v8 incompleto")
    for case in cases:
        if case["review_status"] != "agent_reviewed":
            raise ValueError(f"Estado inesperado: {case['id']}")
        case["release_fingerprint"] = release.fingerprint
        case["review_status"] = "reviewed"
        case["reviewer"] = "Jhiovana"
        case["review_reference_sha256"] = review["correction_review_sha256"]
        case["prior_review_sha256"] = review["prior_review_sha256"]
        for ref in case["expected_references"]:
            ev = evidence[ref["evidence_id"]]
            if (
                any(
                    (ref[key] != ev[key])
                    for key in (
                        "active_ingredient",
                        "strength",
                        "form",
                        "release_characteristic",
                        "medicine_id",
                    )
                )
                or ref["page"] != ev["source"]["page"]
                or ref["source_id"] != ev["source"]["source_id"]
            ):
                raise ValueError(f"Referência divergente: {case['id']}")
    return cases


def main() -> None:
    cases = promote()
    TARGET.write_bytes(jsonl_bytes(cases))
    print(f"{len(cases)} casos v8 revisados e vinculados ao release aprovado")


if __name__ == "__main__":
    main()
