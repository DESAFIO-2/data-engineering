"""Experimental, unapproved corpus from the complete F01/F03/F04 Silver snapshots."""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from hashlib import sha256
from pathlib import Path
from typing import Any

from .table_extract import reme_rows, rename_rows

SCHEMA_VERSION = "2.0"
PARSER_VERSION = "2.2-geometry"
SOURCE_VERSIONS = {
    "F01": "RENAME 2024, 2ª edição",
    "F03": "REME-DF 2026-10-29",
    "F04": "Farmácia Popular 2026-08-31",
}
MANIFEST_PATH = "data/manifests/coleta-inicial-pdfs-2026-11-03.json"
DOSE = re.compile(
    r"\d[\d.,]*\s*(?:mcg|mg|g|UI|U|mEq|mmol|%|gv)"
    r"(?:\s*/\s*(?:\d[\d.,]*\s*)?(?:mL|ml|g|dose))?(?!\w)",
    re.I,
)
FORM = re.compile(
    r"\b(?:pó liofilizado ou solução injetável|"
    r"pó (?:liofilizado|liofilizo)(?: para (?:solução|suspensão)(?: injetável| oral)?| injetável)?|"
    r"solução(?: injetável| oral| oftálmica| nasal| retal| inalatória| para infusão)?|"
    r"suspensão(?: injetável| oral)?|comprimido(?: revestido| mastigável)?|"
    r"granulado revestido|cápsula|pomada(?: oftálmica)?|creme|gel|xarope|supositório(?: retal)?|"
    r"tintura|emulsão|injetável)\b",
    re.I,
)
ITEM = re.compile(r"^\s*\d{1,4}\.\s+")
CODE = re.compile(r"^(?:(?:MSE?|MS)\d+|\d{3,6})\s+")


def digest(raw: bytes) -> str:
    return sha256(raw).hexdigest()


def stable_id(prefix: str, *parts: Any) -> str:
    return prefix + digest(json.dumps(parts, ensure_ascii=False).encode("utf-8"))[:24]


def compact(text: str) -> str:
    return " ".join(text.split())


