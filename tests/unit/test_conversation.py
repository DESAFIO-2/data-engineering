from pathlib import Path
from types import SimpleNamespace

from rag import experimental_cli
from rag.config import Settings
from rag.conversation import (
    format_history,
    greeting_reply,
    is_clarification,
    is_clarification_input,
)


def test_greeting_is_friendly_and_does_not_need_a_model() -> None:
    reply = greeting_reply("Oi!")
    assert reply is not None
    assert "Olá!" in reply
    assert "concentração" in reply
    assert "cápsula" in reply
    assert "supositório" in reply
    assert greeting_reply("Onde tem estoque?") is None


def test_clarification_followup_is_recognized_and_history_is_bounded() -> None:
    assert is_clarification("Informe a forma farmacêutica, por exemplo, comprimido.")
    assert is_clarification_input("comprimido")
    assert is_clarification_input("500 mg comprimido")
    assert is_clarification_input("líquido")
    assert is_clarification_input("supositório")
    assert not is_clarification_input("E em Planaltina?")
    turns = [(str(i), f"resposta {i}") for i in range(8)]
    rendered = format_history(turns)
    assert "Usuário: 1" not in rendered
    assert "Usuário: 7" in rendered


def test_experimental_chat_merges_form_followup_into_live_stock_query(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    monkeypatch.setattr(
        experimental_cli.Corpus,
        "load",
        lambda *args: SimpleNamespace(manifest={}, chunks=[], fingerprint="test"),
    )
    monkeypatch.setattr(experimental_cli.Release, "load", lambda path: object())
    monkeypatch.setattr(
        experimental_cli,
        "sync_snapshot",
        lambda *args: {"ubs_stock": [], "locations": []},
    )
    monkeypatch.setattr(experimental_cli, "load_snapshot", lambda path: {"snapshot": True})
    seen: list[str] = []

    def live_reply(question, release, snapshot):
        seen.append(question)
        if "comprimido" in question:
            return "Saldo consultado para a apresentação completa."
        return "Informe a forma farmacêutica, por exemplo, comprimido."

    monkeypatch.setattr(experimental_cli, "live_reply", live_reply)
    messages = iter(
        ["Tem sinvastatina 40 mg disponível hoje em Planaltina?", "comprimido", "sair"]
    )
    monkeypatch.setattr("builtins.input", lambda prompt: next(messages))
    monkeypatch.setattr(
        experimental_cli,
        "resolve",
        lambda path: path,
    )
    settings = Settings("", "unused", "unused", tmp_path / "release", tmp_path / "index", 5)
    args = SimpleNamespace(
        command="chat",
        curated=None,
        supplement=None,
        corpus=tmp_path / "corpus",
        documental=False,
        strategy="lexical",
        show_context=False,
    )

    assert experimental_cli.run(args, settings) == 0
    assert seen == [
        "Tem sinvastatina 40 mg disponível hoje em Planaltina?",
        "Tem sinvastatina 40 mg disponível hoje em Planaltina? comprimido",
    ]
    output = capsys.readouterr().out
    assert "concentração + forma" in output
    assert "Saldo consultado" in output
