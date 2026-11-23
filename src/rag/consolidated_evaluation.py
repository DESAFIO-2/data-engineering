"""Traceable exact/lexical evaluation for an approved consolidated release."""

from __future__ import annotations

import json
import platform
import re
import subprocess
import time
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

from .consolidated import ConsolidatedRelease, item_name_matches, normalize, search

V7 = "corpus-consolidado-v7-aprovado-2026-11-11"


def _percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    values = sorted(values)
    position = (len(values) - 1) * fraction
    left = int(position)
    right = min(left + 1, len(values) - 1)
    return values[left] + (values[right] - values[left]) * (position - left)


def _git_revision(root: Path) -> dict[str, Any]:
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root, text=True, capture_output=True, check=True
        ).stdout.strip()
        dirty = bool(
            subprocess.run(
                ["git", "status", "--porcelain", "--untracked-files=no"],
                cwd=root,
                text=True,
                capture_output=True,
                check=True,
            ).stdout.strip()
        )
        return {"commit": commit, "dirty": dirty}
    except (OSError, subprocess.CalledProcessError):
        return {"commit": None, "dirty": None}


def _source_filter(question: str) -> str | None:
    query = normalize(question)
    if re.search(r"\b(?:reme|reme-df|f03)\b", query):
        return "F03"
    if "farmacia popular" in query or re.search(r"\bf04\b", query):
        return "F04"
    if re.search(r"\b(?:rename|f01)\b", query):
        return "F01"
    return None


def _trace_candidates(question: str, release: ConsolidatedRelease) -> list[str]:
    query = normalize(question)
    source = _source_filter(question)
    return sorted(
        item["medicine_id"]
        for item in release.catalog
        if item_name_matches(query, item) and (source is None or source in item["source_ids"])
    )


def _review_hash(path: Path, expected: set[str]) -> str:
    """Preserve review hashes when Git checks out text with LF instead of CRLF."""
    raw = path.read_bytes()
    digest = sha256(raw).hexdigest()
    if digest in expected or path.suffix.lower() not in {".md", ".csv", ".txt"}:
        return digest
    crlf = raw.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
    alternate = sha256(crlf).hexdigest()
    return alternate if alternate in expected else digest


def _preflight(
    cases: list[dict[str, Any]],
    release: ConsolidatedRelease,
    split: str,
    review_path: Path | None,
    prior_review_path: Path | None = None,
) -> None:
    version = release.manifest["release_version"]
    v9_or_later_test = version.startswith(
        ("corpus-consolidado-v9-", "corpus-consolidado-v10-")
    ) and (split == "test")
    expected_count = 120 if v9_or_later_test else 119
    if len(cases) != expected_count or len({case["id"] for case in cases}) != len(cases):
        prefix = "Teste fechado: " if v9_or_later_test else ""
        raise ValueError(f"{prefix}o conjunto consolidado exige {expected_count} IDs únicos")
    families = {
        part: {case["family_id"] for case in cases if case["split"] == part}
        for part in ("dev", "test")
    }
    if families["dev"] & families["test"]:
        raise ValueError("Famílias em ambos os splits")
    evidence = {item["evidence_id"]: item for item in release.evidence}
    for case in cases:
        if case.get("release_fingerprint") != release.fingerprint:
            raise ValueError(f"Fingerprint do caso divergente: {case['id']}")
        if (case["expected_status"] == "matched") != bool(case["relevant_ids"]):
            raise ValueError(f"Status/referência incoerentes: {case['id']}")
        for eid in case["relevant_ids"]:
            ev = evidence.get(eid)
            if ev is None or (
                case.get("source_id") and ev["source"]["source_id"] != case["source_id"]
            ):
                raise ValueError(f"Evidência/fonte inválida: {case['id']} {eid}")
        if {ref["evidence_id"] for ref in case["expected_references"]} != set(case["relevant_ids"]):
            raise ValueError(f"Referências/evidências divergentes: {case['id']}")
        for ref in case["expected_references"]:
            ev = evidence[ref["evidence_id"]]
            if any(
                ref[key] != ev[key]
                for key in (
                    "active_ingredient",
                    "strength",
                    "form",
                    "release_characteristic",
                    "medicine_id",
                    "source_row_number",
                )
            ) or any(
                ref[key] != ev["source"][source_key]
                for key, source_key in (
                    ("source_id", "source_id"),
                    ("source_version", "version"),
                    ("page", "page"),
                )
            ):
                raise ValueError(f"Referência divergente do release: {case['id']}")
    if split == "test":
        if review_path is None or not review_path.exists():
            raise ValueError("Teste fechado: revisão humana da planilha não encontrada")
        reviewed_cases = (
            [case for case in cases if case["split"] == "test"]
            if version.startswith(("corpus-consolidado-v9-", "corpus-consolidado-v10-"))
            else cases
        )
        review_hash = _review_hash(
            review_path, {case.get("review_reference_sha256", "") for case in reviewed_cases}
        )
        if any(
            case.get("review_status") != "reviewed"
            or case.get("reviewer") != "Jhiovana"
            or case.get("review_reference_sha256") != review_hash
            for case in reviewed_cases
        ):
            raise ValueError("Teste fechado: casos de teste precisam de revisão humana registrada")
        if prior_review_path is not None:
            if not prior_review_path.exists():
                raise ValueError("Teste fechado: revisão anterior não encontrada")
            prior_hash = sha256(prior_review_path.read_bytes()).hexdigest()
            if any(case.get("prior_review_sha256") != prior_hash for case in cases):
                raise ValueError("Teste fechado: revisão anterior divergente")


