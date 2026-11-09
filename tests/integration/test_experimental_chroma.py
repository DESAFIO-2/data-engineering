from pathlib import Path
from typing import Any

import pytest
from langchain_core.embeddings import DeterministicFakeEmbedding

from rag.experimental import Corpus, Retriever, build_index, open_index, vector_store


class CountingEmbeddings(DeterministicFakeEmbedding):
    calls: int = 0
    fail_at: int = 0

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        self.calls += 1
        if self.calls == self.fail_at:
            raise RuntimeError("simulated interruption")
        return super().embed_documents(texts)


def test_resume_reopen_idempotence_and_identity(tmp_path: Path) -> None:
    chunks: list[dict[str, Any]] = []
    occurrences: list[dict[str, Any]] = []
    for number, strength in enumerate(("5 mg", "25 mg", "50 mg")):
        eid = f"ev-{number}"
        chunks.append(
            {
                "evidence_id": eid,
                "text": f"enalapril {strength} comprimido",
                "chunk_type": "row",
                "source": {"source_id": "F03"},
            }
        )
        occurrences.append(
            {
                "active_ingredient": "enalapril",
                "strength": strength,
                "form": "comprimido",
                "chunk_ids": [eid],
            }
        )
    corpus = Corpus(tmp_path, chunks, occurrences, "resume-fixture", {})
    embeddings = CountingEmbeddings(size=16, fail_at=2)
    with pytest.raises(RuntimeError, match="interruption"):
        build_index(corpus, tmp_path, "fake", embeddings, batch_size=1)
    with pytest.raises(FileNotFoundError):
        open_index(corpus, tmp_path, "fake", embeddings)
    embeddings.fail_at = 0
    location = build_index(corpus, tmp_path, "fake", embeddings, batch_size=1)
    assert embeddings.calls == 4  # first persisted, failed second, two resumed
    assert build_index(corpus, tmp_path, "fake", embeddings) == location
    assert embeddings.calls == 4
    store = open_index(corpus, tmp_path, "fake", embeddings)
    assert set(store.get()["ids"]) == {"ev-0", "ev-1", "ev-2"}
    for strategy in ("hybrid", "vector", "lexical", "exact"):
        result = Retriever(corpus, store).search(
            "enalapril 25mg comprimido REME", strategy=strategy
        )
        assert result["ranked_ids"] == ["ev-1"]
    vector_store(location, embeddings).delete(ids=["ev-1"])
    with pytest.raises(ValueError, match="incompleto"):
        open_index(corpus, tmp_path, "fake", embeddings)
    build_index(corpus, tmp_path, "fake", embeddings)
    assert embeddings.calls == 5
    assert len(open_index(corpus, tmp_path, "fake", embeddings).get()["ids"]) == 3
