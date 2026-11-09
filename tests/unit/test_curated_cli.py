"""CLI integration using synthetic reviews only, without provider/API calls."""

import json
import sys
from hashlib import sha256
from pathlib import Path
from unittest.mock import Mock

import pytest

from rag import cli, curation, experimental_cli
from rag.config import Settings
from rag.release import Release


@pytest.fixture(autouse=True)
def offline(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    settings = Settings("", "unused", "unused", tmp_path / "legacy", tmp_path / "index", 5)
    monkeypatch.setattr(cli, "get_settings", lambda: settings)
    for module in (cli, experimental_cli):
        for name in ("google_chat", "google_embeddings"):
            monkeypatch.setattr(module, name, Mock(side_effect=AssertionError("API forbidden")))
    monkeypatch.setattr(Release, "load", Mock(side_effect=AssertionError("Legacy forbidden")))


@pytest.fixture
def approved(tmp_path: Path) -> Path:
    candidate = tmp_path / "candidate"
    candidate.mkdir()
    chunk = {
        "evidence_id": "ev-synthetic",
        "text": "Documento público fictício sobre cadastro municipal.",
        "chunk_type": "page",
        "source": {
            "source_id": "https://example.org/public",
            "url": "https://example.org/public",
            "version": "synthetic-test",
            "sha256": "a" * 64,
            "page": 1,
        },
    }
    payload = {"chunks.jsonl": (json.dumps(chunk) + "\n").encode(), "occurrences.jsonl": b""}
    for name, raw in payload.items():
        (candidate / name).write_bytes(raw)
    manifest = {
        "status": "experimental",
        "files": {name: {"sha256": sha256(raw).hexdigest()} for name, raw in payload.items()},
    }
    (candidate / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    review = tmp_path / "review.json"
    document = curation.export_review(candidate, None, review)
    document["entries"][0].update(
        decision="approve",
        reviewer="Synthetic test fixture",
        date="2026-01-01",
        reason="Fabricated public text; test only",
    )
    review.write_text(json.dumps(document), encoding="utf-8")
    return curation.publish(review, tmp_path / "approved")


@pytest.mark.parametrize("command", ["index", "search", "ask", "chat", "eval"])
def test_curated_dispatch(monkeypatch: pytest.MonkeyPatch, command: str) -> None:
    run = Mock(return_value=7)
    monkeypatch.setattr(experimental_cli, "run", run)
    monkeypatch.setattr(sys, "argv", ["rag", command, "--curated", "release-folder"])
    assert cli.main() == 7
    args, settings = run.call_args.args
    assert args.curated == Path("release-folder")
    assert args.command == command
    assert args.experimental is False
    assert isinstance(settings, Settings)


def test_modes_mutually_exclusive(monkeypatch: pytest.MonkeyPatch) -> None:
    run = Mock()
    monkeypatch.setattr(experimental_cli, "run", run)
    monkeypatch.setattr(sys, "argv", ["rag", "search", "--curated", "x", "--experimental"])
    with pytest.raises(SystemExit) as error:
        cli.main()
    assert error.value.code == 2
    run.assert_not_called()


def test_supplement_rejected_before_load(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    loader = Mock(side_effect=AssertionError("Must reject before loading"))
    monkeypatch.setattr(curation, "load_approved", loader)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "rag",
            "search",
            "cadastro",
            "--curated",
            "unused",
            "--supplement",
            "unused.jsonl",
            "--strategy",
            "lexical",
        ],
    )
    assert cli.main() == 1
    assert "não aceita suplemento" in capsys.readouterr().err
    loader.assert_not_called()


def test_approved_lexical_search(
    approved: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    loader = Mock(wraps=curation.load_approved)
    monkeypatch.setattr(curation, "load_approved", loader)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "rag",
            "search",
            "cadastro municipal",
            "--curated",
            str(approved),
            "--strategy",
            "lexical",
            "--show-context",
        ],
    )
    assert cli.main() == 0
    loader.assert_called_once_with(approved)
    output = capsys.readouterr()
    assert "CURADO" in output.out
    assert "ev-synthetic" in output.out
    assert "Documento público fictício" in output.out
    assert not output.err


@pytest.mark.parametrize("kind", ["missing", "fake", "tampered"])
def test_invalid_curated_path(
    kind: str,
    approved: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    folder = tmp_path / "missing"
    if kind == "fake":
        folder.mkdir()
        (folder / "manifest.json").write_text(
            json.dumps({"status": "experimental", "schema_version": 2}),
            encoding="utf-8",
        )
    elif kind == "tampered":
        folder = approved
        (folder / "chunks.jsonl").write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "rag",
            "search",
            "cadastro",
            "--curated",
            str(folder),
            "--strategy",
            "lexical",
        ],
    )
    assert cli.main() == 1
    output = capsys.readouterr()
    assert "Erro:" in output.err
    assert "CURADO" not in output.out
    assert "ev-synthetic" not in output.out
