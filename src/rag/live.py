"""Respostas determinísticas para estoque e localização do InfoSaúde-DF."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

from .release import Release
from .retrieval import match_medicine, normalize

PRODUCTS: dict[str, tuple[str, str]] = {
    "med-832a5f9b36e58e02": ("90491", "GLIBENCLAMIDA COMPRIMIDO 5 MG"),
    "med-5b5e165c0b63c656": ("19847", "HIDROCLOROTIAZIDA COMPRIMIDO 25 MG"),
    "med-b7f98aaf59018d9b": ("90380", "FUROSEMIDA COMPRIMIDO 40 MG"),
    "med-023e1cc046cc30e1": ("694", "SINVASTATINA COMPRIMIDO 20 MG"),
    "med-15dc637fe3472c1f": ("695", "SINVASTATINA COMPRIMIDO 40 MG"),
    "med-c00a54cde171c76d": ("18458", "ANLODIPINO (BESILATO) COMPRIMIDO 5 MG"),
}
BRT = ZoneInfo("America/Sao_Paulo")


def load_snapshot(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    snapshot: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    if not all(key in snapshot for key in ("fetched_at_utc", "sources", "ubs_stock", "locations")):
        raise ValueError("Snapshot InfoSaúde incompleto")
    return snapshot


def _timestamp(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value.astimezone(UTC)
    if isinstance(value, int | float) and value > 1_000_000_000_000:
        return datetime.fromtimestamp(value / 1000, UTC)
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value).astimezone(UTC)
        except ValueError:
            return None
    return None


def _stamp(value: Any) -> str:
    date = _timestamp(value)
    return date.astimezone(BRT).strftime("%d/%m/%Y %H:%M BRT") if date else "data não informada"


def _cnes(value: Any) -> str:
    return str(value or "").strip().zfill(7)


def _address(unit: dict[str, Any]) -> str:
    parts = [unit.get("logradouro"), unit.get("numero"), unit.get("complement"), unit.get("bairro")]
    return ", ".join(str(part).strip() for part in parts if part and str(part).strip())


def _map_url(unit: dict[str, Any]) -> str | None:
    latitude, longitude = unit.get("latitude"), unit.get("longitude")
    if not latitude or not longitude:
        return None
    try:
        lat, lon = float(latitude), float(longitude)
    except (TypeError, ValueError):
        return None
    if not (-16.2 <= lat <= -15.3 and -48.4 <= lon <= -47.2):
        return None
    return "https://www.google.com/maps/search/?" + urlencode({"api": "1", "query": f"{lat},{lon}"})


def _unit_line(row: dict[str, Any], unit: dict[str, Any] | None) -> str:
    name = str(unit.get("nome_fanta") if unit else row["i_desc_local_estoque"])
    region = str(row.get("i_desc_radf") or "")
    label = f"- {name} ({region}, CNES {_cnes(row.get('cnes'))})"
    if unit:
        address = _address(unit)
        if address:
            label += f" — {address}"
        map_url = _map_url(unit)
        if map_url:
            label += f" — mapa: {map_url}"
    return label


def _stock_reply(question: str, release: Release, snapshot: dict[str, Any]) -> str:
    match = match_medicine(question, release)
    if match.status != "matched":
        return match.message
    assert match.medicine is not None
    medicine = match.medicine
    product = PRODUCTS.get(medicine["medicine_id"])
    if product is None:
        return "Esta apresentação ainda não tem código UBS validado para consulta de estoque."
    code, description = product
    rows = [
        row
        for row in snapshot["ubs_stock"]
        if str(row.get("i_cod_produto")) == code
        and normalize(str(row.get("i_desc_produto", ""))) == normalize(description)
    ]
    if not rows:
        return "Não há registro validado desse produto no snapshot UBS consultado."
    regions = {normalize(str(row.get("i_desc_radf", ""))) for row in rows}
    query = normalize(question)
    selected = sorted(
        (region for region in regions if len(region) > 3 and region in query), key=len
    )
    if selected:
        region = selected[-1]
        rows = [row for row in rows if normalize(str(row.get("i_desc_radf", ""))) == region]
    dated = [row for row in rows if _timestamp(row.get("data_extracao")) is not None]
    dates = [stamp for row in dated if (stamp := _timestamp(row["data_extracao"]))]
    latest = max(dates) if dates else None
    if latest is None:
        return "O painel não informa data de extração para esse produto; não posso afirmar estoque."
    positive = [
        row
        for row in dated
        if _timestamp(row["data_extracao"]) == latest
        and isinstance(row.get("i_qtd_rede"), int | float)
        and row["i_qtd_rede"] > 0
        and "FARMÁCIA" in str(row.get("i_desc_local_estoque", "")).upper()
    ]
    units = {_cnes(item.get("cnes")): item for item in snapshot["locations"]}
    positive.sort(
        key=lambda row: (str(row.get("i_desc_radf", "")), str(row["i_desc_local_estoque"]))
    )
    stale = datetime.now(UTC) - latest > timedelta(hours=48)
    scope = f" em {selected[-1].title()}" if selected else ""
    if not positive:
        summary = (
            f"Não há saldo positivo datado no painel UBS{scope} para {description} (código {code})."
        )
    else:
        summary = (
            f"O painel UBS registra saldo positivo para {description} (código {code}) "
            f"em {len(positive)} farmácias{scope}."
        )
    lines = [summary, f"Extração do painel: {_stamp(latest)}."]
    if stale:
        lines.append("A extração tem mais de 48 horas; confirme o estoque na unidade antes de ir.")
    else:
        lines.append("O saldo pode mudar após a extração; confirme na unidade antes de ir.")
    for row in positive[:5]:
        lines.append(_unit_line(row, units.get(_cnes(row.get("cnes")))))
    if len(positive) > 5:
        lines.append(f"Exibindo 5 de {len(positive)} farmácias com saldo positivo.")
    lines.append(f"Fonte: {snapshot['sources']['ubs']}")
    return "\n".join(lines)


def _location_reply(question: str, snapshot: dict[str, Any]) -> str:
    query = normalize(question)
    units = snapshot["locations"]
    selected = [
        unit
        for unit in units
        if any(
            len(part) > 3 and re.search(rf"(?<!\w){re.escape(part)}(?!\w)", query)
            for part in (
                normalize(str(unit.get("nome_fanta", ""))),
                normalize(str(unit.get("bairro", ""))),
            )
        )
    ]
    if not selected:
        return "Informe o nome da unidade ou a região para buscar o endereço."
    lines = [f"Localizei {len(selected)} unidade(s) no cadastro InfoSaúde-DF:"]
    for unit in selected[:5]:
        line = f"- {unit['nome_fanta']} (CNES {_cnes(unit.get('cnes'))})"
        address = _address(unit)
        if address:
            line += f" — {address}"
        map_url = _map_url(unit)
        if map_url:
            line += f" — mapa: {map_url}"
        lines.append(line)
    if len(selected) > 5:
        lines.append(f"Exibindo 5 de {len(selected)} unidades.")
    lines.append(f"Cadastro consultado em {_stamp(snapshot['fetched_at_utc'])}.")
    lines.append(f"Fonte: {snapshot['sources']['locations']}")
    return "\n".join(lines)


def live_reply(question: str, release: Release, snapshot: dict[str, Any] | None) -> str | None:
    query = normalize(question)
    stock_intent = query.startswith("tem ") or any(
        term in query
        for term in (
            "estoque",
            "disponivel",
            "disponibilidade",
            "tem hoje",
            "onde encontro",
            "onde tem",
            "qual farmacia tem",
            "quais farmacias tem",
            "qual farmacia possui",
            "quais farmacias possuem",
        )
    )
    location_intent = any(
        term in query for term in ("onde fica", "endereco", "localizacao", "mapa")
    )
    if not stock_intent and not location_intent:
        return None
    if snapshot is None:
        return (
            "Dados de estoque e localização ainda não sincronizados. "
            "Execute: uv run python app.py sync-live"
        )
    if stock_intent:
        return _stock_reply(question, release, snapshot)
    return _location_reply(question, snapshot)
