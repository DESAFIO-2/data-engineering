import json
import sys
import unicodedata
from pathlib import Path
from collections import defaultdict

def normalize_text(s: str) -> str:
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower()
    return " ".join(s.split())

def extract_pdf(pdf_path: Path, txt_path: Path, jsonl_path: Path):
    if txt_path.exists() and jsonl_path.exists():
        print(f"\n=======================================================")
        print(f"Using existing extraction: {txt_path.name} & {jsonl_path.name}")
        print(f"=======================================================")
        pages = {}
        total_chars = 0
        total_words = 0
        with open(jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    rec = json.loads(line)
                    pages[rec["page"]] = rec["text"]
                    total_chars += rec.get("char_count", len(rec["text"]))
                    total_words += rec.get("word_count", len(rec["text"].split()))
        print(f"Pages: {len(pages)}")
        print(f"Total chars: {total_chars}")
        print(f"Total words: {total_words}")
        return pages

    import fitz
    print(f"\n=======================================================")
    print(f"Extracting: {pdf_path.name}")
    print(f"=======================================================")
    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    total_chars = 0
    total_words = 0

    with open(txt_path, "w", encoding="utf-8") as f_txt, open(jsonl_path, "w", encoding="utf-8") as f_jsonl:
        for i, page in enumerate(doc, start=1):
            text = page.get_text("text")
            total_chars += len(text)
            total_words += len(text.split())

            # Write TXT
            f_txt.write(f"--- PÁGINA {i} DE {total_pages} ---\n\n")
            f_txt.write(text.strip())
            f_txt.write("\n\n")

            # Write JSONL
            page_record = {
                "page": i,
                "total_pages": total_pages,
                "char_count": len(text),
                "word_count": len(text.split()),
                "text": text
            }
            f_jsonl.write(json.dumps(page_record, ensure_ascii=False) + "\n")

    print(f"Total pages: {total_pages}")
    print(f"Total characters: {total_chars:,}")
    print(f"Total words: {total_words:,}")
    print(f"TXT saved: {txt_path} ({txt_path.stat().st_size:,} bytes)")
    print(f"JSONL saved: {jsonl_path} ({jsonl_path.stat().st_size:,} bytes)")
    return total_pages, total_chars, total_words

def load_pages(jsonl_path: Path):
    pages = {}
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            data = json.loads(line)
            pages[data["page"]] = {
                "text": data["text"],
                "norm_text": normalize_text(data["text"])
            }
    return pages

def validate_f03(pages, occurrences):
    print(f"\n=======================================================")
    print(f"VALIDATING F03 (REME-DF) RECORDS")
    print(f"=======================================================")
    f03_records = [o for o in occurrences if o.get("source", {}).get("source_id") == "F03"]
    print(f"Total F03 records in occurrences.jsonl: {len(f03_records)}")

    # Sample a record to inspect fields
    if f03_records:
        sample = f03_records[0]
        print("\nSample F03 record keys:", list(sample.keys()))
        print("Sample F03 content:", {
            "active_ingredient": sample.get("active_ingredient"),
            "strength": sample.get("strength"),
            "form": sample.get("form"),
            "source_page": sample.get("source", {}).get("page"),
            "raw_text": sample.get("raw_text")
        })

    field_stats = defaultdict(int)
    mismatches = defaultdict(list)

    for occ in f03_records:
        src_page = occ.get("source", {}).get("page")
        page_norm = pages.get(src_page, {}).get("norm_text", "")

        ing = normalize_text(occ.get("active_ingredient", ""))
        strength = normalize_text(occ.get("strength", ""))
        form = normalize_text(occ.get("form", ""))

        ing_ok = (ing in page_norm) if ing else True
        strength_ok = (strength in page_norm) if strength else True
        form_ok = (form in page_norm) if form else True

        if ing_ok: field_stats["active_ingredient"] += 1
        else: mismatches["active_ingredient"].append((occ["occurrence_id"], src_page, occ.get("active_ingredient")))

        if strength_ok: field_stats["strength"] += 1
        else: mismatches["strength"].append((occ["occurrence_id"], src_page, occ.get("strength")))

        if form_ok: field_stats["form"] += 1
        else: mismatches["form"].append((occ["occurrence_id"], src_page, occ.get("form")))

        if ing_ok and strength_ok and form_ok:
            field_stats["all_fields_strict"] += 1

    print("\nField-level match results against cited source page:")
    for k in ["active_ingredient", "strength", "form", "all_fields_strict"]:
        v = field_stats[k]
        pct = (v / len(f03_records)) * 100
        print(f"  - {k}: {v}/{len(f03_records)} ({pct:.2f}%)")

    if mismatches:
        for field, items in mismatches.items():
            print(f"\nDiscrepancies in {field} ({len(items)} cases):")
            for item in items[:5]:
                print(f"    OccID: {item[0]} | Page {item[1]} | Value: '{item[2]}'")

def validate_f04(pages, occurrences):
    print(f"\n=======================================================")
    print(f"VALIDATING F04 (FARMÁCIA POPULAR - PFPB) RECORDS")
    print(f"=======================================================")
    f04_records = [o for o in occurrences if o.get("source", {}).get("source_id") == "F04"]
    print(f"Total F04 records in occurrences.jsonl: {len(f04_records)}")

    if f04_records:
        sample = f04_records[0]
        print("\nSample F04 record keys:", list(sample.keys()))
        print("Sample F04 content:", {
            "active_ingredient": sample.get("active_ingredient"),
            "strength": sample.get("strength"),
            "form": sample.get("form"),
            "source_page": sample.get("source", {}).get("page"),
            "raw_text": sample.get("raw_text")
        })

    field_stats = defaultdict(int)
    mismatches = defaultdict(list)

    for occ in f04_records:
        src_page = occ.get("source", {}).get("page")
        page_norm = pages.get(src_page, {}).get("norm_text", "")

        ing = normalize_text(occ.get("active_ingredient", ""))
        strength = normalize_text(occ.get("strength", ""))
        form = normalize_text(occ.get("form", ""))

        ing_ok = (ing in page_norm) if ing else True
        strength_ok = (strength in page_norm) if strength else True
        form_ok = (form in page_norm) if form else True

        if ing_ok: field_stats["active_ingredient"] += 1
        else: mismatches["active_ingredient"].append((occ["occurrence_id"], src_page, occ.get("active_ingredient")))

        if strength_ok: field_stats["strength"] += 1
        else: mismatches["strength"].append((occ["occurrence_id"], src_page, occ.get("strength")))

        if form_ok: field_stats["form"] += 1
        else: mismatches["form"].append((occ["occurrence_id"], src_page, occ.get("form")))

        if ing_ok and strength_ok and form_ok:
            field_stats["all_fields_strict"] += 1

    print("\nField-level match results against cited source page:")
    for k in ["active_ingredient", "strength", "form", "all_fields_strict"]:
        v = field_stats[k]
        pct = (v / len(f04_records)) * 100
        print(f"  - {k}: {v}/{len(f04_records)} ({pct:.2f}%)")

    if mismatches:
        for field, items in mismatches.items():
            print(f"\nDiscrepancies in {field} ({len(items)} cases):")
            for item in items[:5]:
                print(f"    OccID: {item[0]} | Page {item[1]} | Value: '{item[2]}'")

def main():
    f03_pdf = Path("data/raw/F03-reme-df/reme-df-2026-10-29.pdf")
    f03_txt = Path("data/raw/F03-reme-df/reme-df-2026-10-29.txt")
    f03_jsonl = Path("data/raw/F03-reme-df/reme-df-2026-10-29-pages.jsonl")

    f04_pdf = Path("data/raw/F04-farmacia-popular/farmacia-popular-elenco-2026-08-31.pdf")
    f04_txt = Path("data/raw/F04-farmacia-popular/farmacia-popular-elenco-2026-08-31.txt")
    f04_jsonl = Path("data/raw/F04-farmacia-popular/farmacia-popular-elenco-2026-08-31-pages.jsonl")

    # Extract PDFs
    extract_pdf(f03_pdf, f03_txt, f03_jsonl)
    extract_pdf(f04_pdf, f04_txt, f04_jsonl)

    # Load occurrences
    occurrences_path = Path("data/corpus/experimental/occurrences.jsonl")
    occurrences = []
    with open(occurrences_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            occurrences.append(json.loads(line))

    # Validate F03
    f03_pages = load_pages(f03_jsonl)
    validate_f03(f03_pages, occurrences)

    # Validate F04
    f04_pages = load_pages(f04_jsonl)
    validate_f04(f04_pages, occurrences)

if __name__ == "__main__":
    main()
