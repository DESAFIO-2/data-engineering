"""Tests for the multi-chunk ranking benchmark and statistical evaluators."""

from __future__ import annotations

import hashlib
import io
import json
import sys
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from langchain_core.embeddings import DeterministicFakeEmbedding

from rag.config import ROOT
from rag.consolidated import (
    ConsolidatedRelease,
    build_chunks,
    build_index,
    index_location,
    load_chunks,
)

sys.path.insert(0, str(ROOT / "scripts"))
from eval_multichunk_benchmark import (  # noqa: E402
    bootstrap_ci,
    build_final_report,
    default_checkpoint_path,
    evaluate_multichunk,
    exact_mcnemar_pvalue,
    format_pvalue_scientific,
    load_and_validate_dataset,
    main,
    paired_hit1_comparison,
    run_benchmark,
    verify_vector_index,
)


class CountingFakeEmbeddings:
    """Deterministic fake embeddings tracking embed_query calls with optional failure injection."""

    def __init__(
        self,
        *,
        size: int = 16,
        fail_on_call: int | None = None,
        fail_exception: BaseException | None = None,
    ) -> None:
        self._inner = DeterministicFakeEmbedding(size=size)
        self.calls = 0
        self.fail_on_call = fail_on_call
        self.fail_exception = fail_exception

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._inner.embed_documents(texts)

    def embed_query(self, text: str) -> list[float]:
        self.calls += 1
        if self.fail_on_call is not None and self.calls == self.fail_on_call:
            exc = self.fail_exception or RuntimeError("simulated embedding failure")
            raise exc
        return self._inner.embed_query(text)


def _dump_jsonl(rows: list[dict[str, Any]]) -> bytes:
    return "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows
    ).encode("utf-8")


