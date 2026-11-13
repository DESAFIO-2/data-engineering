"""Contratos e utilitários comuns para conectores de fontes externas."""

import json
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any
from uuid import uuid4

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


@dataclass(frozen=True)
class IngestionMetadata:
    ingestion_id: str
    collected_at: str
    source_url: str
    http_status: int | None
    payload_sha256: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_retry_session(
    total: int = 4,
    backoff_factor: float = 0.5,
    status_forcelist: tuple[int, ...] = (429, 500, 502, 503, 504),
) -> requests.Session:
    """Create a requests.Session configured with exponential backoff retries."""
    retry = Retry(
        total=total,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        allowed_methods=frozenset({"GET", "POST"}),
        raise_on_status=False,
    )
    session = requests.Session()
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


class BaseConnector(ABC):
    """Interface mínima para coletar, validar e persistir uma fonte."""

    @abstractmethod
    def fetch(self) -> Any:
        """Coleta o payload bruto da fonte."""
        raise NotImplementedError

    def validate_schema(self, raw_data: Any) -> bool:
        return isinstance(raw_data, (dict, list))

    def validate(self, payload: Any) -> bool:
        """Alias de compatibilidade para o contrato anterior."""
        return self.validate_schema(payload)

    def generate_metadata(self, raw_data: Any) -> IngestionMetadata:
        encoded = json.dumps(raw_data, ensure_ascii=False, sort_keys=True, default=str).encode()
        return IngestionMetadata(
            uuid4().hex,
            datetime.now(UTC).isoformat(),
            self.source_url,
            getattr(self, "last_http_status", None),
            sha256(encoded).hexdigest(),
        )

    def request_session(self) -> requests.Session:
        return build_retry_session()

    def checkpoint_path(self, directory: Path) -> Path:
        return directory / f"{type(self).__name__}.json"

    def load_checkpoint(self, directory: Path) -> dict[str, Any]:
        path = self.checkpoint_path(directory)
        return json.loads(path.read_text()) if path.exists() else {}

    def save_checkpoint(self, directory: Path, **state: Any) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        self.checkpoint_path(directory).write_text(json.dumps(state, sort_keys=True))

    source_url = ""
