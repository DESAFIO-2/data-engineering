"""Migrate v8 expectations to an exploratory v9 development dataset.

The v8 test is historical and is never promoted to a new independent test.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "src"))

from rag.consolidated import ConsolidatedRelease, jsonl_bytes  # noqa: E402

SOURCE = ROOT / "evals/datasets/consolidated_v8_reviewed.jsonl"
TARGET = ROOT / "evals/datasets/consolidated_v9_dev_exploratory.jsonl"
RELEASE = ROOT / "data/releases/corpus-consolidado-v9-aprovado-2026-11-12"
CLARITHROMYCIN_CASE = "C-F03-005"
CLARITHROMYCIN_EVIDENCE = {
    "evidence-25d6511151adc3be1b20ddf5",
    "evidence-440a7b86140f721129cdd834",
    "evidence-83202f34ce2ffbeed05ea49d",
}


def prepare() -> list[dict]:
    release = ConsolidatedRelease.load(RELEASE)
    evidence = {item["evidence_id"]: item for item in release.evidence}
    cases = [json.loads(line) for line in SOURCE.read_text(encoding="utf-8").splitlines() if line]
    if len(cases) != 119 or len({case["id"] for case in cases}) != 119:
        raise ValueError("Gabarito v8 inesperado")
    if len({evidence[eid]["medicine_id"] for eid in CLARITHROMYCIN_EVIDENCE}) != 1:
        raise ValueError("As três linhas F03 de claritromicina não compartilham apresentação")
    for case in cases:
        case["release_fingerprint"] = release.fingerprint
        case["review_status"] = "agent_reviewed"
        case["reviewer"] = "agent_technical_audit"
        case.pop("review_reference_sha256", None)
        case.pop("prior_review_sha256", None)
        case.pop("review_date", None)
        case.pop("reviewer_notes", None)
        if case["id"] == CLARITHROMYCIN_CASE:
            case["split"] = "dev"
            case["relevant_ids"] = sorted(CLARITHROMYCIN_EVIDENCE)
            prior_ref = case["expected_references"][0]
            case["expected_references"] = [
                {
                    **prior_ref,
                    "evidence_id": eid,
                    "page": evidence[eid]["source"]["page"],
                    "source_row_number": evidence[eid]["source_row_number"],
                }
                for eid in sorted(CLARITHROMYCIN_EVIDENCE)
            ]
            case["migration_note"] = (
                "Caso do test histórico v8 movido para dev; pergunta genérica de "
                "claritromicina 500 mg comprimido admite as três linhas F03 "
                "documentalmente idênticas em apresentação. Contextos e canais "
                "permanecem distintos. Aprovação de domínio: revisão v9."
            )
        elif case["split"] == "test":
            case["migration_note"] = "Test histórico v8; vedado como novo teste independente."
        for ref in case["expected_references"]:
            ev = evidence[ref["evidence_id"]]
            for key in (
                "active_ingredient",
                "strength",
                "form",
                "release_characteristic",
                "medicine_id",
            ):
                if case["id"] != CLARITHROMYCIN_CASE and ref[key] != ev[key]:
                    raise ValueError(f"Mudança inesperada em {case['id']}: {key}")
                ref[key] = ev[key]
            if ref["source_id"] != ev["source"]["source_id"] or ref["page"] != ev["source"]["page"]:
                raise ValueError(f"Fonte/página divergente: {case['id']}")
    return cases


def main() -> None:
    cases = prepare()
    TARGET.write_bytes(jsonl_bytes(cases))
    print(f"{len(cases)} casos migrados; {sum(c['split'] == 'dev' for c in cases)} em dev")


if __name__ == "__main__":
    main()
