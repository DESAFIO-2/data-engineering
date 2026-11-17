"""Evaluate multi-chunk ranking strategies with atomic checkpointing and paired tests."""

from __future__ import annotations

import argparse
import json
import math
import os
import random
import re
import sys
import tempfile
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any, TextIO

from rag.config import ROOT, get_settings
from rag.consolidated import (
    ConsolidatedRelease,
    index_location,
    ingredient_key,
    load_chunks,
    normalize,
    open_index,
    search,
)
from rag.providers import error_detail, google_embeddings

REQUIRED_STRATEGIES: tuple[str, ...] = ("exact", "lexical", "vector", "hybrid")
VALID_STRATEGIES: frozenset[str] = frozenset(REQUIRED_STRATEGIES)
DEFAULT_RELEASE = ROOT / "data/releases/corpus-consolidado-v9-aprovado-2026-11-12"
DEFAULT_DATASET = ROOT / "evals/datasets/multichunk_v9_benchmark.jsonl"
DEFAULT_OUTPUT = ROOT / "evals/results/multichunk_v9_integracao_test.json"

DEFAULT_TOP_K = 5
DEFAULT_VECTOR_K_MIN = 10
DEFAULT_VECTOR_K_MULTIPLIER = 3
DEFAULT_RRF_K = 60
DEFAULT_BOOTSTRAP_RESAMPLES = 2000
DEFAULT_BOOTSTRAP_SEED = 42

_QUOTA_OR_AUTH_STOP_RE = re.compile(
    r"(?:per day limit exceeded|daily quota|requests per day|"
    r"resource[_ ]exhausted|quota exceeded|rate[ _-]?limit|"
    r"api[_ ]?key[_ ]?not[_ ]?valid|api_key_invalid|invalid[_ ]?api[_ ]?key|"
    r"permission[_ ]?denied|unauthenticated|unauthorized|\b(?:401|403|429)\b)",
    re.IGNORECASE,
)


class CallBudgetReached(RuntimeError):
    """Raised when the configured per-run API call budget is exhausted."""


def default_checkpoint_path(output_path: Path) -> Path:
    """Derive the deterministic checkpoint path from a target report path."""
    if output_path.suffix:
        return output_path.with_suffix(".checkpoint.json")
    return Path(f"{output_path}.checkpoint.json")


def default_query_cache_path(checkpoint_path: Path) -> Path:
    """Derive the optional persistent query-embedding cache path from a checkpoint path."""
    name = checkpoint_path.name
    if name.endswith(".checkpoint.json"):
        base = name[: -len(".checkpoint.json")]
        return checkpoint_path.with_name(f"{base}.query_embeddings.json")
    return checkpoint_path.with_name(f"{name}.query_embeddings.json")


def _sha256_bytes(raw: bytes) -> str:
    return sha256(raw).hexdigest()


