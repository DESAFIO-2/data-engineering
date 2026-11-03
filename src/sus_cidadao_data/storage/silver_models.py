"""Modelos tipados da Silver e tratamento explícito de schema drift."""

import logging
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)


class StockStatus(StrEnum):
    DISPONIVEL = "DISPONIVEL"
    ZERADO = "ZERADO"
    BLOQUEADO = "BLOQUEADO"


class MedicamentoSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")
    principio_ativo: str = Field(min_length=1)
    concentracao: str = Field(min_length=1)
    forma: str = Field(min_length=1)


class FarmaciaSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")
    polo: str = Field(min_length=1)
    endereco: str = Field(min_length=1)
    regiao_administrativa: str = Field(min_length=1)


class EstoqueSnapshotSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id_medicamento: str = Field(min_length=1)
    id_farmacia: str = Field(min_length=1)
    data_referencia: datetime
    quantidade: int = Field(ge=0)
    status: StockStatus

    def model_post_init(self, __context: Any) -> None:
        if self.data_referencia.tzinfo is None:
            object.__setattr__(self, "data_referencia", self.data_referencia.replace(tzinfo=UTC))


def validate_with_drift[ModelT: BaseModel](model: type[ModelT], data: dict[str, Any]) -> ModelT:
    known = set(model.model_fields)
    omitted, unknown = known - set(data), set(data) - known
    if omitted or unknown:
        logger.warning(
            "silver_schema_drift",
            extra={"model": model.__name__, "omitted": sorted(omitted), "unknown": sorted(unknown)},
        )
    return model.model_validate(data)
