"""Ponto de extensão para persistência Silver normalizada."""

from typing import Any

from .base import SilverStore


class InMemorySilverStore(SilverStore):
    """Implementação de referência útil para testes e protótipos."""

    def __init__(self) -> None:
        self.records: list[dict[str, Any]] = []

    def write_records(self, records: list[dict[str, Any]]) -> int:
        self.records.extend(records)
        return len(records)
