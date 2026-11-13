import json
from collections import Counter
from pathlib import Path
from typing import Any

import pytest

from rag.corpus import fields, split_pf_heading, split_text
from rag.experimental import Corpus
from rag.table_extract import reme_rows

ROOT = Path(__file__).resolve().parents[2]


def test_chunks_preserve_offsets_cover_text_and_respect_bound() -> None:
    text = ("Medicamento, concentração e forma.\n" * 250) + "fim"
    windows = split_text(text)
    covered: set[int] = set()
    for start, end, part in windows:
        assert part == text[start:end]
        assert len(part) <= 2000
        covered.update(range(start, end))
    assert covered == set(range(len(text)))
    assert all(left[1] - right[0] <= 240 for left, right in zip(windows, windows[1:], strict=False))
    with pytest.raises(ValueError):
        split_text(text, 20, 20)


def test_explicit_composite_strength_is_preserved_literally() -> None:
    name, strength, form = fields("losartana 50 mg + hidroclorotiazida 12,5 mg comprimido")
    assert name == "losartana + hidroclorotiazida"
    assert strength == "50 mg + 12,5 mg"
    assert form == "comprimido"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            "abatacepte pó liofilizo injetável 250mg frasco ampola + seringa descartável",
            ("abatacepte", "250mg", "pó liofilizado injetável"),
        ),
        (
            "acetato de medroxiprogesterona + estradiol cipionato 25 mg + 5 mg suspensão injetável",
            (
                "acetato de medroxiprogesterona + estradiol cipionato",
                "25 mg + 5 mg",
                "suspensão injetável",
            ),
        ),
        (
            "aciclovir pomada oftálmica 0,03 g/g bisnaga 4,5 g",
            ("aciclovir", "0,03 g/g", "pomada oftálmica"),
        ),
        (
            "ácido paraminossalicilico 4 g granulado revestido - tuberculose",
            ("ácido paraminossalicilico", "4 g", "granulado revestido"),
        ),
        (
            "ácido zoledrônico 4 mg pó liofilizado ou solução injetável frasco ou ampola",
            ("ácido zoledrônico", "4 mg", "pó liofilizado ou solução injetável"),
        ),
    ],
)
def test_reme_fields_preserve_rejected_patterns(text: str, expected: tuple[Any, ...]) -> None:
    assert fields(text) == expected


def test_reme_stacked_codes_are_separated_and_internal_spaces_removed() -> None:
    source = ROOT / "data/raw/F03-reme-df/reme-df-2026-10-29.pdf"
    rows = {row["row_number"]: row for row in reme_rows(source)}
    assert rows[3]["code"] == "MS11126"
    assert rows[10]["code"] == "20833"
    assert rows[25]["code"] == "MS19578, MS38515, MS38516, MS010"


def test_farmacia_popular_compound_names_keep_both_ingredients_and_strengths() -> None:
    assert fields("etinilestradiol 0,03mg + levonorgestrel 0,15mg") == (
        "etinilestradiol + levonorgestrel",
        "0,03mg + 0,15mg",
        None,
    )


def test_farmacia_popular_heading_is_separate_from_medicine_and_supply() -> None:
    assert split_pf_heading("OSTEOPOROSE\u00a0 alendronato de sódio 70mg\u00a0") == (
        "alendronato de sódio 70mg",
        "OSTEOPOROSE",
    )
    assert fields("absorvente higiênico") == ("absorvente higiênico", None, None)


def test_frozen_corpus_has_full_primary_reme_sequence_and_provenance() -> None:
    corpus = Corpus.load(ROOT / "data/corpus/experimental")
    counts = Counter(row["source"]["source_id"] for row in corpus.occurrences)
    assert counts == {"F01": 996, "F03": 1078, "F04": 41}
    reme = [row for row in corpus.occurrences if row["source"]["source_id"] == "F03"]
    assert sorted(row["source_row_number"] for row in reme) == list(range(1, 1079))
    assert max(len(chunk["text"]) for chunk in corpus.chunks) <= 2000
    assert {row["review_status"] for row in corpus.occurrences} == {"approved"}
    assert all(
        row.get("active_ingredient") and row.get("strength") and row.get("form")
        for row in corpus.occurrences
    )
    assert all(not row.get("uncertainties") for row in corpus.occurrences)
    assert all(chunk["source"]["sha256"] and chunk["source"]["page"] for chunk in corpus.chunks)
    f04 = {
        row["source_row_number"]: row
        for row in corpus.occurrences
        if row["source"]["source_id"] == "F04"
    }
    assert f04[10]["release_characteristic"] == "ação prolongada"
    assert f04[26]["active_ingredient"] == "etinilestradiol + levonorgestrel"
    assert f04[26]["strength"] == "0,03mg + 0,15mg"
    assert f04[28]["active_ingredient"] == "valerato de estradiol + enantato de noretisterona"
    assert f04[33]["strength"] == "25mg + 250mg"
    assert f04[34]["strength"] == "25mg + 100mg"
    assert "OSTEOPOROSE" in f04[29]["raw_text"]
    assert f04[29]["active_ingredient"] == "alendronato de sódio"
    assert f04[29]["strength"] == "70mg"
    assert "DIABETES MELLITUS + DOENÇA CARDIOVASCULAR" in f04[40]["raw_text"]
    assert f04[41]["supply_name"] == "absorvente higiênico"
    assert f04[41]["active_ingredient"] == "absorvente higiênico"
    assert f04[42]["supply_name"] == "fralda geriátrica"
    assert f04[42]["active_ingredient"] == "fralda geriátrica"
    # Shared-name cells in the visually checked RENAME table must keep both strengths.
    ambrisentana = [
        row
        for row in corpus.occurrences
        if row["source"]["source_id"] == "F01"
        and row["source"]["page"] == 43
        and row["active_ingredient"] == "ambrisentana"
    ]
    assert {row["strength"] for row in ambrisentana} == {"5 mg", "10 mg"}
    report = json.loads((corpus.folder / "report.json").read_text(encoding="utf-8"))
    assert report["human_verified"] is True
    assert sum(source["pages_preserved"] for source in report["sources"].values()) == 366
