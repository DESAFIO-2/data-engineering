"""Deterministic, additive normalization for consolidated corpus releases (v10).

Every function here is pure: it receives the literal value published in the source
release and returns derived values plus the names of the rules that fired. Literal
fields are never modified by this module; callers store the result under
``occurrence["normalized"]``. No pharmaceutical equivalence is inferred: when the
source does not declare a value, the canonical value is ``None``.
"""

from __future__ import annotations

import json
import re
import unicodedata
from collections import Counter, defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path
from typing import Any

NORMALIZATION_SCHEMA = "consolidated-normalization-v1"
VOCAB_FILES = ("units.json", "forms.json", "channels.json", "ingredients.json")

_NBSP = "\u00a0"
_ABSENT = {"", "-"}


# --------------------------------------------------------------------------- utils


def fold(value: str) -> str:
    """Case/accent/spacing fold used only for comparison keys, never for display."""
    value = unicodedata.normalize("NFKD", value.replace(_NBSP, " ").casefold())
    value = "".join(c for c in value if not unicodedata.combining(c))
    value = re.sub(r"(?<=\d)\s*(?=(?:mcg|mg|g|ml|meq|ui|u|l)\b|%)", " ", value)
    value = re.sub(r"\s*/\s*", "/", value)
    value = re.sub(r"\s*\+\s*", " + ", value)
    return " ".join(value.split())


def _clean_spaces(value: str) -> str:
    return " ".join(value.replace(_NBSP, " ").split())


@dataclass
class RuleTrace:
    """Collects the rules that changed a value (for audit and dry-run statistics)."""

    applied: list[str] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)

    def hit(self, rule: str) -> None:
        if rule not in self.applied:
            self.applied.append(rule)

    def flag(self, name: str) -> None:
        if name not in self.flags:
            self.flags.append(name)


# --------------------------------------------------------------------------- vocab


@dataclass(frozen=True)
class Vocabulary:
    units: dict[str, Any]
    forms: dict[str, Any]
    channels: dict[str, Any]
    ingredients: dict[str, Any]

    @property
    def ingredient_map(self) -> dict[str, str]:
        return {row["variant"]: row["canonical"] for row in self.ingredients.get("mappings", [])}


def load_vocabulary(directory: Path) -> Vocabulary:
    data = {
        name: json.loads((directory / name).read_text(encoding="utf-8")) for name in VOCAB_FILES
    }
    return Vocabulary(
        units=data["units.json"],
        forms=data["forms.json"],
        channels=data["channels.json"],
        ingredients=data["ingredients.json"],
    )


def vocabulary_bundle(directory: Path) -> dict[str, Any]:
    """Self-contained bundle (content + SHA-256 per file) embedded in the release."""
    files: dict[str, Any] = {}
    for name in VOCAB_FILES:
        raw = (directory / name).read_bytes()
        files[name] = {"sha256": sha256(raw).hexdigest(), "content": json.loads(raw)}
    return {"schema_version": NORMALIZATION_SCHEMA, "files": files}


def check_bundle(bundle: dict[str, Any], directory: Path) -> list[str]:
    """Return the vocabulary files whose content diverges from the embedded bundle."""
    current = vocabulary_bundle(directory)["files"]
    return sorted(
        name
        for name in VOCAB_FILES
        if bundle.get("files", {}).get(name, {}).get("sha256") != current[name]["sha256"]
    )


# ---------------------------------------------------------------------- ingredient


_SALT_PAREN_RE = re.compile(r"^(?P<base>[^()]+?)\s*\((?P<salt>[^()]+)\)$")


def _ingredient_surface(value: str, trace: RuleTrace | None = None) -> str:
    cleaned = _clean_spaces(value)
    spaced = re.sub(r"\s*\+\s*", " + ", cleaned)
    if trace is not None and spaced != value:
        trace.hit("ingredient_spacing")
    return spaced


def _accent_count(value: str) -> int:
    return sum(1 for c in unicodedata.normalize("NFD", value) if unicodedata.combining(c))


