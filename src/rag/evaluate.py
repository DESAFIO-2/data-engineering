"""Avalia busca exata e Hit@k vetorial com gabarito fora do índice."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .release import Release
from .retrieval import retrieve


def evaluate_retrieval(
    dataset: Path, release: Release, store: Any, top_k: int = 5
) -> dict[str, Any]:
    cases = [json.loads(line) for line in dataset.read_text(encoding="utf-8").splitlines() if line]
    exact_hits = vector_hits = 0
    errors = []
    for case in cases:
        result = retrieve(case["question"], release, store, top_k)
        matched = (
            result["status"] == "matched"
            and result["medicine"]["medicine_id"] == case["medicine_id"]
        )
        exact_hits += int(matched)
        vector_hit = matched and case["evidence_id"] in result["semantic_ids"][:top_k]
        vector_hits += int(vector_hit)
        if not matched or not vector_hit:
            errors.append(
                f"{case['id']}: match={result['status']}, "
                f"evidências vetoriais={result.get('semantic_ids', [])[:top_k]}"
            )
    return {
        "total": len(cases),
        "exact_hits": exact_hits,
        "vector_hits": vector_hits,
        "errors": errors,
    }
