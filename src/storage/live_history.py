"""Persistência aditiva Medallion (Bronze JSON + Silver SQLite) para consultas ao vivo."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .repository import FileStorageRepository
from .silver_models import StockStatus

logger = logging.getLogger(__name__)


def _parse_reference_datetime(value: Any, fallback: datetime) -> datetime:
    if isinstance(value, str) and value.strip():
        raw = value.strip().replace("Z", "+00:00")
        for candidate in (raw, raw.replace(" ", "T")):
            try:
                parsed = datetime.fromisoformat(candidate)
                return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
            except ValueError:
                continue
        for fmt in ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%d/%m/%Y"):
            try:
                return datetime.strptime(value.strip(), fmt).replace(tzinfo=UTC)
            except ValueError:
                continue
    return fallback


def _to_non_negative_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return max(0, value)
    if isinstance(value, float):
        return max(0, int(value))
    if isinstance(value, str):
        cleaned = value.strip().replace(".", "").replace(",", ".")
        try:
            return max(0, int(float(cleaned)))
        except ValueError:
            return None
    return None


def _ceaf_status(label: str) -> StockStatus:
    folded = label.casefold()
    if "indispon" in folded or "zerad" in folded or "sem estoque" in folded:
        return StockStatus.ZERADO
    if "bloque" in folded:
        return StockStatus.BLOQUEADO
    return StockStatus.DISPONIVEL


def persist_live_stock_history(
    data_root: Path,
    medicine_id: str,
    result: dict[str, Any],
    fetched_at_utc: str,
) -> tuple[str, int]:
    """Grava payload bruto na Bronze e snapshots normalizados na Silver SQLite.

    Apenas identificadores do catálogo e dados públicos da API são persistidos;
    nenhuma pergunta, CEP ou região informada pelo cidadão entra na gravação.
    """
    repo = FileStorageRepository(data_root)
    fallback_dt = _parse_reference_datetime(fetched_at_utc, datetime.now(UTC))
    bronze_payload = {
        "medicine_id": medicine_id,
        "release_fingerprint": result.get("release_fingerprint"),
        "sources": result.get("sources", {}),
        "ubs_products": result.get("ubs_products", []),
        "ubs_stock": result.get("ubs_stock", []),
        "ceaf_stock": result.get("ceaf_stock", []),
    }
    digest = repo.save_bronze(
        "infosaude_live",
        bronze_payload,
        metadata={
            "medicine_id": medicine_id,
            "fetched_at_utc": fetched_at_utc,
        },
    )
    saved = 0
    for row in result.get("ubs_stock", []):
        pharmacy = str(
            row.get("i_desc_estabelecimento")
            or row.get("i_desc_unidade")
            or row.get("i_desc_radf")
            or ""
        ).strip()
        qty = _to_non_negative_int(row.get("i_qtd_rede"))
        if not pharmacy or qty is None:
            continue
        ref_dt = _parse_reference_datetime(row.get("data_extracao"), fallback_dt)
        repo.save_silver_snapshot(
            {
                "id_medicamento": medicine_id,
                "id_farmacia": f"UBS:{pharmacy}",
                "data_referencia": ref_dt,
                "quantidade": qty,
                "status": StockStatus.DISPONIVEL if qty > 0 else StockStatus.ZERADO,
            }
        )
        saved += 1
    for row in result.get("ceaf_stock", []):
        unit = str(row.get("unidade") or "").strip()
        disp = str(row.get("disp_estoque") or "").strip()
        if not unit or not disp:
            continue
        status = _ceaf_status(disp)
        ref_dt = _parse_reference_datetime(row.get("ultima_atualizacao"), fallback_dt)
        repo.save_silver_snapshot(
            {
                "id_medicamento": medicine_id,
                "id_farmacia": f"CEAF:{unit}",
                "data_referencia": ref_dt,
                "quantidade": 1 if status == StockStatus.DISPONIVEL else 0,
                "status": status,
            }
        )
        saved += 1
    return digest, saved
