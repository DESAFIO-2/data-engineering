"""Consulta pública dos painéis InfoSaúde-DF e descompressão do formato DSR."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import requests

API = "https://wabi-brazil-south-api.analysis.windows.net/public/reports/querydata?synchronous=true"
CEAF_URL = (
    "https://info.saude.df.gov.br/saude-do-cidadao/"
    "painel-infosaude-farmacias-de-alto-custo/estoque-de-medicamentos/"
)
UBS_URL = "https://info.saude.df.gov.br/saude-do-cidadao/painel-infosaude-farmacias-das-ubs/"
LOCATIONS_URL = "https://info.saude.df.gov.br/saude-do-cidadao/"


@dataclass(frozen=True)
class Panel:
    key: str
    model_id: int
    dataset_id: str
    entity: str
    columns: tuple[str, ...]
    source_url: str


CEAF = Panel(
    "a665320c-1f2b-43cd-8380-6d39f535daf9",
    10730466,
    "424ade14-3f72-4830-a4dc-ab612ad877ee",
    "estoque_geral_ceaf",
    (
        "cod_produto2",
        "desc_produto",
        "unidade",
        "disp_estoque",
        "Origem do Abastecimento",
        "ultima_atualizacao",
    ),
    CEAF_URL,
)
LOCATIONS = Panel(
    "d77b9ba0-317a-4041-88a0-3241c35384ac",
    10722913,
    "c021e607-7580-407e-bbab-4312c5c14cd9",
    "Estabelecimentos",
    (
        "cnes",
        "nome_fanta",
        "logradouro",
        "numero",
        "complement",
        "bairro",
        "latitude",
        "longitude",
        "tipo_farmacia",
    ),
    LOCATIONS_URL,
)
UBS = Panel(
    "5ccba871-5230-4333-86f6-7fc3a29b5d5b",
    10723062,
    "ceb0186a-2546-4bfd-814e-5dad49b318cc",
    "st_stage_trak tab_sismateriais_epi",
    (
        "i_cod_produto",
        "i_desc_produto",
        "i_qtd_rede",
        "i_qtd_central",
        "data_extracao",
        "i_desc_local_estoque",
        "cnes",
        "i_desc_radf",
    ),
    UBS_URL,
)


def query_body(
    panel: Panel,
    limit: int,
    product_codes: tuple[str, ...] = (),
    product_name: str = "",
) -> dict[str, Any]:
    source = {"SourceRef": {"Source": "e"}}
    specialized = panel.entity == CEAF.entity
    code_column = "cod_produto2" if specialized else "i_cod_produto"
    description_column = "desc_produto" if specialized else "i_desc_produto"
    query: dict[str, Any] = {
        "Version": 2,
        "From": [{"Name": "e", "Entity": panel.entity, "Type": 0}],
        "Select": [
            {"Column": {"Expression": source, "Property": column}, "Name": f"e.{column}"}
            for column in panel.columns
        ],
    }
    if product_codes:
        query["Where"] = [
            {
                "Condition": {
                    "In": {
                        "Expressions": [
                            {"Column": {"Expression": source, "Property": code_column}}
                        ],
                        "Values": [[{"Literal": {"Value": f"'{code}'"}}] for code in product_codes],
                    }
                }
            }
        ]
    if product_name:
        query.setdefault("Where", []).append(
            {
                "Condition": {
                    "Contains": {
                        "Left": {"Column": {"Expression": source, "Property": description_column}},
                        "Right": {
                            "Literal": {"Value": "'" + product_name.replace("'", "''") + "'"}
                        },
                    }
                }
            }
        )
    shape = {
        "Query": query,
        "Binding": {
            "Primary": {"Groupings": [{"Projections": list(range(len(panel.columns)))}]},
            "DataReduction": {"DataVolume": 3, "Primary": {"Window": {"Count": limit}}},
            "Version": 1,
        },
    }
    return {
        "version": "1.0.0",
        "queries": [
            {
                "Query": {"Commands": [{"SemanticQueryDataShapeCommand": shape}]},
                "QueryId": "",
                "ApplicationContext": {
                    "DatasetId": panel.dataset_id,
                    "Sources": [{"ReportId": panel.key}],
                },
            }
        ],
        "cancelQueries": [],
        "modelId": panel.model_id,
    }


def decode_dsr(payload: dict[str, Any], columns: tuple[str, ...]) -> list[dict[str, Any]]:
    """Expande máscaras de repetição/nulo e dicionários de texto do Power BI."""
    dsr = payload["results"][0]["result"]["data"]["dsr"]
    if "DataShapes" in dsr:
        raise ValueError(f"Consulta Power BI recusada: {dsr['DataShapes']}")
    dataset = dsr["DS"][0]
    compressed = dataset["PH"][0]["DM0"]
    if not compressed:
        return []
    shape = compressed[0]["S"]
    if len(shape) != len(columns):
        raise ValueError("Número de colunas DSR divergente do contrato")
    dictionaries = dataset.get("ValueDicts", {})
    previous: list[Any] = [None] * len(columns)
    output: list[dict[str, Any]] = []
    for row in compressed:
        values = iter(row.get("C", []))
        current: list[Any] = []
        for index, descriptor in enumerate(shape):
            bit = 1 << index
            if row.get("Ø", 0) & bit:
                value = None
            elif row.get("R", 0) & bit:
                value = previous[index]
            else:
                value = next(values)
                dictionary = dictionaries.get(descriptor.get("DN", ""), [])
                if (
                    isinstance(value, int)
                    and not isinstance(value, bool)
                    and value < len(dictionary)
                ):
                    value = dictionary[value]
            current.append(value)
        if next(values, None) is not None:
            raise ValueError("Linha DSR contém valores além das colunas esperadas")
        output.append(dict(zip(columns, current, strict=True)))
        previous = current
    return output


class InfoSaudeLiveClient:
    def __init__(self, session: requests.Session | None = None) -> None:
        self.session = session or requests.Session()

    def fetch(
        self,
        panel: Panel,
        *,
        limit: int,
        product_codes: tuple[str, ...] = (),
        product_name: str = "",
    ) -> list[dict[str, Any]]:
        response = self.session.post(
            API,
            json=query_body(panel, limit, product_codes, product_name),
            headers={"X-PowerBI-ResourceKey": panel.key, "Accept": "application/json"},
            timeout=30,
        )
        response.raise_for_status()
        rows = decode_dsr(response.json(), panel.columns)
        if len(rows) >= limit:
            raise ValueError(f"Consulta {panel.entity} atingiu o limite de {limit} linhas")
        return rows

    def discover_ubs_products(self, name: str) -> list[dict[str, Any]]:
        """Distinct product pairs, filtered server-side; refuse truncated catalogs."""
        if not name.strip():
            raise ValueError("Informe o nome do produto UBS")
        catalog = Panel(
            UBS.key,
            UBS.model_id,
            UBS.dataset_id,
            UBS.entity,
            ("i_cod_produto", "i_desc_produto"),
            UBS.source_url,
        )
        return self.fetch(catalog, limit=5000, product_name=name.upper())


def sync_snapshot(path: Path, product_codes: tuple[str, ...]) -> dict[str, Any]:
    client = InfoSaudeLiveClient()
    ceaf = client.fetch(CEAF, limit=2000)
    locations = client.fetch(LOCATIONS, limit=1000)
    ubs = client.fetch(UBS, limit=5000, product_codes=product_codes)
    if not ceaf or not locations or not ubs:
        raise ValueError("Painel público retornou conjunto vazio; snapshot anterior preservado")
    if {str(row.get("i_cod_produto")) for row in ubs} != set(product_codes):
        raise ValueError(
            "Painel UBS não retornou todos os códigos solicitados "
            f"({len(product_codes)}); snapshot anterior preservado"
        )
    snapshot = {
        "fetched_at_utc": datetime.now(UTC).isoformat(),
        "sources": {
            "ceaf": CEAF.source_url,
            "locations": LOCATIONS.source_url,
            "ubs": UBS.source_url,
        },
        "ceaf_stock": ceaf,
        "locations": locations,
        "ubs_stock": ubs,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(snapshot, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)
    return snapshot
