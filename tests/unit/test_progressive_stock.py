from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

import rag.consolidated_chat as chat
import rag.consolidated_live as live
from ingestion.infosaude_live import CEAF, query_body
from rag.catalog_chat import candidates, stock_candidates
from rag.config import ROOT, Settings
from rag.consolidated import ConsolidatedRelease, load_chunks

Corpus = tuple[ConsolidatedRelease, list[dict[str, Any]], dict[str, Any]]

pytestmark = pytest.mark.dvc

DESC = "LIRAGLUTIDA SOLUÇÃO INJETÁVEL 6MG/ML SISTEMA DE APLICAÇÃO 3ML MULTIDOSES DE ATÉ 3,0 MG"
CEAF_DESC = "LIRAGLUTIDA 6 MG/ML SOLUÇÃO INJETÁVEL 3 ML ELENCO ESTADUAL"


@pytest.fixture(scope="module")
def corpus() -> Corpus:
    r = ConsolidatedRelease.load(ROOT / "data/releases/corpus-consolidado-v5-aprovado-2026-11-10")
    c, m = load_chunks(r, ROOT / "data/derived/chunks" / r.manifest["release_version"])
    return r, c, m


@pytest.fixture
def settings(corpus: Corpus) -> Settings:
    return Settings("", "unused", "unused", corpus[0].folder, ROOT / "missing", 5)


@pytest.fixture
def client(monkeypatch: Any, tmp_path: Path) -> Any:
    class Client:
        def __init__(self) -> None:
            self.calls: list[Any] = []
            self.fail: set[str] = set()
            self.ubs = [{"i_cod_produto": "27795", "i_desc_produto": DESC}]
            self.region = "Planaltina"
            self.quantity = 0
            self.date: str | None = None
            self.ceaf_quantity = "COM ESTOQUE"

        def discover_ubs_products(self, name: str) -> list[dict[str, Any]]:
            self.calls.append(("catalog", name))
            if "ubs" in self.fail:
                raise RuntimeError("secret-never-log")
            return self.ubs

        def fetch(self, panel: Any, **kwargs: Any) -> list[dict[str, Any]]:
            self.calls.append((panel, kwargs))
            if panel is CEAF:
                if "ceaf" in self.fail:
                    raise RuntimeError("secret-never-log")
                return [
                    {
                        "cod_produto2": "27795",
                        "desc_produto": CEAF_DESC,
                        "unidade": "Asa Sul",
                        "disp_estoque": self.ceaf_quantity,
                        "ultima_atualizacao": self.date,
                    }
                ]
            return [
                {
                    "i_cod_produto": "27795",
                    "i_desc_produto": DESC,
                    "i_desc_radf": self.region,
                    "i_qtd_rede": self.quantity,
                    "data_extracao": self.date,
                    "i_desc_local_estoque": "FARMÁCIA UBS 1",
                    "cnes": "123",
                }
            ]

    fake = Client()
    monkeypatch.setattr(live, "ROOT", tmp_path)
    monkeypatch.setattr(live, "load_snapshot", lambda *a: None)
    monkeypatch.setattr(live, "InfoSaudeLiveClient", lambda: fake)
    return fake


def test_name_only_lists_all_strengths_and_forms(corpus: Corpus, settings: Settings) -> None:
    items = candidates("metformina", corpus[0])
    reply = chat.ask("metformina", *corpus, settings, {}, documental=True)
    assert len(items) > 2
    assert "500 mg" in reply and "850 mg" in reply and "comprimido" in reply
    assert "ação prolongada" in reply and "Qual dessas" in reply
    assert "Informe a concentração" not in reply and "forma não informada" in reply


def test_missing_form_shows_known_options(corpus: Corpus, settings: Settings) -> None:
    reply = chat.ask("metformina 850 mg RENAME", *corpus, settings, {}, documental=True)
    assert "comprimido" in reply and "RENAME" in reply
    assert "Informe a forma farmacêutica" not in reply


