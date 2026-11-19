from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

import rag.cli as cli
import rag.consolidated_chat as chat
import rag.consolidated_cli as consolidated_cli
from ingestion.infosaude_live import UBS, InfoSaudeLiveClient, query_body
from rag.config import ROOT, Settings
from rag.consolidated import ConsolidatedRelease, load_chunks, search
from rag.live import stock_reply_for_product

CorpusData = tuple[ConsolidatedRelease, list[dict[str, Any]], dict[str, Any]]

RELEASE = ROOT / "data/releases/corpus-consolidado-v5-aprovado-2026-11-10"


@pytest.fixture(scope="module")
def corpus() -> CorpusData:
    release = ConsolidatedRelease.load(RELEASE)
    chunks, manifest = load_chunks(
        release, ROOT / "data/derived/chunks" / release.manifest["release_version"]
    )
    return release, chunks, manifest


@pytest.fixture
def settings() -> Settings:
    return Settings("", "test-model", "test-embedding", RELEASE, Path("missing-index"), 5)


@pytest.mark.parametrize("command", ["chat", "sync-live", "ask", "search", "index", "eval"])
@pytest.mark.parametrize("explicit", [False, True])
def test_dispatch_by_resolved_manifest(
    command: str, explicit: bool, settings: Settings, monkeypatch: Any
) -> None:
    monkeypatch.setattr(cli, "get_settings", lambda: settings)
    seen = []

    def run(args: Any, cfg: Settings) -> int:
        seen.append(args.release)
        return 0

    monkeypatch.setattr(consolidated_cli, "run", run)
    monkeypatch.setattr(
        "sys.argv", ["app.py", command] + (["--release", str(RELEASE)] if explicit else [])
    )
    assert cli.main() == 0
    assert seen == [RELEASE]


def test_multiturn_slots_and_new_subject(corpus: CorpusData) -> None:
    release, chunks, _ = corpus
    state = chat.ConversationState()
    for question, expected in [
        ("O que consta na RENAME sobre metformina?", "ambiguous"),
        ("850 mg", "ambiguous"),
        ("comprimido", "matched"),
    ]:
        resolved = state.resolve(question, release)
        assert search(resolved, release, chunks)["status"] == expected
    resolved = state.resolve("Tem estoque UBS em Planaltina?", release)
    assert "850 mg" in resolved and "Planaltina" in resolved and "estoque" in resolved
    resolved = state.resolve("E na Farmácia Popular?", release)
    assert "Farmácia Popular" in resolved and "estoque" not in resolved
    assert search(resolved, release, chunks)["medicine"]["source_ids"] == ["F04"]
    resolved = state.resolve("Sinvastatina 20 mg comprimido na REME?", release)
    assert "metformina" not in resolved and state.region == "Planaltina"
    assert state.source == "F03"


@pytest.mark.parametrize(
    "query,status",
    [
        ("metformina na RENAME", "ambiguous"),
        ("metformina 850 mg na RENAME", "ambiguous"),
        ("metformina 99999 mg comprimido na RENAME", "not_in_scope"),
        ("metformina 1500 mg comprimido na RENAME", "not_in_scope"),
        ("metformina e sinvastatina 850 mg comprimido", "ambiguous"),
        ("metformina 500 mg Farmácia Popular", "ambiguous"),
        ("metformina 500 mg ação prolongada Farmácia Popular", "matched"),
        ("metformina 500 mg comprimido ação prolongada RENAME", "not_in_scope"),
    ],
)
def test_missing_fields_vs_nonexistent(corpus: CorpusData, query: str, status: str) -> None:
    release, chunks, _ = corpus
    assert search(query, release, chunks)["status"] == status


def test_no_configuration_never_calls_providers(
    corpus: CorpusData, settings: Settings, monkeypatch: Any, capsys: Any
) -> None:
    def forbidden(*args: Any) -> Any:
        pytest.fail("Provider called without configuration")

    monkeypatch.setattr(chat, "google_embeddings", forbidden)
    monkeypatch.setattr(chat, "google_chat", forbidden)
    reply = chat.ask("metformina 850 mg comprimido RENAME", *corpus, settings, {})
    assert "850 mg" in reply and "A10BA02" in reply
    out = capsys.readouterr().out
    assert "APP_GOOGLE_API_KEY ausente" in out and "página 28" in out


