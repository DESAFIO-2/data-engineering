"""Unit tests for v10 additive normalization rules and vocabularies (offline, no DVC)."""

from __future__ import annotations

import json

import pytest

from rag.config import ROOT
from rag.normalization import (
    RuleTrace,
    Vocabulary,
    canonical_form,
    canonical_ingredient,
    canonical_release,
    canonical_strength,
    check_bundle,
    fold,
    identity_key,
    load_vocabulary,
    normalize_occurrence,
    parse_atc,
    parse_channel,
    vocabulary_bundle,
)
from scripts.archive.releases.v10 import build_v10_vocab

VOCAB_DIR = ROOT / "data/vocab"


@pytest.fixture(scope="module")
def vocab() -> Vocabulary:
    return load_vocabulary(VOCAB_DIR)


def test_real_corpus_cases_normalize_cleanly(vocab: Vocabulary) -> None:
    cases = [
        ("0,25mcg", "0,25 mcg", "numeric"),
        ("100ui/ml", "100 UI/mL", "numeric"),
        ("50mg/g", "50 mg/g", "numeric"),
        ("70 %", "70%", "numeric"),
        ("1.250 mg + 400 UI", "1.250 mg + 400 UI", "combination"),
        (
            "20 a 30 mg de derivados (dose diária)",
            "20 a 30 mg de derivados (dose diária)",
            "textual",
        ),
        ("-", None, "absent"),
    ]
    for raw, expected, expected_kind in cases:
        trace = RuleTrace()
        value, kind = canonical_strength(raw, vocab, trace)
        assert value == expected
        assert kind == expected_kind


def test_strength_pdf_artifact_fix_sets_flag(vocab: Vocabulary) -> None:
    trace = RuleTrace()
    value, kind = canonical_strength(
        "lactato de sódio 3 mg/mL + cloreto de potássio 0/ ,3 mg/mL", vocab, trace
    )
    assert value == "lactato de sódio 3 mg/mL + cloreto de potássio 0,3 mg/mL"
    assert kind == "textual"
    assert "strength_pdf_artifact_fix" in trace.applied
    assert "needs_pdf_check" in trace.flags


def test_ingredient_variants_resolve_deterministically(vocab: Vocabulary) -> None:
    for raw, expected in (
        ("alfainterferona 2B", "alfainterferona 2b"),
        ("valproato de sodio", "valproato de sódio"),
        ("metformina (cloridrato)", "cloridrato de metformina"),
        ("amiodarona (cloridrato)", "cloridrato de amiodarona"),
        ("sulfato de sulfametoxazol +trimetoprima", "sulfato de sulfametoxazol + trimetoprima"),
    ):
        trace = RuleTrace()
        assert canonical_ingredient(raw, vocab, trace) == expected


def test_canonical_form_splits_package_release_and_specifications(vocab: Vocabulary) -> None:
    t1 = RuleTrace()
    f1 = canonical_form("frasco-ampola", vocab, t1)
    assert (
        f1["form"] is None
        and f1["package"] == "frasco-ampola"
        and f1["form_kind"] == "package_only"
    )

    t2 = RuleTrace()
    f2 = canonical_form("pó frasco ou envelope", vocab, t2)
    assert f2["form"] == "pó" and f2["package"] == "frasco ou envelope"

    t3 = RuleTrace()
    f3 = canonical_form("solução injetável 10 mL", vocab, t3)
    assert f3["form"] == "solução injetável" and f3["package"] == "10 mL"

    t4 = RuleTrace()
    f4 = canonical_form("implante subcutâneo (seringa preenchida)", vocab, t4)
    assert f4["form"] == "implante subcutâneo" and f4["package"] == "seringa preenchida"

    t5 = RuleTrace()
    f5 = canonical_form("comprimido ou cápsula ou drágea liberação prolongada", vocab, t5)
    assert f5["form"] == "comprimido ou cápsula ou drágea"
    assert f5["form_release"] == "liberação prolongada"

    # Keep mixed-release alternatives distinct rather than collapsing to A ou A
    t6 = RuleTrace()
    f6 = canonical_form(
        "comprimido revestido ou comprimido revestido de liberação retardada", vocab, t6
    )
    assert f6["form"] == "comprimido revestido ou comprimido revestido de liberação retardada"

    t7 = RuleTrace()
    f7 = canonical_form("160 mm x 49 mm", vocab, t7)
    assert (
        f7["form"] is None
        and f7["specification"] == "160 mm x 49 mm"
        and f7["form_kind"] == "specification"
    )


