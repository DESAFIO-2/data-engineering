from pathlib import Path

from storage import FileStorageRepository


def test_stock_survives_restart_and_out_of_order_replay(tmp_path: Path) -> None:
    repo = FileStorageRepository(tmp_path)
    row = dict(
        id_medicamento="A",
        id_farmacia="B",
        data_referencia="2026-11-13T08:00:00-03:00",
        quantidade=7,
        status="DISPONIVEL",
    )
    repo.save_silver_snapshot(row)
    repo.save_silver_snapshot({**row, "data_referencia": "2026-11-13T10:00:00Z", "quantidade": 3})
    repo = FileStorageRepository(tmp_path)
    assert repo.get_latest_stock("A", "B").quantidade == 7
    repo.save_silver_snapshot({**row, "data_referencia": "2026-11-13T11:00:00Z", "quantidade": 6})
    assert FileStorageRepository(tmp_path).get_latest_stock("A", "B").quantidade == 6
    assert repo.get_latest_stock("A", "C") is None