def _build_synthetic_benchmark_env(
    base: Path,
    *,
    release_version: str = "corpus-synthetic-v1",
    colliding_ids: bool = False,
    with_index: bool = True,
    embedding_model: str = "fake-embedding-v1",
) -> dict[str, Path]:
    release_dir = base / "release"
    chunks_dir = base / "chunks"
    vector_dir = base / "vectorstore"
    release_dir.mkdir(parents=True, exist_ok=True)

    src_f03 = {
        "source_id": "F03",
        "version": "REME-DF 2026",
        "page": 10,
        "url": "https://example.org/reme.pdf",
    }
    src_f01 = {
        "source_id": "F01",
        "version": "RENAME 2024",
        "page": 20,
        "url": "https://example.org/rename.pdf",
    }

    med_dev = "med-dev-rifampicina"
    med_test_a = "med-test-claritromicina"
    med_test_b = "med-test-claritromicina-b" if colliding_ids else med_test_a

    catalog: list[dict[str, Any]] = [
        {
            "medicine_id": med_dev,
            "active_ingredient": "rifampicina",
            "strength": "300 mg",
            "form": "cápsula",
            "release_characteristic": None,
            "source_ids": ["F03"],
            "occurrence_ids": ["occ-dev-1", "occ-dev-2", "occ-dev-3"],
        },
        {
            "medicine_id": med_test_a,
            "active_ingredient": "claritromicina",
            "strength": "500 mg",
            "form": "comprimido",
            "release_characteristic": None,
            "source_ids": ["F03", "F01"] if not colliding_ids else ["F03"],
            "occurrence_ids": (
                ["occ-test-1", "occ-test-2", "occ-test-3"]
                if colliding_ids
                else ["occ-test-1", "occ-test-2", "occ-test-3", "occ-test-4"]
            ),
        },
    ]
    if colliding_ids:
        catalog.append(
            {
                "medicine_id": med_test_b,
                "active_ingredient": "claritromicina",
                "strength": "500mg",
                "form": "comprimido",
                "release_characteristic": None,
                "source_ids": ["F01"],
                "occurrence_ids": ["occ-test-4"],
            }
        )

    raw_specs = [
        (
            "occ-dev-1",
            "ev-dev-1",
            med_dev,
            "rifampicina",
            "300 mg",
            "cápsula",
            src_f03,
            "meningite",
        ),
        (
            "occ-dev-2",
            "ev-dev-2",
            med_dev,
            "rifampicina",
            "300 mg",
            "cápsula",
            src_f03,
            "brucelose",
        ),
        (
            "occ-dev-3",
            "ev-dev-3",
            med_dev,
            "rifampicina",
            "300 mg",
            "cápsula",
            src_f03,
            "hanseníase",
        ),
        (
            "occ-test-1",
            "ev-test-1",
            med_test_a,
            "claritromicina",
            "500 mg",
            "comprimido",
            src_f03,
            "coqueluche bordetella pertussis",
        ),
        (
            "occ-test-2",
            "ev-test-2",
            med_test_a,
            "claritromicina",
            "500 mg",
            "comprimido",
            src_f03,
            "hanseníase doença de hansen",
        ),
        (
            "occ-test-3",
            "ev-test-3",
            med_test_a,
            "claritromicina",
            "500 mg",
            "comprimido",
            src_f03,
            "site-tb tuberculose multirresistente",
        ),
        (
            "occ-test-4",
            "ev-test-4",
            med_test_b,
            "claritromicina",
            "500mg" if colliding_ids else "500 mg",
            "comprimido",
            src_f01,
            "lista nacional rename 2024",
        ),
    ]

    occurrences: list[dict[str, Any]] = []
    evidence: list[dict[str, Any]] = []
    for idx, (occ_id, ev_id, mid, ing, strength, form, src, desc) in enumerate(raw_specs, 1):
        raw_text = f"{ing} {strength} {form} {desc}"
        occurrences.append(
            {
                "occurrence_id": occ_id,
                "medicine_id": mid,
                "item_type": "medicine",
                "active_ingredient": ing,
                "strength": strength,
                "form": form,
                "release_characteristic": None,
                "source": src,
                "source_row_number": idx,
                "raw_text": raw_text,
            }
        )
        ev_entry: dict[str, Any] = {
            "evidence_id": ev_id,
            "occurrence_id": occ_id,
            "medicine_id": mid,
            "supply_id": None,
            "item_type": "medicine",
            "active_ingredient": ing,
            "strength": strength,
            "form": form,
            "release_characteristic": None,
            "source": src,
            "source_row_number": idx,
            "text": raw_text,
            "review_status": "approved",
        }
        if src["source_id"] == "F03":
            ev_entry["description_cell"] = desc
        else:
            ev_entry["indication"] = desc
        evidence.append(ev_entry)

    ev_bytes = _dump_jsonl(evidence)
    ev_sha = hashlib.sha256(ev_bytes).hexdigest()
    payloads: dict[str, tuple[bytes, int | None]] = {
        "catalog.jsonl": (_dump_jsonl(catalog), len(catalog)),
        "occurrences.jsonl": (_dump_jsonl(occurrences), len(occurrences)),
        "evidencias.jsonl": (ev_bytes, len(evidence)),
        "exclusions.jsonl": (b"", 0),
        "f03_descriptions.json": (b"{}\n", None),
        "quality_report.json": (b"{}\n", None),
        "domain_review.json": (
            json.dumps({"decision": "approved", "evidence_sha256": ev_sha}).encode("utf-8"),
            None,
        ),
    }
    files_manifest: dict[str, dict[str, Any]] = {}
    for name, (raw, count) in payloads.items():
        (release_dir / name).write_bytes(raw)
        entry: dict[str, Any] = {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
        if count is not None:
            entry["records"] = count
        files_manifest[name] = entry
    manifest = {
        "schema_version": "consolidated-release-v2",
        "release_version": release_version,
        "status": "approved",
        "approval_scope": "synthetic-multichunk-test",
        "files": files_manifest,
    }
    (release_dir / "release.json").write_text(json.dumps(manifest), encoding="utf-8")

    release = ConsolidatedRelease.load(release_dir)
    chunk_manifest = build_chunks(release, chunks_dir)
    chunks, _ = load_chunks(release, chunks_dir)

    if with_index:
        build_index(
            release,
            chunks,
            chunk_manifest,
            vector_dir,
            embedding_model,
            DeterministicFakeEmbedding(size=16),
        )

    dataset_path = base / "dataset.jsonl"
    cases = [
        {
            "id": "SYN-DEV-001",
            "split": "dev",
            "family_id": "rifampicina",
            "clue_kind": "literal_clue",
            "source_id": "F03",
            "presentation": "rifampicina | 300 mg | capsula",
            "question": "Qual evidência de rifampicina 300 mg cápsula trata meningite?",
            "expected_status": "matched",
            "relevant_ids": ["ev-dev-1"],
            "candidate_chunk_count_verified": 3,
            "release_fingerprint": release.fingerprint,
            "synthetic": True,
        },
        {
            "id": "SYN-DEV-002",
            "split": "dev",
            "family_id": "rifampicina",
            "clue_kind": "semantic_paraphrase",
            "source_id": "F03",
            "presentation": "rifampicina | 300 mg | capsula",
            "question": "Qual evidência de rifampicina 300 mg cápsula trata mal de hansen?",
            "expected_status": "matched",
            "relevant_ids": ["ev-dev-3"],
            "candidate_chunk_count_verified": 3,
            "release_fingerprint": release.fingerprint,
            "synthetic": True,
        },
        {
            "id": "SYN-TEST-001",
            "split": "test",
            "family_id": "claritromicina",
            "clue_kind": "literal_clue",
            "source_id": "F03",
            "presentation": "claritromicina | 500 mg | comprimido",
            "question": "Qual evidência de claritromicina 500 mg comprimido especifica coqueluche?",
            "expected_status": "matched",
            "relevant_ids": ["ev-test-1"],
            "candidate_chunk_count_verified": 3,
            "release_fingerprint": release.fingerprint,
            "synthetic": True,
        },
        {
            "id": "SYN-TEST-002",
            "split": "test",
            "family_id": "claritromicina",
            "clue_kind": "semantic_paraphrase",
            "source_id": "F03",
            "presentation": "claritromicina | 500 mg | comprimido",
            "question": (
                "Para claritromicina 500 mg comprimido, qual registro destina-se à "
                "doença de hansen?"
            ),
            "expected_status": "matched",
            "relevant_ids": ["ev-test-2"],
            "candidate_chunk_count_verified": 3,
            "release_fingerprint": release.fingerprint,
            "synthetic": True,
        },
        {
            "id": "SYN-TEST-003",
            "split": "test",
            "family_id": "claritromicina",
            "clue_kind": "literal_clue",
            "source_id": "F03",
            "presentation": "claritromicina | 500 mg | comprimido",
            "question": (
                "Qual evidência de claritromicina 500 mg comprimido trata tuberculose no site-tb?"
            ),
            "expected_status": "matched",
            "relevant_ids": ["ev-test-3"],
            "candidate_chunk_count_verified": 3,
            "release_fingerprint": release.fingerprint,
            "synthetic": True,
        },
        {
            "id": "SYN-TEST-004",
            "split": "test",
            "family_id": "claritromicina",
            "clue_kind": "semantic_paraphrase",
            "source_id": "F01",
            "presentation": "claritromicina | 500 mg | comprimido",
            "question": (
                "Para claritromicina 500 mg comprimido, qual item aparece na lista "
                "nacional de referência?"
            ),
            "expected_status": "matched",
            "relevant_ids": ["ev-test-4"],
            "candidate_chunk_count_verified": 3,
            "release_fingerprint": release.fingerprint,
            "synthetic": True,
        },
    ]
    dataset_path.write_bytes(_dump_jsonl(cases))
    return {
        "release_dir": release_dir,
        "chunks_dir": chunks_dir,
        "vector_dir": vector_dir,
        "dataset_path": dataset_path,
        "output_path": base / "report.json",
    }


def test_paired_significance_helpers_compute_exact_bounds() -> None:
    ci = bootstrap_ci([1.0, 0.0, 1.0, 1.0], resamples=500, seed=42)
    assert ci is not None
    assert 0.0 <= ci["ci95_low"] <= ci["mean"] <= ci["ci95_high"] <= 1.0
    assert exact_mcnemar_pvalue(0, 0) == 1.0
    assert exact_mcnemar_pvalue(10, 0) < 0.005

    # Small p-values must never round down to 0.0.
    p_43 = exact_mcnemar_pvalue(0, 43)
    assert 0.0 < p_43 < 1e-12
    assert format_pvalue_scientific(0, 43) == "2.2737e-13"

    p_2000 = exact_mcnemar_pvalue(0, 2000)
    assert p_2000 > 0.0
    assert format_pvalue_scientific(0, 2000) not in {"0", "0.0", "0.0000"}

    comp = paired_hit1_comparison([1.0, 1.0, 1.0, 0.0], [0.0, 0.0, 1.0, 0.0])
    assert comp["wins"] == 2
    assert comp["losses"] == 0
    assert comp["ties"] == 2
    assert comp["mcnemar_p_value"] > 0.0


def test_atomic_per_case_checkpoint_resume_and_no_repeated_vector_calls(tmp_path: Path) -> None:
    env = _build_synthetic_benchmark_env(tmp_path / "run")
    ckpt = default_checkpoint_path(env["output_path"])
    fake_emb = CountingFakeEmbeddings(size=16)
    delays: list[float] = []
    stream1 = io.StringIO()

    # Batch 1: exact (4) + lexical (4) + first 2 vector calls.
    res1 = run_benchmark(
        release_dir=env["release_dir"],
        dataset_path=env["dataset_path"],
        chunks_dir=env["chunks_dir"],
        vector_dir=env["vector_dir"],
        embedding_model="fake-embedding-v1",
        embeddings=fake_emb,
        split="test",
        output_path=env["output_path"],
        checkpoint_path=ckpt,
        max_new_calls=2,
        request_delay=0.25,
        sleep_fn=delays.append,
        progress_stream=stream1,
    )
    assert not res1.completed
    assert res1.stopped_reason == "max_new_calls"
    assert res1.new_api_calls == 2
    assert fake_emb.calls == 2
    assert delays == [0.25]
    assert not env["output_path"].exists()
    assert ckpt.is_file()
    progress_out = stream1.getvalue()
    assert "[vector] 1/4 | SYN-TEST-001 | ok |" in progress_out
    assert "restante_estrategia=3 | restante_total=7 | chamadas_novas=1/2" in progress_out

    # Batch 2: resume with max_new_calls=4 -> reuses all 10 records, runs 2 vector + 2 hybrid.
    res2 = run_benchmark(
        release_dir=env["release_dir"],
        dataset_path=env["dataset_path"],
        chunks_dir=env["chunks_dir"],
        vector_dir=env["vector_dir"],
        embedding_model="fake-embedding-v1",
        embeddings=fake_emb,
        split="test",
        output_path=env["output_path"],
        checkpoint_path=ckpt,
        max_new_calls=4,
        request_delay=0.25,
        sleep_fn=delays.append,
        progress_stream=io.StringIO(),
    )
    assert not res2.completed
    assert res2.stopped_reason == "max_new_calls"
    assert res2.reused_records == 10
    assert res2.new_api_calls == 4
    assert fake_emb.calls == 6
    assert not env["output_path"].exists()

    # Batch 3: finishes remaining 2 hybrid cases and writes final output.
    res3 = run_benchmark(
        release_dir=env["release_dir"],
        dataset_path=env["dataset_path"],
        chunks_dir=env["chunks_dir"],
        vector_dir=env["vector_dir"],
        embedding_model="fake-embedding-v1",
        embeddings=fake_emb,
        split="test",
        output_path=env["output_path"],
        checkpoint_path=ckpt,
        max_new_calls=4,
        request_delay=0.25,
        sleep_fn=delays.append,
        progress_stream=io.StringIO(),
    )
    assert res3.completed
    assert res3.stopped_reason is None
    assert res3.reused_records == 14
    assert res3.new_api_calls == 2
    assert fake_emb.calls == 8  # 4 vector + 4 hybrid, zero repeated calls
    assert env["output_path"].is_file()
    assert res3.report is not None
    assert set(res3.report["summaries"]) == {"exact", "lexical", "vector", "hybrid"}
    for strategy in ("exact", "lexical", "vector", "hybrid"):
        summary = res3.report["summaries"][strategy]
        assert summary["cases"] == 4
        assert summary["errors"] == 0
        assert set(summary["by_clue_kind"]) == {"literal_clue", "semantic_paraphrase"}
    assert "hybrid_vs_lexical" in res3.report["paired_comparisons"]
    assert "semantic_paraphrase" in res3.report["paired_comparisons_by_clue_kind"]


def test_interruption_preserves_completed_records_and_resumes(tmp_path: Path) -> None:
    env = _build_synthetic_benchmark_env(tmp_path / "interrupt")
    ckpt = default_checkpoint_path(env["output_path"])
    interrupt_emb = CountingFakeEmbeddings(
        size=16, fail_on_call=2, fail_exception=KeyboardInterrupt()
    )

    with pytest.raises(KeyboardInterrupt):
        run_benchmark(
            release_dir=env["release_dir"],
            dataset_path=env["dataset_path"],
            chunks_dir=env["chunks_dir"],
            vector_dir=env["vector_dir"],
            embedding_model="fake-embedding-v1",
            embeddings=interrupt_emb,
            split="test",
            output_path=env["output_path"],
            checkpoint_path=ckpt,
            progress_stream=io.StringIO(),
        )

    assert not env["output_path"].exists()
    saved = json.loads(ckpt.read_text(encoding="utf-8"))
    assert len(saved["records"]["exact"]) == 4
    assert len(saved["records"]["lexical"]) == 4
    assert list(saved["records"]["vector"]) == ["SYN-TEST-001"]

    resumed_emb = CountingFakeEmbeddings(size=16)
    res = run_benchmark(
        release_dir=env["release_dir"],
        dataset_path=env["dataset_path"],
        chunks_dir=env["chunks_dir"],
        vector_dir=env["vector_dir"],
        embedding_model="fake-embedding-v1",
        embeddings=resumed_emb,
        split="test",
        output_path=env["output_path"],
        checkpoint_path=ckpt,
        progress_stream=io.StringIO(),
    )
    assert res.completed
    assert res.reused_records == 9
    assert resumed_emb.calls == 7  # 3 remaining vector + 4 hybrid
    assert env["output_path"].is_file()


def test_error_recording_redacts_secrets_blocks_summary_and_retries_on_resume(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("APP_GOOGLE_API_KEY", "SecretTestEnvKey999")
    env = _build_synthetic_benchmark_env(tmp_path / "errors")
    ckpt = default_checkpoint_path(env["output_path"])
    stream = io.StringIO()

    # Non-quota error on call 2: records redacted error, continues remaining cases, blocks summary.
    err_emb = CountingFakeEmbeddings(
        size=16,
        fail_on_call=2,
        fail_exception=ValueError(
            "Upstream failure key=SecretTestEnvKey999 token=TopSecretTok AIzaFakeExposedKey123"
        ),
    )
    res1 = run_benchmark(
        release_dir=env["release_dir"],
        dataset_path=env["dataset_path"],
        chunks_dir=env["chunks_dir"],
        vector_dir=env["vector_dir"],
        embedding_model="fake-embedding-v1",
        embeddings=err_emb,
        split="test",
        output_path=env["output_path"],
        checkpoint_path=ckpt,
        progress_stream=stream,
    )
    assert not res1.completed
    assert res1.error_records == 1
    assert not env["output_path"].exists()

    ckpt_text = ckpt.read_text(encoding="utf-8")
    assert "SecretTestEnvKey999" not in ckpt_text
    assert "TopSecretTok" not in ckpt_text
    assert "AIzaFakeExposedKey123" not in ckpt_text
    assert "[REDACTED]" in ckpt_text

    ckpt_data = json.loads(ckpt_text)
    with pytest.raises(ValueError, match="Resumo final bloqueado"):
        build_final_report(
            ckpt_data,
            cases=load_and_validate_dataset(
                env["dataset_path"],
                ConsolidatedRelease.load(env["release_dir"]),
                "test",
            )[0],
        )

    # Resume retries only the single failed vector case (15/16 reused).
    clean_emb = CountingFakeEmbeddings(size=16)
    res2 = run_benchmark(
        release_dir=env["release_dir"],
        dataset_path=env["dataset_path"],
        chunks_dir=env["chunks_dir"],
        vector_dir=env["vector_dir"],
        embedding_model="fake-embedding-v1",
        embeddings=clean_emb,
        split="test",
        output_path=env["output_path"],
        checkpoint_path=ckpt,
        progress_stream=io.StringIO(),
    )
    assert res2.completed
    assert res2.reused_records == 15
    assert clean_emb.calls == 1

    # Quota 429 error stops immediately after recording the failed case.
    env_q = _build_synthetic_benchmark_env(tmp_path / "quota")
    ckpt_q = default_checkpoint_path(env_q["output_path"])
    quota_emb = CountingFakeEmbeddings(
        size=16,
        fail_on_call=2,
        fail_exception=RuntimeError("429 RESOURCE_EXHAUSTED: daily quota AIzaSecretQuotaKey"),
    )
    res_q = run_benchmark(
        release_dir=env_q["release_dir"],
        dataset_path=env_q["dataset_path"],
        chunks_dir=env_q["chunks_dir"],
        vector_dir=env_q["vector_dir"],
        embedding_model="fake-embedding-v1",
        embeddings=quota_emb,
        split="test",
        output_path=env_q["output_path"],
        checkpoint_path=ckpt_q,
        progress_stream=io.StringIO(),
    )
    assert not res_q.completed
    assert res_q.stopped_reason == "error"
    assert quota_emb.calls == 2  # Did not continue hammering cases 3 and 4
    assert "AIzaSecretQuotaKey" not in ckpt_q.read_text(encoding="utf-8")


def test_resume_rejects_incompatible_config(tmp_path: Path) -> None:
    env = _build_synthetic_benchmark_env(tmp_path / "base")
    ckpt = default_checkpoint_path(env["output_path"])
    emb = CountingFakeEmbeddings(size=16)
    run_benchmark(
        release_dir=env["release_dir"],
        dataset_path=env["dataset_path"],
        chunks_dir=env["chunks_dir"],
        vector_dir=env["vector_dir"],
        embedding_model="fake-embedding-v1",
        embeddings=emb,
        split="test",
        output_path=env["output_path"],
        checkpoint_path=ckpt,
        max_new_calls=1,
        progress_stream=io.StringIO(),
    )

    # 1. Different split
    with pytest.raises(ValueError, match="Configuração incompatível"):
        run_benchmark(
            release_dir=env["release_dir"],
            dataset_path=env["dataset_path"],
            chunks_dir=env["chunks_dir"],
            vector_dir=env["vector_dir"],
            embedding_model="fake-embedding-v1",
            embeddings=emb,
            split="dev",
            output_path=env["output_path"],
            checkpoint_path=ckpt,
            progress_stream=io.StringIO(),
        )

    # 2. Different embedding model
    env_m2 = _build_synthetic_benchmark_env(tmp_path / "m2", embedding_model="fake-embedding-v2")
    with pytest.raises(ValueError, match="Configuração incompatível"):
        run_benchmark(
            release_dir=env_m2["release_dir"],
            dataset_path=env_m2["dataset_path"],
            chunks_dir=env_m2["chunks_dir"],
            vector_dir=env_m2["vector_dir"],
            embedding_model="fake-embedding-v2",
            embeddings=emb,
            split="test",
            output_path=env["output_path"],
            checkpoint_path=ckpt,
            progress_stream=io.StringIO(),
        )

    # 3. Different strategies
    with pytest.raises(ValueError, match="Configuração incompatível"):
        run_benchmark(
            release_dir=env["release_dir"],
            dataset_path=env["dataset_path"],
            chunks_dir=env["chunks_dir"],
            vector_dir=env["vector_dir"],
            embedding_model="fake-embedding-v1",
            embeddings=emb,
            strategies=("exact", "lexical", "vector"),
            split="test",
            output_path=env["output_path"],
            checkpoint_path=ckpt,
            progress_stream=io.StringIO(),
        )

    # 4. Different parameters (cache_query_embeddings toggled)
    with pytest.raises(ValueError, match="Configuração incompatível"):
        run_benchmark(
            release_dir=env["release_dir"],
            dataset_path=env["dataset_path"],
            chunks_dir=env["chunks_dir"],
            vector_dir=env["vector_dir"],
            embedding_model="fake-embedding-v1",
            embeddings=emb,
            split="test",
            output_path=env["output_path"],
            checkpoint_path=ckpt,
            cache_query_embeddings=True,
            progress_stream=io.StringIO(),
        )

    # 5. Different release / dataset
    env_rel2 = _build_synthetic_benchmark_env(
        tmp_path / "rel2", release_version="corpus-synthetic-v2"
    )
    with pytest.raises(ValueError, match="Configuração incompatível"):
        run_benchmark(
            release_dir=env_rel2["release_dir"],
            dataset_path=env_rel2["dataset_path"],
            chunks_dir=env_rel2["chunks_dir"],
            vector_dir=env_rel2["vector_dir"],
            embedding_model="fake-embedding-v1",
            embeddings=emb,
            split="test",
            output_path=env["output_path"],
            checkpoint_path=ckpt,
            progress_stream=io.StringIO(),
        )

    # 6. Tampered hash/strategy inside a stored record
    tampered = json.loads(ckpt.read_text(encoding="utf-8"))
    tampered["records"]["exact"]["SYN-TEST-001"]["strategy"] = "lexical"
    bad_ckpt = tmp_path / "tampered.checkpoint.json"
    bad_ckpt.write_text(json.dumps(tampered), encoding="utf-8")
    with pytest.raises(ValueError, match="Metadados/hashes do registro divergem"):
        run_benchmark(
            release_dir=env["release_dir"],
            dataset_path=env["dataset_path"],
            chunks_dir=env["chunks_dir"],
            vector_dir=env["vector_dir"],
            embedding_model="fake-embedding-v1",
            embeddings=emb,
            split="test",
            output_path=env["output_path"],
            checkpoint_path=bad_ckpt,
            progress_stream=io.StringIO(),
        )


def test_missing_or_incomplete_vector_index_fails_without_api_calls(tmp_path: Path) -> None:
    env = _build_synthetic_benchmark_env(tmp_path / "missing", with_index=False)
    emb = CountingFakeEmbeddings(size=16)

    with pytest.raises(FileNotFoundError, match="Índice consolidado não construído"):
        run_benchmark(
            release_dir=env["release_dir"],
            dataset_path=env["dataset_path"],
            chunks_dir=env["chunks_dir"],
            vector_dir=env["vector_dir"],
            embedding_model="fake-embedding-v1",
            embeddings=emb,
            split="test",
            output_path=env["output_path"],
            progress_stream=io.StringIO(),
        )
    assert emb.calls == 0

    # Build a valid index then delete its index.json marker -> must fail offline.
    env_inc = _build_synthetic_benchmark_env(tmp_path / "incomplete", with_index=True)
    release = ConsolidatedRelease.load(env_inc["release_dir"])
    _, chunk_manifest = load_chunks(release, env_inc["chunks_dir"])
    loc = index_location(env_inc["vector_dir"], release, chunk_manifest, "fake-embedding-v1")
    (loc / "index.json").unlink()

    with pytest.raises(FileNotFoundError, match="Índice consolidado não construído"):
        verify_vector_index(
            release,
            load_chunks(release, env_inc["chunks_dir"])[0],
            chunk_manifest,
            env_inc["vector_dir"],
            "fake-embedding-v1",
        )
    assert emb.calls == 0


def test_summary_gate_blocks_incomplete_strategies_or_cases(tmp_path: Path) -> None:
    env = _build_synthetic_benchmark_env(tmp_path / "gate")
    ckpt = default_checkpoint_path(env["output_path"])

    # CLI run with only exact,lexical must save checkpoint but NOT write final output.
    exit_code = main(
        [
            "--release",
            str(env["release_dir"]),
            "--dataset",
            str(env["dataset_path"]),
            "--chunks-dir",
            str(env["chunks_dir"]),
            "--output",
            str(env["output_path"]),
            "--checkpoint",
            str(ckpt),
            "--split",
            "test",
            "--strategies",
            "exact,lexical",
        ]
    )
    assert exit_code == 1
    assert ckpt.is_file()
    assert not env["output_path"].exists()

    # summarize-only on that incomplete 2-strategy checkpoint must fail cleanly.
    summarize_code = main(
        [
            "--release",
            str(env["release_dir"]),
            "--dataset",
            str(env["dataset_path"]),
            "--chunks-dir",
            str(env["chunks_dir"]),
            "--output",
            str(env["output_path"]),
            "--checkpoint",
            str(ckpt),
            "--split",
            "test",
            "--strategies",
            "exact,lexical",
            "--summarize-only",
        ]
    )
    assert summarize_code == 1
    assert not env["output_path"].exists()


def test_colliding_ids_dedup_and_optional_query_cache(tmp_path: Path) -> None:
    env_col = _build_synthetic_benchmark_env(tmp_path / "colliding", colliding_ids=True)
    emb_col = CountingFakeEmbeddings(size=16)
    res_col = run_benchmark(
        release_dir=env_col["release_dir"],
        dataset_path=env_col["dataset_path"],
        chunks_dir=env_col["chunks_dir"],
        vector_dir=env_col["vector_dir"],
        embedding_model="fake-embedding-v1",
        embeddings=emb_col,
        split="test",
        output_path=env_col["output_path"],
        progress_stream=io.StringIO(),
    )
    assert res_col.completed
    # Even with 2 colliding medicine_ids, each case embeds the query only once per strategy.
    assert emb_col.calls == 8

    env_cache = _build_synthetic_benchmark_env(tmp_path / "cached")
    emb_cache = CountingFakeEmbeddings(size=16)
    res_cache = run_benchmark(
        release_dir=env_cache["release_dir"],
        dataset_path=env_cache["dataset_path"],
        chunks_dir=env_cache["chunks_dir"],
        vector_dir=env_cache["vector_dir"],
        embedding_model="fake-embedding-v1",
        embeddings=emb_cache,
        split="test",
        output_path=env_cache["output_path"],
        cache_query_embeddings=True,
        progress_stream=io.StringIO(),
    )
    assert res_cache.completed
    # Vector runs 4 API calls; hybrid reuses all 4 from persistent cache -> 4 total calls!
    assert emb_cache.calls == 4
    assert res_cache.report is not None
    assert all(r["query_embedding_cached"] for r in res_cache.report["records"]["hybrid"])
    assert all(r["embedding_calls"] == 0 for r in res_cache.report["records"]["hybrid"])


def test_cli_verify_index_and_batched_execution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    import eval_multichunk_benchmark as mod

    env = _build_synthetic_benchmark_env(tmp_path / "cli")
    capsys.readouterr()
    ckpt = default_checkpoint_path(env["output_path"])
    fake_emb = CountingFakeEmbeddings(size=16)

    monkeypatch.setattr(mod, "google_embeddings", lambda *_args: fake_emb)
    monkeypatch.setattr(time, "sleep", lambda _sec: None)

    assert (
        main(
            [
                "--release",
                str(env["release_dir"]),
                "--chunks-dir",
                str(env["chunks_dir"]),
                "--vector-dir",
                str(env["vector_dir"]),
                "--embedding-model",
                "fake-embedding-v1",
                "--verify-index-only",
            ]
        )
        == 0
    )
    verify_payload = json.loads(capsys.readouterr().out)
    assert verify_payload["index_complete"] is True
    assert verify_payload["chunks_indexed"] == 7
    assert verify_payload["api_calls"] == 0
    assert fake_emb.calls == 0

    base_args = [
        "--release",
        str(env["release_dir"]),
        "--dataset",
        str(env["dataset_path"]),
        "--chunks-dir",
        str(env["chunks_dir"]),
        "--vector-dir",
        str(env["vector_dir"]),
        "--embedding-model",
        "fake-embedding-v1",
        "--output",
        str(env["output_path"]),
        "--checkpoint",
        str(ckpt),
        "--split",
        "test",
        "--strategies",
        "exact,lexical,vector,hybrid",
        "--max-new-calls",
        "4",
        "--request-delay",
        "0.1",
    ]
    assert main(base_args) == 0
    batch1 = json.loads(capsys.readouterr().out)
    assert batch1["final_summary_generated"] is False
    assert batch1["stopped_reason"] == "max_new_calls"
    assert batch1["new_api_calls"] == 4
    assert not env["output_path"].exists()

    assert main(base_args) == 0
    batch2 = json.loads(capsys.readouterr().out)
    assert batch2["final_summary_generated"] is True
    assert env["output_path"].is_file()
    assert fake_emb.calls == 8


@pytest.mark.dvc
def test_multichunk_benchmark_dataset_has_disjoint_families_and_min_three_chunks() -> None:
    dataset = ROOT / "evals/datasets/multichunk_v9_benchmark.jsonl"
    rows = [
        json.loads(line)
        for line in dataset.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(rows) >= 60
    dev_families = {row["family_id"] for row in rows if row["split"] == "dev"}
    test_families = {row["family_id"] for row in rows if row["split"] == "test"}
    assert dev_families and test_families
    assert dev_families & test_families == set()
    assert all(row["candidate_chunk_count_verified"] >= 3 for row in rows)

    report = evaluate_multichunk(
        release_dir=ROOT / "data/releases/corpus-consolidado-v9-aprovado-2026-11-12",
        dataset_path=dataset,
        strategies=("exact", "lexical"),
        split="all",
    )
    assert report["summaries"]["exact"]["cases"] == len(rows)
    assert report["summaries"]["lexical"]["cases"] == len(rows)
    assert report["summaries"]["exact"]["min_candidate_chunk_count"] >= 3
    assert report["summaries"]["lexical"]["critical_confusions"] == 0
    assert (
        report["summaries"]["lexical"]["hit_at_1"]["mean"]
        > report["summaries"]["exact"]["hit_at_1"]["mean"]
    )


@pytest.mark.dvc
def test_multichunk_evaluator_supports_mock_vector_and_hybrid(tmp_path: Path) -> None:
    dataset = ROOT / "evals/datasets/multichunk_v9_benchmark.jsonl"

    first = json.loads(dataset.read_text(encoding="utf-8").splitlines()[0])
    subset = tmp_path / "subset.jsonl"
    subset.write_text(json.dumps(first, ensure_ascii=False) + "\n", encoding="utf-8")

    class FakeStore:
        def similarity_search_with_score(
            self, _question: str, *, k: int, filter: dict[str, Any]
        ) -> list[tuple[SimpleNamespace, float]]:
            assert k >= 3
            assert filter["medicine_id"]
            chunk_id = "chunk-" + first["relevant_ids"][0].removeprefix("evidence-")
            return [(SimpleNamespace(metadata={"chunk_id": chunk_id}), 0.01)]

    report = evaluate_multichunk(
        release_dir=ROOT / "data/releases/corpus-consolidado-v9-aprovado-2026-11-12",
        dataset_path=subset,
        strategies=("lexical", "vector", "hybrid"),
        split="all",
        store=FakeStore(),
    )
    assert report["summaries"]["vector"]["hit_at_1"]["mean"] == 1.0
    assert report["summaries"]["hybrid"]["hit_at_1"]["mean"] == 1.0


@pytest.mark.dvc
def test_local_v9_index_and_test_split_verify_offline() -> None:
    release_dir = ROOT / "data/releases/corpus-consolidado-v9-aprovado-2026-11-12"
    release = ConsolidatedRelease.load(release_dir)
    chunks, manifest = load_chunks(
        release, ROOT / "data/derived/chunks" / release.manifest["release_version"]
    )
    _, marker, _ = verify_vector_index(
        release,
        chunks,
        manifest,
        ROOT / "data/vectorstore/chroma",
        "models/gemini-embedding-2",
    )
    assert marker["count"] == 2114
    assert marker["embedding_dimension"] == 3072
    assert marker["embedding_model"] == "models/gemini-embedding-2"

    test_cases, _, _ = load_and_validate_dataset(
        ROOT / "evals/datasets/multichunk_v9_benchmark.jsonl",
        release,
        "test",
    )
    assert len(test_cases) == 32