def test_canonical_release_separates_patch_delivery_rate() -> None:
    trace = RuleTrace()
    rel, rate = canonical_release("liberação de 9,5 mg/24h", None, trace)
    assert rel is None
    assert rate == "liberação de 9,5 mg/24h"
    assert "release_rate_to_strength_note" in trace.applied


def test_parse_atc_handles_footnotes_partials_multiple_and_continua() -> None:
    t1 = RuleTrace()
    assert parse_atc("C10AW5006(2)", t1) == {
        "codes": ["C10AW5006"],
        "primary": "C10AW5006",
        "kind": "herbal",
        "levels": [5],
        "note": "nota (2)",
    }
    t2 = RuleTrace()
    assert parse_atc("B02BD04 continua", t2)["codes"] == ["B02BD04"]
    assert "atc_parser_artifact" in t2.flags

    t3 = RuleTrace()
    assert parse_atc("J04BA01 e J04BA51", t3)["codes"] == ["J04BA01", "J04BA51"]
    t4 = RuleTrace()
    assert parse_atc("NC", t4) == {
        "codes": [],
        "primary": None,
        "kind": "not_classified",
        "levels": [],
        "note": "NC",
    }
    t5 = RuleTrace()
    assert parse_atc("A12AX", t5)["levels"] == [4]


def test_parse_channel_joins_hyphens_splits_notes_and_assigns_codes(vocab: Vocabulary) -> None:
    raw = (
        "UBS - Unidades de Referência* (farmácia ambulatorial), uso hospitalar e atendimento "
        "pré- hospitalar (SAMU) *UBS Dispensadoras de Medicamentos Sujeitos à Controle Especial."
    )
    trace = RuleTrace()
    res = parse_channel(raw, vocab, trace)
    assert "pré-hospitalar" in res["text"]
    assert "*" not in res["text"]
    assert res["codes"] == [
        "UBS_FARMACIA_AMBULATORIAL",
        "UBS_UNIDADE_REFERENCIA",
        "HOSPITALAR",
        "SAMU",
    ]
    assert len(res["notes"]) == 1
    assert "channel_unmapped" not in trace.flags


def test_identity_key_guards_metformin_absent_forms_and_textual_strengths(
    vocab: Vocabulary,
) -> None:
    occ_reg = {
        "active_ingredient": "cloridrato de metformina",
        "strength": "500mg",
        "form": "-",
        "release_characteristic": None,
    }
    occ_prol = {
        "active_ingredient": "cloridrato de metformina",
        "strength": "500mg",
        "form": "-",
        "release_characteristic": "ação prolongada",
    }
    assert identity_key(normalize_occurrence(occ_reg, vocab), ["F04"]) != identity_key(
        normalize_occurrence(occ_prol, vocab), ["F04"]
    )
    # Absent form never merges across F01 and F04
    occ_f01 = {**occ_reg, "form": "-"}
    assert identity_key(normalize_occurrence(occ_f01, vocab), ["F01"]) != identity_key(
        normalize_occurrence(occ_reg, vocab), ["F04"]
    )
    # Textual strength requires exact literal equality
    t_a = normalize_occurrence(
        {"active_ingredient": "planta x", "strength": "30 mg de ácido gálico", "form": "cápsula"},
        vocab,
    )
    t_b = normalize_occurrence(
        {"active_ingredient": "planta x", "strength": "30 mg de acido gálico", "form": "cápsula"},
        vocab,
    )
    assert t_a["strength_kind"] == "textual" and t_b["strength_kind"] == "textual"
    assert identity_key(t_a, ["F01"]) != identity_key(t_b, ["F01"])


def test_vocab_bundle_and_ingredients_manifest_are_in_sync() -> None:
    bundle = vocabulary_bundle(VOCAB_DIR)
    assert check_bundle(bundle, VOCAB_DIR) == []
    if (
        ROOT / "data/releases/corpus-consolidado-v9-aprovado-2026-11-12/occurrences.jsonl"
    ).exists():
        assert (VOCAB_DIR / "ingredients.json").read_bytes() == build_v10_vocab.render()
    assert fold("50mg/ml") == "50 mg/ml"
    assert fold("100u") == "100 u"
    assert json.loads((VOCAB_DIR / "units.json").read_text())["units"]["ui"] == "UI"