@pytest.mark.parametrize("failure", ["embedding", "missing", "incompatible", "search"])
def test_vector_failure_still_generates_from_lexical(
    corpus: CorpusData, settings: Settings, monkeypatch: Any, capsys: Any, failure: str
) -> None:
    settings = replace(settings, google_api_key="never-print-this-key")

    def fail(*args: Any, **kwargs: Any) -> Any:
        kind = (
            FileNotFoundError
            if failure == "missing"
            else ValueError
            if failure == "incompatible"
            else RuntimeError
        )
        raise kind(settings.google_api_key)

    monkeypatch.setattr(
        chat, "google_embeddings", fail if failure == "embedding" else lambda *a: object()
    )
    monkeypatch.setattr(
        chat,
        "open_index",
        fail if failure != "search" else lambda *a: SimpleNamespace(similarity_search=fail),
    )
    prompts = []

    class Model:
        def invoke(self, messages: Any) -> Any:
            prompts.append(messages)
            return SimpleNamespace(content="Há estoque garantido hoje.")

    monkeypatch.setattr(chat, "google_chat", lambda *args: Model())
    history = [(str(i), "answer") for i in range(8)]
    reply = chat.ask("metformina 850 mg comprimido RENAME", *corpus, settings, {}, history=history)
    assert "estoque garantido" not in reply and "850 mg" in reply
    assert "Usuário: 0" not in str(prompts) and "Usuário: 7" in str(prompts)
    assert "evidence-f16957cc6029096a75e2c5af" in str(prompts)
    output = capsys.readouterr().out
    assert "busca lexical utilizada" in output and settings.google_api_key not in output


@pytest.mark.parametrize("content", [None, [], ""])
def test_generation_failure_has_documentary_content(
    corpus: CorpusData, settings: Settings, monkeypatch: Any, content: Any, capsys: Any
) -> None:
    class Model:
        def invoke(self, messages: Any) -> Any:
            if content is None:
                raise RuntimeError("secret-key")
            return SimpleNamespace(content=content)

    monkeypatch.setattr(chat, "google_chat", lambda *args: Model())
    reply = chat.ask(
        "metformina 850 mg comprimido RENAME",
        *corpus,
        replace(settings, google_api_key="secret-key"),
        {},
        strategy="lexical",
    )
    assert "A10BA02" in reply
    assert "secret-key" not in capsys.readouterr().out


@pytest.mark.parametrize(
    "question",
    [
        "Posso trocar pela de ação prolongada?",
        "Qual a dose de metformina?",
        "Metformina é indicada para mim?",
        "Tenho direito a metformina?",
    ],
)
def test_clinical_requests_block_before_providers(
    corpus: CorpusData, settings: Settings, monkeypatch: Any, question: str
) -> None:
    monkeypatch.setattr(chat, "search", lambda *a, **k: pytest.fail("Search must not run"))
    assert "Não posso orientar" in chat.ask(question, *corpus, settings, {})


def test_documental_chat_does_not_sync_and_bounds_history(
    corpus: CorpusData, settings: Settings, monkeypatch: Any
) -> None:
    release, chunks, manifest = corpus
    monkeypatch.setattr(chat, "sync_live", lambda *a: pytest.fail("documental sync"))
    questions = iter(["Oi"] * 8 + ["metformina 850 mg comprimido RENAME", "sair"])
    monkeypatch.setattr("builtins.input", lambda _: next(questions))
    seen = []

    def ask(*args: Any, **kwargs: Any) -> str:
        seen.append(list(kwargs["history"]))
        return "resposta"

    monkeypatch.setattr(chat, "ask", ask)
    args = SimpleNamespace(documental=True, strategy="lexical", show_context=False)
    assert chat.chat(args, settings, release, chunks, manifest) == 0
    assert len(seen[0]) == 6


def test_validated_links_do_not_include_unknown_form_or_prolonged(corpus: CorpusData) -> None:
    products = chat.validated_products(corpus[0])
    assert len(products) == 3
    assert {p[0] for p in products.values()} == {"90224", "90226"}
    assert all(
        not m.get("release_characteristic") and m["form"] == "comprimido"
        for m in corpus[0].catalog
        if m["medicine_id"] in products
    )


