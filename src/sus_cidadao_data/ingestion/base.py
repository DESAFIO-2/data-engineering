"""Contratos para conectores de fontes externas."""

from abc import ABC, abstractmethod
from typing import Any


class BaseConnector(ABC):
    """Interface mínima para coletar, validar e persistir uma fonte."""

    @abstractmethod
    def fetch(self) -> Any:
        """Coleta o payload bruto da fonte."""
        raise NotImplementedError

    @abstractmethod
    def validate(self, payload: Any) -> bool:
        """Valida o payload sem transformá-lo."""
        raise NotImplementedError

    @abstractmethod
    def save_raw(self, payload: Any) -> str:
        """Persiste o payload na camada Bronze e retorna seu identificador."""
        raise NotImplementedError
