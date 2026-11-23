"""User-reported concentration/device and spelling regressions."""

from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace
from typing import Any

import pytest

import rag.consolidated_chat as chat
from rag.config import ROOT, Settings
from rag.consolidated import ConsolidatedRelease, load_chunks, normalize, search, strength_matches

pytestmark = pytest.mark.dvc


@pytest.fixture(scope="module")
def corpus() -> tuple[ConsolidatedRelease, list[dict[str, Any]], dict[str, Any]]:
    release = ConsolidatedRelease.load(
        ROOT / "data/releases/corpus-consolidado-v5-aprovado-2026-11-10"
    )
    chunks, manifest = load_chunks(
        release, ROOT / "data/derived/chunks" / release.manifest["release_version"]
    )
    return release, chunks, manifest


@pytest.mark.parametrize("strength", ["6mg/ml", "6 mg/ml", "6 mg/mL", "6 mg / mL"])
@pytest.mark.parametrize("verb", ["consta", "contsa"])
def test_liraglutide_concentration_without_device(corpus: Any, strength: str, verb: str) -> None:
    release, chunks, _ = corpus
    question = f"O que {verb} na REME-DF sobre liraglutida {strength} solução injetável?"
    result = search(question, release, chunks, strategy="lexical")
    assert result["status"] == "matched"
    assert result["medicine"]["strength"] == "6 mg/mL (sistema de aplicação 3 mL)"
    assert len(result["evidence"]) == 1
    assert result["evidence"][0]["source"]["source_id"] == "F03"
    assert result["evidence"][0]["source"]["page"] == 39
    assert "sistema de aplicação 3 mL" in result["message"]


@pytest.mark.parametrize(
    "strength",
    ["6 mg", "6 mg/g", "16 mg/mL", "60 mg/mL", "3 mg/mL", "6 mg/mL (sistema de aplicação 1 mL)"],
)
def test_wrong_units_concentration_or_device_do_not_match(corpus: Any, strength: str) -> None:
    release, chunks, _ = corpus
    result = search(f"liraglutida {strength} solução injetável REME-DF", release, chunks)
    assert result["status"] == "not_in_scope" and result["evidence"] == []


def test_multiple_devices_ask_instead_of_selecting_longest(corpus: Any) -> None:
    release, chunks, _ = corpus
    medicine = next(m for m in release.catalog if m["active_ingredient"] == "liraglutida")
    alternate = {
        **medicine,
        "medicine_id": "test-other-device",
        "strength": "6 mg/mL (sistema de aplicação 10 mL)",
    }
    release = replace(release, catalog=[medicine, alternate])
    result = search("liraglutida 6 mg/mL solução injetável REME-DF", release, chunks)
    assert result["status"] == "ambiguous" and result["evidence"] == []
    assert "10 mL" in result["message"] and "3 mL" in result["message"]


def test_chemical_equivalence_annotation_is_not_discarded() -> None:
    strength = "1.250 mg (equivalente a 500 mg de cálcio elementar)"
    assert not strength_matches(normalize("carbonato de cálcio 500 mg comprimido"), strength)


@pytest.mark.parametrize("strength", ["6mg/ml", "6 mg/ml"])
def test_misspelling_suggests_confirmation_without_evidence(corpus: Any, strength: str) -> None:
    release, chunks, _ = corpus
    result = search(
        f"O que contsa na reme-df sobre liraglutid {strength} solução injetável?", release, chunks
    )
    assert result["status"] == "ambiguous" and result["evidence"] == []
    assert "Você quis dizer liraglutida?" in result["message"]
    assert search(result["suggested_question"], release, chunks)["status"] == "matched"


def test_chat_confirms_typo_then_answers_with_source(
    corpus: Any, monkeypatch: Any, capsys: Any
) -> None:
    release, chunks, manifest = corpus
    settings = Settings("", "unused", "unused", release.folder, ROOT / "missing", 5)
    messages = iter(
        ["O que contsa na reme-df sobre liraglutid 6mg/ml solução injetável?", "sim", "sair"]
    )
    monkeypatch.setattr("builtins.input", lambda _: next(messages))
    args = SimpleNamespace(documental=True, strategy="lexical", show_context=False)
    assert chat.chat(args, settings, release, chunks, manifest) == 0
    output = capsys.readouterr().out
    assert "Você quis dizer liraglutida?" in output
    assert "página 39" in output and "sistema de aplicação 3 mL" in output


def test_liraglutide_clarifications_across_turns(corpus: Any) -> None:
    release, chunks, _ = corpus
    state = chat.ConversationState()
    for question, expected in [
        ("liraglutida REME-DF", "ambiguous"),
        ("6mg/ml", "ambiguous"),
        ("solução injetável", "matched"),
    ]:
        result = search(state.resolve(question, release), release, chunks)
        assert result["status"] == expected
