"""Summarize LLM vs. RAG comparison runs with text, guardrail, and historical metrics."""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from rag.config import ROOT
from rag.metrics import text_metrics

_DEFAULT_EVIDENCIAS = (
    ROOT / "data/releases/corpus-consolidado-v9-aprovado-2026-11-12/evidencias.jsonl"
)

_ABSTENTION_MARKERS = (
    "não consta",
    "nao consta",
    "não está disponível",
    "nao esta disponivel",
    "não é possível verificar",
    "nao e possivel verificar",
    "não localiz",
    "nao localiz",
    "sem estoque",
    "orientação clínica",
    "orientacao clinica",
    "qual concentração",
    "qual concentracao",
    "apresentações documentadas",
    "apresentacoes documentadas",
    "não encontrei",
    "nao encontrei",
    "não informad",
    "nao informad",
    "não posso",
    "nao posso",
    "não fornec",
    "nao fornec",
)

_SUMMARY_FIELDS = (
    "cases",
    "positive_cases",
    "hit_at_1",
    "hit_at_3",
    "hit_at_5",
    "mrr_at_5",
    "status_accuracy",
    "critical_confusions",
    "citation_precision",
    "errors",
    "usage_coverage",
    "input_tokens_known",
    "output_tokens_known",
    "latency_p50_ms",
    "latency_p95_ms",
)


