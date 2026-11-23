"""Normalização textual e correspondência exata de princípios ativos, doses e formas."""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from .release import ConsolidatedRelease


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKD", value.casefold())
    value = "".join(c for c in value if not unicodedata.combining(c))
    value = re.sub(r"(?<=\d)\s*(?=(?:mcg|mg|g|ml|meq|ui|u|l)\b|%)", " ", value)
    value = re.sub(r"\s*/\s*", "/", value)
    return " ".join(value.split())


def strength_core(value: str) -> str:
    """Separate a documented device/package/delivery-rate suffix, never chemical equivalence."""
    return re.sub(
        r"\s*\((?:sistema de aplicacao|apresentacoes? de|frasco|"
        r"ampola|caneta|liberacao de)\b[^)]*\)$",
        "",
        normalize(value),
    )


def _textual_presentation(value: str) -> str:
    """Ignore an optional article in the documented homeopathic descriptor."""
    return normalize(value).replace("conforme a farmacopeia", "conforme farmacopeia")


def _form_matches(query: str, form: str) -> bool:
    documented = _textual_presentation(form)
    requested = _textual_presentation(query)
    if documented in requested:
        return True
    if documented == "solucao injetavel":
        return bool(re.search(r"\binjetavel\b", requested))
    if documented.startswith("comprimido de liberacao "):
        return bool(re.search(r"\bcomprimido\b", requested))
    return False


def is_form_absent(item: dict[str, Any]) -> bool:
    """True only when the source declares neither form nor package/specification."""
    return item.get("form") == "-" and not item.get("package") and not item.get("specification")


def item_form_label(item: dict[str, Any]) -> str:
    """Best single label for matching and length comparison across v5-v10 schemas."""
    form = item.get("form")
    if form not in (None, "", "-"):
        return str(form)
    return str(item.get("package") or item.get("specification") or "-")


def item_form_display(item: dict[str, Any]) -> str:
    """Human-readable form/package label preserving legacy text when no package exists."""
    form = item.get("form")
    package = item.get("package")
    specification = item.get("specification")
    if form not in (None, "", "-"):
        return f"{form} ({package})" if package else str(form)
    if package:
        return str(package)
    if specification:
        return str(specification)
    return "forma não informada"


def item_name_matches(query: str, item: dict[str, Any]) -> bool:
    if name_matches(query, item["active_ingredient"]):
        return True
    return any(name_matches(query, alias) for alias in item.get("aliases") or ())


def _package_matches(query: str, package: str) -> bool:
    q_norm = re.sub(r"\s*-\s*", " ", normalize(query))
    p_norm = re.sub(r"\s*-\s*", " ", normalize(package))
    candidates = [p_norm]
    if " ou " in p_norm:
        candidates.extend(part.strip() for part in p_norm.split(" ou ") if part.strip())
    return any(re.search(r"(?<!\w)" + re.escape(cand) + r"(?!\w)", q_norm) for cand in candidates)


def _presentation_form_matches(query: str, item: dict[str, Any]) -> bool:
    if is_form_absent(item):
        return True
    form = item.get("form")
    package = item.get("package")
    specification = item.get("specification")
    if form not in (None, "", "-"):
        matched = (
            _form_matches(query, str(form))
            or any(_form_matches(query, lit) for lit in item.get("literal_forms") or ())
            or any(_form_matches(query, alt) for alt in item.get("form_alternatives") or ())
        )
        if not matched:
            return False
        if (
            package
            and item.get("strength") == "-"
            and re.fullmatch(r"\d+(?:,\d+)?\s*m?l", str(package), re.I)
        ):
            return _package_matches(query, str(package))
        return True
    if package:
        return _package_matches(query, str(package))
    if specification:
        return _textual_presentation(str(specification)) in _textual_presentation(query)
    return False


def _interleaved_association_matches(query: str, strength: str, name: str | None) -> bool:
    if not name or " + " not in normalize(name) or " + " not in normalize(strength):
        return False
    components = normalize(name).split(" + ")
    doses = normalize(strength).split(" + ")
    if len(components) != len(doses):
        return False
    pattern = (
        r"(?<!\w)"
        + r"\s*\+\s*".join(
            re.escape(component) + r"\s+" + re.escape(dose)
            for component, dose in zip(components, doses, strict=True)
        )
        + r"(?![\w/,])"
    )
    return bool(re.search(pattern, query))


