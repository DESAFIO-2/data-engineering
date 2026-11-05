"""Conector JSON do painel de estoque da SES-DF."""

from typing import Any, cast

import requests

from .base import BaseConnector


class InfoSaudeDFConnector(BaseConnector):
    default_source_url = (
        "https://info.saude.df.gov.br/saude-do-cidadao/"
        "painel-infosaude-farmacias-de-alto-custo/estoque-de-medicamentos/"
    )

    def __init__(
        self, endpoint_url: str | None = None, session: requests.Session | None = None
    ) -> None:
        self.endpoint_url = endpoint_url or self.default_source_url
        self.session = session or self.request_session()
        self.last_http_status: int | None = None

    def fetch(self) -> dict[str, Any] | list[Any]:
        response = self.session.get(
            self.endpoint_url, timeout=30, headers={"Accept": "application/json"}
        )
        self.last_http_status = response.status_code
        response.raise_for_status()
        return cast(dict[str, Any] | list[Any], response.json())

    def validate_schema(self, raw_data: Any) -> bool:
        return isinstance(raw_data, list) or (
            isinstance(raw_data, dict)
            and any(key in raw_data for key in ("data", "items", "value", "records"))
        )

    def fetch_with_session_token(self, token: str) -> dict[str, Any] | list[Any]:
        response = self.session.get(
            self.endpoint_url,
            timeout=30,
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        )
        self.last_http_status = response.status_code
        response.raise_for_status()
        return cast(dict[str, Any] | list[Any], response.json())

    @property
    def source_url(self) -> str:  # type: ignore[override]
        return self.endpoint_url
