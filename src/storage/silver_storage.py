"""Armazenamento local temporal da camada Silver (memória e JSONL opcional em disco)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .silver_models import EstoqueSnapshotSchema, validate_with_drift


class FileSilverStorage:
    """Persist validated Silver snapshots in memory and optionally as JSONL on disk."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = Path(root) if root is not None else None
        self.snapshots: list[EstoqueSnapshotSchema] = []
        if self.root is not None:
            path = self.root / "snapshots.jsonl"
            if path.is_file():
                for line in path.read_text(encoding="utf-8").splitlines():
                    if line.strip():
                        self.snapshots.append(EstoqueSnapshotSchema.model_validate_json(line))

    def save(self, data: dict[str, Any]) -> EstoqueSnapshotSchema:
        snapshot = validate_with_drift(EstoqueSnapshotSchema, data)
        self.snapshots.append(snapshot)
        if self.root is not None:
            self.root.mkdir(parents=True, exist_ok=True)
            path = self.root / "snapshots.jsonl"
            with path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(snapshot.model_dump_json() + "\n")
        return snapshot

    def latest(self, medicamento: str, farmacia: str) -> EstoqueSnapshotSchema | None:
        matches = [
            item
            for item in self.snapshots
            if item.id_medicamento == medicamento and item.id_farmacia == farmacia
        ]
        return max(matches, key=lambda item: item.data_referencia) if matches else None
