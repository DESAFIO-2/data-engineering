"""Review gate must reject omissions and changed source-difference identities."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from scripts.archive.releases.v6.validate_v6_review import validate


def fixture_files(tmp_path: Path, *, decision: str, published: str = "50 mg") -> tuple[Path, Path]:
    findings = tmp_path / "findings.json"
    review = tmp_path / "review.csv"
    findings.write_text(
        json.dumps(
            {
                "findings": [
                    {
                        "occurrence_id": "occ-1",
                        "source": "F01",
                        "page": 3,
                        "row": 2,
                        "field": "strength",
                        "published": "50 mg",
                        "extracted": "50 mg*",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    with review.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=(
                "occurrence_id",
                "source",
                "page",
                "row",
                "field",
                "published",
                "extracted",
                "decision",
                "justification",
                "reviewer",
                "reviewed_at",
            ),
        )
        writer.writeheader()
        writer.writerow(
            {
                "occurrence_id": "occ-1",
                "source": "F01",
                "page": 3,
                "row": 2,
                "field": "strength",
                "published": published,
                "extracted": "50 mg*",
                "decision": decision,
                "justification": "Asterisco é nota de rodapé na fonte",
                "reviewer": "Jhiovana",
                "reviewed_at": "2026-11-11",
            }
        )
    return findings, review


def test_complete_decision_is_counted(tmp_path: Path) -> None:
    findings, review = fixture_files(tmp_path, decision="aceitar_normalizacao")
    assert validate(findings, review)["aceitar_normalizacao"] == 1


@pytest.mark.parametrize("decision", ["", "aprovado"])
def test_missing_or_unknown_decision_is_rejected(tmp_path: Path, decision: str) -> None:
    findings, review = fixture_files(tmp_path, decision=decision)
    with pytest.raises(ValueError, match="decisão ausente ou inválida"):
        validate(findings, review)


def test_changed_published_value_is_rejected(tmp_path: Path) -> None:
    findings, review = fixture_files(tmp_path, decision="aceitar_normalizacao", published="500 mg")
    with pytest.raises(ValueError, match="identidade da diferença alterada"):
        validate(findings, review)
