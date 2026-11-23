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

def main():
    pages_path = Path("data/raw/F01-rename/rename-2024-2ed-pages.jsonl")
    occurrences_path = Path("data/corpus/experimental/occurrences.jsonl")

    # Load extracted pages
    pages = {}
    with open(pages_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            data = json.loads(line)
            pages[data["page"]] = {
                "text": data["text"],
                "norm_text": normalize_text(data["text"])
            }

    # Combined full doc normalized text
    full_doc_norm = " \n ".join(p["norm_text"] for p in pages.values())

    # Load occurrences
    occurrences = []
    with open(occurrences_path, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f, start=1):
            if not line.strip():
                continue
            data = json.loads(line)
            data["_line_num"] = idx
            occurrences.append(data)

    f01_records = [o for o in occurrences if o.get("source", {}).get("source_id") == "F01"]
    f03_records = [o for o in occurrences if o.get("source", {}).get("source_id") == "F03"]
    f04_records = [o for o in occurrences if o.get("source", {}).get("source_id") == "F04"]

    print("=================================================================")
    print("DETAILED VERIFICATION: F01 (RENAME 2024)")
    print("=================================================================")
    print(f"Total F01 occurrences: {len(f01_records)}")

    # Field-level verification on stated page
    field_stats = {
        "active_ingredient": 0,
        "strength": 0,
        "form": 0,
        "component": 0,
        "atc": 0,
        "all_fields_strict": 0
    }

    mismatches = defaultdict(list)

    for occ in f01_records:
        src_page = occ.get("source", {}).get("page")
        page_norm = pages.get(src_page, {}).get("norm_text", "")

        ing = normalize_text(occ.get("active_ingredient", ""))
        strength = normalize_text(occ.get("strength", ""))
        form = normalize_text(occ.get("form", ""))
        comp = normalize_text(occ.get("component", ""))
        atc = normalize_text(occ.get("atc", ""))

        ing_ok = ing in page_norm if ing else True
        strength_ok = strength in page_norm if strength else True
        form_ok = form in page_norm if form else True
        comp_ok = comp in page_norm if comp else True
        atc_ok = atc in page_norm if atc else True

        if ing_ok: field_stats["active_ingredient"] += 1
        else: mismatches["active_ingredient"].append((occ["occurrence_id"], src_page, occ.get("active_ingredient")))

        if strength_ok: field_stats["strength"] += 1
        else: mismatches["strength"].append((occ["occurrence_id"], src_page, occ.get("strength")))

        if form_ok: field_stats["form"] += 1
        else: mismatches["form"].append((occ["occurrence_id"], src_page, occ.get("form")))

        if comp_ok: field_stats["component"] += 1
        else: mismatches["component"].append((occ["occurrence_id"], src_page, occ.get("component")))

        if atc_ok: field_stats["atc"] += 1
        else: mismatches["atc"].append((occ["occurrence_id"], src_page, occ.get("atc")))

        if ing_ok and strength_ok and form_ok and comp_ok and atc_ok:
            field_stats["all_fields_strict"] += 1

    for k, v in field_stats.items():
        pct = (v / len(f01_records)) * 100
        print(f"  - {k}: {v}/{len(f01_records)} ({pct:.2f}%)")

    if mismatches:
        for field, items in mismatches.items():
            print(f"\nDiscrepancies in {field} ({len(items)} cases):")
            for item in items[:5]:
                print(f"    OccID: {item[0]} | Page {item[1]} | Value: '{item[2]}'")

    print("\n=================================================================")
    print("COMPARISON OF F03 (REME) AGAINST RENAME 2024 PDF")
    print("=================================================================")
    print(f"Total F03 occurrences: {len(f03_records)}")
    f03_ing_in_rename = 0
    f03_unique_ings = set()
    f03_unique_ings_found = set()

    for occ in f03_records:
        ing = normalize_text(occ.get("active_ingredient", ""))
        if ing:
            f03_unique_ings.add(ing)
            if ing in full_doc_norm:
                f03_ing_in_rename += 1
                f03_unique_ings_found.add(ing)

    print(f"F03 occurrences whose active ingredient is in RENAME PDF: {f03_ing_in_rename}/{len(f03_records)} ({(f03_ing_in_rename/len(f03_records))*100:.2f}%)")
    print(f"F03 unique active ingredients in RENAME PDF: {len(f03_unique_ings_found)}/{len(f03_unique_ings)} ({(len(f03_unique_ings_found)/len(f03_unique_ings))*100:.2f}%)")

    print("\n=================================================================")
    print("COMPARISON OF F04 (FARMÁCIA POPULAR - PFPB) AGAINST RENAME 2024 PDF")
    print("=================================================================")
    print(f"Total F04 occurrences: {len(f04_records)}")
    f04_ing_in_rename = 0
    f04_unique_ings = set()
    f04_unique_ings_found = set()

    for occ in f04_records:
        ing = normalize_text(occ.get("active_ingredient", ""))
        if ing:
            f04_unique_ings.add(ing)
            if ing in full_doc_norm:
                f04_ing_in_rename += 1
                f04_unique_ings_found.add(ing)

    print(f"F04 occurrences whose active ingredient is in RENAME PDF: {f04_ing_in_rename}/{len(f04_records)} ({(f04_ing_in_rename/len(f04_records))*100:.2f}%)")
    print(f"F04 unique active ingredients in RENAME PDF: {len(f04_unique_ings_found)}/{len(f04_unique_ings)} ({(len(f04_unique_ings_found)/len(f04_unique_ings))*100:.2f}%)")

if __name__ == "__main__":
    main()
