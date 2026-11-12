"""On-demand public UBS/CEAF queries with conservative product identity checks."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from ingestion.infosaude_live import CEAF, UBS, InfoSaudeLiveClient

from .config import ROOT
from .consolidated import ConsolidatedRelease, ingredient_key, normalize, strength_core
from .live import _stamp, _timestamp, load_snapshot, stock_reply_for_product


def source_codes(medicine: dict[str, Any], release: ConsolidatedRelease) -> set[str]:
    ids = set(medicine.get("medicine_ids", [medicine["medicine_id"]]))
    return {
        str(o["source_code"])
        for o in release.occurrences
        if o.get("medicine_id") in ids
        and o["source"]["source_id"] == "F03"
        and o.get("source_code")
    }


def compatible_product(
    medicine: dict[str, Any], code: str, description: str, release: ConsolidatedRelease
) -> bool:
    query = normalize(description)
    if medicine["form"] == "-":
        return False
    codes = source_codes(medicine, release)
    if codes and code not in codes:
        return False
    # Compare full ingredient prefix. An association never becomes monotherapy.
    prefix = re.split(
        r"\b(?:comprimido|capsula|solucao|suspensao|po|creme|pomada|gel)\b|\d", query
    )[0]

    def tokens(value: str) -> set[str]:
        return set(re.findall(r"[a-z]+", value)) - {"de", "do", "da"}

    if tokens(prefix) != tokens(ingredient_key(medicine["active_ingredient"])):
        return False
    core = strength_core(medicine["strength"])
    if not re.search(r"(?<![\w.,/])" + re.escape(core) + r"(?![\w.,/])", query):
        return False
    if normalize(medicine["form"]) not in query:
        return False
    modified = any(term in query for term in ("prolongada", "modificada", "retard"))
    if modified != bool(medicine.get("release_characteristic")):
        return False
    device = re.search(
        r"sistema de aplicacao\s+(\d+(?:[.,]\d+)?)\s*ml", normalize(medicine["strength"])
    )
    if device and not re.search(r"(?<![\d.,])" + re.escape(device.group(1)) + r"\s*ml\b", query):
        return False
    return True


def _term(medicine: dict[str, Any]) -> str:
    salts = {
        "cloridrato",
        "besilato",
        "sulfato",
        "fosfato",
        "carbonato",
        "nitrato",
        "acetato",
        "bromidrato",
        "sodico",
        "sodica",
        "de",
        "do",
        "da",
    }
    tokens = [
        t for t in re.findall(r"[a-z]+", normalize(medicine["active_ingredient"])) if t not in salts
    ]
    return max(tokens, key=len).upper() if tokens else str(medicine["active_ingredient"]).upper()


def _cache_path(medicine: dict[str, Any]) -> Path:
    # Only trusted catalog IDs are used; no user question/region/CEP is persisted.
    return ROOT / "data/gold/stock_queries" / (str(medicine["medicine_id"]) + ".json")


def _ceaf_reply(
    rows: list[dict[str, Any]], region: str, fetched: str | None, *, cached: bool
) -> str:
    lines = ["Farmácias especializadas (CEAF), consulta separada das UBS:"]
    matching = [r for r in rows if normalize(str(r.get("unidade", ""))) == normalize(region)]
    if matching:
        shown = matching
    else:
        shown = rows
        lines.append(
            f"Não há unidade CEAF identificada como {region} nesses registros. "
            "As unidades abaixo não são UBS dessa região "
            "e não indicam onde você será atendido."
        )
    for row in shown:
        lines.append(
            f"- {row['unidade']}: o painel informa {row['disp_estoque']} "
            f"(código {row['cod_produto2']})."
        )
    dates = [r.get("ultima_atualizacao") for r in shown if r.get("ultima_atualizacao")]
    lines.append(
        "Atualização informada pelo painel: " + "; ".join(_stamp(d) for d in dates) + "."
        if dates
        else "O painel não informa a data dessa posição; não posso confirmar estoque de hoje."
    )
    lines.append(
        f"{'Snapshot anterior coletado' if cached else 'API pública consultada'} "
        f"em {_stamp(fetched)}."
    )
    timestamps = [stamp for value in dates if (stamp := _timestamp(value)) is not None]
    if timestamps and datetime.now(UTC) - max(timestamps) > timedelta(hours=48):
        lines.append("A posição do painel tem mais de 48 horas; confirme com a farmácia.")
    lines.append("Confirme com a farmácia antes de se deslocar. Fonte: " + CEAF.source_url)
    return "\n".join(lines)


def lookup_stock(
    medicine: dict[str, Any],
    release: ConsolidatedRelease,
    region: str,
    products: dict[str, tuple[str, str]] | None = None,
) -> str:
    client = InfoSaudeLiveClient()
    now = datetime.now(UTC).isoformat()
    result: dict[str, Any] = {
        "fetched_at_utc": now,
        "sources": {"ubs": UBS.source_url, "ceaf": CEAF.source_url},
        "locations": [],
        "ubs_stock": [],
        "ceaf_stock": [],
    }
    warnings = []
    failed = set()
    try:
        previous = load_snapshot(ROOT / "data/gold/infosaude_live_snapshot.json")
        result["locations"] = previous.get("locations", []) if previous else []
    except (ValueError, OSError):
        previous = None
    cached_result: dict[str, Any] = {}
    path = _cache_path(medicine)
    if path.exists():
        try:
            cached_result = json.loads(path.read_text(encoding="utf-8"))
            if cached_result.get("release_fingerprint") != release.fingerprint:
                cached_result = {}
        except (OSError, ValueError):
            pass
    if not cached_result and previous:
        ubs_rows = [
            r
            for r in previous.get("ubs_stock", [])
            if compatible_product(
                medicine, str(r.get("i_cod_produto", "")), str(r.get("i_desc_produto", "")), release
            )
        ]
        pairs = {(str(r["i_cod_produto"]), str(r["i_desc_produto"])) for r in ubs_rows}
        cached_result = {
            "ubs_stock": ubs_rows,
            "ubs_products": [
                {"i_cod_produto": code, "i_desc_produto": desc} for code, desc in sorted(pairs)
            ],
            "ceaf_stock": [
                r
                for r in previous.get("ceaf_stock", [])
                if compatible_product(
                    medicine,
                    str(r.get("cod_produto2", "")),
                    str(r.get("desc_produto", "")),
                    release,
                )
            ],
            "ubs_fetched_at": previous["fetched_at_utc"],
            "ceaf_fetched_at": previous["fetched_at_utc"],
        }
    catalog: list[dict[str, Any]] = []
    try:
        catalog = client.discover_ubs_products(_term(medicine))
        matching = [
            r
            for r in catalog
            if compatible_product(
                medicine, str(r["i_cod_produto"]), str(r["i_desc_produto"]), release
            )
        ]
        # Reviewed explicit links remain usable when catalog labels are abbreviated.
        explicit = (products or {}).get(medicine["medicine_id"])
        if explicit:
            matching = [
                r for r in catalog if (str(r["i_cod_produto"]), r["i_desc_produto"]) == explicit
            ]
        result["ubs_products"] = matching
        if len(matching) == 1:
            result["ubs_stock"] = client.fetch(
                UBS, limit=5000, product_codes=(str(matching[0]["i_cod_produto"]),)
            )
            if any(
                str(r.get("i_cod_produto")) != str(matching[0]["i_cod_produto"])
                or r.get("i_desc_produto") != matching[0]["i_desc_produto"]
                for r in result["ubs_stock"]
            ):
                raise ValueError("Resposta UBS diverge do produto validado")
        elif len(matching) > 1:
            warnings.append(
                "Mais de um código UBS corresponde aos dados informados; "
                "não escolhi um automaticamente: "
                + "; ".join(f"{r['i_cod_produto']}: {r['i_desc_produto']}" for r in matching)
            )
        else:
            warnings.append(
                "UBS: não encontrei vínculo seguro no catálogo consultado para essa apresentação; "
                "isso não significa falta de estoque."
            )
    except Exception as exc:
        failed.add("ubs")
        warnings.append(f"Consulta UBS indisponível ({type(exc).__name__}); sem confirmação atual.")
    try:
        rows = client.fetch(CEAF, limit=2000, product_name=_term(medicine))
        result["ceaf_stock"] = [
            r
            for r in rows
            if compatible_product(medicine, str(r["cod_produto2"]), str(r["desc_produto"]), release)
        ]
        if len({str(r["cod_produto2"]) for r in result["ceaf_stock"]}) > 1:
            warnings.append(
                "CEAF: mais de um código corresponde à descrição; "
                "preciso distinguir os produtos antes de informar estoque."
            )
            result["ceaf_stock"] = []
    except Exception as exc:
        failed.add("ceaf")
        warnings.append(
            f"Consulta CEAF indisponível ({type(exc).__name__}); sem confirmação atual."
        )
    # Failed responses never replace previously successful data for that channel.
    result["release_fingerprint"] = release.fingerprint
    for channel in ("ubs", "ceaf"):
        if channel in failed:
            result[channel + "_stock"] = cached_result.get(channel + "_stock", [])
            if channel == "ubs":
                result["ubs_products"] = cached_result.get("ubs_products", [])
            result[channel + "_fetched_at"] = cached_result.get(channel + "_fetched_at")
        else:
            result[channel + "_fetched_at"] = now
    if len(failed) < 2:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(result, ensure_ascii=False) + "\n", encoding="utf-8")
        temporary.replace(path)
    lines = [
        f"Consultando {medicine['active_ingredient']} {medicine['strength']} "
        f"({medicine['form']}) para {region}.",
        *warnings,
    ]
    rows = result["ubs_stock"]
    if rows:
        stamp = result.get("ubs_fetched_at")
        lines.append(
            f"UBS — {'snapshot anterior' if 'ubs' in failed else 'API consultada'} "
            f"em {_stamp(stamp)}."
        )
        products_found = result.get("ubs_products", [])
        if len(products_found) == 1:
            row = products_found[0]
            lines.append(f"Apresentação conferida no catálogo UBS: código {row['i_cod_produto']}.")
            regional = [
                r for r in rows if normalize(str(r.get("i_desc_radf", ""))) == normalize(region)
            ]
            if regional and not any(r.get("data_extracao") for r in regional):
                numeric = [
                    r["i_qtd_rede"]
                    for r in regional
                    if isinstance(r.get("i_qtd_rede"), (int, float))
                ]
                lines.append(
                    f"UBS de {region}: {len(regional)} registros sem data de extração. "
                    + (
                        "Os saldos informados são zero, mas não confirmam a posição de hoje."
                        if numeric
                        and len(numeric) == len(regional)
                        and all(n == 0 for n in numeric)
                        else "Não posso confirmar disponibilidade atual a partir desses registros."
                    )
                )
                lines.append("Fonte UBS: " + UBS.source_url)
            else:
                lines.append(
                    stock_reply_for_product(
                        "", result, (str(row["i_cod_produto"]), row["i_desc_produto"]), region
                    )
                )
    elif "ubs" not in failed and result.get("ubs_products"):
        lines.append(
            f"UBS: a consulta não retornou registros para o código validado; "
            f"isso não comprova saldo zero em {region}. Fonte: {UBS.source_url}"
        )
    if result["ceaf_stock"]:
        lines.append(
            _ceaf_reply(
                result["ceaf_stock"],
                region,
                result.get("ceaf_fetched_at"),
                cached="ceaf" in failed,
            )
        )
    elif "ceaf" not in failed:
        lines.append("CEAF: nenhuma correspondência segura nesse painel. Fonte: " + CEAF.source_url)
    return "\n".join(lines)
