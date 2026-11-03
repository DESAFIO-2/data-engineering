"""Repository Pattern para desacoplar ingestão do motor de persistência."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from .bronze_storage import FileBronzeStorage
from .silver_storage import FileSilverStorage


class StorageRepository(ABC):
    @abstractmethod
    def save_bronze(
        self, source_name: str, payload: Any, metadata: dict[str, Any] | None = None
    ) -> str: ...
    @abstractmethod
    def save_silver_snapshot(self, snapshot: Any) -> None: ...
    @abstractmethod
    def get_latest_stock(self, medicamento: str, farmacia: str) -> Any: ...


class FileStorageRepository(StorageRepository):
    def __init__(self, root: Path) -> None:
        self.bronze = FileBronzeStorage(root / "bronze")
        self.silver = FileSilverStorage()

    def save_bronze(
        self, source_name: str, payload: Any, metadata: dict[str, Any] | None = None
    ) -> str:
        digest, _ = self.bronze.save(source_name, payload, metadata)
        return digest

    def save_silver_snapshot(self, snapshot: Any) -> None:
        self.silver.save(snapshot if isinstance(snapshot, dict) else snapshot.model_dump())

    def get_latest_stock(self, medicamento: str, farmacia: str) -> Any:
        return self.silver.latest(medicamento, farmacia)
