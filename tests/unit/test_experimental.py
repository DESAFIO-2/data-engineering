import json
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from rag.experimental import SAFE_ABSTENTION, Corpus, Retriever, generate


def sample_corpus() -> Corpus:
    chunks: list[dict[str, Any]] = []
    occurrences: list[dict[str, Any]] = []
    for number, (strength, form, source) in enumerate(
        [
            ("5 mg", "comprimido", "F03"),
            ("25 mg", "comprimido", "F03"),
            ("25 mg", "comprimido revestido", "F03"),
            ("5 mg", "comprimido", "F01"),
        ]
    ):
        eid = f"ev-{number}"
        chunks.append(
            {
                "evidence_id": eid,
                "text": f"enalapril {strength} {form}",
                "chunk_type": "row",
                "source": {
                    "source_id": source,
                    "url": "https://example.org",
                    "sha256": "abc",
                    "version": "2026",
                    "page": 1,
                },
            }
        )
        occurrences.append(
            {
                "active_ingredient": "enalapril",
                "strength": strength,
                "form": form,
                "chunk_ids": [eid],
            }
        )
    for sid in ("C01", "C17", "F04"):
        chunks.append(
            {
                "evidence_id": f"ev-{sid}",
                "text": "Farmácia Popular documentos para retirada CPF receita",
                "source": {
                    "source_id": sid,
                    "url": "https://example.org",
                    "sha256": "abc",
                    "version": "2026",
                    "section": "acesso",
                },
            }
        )
    return Corpus(Path("."), chunks, occurrences, "fixture", {})


@pytest.mark.parametrize(
    ("query", "status", "ids"),
    [
        ("enalapril 5mg comprimido REME", "matched", ["ev-0"]),
        ("enalapril 25mg comprimido REME", "matched", ["ev-1"]),
        ("enalapril 25mg comprimido revestido REME", "matched", ["ev-2"]),
        ("enalapril 25mg REME", "ambiguous", []),
        ("enalapril REME", "ambiguous", []),
        ("enalapril 15mg comprimido", "insufficient", []),
        ("enalapril 5mg capsula", "insufficient", []),
        ("enalapril 5mg comprimidoso", "matched", ["ev-0", "ev-3"]),
        ("enalapril 5mg e 25mg comprimido", "ambiguous", []),
        ("enalapril 0,5mg comprimido", "insufficient", []),
        ("enalapril 5mg/ml comprimido", "insufficient", []),
    ],
)
def test_identity(query: str, status: str, ids: list[str]) -> None:
    result = Retriever(sample_corpus()).search(query, strategy="exact")
    assert result["status"] == status
    assert result["ranked_ids"] == ids


class FakeStore:
    def __init__(self) -> None:
        self.filters: Any = None

    def similarity_search(self, question: str, k: int, filter: Any) -> list[Any]:
        self.filters = filter
        return [
            SimpleNamespace(metadata={"evidence_id": eid})
            for eid in ("ev-F04", "ev-C17", "ev-C01", "ev-1", "ev-0")
        ]


def test_hybrid_source_filters_and_rrf() -> None:
    store = FakeStore()
    retriever = Retriever(sample_corpus(), store)
    result = retriever.search("documentos Farmácia Popular")
    assert set(result["ranked_ids"]) == {"ev-C01", "ev-C17"}
    assert store.filters == {"source_id": {"$in": ["C01", "C17"]}}
    result = retriever.search("documentos Farmácia Popular C01")
    assert result["ranked_ids"] == ["ev-C01"]
    assert store.filters == {"source_id": {"$in": ["C01"]}}
    result = retriever.search("enalapril 5mg comprimido REME")
    assert result["ranked_ids"] == ["ev-0"]
    assert store.filters == {"evidence_id": {"$in": ["ev-0"]}}


def test_hybrid_falls_back_to_lexical_when_embedding_quota_fails() -> None:
    class UnavailableStore:
        def similarity_search(self, question: str, k: int, filter: Any) -> list[Any]:
            raise RuntimeError("429 RESOURCE_EXHAUSTED")

    result = Retriever(sample_corpus(), UnavailableStore()).search(
        "enalapril 5mg comprimido REME", strategy="hybrid"
    )
    assert result["ranked_ids"] == ["ev-0"]
    assert result["strategy"] == "hybrid_fallback_lexical"
    assert "somente em busca lexical" in result["retrieval_warning"]