def _canonical_json_sha256(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return _sha256_bytes(payload.encode("utf-8"))


def _normalized_file_sha256(path: Path) -> str:
    return _sha256_bytes(path.read_bytes().replace(b"\r\n", b"\n"))


def _case_sha256(case: dict[str, Any]) -> str:
    canonical_fields = {
        "id": case["id"],
        "split": case["split"],
        "family_id": case.get("family_id"),
        "clue_kind": case["clue_kind"],
        "source_id": case.get("source_id"),
        "presentation": case.get("presentation"),
        "question": case["question"],
        "expected_status": case.get("expected_status"),
        "relevant_ids": case["relevant_ids"],
        "candidate_chunk_count_verified": case.get("candidate_chunk_count_verified"),
        "release_fingerprint": case.get("release_fingerprint"),
    }
    return _canonical_json_sha256(canonical_fields)


def _code_hashes() -> dict[str, str]:
    files = (
        ROOT / "src/rag/consolidated.py",
        ROOT / "scripts/eval_multichunk_benchmark.py",
    )
    return {str(path.relative_to(ROOT)): _normalized_file_sha256(path) for path in files}


def atomic_write_text(path: Path, text: str) -> None:
    """Atomically persist UTF-8 text via temp file + fsync + replace in target directory."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(path.parent),
    )
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
    except BaseException:
        tmp_path.unlink(missing_ok=True)
        raise


def atomic_write_json(path: Path, payload: Any) -> None:
    """Atomically write a JSON object or array with UTF-8 encoding."""
    atomic_write_text(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def sanitize_error(exc: Exception, *, keys: Sequence[str] = ()) -> str:
    """Return a concise exception summary without exposing API keys or secrets."""
    secret_values = list(keys)
    for env_key, env_val in os.environ.items():
        if (
            env_val
            and len(env_val) >= 6
            and any(tag in env_key.upper() for tag in ("KEY", "TOKEN", "SECRET", "PASS", "AUTH"))
        ):
            secret_values.append(env_val)
    msg = error_detail(exc, keys=secret_values)
    msg = re.sub(r"(?i)bearer\s+\S+", "Bearer [REDACTED]", msg)
    msg = re.sub(
        r"(?i)(x-goog-api-key|authorization|token|secret|password)\s*[:=]\s*[^\s,;]+",
        r"\1=[REDACTED]",
        msg,
    )
    return msg


def _is_quota_or_auth_error(exc: Exception) -> bool:
    return bool(_QUOTA_OR_AUTH_STOP_RE.search(f"{type(exc).__name__}: {exc}"))


def _pres_key(ev: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        ingredient_key(ev["active_ingredient"]),
        normalize(ev["strength"]),
        normalize(ev["form"]),
        normalize(ev.get("release_characteristic") or ""),
    )


def percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    point = (len(ordered) - 1) * q
    low = int(point)
    return round(
        ordered[low] + (ordered[min(low + 1, len(ordered) - 1)] - ordered[low]) * (point - low),
        3,
    )


def bootstrap_ci(
    values: list[float],
    *,
    resamples: int = DEFAULT_BOOTSTRAP_RESAMPLES,
    seed: int = DEFAULT_BOOTSTRAP_SEED,
) -> dict[str, float] | None:
    """Compute deterministic percentile 95% bootstrap confidence interval for the mean."""
    if not values:
        return None
    rng = random.Random(seed)
    n = len(values)
    means: list[float] = []
    for _ in range(resamples):
        sample = [values[rng.randrange(n)] for _ in range(n)]
        means.append(sum(sample) / n)
    means.sort()
    low_idx = int(0.025 * (resamples - 1))
    high_idx = int(0.975 * (resamples - 1))
    return {
        "mean": round(sum(values) / n, 4),
        "ci95_low": round(means[low_idx], 4),
        "ci95_high": round(means[high_idx], 4),
    }


def _exact_mcnemar_log_p(wins: int, losses: int) -> float:
    n = wins + losses
    if n == 0:
        return 0.0
    k = min(wins, losses)
    if n <= 1000:
        numerator = sum(math.comb(n, i) for i in range(k + 1))
        val = min(1.0, math.ldexp(float(numerator), 1 - n))
        return math.log(val) if val > 0.0 else (1 - n) * math.log(2.0)
    log_terms = [
        math.lgamma(n + 1) - math.lgamma(i + 1) - math.lgamma(n - i + 1) - n * math.log(2.0)
        for i in range(k + 1)
    ]
    top = max(log_terms)
    log_tail = top + math.log(sum(math.exp(term - top) for term in log_terms))
    return min(0.0, math.log(2.0) + log_tail)


def exact_mcnemar_pvalue(wins: int, losses: int) -> float:
    """Exact two-sided binomial sign/McNemar test p-value; never rounds positive values to zero."""
    n = wins + losses
    if n == 0:
        return 1.0
    log_p = _exact_mcnemar_log_p(wins, losses)
    if log_p < math.log(sys.float_info.min):
        return sys.float_info.min
    p = min(1.0, math.exp(log_p))
    if p == 0.0:
        return sys.float_info.min
    return float(f"{p:.6g}")


def format_pvalue_scientific(wins: int, losses: int) -> str:
    """Format an exact McNemar p-value without ever printing zero."""
    n = wins + losses
    if n == 0:
        return "1.0"
    log_p = _exact_mcnemar_log_p(wins, losses)
    if log_p < math.log(sys.float_info.min):
        log10_p = log_p / math.log(10.0)
        exponent = math.floor(log10_p)
        mantissa = 10.0 ** (log10_p - exponent)
        return f"{mantissa:.4f}e{exponent:+d}"
    p = min(1.0, math.exp(log_p))
    return f"{p:.4e}" if p < 1e-3 else f"{p:.6g}"


def paired_hit1_comparison(
    candidate_hits: list[float], baseline_hits: list[float]
) -> dict[str, Any]:
    """Compare two paired binary Hit@1 series via exact McNemar and bootstrap delta CI."""
    wins = sum(1 for a, b in zip(candidate_hits, baseline_hits, strict=True) if a > b)
    losses = sum(1 for a, b in zip(candidate_hits, baseline_hits, strict=True) if a < b)
    ties = len(candidate_hits) - wins - losses
    deltas = [a - b for a, b in zip(candidate_hits, baseline_hits, strict=True)]
    return {
        "wins": wins,
        "losses": losses,
        "ties": ties,
        "mcnemar_p_value": exact_mcnemar_pvalue(wins, losses),
        "mcnemar_p_value_scientific": format_pvalue_scientific(wins, losses),
        "hit1_delta": bootstrap_ci(deltas),
    }


def paired_strategy_comparison(
    candidate_records: list[dict[str, Any]],
    baseline_records: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compare two aligned strategy record lists strictly on the same split and case order."""
    if not candidate_records or len(candidate_records) != len(baseline_records):
        raise ValueError("Comparação pareada exige o mesmo número não nulo de registros")
    cand_ids = [r["id"] for r in candidate_records]
    base_ids = [r["id"] for r in baseline_records]
    cand_splits = [r["split"] for r in candidate_records]
    base_splits = [r["split"] for r in baseline_records]
    if cand_ids != base_ids or cand_splits != base_splits:
        raise ValueError("Comparação pareada exige IDs e splits idênticos e alinhados")
    if any(r.get("error") is not None for r in (*candidate_records, *baseline_records)):
        raise ValueError("Comparação pareada exige todos os registros sem erros")

    cand_hit1 = [1.0 if r["first_relevant_rank"] == 1 else 0.0 for r in candidate_records]
    base_hit1 = [1.0 if r["first_relevant_rank"] == 1 else 0.0 for r in baseline_records]
    cand_hit5 = [
        1.0 if r["first_relevant_rank"] and r["first_relevant_rank"] <= 5 else 0.0
        for r in candidate_records
    ]
    base_hit5 = [
        1.0 if r["first_relevant_rank"] and r["first_relevant_rank"] <= 5 else 0.0
        for r in baseline_records
    ]
    cand_mrr = [
        1.0 / r["first_relevant_rank"] if r["first_relevant_rank"] else 0.0
        for r in candidate_records
    ]
    base_mrr = [
        1.0 / r["first_relevant_rank"] if r["first_relevant_rank"] else 0.0
        for r in baseline_records
    ]

    comparison = paired_hit1_comparison(cand_hit1, base_hit1)
    comparison["cases"] = len(candidate_records)
    comparison["splits"] = sorted(set(cand_splits))
    comparison["hit5_delta"] = bootstrap_ci(
        [a - b for a, b in zip(cand_hit5, base_hit5, strict=True)]
    )
    comparison["mrr5_delta"] = bootstrap_ci(
        [a - b for a, b in zip(cand_mrr, base_mrr, strict=True)]
    )
    return comparison


def summarize_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    completed = [r for r in records if r.get("error") is None]
    errors = sum(1 for r in records if r.get("error") is not None)
    hit1 = [1.0 if r.get("first_relevant_rank") == 1 else 0.0 for r in records]
    hit3 = [
        1.0 if r.get("first_relevant_rank") and r["first_relevant_rank"] <= 3 else 0.0
        for r in records
    ]
    hit5 = [
        1.0 if r.get("first_relevant_rank") and r["first_relevant_rank"] <= 5 else 0.0
        for r in records
    ]
    mrr = [1.0 / r["first_relevant_rank"] if r.get("first_relevant_rank") else 0.0 for r in records]
    latencies = [float(r["latency_ms"]) for r in records if r.get("latency_ms") is not None]
    cand_counts = [
        int(r["candidate_chunk_count"])
        for r in completed
        if r.get("candidate_chunk_count") is not None
    ]
    return {
        "cases": len(records),
        "completed_cases": len(completed),
        "errors": errors,
        "min_candidate_chunk_count": min(cand_counts) if cand_counts else 0,
        "hit_at_1": bootstrap_ci(hit1),
        "hit_at_1_count": int(sum(hit1)),
        "hit_at_3": round(sum(hit3) / len(hit3), 4) if hit3 else None,
        "hit_at_5": round(sum(hit5) / len(hit5), 4) if hit5 else None,
        "hit_at_5_count": int(sum(hit5)),
        "mrr_at_5": bootstrap_ci(mrr),
        "critical_confusions": sum(1 for r in records if r.get("critical_confusion")),
        "latency_p50_ms": percentile(latencies, 0.5),
        "latency_p95_ms": percentile(latencies, 0.95),
        "latency_mean_ms": round(sum(latencies) / len(latencies), 3) if latencies else None,
    }


def load_and_validate_dataset(
    dataset_path: Path,
    release: ConsolidatedRelease,
    split: str,
    *,
    frozen_dataset_sha256: str | None = None,
) -> tuple[list[dict[str, Any]], str, str]:
    """Load dataset, verify leak-free splits and gold labels, and filter to requested split."""
    if not dataset_path.is_file():
        raise FileNotFoundError(f"Dataset não encontrado: {dataset_path}")
    raw = dataset_path.read_bytes()
    raw_sha = _sha256_bytes(raw)
    lf_sha = _sha256_bytes(raw.replace(b"\r\n", b"\n"))
    if frozen_dataset_sha256 and frozen_dataset_sha256 not in {raw_sha, lf_sha}:
        raise ValueError(
            f"Hash do dataset divergente do congelado: esperado={frozen_dataset_sha256}, "
            f"obtido={lf_sha}"
        )
    dataset_sha256 = frozen_dataset_sha256 or lf_sha

    all_cases = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]
    if not all_cases:
        raise ValueError(f"Dataset vazio: {dataset_path}")
    if len({c["id"] for c in all_cases}) != len(all_cases):
        raise ValueError("Dataset possui IDs de caso duplicados")

    dev_families = {
        c["family_id"] for c in all_cases if c.get("split") == "dev" and "family_id" in c
    }
    test_families = {
        c["family_id"] for c in all_cases if c.get("split") == "test" and "family_id" in c
    }
    if dev_families & test_families:
        raise ValueError("Vazamento entre splits dev e test: family_id compartilhado")

    cases = all_cases if split == "all" else [c for c in all_cases if c.get("split") == split]
    if not cases:
        raise ValueError(f"Nenhum caso encontrado para split={split}")

    evidence_by_id = {ev["evidence_id"]: ev for ev in release.evidence}
    for case in cases:
        if case.get("release_fingerprint") != release.fingerprint:
            raise ValueError(
                f"Caso {case['id']} pertence a outro release ({case.get('release_fingerprint')})"
            )
        if case.get("expected_status") != "matched" or not case.get("relevant_ids"):
            raise ValueError(f"Gabarito inválido no caso {case['id']}")
        missing_eids = [eid for eid in case["relevant_ids"] if eid not in evidence_by_id]
        if missing_eids:
            raise ValueError(f"Evidências ausentes no release para {case['id']}: {missing_eids}")
        verified = case.get("candidate_chunk_count_verified")
        if verified is not None and int(verified) < 3:
            raise ValueError(f"Caso {case['id']} possui menos de 3 chunks verificados ({verified})")

    split_cases_sha256 = _canonical_json_sha256(cases)
    return cases, dataset_sha256, split_cases_sha256


