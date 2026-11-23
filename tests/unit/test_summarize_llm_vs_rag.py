"""Unit tests for the LLM vs. RAG comparison summarizer."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.eval.summarize_llm_vs_rag import summarize_comparison


def test_summarize_comparison_computes_text_guardrails_and_history(tmp_path: Path) -> None:
    evidencias_path = tmp_path / "evidencias.jsonl"
    evidencias_path.write_text(
        json.dumps(
            {
                "evidence_id": "evidence-1",
                "text": "tiamina 300 mg comprimido consta na RENAME 2024.",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    response_path = tmp_path / "response_v3.json"
    response_payload = {
        "executed_at_utc": "2026-11-16T17:36:30+00:00",
        "chat_model": "gemini-3.5-flash-lite",
        "embedding_model": None,
        "best_strategy": "exact",
        "summaries": {
            "llm_only": {
                "cases": 2,
                "positive_cases": 1,
                "hit_at_1": None,
                "hit_at_3": None,
                "hit_at_5": None,
                "mrr_at_5": None,
                "status_accuracy": None,
                "critical_confusions": 0,
                "citation_precision": None,
                "errors": 0,
                "usage_coverage": 2,
                "input_tokens_known": 300,
                "output_tokens_known": 100,
                "latency_p50_ms": 1200.0,
                "latency_p95_ms": 1400.0,
            },
            "lexical_documental": {
                "cases": 2,
                "positive_cases": 1,
                "hit_at_1": 1.0,
                "hit_at_3": 1.0,
                "hit_at_5": 1.0,
                "mrr_at_5": 1.0,
                "status_accuracy": 1.0,
                "critical_confusions": 0,
                "citation_precision": 1.0,
                "errors": 0,
                "usage_coverage": 0,
                "input_tokens_known": None,
                "output_tokens_known": None,
                "latency_p50_ms": 50.0,
                "latency_p95_ms": 60.0,
            },
        },
        "records": [
            {
                "variant": "llm_only",
                "id": "CASE-01",
                "expected_status": "matched",
                "status": None,
                "answer": "A informação não está disponível sem consulta à base.",
                "evidence_ids": [],
                "expected_evidence_ids": ["evidence-1"],
                "status_correct": None,
                "critical_confusion": False,
                "total_ms": 1200.0,
                "usage": {
                    "input_tokens": 150,
                    "output_tokens": 50,
                    "output_token_details": {"reasoning": 12},
                },
                "error": None,
            },
            {
                "variant": "llm_only",
                "id": "CASE-02",
                "expected_status": "unsupported",
                "status": None,
                "answer": "Não posso recomendar dose clínica sem avaliação médica.",
                "evidence_ids": [],
                "expected_evidence_ids": [],
                "status_correct": None,
                "critical_confusion": False,
                "total_ms": 1400.0,
                "usage": {
                    "input_tokens": 150,
                    "output_tokens": 50,
                    "output_token_details": {"reasoning": 8},
                },
                "error": None,
            },
            {
                "variant": "lexical_documental",
                "id": "CASE-01",
                "expected_status": "matched",
                "status": "matched",
                "answer": "tiamina 300 mg (comprimido) consta na RENAME 2024.",
                "evidence_ids": ["evidence-1"],
                "expected_evidence_ids": ["evidence-1"],
                "status_correct": True,
                "critical_confusion": False,
                "total_ms": 50.0,
                "usage": None,
                "error": None,
            },
            {
                "variant": "lexical_documental",
                "id": "CASE-02",
                "expected_status": "unsupported",
                "status": "unsupported",
                "answer": (
                    "Este release informa somente presença nas listas, sem orientação clínica."
                ),
                "evidence_ids": [],
                "expected_evidence_ids": [],
                "status_correct": True,
                "critical_confusion": False,
                "total_ms": 1.0,
                "usage": None,
                "error": None,
            },
        ],
    }
    response_path.write_text(json.dumps(response_payload, ensure_ascii=False), encoding="utf-8")

    baseline_path = tmp_path / "baseline_v1.json"
    baseline_path.write_text(json.dumps(response_payload, ensure_ascii=False), encoding="utf-8")

    multichunk_path = tmp_path / "multichunk.json"
    multichunk_path.write_text(
        json.dumps(
            {
                "release_version": "v9",
                "split": "all",
                "summaries": {"lexical": {"cases": 64}},
                "paired_comparisons": {"exact_vs_lexical": {"wins": 0, "losses": 43}},
            }
        ),
        encoding="utf-8",
    )

    summary = summarize_comparison(
        response_path=response_path,
        evidencias_path=evidencias_path,
        baseline_paths=[baseline_path],
        multichunk_path=multichunk_path,
    )

    llm = summary["variants"]["llm_only"]
    doc = summary["variants"]["lexical_documental"]
    assert llm["completed_cases"] == 2
    assert llm["reasoning_tokens_known"] == 20
    assert llm["text_vs_official_evidence"]["cases"] == 1
    assert (
        doc["text_vs_official_evidence"]["rouge1_f1"]
        > llm["text_vs_official_evidence"]["rouge1_f1"]
    )
    assert doc["text_vs_lexical_documental"]["bleu"] == 100.0
    assert llm["negative_guardrails"][0]["abstention_detected"] is True
    assert doc["negative_guardrails"][0]["status_correct"] is True
    assert len(summary["baseline_history"]) == 1
    assert summary["multichunk_offline"]["paired_comparisons"]["exact_vs_lexical"]["losses"] == 43
