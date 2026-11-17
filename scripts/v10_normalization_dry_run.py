"""Dry-run of the v10 normalization rules over the approved v9 release (F1 exit gate).

Writes nothing into data/releases. Produces a report with:
- rule frequency (overall and per source) and rules/vocabulary entries that never fire;
- review flags (PDF artifacts, ambiguous decimals, unmapped channels, conflicts);
- distinct values before/after per field;
- projected catalog identity (merges) compared with v9 and the superseded v10-reconciliada.

Usage: PYTHONPATH=src python3 scripts/v10_normalization_dry_run.py [--fail-on-gate]
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from rag.normalization import (
    fold,
    identity_key,
    load_vocabulary,
    normalize_occurrence,
)

ROOT = Path(__file__).resolve().parents[1]
V9 = ROOT / "data/releases/corpus-consolidado-v9-aprovado-2026-11-12"
V10_OLD = ROOT / "data/releases/corpus-consolidado-v10-reconciliada-2026-11-16"
VOCAB = ROOT / "data/vocab"
OUT_DIR = ROOT / "docs/reports/v10"

KNOWN_RULES = (
    "ingredient_spacing",
    "ingredient_vocab",
    "strength_whitespace",
    "strength_pdf_artifact_fix",
    "strength_unit_canonical",
    "strength_percent_spacing",
    "form_specification",
    "form_descriptor",
    "form_spelling",
    "form_synonym",
    "form_release_preposition",
    "form_volume_to_package",
    "form_package_suffix",
    "form_package_only",
    "form_release_extracted",
    "form_alternatives",
    "release_whitespace_case",
    "release_rate_to_strength_note",
    "atc_strip_continua",
    "atc_footnote_split",
    "atc_join_space",
    "atc_multiple_split",
    "channel_hyphen_join",
    "channel_punctuation",
    "channel_note_split",
    "channel_marker_strip",
    "channel_capitalize",
)
GATE_FLAGS_BLOCKING = ("channel_unmapped", "atc_invalid")


def rows(path: Path) -> list[dict[str, Any]]:
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def run() -> dict[str, Any]:
    vocab = load_vocabulary(VOCAB)
    occurrences = rows(V9 / "occurrences.jsonl")
    catalog = rows(V9 / "catalog.jsonl")
    before = json.dumps(occurrences, sort_keys=True)

    normalized = {o["occurrence_id"]: normalize_occurrence(o, vocab) for o in occurrences}
    if json.dumps(occurrences, sort_keys=True) != before:
        raise AssertionError("A normalização alterou campos literais")
    by_occ = {o["occurrence_id"]: o for o in occurrences}

    rule_counts: Counter[str] = Counter()
    rule_by_source: dict[str, Counter[str]] = defaultdict(Counter)
    flag_examples: dict[str, list[dict[str, Any]]] = defaultdict(list)
    flag_counts: Counter[str] = Counter()
    for oid, norm in normalized.items():
        src = by_occ[oid]["source"]["source_id"]
        for rule in norm["rules_applied"]:
            rule_counts[rule] += 1
            rule_by_source[rule][src] += 1
        for flag in norm["review_flags"]:
            flag_counts[flag] += 1
            if len(flag_examples[flag]) < 5:
                o = by_occ[oid]
                flag_examples[flag].append(
                    {
                        "occurrence_id": oid,
                        "source": src,
                        "page": o["source"]["page"],
                        "strength": o["strength"],
                        "form": o["form"],
                        "atc": o.get("atc"),
                        "channel": (o.get("channel") or "")[:160],
                    }
                )

    # Vocabulary entries that never fire
    unused: dict[str, list[str]] = {}
    forms_low = [(o.get("form") or "").lower() for o in occurrences]
    unused["forms.spelling_fixes"] = [
        k for k in vocab.forms["spelling_fixes"] if not any(k.strip() in f for f in forms_low)
    ]
    unused["forms.package_only"] = [k for k in vocab.forms["package_only"] if k not in forms_low]
    used_codes = Counter(
        c for n in normalized.values() for c in n["channel_codes"] + n["channel_note_codes"]
    )
    unused["channels.codes"] = [c for c in vocab.channels["codes"] if c not in used_codes]
    used_flags = Counter(f for n in normalized.values() for f in n["channel_flags"])
    unused["channels.restriction_flags"] = [
        f for f in vocab.channels["restriction_flags"] if f not in used_flags
    ]
    literal_names = {o["active_ingredient"] for o in occurrences}
    spaced_names = {re.sub(r"\s*\+\s*", " + ", " ".join(n.split())) for n in literal_names}
    unused["ingredients.mappings"] = [
        m["variant"] for m in vocab.ingredients["mappings"] if m["variant"] not in spaced_names
    ]

    # Distinct values before / after
    def distinct(field: str, norm_field: str, source: str | None = None) -> dict[str, int]:
        sel = [o for o in occurrences if source is None or o["source"]["source_id"] == source]
        lit = {o.get(field) for o in sel if o.get(field) not in (None, "", "-")}
        can = {
            normalized[o["occurrence_id"]][norm_field]
            for o in sel
            if normalized[o["occurrence_id"]][norm_field] not in (None, "", [])
        }
        return {"literal": len(lit), "canonical": len(can)}

    channel_codesets = Counter(
        tuple(normalized[o["occurrence_id"]]["channel_codes"])
        for o in occurrences
        if o.get("channel")
    )
    folded_ingredients: dict[str, set[str]] = defaultdict(set)
    for n in normalized.values():
        folded_ingredients[fold(n["active_ingredient"])].add(n["active_ingredient"])
    remaining_variants = {k: sorted(v) for k, v in folded_ingredients.items() if len(v) > 1}

    distinct_report = {
        "active_ingredient": distinct("active_ingredient", "active_ingredient"),
        "strength": distinct("strength", "strength"),
        "form": distinct("form", "form"),
        "channel_text(F03)": distinct("channel", "channel_text", "F03"),
        "channel_codesets(F03)": len(channel_codesets),
        "ingredient_variants_remaining_after_fold": len(remaining_variants),
    }
    kinds = {
        "strength_kind": Counter(n["strength_kind"] for n in normalized.values()),
        "form_kind": Counter(n["form_kind"] for n in normalized.values()),
        "atc_kind": Counter(
            str(normalized[o["occurrence_id"]]["atc"]["kind"]) for o in occurrences if o.get("atc")
        ),
    }

    # Projected catalog identity
    groups: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    split_entries = []
    for entry in catalog:
        keys = {
            identity_key(normalized[oid], entry["source_ids"]) for oid in entry["occurrence_ids"]
        }
        if len(keys) != 1:
            split_entries.append(entry["medicine_id"])
        groups[sorted(keys)[0]].append(entry)
    merges = [g for g in groups.values() if len(g) > 1]
    old_merged_ids: set[str] = set()
    if (V10_OLD / "catalog.jsonl").exists():
        old_ids = {e["medicine_id"] for e in rows(V10_OLD / "catalog.jsonl")}
        old_merged_ids = {e["medicine_id"] for e in catalog} - old_ids
    new_merged_ids = {e["medicine_id"] for g in merges for e in g[1:]}
    merged_entry_ids = {e["medicine_id"] for g in merges for e in g}
    projected = {
        "catalog_v9": len(catalog),
        "catalog_projected": len(groups),
        "merge_groups": len(merges),
        "entries_absorbed": sum(len(g) - 1 for g in merges),
        "entries_split_inconsistent": split_entries,
        "v10_reconciliada_absorbed": len(old_merged_ids),
        "v10_reconciliada_absorbed_not_merged_now": sorted(old_merged_ids - merged_entry_ids),
        "sources_after": Counter(
            ",".join(sorted({s for e in g for s in e["source_ids"]})) for g in groups.values()
        ),
        "merge_reasons": Counter(
            "+".join(
                sorted(
                    {
                        r
                        for e in g
                        for oid in e["occurrence_ids"]
                        for r in normalized[oid]["rules_applied"]
                        if r.startswith(
                            (
                                "ingredient_",
                                "strength_unit",
                                "strength_percent",
                                "form_",
                                "release_",
                            )
                        )
                    }
                )
            )
            or "fold_only"
            for g in merges
        ),
        "merge_examples": [
            [
                f"{e['active_ingredient']} | {e['strength']} | {e['form']} | "
                f"{e.get('release_characteristic')} | {e['source_ids']}"
                for e in g
            ]
            for g in merges[:15]
        ],
    }
    _ = new_merged_ids

    gate = {
        "blocking_flags": {f: flag_counts.get(f, 0) for f in GATE_FLAGS_BLOCKING},
        "rules_never_fired": [r for r in KNOWN_RULES if rule_counts.get(r, 0) == 0],
        "catalog_entries_split": len(split_entries),
        "ingredient_variants_remaining": len(remaining_variants),
    }
    gate["passed"] = (
        all(v == 0 for v in gate["blocking_flags"].values())
        and gate["catalog_entries_split"] == 0
        and gate["ingredient_variants_remaining"] == 0
    )

    return {
        "source_release": V9.name,
        "occurrences": len(occurrences),
        "literal_fields_unchanged": True,
        "rule_counts": dict(rule_counts.most_common()),
        "rule_counts_by_source": {k: dict(v) for k, v in sorted(rule_by_source.items())},
        "review_flags": dict(flag_counts.most_common()),
        "review_flag_examples": flag_examples,
        "unused_vocabulary": unused,
        "distinct_values": distinct_report,
        "remaining_ingredient_variants": remaining_variants,
        "kinds": {k: dict(v) for k, v in kinds.items()},
        "channel_codes_frequency": dict(used_codes.most_common()),
        "projected_catalog": projected,
        "gate": gate,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fail-on-gate", action="store_true")
    args = parser.parse_args()
    report = run()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / "dry-run-normalizacao-v10.json"
    out.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, default=list) + "\n", encoding="utf-8"
    )
    summary = {
        "output": str(out.relative_to(ROOT)),
        "gate": report["gate"],
        "distinct_values": report["distinct_values"],
        "catalog": {
            k: report["projected_catalog"][k]
            for k in (
                "catalog_v9",
                "catalog_projected",
                "merge_groups",
                "entries_absorbed",
                "v10_reconciliada_absorbed",
            )
        },
    }
    print(json.dumps(summary, ensure_ascii=False, indent=1, default=list))
    return 1 if args.fail_on_gate and not report["gate"]["passed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