def evaluate(
    *,
    dataset: Path,
    release: ConsolidatedRelease,
    chunks: list[dict[str, Any]],
    chunk_manifest: dict[str, Any],
    strategy: str,
    split: str,
    top_k: int = 5,
    review_path: Path | None = None,
    prior_review_path: Path | None = None,
    store: Any = None,
    embedding_model: str | None = None,
) -> dict[str, Any]:
    if (
        strategy not in {"exact", "lexical", "vector", "hybrid"}
        or split not in {"dev", "test"}
        or top_k != 5
    ):
        raise ValueError("Este gate usa exact/lexical/vector/hybrid e top_k=5")
    if strategy in {"vector", "hybrid"} and (store is None or not embedding_model):
        raise ValueError("Busca vetorial exige índice compatível e modelo registrado")
    cases = [json.loads(x) for x in dataset.read_text(encoding="utf-8").splitlines() if x]
    _preflight(cases, release, split, review_path, prior_review_path)
    evidence = {item["evidence_id"]: item for item in release.evidence}
    chunk_by_evidence = {item["evidence_id"]: item for item in chunks}
    records = []
    for case in cases:
        if case["split"] != split:
            continue
        started = time.perf_counter()
        result = search(
            case["question"], release, chunks, store=store, strategy=strategy, top_k=top_k
        )
        elapsed_ms = (time.perf_counter() - started) * 1000
        found = result.get("evidence", [])
        retrieved = [item["evidence_id"] for item in found]
        relevant = set(case["relevant_ids"])
        rank = next((i for i, eid in enumerate(retrieved, 1) if eid in relevant), None)
        expected_mids = {ref["medicine_id"] for ref in case["expected_references"]}
        returned_mids = {item["medicine_id"] for item in found}
        presentation_correct = bool(expected_mids) and returned_mids == expected_mids
        citation_checks = [
            evidence.get(item["evidence_id"]) == item
            and chunk_by_evidence.get(item["evidence_id"], {}).get("source") == item["source"]
            and item["source"].get("page") is not None
            and bool(item["source"].get("url"))
            for item in found
        ]
        critical = result["status"] == "matched" and (
            case["expected_status"] != "matched"
            or not presentation_correct
            or (
                case.get("source_id") is not None
                and any(item["source"]["source_id"] != case["source_id"] for item in found)
            )
        )
        records.append(
            {
                "id": case["id"],
                "source_id": case.get("source_id"),
                "expected_status": case["expected_status"],
                "status": result["status"],
                "status_correct": result["status"] == case["expected_status"],
                "candidate_presentation_ids": _trace_candidates(case["question"], release),
                "selected_presentation_ids": result.get("candidate_presentation_ids", []),
                "candidate_chunk_count": result.get("candidate_chunk_count", 0),
                "filter_reason": result.get("message") if result["status"] != "matched" else None,
                "ranked_chunk_ids": result.get("ranked_chunk_ids", []),
                "expected_evidence_ids": case["relevant_ids"],
                "retrieved_evidence_ids": retrieved,
                "first_relevant_rank": rank,
                "presentation_correct": presentation_correct,
                "critical_confusion": critical,
                "citation_checks": citation_checks,
                "latency_ms": round(elapsed_ms, 3),
            }
        )
    negatives = [r for r in records if r["expected_status"] != "matched"]
    citation_checks = [check for record in records for check in record["citation_checks"]]

    def metrics(group: list[dict[str, Any]]) -> dict[str, Any]:
        positive = [r for r in group if r["expected_status"] == "matched"]
        return {
            "cases": len(group),
            "positive_cases": len(positive),
            "hit_at_1": sum(r["first_relevant_rank"] == 1 for r in positive) / len(positive)
            if positive
            else None,
            "hit_at_3": sum(
                r["first_relevant_rank"] is not None and r["first_relevant_rank"] <= 3
                for r in positive
            )
            / len(positive)
            if positive
            else None,
            "hit_at_5": sum(
                r["first_relevant_rank"] is not None and r["first_relevant_rank"] <= 5
                for r in positive
            )
            / len(positive)
            if positive
            else None,
            "mrr_at_5": sum(
                1 / r["first_relevant_rank"] if r["first_relevant_rank"] else 0 for r in positive
            )
            / len(positive)
            if positive
            else None,
            "status_accuracy": sum(r["status_correct"] for r in group) / len(group)
            if group
            else None,
            "presentation_accuracy": sum(r["presentation_correct"] for r in positive)
            / len(positive)
            if positive
            else None,
            "critical_confusions": sum(r["critical_confusion"] for r in group),
            "latency_p50_ms": _percentile([r["latency_ms"] for r in group], 0.5),
            "latency_p95_ms": _percentile([r["latency_ms"] for r in group], 0.95),
        }

    summary = metrics(records)
    summary.update(
        {
            "negative_cases": len(negatives),
            "correct_abstention": sum(r["status_correct"] for r in negatives) / len(negatives)
            if negatives
            else None,
            "citations": len(citation_checks),
            "citation_precision": sum(citation_checks) / len(citation_checks)
            if citation_checks
            else None,
        }
    )
    return {
        "schema_version": "consolidated-retrieval-eval-v1",
        "evaluated_at_utc": datetime.now(UTC).isoformat(),
        "release_version": release.manifest["release_version"],
        "release_fingerprint": release.fingerprint,
        "content_fingerprint": release.manifest.get("corpus_fingerprint"),
        "chunks_sha256": chunk_manifest["files"]["chunks.jsonl"]["sha256"],
        "dataset_sha256": sha256(dataset.read_bytes()).hexdigest(),
        "review_sha256": _review_hash(
            review_path,
            {case.get("review_reference_sha256", "") for case in cases if case["split"] == "test"},
        )
        if split == "test" and review_path
        else None,
        "git": _git_revision(release.folder.parents[2]),
        "python_version": platform.python_version(),
        "strategy": strategy,
        "embedding_model": embedding_model if store is not None else None,
        "split": split,
        "top_k": top_k,
        "reviewed_cases": sum(
            c.get("review_status") == "reviewed" and c["split"] == split for c in cases
        ),
        "summary": summary,
        "by_source": {
            source: metrics([r for r in records if r["source_id"] == source])
            for source in ("F01", "F03", "F04")
        },
        "results": records,
    }
