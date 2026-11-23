"""Camada unificada de persistência Medallion (Bronze JSON + Silver SQLite)."""

from .base import BronzeStore, SilverStore
from .bronze import JsonBronzeStore
from .bronze_storage import FileBronzeStorage
from .live_history import persist_live_stock_history
from .repository import FileStorageRepository, StorageRepository
from .silver import InMemorySilverStore
from .silver_models import (
    EstoqueSnapshotSchema,
    FarmaciaSchema,
    MedicamentoSchema,
    StockStatus,
    validate_with_drift,
)
from .silver_storage import FileSilverStorage

__all__ = [
    "BronzeStore",
    "EstoqueSnapshotSchema",
    "FarmaciaSchema",
    "FileBronzeStorage",
    "FileSilverStorage",
    "FileStorageRepository",
    "InMemorySilverStore",
    "JsonBronzeStore",
    "MedicamentoSchema",
    "SilverStore",
    "StockStatus",
    "StorageRepository",
    "persist_live_stock_history",
    "validate_with_drift",
]
