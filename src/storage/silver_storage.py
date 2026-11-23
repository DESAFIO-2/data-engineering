"""Armazenamento local temporal da camada Silver."""

import sqlite3
from contextlib import closing
from datetime import UTC
from pathlib import Path
from typing import Any

from .silver_models import EstoqueSnapshotSchema, validate_with_drift


class FileSilverStorage:
    def __init__(self, root: Path | None = None) -> None:
        self.database = root / "estoque.sqlite3" if root else None
        if root and self.database:
            root.mkdir(parents=True, exist_ok=True)
            with closing(sqlite3.connect(self.database)) as db, db:
                db.execute(
                    "CREATE TABLE IF NOT EXISTS estoque (med TEXT, farmacia TEXT, "
                    "referencia TEXT, payload TEXT NOT NULL, "
                    "PRIMARY KEY (med, farmacia, referencia))"
                )
                legacy = root / "snapshots.jsonl"
                if legacy.is_file() and not db.execute("PRAGMA user_version").fetchone()[0]:
                    with legacy.open(encoding="utf-8") as stream:
                        for line in stream:
                            if line.strip():
                                snapshot = EstoqueSnapshotSchema.model_validate_json(line)
                                db.execute(
                                    "INSERT OR IGNORE INTO estoque VALUES (?, ?, ?, ?)",
                                    (
                                        snapshot.id_medicamento,
                                        snapshot.id_farmacia,
                                        snapshot.data_referencia.astimezone(UTC).isoformat(
                                            timespec="microseconds"
                                        ),
                                        snapshot.model_dump_json(),
                                    ),
                                )
                    db.execute("PRAGMA user_version=1")
        self.snapshots: list[EstoqueSnapshotSchema] = []

    def save(self, data: dict[str, Any]) -> EstoqueSnapshotSchema:
        snapshot = validate_with_drift(EstoqueSnapshotSchema, data)
        if self.database:
            timestamp = snapshot.data_referencia.astimezone(UTC).isoformat(timespec="microseconds")
            with closing(sqlite3.connect(self.database)) as db, db:
                db.execute(
                    "INSERT INTO estoque VALUES (?, ?, ?, ?) "
                    "ON CONFLICT(med, farmacia, referencia) DO UPDATE SET payload=excluded.payload",
                    (
                        snapshot.id_medicamento,
                        snapshot.id_farmacia,
                        timestamp,
                        snapshot.model_dump_json(),
                    ),
                )
        else:
            self.snapshots.append(snapshot)
        return snapshot

    def latest(self, medicamento: str, farmacia: str) -> EstoqueSnapshotSchema | None:
        if self.database:
            with closing(sqlite3.connect(self.database)) as db:
                row = db.execute(
                    "SELECT payload FROM estoque WHERE med=? AND farmacia=? "
                    "ORDER BY referencia DESC LIMIT 1",
                    (medicamento, farmacia),
                ).fetchone()
            return EstoqueSnapshotSchema.model_validate_json(row[0]) if row else None
        matches = [
            item
            for item in self.snapshots
            if item.id_medicamento == medicamento and item.id_farmacia == farmacia
        ]
        return max(matches, key=lambda item: item.data_referencia) if matches else None
