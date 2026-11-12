"""New development fixtures for documentary presentation identity.

Synthetic families intentionally differ from the frozen v9 test families.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from rag.consolidated import search


def corpus(*presentations: tuple[str, str, str, str | None, str]):
    catalog = []
    evidence = []
    chunks = []
    for index, (name, strength, form, characteristic, source_id) in enumerate(
        presentations, 1
    ):
        medicine_id = f"synthetic-med-{index}"
        evidence_id = f"synthetic-evidence-{index}"
        source = {"source_id": source_id, "page": index, "url": "https://example.org/pdf"}
        catalog.append(
            {
                "active_ingredient": name,
                "strength": strength,
                "form": form,
                "release_characteristic": characteristic,
                "medicine_id": medicine_id,
                "source_ids": [source_id],
            }
        )
        evidence.append({"evidence_id": evidence_id, "medicine_id": medicine_id, "source": source})
        chunks.append(
            {
                "chunk_id": f"synthetic-chunk-{index}",
                "medicine_id": medicine_id,
                "evidence_id": evidence_id,
                "source": source,
                "text": f"{name} {strength} {form}",
            }
        )
    return SimpleNamespace(catalog=catalog, evidence=evidence, occurrences=[]), chunks


@pytest.mark.parametrize("strategy", ["exact", "lexical"])
def test_textual_strength_with_optional_article(strategy: str) -> None:
    release, chunks = corpus(
        (
            "produto homeopático alfa",
            "Conforme Farmacopeia Homeopática Brasileira vigente",
            "Conforme Farmacopeia Homeopática Brasileira vigente",
            None,
            "F01",
        )
    )
    result = search(
        "Na RENAME há produto homeopático alfa conforme a Farmacopeia "
        "Homeopática Brasileira vigente?",
        release,
        chunks,
        strategy=strategy,
    )
    assert result["status"] == "matched"


@pytest.mark.parametrize("strategy", ["exact", "lexical"])
def test_delayed_release_selects_only_delayed_presentation(strategy: str) -> None:
    release, chunks = corpus(
        ("extrato vegetal alfa", "50 mg", "comprimido", None, "F01"),
        (
            "extrato vegetal alfa",
            "50 mg",
            "comprimido de liberação retardada",
            "liberação retardada",
            "F01",
        ),
    )
    delayed = search(
        "Na RENAME há extrato vegetal alfa 50 mg comprimido de liberação retardada?",
        release,
        chunks,
        strategy=strategy,
    )
    assert delayed["status"] == "matched"
    assert [e["medicine_id"] for e in delayed["evidence"]] == ["synthetic-med-2"]
    unspecified = search("extrato vegetal alfa 50 mg comprimido RENAME", release, chunks)
    assert unspecified["status"] == "ambiguous" and unspecified["evidence"] == []


@pytest.mark.parametrize("strategy", ["exact", "lexical"])
def test_range_and_container_preserve_dose_and_source(strategy: str) -> None:
    release, chunks = corpus(
        (
            "imunoglobulina teste alfa",
            "de 150 mcg a 200 mcg frasco - ampola ou seringa preenchida",
            "solução injetável",
            None,
            "F03",
        )
    )
    good = search(
        "Na REME-DF há imunoglobulina teste alfa solução injetável de 150 mcg "
        "a 200 mcg em frasco-ampola?",
        release,
        chunks,
        strategy=strategy,
    )
    assert good["status"] == "matched"
    for question in (
        "REME-DF imunoglobulina teste alfa solução injetável de 150 mg a 200 mg",
        "REME-DF imunoglobulina teste alfa solução injetável de 150 mcg a 250 mcg",
        "RENAME imunoglobulina teste alfa solução injetável de 150 mcg a 200 mcg",
    ):
        assert search(question, release, chunks, strategy=strategy)["evidence"] == []


@pytest.mark.parametrize("strategy", ["exact", "lexical"])
def test_volume_and_container_preserve_volume(strategy: str) -> None:
    release, chunks = corpus(
        (
            "solução eletrolítica alfa",
            "bolsa ou frasco 750 mL (sistema fechado de infusão)",
            "solução injetável",
            None,
            "F03",
        )
    )
    assert search(
        "REME-DF solução eletrolítica alfa injetável em bolsa de 750 mL "
        "sistema fechado de infusão",
        release,
        chunks,
        strategy=strategy,
    )["status"] == "matched"
    assert search(
        "REME-DF solução eletrolítica alfa injetável em bolsa de 500 mL",
        release,
        chunks,
        strategy=strategy,
    )["evidence"] == []


@pytest.mark.parametrize("strategy", ["exact", "lexical"])
def test_interleaved_association_keeps_component_doses(strategy: str) -> None:
    release, chunks = corpus(
        ("composto alfa + composto beta", "0,03 mg + 0,15 mg", "-", None, "F04")
    )
    assert search(
        "Na Farmácia Popular há composto alfa 0,03mg + composto beta 0,15mg?",
        release,
        chunks,
        strategy=strategy,
    )["status"] == "matched"
    for question in (
        "Farmácia Popular composto alfa 0,15mg + composto beta 0,03mg",
        "Farmácia Popular composto alfa 0,03mg + composto beta 0,20mg",
    ):
        assert search(question, release, chunks, strategy=strategy)["evidence"] == []
