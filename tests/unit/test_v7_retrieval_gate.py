"""Release v7 chunk identity, retrieval safety and closed test gate."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from rag.config import ROOT
from rag.consolidated import ConsolidatedRelease, load_chunks, search
from rag.consolidated_evaluation import _preflight

RELEASE = ROOT / "data/releases/corpus-consolidado-v7-aprovado-2026-11-11"
CHUNKS = ROOT / "data/derived/chunks/corpus-consolidado-v7-aprovado-2026-11-11"
DATASET = ROOT / "evals/datasets/consolidated_v7_agent_reviewed.jsonl"


@pytest.fixture(scope="module")
def corpus() -> tuple[ConsolidatedRelease, list[dict], dict]:
    release = ConsolidatedRelease.load(RELEASE)
    chunks, manifest = load_chunks(release, CHUNKS)
    return release, chunks, manifest


def test_v7_chunk_links_and_hashes(corpus: tuple) -> None:
    release, chunks, manifest = corpus
    assert release.fingerprint == "8399f37f6664f474c18622d912ad9795f04ec199102724cfafbe6e295eeab20b"
    assert len(chunks) == len(release.evidence) == 2114
    assert len({c["chunk_id"] for c in chunks}) == len(chunks)
    assert manifest["files"]["chunks.jsonl"]["records"] == 2114
    for chunk, evidence in zip(chunks, release.evidence, strict=True):
        assert chunk["evidence_id"] == evidence["evidence_id"]
        assert chunk["occurrence_id"] == evidence["occurrence_id"]
        assert chunk["medicine_id"] == evidence["medicine_id"]
        assert chunk["source"] == evidence["source"]
        assert chunk["release_version"] == release.manifest["release_version"]
        assert chunk["text"].strip()


@pytest.mark.parametrize("mutation", ["hash", "duplicate", "page"])
def test_load_rejects_tampered_chunks(corpus: tuple, tmp_path: Path, mutation: str) -> None:
    release, chunks, manifest = corpus
    copied = [dict(c) for c in chunks]
    meta = json.loads(json.dumps(manifest))
    if mutation == "hash":
        meta["files"]["chunks.jsonl"]["sha256"] = "0" * 64
    elif mutation == "duplicate":
        copied[1]["chunk_id"] = copied[0]["chunk_id"]
    else:
        copied[0]["source"] = {**copied[0]["source"], "page": 999}
    (tmp_path / "manifest.json").write_text(json.dumps(meta), encoding="utf-8")
    (tmp_path / "chunks.jsonl").write_text(
        "".join(json.dumps(c, ensure_ascii=False, sort_keys=True) + "\n" for c in copied),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Manifesto|correspondem"):
        load_chunks(release, tmp_path)


def test_name_only_lists_presentations_without_selecting(corpus: tuple) -> None:
    release, chunks, _ = corpus
    result = search("metformina na RENAME", release, chunks, strategy="lexical")
    assert result["status"] == "ambiguous"
    assert result["evidence"] == []
    assert len(result["candidate_presentations"]) >= 2
    assert "comprimido" in result["message"]


@pytest.mark.parametrize("strategy", ["exact", "lexical"])
def test_presentation_filters_and_source(corpus: tuple, strategy: str) -> None:
    release, chunks, _ = corpus
    result = search(
        "liraglutida 6 mg/mL solução injetável REME-DF", release, chunks, strategy=strategy
    )
    assert result["status"] == "matched"
    assert all(e["source"]["source_id"] == "F03" for e in result["evidence"])
    assert all(e["source"]["page"] == 39 for e in result["evidence"])
    assert result["candidate_chunk_count"] >= 1
    assert result["ranked_chunk_ids"]
    wrong = search(
        "liraglutida 6 mg/g solução injetável REME-DF", release, chunks, strategy=strategy
    )
    assert wrong["status"] == "not_in_scope" and wrong["evidence"] == []


def test_f04_partial_and_release_characteristic(corpus: tuple) -> None:
    release, chunks, _ = corpus
    partial = search(
        "cloridrato de metformina 500mg Farmácia Popular", release, chunks, strategy="exact"
    )
    assert partial["status"] == "ambiguous"
    prolonged = search(
        "cloridrato de metformina 500mg ação prolongada Farmácia Popular",
        release,
        chunks,
        strategy="lexical",
    )
    assert prolonged["status"] == "matched"
    assert prolonged["evidence"][0]["evidence_id"] == "evidence-48e616ae9f8df7c435126c21"
    assert prolonged["medicine"]["exact_presentation_supported"] is False


def test_test_split_remains_closed(corpus: tuple) -> None:
    release, _, _ = corpus
    cases = [json.loads(x) for x in DATASET.read_text(encoding="utf-8").splitlines() if x]
    with pytest.raises(ValueError, match="Teste fechado"):
        _preflight(cases, release, "test", ROOT / "docs/reports/v7-retrieval-review.xlsx")
