"""Testes de integração da camada src/storage (Bronze + Silver SQLite) com estoque vivo."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest

import rag.consolidated.live as live
from ingestion.infosaude_live import UBS
from rag.consolidated import ConsolidatedRelease
from storage import (
    BronzeStore,
    FileBronzeStorage,
    FileSilverStorage,
    FileStorageRepository,
    SilverStore,
    StockStatus,
    persist_live_stock_history,
)


def _fake_release() -> ConsolidatedRelease:
    return cast(
        ConsolidatedRelease,
        SimpleNamespace(
            fingerprint="fp-test-storage",
            occurrences=[
                {
                    "medicine_id": "med-met-500",
                    "source_code": "1001",
                    "source": {"source_id": "F03"},
                }
            ],
        ),
    )


def _fake_medicine() -> dict[str, Any]:
    return {
        "medicine_id": "med-met-500",
        "active_ingredient": "cloridrato de metformina",
        "strength": "500 mg",
        "form": "comprimido",
        "release_characteristic": None,
    }


def test_file_storages_implement_base_contracts(tmp_path: Path) -> None:
    bronze = FileBronzeStorage(tmp_path / "bronze")
    silver = FileSilverStorage(tmp_path / "silver")
    assert isinstance(bronze, BronzeStore)
    assert isinstance(silver, SilverStore)

    digest = bronze.write({"ok": True}, {"source": "infosaude_live"})
    assert len(digest) == 64

    written = silver.write_records(
        [
            {
                "id_medicamento": "med-1",
                "id_farmacia": "UBS:Planaltina",
                "data_referencia": "2026-11-23T10:00:00+00:00",
                "quantidade": 12,
                "status": "DISPONIVEL",
            }
        ]
    )
    assert written == 1
    latest = silver.latest("med-1", "UBS:Planaltina")
    assert latest is not None
    assert latest.quantidade == 12
    assert latest.status == StockStatus.DISPONIVEL


def test_persist_live_stock_history_writes_bronze_and_silver_without_pii(tmp_path: Path) -> None:
    result = {
        "release_fingerprint": "fp-test-storage",
        "sources": {"ubs": "https://ubs", "ceaf": "https://ceaf"},
        "ubs_products": [
            {"i_cod_produto": "1001", "i_desc_produto": "METFORMINA 500MG COMPRIMIDO"}
        ],
        "ubs_stock": [
            {
                "i_cod_produto": "1001",
                "i_desc_produto": "METFORMINA 500MG COMPRIMIDO",
                "i_desc_estabelecimento": "UBS 1 PLANALTINA",
                "i_desc_radf": "Planaltina",
                "i_qtd_rede": 45,
                "data_extracao": "2026-11-23T09:30:00Z",
            }
        ],
        "ceaf_stock": [
            {
                "cod_produto2": "2002",
                "desc_produto": "METFORMINA 500MG COMPRIMIDO",
                "unidade": "ASA SUL",
                "disp_estoque": "Indisponível",
                "ultima_atualizacao": "2026-11-23T09:00:00Z",
            }
        ],
    }

    digest, saved = persist_live_stock_history(
        tmp_path / "data",
        "med-met-500",
        result,
        "2026-11-23T10:00:00+00:00",
    )
    assert len(digest) == 64
    assert saved == 2

    bronze_files = list((tmp_path / "data/bronze/infosaude_live").rglob("*.json"))
    assert len(bronze_files) == 1
    envelope = json.loads(bronze_files[0].read_text(encoding="utf-8"))
    assert envelope["metadata"]["medicine_id"] == "med-met-500"
    assert "region" not in envelope["payload"]
    assert "question" not in envelope["payload"]

    repo = FileStorageRepository(tmp_path / "data")
    ubs_latest = repo.get_latest_stock("med-met-500", "UBS:UBS 1 PLANALTINA")
    ceaf_latest = repo.get_latest_stock("med-met-500", "CEAF:ASA SUL")
    assert ubs_latest is not None
    assert ubs_latest.quantidade == 45
    assert ubs_latest.status == StockStatus.DISPONIVEL
    assert ceaf_latest is not None
    assert ceaf_latest.quantidade == 0
    assert ceaf_latest.status == StockStatus.ZERADO


def test_lookup_stock_persists_medallion_and_survives_storage_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class FakeClient:
        def discover_ubs_products(self, _term: str) -> list[dict[str, Any]]:
            return [
                {
                    "i_cod_produto": "1001",
                    "i_desc_produto": "CLORIDRATO DE METFORMINA 500MG COMPRIMIDO",
                }
            ]

        def fetch(self, source: Any, **_kwargs: Any) -> list[dict[str, Any]]:
            if source is UBS:
                return [
                    {
                        "i_cod_produto": "1001",
                        "i_desc_produto": "CLORIDRATO DE METFORMINA 500MG COMPRIMIDO",
                        "i_desc_estabelecimento": "UBS 1 PLANALTINA",
                        "i_desc_radf": "Planaltina",
                        "i_qtd_rede": 10,
                        "data_extracao": "2026-11-23T09:30:00Z",
                    }
                ]
            return []

    monkeypatch.setattr(live, "ROOT", tmp_path)
    monkeypatch.setattr(live, "load_snapshot", lambda *_a: None)
    monkeypatch.setattr(live, "InfoSaudeLiveClient", FakeClient)

    reply = live.lookup_stock(_fake_medicine(), _fake_release(), "Planaltina")
    assert "1001" in reply
    assert (tmp_path / "data/gold/stock_queries/med-met-500.json").is_file()
    assert (tmp_path / "data/silver/estoque.sqlite3").is_file()
    assert list((tmp_path / "data/bronze/infosaude_live").rglob("*.json"))

    def failing_persist(*_args: Any, **_kwargs: Any) -> tuple[str, int]:
        raise OSError("disk full")

    monkeypatch.setattr(live, "persist_live_stock_history", failing_persist)
    resilient_reply = live.lookup_stock(_fake_medicine(), _fake_release(), "Planaltina")
    assert "1001" in resilient_reply
