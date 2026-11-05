from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from storage.silver_models import (
    EstoqueSnapshotSchema,
    StockStatus,
    validate_with_drift,
)


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
