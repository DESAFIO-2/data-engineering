import json
from hashlib import sha256
from pathlib import Path

from sus_cidadao_data.ingestion.base import BaseConnector


class Connector(BaseConnector):
    source_url = "https://example.test"

    def fetch(self) -> dict[str, list[int]]:
        return {"items": [1]}


def test_metadata_hash_is_stable_for_same_payload() -> None:
    payload = {"items": [1]}
    metadata = Connector().generate_metadata(payload)
    expected = sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    assert metadata.payload_sha256 == expected


def test_checkpoint_round_trip(tmp_path: Path) -> None:
    connector = Connector()
    connector.save_checkpoint(tmp_path, page=3, cursor="abc")
    assert connector.load_checkpoint(tmp_path) == {"cursor": "abc", "page": 3}