def test_one_presentation_just_asks_region(corpus: Corpus, settings: Settings) -> None:
    reply = chat.ask("liraglutida", *corpus, settings, {})
    assert "6 mg/mL" in reply and "solução injetável" in reply and "página 39" in reply
    assert "Em qual região" in reply and "não precisa repetir" in reply


def test_ambiguity_before_network(corpus: Corpus, settings: Settings, monkeypatch: Any) -> None:
    monkeypatch.setattr(chat, "lookup_stock", lambda *a: pytest.fail("Ambiguous product queried"))
    reply = chat.ask("metformina estoque em Planaltina", *corpus, settings, {})
    assert "500 mg" in reply and "850 mg" in reply and "ação prolongada" in reply


def test_unknown_form_prolonged_not_silently_discarded(corpus: Corpus) -> None:
    items = stock_candidates(candidates("metformina 500 mg", corpus[0]))
    assert len(items) == 2 and any(m.get("release_characteristic") for m in items)


@pytest.mark.parametrize(
    "followup",
    [
        "e tem estoque desse remédio em planaltina?",
        "tem estoque desse remédio em planaltina?",
        "Planaltina",
    ],
)
def test_anaphora_and_region_keep_medicine(corpus: Corpus, followup: str) -> None:
    state = chat.ConversationState()
    state.resolve("liraglutida", corpus[0])
    resolved = state.resolve(followup, corpus[0])
    assert "liraglutida" in resolved and "estoque" in resolved
    assert chat.region_in(resolved) == "Planaltina"


def test_numbered_selection_keeps_stock_region(corpus: Corpus) -> None:
    state = chat.ConversationState()
    question = state.resolve("Tem metformina em Planaltina?", corpus[0])
    state.options = stock_candidates(candidates(question, corpus[0]))
    selected = next(i for i, m in enumerate(state.options, 1) if m["strength"] == "850 mg")
    result = state.resolve(str(selected), corpus[0])
    assert "850 mg" in result and "estoque" in result and "Planaltina" in result


def test_switch_medicine_then_numbered_choice_uses_exact_presentation(
    corpus: Corpus, settings: Settings, monkeypatch: Any, capsys: Any
) -> None:
    seen: list[tuple[str, str, str]] = []

    def lookup(medicine: Any, release: Any, region: str, products: Any) -> str:
        seen.append((medicine["active_ingredient"], medicine["strength"], region))
        return "Saldo consultado."

    monkeypatch.setattr(chat, "sync_live", lambda *a: None)
    monkeypatch.setattr(chat, "lookup_stock", lookup)
    inputs = iter(["liraglutida tem?", "Planaltina", "metformina?", "1", "sair"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))
    args = SimpleNamespace(documental=False, strategy="lexical", show_context=False)
    assert chat.chat(args, settings, *corpus) == 0
    out = capsys.readouterr().out
    assert "Qual dessas apresentações" in out
    assert seen == [
        ("liraglutida", "6 mg/mL (sistema de aplicação 3 mL)", "Planaltina"),
        ("cloridrato de metformina", "500 mg", "Planaltina"),
    ]


def test_chat_name_region_and_repeat_refresh(
    corpus: Corpus, settings: Settings, client: Any, monkeypatch: Any, capsys: Any
) -> None:
    monkeypatch.setattr(chat, "sync_live", lambda *a: None)
    inputs = iter(
        ["liraglutida", "e tem estoque desse remédio em planaltina?", "e em Ceilândia?", "sair"]
    )
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))
    args = SimpleNamespace(documental=False, strategy="lexical", show_context=False)
    assert chat.chat(args, settings, *corpus) == 0
    out = capsys.readouterr().out
    assert "27795" in out and "COM ESTOQUE" in out and "sem data de extração" in out
    assert "não posso confirmar estoque de hoje" in out
    assert sum(call[0] == "catalog" for call in client.calls) == 2


