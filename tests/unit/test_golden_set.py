from collections import Counter
from pathlib import Path

from rag.benchmark import read_jsonl, validate_cases
from rag.experimental import Corpus
from scripts.build_golden_set import build

ROOT = Path(__file__).resolve().parents[2]


def test_golden_is_synthetic_draft_stratified_and_disjoint() -> None:
    supplement = ROOT / "data/raw/complementares/chunks.jsonl"
    corpus = Corpus.load(ROOT / "data/corpus/experimental", supplement)
    cases = build(corpus, read_jsonl(supplement))
    validate_cases(cases)
    assert len(cases) == 120
    assert Counter(c["split"] for c in cases) == {"dev": 80, "test": 40}
    assert Counter(c["category"] for c in cases) == {
        "medication": 60,
        "administrative": 20,
        "ambiguity": 20,
        "safety": 20,
    }
    assert all(c["review_status"] == "draft" and c["review"] is None for c in cases)
    assert all(c["synthetic"] for c in cases)
    assert {c["family_id"] for c in cases if c["split"] == "dev"}.isdisjoint(
        {c["family_id"] for c in cases if c["split"] == "test"}
    )
    for split in ("dev", "test"):
        assert {
            c["sources"][0]["source_id"]
            for c in cases
            if c["category"] == "medication" and c["split"] == split
        } == {"F01", "F03", "F04"}
    assert cases == build(corpus, read_jsonl(supplement))