def verify_vector_index(
    release: ConsolidatedRelease,
    chunks: list[dict[str, Any]],
    chunk_manifest: dict[str, Any],
    vector_dir: Path,
    embedding_model: str,
) -> tuple[Path, dict[str, Any], str]:
    """Verify local vector index marker, all chunk IDs/texts, and vector dimensions offline."""
    location = index_location(vector_dir, release, chunk_manifest, embedding_model)
    marker_path = location / "index.json"
    if not marker_path.is_file():
        raise FileNotFoundError(
            f"Índice consolidado não construído em '{location}' "
            f"(marcador {marker_path.name} ausente)."
        )
    marker_bytes = marker_path.read_bytes()
    marker = json.loads(marker_bytes)
    open_index(release, chunks, chunk_manifest, vector_dir, embedding_model, None)
    return location, marker, _sha256_bytes(marker_bytes)


class TrackedEmbeddings:
    """Wrap an embeddings client with per-case dedup, optional disk cache, and strict call cap."""

    def __init__(
        self,
        inner: Any,
        *,
        embedding_model: str,
        max_new_calls: int | None = None,
        cache_across_queries: bool = False,
        cache_path: Path | None = None,
    ) -> None:
        self._inner = inner
        self.embedding_model = embedding_model
        self.max_new_calls = max_new_calls
        self.cache_across_queries = cache_across_queries
        self.cache_path = cache_path
        self.new_calls = 0
        self.cache_hits = 0
        self.last_case_calls = 0
        self.last_case_cache_hit = False
        self._per_case_cache: dict[str, list[float]] = {}
        self._persistent_cache: dict[str, list[float]] = {}
        if cache_across_queries and cache_path is not None and cache_path.is_file():
            data = json.loads(cache_path.read_text(encoding="utf-8"))
            if data.get("embedding_model") != embedding_model:
                raise ValueError(
                    "Cache de embeddings de consulta incompatível com o modelo configurado: "
                    f"{data.get('embedding_model')} != {embedding_model}"
                )
            vectors = data.get("vectors", {})
            if isinstance(vectors, dict):
                self._persistent_cache = {str(k): [float(x) for x in v] for k, v in vectors.items()}

    def begin_case(self) -> None:
        self.last_case_calls = 0
        self.last_case_cache_hit = False
        self._per_case_cache.clear()

    def will_call_api(self, question: str) -> bool:
        if self.cache_across_queries and question in self._persistent_cache:
            return False
        return question not in self._per_case_cache

    def _save_persistent_cache(self) -> None:
        if self.cache_path is None:
            return
        atomic_write_json(
            self.cache_path,
            {
                "schema_version": "multichunk-query-cache-v1",
                "embedding_model": self.embedding_model,
                "vectors": self._persistent_cache,
            },
        )

    def embed_query(self, text: str) -> list[float]:
        if self.cache_across_queries and text in self._persistent_cache:
            self.cache_hits += 1
            self.last_case_cache_hit = True
            return self._persistent_cache[text]
        if text in self._per_case_cache:
            self.cache_hits += 1
            self.last_case_cache_hit = True
            return self._per_case_cache[text]
        if self.max_new_calls is not None and self.new_calls >= self.max_new_calls:
            raise CallBudgetReached(
                f"Limite de novas chamadas atingido ({self.new_calls}/{self.max_new_calls})."
            )
        self.new_calls += 1
        self.last_case_calls += 1
        vector = [float(x) for x in self._inner.embed_query(text)]
        self._per_case_cache[text] = vector
        if self.cache_across_queries:
            self._persistent_cache[text] = vector
            self._save_persistent_cache()
        return vector

    def embed_documents(self, _texts: list[str]) -> list[list[float]]:
        raise RuntimeError("embed_documents não deve ser chamado durante a avaliação de consultas")


class _CacheOnlyEmbeddings:
    """Fallback inner client when max_new_calls=0 so cache hits run without API credentials."""

    def embed_query(self, _text: str) -> list[float]:
        raise CallBudgetReached("Orçamento max_new_calls=0 não permite novas chamadas à API.")

    def embed_documents(self, _texts: list[str]) -> list[list[float]]:
        raise RuntimeError("embed_documents não deve ser chamado durante a avaliação de consultas")


def _build_parameters(
    *,
    top_k: int = DEFAULT_TOP_K,
    cache_query_embeddings: bool = False,
) -> dict[str, Any]:
    return {
        "top_k": top_k,
        "vector_k_min": DEFAULT_VECTOR_K_MIN,
        "vector_k_multiplier": DEFAULT_VECTOR_K_MULTIPLIER,
        "rrf_k": DEFAULT_RRF_K,
        "cache_query_embeddings": cache_query_embeddings,
        "bootstrap_resamples": DEFAULT_BOOTSTRAP_RESAMPLES,
        "bootstrap_seed": DEFAULT_BOOTSTRAP_SEED,
    }


