from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace
from typing import cast
from unittest.mock import Mock

import pytest

import rag.experimental_cli as experimental_cli
from rag.config import ROOT, Settings
from rag.experimental import Corpus, Retriever
from rag.release import Release


def _args(command: str, question: str | None = None, *, documental: bool = False) -> Namespace:
    return Namespace(
        command=command,
        question=question,
        curated=None,
        supplement=None,
        corpus=Path("unused"),
        documental=documental,
        strategy="lexical",
        show_context=False,
    )


def _settings(tmp_path: Path) -> Settings:
    return Settings("", "unused", "unused", tmp_path / "release", tmp_path / "index", 5)


def _corpus() -> SimpleNamespace:
    return SimpleNamespace(manifest={}, chunks=[], fingerprint="test")


def test_default_restored_corpus_automatically_includes_archived_supplement() -> None:
    args = Namespace(corpus=ROOT / "data/corpus/experimental", supplement=None)
    assert experimental_cli.corpus_supplement(args) == (
        ROOT / "data/raw/complementares/chunks.jsonl"
    )


def test_validated_mode_excludes_pending_supplement() -> None:
    args = Namespace(corpus=ROOT / "data/corpus", supplement=None, validated=True)
    assert experimental_cli.corpus_supplement(args) is None
    args.supplement = ROOT / "data/raw/complementares/chunks.jsonl"
    with pytest.raises(ValueError, match="pendente"):
        experimental_cli.corpus_supplement(args)


def test_validated_vector_reuse_checks_primary_texts(monkeypatch: pytest.MonkeyPatch) -> None:
    current = cast(
        Corpus, SimpleNamespace(chunks=[{"evidence_id": "ev-primary", "text": "texto validado"}])
    )
    store = SimpleNamespace(
        get=lambda include: {
            "ids": ["ev-primary", "ev-pending"],
            "documents": ["texto validado", "texto complementar pendente"],
        }
    )
    monkeypatch.setattr(Corpus, "load", lambda *args: object())
    monkeypatch.setattr(experimental_cli, "open_index", lambda *args: store)
    assert experimental_cli.open_validated_vectors(current, Path("."), "fake", object()) is store
    current.chunks[0]["text"] = "texto alterado"
    with pytest.raises(ValueError, match="divergem"):
        experimental_cli.open_validated_vectors(current, Path("."), "fake", object())


def test_validated_chat_loads_consolidated_corpus_and_syncs_at_startup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    args = _args("chat")
    args.validated = True
    args.corpus = ROOT / "data/corpus"
    sync = Mock(return_value={"ceaf_stock": [], "ubs_stock": [{}], "locations": [{}]})
    monkeypatch.setattr(experimental_cli, "sync_snapshot", sync)
    monkeypatch.setattr("builtins.input", lambda prompt: "sair")

    assert experimental_cli.run(args, _settings(tmp_path)) == 0
    sync.assert_called_once()
    assert len(sync.call_args.args[1]) == 6
    output = capsys.readouterr().out
    assert "CORPUS CONSOLIDADO APROVADO" in output
    assert "2620 chunks do corpus ainda não têm aprovação individual" in output
    assert "InfoSaúde sincronizado" in output


def test_experimental_stock_intent_uses_live_reply_before_retrieval(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(Corpus, "load", lambda *args: _corpus())
    monkeypatch.setattr(Release, "load", lambda path: object())
    monkeypatch.setattr(experimental_cli, "load_snapshot", lambda path: {"snapshot": True})
    monkeypatch.setattr(
        experimental_cli,
        "live_reply",
        lambda question, release, snapshot: "Saldo ao vivo: UBS teste.",
    )
    monkeypatch.setattr(
        Retriever,
        "search",
        Mock(side_effect=AssertionError("RAG não deve rodar para intenção de estoque")),
    )

    assert (
        experimental_cli.run(
            _args("ask", "Onde tem estoque de sinvastatina 20 mg?"), _settings(tmp_path)
        )
        == 0
    )
    output = capsys.readouterr().out
    assert "Saldo ao vivo: UBS teste." in output


def test_documental_mode_skips_live_lookup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(Corpus, "load", lambda *args: _corpus())
    live = Mock(side_effect=AssertionError("modo documental não consulta InfoSaúde"))
    monkeypatch.setattr(experimental_cli, "live_reply", live)
    monkeypatch.setattr(
        experimental_cli,
        "Retriever",
        lambda corpus, store: SimpleNamespace(
            search=lambda *args: {
                "status": "no_match",
                "message": "Sem evidência",
                "evidence": [],
            }
        ),
    )

    assert (
        experimental_cli.run(
            _args("search", "Onde tem estoque de losartana 50 mg?", documental=True),
            _settings(tmp_path),
        )
        == 0
    )
    live.assert_not_called()
    assert "Sem evidência" in capsys.readouterr().out


def test_sync_live_experimental_requests_only_validated_product_codes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    sync = Mock(return_value={"ceaf_stock": [], "ubs_stock": [{}, {}], "locations": [{}]})
    monkeypatch.setattr(experimental_cli, "sync_snapshot", sync)

    assert experimental_cli.run(_args("sync-live"), _settings(tmp_path)) == 0
    codes = sync.call_args.args[1]
    assert len(codes) == 6
    assert "2 linhas UBS" in capsys.readouterr().out


def test_experimental_documental_chat_still_syncs_stock_at_startup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(Corpus, "load", lambda *args: _corpus())
    sync = Mock(return_value={"ceaf_stock": [], "ubs_stock": [{}], "locations": [{}]})
    monkeypatch.setattr(experimental_cli, "sync_snapshot", sync)
    monkeypatch.setattr("builtins.input", lambda prompt: "sair")

    assert experimental_cli.run(_args("chat", documental=True), _settings(tmp_path)) == 0
    sync.assert_called_once()
    assert "InfoSaúde sincronizado" in capsys.readouterr().out


def test_unmapped_stock_question_gets_clear_message_without_rag(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(Corpus, "load", lambda *args: _corpus())
    monkeypatch.setattr(Release, "load", lambda path: object())
    monkeypatch.setattr(experimental_cli, "load_snapshot", lambda path: {"snapshot": True})
    monkeypatch.setattr(
        experimental_cli,
        "live_reply",
        lambda *args: "Não localizado no recorte consultado: seis apresentações.",
    )
    monkeypatch.setattr(
        Retriever,
        "search",
        Mock(side_effect=AssertionError("não deve buscar no RAG")),
    )

    assert (
        experimental_cli.run(_args("ask", "Tem estoque de losartana 50 mg?"), _settings(tmp_path))
        == 0
    )
    assert "ainda não está mapeada" in capsys.readouterr().out
