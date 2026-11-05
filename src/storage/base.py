"""Contratos agnósticos de persistência por camada."""

from abc import ABC, abstractmethod
from typing import Any


class BronzeStore(ABC):
    """Persistência de payloads imutáveis e seus metadados de coleta."""

    @abstractmethod
    def write(self, payload: Any, metadata: dict[str, Any]) -> str:
        raise NotImplementedError


class SilverStore(ABC):
    """Persistência de registros normalizados e prontos para consulta."""

    @abstractmethod
    def write_records(self, records: list[dict[str, Any]]) -> int:
        raise NotImplementedError