def split_text(text: str, limit: int = 2000, overlap: int = 240) -> list[tuple[int, int, str]]:
    """Bounded Unicode-character windows with exact offsets, within one source unit."""
    if limit < 1 or not 0 <= overlap < limit:
        raise ValueError("Invalid chunk size/overlap")
    result = []
    start = 0
    while start < len(text):
        end = min(start + limit, len(text))
        if end < len(text):
            boundary = text.rfind("\n", start + limit // 2, end)
            if boundary < 0:
                boundary = text.rfind(" ", start + limit // 2, end)
            if boundary > start:
                end = boundary
        result.append((start, end, text[start:end]))
        if end == len(text):
            break
        start = max(start + 1, end - overlap)
    return result


def fields(text: str) -> tuple[str | None, str | None, str | None]:
    """Only literal substrings; no terminology enrichment or cross-row inheritance."""
    value = compact(text)
    value = ITEM.sub("", value)
    while CODE.match(value):
        value = CODE.sub("", value, count=1)
    doses, form = list(DOSE.finditer(value)), FORM.search(value)
    boundary = min((m.start() for m in (*doses, form) if m), default=len(value))
    name = value[:boundary].strip(" -") or None
    if name and (not any(c.isalpha() for c in name) or len(name) > 150):
        name = None
    # Prefer doses before the dosage form; a later package size is not strength.
    # When the source lists a fixed-dose combination, retain all its components.
    before_form = [match for match in doses if form and match.start() < form.start()]
    selected_doses = before_form or doses[:1]
    strength = " + ".join(match.group() for match in selected_doses) or None
    if len(doses) >= 2 and "+" in value[doses[0].end() : doses[1].start()]:
        first, second = doses[:2]
        between = value[first.end() : second.start()]
        first_name = value[: first.start()].strip(" -")
        second_name = between.split("+", 1)[1].strip(" -")
        if first_name and second_name and any(char.isalpha() for char in second_name):
            return (
                f"{first_name} + {second_name}",
                f"{first.group()} + {second.group()}",
                form.group() if form else None,
            )
    if len(selected_doses) > 1 and "+" not in (name or ""):
        strength = None
    form_text = form.group() if form else None
    if form_text:
        form_text = form_text.replace("liofilizo", "liofilizado")
    return name, strength, form_text


def split_pf_heading(line: str) -> tuple[str, str | None]:
    """Separate an uppercase indication/program label from its item text."""
    match = re.match(r"^\s*([A-ZÁÀÂÃÉÊÍÓÔÕÚÇ +]+)\s+(?=[a-záàâãéêíóôõúç])", line)
    if not match:
        return line.strip(), None
    return line[match.end() :].strip(), match.group(1).strip()


def parse_f01(lines: list[str]) -> list[tuple[int, int, str, str]]:
    """Dose anchors plus surrounding table cells; never guess a merged DCB cell."""
    result = []
    headers = [i for i, line in enumerate(lines) if line.strip() in ("Código ATC", "ATC")]
    if headers:
        start = headers[0] + 1
        for i in range(start, len(lines)):
            if re.search(
                r"\b[A-Z]\d{2}[A-Z]{1,2}(?:\d{2,4})?(?:\(\d\))?(?:\s+[-\w]+)?$", lines[i].strip()
            ):
                value = "\n".join(lines[start : i + 1])
                result.append((start, i + 1, value, "rename_atc_row"))
                start = i + 1
        if result:
            # Preserve unusual trailing cells as unresolved candidates too.
            for i in range(start, len(lines)):
                if DOSE.search(lines[i]) or FORM.search(lines[i]):
                    result.append((i, min(len(lines), i + 3), lines[i], "rename_cell_anchor"))
            return result
    for i, line in enumerate(lines):
        if DOSE.search(line) or FORM.search(line):
            result.append((i, min(len(lines), i + 3), line, "rename_cell_anchor"))
    return result


def parse_f03(lines: list[str]) -> list[tuple[int, int, str, str]]:
    starts = [i for i, line in enumerate(lines) if ITEM.match(line)]
    result = []
    if starts:
        for n, start in enumerate(starts):
            end = starts[n + 1] if n + 1 < len(starts) else len(lines)
            result.append((start, end, "\n".join(lines[start:end]), "reme_numbered_row"))
    else:
        # Secondary tables may have codes without item numbers or no codes at all.
        for i, line in enumerate(lines):
            if CODE.match(line.strip()) or DOSE.search(line) or FORM.search(line):
                result.append((i, min(len(lines), i + 3), line, "reme_secondary_anchor"))
    return result


def parse_f04(lines: list[str]) -> list[tuple[int, int, str, str]]:
    result = []
    for i, line in enumerate(lines):
        if DOSE.search(line) or "absorvente higiênico" in line or "fralda geriátrica" in line:
            # Uppercase indication labels sometimes share the medication line.
            value, _ = split_pf_heading(line)
            result.append((i, i + 1, value, "pfpb_literal_row"))
    return result


PARSERS = {"F01": parse_f01, "F03": parse_f03, "F04": parse_f04}


def build_corpus(root: Path, output: Path | None = None) -> dict[str, Any]:
    root = root.resolve()
    output = (output or root / "data/corpus/experimental").resolve()
    if output != root / "data/corpus/experimental":
        raise ValueError("Output must be data/corpus/experimental; releases are immutable here")
    manifest_bytes = (root / MANIFEST_PATH).read_bytes()
    collection = json.loads(manifest_bytes)
    occurrences: list[dict[str, Any]] = []
    chunks: list[dict[str, Any]] = []
    sources = []
    summaries = {}
    for sid in SOURCE_VERSIONS:
        source = next(s for s in collection["sources"] if s["source_id"] == sid)
        pdf_path = root / "data" / source["path"]
        if digest(pdf_path.read_bytes()) != source["sha256"]:
            raise ValueError(f"PDF hash mismatch: {sid}")
        silver_path = root / "data/silver" / sid / f"{source['sha256']}.jsonl"
        silver_bytes = silver_path.read_bytes()
        pages = [json.loads(line) for line in silver_bytes.decode("utf-8").splitlines() if line]
        if sorted(p["page"] for p in pages) != list(range(1, source["pages"] + 1)):
            raise ValueError(f"Missing or duplicate Silver pages: {sid}")
        count_before = len(occurrences)
        geometry: dict[int, list[dict[str, Any]]] = defaultdict(list)
        if sid in {"F01", "F03"}:
            extracted = rename_rows(pdf_path) if sid == "F01" else reme_rows(pdf_path)
            for record in extracted:
                geometry[record["page"]].append(record)
        empty_pages, no_rows, page_counts = [], [], {}
        for page in sorted(pages, key=lambda p: p["page"]):
            if (
                page["source_id"] != sid
                or page["content_sha256"] != source["sha256"]
                or page["source_url"] != source["source_url"]
            ):
                raise ValueError(f"Silver provenance mismatch: {sid}")
            text = page["text"]
            if len(text) != page["text_length"]:
                raise ValueError(f"Silver text length mismatch: {sid}")
            lines = text.splitlines()
            provenance = {
                "source_id": sid,
                "url": source["source_url"],
                "version": SOURCE_VERSIONS[sid],
                "sha256": source["sha256"],
                "page": page["page"],
            }
            page_ids = []
            for offset, finish, part in split_text(text):
                page_id = stable_id("ev-", provenance, "page", offset, finish, part)
                page_ids.append(page_id)
                chunks.append(
                    {
                        "evidence_id": page_id,
                        "text": part,
                        "medicine_id": None,
                        "source": provenance,
                        "review_status": "pending",
                        "chunk_type": "page",
                        "occurrence_id": None,
                        "char_start": offset,
                        "char_end": finish,
                    }
                )
            candidates = (
                [
                    (i, i + 1, row["raw_text"], row["parser"])
                    for i, row in enumerate(geometry[page["page"]])
                ]
                if sid in {"F01", "F03"}
                else parse_f04(lines)
            )
            page_counts[str(page["page"])] = len(candidates)
            if not text.strip():
                empty_pages.append(page["page"])
            if not candidates:
                no_rows.append(page["page"])
            for start, end, value, parser in candidates:
                geometric = geometry[page["page"]][start] if sid in {"F01", "F03"} else {}
                source_raw = geometric.get("raw_text", "\n".join(lines[start:end]))
                indication = None
                if sid == "F04":
                    raw, indication = split_pf_heading(source_raw)
                else:
                    raw = source_raw
                name, strength, form = (
                    fields(geometric.get("description") or "")
                    if sid == "F03"
                    else (geometric["active_ingredient"], geometric["strength"], geometric["form"])
                    if sid == "F01"
                    else fields(value)
                )
                release_characteristic = (
                    "ação prolongada"
                    if sid == "F04" and re.search(r"\bação prolongada\b", raw, re.I)
                    else None
                )
                item_type = "supply" if re.search(r"fralda|absorvente", raw, re.I) else "medicine"
                supply_name = name if item_type == "supply" else None
                if item_type == "supply":
                    name = None
                issues = ["human_verification_pending", "list_membership_not_verified"]
                if sid == "F03" and "liofilizo" in (geometric.get("description") or ""):
                    issues.append("source_typo_normalized_in_form_raw_text_preserved")
                if parser.endswith("anchor"):
                    issues.append("cell_boundaries_and_shared_names_unresolved")
                    # A cell fragment is not a confidently delimited ingredient.
                    name = None
                if sid == "F04":
                    issues.append("same_line_indication_label_requires_human_verification")
                for key, val in (
                    ("active_ingredient", name if item_type == "medicine" else supply_name),
                    ("strength", strength),
                    ("form", form),
                ):
                    if val is None and not (item_type == "supply" and key != "active_ingredient"):
                        issues.append(f"{key}_unresolved")
                oid = stable_id("occ-", provenance, parser, start + 1, end, raw)
                row_text = (
                    f"Descrição: {geometric['description']}\n"
                    f"Código: {geometric.get('code')}\n"
                    f"Canal na linha: {geometric.get('channel')}"
                    if sid == "F03"
                    else (
                        f"Indicação/programa: {indication}\nItem: {raw}"
                        if sid == "F04" and indication
                        else raw
                    )
                )
                row_ids = []
                for offset, finish, part in split_text(row_text):
                    eid = stable_id("ev-", oid, "row", offset, finish, part)
                    row_ids.append(eid)
                    chunks.append(
                        {
                            "evidence_id": eid,
                            "text": part,
                            "medicine_id": None,
                            "source": provenance,
                            "review_status": "pending",
                            "chunk_type": "row",
                            "occurrence_id": oid,
                            "char_start": offset,
                            "char_end": finish,
                        }
                    )
                occurrences.append(
                    {
                        "occurrence_id": oid,
                        "active_ingredient": name,
                        "supply_name": supply_name,
                        "strength": strength,
                        "form": form,
                        "release_characteristic": release_characteristic,
                        "source": provenance,
                        "raw_text": raw,
                        "chunk_ids": row_ids + page_ids,
                        "review_status": "pending",
                        "parser": parser,
                        "line_start": start + 1 if not geometric else None,
                        "line_end": end if not geometric else None,
                        "bbox": geometric.get("bbox"),
                        "source_row_number": geometric.get("row_number", start + 1),
                        "source_code": geometric.get("code"),
                        "channel": geometric.get("channel"),
                        "component": geometric.get("component"),
                        "atc": geometric.get("atc"),
                        "item_type": item_type,
                        "context": {
                            "page_chunk_ids": page_ids,
                            "indication": indication,
                        },
                        "uncertainties": issues,
                    }
                )
        source_rows = occurrences[count_before:]
        summaries[sid] = {
            "pages_expected": source["pages"],
            "pages_preserved": len(pages),
            "candidate_occurrences": len(source_rows),
            "empty_text_pages": empty_pages,
            "pages_without_candidates": no_rows,
            "candidates_by_page": page_counts,
            "unresolved_fields": {
                k: sum(r[k] is None for r in source_rows)
                for k in ("active_ingredient", "strength", "form")
            },
            "parsers": dict(Counter(r["parser"] for r in source_rows)),
            "candidate_medicines": sum(r["item_type"] == "medicine" for r in source_rows),
            "candidate_supplies": sum(r["item_type"] == "supply" for r in source_rows),
            "missing_main_sequence": sorted(
                set(range(1, 1079)) - {r["source_row_number"] for r in source_rows}
            )
            if sid == "F03"
            else None,
        }
        sources.append(
            {
                **source,
                "version": SOURCE_VERSIONS[sid],
                "review_status": "pending",
                "pdf_path": pdf_path.relative_to(root).as_posix(),
                "silver_path": silver_path.relative_to(root).as_posix(),
                "silver_sha256": digest(silver_bytes),
            }
        )
    catalog: dict[str, dict[str, Any]] = {}
    for row in occurrences:
        if row["item_type"] != "medicine" or not all(
            row[k] for k in ("active_ingredient", "strength", "form")
        ):
            continue
        identity = [
            compact(row[k] or "").casefold()
            for k in ("active_ingredient", "strength", "form", "release_characteristic")
        ]
        mid = stable_id("med-", identity)
        row["medicine_id"] = mid
        entry = catalog.setdefault(
            mid,
            {
                "medicine_id": mid,
                "active_ingredient": row["active_ingredient"],
                "strength": row["strength"],
                "form": row["form"],
                "release_characteristic": row["release_characteristic"],
                "review_status": "pending",
                "occurrence_ids": [],
                "source_ids": [],
            },
        )
        entry["occurrence_ids"].append(row["occurrence_id"])
        entry["source_ids"] = sorted(set(entry["source_ids"]) | {row["source"]["source_id"]})
    by_occurrence = {r["occurrence_id"]: r for r in occurrences}
    for chunk in chunks:
        if chunk["occurrence_id"]:
            chunk["medicine_id"] = by_occurrence[chunk["occurrence_id"]].get("medicine_id")
    report = {
        "schema_version": SCHEMA_VERSION,
        "status": "experimental",
        "review_status": "pending",
        "structured_extraction_complete": False,
        "human_verified": False,
        "coverage": (
            "All source pages preserved; primary table rows extracted by geometry; "
            "human reconciliation pending"
        ),
        "limitations": [
            "Visual verification sampled RENAME p43 and REME p16; no exhaustive human review",
            "Duplicates across tables and sources intentionally retained",
            "RENAME Appendix A and REME primary list structured; secondary tables in page chunks",
            "Merged cells, multiline doses and page continuations require human review",
            "No inferred identity, clinical indication, availability or approval",
        ],
        "sources": summaries,
        "occurrences": len(occurrences),
        "chunks": len(chunks),
        "catalog_presentations": len(catalog),
        "chunking": {
            "unit": "unicode_characters",
            "max_size": 2000,
            "overlap_max": 240,
            "scope": "within source page or table row",
        },
    }
    output.mkdir(parents=True, exist_ok=True)
    files = {}
    for name, content in (
        ("occurrences.jsonl", occurrences),
        ("chunks.jsonl", chunks),
        ("catalog.jsonl", list(catalog.values())),
        ("report.json", report),
    ):
        if isinstance(content, list):
            raw_bytes = "".join(
                json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in content
            ).encode("utf-8")
        else:
            raw_bytes = (
                json.dumps(content, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
            ).encode("utf-8")
        (output / name).write_bytes(raw_bytes)
        files[name] = {"sha256": digest(raw_bytes), "bytes": len(raw_bytes)}
        if isinstance(content, list):
            files[name]["records"] = len(content)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "parser_version": PARSER_VERSION,
        "status": "experimental",
        "review_status": "pending",
        "sources": sources,
        "collection_manifest_sha256": digest(manifest_bytes),
        "files": files,
        "chunking": report["chunking"],
    }
    (output / "manifest.json").write_bytes(
        (json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    )
    return report
