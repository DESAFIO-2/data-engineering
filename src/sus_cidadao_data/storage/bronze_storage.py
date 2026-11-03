"""Bronze imutável, particionada por fonte, data e SHA-256."""

import json
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any


class FileBronzeStorage:
    def __init__(self, root: Path) -> None:
        self.root = Path(root)

    def save(
        self, source_name: str, payload: Any, metadata: dict[str, Any] | None = None
    ) -> tuple[str, bool]:
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str).encode()
        digest = sha256(encoded).hexdigest()
        now = datetime.now(UTC)
        path = (
            self.root
            / source_name
            / str(now.year)
            / f"{now.month:02d}"
            / f"{now.day:02d}"
            / f"{digest}.json"
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        duplicate = path.exists()
        if not duplicate:
            path.write_text(
                json.dumps(
                    {
                        "metadata": {
                            **(metadata or {}),
                            "payload_sha256": digest,
                            "collected_at": now.isoformat(),
                        },
                        "payload": payload,
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                )
            )
        return digest, duplicate
