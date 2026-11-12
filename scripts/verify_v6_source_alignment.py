"""Compare frozen source extractions with every published v6 occurrence.

This is an independent, read-only verification. It never rewrites a release.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from collections import Counter
from hashlib import sha256
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rag.table_extract import reme_rows, rename_rows  # type: ignore[import-untyped]  # noqa: E402

RELEASE = ROOT / "data/releases/corpus-consolidado-v6-auditado-2026-11-11"
SOURCE_PATHS = {
    "F01": ROOT / "data/raw/F01-rename/rename-2024-2ed.pdf",
    "F03": ROOT / "data/raw/F03-reme-df/reme-df-2026-10-29.pdf",
    "F04": ROOT / "data/raw/F04-farmacia-popular/farmacia-popular-elenco-2026-08-31.pdf",
}


def normalized(value: Any) -> str:
    """Normalize only Unicode, case, whitespace and source line hyphenation."""
    text = unicodedata.normalize("NFKD", str(value or "").casefold())
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"(?<=\w)-\s+(?=\w)", "", text)
    return " ".join(text.split())


def rows(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def extraction(source: str) -> tuple[list[dict[str, Any]], bool | None]:
    parser = rename_rows if source == "F01" else reme_rows
    pdf = SOURCE_PATHS[source]
    cache = ROOT / "scripts" / f"{source.lower()}_extracted_cache.json"
    fresh = parser(pdf)
    if not cache.exists():
        return fresh, None
    cached = json.loads(cache.read_text(encoding="utf-8"))
    return fresh, fresh == cached


def verify(release: Path = RELEASE) -> dict[str, Any]:
    manifest = json.loads((release / "release.json").read_text(encoding="utf-8"))
    findings: list[dict[str, Any]] = []
    for source, pdf_path in SOURCE_PATHS.items():
        actual = sha256(pdf_path.read_bytes()).hexdigest()
        if actual != manifest["sources"][source]["sha256"]:
            findings.append(
                {
                    "source": source,
                    "field": "pdf_sha256",
                    "expected": manifest["sources"][source]["sha256"],
                    "actual": actual,
                }
            )
    extracted_sources = {name: extraction(name) for name in ("F01", "F03")}
    source_rows = {name: value[0] for name, value in extracted_sources.items()}
    for name, (_, cache_equal) in extracted_sources.items():
        if cache_equal is False:
            findings.append({"source": name, "field": "cache_missing_or_divergent"})
    by_key = {
        name: {(row["page"], row["row_number"]): row for row in values}
        for name, values in source_rows.items()
    }
    for name, values in source_rows.items():
        if len(by_key[name]) != len(values):
            findings.append({"source": name, "field": "duplicate_extracted_row_key"})
    published = rows(release / "occurrences.jsonl")
    catalog = rows(release / "catalog.jsonl")
    audit = rows(release / "audit_log.jsonl")
    audits = {x.get("occurrence_id"): x for x in audit}
    for medicine in catalog:
        expected_exact = medicine.get("strength") not in (None, "", "-") and medicine.get(
            "form"
        ) not in (None, "", "-")
        if medicine.get("exact_presentation_supported") is not expected_exact:
            findings.append(
                {
                    "medicine_id": medicine["medicine_id"],
                    "field": "exact_presentation_supported",
                    "published": medicine.get("exact_presentation_supported"),
                    "expected": expected_exact,
                }
            )
    import pdfplumber

    with pdfplumber.open(SOURCE_PATHS["F04"]) as pdf:
        f04_lines = [normalized(line) for line in (pdf.pages[0].extract_text() or "").splitlines()]
    f04_used: set[int] = set()
    used: dict[str, set[tuple[int, int]]] = {"F01": set(), "F03": set()}

    def compare(occ: dict[str, Any], field: str, actual: Any, *, contains: bool = False) -> None:
        expected = occ.get(field)
        a, e = normalized(actual), normalized(expected)
        if e not in a if contains else e != a:
            findings.append(
                {
                    "occurrence_id": occ["occurrence_id"],
                    "source": occ["source"]["source_id"],
                    "page": occ["source"]["page"],
                    "row": occ.get("source_row_number"),
                    "field": field,
                    "published": expected,
                    "extracted": actual,
                }
            )

    for occ in published:
        source = occ["source"]["source_id"]
        audit_record = audits.get(occ["occurrence_id"])
        expected_exact = occ.get("strength") not in (None, "", "-") and occ.get("form") not in (
            None,
            "",
            "-",
        )
        if (
            not audit_record
            or audit_record.get("exact_presentation_supported") is not expected_exact
        ):
            findings.append(
                {
                    "occurrence_id": occ["occurrence_id"],
                    "source": source,
                    "field": "audit_exact_presentation_supported",
                }
            )
        if source == "F04":
            literal = normalized(occ["raw_text"])
            matches = [i for i, line in enumerate(f04_lines) if line.endswith(literal)]
            if len(matches) != 1:
                findings.append(
                    {
                        "occurrence_id": occ["occurrence_id"],
                        "source": source,
                        "field": "literal_row",
                        "published": occ["raw_text"],
                        "matches": len(matches),
                    }
                )
            else:
                if matches[0] in f04_used:
                    findings.append(
                        {
                            "occurrence_id": occ["occurrence_id"],
                            "source": source,
                            "field": "duplicate_source_row",
                            "row": matches[0],
                        }
                    )
                # The published F04 row number counts product rows, while
                # extract_text also includes standalone indication headings.
                expected_row_number = 2 + len(f04_used)
                f04_used.add(matches[0])
                if occ.get("source_row_number") != expected_row_number:
                    findings.append(
                        {
                            "occurrence_id": occ["occurrence_id"],
                            "source": source,
                            "field": "source_row_number",
                            "published": occ.get("source_row_number"),
                            "extracted": expected_row_number,
                        }
                    )
            if occ["form"] != "-":
                findings.append(
                    {
                        "occurrence_id": occ["occurrence_id"],
                        "source": source,
                        "field": "unsubstantiated_form",
                        "published": occ["form"],
                    }
                )
            continue
        if source not in by_key:
            continue
        key = (occ["source"]["page"], occ["source_row_number"])
        extracted = by_key[source].get(key)
        if extracted is None:
            findings.append(
                {
                    "occurrence_id": occ["occurrence_id"],
                    "source": source,
                    "field": "source_row_missing",
                    "page": key[0],
                    "row": key[1],
                }
            )
            continue
        if key in used[source]:
            findings.append(
                {
                    "occurrence_id": occ["occurrence_id"],
                    "source": source,
                    "field": "duplicate_source_row",
                    "page": key[0],
                    "row": key[1],
                }
            )
        used[source].add(key)
        compare(occ, "raw_text", extracted["raw_text"])
        compare(occ, "bbox", extracted["bbox"])
        if source == "F01":
            for field in ("active_ingredient", "strength", "form", "component", "atc"):
                compare(occ, field, extracted[field])
        else:
            compare(occ, "source_code", extracted["code"])
            compare(occ, "channel", extracted["channel"])
            for field in ("active_ingredient", "strength", "form"):
                if occ.get(field) not in (None, "", "-"):
                    compare(occ, field, extracted["description"], contains=True)
            if occ.get("release_characteristic"):
                compare(occ, "release_characteristic", extracted["description"], contains=True)
    exclusions = rows(release / "exclusions.jsonl")
    excluded = {(x["source"]["page"], x["source_row_number"]) for x in exclusions}
    for source, mapping in by_key.items():
        for key in mapping.keys() - used[source] - (excluded if source == "F03" else set()):
            findings.append(
                {"source": source, "field": "unpublished_source_row", "page": key[0], "row": key[1]}
            )
    headings = {
        normalized(x.get("context", {}).get("indication", ""))
        for x in published
        if x["source"]["source_id"] == "F04"
    }
    for index, line in enumerate(f04_lines):
        if (
            index not in f04_used
            and index not in {0, 1, len(f04_lines) - 1}
            and line not in headings
        ):
            findings.append(
                {
                    "source": "F04",
                    "field": "unpublished_source_row",
                    "page": 1,
                    "row": index,
                    "text": line,
                }
            )
    return {
        "release": manifest["release_version"],
        "occurrences_checked": len(published),
        "source_rows": {k: len(v) for k, v in source_rows.items()},
        "cache_matches_fresh_extraction": {
            name: value[1] for name, value in extracted_sources.items()
        },
        "method": "fresh PDF geometric extraction F01/F03 and page-1 literal lines F04",
        "findings_by_field": dict(Counter(x["field"] for x in findings)),
        "findings": findings,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--release", type=Path, default=RELEASE)
    args = parser.parse_args()
    result = verify(args.release)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({k: v for k, v in result.items() if k != "findings"}, ensure_ascii=False))
    raise SystemExit(1 if result["findings"] else 0)


if __name__ == "__main__":
    main()