def test_invalid_link_fingerprint_is_rejected(
    corpus: CorpusData, monkeypatch: Any, tmp_path: Path
) -> None:
    directory = tmp_path / "data/mappings"
    directory.mkdir(parents=True)
    (directory / "ubs_consolidated.json").write_text(json.dumps({"release_fingerprint": "wrong"}))
    monkeypatch.setattr(chat, "ROOT", tmp_path)
    assert chat.validated_products(corpus[0]) == {}

    ubs_dir = directory / "ubs"
    ubs_dir.mkdir(parents=True)
    (ubs_dir / f"{corpus[0].fingerprint}.json").write_text(
        json.dumps({"release_fingerprint": "wrong"})
    )
    with pytest.raises(ValueError, match="outro release"):
        chat.validated_products(corpus[0])


def test_discovery_filters_server_side_and_has_only_catalog_columns(monkeypatch: Any) -> None:
    seen = []
    client = InfoSaudeLiveClient()

    def fetch(panel: Any, **kwargs: Any) -> list[dict[str, Any]]:
        seen.append((panel, kwargs))
        return []

    monkeypatch.setattr(client, "fetch", fetch)
    client.discover_ubs_products("metformina")
    panel, kwargs = seen[0]
    assert panel.columns == ("i_cod_produto", "i_desc_produto")
    body = query_body(panel, **kwargs)
    query = body["queries"][0]["Query"]["Commands"][0]["SemanticQueryDataShapeCommand"]["Query"]
    assert "METFORMINA" in str(query["Where"]) and len(query["Select"]) == 2


@pytest.mark.parametrize(
    "region,quantity,date,expected",
    [
        ("Taguatinga", 10, "2026-11-01T12:00:00+00:00", "não comprova saldo zero"),
        ("Planaltina", 0, "2026-11-01T12:00:00+00:00", "Não há saldo positivo"),
        ("Planaltina", 10, "2026-11-01T12:00:00+00:00", "mais de 48 horas"),
        ("Planaltina", 10, None, "não posso afirmar estoque"),
    ],
)
def test_stock_region_zero_stale_and_undated(
    region: str, quantity: int, date: Any, expected: str
) -> None:
    snapshot = {
        "sources": {"ubs": UBS.source_url},
        "locations": [],
        "ubs_stock": [
            {
                "i_cod_produto": "90226",
                "i_desc_produto": "METFORMINA 850 MG",
                "i_desc_radf": region,
                "i_qtd_rede": quantity,
                "data_extracao": date,
                "i_desc_local_estoque": "FARMÁCIA UBS 1",
            }
        ],
    }
    reply = stock_reply_for_product(
        "metformina", snapshot, ("90226", "METFORMINA 850 MG"), "Planaltina"
    )
    assert expected in reply
    if region != "Planaltina":
        assert "saldo positivo para" not in reply


def test_product_description_mismatch_does_not_claim_stock() -> None:
    snapshot = {"ubs_stock": [{"i_cod_produto": "90226", "i_desc_produto": "outra apresentação"}]}
    assert "Não há registro validado" in stock_reply_for_product(
        "metformina", snapshot, ("90226", "METFORMINA 850 MG")
    )


def test_stock_and_popular_have_separate_sources(
    corpus: CorpusData, settings: Settings, monkeypatch: Any
) -> None:
    monkeypatch.setattr(chat, "load_snapshot", lambda *a: None)
    reply = chat.ask(
        "metformina 850 mg comprimido estoque UBS e Farmácia Popular",
        *corpus,
        settings,
        {},
        strategy="lexical",
    )
    assert "Estoque UBS:" in reply and "Em qual região" in reply
    assert "Presença na Farmácia Popular:" in reply and "F04" in reply


def test_full_stock_question_can_change_region_and_switch_to_document(corpus: CorpusData) -> None:
    release, chunks, _ = corpus
    state = chat.ConversationState()
    state.resolve("Tem metformina 850 mg comprimido em Planaltina?", release)
    resolved = state.resolve("E em Taguatinga?", release)
    assert chat.region_in(resolved) == "Taguatinga"
    assert "planaltina" not in resolved.lower()
    resolved = state.resolve("E na Farmácia Popular?", release)
    assert not chat.stock_intent(resolved)
    assert search(resolved, release, chunks)["status"] == "matched"