def build_ingredient_map(
    names: Iterable[tuple[str, str]],
) -> list[dict[str, Any]]:
    """Derive variant -> canonical spelling from (name, source_id) pairs.

    Variants are grouped by the folded key. ``X (sal)`` joins the group of
    ``sal de X`` or ``X sal`` only when that spelling exists in the corpus.
    Preference: spelling used in F01 (RENAME/DCB), then more accents, then
    lower-case, then frequency, then lexicographic order.
    """
    counts: Counter[str] = Counter()
    sources: dict[str, set[str]] = defaultdict(set)
    for name, source_id in names:
        surface = _ingredient_surface(name)
        counts[surface] += 1
        sources[surface].add(source_id)

    by_key: dict[str, set[str]] = defaultdict(set)
    for surface in counts:
        by_key[fold(surface)].add(surface)

    reasons: dict[str, str] = {}
    for surface in list(counts):
        match = _SALT_PAREN_RE.match(surface)
        if not match:
            continue
        base, salt = match["base"].strip(), match["salt"].strip()
        for candidate in (f"{salt} de {base}", f"{base} {salt}"):
            target = fold(candidate)
            if target in by_key and target != fold(surface):
                by_key[target].add(surface)
                by_key[fold(surface)].discard(surface)
                reasons[surface] = "salt_order"
                break

    mappings: list[dict[str, Any]] = []
    for key in sorted(by_key):
        group = by_key[key]
        if len(group) < 2:
            continue
        canonical = sorted(
            group,
            key=lambda s: (
                0 if "F01" in sources[s] else 1,
                -_accent_count(s),
                0 if s == s.lower() else 1,
                -counts[s],
                s,
            ),
        )[0]
        for variant in sorted(group - {canonical}):
            reason = reasons.get(variant)
            if reason is None:
                if fold(variant) == fold(canonical) and variant.casefold() == canonical.casefold():
                    reason = "case"
                elif _accent_count(variant) < _accent_count(canonical):
                    reason = "accent"
                else:
                    reason = "spelling"
            mappings.append(
                {
                    "variant": variant,
                    "canonical": canonical,
                    "reason": reason,
                    "variant_sources": sorted(sources[variant]),
                    "canonical_sources": sorted(sources[canonical]),
                    "occurrences": counts[variant],
                }
            )
    return mappings


def canonical_ingredient(value: str, vocab: Vocabulary, trace: RuleTrace) -> str:
    surface = _ingredient_surface(value, trace)
    mapped = vocab.ingredient_map.get(surface)
    if mapped is not None and mapped != surface:
        trace.hit("ingredient_vocab")
        return mapped
    return surface


# ------------------------------------------------------------------------ strength


_NUM = r"\d+(?:[.,]\d+)*"
_UNIT_TOKEN_RE = re.compile(
    rf"(?<![\w,.])(?P<num>{_NUM})\s*(?P<unit>[A-Za-zµ]+)(?:\s*/\s*(?P<per>[A-Za-z]+))?(?![A-Za-z])"
)


def canonical_strength(value: str, vocab: Vocabulary, trace: RuleTrace) -> tuple[str | None, str]:
    """Return (canonical strength, kind) where kind is numeric|combination|textual|absent."""
    if value is None or value.strip() in _ABSENT:
        return None, "absent"
    units: dict[str, str] = vocab.units["units"]
    text = _clean_spaces(value)
    if text != value:
        trace.hit("strength_whitespace")

    repaired = re.sub(r"(\d)/\s*,(\d)", r"\1,\2", text)
    if repaired != text:
        trace.hit("strength_pdf_artifact_fix")
        trace.flag("needs_pdf_check")
        text = repaired

    def _unit(match: re.Match[str]) -> str:
        unit_raw, per_raw = match["unit"], match["per"]
        unit = units.get(unit_raw.lower())
        if unit is None:
            return match.group(0)
        out = f"{match['num']} {unit}"
        if per_raw:
            out += "/" + units.get(per_raw.lower(), per_raw)
        return out

    spaced = _UNIT_TOKEN_RE.sub(_unit, text)
    if spaced != text:
        trace.hit("strength_unit_canonical")
        text = spaced

    no_space_pct = re.sub(r"(\d)\s+%", r"\1%", text)
    if no_space_pct != text:
        trace.hit("strength_percent_spacing")
        text = no_space_pct

    if re.search(r"\d\.\d{1,2}(?!\d)", text):
        trace.flag("ambiguous_decimal_point")

    residue = _UNIT_TOKEN_RE.sub("", text)
    residue = re.sub(r"\d+(?:[.,]\d+)*%?|[+()/;,\s-]", " ", residue)
    words = [w for w in residue.split() if w.lower() not in {"de", "e", "ou", "a"}]
    if len(words) >= 2:
        kind = "textual"
    elif "+" in text:
        kind = "combination"
    else:
        kind = "numeric"
    return text, kind