def _build_checkpoint_config(
    *,
    release: ConsolidatedRelease,
    chunks_sha256: str,
    dataset_sha256: str,
    split_cases_sha256: str,
    split: str,
    strategies: tuple[str, ...],
    embedding_model: str | None,
    index_marker_sha256: str | None,
    parameters: dict[str, Any],
    code_sha256: dict[str, str],
) -> dict[str, Any]:
    return {
        "release_version": release.manifest["release_version"],
        "release_fingerprint": release.fingerprint,
        "chunks_sha256": chunks_sha256,
        "dataset_sha256": dataset_sha256,
        "split_cases_sha256": split_cases_sha256,
        "split": split,
        "strategies": list(strategies),
        "embedding_model": embedding_model,
        "index_marker_sha256": index_marker_sha256,
        "parameters": parameters,
        "code_sha256": code_sha256,
    }


def _validate_checkpoint(
    checkpoint: dict[str, Any],
    expected_config: dict[str, Any],
    cases: list[dict[str, Any]],
) -> None:
    if checkpoint.get("schema_version") != "multichunk-checkpoint-v1":
        raise ValueError(f"Versão de checkpoint incompatível: {checkpoint.get('schema_version')!r}")
    saved_config = checkpoint.get("config")
    if not isinstance(saved_config, dict):
        raise ValueError("Checkpoint sem bloco 'config' válido")

    mismatches: list[str] = []
    for key, expected_val in expected_config.items():
        if saved_config.get(key) != expected_val:
            mismatches.append(f"{key} (salvo={saved_config.get(key)!r} != atual={expected_val!r})")
    if mismatches:
        raise ValueError("Configuração incompatível na retomada: " + "; ".join(mismatches))

    raw_records = checkpoint.get("records")
    if not isinstance(raw_records, dict):
        raise ValueError("Checkpoint sem bloco 'records' válido")

    cases_by_id = {c["id"]: c for c in cases}
    expected_strategies = set(expected_config["strategies"])
    for strategy, bucket in raw_records.items():
        if strategy not in expected_strategies:
            raise ValueError(f"Estratégia inesperada no checkpoint: {strategy!r}")
        if not isinstance(bucket, dict):
            raise ValueError(f"Registros inválidos para estratégia {strategy!r}")
        expected_emb = (
            expected_config["embedding_model"] if strategy in {"vector", "hybrid"} else None
        )
        for case_id, rec in bucket.items():
            if case_id not in cases_by_id:
                raise ValueError(f"Caso inesperado no checkpoint: {strategy}/{case_id}")
            if not isinstance(rec, dict):
                raise ValueError(f"Registro corrompido no checkpoint: {strategy}/{case_id}")
            case = cases_by_id[case_id]
            checks = (
                rec.get("id") == case_id,
                rec.get("split") == case["split"],
                rec.get("strategy") == strategy,
                rec.get("case_sha256") == _case_sha256(case),
                rec.get("release_fingerprint") == expected_config["release_fingerprint"],
                rec.get("chunks_sha256") == expected_config["chunks_sha256"],
                rec.get("dataset_sha256") == expected_config["dataset_sha256"],
                rec.get("embedding_model") == expected_emb,
                rec.get("parameters") == expected_config["parameters"],
            )
            if not all(checks):
                raise ValueError(
                    f"Metadados/hashes do registro divergem na retomada: {strategy}/{case_id}"
                )


def _compute_paired_comparisons(
    per_strategy: dict[str, list[dict[str, Any]]], strategies: Sequence[str]
) -> dict[str, Any]:
    comparisons: dict[str, Any] = {}
    pairs: list[tuple[str, str, str]] = [
        ("exact_vs_lexical", "exact", "lexical"),
        ("lexical_vs_exact", "lexical", "exact"),
        ("vector_vs_exact", "vector", "exact"),
        ("hybrid_vs_exact", "hybrid", "exact"),
        ("vector_vs_lexical", "vector", "lexical"),
        ("hybrid_vs_lexical", "hybrid", "lexical"),
        ("hybrid_vs_vector", "hybrid", "vector"),
    ]
    present = set(strategies)
    for label, cand, base in pairs:
        if cand in present and base in present:
            comparisons[label] = paired_strategy_comparison(per_strategy[cand], per_strategy[base])
    return comparisons


def build_final_report(
    checkpoint: dict[str, Any],
    *,
    cases: list[dict[str, Any]],
    require_all_strategies: bool = True,
) -> dict[str, Any]:
    """Assemble final summary and paired comparisons only when completeness gates pass."""
    config = checkpoint["config"]
    strategies = tuple(config["strategies"])
    if require_all_strategies and set(strategies) != set(REQUIRED_STRATEGIES):
        missing = [s for s in REQUIRED_STRATEGIES if s not in strategies]
        raise ValueError(
            f"Resumo final exige todas as 4 estratégias {REQUIRED_STRATEGIES}; faltando: {missing}"
        )

    raw_records = checkpoint["records"]
    per_strategy: dict[str, list[dict[str, Any]]] = {}
    incomplete_details: list[str] = []

    target_strategies = REQUIRED_STRATEGIES if require_all_strategies else strategies
    for strategy in target_strategies:
        bucket = raw_records.get(strategy, {})
        ordered: list[dict[str, Any]] = []
        missing_ids = [c["id"] for c in cases if c["id"] not in bucket]
        if missing_ids:
            incomplete_details.append(f"{strategy}: faltam {len(missing_ids)} casos")
            continue
        error_ids = [c["id"] for c in cases if bucket[c["id"]].get("error") is not None]
        if error_ids:
            incomplete_details.append(f"{strategy}: {len(error_ids)} casos com erro")
            continue
        for case in cases:
            ordered.append(bucket[case["id"]])
        per_strategy[strategy] = ordered

    if incomplete_details:
        raise ValueError(
            "Resumo final bloqueado até concluir todos os casos nas 4 estratégias sem erros: "
            + "; ".join(incomplete_details)
        )

    summaries: dict[str, Any] = {}
    for strategy, recs in per_strategy.items():
        by_kind = {
            kind: summarize_records([r for r in recs if r["clue_kind"] == kind])
            for kind in sorted({r["clue_kind"] for r in recs})
        }
        summaries[strategy] = {
            **summarize_records(recs),
            "by_clue_kind": by_kind,
        }

    ordered_strategies = list(target_strategies)
    comparisons = _compute_paired_comparisons(per_strategy, ordered_strategies)

    clue_kinds = sorted({c["clue_kind"] for c in cases})
    comparisons_by_kind: dict[str, Any] = {}
    for kind in clue_kinds:
        sub_records = {
            strategy: [r for r in per_strategy[strategy] if r["clue_kind"] == kind]
            for strategy in ordered_strategies
        }
        comparisons_by_kind[kind] = _compute_paired_comparisons(sub_records, ordered_strategies)

    return {
        "schema_version": "multichunk-benchmark-v2",
        "executed_at_utc": datetime.now(UTC).isoformat(),
        "release_version": config["release_version"],
        "release_fingerprint": config["release_fingerprint"],
        "chunks_sha256": config["chunks_sha256"],
        "dataset_sha256": config["dataset_sha256"],
        "split_cases_sha256": config["split_cases_sha256"],
        "split": config["split"],
        "total_cases": len(cases),
        "strategies": ordered_strategies,
        "embedding_model": config["embedding_model"],
        "index_marker_sha256": config["index_marker_sha256"],
        "parameters": config["parameters"],
        "code_sha256": config["code_sha256"],
        "summaries": summaries,
        "paired_comparisons": comparisons,
        "paired_comparisons_by_clue_kind": comparisons_by_kind,
        "records": per_strategy,
    }


