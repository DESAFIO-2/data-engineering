"""Progressive catalog exploration without requiring a complete presentation."""

from __future__ import annotations

import re
from typing import Any

from .consolidated import (
    ConsolidatedRelease,
    ingredient_key,
    name_matches,
    normalize,
    strength_core,
    strength_matches,
)
from .retrieval import FORM_TERMS, _form_matches


def _browse_base(name: str) -> str:
    return " ".join(
        word
        for word in re.findall(r"[a-z]+|\+", normalize(name))
        if word
        not in {
            "de",
            "do",
            "da",
            "cloridrato",
            "besilato",
            "sulfato",
            "fosfato",
            "sodico",
            "sodica",
            "potassico",
            "potassica",
        }
    )


def catalog_name_matches(query: str, name: str) -> bool:
    if name_matches(query, name):
        return True
    base = _browse_base(name)
    # This only finds options; each salt/form remains a separate documented item.
    return bool(
        base
        and "+" not in base
        and re.search(
            r"(?<!\w)" + re.escape(base) + r"(?!\w)",
            query,
        )
    )


def presentation_query(medicine: dict[str, Any]) -> str:
    return " ".join(
        str(medicine.get(field) or "")
        for field in (
            "active_ingredient",
            "strength",
            "form",
            "release_characteristic",
        )
        if medicine.get(field) not in {"-", None, ""}
    ).strip()


def candidates(question: str, release: ConsolidatedRelease) -> list[dict[str, Any]]:
    query = normalize(question)
    source = next(
        (
            sid
            for term, sid in (
                ("reme", "F03"),
                ("farmacia popular", "F04"),
                ("rename", "F01"),
                ("f03", "F03"),
                ("f04", "F04"),
                ("f01", "F01"),
            )
            if re.search(r"\b" + re.escape(term) + r"\b", query)
        ),
        None,
    )
    names = [
        m
        for m in release.catalog
        if catalog_name_matches(query, m["active_ingredient"])
        and (source is None or source in m["source_ids"])
    ]
    if not names:
        return []
    identities = {_browse_base(m["active_ingredient"]) for m in names}
    longest = max(identities, key=len)
    if any(identity not in longest for identity in identities):
        return []
    names = [m for m in names if _browse_base(m["active_ingredient"]) == longest]
    exact = {
        ingredient_key(m["active_ingredient"])
        for m in names
        if re.search(
            r"(?<!\w)" + re.escape(normalize(m["active_ingredient"])) + r"(?!\w)",
            query,
        )
    }
    if exact:
        names = [m for m in names if ingredient_key(m["active_ingredient"]) in exact]
    if re.search(r"\d+(?:[.,]\d+)?\s*(mg|mcg|g|ui|ml|%)(?!\w)", query):
        names = [
            m for m in names if m["strength"] != "-" and strength_matches(query, m["strength"])
        ]
    forms = [
        form for form in FORM_TERMS if re.search(r"\b" + re.escape(normalize(form)) + r"\b", query)
    ]
    if forms:
        names = [
            m
            for m in names
            if m["form"] == "-" or any(_form_matches(m["form"], form) for form in forms)
        ]
    if "prolongada" in query:
        names = [m for m in names if m.get("release_characteristic")]
    elif "convencional" in query or "imediata" in query:
        names = [m for m in names if not m.get("release_characteristic")]
    grouped: dict[tuple[str, ...], dict[str, Any]] = {}
    for medicine in names:
        key = (
            ingredient_key(medicine["active_ingredient"]),
            normalize(medicine["strength"]),
            normalize(medicine["form"]),
            normalize(medicine.get("release_characteristic") or ""),
        )
        if key not in grouped:
            grouped[key] = {**medicine, "medicine_ids": [], "source_ids": []}
        item = grouped[key]
        item["medicine_ids"].append(medicine["medicine_id"])
        item["source_ids"] = sorted(
            set(item["source_ids"]) | ({source} if source else set(medicine["source_ids"]))
        )
    return sorted(
        grouped.values(),
        key=lambda m: (
            _strength_order(m["strength"]),
            m["form"] == "-",
            m["form"],
            m.get("release_characteristic") or "",
            m["medicine_id"],
        ),
    )


def options_reply(
    items: list[dict[str, Any]], release: ConsolidatedRelease, *, stock: bool = False
) -> str:
    lines = [f"Encontrei {len(items)} apresentação(ões) com as informações que você passou:"]
    for index, item in enumerate(items, 1):
        form = item["form"] if item["form"] != "-" else "forma não informada na fonte"
        characteristic = (
            f"; {item['release_characteristic']}" if item.get("release_characteristic") else ""
        )
        evidence = [
            e
            for e in release.evidence
            if e["medicine_id"] in item["medicine_ids"]
            and e["source"]["source_id"] in item["source_ids"]
        ]
        refs = sorted(
            {
                f"{e['source']['source_id']} ({e['source']['version']}), "
                f"página {e['source']['page']} [{e['evidence_id']}]"
                for e in evidence
            }
        )
        lines.append(
            f"{index}. {item['active_ingredient']} — {item['strength']}; {form}{characteristic} "
            f"({'; '.join(refs)})."
        )
    if len(items) > 1:
        lines.append(
            "Qual dessas apresentações você procura? Pode responder com o número, "
            "a concentração ou a forma que souber, olhando a embalagem ou receita."
        )
    else:
        lines.append("Você não precisa repetir esses detalhes.")
    lines.append(
        "Em qual região você quer procurar nas farmácias/UBS?"
        if not stock
        else "Vou manter a região informada para consultar o estoque após a escolha."
    )
    lines.append(
        "Essas são apresentações documentadas, não alternativas terapêuticas "
        "nem confirmação de estoque."
    )
    return "\n".join(lines)


def _strength_order(strength: str) -> float:
    number = re.search(r"\d+(?:[.,]\d+)?", strength)
    return float(number[0].replace(",", ".")) if number else 0


def stock_candidates(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Collapse undocumented duplicates, never a distinct release characteristic."""
    known = [m for m in items if m["form"] != "-"]
    return [
        m
        for m in items
        if m["form"] != "-"
        or not any(
            strength_core(k["strength"]) == strength_core(m["strength"])
            and k.get("release_characteristic") == m.get("release_characteristic")
            for k in known
        )
    ]
