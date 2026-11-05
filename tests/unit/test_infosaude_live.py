from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

import ingestion.infosaude_live as live_source
import rag.cli as cli
from ingestion.infosaude_live import UBS, decode_dsr, query_body
from rag.live import PRODUCTS, live_reply
from rag.release import Release

RELEASE = Path(__file__).resolve().parents[2] / "data/releases/rag-lote-1-aprovado-2026-11-05"


def test_dsr_decodes_dictionaries_repeat_and_null() -> None:
    payload: dict[str, Any] = {
        "results": [
            {
                "result": {
                    "data": {
                        "dsr": {
                            "DS": [
                                {
                                    "ValueDicts": {"D0": ["A", "B"]},
                                    "PH": [
                                        {
                                            "DM0": [
                                                {"S": [{"DN": "D0"}, {}], "C": [0, 12]},
                                                {"C": [1], "R": 2},
                                                {"C": [7], "Ø": 1},
                                            ]
                                        }
                                    ],
                                }
                            ]
                        }
                    }
                }
            }
        ]
    }
    assert decode_dsr(payload, ("product", "amount")) == [
        {"product": "A", "amount": 12},
        {"product": "B", "amount": 12},
        {"product": None, "amount": 7},
    ]


def test_ubs_query_filters_only_approved_product_codes() -> None:
    payload = query_body(UBS, 5000, tuple(code for code, _ in PRODUCTS.values()))
    command = payload["queries"][0]["Query"]["Commands"][0]["SemanticQueryDataShapeCommand"]
    values = command["Query"]["Where"][0]["Condition"]["In"]["Values"]
    assert len(values) == 6
    assert {item[0]["Literal"]["Value"].strip("'") for item in values} == {
        code for code, _ in PRODUCTS.values()
    }


def test_stock_answer_uses_dated_record_and_unit_address() -> None:
    release = Release.load(RELEASE)
    snapshot = {
        "fetched_at_utc": datetime.now(UTC).isoformat(),
        "sources": {
            "ubs": "https://info.saude.df.gov.br/ubs",
            "locations": "https://info.saude.df.gov.br",
        },
        "ubs_stock": [
            {
                "i_cod_produto": "694",
                "i_desc_produto": "SINVASTATINA COMPRIMIDO 20 MG",
                "i_qtd_rede": 20,
                "data_extracao": int(datetime.now(UTC).timestamp() * 1000),
                "i_desc_local_estoque": "FARMÁCIA - UBS 1 - DCCP",
                "cnes": "263680",
                "i_desc_radf": "Plano Piloto",
            }
        ],
        "locations": [
            {
                "cnes": "0263680",
                "nome_fanta": "UBS 01 DCCP",
                "logradouro": "Rua Central",
                "numero": "1",
                "bairro": "Plano Piloto",
                "latitude": "-15.8",
                "longitude": "-47.9",
            }
        ],
    }
    answer = live_reply("Onde tem estoque de sinvastatina 20 mg comprimido?", release, snapshot)
    assert answer is not None
    assert "UBS 01 DCCP" in answer
    assert "Rua Central" in answer
    assert "Extração do painel" in answer
    assert "BRT" in answer
    assert "data não informada" not in answer
    assert "Fonte: https://info.saude.df.gov.br/ubs" in answer
    assert "maps/search" in answer


def test_stock_without_snapshot_does_not_claim_availability() -> None:
    release = Release.load(RELEASE)
    answer = live_reply("Sinvastatina 20 mg comprimido tem estoque?", release, None)
    assert answer is not None
    assert "não sincronizados" in answer


def test_sync_preserves_previous_snapshot_if_panel_is_incomplete(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class IncompleteClient:
        def fetch(
            self, panel: Any, *, limit: int, product_codes: tuple[str, ...] = ()
        ) -> list[dict[str, Any]]:
            if panel is UBS:
                return [{"i_cod_produto": "694"}]
            return [{"sample": "data"}]

    path = tmp_path / "snapshot.json"
    path.write_text("previous snapshot", encoding="utf-8")
    monkeypatch.setattr(live_source, "InfoSaudeLiveClient", IncompleteClient)
    with pytest.raises(ValueError, match="seis códigos"):
        live_source.sync_snapshot(path, tuple(code for code, _ in PRODUCTS.values()))
    assert path.read_text(encoding="utf-8") == "previous snapshot"


def test_chat_syncs_before_accepting_questions(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    events: list[str] = []

    def fake_sync(path: Path, product_codes: tuple[str, ...]) -> dict[str, Any]:
        events.append("sync")
        assert len(product_codes) == 6
        return {"ceaf_stock": [], "ubs_stock": [], "locations": []}

    def fake_input(prompt: str) -> str:
        events.append("input")
        return "sair"

    monkeypatch.setattr(cli, "sync_snapshot", fake_sync)
    monkeypatch.setattr("builtins.input", fake_input)
    monkeypatch.setattr("sys.argv", ["app.py", "chat"])

    assert cli.main() == 0
    assert events == ["sync", "input"]
    assert "InfoSaúde sincronizado" in capsys.readouterr().out
