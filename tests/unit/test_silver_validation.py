from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from storage.repository import FileStorageRepository
from storage.silver_models import (
    EstoqueSnapshotSchema,
    StockStatus,
    validate_with_drift,
)
from storage.silver_storage import FileSilverStorage


def test_snapshot_accepts_optional_schema_drift_and_normalizes_naive_datetime(
    caplog: pytest.LogCaptureFixture,
) -> None:
    snapshot = validate_with_drift(
        EstoqueSnapshotSchema,
        {
            "id_medicamento": "med-1",
            "id_farmacia": "farm-1",
            "data_referencia": datetime(2026, 11, 3, 12),
            "quantidade": 4,
            "status": "DISPONIVEL",
            "campo_novo": "preservar no alerta",
        },
    )
    assert snapshot.data_referencia.tzinfo == UTC
    assert "silver_schema_drift" in caplog.text


def test_snapshot_rejects_negative_quantity() -> None:
    with pytest.raises(ValidationError):
        EstoqueSnapshotSchema(
            id_medicamento="med-1",
            id_farmacia="farm-1",
            data_referencia=datetime.now(UTC),
            quantidade=-1,
            status=StockStatus.ZERADO,
        )


def test_silver_storage_and_repository_persist_and_reload_on_disk(tmp_path: Path) -> None:
    older = {
        "id_medicamento": "med-1",
        "id_farmacia": "farm-1",
        "data_referencia": datetime(2026, 11, 1, 10, tzinfo=UTC),
        "quantidade": 0,
        "status": "ZERADO",
    }
    newer = {
        "id_medicamento": "med-1",
        "id_farmacia": "farm-1",
        "data_referencia": datetime(2026, 11, 2, 12, tzinfo=UTC),
        "quantidade": 15,
        "status": "DISPONIVEL",
    }

    memory_only = FileSilverStorage()
    memory_only.save(older)
    assert memory_only.latest("med-1", "farm-1") is not None

    repo = FileStorageRepository(tmp_path)
    repo.save_silver_snapshot(older)
    repo.save_silver_snapshot(newer)
    assert (tmp_path / "silver/snapshots.jsonl").is_file()

    reloaded = FileStorageRepository(tmp_path)
    latest = reloaded.get_latest_stock("med-1", "farm-1")
    assert latest is not None
    assert latest.quantidade == 15
    assert latest.status == StockStatus.DISPONIVEL
