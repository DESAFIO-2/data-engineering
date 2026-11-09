"""Explicit, dependency-light retrieval metrics and standard text metrics."""

from __future__ import annotations

import math
import re
import unicodedata
from collections.abc import Sequence
from typing import Any


def retrieval_metrics(ranked: Sequence[str], relevant: Sequence[str]) -> dict[str, float | None]:
    """Deduplicate ranks preserving order; precision denominator is k, even if short."""
    gold = set(relevant)
    if not gold:
        return {
            **{
                f"{metric}@{k}": None
                for metric in ("hit", "recall", "precision")
                for k in (1, 3, 5)
            },
            "mrr": None,
            "mrr@5": None,
        }
    ids = list(dict.fromkeys(ranked))
    result: dict[str, float | None] = {}
    for k in (1, 3, 5):
        count = len(set(ids[:k]) & gold)
        result.update(
            {
                f"hit@{k}": float(count > 0),
                f"recall@{k}": count / len(gold),
                f"precision@{k}": count / k,
            }
        )
    result["mrr@5"] = next((1 / i for i, eid in enumerate(ids[:5], 1) if eid in gold), 0.0)
    result["mrr"] = result["mrr@5"]  # Compatibility alias, explicitly capped at five.
    return result


def strip_citations(text: str) -> str:
    """Remove bracketed numeric/evidence citations, preserving other bracketed prose."""
    return re.sub(r"\[(?:\d+(?:\s*[,;–-]\s*\d+)*|(?:ev|occ)-[\w-]+)\]", "", text)


class PortugueseTokenizer:
    """NFC + Unicode casefold + alphanumeric words; accents retained, no stemming."""

    def tokenize(self, text: str) -> list[str]:
        return re.findall(r"[^\W_]+", unicodedata.normalize("NFC", text).casefold())


def percentile(values: Sequence[float], percent: float) -> float | None:
    """Linear interpolation at (n-1)*p; empty samples have no percentile."""
    if not 0 <= percent <= 100:
        raise ValueError("percent must be in [0, 100]")
    if any(not math.isfinite(v) or v < 0 for v in values):
        raise ValueError("Samples must be finite and nonnegative")
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * percent / 100
    lo, hi = math.floor(position), math.ceil(position)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (position - lo)


def text_metrics(predictions: Sequence[str], references: Sequence[str]) -> dict[str, Any]:
    """One reference per case; corpus BLEU (0..100), mean ROUGE F1 (0..1)."""
    if len(predictions) != len(references):
        raise ValueError("Predictions and references must have equal lengths")
    from rouge_score import rouge_scorer  # type: ignore[import-untyped]
    from sacrebleu.metrics.bleu import BLEU

    bleu = BLEU(tokenize="13a", lowercase=False, smooth_method="exp", effective_order=False)
    scorer = rouge_scorer.RougeScorer(
        ["rouge1", "rouge2", "rougeL"], use_stemmer=False, tokenizer=PortugueseTokenizer()
    )
    if not predictions:
        return {
            "bleu": None,
            "rouge1": None,
            "rouge2": None,
            "rougeL": None,
            "bleu_signature": None,
            **{
                f"{key}_{metric}": None
                for key in ("rouge1", "rouge2", "rougeL")
                for metric in ("precision", "recall", "f1")
            },
        }
    predictions = [strip_citations(text) for text in predictions]
    references = [strip_citations(text) for text in references]
    score = bleu.corpus_score(list(predictions), [list(references)])
    scores = [scorer.score(ref, pred) for pred, ref in zip(predictions, references, strict=True)]
    return {
        "bleu": score.score,
        "bleu_signature": str(bleu.get_signature()),
        **{
            key: sum(row[key].fmeasure for row in scores) / len(scores)
            for key in ("rouge1", "rouge2", "rougeL")
        },
        **{
            f"{key}_{metric}": sum(getattr(row[key], attribute) for row in scores) / len(scores)
            for key in ("rouge1", "rouge2", "rougeL")
            for metric, attribute in (
                ("precision", "precision"),
                ("recall", "recall"),
                ("f1", "fmeasure"),
            )
        },
        "rouge_tokenizer": "unicode_nfc_casefold_alphanumeric_no_stemming",
    }
