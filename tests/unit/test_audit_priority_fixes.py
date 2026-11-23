"""Unit tests for priority audit fixes (explicit modes, shared guardrails, config consistency)."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

import rag.consolidated_chat as chat
import rag.consolidated_cli as consolidated_cli
from rag.answer import synthesize
from rag.config import ROOT, Settings, get_settings
from rag.consolidated import (
    CHUNK_RECIPE_V1,
    CHUNK_RECIPE_V2,
    CLINICAL_BLOCKED_TERMS,
    ConsolidatedRelease,
    build_chunks,
    chunk_for,
    load_chunks,
    matches_clinical_guardrail,
    search,
)
from rag.providers import invoke_with_retry, is_transient_provider_error


def _synthetic_corpus() -> tuple[ConsolidatedRelease, list[dict[str, Any]]]:
    source_f01 = {
        "source_id": "F01",
        "version": "RENAME 2024",
        "page": 10,
        "url": "https://example.org/rename.pdf",
    }
    source_f03 = {
        "source_id": "F03",
        "version": "REME-DF 2026",
        "page": 21,
        "url": "https://example.org/reme.pdf",
    }
    catalog = [
        {
            "medicine_id": "med-met-500",
            "active_ingredient": "cloridrato de metformina",
            "strength": "500 mg",
            "form": "comprimido",
            "release_characteristic": None,
            "source_ids": ["F01", "F03"],
        }
    ]
    evidence = [
        {
            "evidence_id": "ev-f01",
            "occurrence_id": "occ-f01",
            "medicine_id": "med-met-500",
            "source": source_f01,
            "text": "cloridrato de metformina | 500 mg | comprimido",
            "review_status": "approved",
        },
        {
            "evidence_id": "ev-f03",
            "occurrence_id": "occ-f03",
            "medicine_id": "med-met-500",
            "source": source_f03,
            "text": "cloridrato de metformina 500 mg comprimido",
            "review_status": "approved",
        },
    ]
    chunks: list[dict[str, Any]] = [
        {
            "chunk_id": "chunk-f01",
            "evidence_id": "ev-f01",
            "occurrence_id": "occ-f01",
            "medicine_id": "med-met-500",
            "source": source_f01,
            "text": "Princípio ativo: cloridrato de metformina 500 mg comprimido F01",
        },
        {
            "chunk_id": "chunk-f03",
            "evidence_id": "ev-f03",
            "occurrence_id": "occ-f03",
            "medicine_id": "med-met-500",
            "source": source_f03,
            "text": "Princípio ativo: cloridrato de metformina 500 mg comprimido F03",
        },
    ]
    release = ConsolidatedRelease(Path("."), {}, catalog, [], evidence, "synthetic")
    return release, chunks


@pytest.mark.parametrize("strategy", ["vector", "hybrid"])
def test_vector_and_hybrid_without_store_fail_explicitly(strategy: str) -> None:
    release, chunks = _synthetic_corpus()
    with pytest.raises(ValueError, match="exige índice vetorial"):
        search(
            "metformina 500 mg comprimido consta na RENAME?",
            release,
            chunks,
            store=None,
            strategy=strategy,
        )


@pytest.mark.parametrize("strategy", ["vector", "hybrid"])
def test_vector_and_hybrid_work_with_store(strategy: str) -> None:
    release, chunks = _synthetic_corpus()

    class FakeStore:
        def similarity_search(self, _question: str, **_kwargs: object) -> list[SimpleNamespace]:
            return [
                SimpleNamespace(metadata={"chunk_id": "chunk-f03"}),
                SimpleNamespace(metadata={"chunk_id": "chunk-f01"}),
            ]

    result = search(
        "metformina 500 mg comprimido",
        release,
        chunks,
        store=FakeStore(),
        strategy=strategy,
    )
    assert result["status"] == "matched"
    if strategy == "vector":
        assert [e["evidence_id"] for e in result["evidence"]] == ["ev-f03", "ev-f01"]
    else:
        assert {e["evidence_id"] for e in result["evidence"]} == {"ev-f01", "ev-f03"}


def test_chat_and_search_share_clinical_guardrail_source() -> None:
    assert chat.BLOCKED is CLINICAL_BLOCKED_TERMS


@pytest.mark.parametrize(
    "question",
    [
        "Qual a posologia da metformina 500 mg?",
        "Qual dose de varfarina devo tomar?",
        "Metformina causa efeito colateral?",
        "Quais os efeitos colaterais da losartana?",
        "Grávida pode usar metformina?",
        "É seguro na gravidez ou gestação?",
        "Gestante pode tomar amoxicilina?",
        "Existe interação medicamentosa entre metformina e álcool?",
        "Varfarina interage com omeprazol?",
        "Como usar metformina 500 mg?",
        "Como tomar sinvastatina?",
        "Qual a reação adversa mais comum?",
        "Losartana é equivalente a valsartana?",
        "Qual o medicamento equivalente da metformina?",
    ],
)
def test_clinical_guardrails_block_priority_cases_in_search_and_chat(
    question: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    release, chunks = _synthetic_corpus()
    assert matches_clinical_guardrail(question)
    result = search(question, release, chunks, strategy="lexical")
    assert result["status"] == "unsupported"
    assert result["evidence"] == []

    monkeypatch.setattr(
        chat,
        "google_chat",
        lambda *_args: (_ for _ in ()).throw(AssertionError("LLM nao pode ser chamado")),
    )
    reply = chat.ask(question, release, chunks, {}, get_settings(), {}, documental=True)
    assert "Não posso orientar dose" in reply


def test_legitimate_documentary_query_is_not_blocked_by_guardrails() -> None:
    release, chunks = _synthetic_corpus()
    result = search(
        "metformina 500 mg comprimido consta na RENAME?",
        release,
        chunks,
        strategy="lexical",
    )
    assert result["status"] == "matched"
    assert [e["evidence_id"] for e in result["evidence"]] == ["ev-f01"]
    assert not matches_clinical_guardrail(
        "carbonato de cálcio (equivalente a 500 ou 600 mg de cálcio) + colecalciferol 400 UI?"
    )


def test_env_example_and_config_default_point_to_approved_local_release() -> None:
    env_lines = (ROOT / ".env.example").read_text(encoding="utf-8").splitlines()
    env_map = dict(
        line.split("=", 1)
        for line in env_lines
        if "=" in line and not line.lstrip().startswith("#")
    )
    default_rel = Path(env_map["APP_RAG_RELEASE_DIR"])
    manifest_path = ROOT / default_rel / "release.json"
    assert manifest_path.is_file()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["status"] == "approved"


def test_readme_documents_dvc_for_v9_and_does_not_approve_pending_candidate() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "dvc pull" in readme
    assert "pending_review" in readme
    assert "corpus-consolidado-v9-aprovado-2026-11-12" in readme


def test_consolidated_cli_missing_dvc_release_gives_actionable_error() -> None:
    dvc_release = ROOT / "data/releases/corpus-consolidado-v9-aprovado-2026-11-12"
    if (dvc_release / "release.json").is_file():
        pytest.skip("Release DVC já está presente localmente")
    args = Namespace(release=dvc_release, command="search", question="metformina")
    with pytest.raises(FileNotFoundError, match="dvc pull"):
        consolidated_cli.run(args, get_settings())


def _write_synthetic_release_dir(
    folder: Path, *, text: str, exclusions: list[dict[str, Any]] | None = None
) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    source = {"source_id": "F01", "version": "RENAME 2024", "page": 1, "url": "https://example.org"}
    catalog = [
        {
            "medicine_id": "med-1",
            "active_ingredient": "metformina",
            "strength": "500 mg",
            "form": "comprimido",
            "release_characteristic": None,
            "source_ids": ["F01"],
            "occurrence_ids": ["occ-synthetic-1"],
        }
    ]
    occurrences = [
        {
            "occurrence_id": "occ-synthetic-1",
            "medicine_id": "med-1",
            "item_type": "medicine",
            "source": source,
            "raw_text": text,
        }
    ]
    evidence = [
        {
            "evidence_id": "ev-synthetic-1",
            "occurrence_id": "occ-synthetic-1",
            "medicine_id": "med-1",
            "source": source,
            "text": text,
            "review_status": "approved",
        }
    ]

    def dump_jsonl(items: list[dict[str, Any]]) -> bytes:
        return "".join(
            json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n" for item in items
        ).encode("utf-8")

    ev_bytes = dump_jsonl(evidence)
    ev_sha = hashlib.sha256(ev_bytes).hexdigest()
    payloads: dict[str, tuple[bytes, int | None]] = {
        "catalog.jsonl": (dump_jsonl(catalog), len(catalog)),
        "occurrences.jsonl": (dump_jsonl(occurrences), len(occurrences)),
        "evidencias.jsonl": (ev_bytes, len(evidence)),
        "exclusions.jsonl": (dump_jsonl(exclusions or []), len(exclusions or [])),
        "f03_descriptions.json": (b"{}\n", None),
        "quality_report.json": (b"{}\n", None),
        "domain_review.json": (
            json.dumps({"decision": "approved", "evidence_sha256": ev_sha}).encode("utf-8"),
            None,
        ),
    }
    files_manifest: dict[str, dict[str, Any]] = {}
    for name, (raw, count) in payloads.items():
        (folder / name).write_bytes(raw)
        entry: dict[str, Any] = {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
        if count is not None:
            entry["records"] = count
        files_manifest[name] = entry
    manifest = {
        "schema_version": "consolidated-release-v2",
        "status": "approved",
        "approval_scope": "synthetic-test",
        "files": files_manifest,
    }
    (folder / "release.json").write_text(json.dumps(manifest), encoding="utf-8")
    return folder


@pytest.mark.parametrize(
    ("text", "exclusions"),
    [
        ("   ", None),
        ("987.", None),
        ("metformina 500 mg", [{"occurrence_id": "occ-synthetic-1", "reason": "excluded"}]),
    ],
)
def test_release_load_rejects_blank_numbered_or_excluded_evidence_generically(
    tmp_path: Path, text: str, exclusions: list[dict[str, Any]] | None
) -> None:
    folder = _write_synthetic_release_dir(tmp_path / "rel", text=text, exclusions=exclusions)
    with pytest.raises(ValueError, match="Linha em branco ou excluída publicada"):
        ConsolidatedRelease.load(folder)


def test_week3_test_freeze_references_existing_review_record() -> None:
    freeze = json.loads(
        (ROOT / "evals/datasets/week3_v9_test_freeze.json").read_text(encoding="utf-8")
    )
    record_path = ROOT / freeze["review_record"]
    assert record_path.is_file()
    normalized = record_path.read_bytes().replace(b"\r\n", b"\n")
    assert hashlib.sha256(normalized).hexdigest() == freeze["review_record_sha256"]


class _RateLimit429(Exception):
    def __init__(self, message: str = "429 Too Many Requests; retry in 1.5s") -> None:
        super().__init__(message)
        self.status_code = 429


def test_invoke_with_retry_recovers_from_transient_and_nested_errors() -> None:
    calls = 0
    delays: list[float] = []

    class FlakyModel:
        def invoke(self, messages: Any) -> Any:
            nonlocal calls
            calls += 1
            if calls == 1:
                raise _RateLimit429("Resource exhausted; retry in 2.5s")
            if calls == 2:
                outer = RuntimeError("wrapper failure")
                outer.__cause__ = _RateLimit429("503 Service Unavailable")
                raise outer
            return SimpleNamespace(content="ok", usage_metadata={"total_tokens": 12})

    res = invoke_with_retry(FlakyModel(), [("human", "oi")], sleep=delays.append)
    assert res.content == "ok"
    assert calls == 3
    assert delays == [2.5, 2.0]


@pytest.mark.parametrize(
    "exc",
    [
        ValueError("invalid prompt"),
        RuntimeError("429 per day limit exceeded / daily quota"),
    ],
)
def test_invoke_with_retry_does_not_sleep_on_permanent_errors(exc: Exception) -> None:
    calls = 0
    delays: list[float] = []

    class BrokenModel:
        def invoke(self, messages: Any) -> Any:
            nonlocal calls
            calls += 1
            raise exc

    assert not is_transient_provider_error(exc)
    with pytest.raises(type(exc)):
        invoke_with_retry(BrokenModel(), [("human", "oi")], sleep=delays.append)
    assert calls == 1
    assert delays == []


def test_synthesize_and_measured_model_retry_without_multiplying_attempts() -> None:
    spec = importlib.util.spec_from_file_location(
        "week3_compare_test", ROOT / "scripts/week3_compare.py"
    )
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    attempts = 0
    delays: list[float] = []

    class RawModel:
        def invoke(self, messages: Any) -> Any:
            nonlocal attempts
            attempts += 1
            if attempts < 3:
                raise _RateLimit429()
            return SimpleNamespace(content="Consta na RENAME.", usage_metadata={"tokens": 5})

    measured = mod.MeasuredModel(RawModel(), sleep=delays.append)
    resp = measured.invoke([("human", "oi")])
    assert resp.content == "Consta na RENAME."
    assert attempts == 3
    assert measured.last_usage == {"tokens": 5}
    assert delays == [1.5, 1.5]

    # When MeasuredModel always fails with 429 inside synthesize, total calls must be bounded to 4.
    fail_attempts = 0
    fail_delays: list[float] = []

    class Always429:
        def invoke(self, messages: Any) -> Any:
            nonlocal fail_attempts
            fail_attempts += 1
            raise _RateLimit429()

    release, chunks = _synthetic_corpus()
    result = search("metformina 500 mg comprimido consta na RENAME?", release, chunks)
    measured_fail = mod.MeasuredModel(Always429(), sleep=fail_delays.append)
    with pytest.raises(_RateLimit429):
        synthesize("metformina 500 mg comprimido?", result, measured_fail, sleep=fail_delays.append)
    assert fail_attempts == 4


def test_consolidated_chat_transient_429_does_not_disable_session(
    monkeypatch: Any, capsys: Any
) -> None:
    release, chunks = _synthetic_corpus()
    settings = Settings("fake-key", "test-model", "test-emb", Path("."), Path("missing"), 5)
    monkeypatch.setattr("time.sleep", lambda _: None)

    turn = 0

    class RecoveringModel:
        def invoke(self, messages: Any) -> Any:
            nonlocal turn
            if turn == 0:
                raise _RateLimit429()
            return SimpleNamespace(content="Metformina 500 mg consta na RENAME consultada.")

    monkeypatch.setattr(chat, "google_chat", lambda *a: RecoveringModel())
    cache: dict[str, Any] = {}
    first = chat.ask(
        "metformina 500 mg comprimido RENAME",
        release,
        chunks,
        {},
        settings,
        cache,
        strategy="lexical",
    )
    assert "cloridrato de metformina" in first.lower()
    assert not cache.get("generation_disabled")
    assert "geração indisponível" in capsys.readouterr().out

    turn = 1
    second = chat.ask(
        "metformina 500 mg comprimido RENAME",
        release,
        chunks,
        {},
        settings,
        cache,
        strategy="lexical",
    )
    assert second == first
    assert "síntese não verificada" in capsys.readouterr().out

    # Non-transient failure still disables generation for the rest of the session.
    class AuthBrokenModel:
        def invoke(self, messages: Any) -> Any:
            raise RuntimeError("invalid credential")

    cache2: dict[str, Any] = {}
    monkeypatch.setattr(chat, "google_chat", lambda *a: AuthBrokenModel())
    chat.ask(
        "metformina 500 mg comprimido RENAME",
        release,
        chunks,
        {},
        settings,
        cache2,
        strategy="lexical",
    )
    assert cache2.get("generation_disabled") is True


def test_chunk_recipe_v2_disambiguates_duplicate_f03_and_keeps_v1_compat(tmp_path: Path) -> None:
    src = {
        "source_id": "F03",
        "version": "REME-DF 2026-10-29",
        "page": 19,
        "url": "https://example.org/reme.pdf",
    }
    ev_base: dict[str, Any] = {
        "medicine_id": "med-cab",
        "supply_id": None,
        "item_type": "medicine",
        "active_ingredient": "cabergolina",
        "strength": "0,5mg",
        "form": "comprimido",
        "release_characteristic": None,
        "description_cell": "cabergolina 0,5mg comprimido",
        "review_status": "approved",
        "source": src,
    }
    ev1 = {
        **ev_base,
        "evidence_id": "evidence-1",
        "occurrence_id": "occ-1",
        "source_row_number": 181,
        "text": "181 cabergolina Uso hospitalar",
    }
    ev2 = {
        **ev_base,
        "evidence_id": "evidence-2",
        "occurrence_id": "occ-2",
        "source_row_number": 182,
        "text": "182 cabergolina CEAF",
    }
    release = ConsolidatedRelease(
        tmp_path, {"release_version": "synthetic-test"}, [], [], [ev1, ev2], "fp-synth"
    )
    assert chunk_for(ev1, "synthetic-test")["text"] == chunk_for(ev2, "synthetic-test")["text"]

    v2_dir = tmp_path / "chunks_v2"
    manifest_v2 = build_chunks(release, v2_dir, recipe=CHUNK_RECIPE_V2)
    assert manifest_v2["recipe"] == CHUNK_RECIPE_V2
    loaded_v2, _ = load_chunks(release, v2_dir)
    assert len({c["text"] for c in loaded_v2}) == 2
    assert "Proveniência: F03 (p. 19, item 181)." in loaded_v2[0]["text"]

    v1_dir = tmp_path / "chunks_v1"
    build_chunks(release, v1_dir, recipe=CHUNK_RECIPE_V1)
    loaded_v1, m1 = load_chunks(release, v1_dir)
    assert m1["recipe"] == CHUNK_RECIPE_V1
    assert loaded_v1[0]["text"] == loaded_v1[1]["text"]

    # Duplicate page + row must fail under v2.
    ev_dup = {**ev1, "evidence_id": "evidence-3", "occurrence_id": "occ-3"}
    rel_dup = ConsolidatedRelease(
        tmp_path, {"release_version": "synthetic-dup"}, [], [], [ev1, ev_dup], "fp-dup"
    )
    with pytest.raises(ValueError, match="Chunks duplicados"):
        build_chunks(rel_dup, tmp_path / "chunks_dup", recipe=CHUNK_RECIPE_V2)


@pytest.mark.parametrize("strategy", ["vector", "hybrid"])
def test_colliding_medicine_ids_rank_globally_by_vector_distance(strategy: str) -> None:
    src_f01 = {
        "source_id": "F01",
        "version": "RENAME 2024",
        "page": 10,
        "url": "https://example.org/rename.pdf",
    }
    src_f03 = {
        "source_id": "F03",
        "version": "REME-DF 2026",
        "page": 20,
        "url": "https://example.org/reme.pdf",
    }
    catalog = [
        {
            "medicine_id": "med-a",
            "active_ingredient": "calcitriol",
            "strength": "0,25 mcg",
            "form": "cápsula",
            "release_characteristic": None,
            "source_ids": ["F01"],
        },
        {
            "medicine_id": "med-b",
            "active_ingredient": "calcitriol",
            "strength": "0,25mcg",
            "form": "cápsula",
            "release_characteristic": None,
            "source_ids": ["F03"],
        },
    ]
    evidence = [
        {
            "evidence_id": "ev-a",
            "occurrence_id": "occ-a",
            "medicine_id": "med-a",
            "source": src_f01,
            "text": "calcitriol 0,25 mcg cápsula genérico",
            "review_status": "approved",
        },
        {
            "evidence_id": "ev-b",
            "occurrence_id": "occ-b",
            "medicine_id": "med-b",
            "source": src_f03,
            "text": "calcitriol 0,25mcg cápsula protocolo único",
            "review_status": "approved",
        },
    ]
    chunks: list[dict[str, Any]] = [
        {
            "chunk_id": "chunk-a",
            "evidence_id": "ev-a",
            "occurrence_id": "occ-a",
            "medicine_id": "med-a",
            "source": src_f01,
            "text": "calcitriol 0,25 mcg cápsula",
        },
        {
            "chunk_id": "chunk-b",
            "evidence_id": "ev-b",
            "occurrence_id": "occ-b",
            "medicine_id": "med-b",
            "source": src_f03,
            "text": "calcitriol 0,25mcg cápsula protocolo único",
        },
    ]
    release = ConsolidatedRelease(Path("."), {}, catalog, [], evidence, "synthetic-collision")

    class ScoredStore:
        def similarity_search_with_score(
            self, _question: str, *, k: int, filter: dict[str, str]
        ) -> list[tuple[SimpleNamespace, float]]:
            assert k >= 2
            if filter["medicine_id"] == "med-a":
                return [(SimpleNamespace(metadata={"chunk_id": "chunk-a"}), 0.90)]
            return [(SimpleNamespace(metadata={"chunk_id": "chunk-b"}), 0.05)]

    result = search(
        "calcitriol 0,25 mcg cápsula protocolo único",
        release,
        chunks,
        store=ScoredStore(),
        strategy=strategy,
    )
    assert result["status"] == "matched"
    assert result["candidate_presentation_ids"] == ["med-a", "med-b"]
    assert [ev["evidence_id"] for ev in result["evidence"]][0] == "ev-b"


def test_config_defaults_env_example_and_week3_evals_stay_coherent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import rag.config as config_mod

    monkeypatch.setattr(config_mod, "_env", lambda: {})
    defaults = config_mod.get_settings()

    env_lines = (ROOT / ".env.example").read_text(encoding="utf-8").splitlines()
    env_map = dict(
        line.split("=", 1)
        for line in env_lines
        if "=" in line and not line.lstrip().startswith("#")
    )
    assert defaults.rag_chat_model == env_map["APP_RAG_CHAT_MODEL"] == "gemini-3.5-flash"
    assert (
        defaults.rag_embedding_model
        == env_map["APP_RAG_EMBEDDING_MODEL"]
        == "models/gemini-embedding-2"
    )
    assert (
        defaults.rag_release_dir.as_posix()
        == env_map["APP_RAG_RELEASE_DIR"]
        == "data/releases/corpus-consolidado-v10-aprovado-2026-11-17"
    )
    manifest = json.loads(
        (ROOT / defaults.rag_release_dir / "release.json").read_text(encoding="utf-8")
    )
    assert manifest["schema_version"] == "consolidated-release-v2"
    assert manifest["status"] == "approved"

    resp_eval = json.loads(
        (ROOT / "evals/results/week3_v9_response_test.json").read_text(encoding="utf-8")
    )
    retr_eval = json.loads(
        (ROOT / "evals/results/week3_v9_retrieval_test.json").read_text(encoding="utf-8")
    )
    assert resp_eval["chat_model"] == defaults.rag_chat_model
    assert retr_eval["embedding_model"] == defaults.rag_embedding_model


def test_cli_warns_on_legacy_release_and_routes_unpulled_dvc_cleanly(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    import rag.cli as cli_mod

    monkeypatch.setattr(
        "sys.argv",
        [
            "app.py",
            "search",
            "--release",
            str(ROOT / "data/releases/rag-lote-1-aprovado-2026-11-05"),
            "--strategy",
            "lexical",
            "sinvastatina 20 mg comprimido consta na RENAME?",
        ],
    )
    monkeypatch.setattr(
        cli_mod,
        "google_embeddings",
        lambda *_args: (_ for _ in ()).throw(RuntimeError("offline")),
    )
    assert cli_mod.main() == 0
    captured = capsys.readouterr()
    assert "lote legado" in captured.err

    dvc_dir = tmp_path / "data/releases/fake-dvc-release"
    dvc_dir.parent.mkdir(parents=True)
    dvc_dir.with_name(dvc_dir.name + ".dvc").write_text("outs: []\n", encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        ["app.py", "search", "--release", str(dvc_dir), "metformina"],
    )
    assert cli_mod.main() == 1
    assert "dvc pull" in capsys.readouterr().err


def test_week3_compare_accepts_crlf_files_against_lf_hashes(
    tmp_path: Path, monkeypatch: Any
) -> None:
    spec = importlib.util.spec_from_file_location(
        "week3_compare_crlf", ROOT / "scripts/week3_compare.py"
    )
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    monkeypatch.setattr(
        mod.subprocess,
        "run",
        lambda args, **kw: SimpleNamespace(stdout="abc123" if "rev-parse" in args else ""),
    )

    release = ConsolidatedRelease.load(
        ROOT / "data/releases/corpus-consolidado-v5-aprovado-2026-11-10"
    )
    first_ev = release.evidence[0]
    review_lf = b"# Aprovacao\nRevisado.\n"
    review_sha = hashlib.sha256(review_lf).hexdigest()
    review_file = tmp_path / "review.md"
    review_file.write_bytes(review_lf.replace(b"\n", b"\r\n"))

    case = {
        "id": "CRLF-TEST-01",
        "split": "test",
        "source_id": first_ev["source"]["source_id"],
        "question": (f"{first_ev['active_ingredient']} {first_ev['strength']} {first_ev['form']}?"),
        "expected_status": "matched",
        "relevant_ids": [first_ev["evidence_id"]],
        "release_fingerprint": release.fingerprint,
        "synthetic": True,
        "review_status": "reviewed",
        "reviewer": "Jhiovana",
        "reviewed_at": "2026-11-16",
        "review_record_sha256": review_sha,
    }
    dataset_lf = (json.dumps(case, ensure_ascii=False) + "\n").encode("utf-8")
    dataset_sha = hashlib.sha256(dataset_lf).hexdigest()
    dataset_file = tmp_path / "dataset.jsonl"
    dataset_file.write_bytes(dataset_lf.replace(b"\n", b"\r\n"))

    out_file = tmp_path / "out.json"
    report = mod.run(
        Namespace(
            matrix="retrieval",
            release=ROOT / "data/releases/corpus-consolidado-v5-aprovado-2026-11-10",
            dataset=dataset_file,
            output=out_file,
            best_strategy="lexical",
            variants="lexical",
            split="test",
            frozen_dataset_sha256=dataset_sha,
            review_record=review_file,
            request_delay=0.0,
        )
    )
    assert report["dataset_sha256"] == dataset_sha
    assert report["review_sha256"] == review_sha


@pytest.mark.dvc
def test_v9_chunk_recipe_v2_has_zero_duplicate_texts() -> None:
    rel_dir = ROOT / "data/releases/corpus-consolidado-v9-aprovado-2026-11-12"
    release = ConsolidatedRelease.load(rel_dir)
    v1_chunks, m1 = load_chunks(
        release, ROOT / "data/derived/chunks" / release.manifest["release_version"]
    )
    assert m1["recipe"] == CHUNK_RECIPE_V1
    assert len(v1_chunks) == len(release.evidence)

    v2_chunks = [
        chunk_for(ev, release.manifest["release_version"], recipe=CHUNK_RECIPE_V2)
        for ev in release.evidence
    ]
    assert len({c["text"] for c in v2_chunks}) == len(v2_chunks)