def test_live_validated_code_both_panels_no_false_regional_ceaf(
    corpus: Corpus, client: Any
) -> None:
    m = candidates("liraglutida", corpus[0])[0]
    reply = live.lookup_stock(m, corpus[0], "Planaltina")
    assert (
        "27795" in reply and "20 registros" not in reply and "saldos informados são zero" in reply
    )
    assert "Asa Sul: o painel informa COM ESTOQUE" in reply
    assert "não são UBS dessa região" in reply and "não posso confirmar estoque de hoje" in reply
    assert "API pública consultada" in reply


@pytest.mark.parametrize(
    "code,description",
    [
        ("37352", DESC),
        ("27795", DESC.replace("6MG/ML", "3MG/ML")),
        ("27795", DESC.replace("3ML", "1ML")),
        ("27795", "INSULINA DEGLUDECA + " + DESC),
        ("27795", DESC + " LIBERAÇÃO PROLONGADA"),
    ],
)
def test_wrong_code_association_strength_device_or_release_rejected(
    corpus: Corpus, code: str, description: str
) -> None:
    assert not live.compatible_product(
        candidates("liraglutida", corpus[0])[0], code, description, corpus[0]
    )


def test_ceaf_filter_uses_ceaf_columns() -> None:
    body = query_body(CEAF, 2000, product_codes=("27795",), product_name="LIRAGLUTIDA")
    serialized = json.dumps(body)
    assert '"Property": "cod_produto2"' in serialized and '"Property": "desc_produto"' in serialized
    assert '"i_cod_produto"' not in serialized


def test_cache_failure_preserves_old_data_and_timestamp(
    corpus: Corpus, client: Any, tmp_path: Path
) -> None:
    m = candidates("liraglutida", corpus[0])[0]
    live.lookup_stock(m, corpus[0], "Planaltina")
    path = next((tmp_path / "data/gold/stock_queries").glob("*.json"))
    before = path.read_bytes()
    client.fail = {"ubs", "ceaf"}
    reply = live.lookup_stock(m, corpus[0], "Planaltina")
    assert path.read_bytes() == before
    assert "snapshot anterior" in reply and "sem confirmação atual" in reply
    assert "secret-never-log" not in reply


def test_partial_failure_does_not_discard_other_channel(corpus: Corpus, client: Any) -> None:
    client.fail = {"ubs"}
    reply = live.lookup_stock(candidates("liraglutida", corpus[0])[0], corpus[0], "Planaltina")
    assert "Consulta UBS indisponível" in reply and "Asa Sul: o painel informa COM ESTOQUE" in reply


def test_no_regional_rows_does_not_use_other_region(corpus: Corpus, client: Any) -> None:
    client.region = "Taguatinga"
    reply = live.lookup_stock(candidates("liraglutida", corpus[0])[0], corpus[0], "Planaltina")
    assert "Não há registro desse produto em Planaltina" in reply
    assert "saldo positivo para" not in reply


def test_cep_is_not_collected_or_resolved(
    corpus: Corpus, settings: Settings, monkeypatch: Any
) -> None:
    monkeypatch.setattr(chat, "lookup_stock", lambda *a: pytest.fail("CEP must not query"))
    reply = chat.ask("meu CEP é 73300-000", *corpus, settings, {})
    assert "ainda não está integrada" in reply and "informe somente a região" in reply


def test_common_name_shows_documented_salts_without_merging_forms(
    corpus: Corpus, settings: Settings
) -> None:
    reply = chat.ask("losartana", *corpus, settings, {}, documental=True)
    assert "potássica" in reply or "potassica" in reply
    assert "50 mg" in reply and "comprimido revestido" in reply
    state = chat.ConversationState()
    state.resolve("losartana", corpus[0])
    assert "losartana" in state.resolve("Planaltina", corpus[0])