def strength_matches(query: str, strength: str, name: str | None = None) -> bool:
    stored = normalize(strength)
    core = strength_core(stored)
    if stored.startswith("de ") and " frasco" in stored:
        core = stored.split(" frasco", 1)[0]
    elif stored.startswith("bolsa ou frasco "):
        volume = re.search(r"\b\d+(?:[.,]\d+)?\s*ml\b", stored)
        core = volume.group() if volume else core
    comparison_query = _textual_presentation(query)
    comparison_core = _textual_presentation(core)
    literal = re.search(
        r"(?<![\w.,/])" + re.escape(comparison_core) + r"(?![\w./]|,\d)",
        comparison_query,
    )
    # Parentheses in a natural question may group a documented strength without
    # changing its units, alternatives or ingredient order.
    flat_query = _textual_presentation(re.sub(r"[()]", " ", query))
    flat_core = _textual_presentation(re.sub(r"[()]", " ", core))
    grouped = re.search(r"(?<![\w.,/])" + re.escape(flat_core) + r"(?![\w./]|,\d)", flat_query)
    if not (literal or grouped or _interleaved_association_matches(query, strength, name)):
        return False
    requested_packages = set(re.findall(r"\b(?:bolsa|frasco|ampola|seringa)\b", query))
    stored_packages = set(re.findall(r"\b(?:bolsa|frasco|ampola|seringa)\b", stored))
    if stored_packages and requested_packages - stored_packages:
        return False
    if "sistema fechado" in query and "sistema fechado" not in stored:
        return False
    requested_device = re.search(r"sistema de aplicacao\s+(\d+(?:[.,]\d+)?)\s*ml", query)
    if requested_device:
        stored_device = re.search(r"sistema de aplicacao\s+(\d+(?:[.,]\d+)?)\s*ml", stored)
        if not stored_device or requested_device.group(1) != stored_device.group(1):
            return False
    return True


def name_suggestion(question: str, catalog: list[dict[str, Any]]) -> tuple[str, str] | None:
    """Suggest a unique one-character typo; never silently select a medicine."""
    query = normalize(question)
    if any(item_name_matches(query, m) for m in catalog):
        return None
    names: dict[str, str] = {}
    for m in catalog:
        for candidate in (m["active_ingredient"], *(m.get("aliases") or ())):
            norm = normalize(candidate)
            if re.fullmatch(r"[a-z]{6,}", norm):
                names.setdefault(norm, candidate)
    suggestions = set()
    for token in re.findall(r"\b[a-z]{6,}\b", query):
        for name in names:
            if abs(len(token) - len(name)) > 1:
                continue
            if len(token) == len(name):
                different = [i for i, (a, b) in enumerate(zip(token, name, strict=True)) if a != b]
                close = len(different) == 1 or (
                    len(different) == 2
                    and different[1] == different[0] + 1
                    and token[different[0]] == name[different[1]]
                    and token[different[1]] == name[different[0]]
                )
            else:
                shorter, longer = sorted((token, name), key=len)
                close = any(longer[:i] + longer[i + 1 :] == shorter for i in range(len(longer)))
            if close:
                corrected = re.sub(r"\b" + re.escape(token) + r"\b", name, query)
                suggestions.add((names[name], corrected))
    return next(iter(suggestions)) if len(suggestions) == 1 else None


def _matching_supplies(
    query: str,
    release: ConsolidatedRelease,
    source_filter: str | None,
) -> list[dict[str, Any]]:
    supplies = [
        o
        for o in release.occurrences
        if o["item_type"] == "supply"
        and normalize(o["active_ingredient"]) in query
        and (o["strength"] == "-" or normalize(o["strength"]) in query)
    ]
    if source_filter:
        supplies = [o for o in supplies if o["source"]["source_id"] == source_filter]
    if len(supplies) > 1:
        narrowed = [o for o in supplies if _presentation_form_matches(query, o)]
        if narrowed:
            supplies = narrowed
    return supplies


def name_matches(query: str, name: str) -> bool:
    """Explicit ingredient alias; never infers therapeutic equivalence."""
    normalized = normalize(name)
    aliases = [normalized]
    if normalized in {"cloridrato de metformina", "metformina (cloridrato)"}:
        aliases.append("metformina")
    if any(re.search(r"(?<!\w)" + re.escape(alias) + r"(?!\w)", query) for alias in aliases):
        return True
    if " + " in normalized:
        components = normalized.split(" + ")
        pattern = r"(?<!\w)" + re.escape(components[0])
        for component in components[1:]:
            pattern += r"\s*(?:\([^)]*\)\s*)?\+\s*" + re.escape(component)
        if re.search(pattern + r"(?!\w)", query):
            return True
        dose = r"\s+\d+(?:[.,]\d+)?\s*(?:mg|mcg|g|ui)(?:/(?:ml|g))?"
        interleaved = r"(?<!\w)" + r"\s*\+\s*".join(
            re.escape(component) + dose for component in components
        )
        return bool(re.search(interleaved + r"(?!\w)", query))
    return False


def ingredient_key(name: str) -> str:
    normalized = normalize(name)
    return "cloridrato de metformina" if normalized == "metformina (cloridrato)" else normalized
