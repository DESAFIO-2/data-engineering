"""Export a Week 3 response comparison JSON to a blank human-review CSV template."""

from __future__ import annotations

import argparse
import csv
import json
from hashlib import sha256
from pathlib import Path

from scripts.eval.week3_review import CRITERIA, load_answers

FIELDNAMES = [
    "variant",
    "retrieval_strategy",
    "id",
    "response_sha256",
    "question",
    "answer",
    "evidence_ids",
    *CRITERIA,
    "reviewer",
    "reviewed_at",
    "rationale",
]


def export_csv(runs: list[Path], output: Path) -> int:
    """Write human-review CSV rows with SHA-256 checksums for all answers."""
    best_strategy = "exact"
    for path in runs:
        report = json.loads(path.read_text(encoding="utf-8"))
        if report.get("best_strategy"):
            best_strategy = str(report["best_strategy"])

    answers = load_answers(runs)
    strategy_by_variant = {
        "llm_only": "none",
        "lexical_documental": "lexical",
        "lexical_llm": "lexical",
        "best_llm": best_strategy,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES, lineterminator="\n")
        writer.writeheader()
        for (variant, case_id), record in answers.items():
            answer = record.get("answer") or ""
            writer.writerow(
                {
                    "variant": variant,
                    "retrieval_strategy": strategy_by_variant.get(variant, "lexical"),
                    "id": case_id,
                    "response_sha256": sha256(answer.encode()).hexdigest(),
                    "question": record["question"],
                    "answer": answer,
                    "evidence_ids": json.dumps(record.get("evidence_ids", []), ensure_ascii=False),
                    **{criterion: "" for criterion in CRITERIA},
                    "reviewer": "",
                    "reviewed_at": "",
                    "rationale": "",
                }
            )
    return len(answers)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=Path, nargs="+", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    count = export_csv(args.runs, args.output)
    print(json.dumps({"rows": count, "output": str(args.output)}))


if __name__ == "__main__":
    main()
