"""Consolidate human judgments for the four Week 3 response configurations."""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from hashlib import sha256
from pathlib import Path
from typing import Any

CRITERIA = (
    "factual_accuracy",
    "fidelity",
    "completeness",
    "citation_support",
    "critical_error",
    "abstention_correct",
)


def load_answers(paths: list[Path]) -> dict[tuple[str, str], dict[str, Any]]:
    answers: dict[tuple[str, str], dict[str, Any]] = {}
    for path in paths:
        report = json.loads(path.read_text(encoding="utf-8"))
        for record in report["records"]:
            variant = record["variant"]
            if variant == "best_llm" and report.get("best_strategy") != "exact":
                continue  # Exclude the preliminary duplicated lexical run.
            key = (variant, record["id"])
            if key in answers:
                raise ValueError(f"Resposta duplicada: {key}")
            answers[key] = record
    return answers


def run(args: argparse.Namespace) -> dict[str, Any]:
    if args.output.exists():
        raise FileExistsError(args.output)
    answers = load_answers(args.runs)
    regression = load_answers([args.regression])
    for key, record in regression.items():
        if key[1] != "W3-DEV-02":
            raise ValueError("Regressão inesperada")
        answers[key] = record
    with args.reviews.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != len(answers):
        raise ValueError("Cobertura da revisão divergente")
    judged: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        key = (row["variant"], row["id"])
        if key not in answers or key in judged:
            raise ValueError(f"ID de revisão ausente ou duplicado: {key}")
        digest = sha256((answers[key]["answer"] or "").encode()).hexdigest()
        if row["response_sha256"] != digest:
            raise ValueError(f"Hash da resposta divergente: {key}")
        if not row["reviewer"] or not row["reviewed_at"] or not row["rationale"]:
            raise ValueError(f"Revisão incompleta: {key}")
        notes: dict[str, bool | None] = {}
        for criterion in CRITERIA:
            value = row[criterion].strip().lower()
            if value not in {"true", "false", ""}:
                raise ValueError(f"Nota inválida em {criterion}: {key}")
            notes[criterion] = None if value == "" else value == "true"
        judged[key] = {
            "variant": key[0],
            "id": key[1],
            "response_sha256": digest,
            "reviewer": row["reviewer"],
            "reviewed_at": row["reviewed_at"],
            "rationale": row["rationale"],
            "notes": notes,
        }
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entry in judged.values():
        groups[entry["variant"]].append(entry)
    summary = {
        variant: {
            "reviewed": len(group),
            **{
                criterion: {
                    "known": len(values),
                    "true": sum(values),
                    "rate": sum(values) / len(values) if values else None,
                }
                for criterion in CRITERIA
                for values in [
                    [
                        entry["notes"][criterion]
                        for entry in group
                        if entry["notes"][criterion] is not None
                    ]
                ]
            },
        }
        for variant, group in groups.items()
    }
    result = {
        "schema_version": "week3-human-review-v1",
        "review_csv_sha256": sha256(args.reviews.read_bytes()).hexdigest(),
        "summaries": summary,
        "reviews": list(judged.values()),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=Path, nargs="+", required=True)
    parser.add_argument("--regression", type=Path, required=True)
    parser.add_argument("--reviews", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    print(json.dumps(run(parser.parse_args())["summaries"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
