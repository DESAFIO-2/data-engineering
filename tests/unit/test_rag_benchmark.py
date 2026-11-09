import json
from pathlib import Path
from typing import Any
from unittest.mock import Mock

import pytest

from rag.benchmark import (
    RUBRIC_FIELDS,
    dataset_hash,
    read_jsonl,
    report_human_reviews,
    run_benchmark,
    validate_cases,
)


def case(identifier: str = "a", status: str = "matched") -> dict[str, Any]:
    return {
        "id": identifier,
        "family_id": identifier,
        "question": "Pergunta sintética?",
        "reference_answer": "O serviço atende pessoas na unidade.",
        "relevant_ids": ["ev-a"] if status == "matched" else [],
        "split": "dev",
        "synthetic": True,
        "review_status": "draft",
        "expected_status": status,
    }


@pytest.mark.parametrize(
    "change,kwargs",
    [
        ({}, {}),
        ({"synthetic": False}, {"allow_draft": True}),
        ({"evaluable": False}, {"allow_draft": True}),
        ({"split": "test"}, {"split": "test", "allow_draft": True}),
        ({"review_status": "reviewed"}, {}),
    ],
)
def test_validation_precedes_api_calls(
    tmp_path: Path, change: dict[str, Any], kwargs: dict[str, Any]
) -> None:
    runner = Mock()
    with pytest.raises(ValueError):
        run_benchmark([{**case(), **change}], runner, tmp_path / "run.jsonl", **kwargs)
    runner.assert_not_called()


def test_family_leakage_rejected() -> None:
    with pytest.raises(ValueError, match="Family leakage"):
        validate_cases([case(), {**case("b"), "family_id": "a", "split": "test"}])


def test_reviewed_frozen_test_gate(tmp_path: Path) -> None:
    cases = [
        {
            **case(),
            "split": "test",
            "review_status": "reviewed",
            "review": {
                "reviewer": "test fixture",
                "reviewed_at": "2026-11-06",
                "record_id": "fixture-only",
            },
        }
    ]
    runner = Mock(return_value={"status": "matched", "answer": "ok", "ranked_ids": ["ev-a"]})
    with pytest.raises(ValueError, match="frozen"):
        run_benchmark(cases, runner, tmp_path / "bad.jsonl", split="test")
    runner.assert_not_called()
    result = run_benchmark(
        cases,
        runner,
        tmp_path / "ok.jsonl",
        split="test",
        frozen_dataset_sha256=dataset_hash(cases),
    )
    assert result["review_status"] == "reviewed"
    assert result["factual_accuracy"] is None


def test_failure_denominators_timings_exports_and_review_fields(tmp_path: Path) -> None:
    cases = [case(), case("b", "blocked"), case("c")]

    def runner(item: dict[str, Any]) -> dict[str, Any]:
        if item["id"] == "c":
            raise RuntimeError("SECRET must not appear in artifact")
        return {
            "status": item["expected_status"],
            "answer": item["reference_answer"],
            "ranked_ids": item["relevant_ids"],
            "latency_ms": 20,
            "retrieval_ms": 5,
            "generation_ms": 15,
            "usage": {"input_tokens": 10, "output_tokens": 4},
        }

    output = tmp_path / "run.jsonl"
    result = run_benchmark(cases, runner, output, allow_draft=True, repeat=2)
    assert result["total"] == 6
    assert result["errors"] == 2
    assert result["hit@1"] == 0.5
    assert result["behavior_accuracy"] == 1
    assert result["text_scored_cases"] == 4
    assert result["input_tokens"] == 40
    assert result["input_tokens_known_cases"] == 4
    assert result["retrieval_p95_ms"] == 5
    assert result["throughput_cases_per_second"] > 0
    assert result["factual_review"] == "pending"
    rows = read_jsonl(output)
    assert rows[0]["question"] == cases[0]["question"]
    assert rows[0]["answer"] == cases[0]["reference_answer"]
    assert rows[1]["hit@1"] is None
    assert "SECRET" not in output.read_text(encoding="utf-8")
    assert output.with_suffix(".csv").exists()
    assert output.with_suffix(".md").exists()
    blocked = Mock()
    with pytest.raises(FileExistsError):
        run_benchmark(cases, blocked, output, allow_draft=True)
    blocked.assert_not_called()


@pytest.mark.parametrize("mode,metric", [("retrieval", "bleu"), ("generation", "mrr@5")])
def test_stage_excludes_inapplicable_metrics(tmp_path: Path, mode: str, metric: str) -> None:
    result = run_benchmark(
        [case()],
        lambda _: {"status": "matched", "answer": "answer", "ranked_ids": ["ev-a"]},
        tmp_path / "run.jsonl",
        mode=mode,
        allow_draft=True,
    )
    assert result[metric] is None


def test_manual_review_binding_and_coverage(tmp_path: Path) -> None:
    run = tmp_path / "run.jsonl"
    run_benchmark(
        [case()], lambda _: {"status": "matched", "answer": "answer"}, run, allow_draft=True
    )
    row = read_jsonl(run)[0]
    review = {
        "id": "a",
        "repeat_index": 0,
        "reviewer": "fixture",
        "reviewed_at": "2026-11-06",
        "record_id": "fixture-record",
        "rationale": "Test fixture only",
        "response_sha256": row["response_sha256"],
        **dict.fromkeys(RUBRIC_FIELDS, None),
        "factual_accuracy": False,
        "critical_error": True,
    }
    reviews = tmp_path / "reviews.jsonl"
    reviews.write_text(json.dumps(review) + "\n", encoding="utf-8")
    summary = report_human_reviews(run, reviews, tmp_path / "human.jsonl")
    assert summary["factual_accuracy"] == 0
    assert summary["critical_error"] == 1
    assert summary["abstention_correct"] is None
    review["response_sha256"] = "wrong"
    reviews.write_text(json.dumps(review) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="hash mismatch"):
        report_human_reviews(run, reviews, tmp_path / "bad.jsonl")
