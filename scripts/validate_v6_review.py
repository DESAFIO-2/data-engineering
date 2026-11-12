"""Validate Jhiovana's field-by-field decisions without granting approval."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

ALLOWED = {"aceitar_normalizacao", "corrigir_release", "manter_pendente"}
IDENTITY = ("occurrence_id", "source", "page", "row", "field", "published", "extracted")


def validate(findings_path: Path, review_path: Path) -> dict[str, int]:
    findings = json.loads(findings_path.read_text(encoding="utf-8"))["findings"]
    with review_path.open(encoding="utf-8-sig", newline="") as handle:
        decisions = list(csv.DictReader(handle))
    if len(decisions) != len(findings):
        raise ValueError("Número de decisões difere do relatório de diferenças")
    counts = {value: 0 for value in ALLOWED}
    for index, (finding, decision) in enumerate(zip(findings, decisions, strict=True), 1):
        if any(str(finding.get(field, "")) != (decision.get(field) or "") for field in IDENTITY):
            raise ValueError(f"Linha {index}: identidade da diferença alterada")
        choice = (decision.get("decision") or "").strip()
        if choice not in ALLOWED:
            raise ValueError(f"Linha {index}: decisão ausente ou inválida")
        if not all(
            (decision.get(field) or "").strip()
            for field in ("justification", "reviewer", "reviewed_at")
        ):
            raise ValueError(f"Linha {index}: justificativa, revisor ou data ausente")
        counts[choice] += 1
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--findings", type=Path, required=True)
    parser.add_argument("--review", type=Path, required=True)
    args = parser.parse_args()
    try:
        counts = validate(args.findings, args.review)
    except ValueError as exc:
        parser.exit(2, f"Gate aberto: {exc}\n")
    print(json.dumps(counts, ensure_ascii=False))
    if counts["corrigir_release"] or counts["manter_pendente"]:
        raise SystemExit("Gate aberto: corrigir o release ou resolver pendências")


if __name__ == "__main__":
    main()
