"""Armazenamento local temporal da camada Silver."""

from typing import Any

from .silver_models import EstoqueSnapshotSchema, validate_with_drift


class FileSilverStorage:
    def __init__(self) -> None:
        self.snapshots: list[EstoqueSnapshotSchema] = []

    def save(self, data: dict[str, Any]) -> EstoqueSnapshotSchema:
        snapshot = validate_with_drift(EstoqueSnapshotSchema, data)
        self.snapshots.append(snapshot)
        return snapshot

    def latest(self, medicamento: str, farmacia: str) -> EstoqueSnapshotSchema | None:
        matches = [
            item
            for item in self.snapshots
            if item.id_medicamento == medicamento and item.id_farmacia == farmacia
        ]
        return max(matches, key=lambda item: item.data_referencia) if matches else None