def test_chat_search_uses_lexical_if_vector_index_is_unavailable() -> None:
    result = Retriever(sample_corpus()).search_with_fallback("enalapril 5mg comprimido REME")
    assert result["status"] == "matched"
    assert result["ranked_ids"] == ["ev-0"]
    assert result["strategy"] == "hybrid_fallback_lexical"
    assert "somente em busca lexical" in result["retrieval_warning"]


def test_chat_preserves_quota_error_instead_of_reporting_empty_vectors() -> None:
    class Store:
        def similarity_search(self, *args: Any, **kwargs: Any) -> list[Any]:
            raise RuntimeError("429 RESOURCE_EXHAUSTED")

    result = Retriever(sample_corpus(), Store()).search_with_fallback(
        "enalapril 5mg comprimido REME"
    )
    assert "429 RESOURCE_EXHAUSTED" in result["retrieval_warning"]
    assert result["vector_diagnostics"]["returned"] is None


def test_vector_diagnostics_distinguish_discarded_chunks() -> None:
    class Store:
        def similarity_search(self, *args: Any, **kwargs: Any) -> list[Any]:
            return [SimpleNamespace(metadata={"evidence_id": "ev-3"})]

    result = Retriever(sample_corpus(), Store()).search_with_fallback(
        "enalapril 5mg comprimido REME"
    )
    assert result["vector_diagnostics"]["returned"] == 1
    assert result["vector_diagnostics"]["accepted"] == 0
    assert result["vector_diagnostics"]["discarded"] == 1
    assert "descartados pelos filtros" in result["retrieval_warning"]


def test_abbreviated_ingredient_resolves_before_form_typo_suggestions() -> None:
    corpus = sample_corpus()
    for row in corpus.occurrences:
        row["active_ingredient"] = "cloridrato de metformina"
    corpus.occurrences.append({"active_ingredient": "comprimidos", "chunk_ids": []})
    result = Retriever(corpus).search(
        "Qual componente de financiamento aparece para metformina 5 mg comprimido?",
        strategy="lexical",
    )
    assert "Confira se quis dizer" not in result["message"]
    assert result["status"] == "matched"


def test_vector_does_not_hide_embedding_quota_failure() -> None:
    class UnavailableStore:
        def similarity_search(self, question: str, k: int, filter: Any) -> list[Any]:
            raise RuntimeError("429 RESOURCE_EXHAUSTED")

    with pytest.raises(RuntimeError, match="RESOURCE_EXHAUSTED"):
        Retriever(sample_corpus(), UnavailableStore()).search(
            "enalapril 5mg comprimido REME", strategy="vector"
        )


@pytest.mark.parametrize(
    ("answer", "valid"),
    [
        ("Consta [ev-0].", True),
        ("Consta [ev-0] [inventado].", False),
        ("Consta [ev-inventado].", False),
        ("Consta [1].", False),
        ("Consta.", False),
        (SAFE_ABSTENTION, True),
        (SAFE_ABSTENTION + " [inventado]", False),
    ],
)
def test_citations(answer: str, valid: bool) -> None:
    class LLM:
        def invoke(self, messages: Any) -> Any:
            return SimpleNamespace(content=answer)

    result = Retriever(sample_corpus()).search("enalapril 5mg comprimido", strategy="exact")
    generated = generate("consta?", result, LLM())
    assert generated["citation_valid"] is valid
    if answer == SAFE_ABSTENTION:
        assert generated["status"] == "insufficient"
        assert generated["citation_ids"] == []


def test_generation_prompt_requires_consistent_answer_format() -> None:
    seen: list[Any] = []

    class LLM:
        def invoke(self, messages: Any) -> Any:
            seen.extend(messages)
            return SimpleNamespace(content="Resposta: Consta [ev-0].")

    result = Retriever(sample_corpus()).search("enalapril 5mg comprimido", strategy="exact")
    generate("consta?", result, LLM())
    system_prompt = seen[0][1]
    assert "Use sempre este formato" in system_prompt
    assert "Resposta:" in system_prompt
    assert "Limite:" in system_prompt
    assert "as fontes serão exibidas separadamente" in system_prompt


