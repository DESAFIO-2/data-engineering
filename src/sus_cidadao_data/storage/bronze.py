"""Implementação local simples da camada Bronze em JSON."""

import json
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

from .base import BronzeStore


class JsonBronzeStore(BronzeStore):
    """Grava cada coleta como um envelope JSON com metadados e hash."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def write(self, payload: Any, metadata: dict[str, Any]) -> str:
        collected_at = metadata.get("collected_at", datetime.now(UTC).isoformat())
        envelope = {"metadata": {**metadata, "collected_at": collected_at}, "payload": payload}
        encoded = json.dumps(envelope, ensure_ascii=False, sort_keys=True).encode("utf-8")
        digest = sha256(encoded).hexdigest()
        path = self.root / f"{digest}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(encoded)
        return digest
