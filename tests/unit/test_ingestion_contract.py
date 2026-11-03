from typing import Any

import pytest

from sus_cidadao_data.ingestion.base import BaseConnector


class Connector(BaseConnector):
    def fetch(self) -> Any:
        return {"items": [1]}

    def validate(self, payload: Any) -> bool:
        return "items" in payload

    def save_raw(self, payload: Any) -> str:
        return "raw-id"


def test_connector_contract_exposes_expected_flow() -> None:
    connector = Connector()
    payload = connector.fetch()
    assert connector.validate(payload)
    assert connector.save_raw(payload) == "raw-id"


def test_base_connector_is_abstract() -> None:
    with pytest.raises(TypeError):
        BaseConnector()  # type: ignore[abstract]
