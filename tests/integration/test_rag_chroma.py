from pathlib import Path

from langchain_core.embeddings import DeterministicFakeEmbedding

from rag.evaluate import evaluate_retrieval
from rag.release import Release
from rag.retrieval import retrieve
from rag.vector import build_index, open_index

RELEASE = Path(__file__).resolve().parents[2] / "data/releases/rag-lote-1-aprovado-2026-11-05"


def test_chroma_indexes_all_evidence_and_reopens(tmp_path: Path) -> None:
    release = Release.load(RELEASE)
    embeddings = DeterministicFakeEmbedding(size=32)
    location = build_index(release, tmp_path, "fake-test-model", embeddings)
    assert (location / "index.json").exists()
    second = build_index(release, tmp_path, "fake-test-model", embeddings)
    assert second == location
    store = open_index(release, tmp_path, "fake-test-model", embeddings)
    assert len(store.get()["ids"]) == 18
    result = retrieve("sinvastatina 20 mg comprimido consta na REME?", release, store)
    assert result["status"] == "matched"
    assert {e["source"]["source_id"] for e in result["evidence"]} == {"F01", "F03", "F04"}
    dataset = Path(__file__).resolve().parents[2] / "evals/datasets/retrieval_lote1.jsonl"
    summary = evaluate_retrieval(dataset, release, store)
    assert summary["exact_hits"] == 6
    assert summary["vector_hits"] == 6