def test_release_characteristic_followup_is_retained(corpus: CorpusData) -> None:
    release, chunks, _ = corpus
    state = chat.ConversationState()
    state.resolve("metformina 500 mg Farmácia Popular", release)
    resolved = state.resolve("ação prolongada", release)
    result = search(resolved, release, chunks)
    assert result["status"] == "matched"
    assert result["medicine"]["release_characteristic"] == "ação prolongada"
    resolved = state.resolve("convencional", release)
    assert search(resolved, release, chunks)["medicine"]["release_characteristic"] is None


def test_unknown_requested_region_is_not_ignored() -> None:
    assert (
        chat.region_in("metformina 850 mg comprimido em Região Inexistente?")
        == "Região Inexistente"
    )


def test_unknown_medicine_does_not_inherit_previous_identity(corpus: CorpusData) -> None:
    state = chat.ConversationState()
    state.resolve("metformina 850 mg comprimido", corpus[0])
    resolved = state.resolve("Tem estoque de medicamento-inexistente em Planaltina?", corpus[0])
    assert "metformina" not in resolved


def test_combined_intent_survives_conversation_resolution(corpus: CorpusData) -> None:
    state = chat.ConversationState()
    resolved = state.resolve(
        "metformina 850 mg comprimido estoque UBS e Farmácia Popular", corpus[0]
    )
    assert "estoque UBS" in resolved and "Farmácia Popular" in resolved


def test_chat_blocks_raw_unsafe_followup(
    corpus: CorpusData, settings: Settings, monkeypatch: Any, capsys: Any
) -> None:
    release, chunks, manifest = corpus
    questions = iter(
        ["metformina 850 mg comprimido RENAME", "Posso trocar pela de ação prolongada?", "sair"]
    )
    monkeypatch.setattr("builtins.input", lambda _: next(questions))
    args = SimpleNamespace(documental=True, strategy="lexical", show_context=False)
    assert chat.chat(args, settings, release, chunks, manifest) == 0
    assert "Não posso orientar" in capsys.readouterr().out


def test_sync_includes_legacy_and_validated_codes(corpus: CorpusData, monkeypatch: Any) -> None:
    seen: list[str] = []

    def sync(path: Path, codes: tuple[str, ...]) -> dict[str, Any]:
        seen.extend(codes)
        return {"ubs_stock": [{"i_cod_produto": c} for c in codes]}

    monkeypatch.setattr(chat, "sync_snapshot", sync)
    chat.sync_live(corpus[0])
    assert set(seen) == {"18458", "19847", "694", "695", "90224", "90226", "90380", "90491"}


def test_stock_unique_presentation_does_not_require_form(
    corpus: CorpusData,
    settings: Settings,
    monkeypatch: Any,
) -> None:
    seen = []

    def lookup(medicine: Any, release: Any, region: str, products: Any) -> str:
        seen.append((medicine, region))
        return "Consulta realizada para a apresentação identificada."

    monkeypatch.setattr(chat, "lookup_stock", lookup)
    reply = chat.ask("metformina 850 mg estoque UBS em Planaltina", *corpus, settings, {})
    assert "Consulta realizada" in reply
    assert seen[0][0]["form"] == "comprimido" and seen[0][1] == "Planaltina"


def test_stock_balances_are_not_sent_to_generation(
    corpus: CorpusData, settings: Settings, monkeypatch: Any
) -> None:
    prompts = []

    class Model:
        def invoke(self, messages: Any) -> Any:
            prompts.append(messages)
            return SimpleNamespace(content="Consta na fonte consultada.")

    monkeypatch.setattr(chat, "google_chat", lambda *args: Model())
    history = [("E em Planaltina?", f"Saldo registrado: 123456789. Fonte: {UBS.source_url}")]
    chat.ask(
        "metformina 850 mg Farmácia Popular",
        *corpus,
        replace(settings, google_api_key="test-key"),
        {},
        strategy="lexical",
        history=history,
    )
    assert "123456789" not in str(prompts)
    assert "Consulta UBS respondida separadamente" in str(prompts)
