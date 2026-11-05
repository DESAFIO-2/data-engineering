import json
from pathlib import Path

from storage.bronze import JsonBronzeStore


def test_bronze_writes_payload_and_collection_metadata(tmp_path: Path) -> None:
    store = JsonBronzeStore(tmp_path)
    digest = store.write(
        {"medicamentos": [{"nome": "Teste", "estoque": 3}]},
        {"source_id": "infosaude-df", "collected_at": "2026-11-03T12:00:00+00:00"},
    )

    document = json.loads((tmp_path / f"{digest}.json").read_text())
    assert document["metadata"]["source_id"] == "infosaude-df"
    assert document["metadata"]["collected_at"] == "2026-11-03T12:00:00+00:00"
    assert document["payload"]["medicamentos"][0]["estoque"] == 3
