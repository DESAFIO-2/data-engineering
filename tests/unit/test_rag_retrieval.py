from pathlib import Path
from types import SimpleNamespace
from typing import Any

from rag.release import Release
from rag.retrieval import match_medicine, retrieve, retrieve_lexical

RELEASE = Path(__file__).resolve().parents[2] / "data/releases/rag-lote-1-aprovado-2026-11-05"


class FakeStore:
    def __init__(self, evidence: list[dict[str, Any]]) -> None:
        self.evidence = evidence
        self.filter_seen: dict[str, str] | None = None

    def similarity_search(
        self, query: str, k: int, filter: dict[str, str]
    ) -> list[SimpleNamespace]:
        self.filter_seen = filter
        return [
            SimpleNamespace(metadata={"evidence_id": e["evidence_id"]})
            for e in self.evidence
            if e["medicine_id"] == filter["medicine_id"]
        ][:k]


def test_release_approval_and_hashes_are_valid() -> None:
    release = Release.load(RELEASE)
    assert release.manifest["status"] == "approved"
    assert len(release.medicines) == 6
    assert len(release.evidence) == 18


def test_exact_match_requires_concentration_and_form() -> None:
    release = Release.load(RELEASE)
    assert match_medicine("sinvastatina", release).status == "ambiguous"
    assert match_medicine("sinvastatina 20mg", release).status == "ambiguous"
    assert match_medicine("sinvastatina 10 mg comprimido", release).status == "not_in_scope"
    match = match_medicine("sinvastatina 20mg comprimido", release)
    assert match.status == "matched"
    assert match.medicine is not None
    assert match.medicine["strength"] == "20 mg"
    wrong_form = match_medicine("sinvastatina 20 mg cápsula", release)
    assert wrong_form.status == "not_in_scope"
    assert "comprimido" in wrong_form.message


def test_retrieval_filters_same_medicine_and_cites_three_sources() -> None:
    release = Release.load(RELEASE)
    store = FakeStore(release.evidence)
    result = retrieve("Sinvastatina 20 mg comprimido consta na REME?", release, store)
    assert result["status"] == "matched"
    assert {e["source"]["source_id"] for e in result["evidence"]} == {"F01", "F03", "F04"}
    assert store.filter_seen == {"medicine_id": result["medicine"]["medicine_id"]}
    assert all(e["medicine_id"] == result["medicine"]["medicine_id"] for e in result["evidence"])


def test_lexical_fallback_returns_exact_catalog_evidence_without_vector_store() -> None:
    release = Release.load(RELEASE)
    result = retrieve_lexical("Sinvastatina 20 mg comprimido consta na REME?", release)
    assert result["status"] == "matched"
    assert result["retrieval_strategy"] == "lexical_exact_fallback"
    assert result["medicine"]["strength"] == "20 mg"
    assert result["evidence"]


def test_unsupported_claims_do_not_call_vector_search() -> None:
    release = Release.load(RELEASE)
    store = FakeStore(release.evidence)
    for question in (
        "Sinvastatina 20 mg comprimido tem estoque?",
        "Quais documentos preciso para sinvastatina 20 mg comprimido?",
        "Posso tomar sinvastatina 20 mg comprimido?",
    ):
        assert retrieve(question, release, store)["status"] in {"unsupported", "blocked"}
    assert store.filter_seen is None