def test_loader_hashes_and_portable_sidecar(tmp_path: Path) -> None:
    corpus = sample_corpus()
    files = {}
    for name, records in (
        ("chunks.jsonl", corpus.chunks),
        ("occurrences.jsonl", corpus.occurrences),
    ):
        body = "".join(json.dumps(row) + "\n" for row in records)
        (tmp_path / name).write_text(body, encoding="utf-8")
        files[name] = {
            "sha256": sha256((tmp_path / name).read_bytes()).hexdigest(),
            "records": len(records),
        }
    (tmp_path / "manifest.json").write_text(
        json.dumps({"status": "experimental", "files": files}), encoding="utf-8"
    )
    supplement = tmp_path / "extra.jsonl"
    supplement.write_text("", encoding="utf-8")
    sidecar = supplement.with_suffix(".manifest.json")
    sidecar.write_text(
        json.dumps({"files": {supplement.name: {"sha256": sha256(b"").hexdigest(), "records": 0}}}),
        encoding="utf-8",
    )
    loaded = Corpus.load(tmp_path, supplement)
    assert loaded.fingerprint == Corpus.load(tmp_path, supplement).fingerprint
    supplement.write_text("\n", encoding="utf-8")
    with pytest.raises(ValueError, match="suplemento"):
        Corpus.load(tmp_path, supplement)
    with pytest.raises(ValueError, match="exige"):
        Corpus.load(tmp_path, supplement_manifest=sidecar)


def test_split_row_without_name_uses_occurrence_lineage() -> None:
    corpus = sample_corpus()
    row = corpus.occurrences[0]
    row["occurrence_id"] = "occ-selected"
    row["source"] = corpus.chunks[0]["source"]
    corpus.chunks[0]["occurrence_id"] = "occ-selected"
    for eid, kind, occurrence in (
        ("ev-tail", "row", "occ-selected"),
        ("ev-neighbor", "row", "occ-other"),
        ("ev-page", "page", None),
    ):
        corpus.chunks.append(
            {
                "evidence_id": eid,
                "text": "Canal na linha: componente básico",
                "chunk_type": kind,
                "occurrence_id": occurrence,
                "source": row["source"],
            }
        )
        row["chunk_ids"].append(eid)

    class SplitStore:
        def similarity_search(self, question: str, k: int, filter: Any) -> list[Any]:
            assert filter == {"evidence_id": {"$in": ["ev-0", "ev-tail"]}}
            return [
                SimpleNamespace(metadata={"evidence_id": eid})
                for eid in ("ev-tail", "ev-neighbor", "ev-page", "ev-0")
            ]

    retriever = Retriever(corpus, SplitStore())
    for strategy in ("exact", "vector", "hybrid"):
        result = retriever.search("enalapril 5mg comprimido REME", strategy=strategy)
        assert set(result["ranked_ids"]) == {"ev-0", "ev-tail"}


@pytest.mark.parametrize(
    ("recorded", "supplied", "expected"),
    [
        ("3 mg/mL + 3 mg/mL", "3mg/mL+3mg/mL", "matched"),
        ("3 mg/mL + 3 mg/mL", "3 mg/mL", "insufficient"),
        ("3 mg/mL + 3 mg/mL", "3mg/mL+3mg/mL+3mg/mL", "insufficient"),
        ("3 mg/mL + 3 mg/mL", "13mg/mL+3mg/mL", "insufficient"),
        ("25 mg/0,5 mL + 5 mg/ 0,5 mL", "25mg/0.5mL+5mg/0.5mL", "matched"),
        ("25 mg/0,5 mL + 5 mg/ 0,5 mL", "5mg/0.5mL+25mg/0.5mL", "insufficient"),
        ("25 mg/0,5 mL + 5 mg/ 0,5 mL", "25mg/mL+5mg/mL", "insufficient"),
        ("10 mg/g (1%)", "10mg/g (1%)", "matched"),
        ("10 mg/g (1%)", "10mg/g (2%)", "insufficient"),
        ("10 mg/g (1%)", "1%", "insufficient"),
        ("10 mg/g (1%)", "10mg/g (1%) e 20mg/g", "insufficient"),
    ],
)
def test_complete_compound_strength(recorded: str, supplied: str, expected: str) -> None:
    corpus = sample_corpus()
    name = "acetato de betametasona + fosfato dissódico de betametasona"
    # Include both component names as independent rows: the full literal name wins.
    names = [name, "acetato de betametasona", "fosfato dissódico de betametasona", name]
    for index, row in enumerate(corpus.occurrences):
        row.update(active_ingredient=names[index], strength=recorded, form="creme")
        corpus.chunks[index]["text"] = f"{names[index]} {recorded} creme"
    result = Retriever(corpus).search(f"{name} {supplied} creme REME", strategy="lexical")
    assert result["status"] == expected
    assert result["ranked_ids"] == (["ev-0"] if expected == "matched" else [])
    separated = Retriever(corpus).search(
        "acetato de betametasona e fosfato dissódico de betametasona", strategy="exact"
    )
    assert separated["status"] == "ambiguous"


