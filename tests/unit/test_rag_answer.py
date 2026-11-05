from pathlib import Path
from types import SimpleNamespace
from typing import Any

from rag.answer import synthesize
from rag.release import Release
from rag.retrieval import retrieve

RELEASE = Path(__file__).resolve().parents[2] / "data/releases/rag-lote-1-aprovado-2026-11-05"


class FakeStore:
    def similarity_search(
        self, query: str, k: int, filter: dict[str, str]
    ) -> list[SimpleNamespace]:
        return []


class FakeLLM:
    def __init__(self, content: Any) -> None:
        self.content = content

    def invoke(self, messages: Any) -> SimpleNamespace:
        return SimpleNamespace(content=self.content)


def test_synthesis_prints_only_text_blocks() -> None:
    release = Release.load(RELEASE)
    question = "Sinvastatina 20 mg comprimido consta na REME-DF?"
    result = retrieve(question, release, FakeStore())
    llm = FakeLLM(
        [
            {
                "type": "text",
                "text": "Sim, consta na versão consultada.",
                "extras": {"signature": "segredo"},
            },
            {"type": "reasoning", "text": "raciocínio interno"},
        ]
    )
    assert synthesize(question, result, llm) == "Sim, consta na versão consultada."


def test_synthesis_keeps_plain_text_response() -> None:
    release = Release.load(RELEASE)
    question = "Sinvastatina 20 mg comprimido consta na REME-DF?"
    result = retrieve(question, release, FakeStore())
    assert synthesize(question, result, FakeLLM("  Sim.  ")) == "Sim."