@dataclass(frozen=True)
class BenchmarkRunResult:
    """Structured outcome of a resumable multi-chunk benchmark run."""

    completed: bool
    stopped_reason: str | None
    report: dict[str, Any] | None
    checkpoint_path: Path
    new_api_calls: int
    reused_records: int
    executed_records: int
    error_records: int
    pending_by_strategy: dict[str, int]
    index_verified: dict[str, Any] | None


def _pending_counts(
    checkpoint: dict[str, Any],
    cases: list[dict[str, Any]],
    strategies: Sequence[str],
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for strategy in strategies:
        bucket = checkpoint["records"].get(strategy, {})
        counts[strategy] = sum(
            1
            for case in cases
            if case["id"] not in bucket or bucket[case["id"]].get("error") is not None
        )
    return counts


def _log_progress(stream: TextIO, message: str) -> None:
    print(message, file=stream, flush=True)


def _build_case_record(
    *,
    case: dict[str, Any],
    strategy: str,
    candidate_chunk_count: int | None,
    status: str,
    first_relevant_rank: int | None,
    returned_evidence_ids: list[str],
    critical_confusion: bool,
    latency_ms: float,
    error: str | None,
    embedding_calls: int,
    query_embedding_cached: bool,
    embedding_model: str | None,
    release_fingerprint: str,
    chunks_sha256: str,
    dataset_sha256: str,
    parameters: dict[str, Any],
) -> dict[str, Any]:
    return {
        "id": case["id"],
        "split": case["split"],
        "strategy": strategy,
        "clue_kind": case["clue_kind"],
        "candidate_chunk_count": candidate_chunk_count,
        "status": status,
        "first_relevant_rank": first_relevant_rank,
        "returned_evidence_ids": returned_evidence_ids,
        "expected_evidence_ids": case["relevant_ids"],
        "critical_confusion": critical_confusion,
        "latency_ms": latency_ms,
        "error": error,
        "embedding_calls": embedding_calls,
        "query_embedding_cached": query_embedding_cached,
        "embedding_model": embedding_model if strategy in {"vector", "hybrid"} else None,
        "release_fingerprint": release_fingerprint,
        "chunks_sha256": chunks_sha256,
        "dataset_sha256": dataset_sha256,
        "case_sha256": _case_sha256(case),
        "parameters": parameters,
        "recorded_at_utc": datetime.now(UTC).isoformat(),
    }


def _persist_case_record(
    checkpoint: dict[str, Any],
    checkpoint_path: Path | None,
    strategy: str,
    case_id: str,
    record: dict[str, Any],
) -> None:
    checkpoint["records"].setdefault(strategy, {})[case_id] = record
    checkpoint["updated_at_utc"] = datetime.now(UTC).isoformat()
    if checkpoint_path is not None:
        atomic_write_json(checkpoint_path, checkpoint)


def _format_progress_line(
    *,
    strategy: str,
    completed_in_strategy: int,
    total_in_strategy: int,
    case_id: str,
    outcome: str,
    elapsed_ms: float,
    remaining_strategy: int,
    remaining_total: int,
    used_calls: int,
    max_new_calls: int | None,
) -> str:
    budget = (
        f" | chamadas_novas={used_calls}/{max_new_calls}"
        if max_new_calls is not None
        else f" | chamadas_novas={used_calls}"
    )
    return (
        f"[{strategy}] {completed_in_strategy}/{total_in_strategy} | {case_id} | "
        f"{outcome} | {elapsed_ms:.1f} ms | restante_estrategia={remaining_strategy} | "
        f"restante_total={remaining_total}{budget}"
    )


def _open_tracked_store(
    *,
    release: ConsolidatedRelease,
    chunks: list[dict[str, Any]],
    chunk_manifest: dict[str, Any],
    vector_dir: Path,
    embedding_model: str,
    embeddings: Any,
    settings_keys: tuple[str, ...],
    max_new_calls: int | None,
    cache_query_embeddings: bool,
    checkpoint_path: Path | None,
) -> tuple[Any, TrackedEmbeddings]:
    raw_embeddings: Any
    if max_new_calls == 0:
        raw_embeddings = _CacheOnlyEmbeddings()
    elif embeddings is not None:
        raw_embeddings = embeddings
    else:
        raw_embeddings = google_embeddings(embedding_model, settings_keys)
    cache_file = (
        default_query_cache_path(checkpoint_path)
        if cache_query_embeddings and checkpoint_path is not None
        else None
    )
    tracked = TrackedEmbeddings(
        raw_embeddings,
        embedding_model=embedding_model,
        max_new_calls=max_new_calls,
        cache_across_queries=cache_query_embeddings,
        cache_path=cache_file,
    )
    opened = open_index(
        release,
        chunks,
        chunk_manifest,
        vector_dir,
        embedding_model,
        tracked,
    )
    return opened, tracked


def run_benchmark(
    *,
    release_dir: Path,
    dataset_path: Path,
    strategies: tuple[str, ...] = REQUIRED_STRATEGIES,
    split: str = "test",
    output_path: Path | None = None,
    checkpoint_path: Path | None = None,
    chunks_dir: Path | None = None,
    vector_dir: Path | None = None,
    embedding_model: str | None = None,
    embeddings: Any = None,
    store: Any = None,
    max_new_calls: int | None = None,
    request_delay: float = 0.0,
    cache_query_embeddings: bool = False,
    stop_on_error: bool = False,
    frozen_dataset_sha256: str | None = None,
    require_all_strategies: bool = True,
    summarize_only: bool = False,
    sleep_fn: Callable[[float], None] | None = None,
    progress_stream: TextIO = sys.stderr,
) -> BenchmarkRunResult:
    """Run or resume the multi-chunk benchmark with atomic per-case checkpointing."""
    resolved_sleep = sleep_fn or time.sleep
    if not strategies or len(set(strategies)) != len(strategies):
        raise ValueError("Lista de estratégias vazia ou duplicada")
    if any(s not in VALID_STRATEGIES for s in strategies):
        raise ValueError(f"Estratégia inválida em {strategies}; permitidas: {REQUIRED_STRATEGIES}")
    if max_new_calls is not None and max_new_calls < 0:
        raise ValueError("--max-new-calls deve ser >= 0")
    if request_delay < 0:
        raise ValueError("--request-delay deve ser >= 0")

    settings = get_settings()
    resolved_vector_dir = vector_dir if vector_dir is not None else ROOT / settings.rag_vector_dir
    uses_vector = any(s in {"vector", "hybrid"} for s in strategies)
    resolved_model = (
        (embedding_model or settings.rag_embedding_model) if uses_vector else embedding_model
    )

    release = ConsolidatedRelease.load(release_dir)
    resolved_chunks_dir = (
        chunks_dir
        if chunks_dir is not None
        else ROOT / "data/derived/chunks" / release.manifest["release_version"]
    )
    chunks, chunk_manifest = load_chunks(release, resolved_chunks_dir)
    chunks_sha256 = chunk_manifest["files"]["chunks.jsonl"]["sha256"]
    cases, dataset_sha256, split_cases_sha256 = load_and_validate_dataset(
        dataset_path, release, split, frozen_dataset_sha256=frozen_dataset_sha256
    )

    index_verified: dict[str, Any] | None = None
    index_marker_sha256: str | None = None
    if uses_vector and store is None:
        assert resolved_model is not None
        location, marker, index_marker_sha256 = verify_vector_index(
            release, chunks, chunk_manifest, resolved_vector_dir, resolved_model
        )
        index_verified = {
            "location": str(location),
            "count": marker["count"],
            "embedding_model": marker["embedding_model"],
            "embedding_dimension": marker["embedding_dimension"],
            "marker_sha256": index_marker_sha256,
        }
        _log_progress(
            progress_stream,
            f"[index] verificado localmente: {marker['count']}/{len(chunks)} IDs, "
            f"dim={marker['embedding_dimension']}, modelo={marker['embedding_model']}, "
            "0 chamadas à API",
        )

    parameters = _build_parameters(
        top_k=DEFAULT_TOP_K,
        cache_query_embeddings=cache_query_embeddings,
    )
    expected_config = _build_checkpoint_config(
        release=release,
        chunks_sha256=chunks_sha256,
        dataset_sha256=dataset_sha256,
        split_cases_sha256=split_cases_sha256,
        split=split,
        strategies=strategies,
        embedding_model=resolved_model,
        index_marker_sha256=index_marker_sha256,
        parameters=parameters,
        code_sha256=_code_hashes(),
    )

    resolved_checkpoint = (
        checkpoint_path
        if checkpoint_path is not None
        else (default_checkpoint_path(output_path) if output_path is not None else None)
    )
    if resolved_checkpoint is not None and resolved_checkpoint.is_file():
        checkpoint = json.loads(resolved_checkpoint.read_text(encoding="utf-8"))
        _validate_checkpoint(checkpoint, expected_config, cases)
    else:
        if summarize_only:
            raise FileNotFoundError(
                f"Checkpoint ausente para --summarize-only: {resolved_checkpoint}"
            )
        checkpoint = {
            "schema_version": "multichunk-checkpoint-v1",
            "created_at_utc": datetime.now(UTC).isoformat(),
            "updated_at_utc": datetime.now(UTC).isoformat(),
            "config": expected_config,
            "records": {s: {} for s in strategies},
        }

    pending_map = _pending_counts(checkpoint, cases, strategies)
    reused_records = sum(
        1
        for strategy in strategies
        for case in cases
        if case["id"] in checkpoint["records"].get(strategy, {})
        and checkpoint["records"][strategy][case["id"]].get("error") is None
    )
    total_pending = sum(pending_map.values())
    _log_progress(
        progress_stream,
        f"[retomada] reutilizados={reused_records} | pendentes={total_pending} | "
        f"por_estrategia={pending_map}",
    )

    if summarize_only:
        summary_report = build_final_report(
            checkpoint,
            cases=cases,
            require_all_strategies=require_all_strategies,
        )
        if output_path is not None:
            atomic_write_json(output_path, summary_report)
        return BenchmarkRunResult(
            completed=True,
            stopped_reason=None,
            report=summary_report,
            checkpoint_path=resolved_checkpoint or Path(),
            new_api_calls=0,
            reused_records=reused_records,
            executed_records=0,
            error_records=0,
            pending_by_strategy={s: 0 for s in strategies},
            index_verified=index_verified,
        )

    pending_vector = sum(pending_map.get(s, 0) for s in strategies if s in {"vector", "hybrid"})
    tracked_embeddings: TrackedEmbeddings | None = None
    active_store = store
    if (
        uses_vector
        and pending_vector > 0
        and active_store is None
        and (max_new_calls is None or max_new_calls > 0 or cache_query_embeddings)
    ):
        assert resolved_model is not None
        active_store, tracked_embeddings = _open_tracked_store(
            release=release,
            chunks=chunks,
            chunk_manifest=chunk_manifest,
            vector_dir=resolved_vector_dir,
            embedding_model=resolved_model,
            embeddings=embeddings,
            settings_keys=settings.google_api_keys,
            max_new_calls=max_new_calls,
            cache_query_embeddings=cache_query_embeddings,
            checkpoint_path=resolved_checkpoint,
        )

    evidence_by_id = {ev["evidence_id"]: ev for ev in release.evidence}
    configured_keys = settings.google_api_keys
    executed_records = 0
    error_records = 0
    external_vector_calls = 0
    stopped_reason: str | None = None
    remaining_total = total_pending

    def _current_api_calls() -> int:
        if tracked_embeddings is not None:
            return tracked_embeddings.new_calls
        return external_vector_calls

    for strategy in strategies:
        bucket = checkpoint["records"].setdefault(strategy, {})
        remaining_strategy = pending_map[strategy]
        completed_in_strategy = len(cases) - remaining_strategy

        for case in cases:
            existing = bucket.get(case["id"])
            if existing is not None and existing.get("error") is None:
                continue

            is_vector_strategy = strategy in {"vector", "hybrid"}
            if is_vector_strategy:
                if tracked_embeddings is not None:
                    tracked_embeddings.begin_case()
                    needs_api = tracked_embeddings.will_call_api(case["question"])
                else:
                    needs_api = True
                used_calls = _current_api_calls()
                if needs_api and max_new_calls is not None and used_calls >= max_new_calls:
                    stopped_reason = "max_new_calls"
                    _log_progress(
                        progress_stream,
                        f"[limite] orçamento de {max_new_calls} chamadas novas atingido antes de "
                        f"{strategy}/{case['id']}; restante_total={remaining_total}",
                    )
                    break
                if needs_api and used_calls > 0 and request_delay > 0:
                    resolved_sleep(request_delay)

            started = time.perf_counter()
            try:
                res = search(
                    case["question"],
                    release,
                    chunks,
                    store=active_store,
                    strategy=strategy,
                    top_k=DEFAULT_TOP_K,
                )
                elapsed_ms = round((time.perf_counter() - started) * 1000, 3)
                cand_count = int(res.get("candidate_chunk_count") or 0)
                if cand_count < 3:
                    raise ValueError(
                        f"Caso {case['id']} caiu abaixo de 3 chunks candidatos ({cand_count})"
                    )
                found = res.get("evidence", [])
                ids = [ev["evidence_id"] for ev in found]
                relevant = set(case["relevant_ids"])
                rank = next((i for i, eid in enumerate(ids, 1) if eid in relevant), None)
                expected_pres = {_pres_key(evidence_by_id[eid]) for eid in relevant}
                found_pres = {_pres_key(ev) for ev in found}
                if is_vector_strategy and tracked_embeddings is None:
                    external_vector_calls += 1
                calls_here = (
                    tracked_embeddings.last_case_calls
                    if (is_vector_strategy and tracked_embeddings is not None)
                    else (1 if is_vector_strategy else 0)
                )
                cached_here = (
                    tracked_embeddings.last_case_cache_hit
                    if (is_vector_strategy and tracked_embeddings is not None)
                    else False
                )
                record = _build_case_record(
                    case=case,
                    strategy=strategy,
                    candidate_chunk_count=cand_count,
                    status=res["status"],
                    first_relevant_rank=rank,
                    returned_evidence_ids=ids,
                    critical_confusion=res["status"] != "matched" or found_pres != expected_pres,
                    latency_ms=elapsed_ms,
                    error=None,
                    embedding_calls=calls_here,
                    query_embedding_cached=cached_here,
                    embedding_model=resolved_model,
                    release_fingerprint=release.fingerprint,
                    chunks_sha256=chunks_sha256,
                    dataset_sha256=dataset_sha256,
                    parameters=parameters,
                )
                _persist_case_record(checkpoint, resolved_checkpoint, strategy, case["id"], record)
                executed_records += 1
                completed_in_strategy += 1
                remaining_strategy -= 1
                remaining_total -= 1
                _log_progress(
                    progress_stream,
                    _format_progress_line(
                        strategy=strategy,
                        completed_in_strategy=completed_in_strategy,
                        total_in_strategy=len(cases),
                        case_id=case["id"],
                        outcome="ok",
                        elapsed_ms=elapsed_ms,
                        remaining_strategy=remaining_strategy,
                        remaining_total=remaining_total,
                        used_calls=_current_api_calls(),
                        max_new_calls=max_new_calls,
                    ),
                )
            except CallBudgetReached:
                stopped_reason = "max_new_calls"
                _log_progress(
                    progress_stream,
                    f"[limite] orçamento de {max_new_calls} chamadas novas atingido durante "
                    f"{strategy}/{case['id']}; restante_total={remaining_total}",
                )
                break
            except Exception as exc:
                elapsed_ms = round((time.perf_counter() - started) * 1000, 3)
                if is_vector_strategy and tracked_embeddings is None:
                    external_vector_calls += 1
                error_records += 1
                calls_here = (
                    tracked_embeddings.last_case_calls
                    if (is_vector_strategy and tracked_embeddings is not None)
                    else (1 if is_vector_strategy else 0)
                )
                record = _build_case_record(
                    case=case,
                    strategy=strategy,
                    candidate_chunk_count=None,
                    status="error",
                    first_relevant_rank=None,
                    returned_evidence_ids=[],
                    critical_confusion=False,
                    latency_ms=elapsed_ms,
                    error=sanitize_error(exc, keys=configured_keys),
                    embedding_calls=calls_here,
                    query_embedding_cached=False,
                    embedding_model=resolved_model,
                    release_fingerprint=release.fingerprint,
                    chunks_sha256=chunks_sha256,
                    dataset_sha256=dataset_sha256,
                    parameters=parameters,
                )
                _persist_case_record(checkpoint, resolved_checkpoint, strategy, case["id"], record)
                executed_records += 1
                _log_progress(
                    progress_stream,
                    _format_progress_line(
                        strategy=strategy,
                        completed_in_strategy=completed_in_strategy,
                        total_in_strategy=len(cases),
                        case_id=case["id"],
                        outcome=f"err={type(exc).__name__}",
                        elapsed_ms=elapsed_ms,
                        remaining_strategy=remaining_strategy,
                        remaining_total=remaining_total,
                        used_calls=_current_api_calls(),
                        max_new_calls=max_new_calls,
                    ),
                )
                if stop_on_error or _is_quota_or_auth_error(exc):
                    stopped_reason = "error"
                    break

        if stopped_reason is not None:
            break

    final_pending = _pending_counts(checkpoint, cases, strategies)
    all_target_strategies = set(strategies) == set(REQUIRED_STRATEGIES)
    all_cases_done = all(count == 0 for count in final_pending.values()) and (
        not require_all_strategies or all_target_strategies
    )

    report: dict[str, Any] | None = None
    if all_cases_done:
        report = build_final_report(
            checkpoint,
            cases=cases,
            require_all_strategies=require_all_strategies,
        )
        if output_path is not None:
            atomic_write_json(output_path, report)
    elif stopped_reason is None:
        stopped_reason = "incomplete_errors" if error_records > 0 else "incomplete_strategies"

    return BenchmarkRunResult(
        completed=all_cases_done,
        stopped_reason=stopped_reason,
        report=report,
        checkpoint_path=resolved_checkpoint or Path(),
        new_api_calls=_current_api_calls(),
        reused_records=reused_records,
        executed_records=executed_records,
        error_records=error_records,
        pending_by_strategy=final_pending,
        index_verified=index_verified,
    )


def evaluate_multichunk(
    *,
    release_dir: Path,
    dataset_path: Path,
    strategies: tuple[str, ...],
    split: str = "all",
    store: Any = None,
    chunks_dir: Path | None = None,
    checkpoint_path: Path | None = None,
    max_new_calls: int | None = None,
    request_delay: float = 0.0,
    require_all_strategies: bool = False,
    progress_stream: TextIO = sys.stderr,
) -> dict[str, Any]:
    """Run multi-chunk ranking evaluation and return full structured metrics."""
    result = run_benchmark(
        release_dir=release_dir,
        dataset_path=dataset_path,
        strategies=strategies,
        split=split,
        chunks_dir=chunks_dir,
        checkpoint_path=checkpoint_path,
        store=store,
        max_new_calls=max_new_calls,
        request_delay=request_delay,
        require_all_strategies=require_all_strategies,
        progress_stream=progress_stream,
    )
    if result.report is None:
        raise ValueError(
            f"Avaliação incompleta ({result.stopped_reason}): "
            f"pendentes={result.pending_by_strategy}"
        )
    return result.report


def _format_human_summary(report: dict[str, Any]) -> str:
    lines: list[str] = [
        f"Resumo Multi-Chunk ({report['split']}, n={report['total_cases']}):",
        "estrategia | hit@1 | hit@5 | mrr@5 | confusoes | erros | p50_ms | p95_ms",
    ]
    for strategy in report["strategies"]:
        s = report["summaries"][strategy]
        h1 = s["hit_at_1"]["mean"] if s["hit_at_1"] else None
        mrr = s["mrr_at_5"]["mean"] if s["mrr_at_5"] else None
        lines.append(
            f"{strategy:10s} | {h1} ({s['hit_at_1_count']}/{s['cases']}) | "
            f"{s['hit_at_5']} | {mrr} | {s['critical_confusions']} | {s['errors']} | "
            f"{s['latency_p50_ms']} | {s['latency_p95_ms']}"
        )
        for kind, ks in s["by_clue_kind"].items():
            kh1 = ks["hit_at_1"]["mean"] if ks["hit_at_1"] else None
            kmrr = ks["mrr_at_5"]["mean"] if ks["mrr_at_5"] else None
            lines.append(
                f"  - {kind:20s} | {kh1} ({ks['hit_at_1_count']}/{ks['cases']}) | "
                f"{ks['hit_at_5']} | {kmrr} | {ks['critical_confusions']} | {ks['errors']} | "
                f"{ks['latency_p50_ms']} | {ks['latency_p95_ms']}"
            )
    lines.append("Comparações pareadas (mesmo split):")
    for label, comp in report["paired_comparisons"].items():
        delta = comp["hit1_delta"]["mean"] if comp["hit1_delta"] else None
        lines.append(
            f"  {label}: wins={comp['wins']}, losses={comp['losses']}, ties={comp['ties']}, "
            f"delta_hit1={delta}, p={comp['mcnemar_p_value_scientific']}"
        )
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release", type=Path, default=DEFAULT_RELEASE)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--checkpoint", type=Path, default=None)
    parser.add_argument("--chunks-dir", type=Path, default=None)
    parser.add_argument("--vector-dir", type=Path, default=None)
    parser.add_argument("--embedding-model", default=None)
    parser.add_argument("--split", choices=("dev", "test", "all"), default="test")
    parser.add_argument(
        "--strategies",
        default=",".join(REQUIRED_STRATEGIES),
        help="Estratégias separadas por vírgula (padrão: exact,lexical,vector,hybrid)",
    )
    parser.add_argument("--include-vector", action="store_true")
    parser.add_argument(
        "--max-new-calls",
        type=int,
        default=None,
        help="Limita o número máximo de novas chamadas à API de embeddings nesta execução",
    )
    parser.add_argument(
        "--request-delay",
        type=float,
        default=0.0,
        help="Intervalo em segundos entre novas chamadas à API de embeddings",
    )
    parser.add_argument(
        "--cache-query-embeddings",
        action="store_true",
        help="Cacheia embeddings de consulta entre vector e hybrid (reduz chamadas pela metade)",
    )
    parser.add_argument("--stop-on-error", action="store_true")
    parser.add_argument("--frozen-dataset-sha256", default=None)
    parser.add_argument("--verify-index-only", action="store_true")
    parser.add_argument("--summarize-only", action="store_true")
    args = parser.parse_args(argv)

    settings = get_settings()
    if args.verify_index_only:
        try:
            release = ConsolidatedRelease.load(args.release)
            cdir = (
                args.chunks_dir
                if args.chunks_dir is not None
                else ROOT / "data/derived/chunks" / release.manifest["release_version"]
            )
            chunks, manifest = load_chunks(release, cdir)
            vdir = (
                args.vector_dir if args.vector_dir is not None else ROOT / settings.rag_vector_dir
            )
            model = args.embedding_model or settings.rag_embedding_model
            location, marker, marker_sha = verify_vector_index(
                release, chunks, manifest, vdir, model
            )
        except (FileNotFoundError, ValueError) as exc:
            print(f"Erro: {exc}", file=sys.stderr)
            return 1
        print(
            json.dumps(
                {
                    "index_complete": True,
                    "location": str(location),
                    "chunks_expected": len(chunks),
                    "chunks_indexed": marker["count"],
                    "embedding_model": marker["embedding_model"],
                    "embedding_dimension": marker["embedding_dimension"],
                    "release_fingerprint": release.fingerprint,
                    "chunks_sha256": manifest["files"]["chunks.jsonl"]["sha256"],
                    "marker_sha256": marker_sha,
                    "api_calls": 0,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    strategies_list = [s.strip() for s in args.strategies.split(",") if s.strip()]
    if args.include_vector:
        for extra in ("vector", "hybrid"):
            if extra not in strategies_list:
                strategies_list.append(extra)
    strategies = tuple(strategies_list)

    checkpoint_path = (
        args.checkpoint if args.checkpoint is not None else default_checkpoint_path(args.output)
    )
    try:
        result = run_benchmark(
            release_dir=args.release,
            dataset_path=args.dataset,
            strategies=strategies,
            split=args.split,
            output_path=args.output,
            checkpoint_path=checkpoint_path,
            chunks_dir=args.chunks_dir,
            vector_dir=args.vector_dir,
            embedding_model=args.embedding_model,
            max_new_calls=args.max_new_calls,
            request_delay=args.request_delay,
            cache_query_embeddings=args.cache_query_embeddings,
            stop_on_error=args.stop_on_error,
            frozen_dataset_sha256=args.frozen_dataset_sha256,
            require_all_strategies=True,
            summarize_only=args.summarize_only,
        )
    except KeyboardInterrupt:
        print(
            f"\nExecução interrompida pelo usuário. Registros concluídos preservados em "
            f"{checkpoint_path}.",
            file=sys.stderr,
        )
        return 130
    except (FileNotFoundError, ValueError) as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1

    if result.completed and result.report is not None:
        _log_progress(sys.stderr, _format_human_summary(result.report))
        print(
            json.dumps(
                {
                    "final_summary_generated": True,
                    "output": str(args.output),
                    "checkpoint": str(result.checkpoint_path),
                    "summaries": result.report["summaries"],
                    "paired_comparisons": result.report["paired_comparisons"],
                    "paired_comparisons_by_clue_kind": result.report[
                        "paired_comparisons_by_clue_kind"
                    ],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    print(
        json.dumps(
            {
                "final_summary_generated": False,
                "stopped_reason": result.stopped_reason,
                "checkpoint": str(result.checkpoint_path),
                "new_api_calls": result.new_api_calls,
                "reused_records": result.reused_records,
                "executed_records": result.executed_records,
                "error_records": result.error_records,
                "pending_by_strategy": result.pending_by_strategy,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if result.stopped_reason == "max_new_calls" else 1


if __name__ == "__main__":
    raise SystemExit(main())