# ---------------------------------------------------------------------------- form


def canonical_form(value: str, vocab: Vocabulary, trace: RuleTrace) -> dict[str, Any]:
    """Split a literal form into form / package / release / specification."""
    result: dict[str, Any] = {
        "form": None,
        "form_kind": "absent",
        "form_alternatives": [],
        "package": None,
        "specification": None,
        "form_release": None,
    }
    if value is None or value.strip() in _ABSENT:
        return result
    rules = vocab.forms
    text = _clean_spaces(value)
    low = text.lower()

    for pattern in rules["specification_patterns"]:
        if re.match(pattern, low):
            trace.hit("form_specification")
            result.update(form_kind="specification", specification=text)
            return result
    if low in rules["descriptor_forms"]:
        trace.hit("form_descriptor")
        result.update(form_kind="descriptor", specification=text)
        return result

    padded = f" {low} "
    for wrong, right in rules["spelling_fixes"].items():
        target = wrong if wrong.startswith(" ") else f" {wrong}"
        replacement = right if right.startswith(" ") else f" {right}"
        if target in padded:
            padded = padded.replace(target, replacement)
            trace.hit("form_spelling")
    for wrong, right in rules["release_insertions"].items():
        if f" {wrong} " in padded and f" {right} " not in padded:
            padded = padded.replace(f" {wrong} ", f" {right} ")
            trace.hit("form_release_preposition")
    low = padded.strip()

    if low in rules.get("volume_phrase_packages", {}):
        result["package"] = rules["volume_phrase_packages"][low]
        trace.hit("form_volume_to_package")
    if low in rules.get("canonical_synonyms", {}):
        low = rules["canonical_synonyms"][low]
        trace.hit("form_synonym")

    volume = re.match(r"^(?P<form>.+?)\s+(?P<vol>\d+(?:,\d+)?)\s*ml$", low)
    if volume:
        trace.hit("form_volume_to_package")
        result["package"] = f"{volume['vol']} mL"
        low = volume["form"]

    for pkg_suffix in rules.get("package_phrase_suffixes", []):
        if low.endswith(f" {pkg_suffix}") and len(low) > len(pkg_suffix) + 1:
            result["package"] = pkg_suffix
            low = low[: -(len(pkg_suffix) + 1)].strip()
            trace.hit("form_package_suffix")
            break

    suffix = re.match(r"^(?P<form>.+?)\s*\((?P<pkg>[^()]+)\)$", low)
    if suffix and suffix["pkg"] in rules["package_suffixes"]:
        trace.hit("form_package_suffix")
        result["package"] = suffix["pkg"]
        low = suffix["form"]

    alternatives = [low]
    for separator in rules["alternative_separators"]:
        alternatives = [part for alt in alternatives for part in alt.split(separator)]
    alternatives = [a.strip() for a in alternatives if a.strip()]

    package_terms = set(rules["package_only"]) | set(rules["package_suffixes"])
    if low in rules["package_only"] or (
        alternatives and all(a in package_terms for a in alternatives)
    ):
        trace.hit("form_package_only")
        result.update(form_kind="package_only", package=low)
        return result

    if len(alternatives) == 1:
        for pattern, release in rules["release_patterns"].items():
            if f" {pattern}" in f" {low}":
                low = _clean_spaces(f" {low} ".replace(f" {pattern} ", " "))
                result["form_release"] = release
                trace.hit("form_release_extracted")
                break
        result.update(form=low, form_kind="form")
    else:
        for pattern, release in rules["release_patterns"].items():
            if alternatives[-1].endswith(f" {pattern}"):
                stripped_last = alternatives[-1][: -(len(pattern) + 1)].strip()
                candidate_alts = [*alternatives[:-1], stripped_last]
                if stripped_last and len(set(candidate_alts)) == len(candidate_alts):
                    alternatives = candidate_alts
                    result["form_release"] = release
                    trace.hit("form_release_extracted")
                break
        trace.hit("form_alternatives")
        result.update(
            form=" ou ".join(alternatives),
            form_kind="alternatives",
            form_alternatives=alternatives,
        )
    return result


