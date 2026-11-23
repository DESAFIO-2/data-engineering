"""Create a reproducible draft retrieval set; human review remains required."""

from __future__ import annotations

import json
import sys
from hashlib import sha256
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from rag.consolidated import ConsolidatedRelease, load_chunks  # noqa: E402


def main() -> None:
    release = ConsolidatedRelease.load(
        ROOT / "data/releases/corpus-consolidado-v5-aprovado-2026-11-10"
    )
    load_chunks(release, ROOT / "data/derived/chunks" / release.manifest["release_version"])
    sources = {"F01": "RENAME", "F03": "REME DF", "F04": "Farmácia Popular"}
    cases = []
    for sid, label in sources.items():
        chosen = 0
        for med in sorted(release.catalog, key=lambda m: m["medicine_id"]):
            if sid not in med["source_ids"]:
                continue
            parts = [med["active_ingredient"], med["strength"], med["form"]]
            if med.get("release_characteristic"):
                parts.append(med["release_characteristic"])
            detail = " ".join(x for x in parts if x and x != "-")
            question = f"{detail} consta na {label}?"
            relevant = [
                e["evidence_id"]
                for e in release.evidence
                if e["medicine_id"] == med["medicine_id"] and e["source"]["source_id"] == sid
            ]
            family = med["active_ingredient"]
            split = "test" if int(sha256(family.encode()).hexdigest()[:2], 16) % 4 == 0 else "dev"
            cases.append(
                {
                    "id": f"C-{sid}-{chosen + 1:03d}",
                    "family_id": family,
                    "source_id": sid,
                    "split": split,
                    "question": question,
                    "expected_status": "matched",
                    "relevant_ids": relevant,
                    "review_status": "draft",
                    "synthetic": True,
                }
            )
            chosen += 1
            if chosen == 30:
                break
    supply_count = 0
    for item in sorted(
        (o for o in release.occurrences if o["item_type"] == "supply"),
        key=lambda o: o["occurrence_id"],
    ):
        label = sources[item["source"]["source_id"]]
        strength = item["strength"] if item["strength"] != "-" else ""
        question = f"{item['active_ingredient']} {strength} consta como insumo na {label}?"
        alternatives = [
            o
            for o in release.occurrences
            if o["item_type"] == "supply"
            and o["source"]["source_id"] == item["source"]["source_id"]
            and o["active_ingredient"] == item["active_ingredient"]
            and o["strength"] == item["strength"]
        ]
        ambiguous = len(alternatives) > 1
        relevant = (
            []
            if ambiguous
            else [
                e["evidence_id"]
                for e in release.evidence
                if e["occurrence_id"] == item["occurrence_id"]
            ]
        )
        split = (
            "test"
            if int(sha256(item["active_ingredient"].encode()).hexdigest()[:2], 16) % 4 == 0
            else "dev"
        )
        cases.append(
            {
                "id": f"C-SUP-{supply_count + 1:03d}",
                "family_id": item["active_ingredient"],
                "source_id": item["source"]["source_id"],
                "split": split,
                "question": question,
                "expected_status": "ambiguous" if ambiguous else "matched",
                "relevant_ids": relevant,
                "review_status": "draft",
                "synthetic": True,
            }
        )
        supply_count += 1
        if supply_count == 12:
            break
    for i, med in enumerate(release.catalog[:12], 1):
        question = f"{med['active_ingredient']} 99999 mg {med['form']} consta na RENAME?"
        cases.append(
            {
                "id": f"C-WRONG-STRENGTH-{i:03d}",
                "family_id": med["active_ingredient"],
                "split": "test"
                if int(sha256(med["active_ingredient"].encode()).hexdigest()[:2], 16) % 4 == 0
                else "dev",
                "question": question,
                "expected_status": "not_in_scope",
                "relevant_ids": [],
                "review_status": "draft",
                "synthetic": True,
            }
        )
    for i, question in enumerate(
        (
            "Qual o estoque de metformina hoje?",
            "Posso tomar sinvastatina e qual dose?",
            "Quais documentos preciso para a Farmácia Popular?",
            "Qual o jejum para exame de sangue?",
            "A farmácia da minha UBS tem losartana hoje?",
        ),
        1,
    ):
        cases.append(
            {
                "id": f"C-NEG-{i:03d}",
                "family_id": f"negative-{i}",
                "split": "test" if i % 2 else "dev",
                "question": question,
                "expected_status": "unsupported",
                "relevant_ids": [],
                "review_status": "draft",
                "synthetic": True,
            }
        )
    output = ROOT / "evals/datasets/consolidated_v5_draft.jsonl"
    output.write_text(
        "".join(json.dumps(case, ensure_ascii=False, sort_keys=True) + "\n" for case in cases)
    )
    print(f"{len(cases)} casos sintéticos em {output}")


if __name__ == "__main__":
    main()