def load_json_dict(path: Path) -> dict[str, Any]:
    """Load a JSON object file and ensure the top-level value is a mapping."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return data


def load_evidence_texts(path: Path) -> dict[str, str]:
    """Load official evidence_id -> text mappings from an evidencias.jsonl release file."""
    texts: dict[str, str] = {}
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            row = json.loads(stripped)
            evidence_id = row.get("evidence_id")
            text = row.get("text")
            if isinstance(evidence_id, str) and isinstance(text, str):
                texts[evidence_id] = text
    return texts


def _is_abstention(answer: str) -> bool:
    lowered = answer.lower()
    return any(marker in lowered for marker in _ABSTENTION_MARKERS)


def _reasoning_tokens(records: Sequence[Mapping[str, Any]]) -> int | None:
    total = 0
    found = False
    for record in records:
        usage = record.get("usage")
        if not isinstance(usage, Mapping):
            continue
        details = usage.get("output_token_details")
        if not isinstance(details, Mapping):
            continue
        reasoning = details.get("reasoning")
        if isinstance(reasoning, int) and not isinstance(reasoning, bool):
            total += reasoning
            found = True
    return total if found else None


def _compute_text_alignment(
    predictions: Sequence[str],
    references: Sequence[str],
) -> dict[str, Any] | None:
    if not predictions:
        return None
    metrics = text_metrics(predictions, references)
    return {
        "cases": len(predictions),
        "bleu": round(float(metrics["bleu"]), 4),
        "rouge1_f1": round(float(metrics["rouge1"]), 4),
        "rouge2_f1": round(float(metrics["rouge2"]), 4),
        "rougeL_f1": round(float(metrics["rougeL"]), 4),
    }


def _positive_pairs_against_evidence(
    records: Sequence[Mapping[str, Any]],
    evidence_texts: Mapping[str, str],
) -> tuple[list[str], list[str]]:
    predictions: list[str] = []
    references: list[str] = []
    for record in records:
        if record.get("expected_status") != "matched" or record.get("error") is not None:
            continue
        answer = record.get("answer")
        expected_ids = record.get("expected_evidence_ids")
        if not isinstance(answer, str) or not answer.strip() or not isinstance(expected_ids, list):
            continue
        resolved = [
            evidence_texts[ev_id]
            for ev_id in expected_ids
            if isinstance(ev_id, str) and ev_id in evidence_texts
        ]
        if not resolved:
            continue
        predictions.append(answer)
        references.append("\n".join(resolved))
    return predictions, references


def _positive_pairs_against_baseline(
    records: Sequence[Mapping[str, Any]],
    baseline_by_id: Mapping[str, str],
) -> tuple[list[str], list[str]]:
    predictions: list[str] = []
    references: list[str] = []
    for record in records:
        if record.get("expected_status") != "matched" or record.get("error") is not None:
            continue
        case_id = record.get("id")
        answer = record.get("answer")
        if (
            not isinstance(case_id, str)
            or not isinstance(answer, str)
            or not answer.strip()
            or case_id not in baseline_by_id
        ):
            continue
        predictions.append(answer)
        references.append(baseline_by_id[case_id])
    return predictions, references


def _audit_guardrails(records: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    audit: list[dict[str, Any]] = []
    for record in records:
        if record.get("expected_status") == "matched":
            continue
        raw_answer = record.get("answer")
        answer = raw_answer if isinstance(raw_answer, str) else ""
        evidence_ids = record.get("evidence_ids")
        has_evidence = isinstance(evidence_ids, list) and len(evidence_ids) > 0
        audit.append(
            {
                "id": record.get("id"),
                "expected_status": record.get("expected_status"),
                "status": record.get("status"),
                "status_correct": record.get("status_correct"),
                "critical_confusion": record.get("critical_confusion"),
                "error": record.get("error"),
                "has_evidence_ids": has_evidence,
                "abstention_detected": _is_abstention(answer) if answer else False,
                "latency_ms": record.get("total_ms"),
                "answer_preview": answer.strip()[:240],
            }
        )
    return audit


def _summarize_variant(
    summary: Mapping[str, Any],
    records: Sequence[Mapping[str, Any]],
    evidence_texts: Mapping[str, str],
    lexical_doc_by_id: Mapping[str, str],
) -> dict[str, Any]:
    non_error = [r for r in records if r.get("error") is None]
    answers = [
        r["answer"] for r in non_error if isinstance(r.get("answer"), str) and r["answer"].strip()
    ]
    positive_ok = [
        r
        for r in non_error
        if r.get("expected_status") == "matched"
        and isinstance(r.get("answer"), str)
        and str(r.get("answer")).strip()
    ]
    avg_chars = round(sum(len(a) for a in answers) / len(answers), 1) if answers else None

    ev_preds, ev_refs = _positive_pairs_against_evidence(records, evidence_texts)
    base_preds, base_refs = _positive_pairs_against_baseline(records, lexical_doc_by_id)

    payload: dict[str, Any] = {field: summary.get(field) for field in _SUMMARY_FIELDS}
    payload["completed_cases"] = len(non_error)
    payload["positive_completed_cases"] = len(positive_ok)
    payload["avg_answer_chars"] = avg_chars
    payload["reasoning_tokens_known"] = _reasoning_tokens(records)
    payload["text_vs_official_evidence"] = _compute_text_alignment(ev_preds, ev_refs)
    payload["text_vs_lexical_documental"] = _compute_text_alignment(base_preds, base_refs)
    payload["negative_guardrails"] = _audit_guardrails(records)
    return payload


def _build_baseline_history(paths: Sequence[Path]) -> list[dict[str, Any]]:
    history: list[dict[str, Any]] = []
    for path in paths:
        report = load_json_dict(path)
        summaries = report.get("summaries")
        if not isinstance(summaries, Mapping):
            continue
        variants_summary: dict[str, dict[str, Any]] = {}
        for variant, summary in summaries.items():
            if not isinstance(variant, str) or not isinstance(summary, Mapping):
                continue
            variants_summary[variant] = {
                "cases": summary.get("cases"),
                "errors": summary.get("errors"),
                "status_accuracy": summary.get("status_accuracy"),
                "hit_at_1": summary.get("hit_at_1"),
                "citation_precision": summary.get("citation_precision"),
                "latency_p50_ms": summary.get("latency_p50_ms"),
                "input_tokens_known": summary.get("input_tokens_known"),
                "output_tokens_known": summary.get("output_tokens_known"),
            }
        history.append(
            {
                "file": path.name,
                "executed_at_utc": report.get("executed_at_utc"),
                "chat_model": report.get("chat_model"),
                "best_strategy": report.get("best_strategy"),
                "variants": variants_summary,
            }
        )
    return history


def summarize_comparison(
    response_path: Path,
    evidencias_path: Path,
    baseline_paths: Sequence[Path] = (),
    multichunk_path: Path | None = None,
) -> dict[str, Any]:
    """Compute a consolidated comparison report from Week 3 and offline benchmark JSONs."""
    report = load_json_dict(response_path)
    evidence_texts = load_evidence_texts(evidencias_path)

    raw_summaries = report.get("summaries")
    raw_records = report.get("records")
    if not isinstance(raw_summaries, Mapping) or not isinstance(raw_records, list):
        raise ValueError(f"Invalid response report structure in {response_path}")

    records_by_variant: dict[str, list[Mapping[str, Any]]] = {}
    for item in raw_records:
        if not isinstance(item, Mapping):
            continue
        variant = item.get("variant")
        if isinstance(variant, str):
            records_by_variant.setdefault(variant, []).append(item)

    lexical_doc_by_id: dict[str, str] = {}
    for record in records_by_variant.get("lexical_documental", []):
        case_id = record.get("id")
        answer = record.get("answer")
        if (
            record.get("error") is None
            and isinstance(case_id, str)
            and isinstance(answer, str)
            and answer.strip()
        ):
            lexical_doc_by_id[case_id] = answer

    variants_out: dict[str, dict[str, Any]] = {}
    for variant, summary in raw_summaries.items():
        if not isinstance(variant, str) or not isinstance(summary, Mapping):
            continue
        variants_out[variant] = _summarize_variant(
            summary=summary,
            records=records_by_variant.get(variant, []),
            evidence_texts=evidence_texts,
            lexical_doc_by_id=lexical_doc_by_id,
        )

    result: dict[str, Any] = {
        "schema_version": "comparativo-llm-vs-rag-v1",
        "source_response_file": str(response_path),
        "executed_at_utc": report.get("executed_at_utc"),
        "chat_model": report.get("chat_model"),
        "embedding_model": report.get("embedding_model"),
        "best_strategy": report.get("best_strategy"),
        "variants": variants_out,
    }
    if baseline_paths:
        result["baseline_history"] = _build_baseline_history(baseline_paths)
    if multichunk_path is not None:
        mc = load_json_dict(multichunk_path)
        result["multichunk_offline"] = {
            "source_file": str(multichunk_path),
            "release_version": mc.get("release_version"),
            "split": mc.get("split"),
            "summaries": mc.get("summaries"),
            "paired_comparisons": mc.get("paired_comparisons"),
        }
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--response-json", type=Path, required=True)
    parser.add_argument("--evidencias-jsonl", type=Path, default=_DEFAULT_EVIDENCIAS)
    parser.add_argument("--baseline-runs", type=Path, nargs="*", default=[])
    parser.add_argument("--multichunk-json", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    summary = summarize_comparison(
        response_path=args.response_json,
        evidencias_path=args.evidencias_jsonl,
        baseline_paths=args.baseline_runs,
        multichunk_path=args.multichunk_json,
    )
    rendered = json.dumps(summary, ensure_ascii=False, indent=2)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