_RELEASE_RATE_RE = re.compile(r"^liberação de .+?/24\s*h$", re.IGNORECASE)


def canonical_release(
    literal: str | None, form_release: str | None, trace: RuleTrace
) -> tuple[str | None, str | None]:
    lit = _clean_spaces(literal).lower() if literal else None
    if lit and _RELEASE_RATE_RE.match(lit):
        trace.hit("release_rate_to_strength_note")
        trace.flag("release_rate_in_strength")
        return form_release, lit
    if lit and form_release and lit != form_release:
        trace.flag("release_conflict_literal_vs_form")
        return lit, None
    if lit:
        if lit != literal:
            trace.hit("release_whitespace_case")
        return lit, None
    return form_release, None


# ----------------------------------------------------------------------------- ATC


_ATC_WHO = re.compile(r"^[A-Z]\d{2}[A-Z]{2}\d{2}$")
_ATC_HERBAL = re.compile(r"^[A-Z]\d{2}[A-Z]{2}\d{4}$")
_ATC_PARTIAL = re.compile(r"^[A-Z](?:\d{2}(?:[A-Z](?:[A-Z])?)?)?$")


def parse_atc(value: str | None, trace: RuleTrace) -> dict[str, Any]:
    result: dict[str, Any] = {
        "codes": [],
        "primary": None,
        "kind": None,
        "levels": [],
        "note": None,
    }
    if not value or not value.strip():
        return result
    text = _clean_spaces(value)
    if text.lower().endswith(" continua"):
        trace.hit("atc_strip_continua")
        trace.flag("atc_parser_artifact")
        text = text[: -len(" continua")].strip()
    footnote = re.match(r"^(?P<code>.+?)\((?P<note>\d+)\)$", text)
    if footnote:
        trace.hit("atc_footnote_split")
        result["note"] = f"nota ({footnote['note']})"
        text = footnote["code"].strip()
    joined = re.sub(r"(?<=[A-Z]{2})\s+(?=\d{4}\b)", "", text)
    if joined != text:
        trace.hit("atc_join_space")
        text = joined
    if text.upper() == "NC":
        result.update(kind="not_classified", note=result["note"] or "NC")
        return result
    parts = [p.strip() for p in re.split(r";|\s+e\s+", text) if p.strip()]
    if len(parts) > 1:
        trace.hit("atc_multiple_split")
    kinds: list[str] = []
    levels: list[int | None] = []
    for code in parts:
        if _ATC_WHO.match(code):
            kinds.append("who")
            levels.append(5)
        elif _ATC_HERBAL.match(code):
            kinds.append("herbal")
            levels.append(5)
        elif _ATC_PARTIAL.match(code):
            kinds.append("partial")
            levels.append({1: 1, 3: 2, 4: 3, 5: 4}[len(code)])
        else:
            kinds.append("invalid")
            levels.append(None)
            trace.flag("atc_invalid")
    result["codes"] = parts
    result["primary"] = parts[0] if parts else None
    result["levels"] = levels
    result["kind"] = "multiple" if len(parts) > 1 else (kinds[0] if kinds else None)
    return result


# -------------------------------------------------------------------------- channel


_NOTE_MARK_RE = re.compile(r"(?:(?<=\s)|(?<=\*))\*\s?(?=[A-ZÀ-Ú])")


