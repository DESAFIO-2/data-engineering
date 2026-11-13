"""Coordinate-aware extraction of frozen list tables; all output remains pending."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pdfplumber


def clean(value: str | None) -> str | None:
    return " ".join(value.split()) if value else None


def rename_rows(path: Path) -> list[dict[str, Any]]:
    """Appendix A is the primary complete list; Appendix B repeats financing views.

    A missing cell is resolved ONLY from a geometrically spanning merged cell.
    Page numbers refer to the frozen 267-page PDF, not printed pagination.
    """
    result = []
    with pdfplumber.open(path) as pdf:
        if len(pdf.pages) != 267:
            raise ValueError("Layout RENAME exige a edição congelada de 267 páginas")
        for number in range(26, 133):
            page = pdf.pages[number - 1]
            for table in page.find_tables():
                extracted = table.extract()
                if not extracted or len(extracted[0]) < 5:
                    continue
                header = " ".join(v or "" for v in extracted[0])
                if "Farmac" not in header or "Comum" not in header:
                    continue
                header_cells = table.rows[0].cells
                for row_index, row in enumerate(table.rows[1:], 1):
                    values, inherited = [], []
                    for col, cell in enumerate(row.cells):
                        header_cell = header_cells[col]
                        if cell is None and header_cell is not None:
                            x0, _, x1, _ = header_cell
                            midpoint_x = (x0 + x1) / 2
                            midpoint_y = (row.bbox[1] + row.bbox[3]) / 2
                            matches = [
                                c
                                for c in table.cells
                                if c[0] < midpoint_x < c[2] and c[1] < midpoint_y < c[3]
                            ]
                            if len(matches) == 1:
                                cell = matches[0]
                                inherited.append(col)
                        value = page.crop(cell).extract_text() if cell is not None else None
                        values.append(clean(value))
                    if not any(values) or len(values) < 5:
                        continue
                    name, strength, form = values[:3]
                    component = next(
                        (
                            values[j]
                            for j, h in enumerate(extracted[0])
                            if h and "Financiamento" in h
                        ),
                        None,
                    )
                    atc = next(
                        (values[j] for j, h in enumerate(extracted[0]) if h and "ATC" in h), None
                    )
                    result.append(
                        {
                            "page": number,
                            "active_ingredient": name,
                            "strength": strength,
                            "form": form,
                            "component": component,
                            "atc": atc,
                            "raw_text": " | ".join(v or "[não informado]" for v in values),
                            "bbox": list(row.bbox),
                            "row_number": row_index,
                            "inherited_columns": inherited,
                            "parser": "rename_geometry_appendix_a",
                        }
                    )
    return result


def reme_rows(path: Path) -> list[dict[str, Any]]:
    """Recover numbered rows using the bounding rectangle around the number.

    Restricts to the main alphabetical list (pages 12–59 after header discovery);
    other tables remain available in page chunks, not conflated with the main list.
    """
    result = []
    with pdfplumber.open(path) as pdf:
        for number, page in enumerate(pdf.pages, 1):
            if not 12 <= number <= 59:
                continue
            words = page.extract_words()
            anchors = [
                w for w in words if re.fullmatch(r"\d{1,4}\.", w["text"]) and 35 <= w["x0"] <= 65
            ]
            if not anchors:
                continue
            boundaries = sorted(
                {
                    e["top"]
                    for e in page.edges
                    if e["orientation"] == "h" and 34 <= e["x0"] <= 38 and e["x1"] >= 70
                }
            )
            for word in anchors:
                above = [y for y in boundaries if y <= word["top"]]
                below = [y for y in boundaries if y >= word["bottom"]]
                if not above or not below:
                    continue
                top, bottom = max(above), min(below)
                # Main layout: item, code, description, class, access channel.
                raw = page.crop((36, top, min(562, page.width), bottom)).extract_text() or ""
                desc = clean(page.crop((123, top, 284, bottom)).extract_text())
                code_text = page.crop((72, top, 122, bottom)).extract_text() or ""
                code_lines = [
                    re.sub(r"\s+", "", line) for line in code_text.splitlines() if line.strip()
                ]
                code = ", ".join(code_lines) or None
                channel = clean(page.crop((398, top, min(562, page.width), bottom)).extract_text())
                result.append(
                    {
                        "page": number,
                        "row_number": int(word["text"][:-1]),
                        "description": desc,
                        "code": code,
                        "channel": channel,
                        "raw_text": raw,
                        "bbox": [36, top, min(562, page.width), bottom],
                        "parser": "reme_geometry_numbered",
                    }
                )
    return result
