"""Validação comparativa final do corpus consolidado contra as extrações literais das 3 fontes (F01, F03, F04)."""

from __future__ import annotations

import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]


def normalize_text(s: str) -> str:
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower()
    # Join words hyphenated across line breaks in PDF text
    s = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", s)
    return " ".join(s.split())


def load_pages_jsonl(path: Path, pdf_path: Path | None = None) -> tuple[dict[int, str], str]:
    pages: dict[int, str] = {}
    if path.is_file():
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    rec = json.loads(line)
                    pages[int(rec["page"])] = rec["text"]
        txt_path = path.with_name(path.name.replace("-pages.jsonl", ".txt"))
        raw_txt = txt_path.read_text(encoding="utf-8") if txt_path.is_file() else "\n".join(pages.values())
        return pages, raw_txt

    if pdf_path is not None and pdf_path.is_file():
        try:
            import pdfplumber  # type: ignore

            with pdfplumber.open(pdf_path) as pdf:
                for idx, page in enumerate(pdf.pages, start=1):
                    pages[idx] = page.extract_text() or ""
        except ImportError:
            import subprocess
            import tempfile

            dump_bin = Path("/tmp/pdf_dump_jsonl")
            if dump_bin.is_file():
                with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as tf:
                    tmp_jsonl = Path(tf.name)
                subprocess.run([str(dump_bin), str(pdf_path), str(tmp_jsonl)], check=True)
                for line in tmp_jsonl.read_text(encoding="utf-8").splitlines():
                    if line.strip():
                        rec = json.loads(line)
                        pages[int(rec["page"])] = rec["text"]
                tmp_jsonl.unlink(missing_ok=True)
        raw_txt = "\n".join(pages[k] for k in sorted(pages))
        return pages, raw_txt

    raise FileNotFoundError(f"Não foi possível carregar páginas de {path} nem de {pdf_path}")


def check_source_occurrences(
    occs: list[dict[str, Any]],
    pages: dict[int, str],
    raw_txt: str,
    source_id: str,
) -> dict[str, Any]:
    norm_pages = {p: normalize_text(t) for p, t in pages.items()}
    norm_full = normalize_text(raw_txt)

    total = len(occs)
    null_counts = {"active_ingredient": 0, "strength": 0, "form": 0}
    pending_reviews = 0
    unresolved_uncertainties = 0

    raw_text_in_page = 0
    raw_text_in_doc = 0
    ing_in_page = 0
    ing_in_doc = 0
    str_in_page = 0
    form_in_page = 0
    inferred_forms: list[dict[str, Any]] = []
    clinical_indications_in_strength: list[str] = []

    clinical_markers = [
        "- hiv",
        "- hepatite",
        "- tuberculose",
        "- toxoplasmose",
        "covid-19",
        "enxaqueca",
        "diabetes mellitus",
        "osteoporose",
        "dignidade menstrual",
        "incontinencia urinaria",
    ]

    for occ in occs:
        for k in null_counts:
            val = occ.get(k)
            if val is None or str(val).strip() == "":
                null_counts[k] += 1
        if occ.get("review_status") != "approved":
            pending_reviews += 1
        if occ.get("uncertainties"):
            unresolved_uncertainties += 1

        page = occ["source"]["page"]
        p_norm = norm_pages.get(page, "")

        rt_norm = normalize_text(occ.get("raw_text", ""))
        if rt_norm and rt_norm in p_norm:
            raw_text_in_page += 1
        if rt_norm and rt_norm in norm_full:
            raw_text_in_doc += 1

        ing_norm = normalize_text(occ.get("active_ingredient", ""))
        # Handle composite ingredients separated by '+' or ';'
        ing_parts = [
            p.strip()
            for p in re.split(r"[+;]", ing_norm)
            if p.strip() and p.strip() != "-"
        ]
        if not ing_parts or all(part in p_norm for part in ing_parts):
            ing_in_page += 1
        if not ing_parts or all(part in norm_full for part in ing_parts):
            ing_in_doc += 1

        st_raw = occ.get("strength", "")
        st_norm = normalize_text(st_raw)
        for marker in clinical_markers:
            if marker in st_norm:
                clinical_indications_in_strength.append(occ["occurrence_id"])

        st_parts = [
            p.strip()
            for p in re.split(r"[+;]", st_norm)
            if p.strip() and p.strip() != "-"
        ]
        if not st_parts or all(
            part in p_norm or part.replace(" ", "") in p_norm.replace(" ", "")
            for part in st_parts
        ):
            str_in_page += 1

        fm_norm = normalize_text(occ.get("form", ""))
        fm_words = [w for w in re.split(r"[\s/(),+-]+", fm_norm) if len(w) >= 2 and w not in {"de", "da", "do", "ou", "para", "com", "em", "por"}]
        if (
            fm_norm == "-"
            or fm_norm in p_norm
            or fm_norm in rt_norm
            or (fm_words and all(w in p_norm or w in rt_norm for w in fm_words))
        ):
            form_in_page += 1
        else:
            inferred_forms.append(
                {
                    "occurrence_id": occ["occurrence_id"],
                    "source_row_number": occ.get("source_row_number"),
                    "page": page,
                    "active_ingredient": occ.get("active_ingredient"),
                    "strength": occ.get("strength"),
                    "form": occ.get("form"),
                    "raw_text": occ.get("raw_text"),
                }
            )

    return {
        "source_id": source_id,
        "total_occurrences": total,
        "total_pages_in_source": len(pages),
        "raw_txt_chars": len(raw_txt),
        "null_counts": null_counts,
        "pending_reviews": pending_reviews,
        "unresolved_uncertainties": unresolved_uncertainties,
        "clinical_indications_in_strength": clinical_indications_in_strength,
        "raw_text_in_page": raw_text_in_page,
        "raw_text_in_doc": raw_text_in_doc,
        "active_ingredient_in_page": ing_in_page,
        "active_ingredient_in_doc": ing_in_doc,
        "strength_in_page": str_in_page,
        "form_literal_in_page": form_in_page,
        "form_standardized_or_inferred_count": len(inferred_forms),
        "form_standardized_or_inferred_examples": inferred_forms[:15],
    }