def test_compact_strength_query_matches_only_requested_corpus_row() -> None:
    corpus = sample_corpus()
    corpus.occurrences[0].update(
        active_ingredient="cloridrato de metformina",
        strength="500 mg",
        form="comprimido",
        source={**corpus.chunks[0]["source"], "source_id": "F01"},
        medicine_id="med-metformina",
        occurrence_id="occ-metformina-500",
        chunk_ids=["ev-0"],
    )
    corpus.chunks[0]["text"] = "cloridrato de metformina | 500 mg | comprimido | Básico | A10BA02"
    corpus.chunks[0]["occurrence_id"] = "occ-metformina-500"
    corpus.chunks[0]["source"]["source_id"] = "F01"
    for index in (1, 2, 3):
        corpus.occurrences[index]["active_ingredient"] = f"outro medicamento {index}"
        corpus.occurrences[index]["source"] = {"source_id": "F03"}
        corpus.chunks[index]["source"]["source_id"] = "F03"
    result = Retriever(corpus).search(
        "O que consta na RENAME sobre metformina 500mg?", strategy="lexical"
    )
    assert result["ranked_ids"] == ["ev-0"]


def test_wrong_strength_for_resolved_alias_abstains_without_neighbor_chunks() -> None:
    corpus = sample_corpus()
    occurrence = corpus.occurrences[0]
    occurrence.update(
        active_ingredient="losartana potássica",
        strength="50 mg",
        form="comprimido",
        source={**corpus.chunks[0]["source"], "source_id": "F01"},
        medicine_id="med-losartana",
        occurrence_id="occ-losartana-50",
        chunk_ids=["ev-0"],
    )
    corpus.chunks[0].update(
        text="losartana potássica | 50 mg | comprimido",
        occurrence_id="occ-losartana-50",
    )
    corpus.chunks[0]["source"]["source_id"] = "F01"
    for index in (1, 2, 3):
        corpus.occurrences[index]["source"] = {"source_id": "F03"}
        corpus.chunks[index]["source"]["source_id"] = "F03"

    retriever = Retriever(corpus)
    wrong = retriever.search("RENAME losartana 500mg", strategy="lexical")
    right = retriever.search("RENAME losartana 50mg", strategy="lexical")

    assert wrong["status"] == "insufficient"
    assert wrong["evidence"] == []
    assert "concentração informada não foi localizada" in wrong["message"]
    assert right["ranked_ids"] == ["ev-0"]


def test_typo_in_medicine_name_requests_clarification_instead_of_location_matches() -> None:
    corpus = sample_corpus()
    corpus.occurrences[0].update(
        active_ingredient="losartana potássica",
        strength="50 mg",
        form="comprimido",
        source={**corpus.chunks[0]["source"], "source_id": "F03"},
        medicine_id="med-losartana",
        occurrence_id="occ-losartana-50",
        chunk_ids=["ev-0"],
    )
    corpus.chunks[0].update(
        text="losartana potássica | 50 mg | comprimido",
        occurrence_id="occ-losartana-50",
    )
    retriever = Retriever(corpus)
    result = retriever.search("Onde tem losarnata em Planaltina?", strategy="lexical")
    assert result["status"] == "ambiguous"
    assert "losartana" in result["message"]
    assert result["evidence"] == []


def test_empty_corpus_and_safety() -> None:
    retriever = Retriever(Corpus(Path("."), [], [], "empty", {}))
    assert retriever.search("documentos", strategy="lexical")["status"] == "insufficient"
    assert retriever.search("posso tomar enalapril?")["status"] == "blocked"
    assert retriever.search("estoque enalapril")["status"] == "unsupported"


def test_wrong_form_and_shared_passage_are_not_identity_evidence() -> None:
    corpus = sample_corpus()
    retriever = Retriever(corpus)
    assert (
        retriever.search("enalapril 5mg comprimido efervescente", strategy="exact")["status"]
        == "insufficient"
    )
    assert retriever.search("enalapril 5mg comprimido receita REME", strategy="exact")[
        "ranked_ids"
    ] == ["ev-0"]
    corpus.occurrences[1]["chunk_ids"].append("ev-0")
    assert (
        Retriever(corpus).search("enalapril 5mg comprimido REME", strategy="exact")["status"]
        == "insufficient"
    )
