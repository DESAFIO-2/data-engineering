"""Safety boundaries for the approved consolidated corpus."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest

from rag.consolidated import ConsolidatedRelease, chunk_for, load_chunks, search, strength_matches

ROOT = Path(__file__).resolve().parents[2]
RELEASE = ROOT / "data/releases/corpus-consolidado-v5-aprovado-2026-11-10"
CHUNKS = ROOT / "data/derived/chunks/corpus-consolidado-v5-aprovado-2026-11-10"


def test_chunks_follow_approved_evidence_and_exclude_blank() -> None:
    release = ConsolidatedRelease.load(RELEASE)
    chunks, _ = load_chunks(release, CHUNKS)
    assert len(chunks) == len(release.evidence) == 2114
    assert len({c["chunk_id"] for c in chunks}) == len(chunks)
    assert all(
        c == chunk_for(e, release.manifest["release_version"])
        for c, e in zip(chunks, release.evidence, strict=True)
    )
    assert all(c["occurrence_id"] != "occ-dd3666cce6867d6246aae72f" for c in chunks)
    assert sum("Descrição na REME-DF" in c["text"] for c in chunks) == 1077
    assert sum("Indicação no elenco" in c["text"] for c in chunks) == 41


def test_release_hash_change_is_rejected(tmp_path: Path) -> None:
    folder = tmp_path / "release"
    shutil.copytree(RELEASE, folder)
    path = folder / "domain_review.json"
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(ValueError, match="Hash divergente"):
        ConsolidatedRelease.load(folder)


def test_wrong_strength_and_unsupported_requests_do_not_retrieve() -> None:
    release = ConsolidatedRelease.load(RELEASE)
    chunks, _ = load_chunks(release, CHUNKS)
    wrong = search("sinvastatina 99999 mg comprimido consta na REME DF?", release, chunks)
    stock = search("A farmácia tem sinvastatina hoje?", release, chunks)
    dosage = search("Qual dose de varfarina devo tomar?", release, chunks)
    assert wrong["status"] == "not_in_scope" and wrong["evidence"] == []
    assert stock["status"] == "unsupported" and stock["evidence"] == []
    assert dosage["status"] == "unsupported" and dosage["evidence"] == []


def test_cross_medicine_vector_results_cannot_be_returned() -> None:
    release = ConsolidatedRelease.load(RELEASE)
    chunks, _ = load_chunks(release, CHUNKS)
    case = next(
        c
        for c in (
            json.loads(s)
            for s in (ROOT / "evals/datasets/consolidated_v5_draft.jsonl").read_text().splitlines()
        )
        if c["expected_status"] == "matched" and "sinvastatina" in c["question"].lower()
    )

    class WrongStore:
        def similarity_search(self, _question: str, **_kwargs: object) -> list[SimpleNamespace]:
            return [SimpleNamespace(metadata={"chunk_id": "chunk-unrelated"})]

    result = search(case["question"], release, chunks, store=WrongStore(), strategy="hybrid")
    assert result["status"] == "matched"
    assert all(e["medicine_id"] in result["equivalent_medicine_ids"] for e in result["evidence"])


def test_strength_followed_by_sentence_comma_keeps_exact_dose() -> None:
    assert strength_matches("Existe entacapona 200 mg, comprimido?", "200 mg", "entacapona")
    assert not strength_matches("Existe entacapona 20 mg, comprimido?", "200 mg", "entacapona")
    assert not strength_matches("Existe entacapona 200 mg,5?", "200 mg", "entacapona")