def parse_channel(value: str | None, vocab: Vocabulary, trace: RuleTrace) -> dict[str, Any]:
    result: dict[str, Any] = {"text": None, "codes": [], "note_codes": [], "notes": [], "flags": []}
    if not value or not value.strip():
        return result
    text = _clean_spaces(value)
    joined = re.sub(r"(?<=[a-zà-ú])- (?=[a-zà-ú])", "-", text)
    if joined != text:
        trace.hit("channel_hyphen_join")
        text = joined
    fixed = re.sub(r",\s*,", ",", text)
    fixed = re.sub(r"\)(?=[a-zà-ú])", ") ", fixed)
    fixed = fixed.replace(" – ", " - ")
    if fixed != text:
        trace.hit("channel_punctuation")
        text = fixed

    match = _NOTE_MARK_RE.search(text)
    main, notes_text = (text[: match.start()], text[match.start() :]) if match else (text, "")
    notes = [
        _clean_spaces(n).rstrip(" .")
        for n in re.split(r"(?:^|\s)\*\s?(?=[A-ZÀ-Ú])", notes_text)
        if n.strip(" *")
    ]
    if notes:
        trace.hit("channel_note_split")
    main_clean = _clean_spaces(main.replace("*", " ")).rstrip(" .")
    if main_clean != main.strip():
        trace.hit("channel_marker_strip")
    if main_clean and main_clean[0].islower():
        main_clean = main_clean[0].upper() + main_clean[1:]
        trace.hit("channel_capitalize")

    def codes_for(segment: str) -> list[str]:
        folded = fold(segment)
        return [
            code
            for code, spec in vocab.channels["codes"].items()
            if any(re.search(p, folded) for p in spec["patterns"])
        ]

    codes = codes_for(main_clean)
    if not codes:
        trace.flag("channel_unmapped")
    note_codes = [c for c in codes_for(" ".join(notes)) if c not in codes]
    full = fold(text)
    flags = [name for name, needle in vocab.channels["restriction_flags"].items() if needle in full]
    result.update(text=main_clean, codes=codes, note_codes=note_codes, notes=notes, flags=flags)
    return result


# ----------------------------------------------------------------------- occurrence


def normalize_occurrence(occ: dict[str, Any], vocab: Vocabulary) -> dict[str, Any]:
    """Return the additive ``normalized`` object for one occurrence."""
    trace = RuleTrace()
    ingredient = canonical_ingredient(occ["active_ingredient"], vocab, trace)
    strength, strength_kind = canonical_strength(occ.get("strength") or "", vocab, trace)
    form = canonical_form(occ.get("form") or "", vocab, trace)
    release, release_rate = canonical_release(
        occ.get("release_characteristic"), form.pop("form_release"), trace
    )
    atc = parse_atc(occ.get("atc"), trace)
    channel = parse_channel(occ.get("channel"), vocab, trace)
    return {
        "active_ingredient": ingredient,
        "strength": strength,
        "strength_kind": strength_kind,
        **form,
        "release": release,
        "release_rate": release_rate,
        "atc": atc,
        "channel_text": channel["text"],
        "channel_codes": channel["codes"],
        "channel_note_codes": channel["note_codes"],
        "channel_notes": channel["notes"],
        "channel_flags": channel["flags"],
        "rules_applied": trace.applied,
        "review_flags": trace.flags,
    }


def identity_key(
    normalized: dict[str, Any], source_ids: Iterable[str]
) -> tuple[str, str, str, str]:
    """Catalog identity. Package is part of identity; absent forms never merge across sources."""
    if normalized["form"]:
        form_key = fold(normalized["form"])
        if normalized["package"]:
            form_key += "|pkg:" + fold(normalized["package"])
    elif normalized["package"]:
        form_key = "pkg:" + fold(normalized["package"])
    elif normalized["specification"]:
        form_key = "spec:" + fold(normalized["specification"])
    else:
        form_key = "absent:" + ",".join(sorted(set(source_ids)))
    if not normalized["strength"]:
        strength = "absent"
    elif normalized.get("strength_kind") == "textual":
        # Never merge textual strengths without literal equality.
        strength = "lit:" + normalized["strength"]
    else:
        strength = fold(normalized["strength"])
    return (
        fold(normalized["active_ingredient"]),
        strength,
        form_key,
        fold(normalized["release"] or ""),
    )