def main() -> None:
    occ_path = ROOT / "data/corpus/experimental/occurrences.jsonl"
    f04_occ_path = ROOT / "data/corpus/f04/occurrences.jsonl"

    occs = [
        json.loads(line)
        for line in occ_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    f04_occs = [
        json.loads(line)
        for line in f04_occ_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    assert [o for o in occs if o["source"]["source_id"] == "F04"] == f04_occs, (
        "F04 em data/corpus/experimental/occurrences.jsonl diverge de data/corpus/f04/occurrences.jsonl!"
    )

    by_source: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for o in occs:
        by_source[o["source"]["source_id"]].append(o)

    sources_cfg = {
        "F01": (
            ROOT / "data/raw/F01-rename/rename-2024-2ed.pdf",
            ROOT / "data/raw/F01-rename/rename-2024-2ed-pages.jsonl",
        ),
        "F03": (
            ROOT / "data/raw/F03-reme-df/reme-df-2026-10-29.pdf",
            ROOT / "data/raw/F03-reme-df/reme-df-2026-10-29-pages.jsonl",
        ),
        "F04": (
            ROOT / "data/raw/F04-farmacia-popular/farmacia-popular-elenco-2026-08-31.pdf",
            ROOT / "data/raw/F04-farmacia-popular/farmacia-popular-elenco-2026-08-31-pages.jsonl",
        ),
    }

    results: dict[str, Any] = {}
    for sid, (pdf_path, jsonl_path) in sources_cfg.items():
        pages, raw_txt = load_pages_jsonl(jsonl_path, pdf_path=pdf_path)
        results[sid] = check_source_occurrences(by_source[sid], pages, raw_txt, sid)

    # Specific mandatory assertions requested by user
    occ_by_id = {o["occurrence_id"]: o for o in occs}

    water_ids = [
        "occ-32f9c026384ce1b61a6b03a2",
        "occ-405fcd5d37f8cf3fbb357a41",
        "occ-adec0f7209079b9611b5cfc9",
    ]
    for wid in water_ids:
        assert occ_by_id[wid]["active_ingredient"] == "água para injetáveis", f"Falha em {wid}"

    metf_id = "occ-48e616ae9f8df7c435126c21"
    assert occ_by_id[metf_id]["release_characteristic"] == "ação prolongada"

    f04_plus_ids = {
        "occ-bd645fca4e10b51f38485f06": ("etinilestradiol + levonorgestrel", "0,03mg + 0,15mg"),
        "occ-2e237469ad52f38dc54b786e": ("valerato de estradiol + enantato de noretisterona", "5mg + 50mg"),
        "occ-31f830e7fbb52c0353da2946": ("carbidopa + levodopa", "25mg + 250mg"),
        "occ-e7d83368e51a7cb974fd6bd9": ("cloridrato de benserazida + levodopa", "25mg + 100mg"),
    }
    for pid, (exp_ing, exp_str) in f04_plus_ids.items():
        assert occ_by_id[pid]["active_ingredient"] == exp_ing
        assert occ_by_id[pid]["strength"] == exp_str

    lira_id = "occ-8d4d96cbceb2f870e79e3b16"
    assert occ_by_id[lira_id]["strength"] == "6 mg/mL (sistema de aplicação 3 mL)"
    assert "diabetes" not in occ_by_id[lira_id]["strength"].lower()

    summary = {
        "total_occurrences": len(occs),
        "sources": results,
        "specific_checks": {
            "agua_para_injetaveis_3_ids": True,
            "metformina_f04_acao_prolongada": True,
            "f04_4_combinacoes_com_mais": True,
            "liraglutida_strength_sem_indicacao_clinica": True,
            "zero_null_structured_fields": all(
                sum(r["null_counts"].values()) == 0 for r in results.values()
            ),
            "zero_pending_reviews": all(
                r["pending_reviews"] == 0 for r in results.values()
            ),
            "zero_unresolved_uncertainties": all(
                r["unresolved_uncertainties"] == 0 for r in results.values()
            ),
            "zero_clinical_indications_in_strength": all(
                len(r["clinical_indications_in_strength"]) == 0 for r in results.values()
            ),
        },
    }

    out_json = ROOT / "data/corpus/experimental/validation-report.json"
    out_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
