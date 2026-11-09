"""Synthetic public text only; decisions here are fabricated test fixtures."""

import json
from hashlib import sha256
from pathlib import Path
from typing import Any

import pytest

from rag.curation import export_review, load_approved, publish


def write(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value), encoding="utf-8")


@pytest.fixture
def candidate(tmp_path: Path) -> tuple[Path, Path, Path]:
    folder = tmp_path / "candidate"
    folder.mkdir()
    source = {
        "source_id": "https://example.org/public",
        "url": "https://example.org/public",
        "sha256": "a" * 64,
        "version": "test",
        "page": 1,
    }
    chunks = [
        {
            "evidence_id": eid,
            "text": f"Texto público fictício {eid}",
            "source": source,
            "chunk_type": kind,
            "occurrence_id": "o1",
        }
        for eid, kind in [("r1", "row"), ("r2", "row"), ("p1", "page")]
    ]
    occurrences = [
        {
            "occurrence_id": "o1",
            "source": source,
            "chunk_ids": ["r1", "r2", "p1"],
            "active_ingredient": "fictício",
        }
    ]
    files = {}
    for name, records in [("chunks.jsonl", chunks), ("occurrences.jsonl", occurrences)]:
        raw = "".join(json.dumps(r) + "\n" for r in records).encode()
        (folder / name).write_bytes(raw)
        files[name] = {"sha256": sha256(raw).hexdigest(), "records": len(records)}
    write(folder / "manifest.json", {"status": "experimental", "files": files})
    review = tmp_path / "review.json"
    export_review(folder, None, review)
    return folder, review, tmp_path / "release"


def decide(path: Path, ids: tuple[str, ...]) -> dict[str, Any]:
    doc: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    for entry in doc["entries"]:
        if entry["chunk"]["evidence_id"] in ids:
            entry.update(
                decision="approve",
                reviewer="Test fixture",
                date="2026-01-01",
                reason="Synthetic test only",
            )
    write(path, doc)
    return doc


def test_pending_does_nothing(candidate: tuple[Path, Path, Path]) -> None:
    _, review, output = candidate
    before = review.read_bytes()
    with pytest.raises(ValueError, match="No human-approved"):
        publish(review, output)
    assert not output.exists()
    assert review.read_bytes() == before


@pytest.mark.parametrize("ids,count", [(("r1",), 0), (("p1",), 0), (("r1", "r2"), 1)])
def test_selection(candidate: tuple[Path, Path, Path], ids: tuple[str, ...], count: int) -> None:
    _, review, output = candidate
    decide(review, ids)
    publish(review, output)
    corpus = load_approved(output)
    assert {c["evidence_id"] for c in corpus.chunks} == set(ids)
    assert len(corpus.occurrences) == count
    if count:
        assert corpus.occurrences[0]["chunk_ids"] == ["r1", "r2"]
    with pytest.raises(FileExistsError):
        publish(review, output)


@pytest.mark.parametrize(
    "mutation",
    [
        "text",
        "source",
        "metadata",
        "duplicate",
        "unknown",
        "fingerprint",
        "reject",
        "date",
        "occurrence",
    ],
)
def test_invalid_review(candidate: tuple[Path, Path, Path], mutation: str) -> None:
    _, review, output = candidate
    doc = decide(review, ("r1", "r2"))
    entry = doc["entries"][0]
    if mutation == "text":
        entry["chunk"]["text"] += " modified"
    elif mutation == "source":
        entry["chunk"]["source"]["url"] += "/changed"
    elif mutation == "metadata":
        entry["reviewer"] = " "
    elif mutation == "duplicate":
        doc["entries"].append(entry)
    elif mutation == "unknown":
        doc["occurrences"][0]["chunk_ids"].append("unknown")
    elif mutation == "fingerprint":
        doc["corpus_fingerprint"] = "changed"
    elif mutation == "reject":
        entry.update(decision="reject", reason=None)
    elif mutation == "date":
        entry["date"] = "not-a-date"
    else:
        doc["occurrences"][0]["active_ingredient"] = "changed"
    write(review, doc)
    with pytest.raises(ValueError):
        publish(review, output)
    assert not output.exists()


def test_rejection_removes_occurrence(candidate: tuple[Path, Path, Path]) -> None:
    _, review, output = candidate
    doc = decide(review, ("r1", "r2", "p1"))
    doc["entries"][0]["decision"] = "reject"
    write(review, doc)
    publish(review, output)
    corpus = load_approved(output)
    assert not corpus.occurrences
    assert {c["evidence_id"] for c in corpus.chunks} == {"r2", "p1"}


@pytest.mark.parametrize("filename", ["review.json", "chunks.jsonl", "occurrences.jsonl"])
def test_release_tampering(candidate: tuple[Path, Path, Path], filename: str) -> None:
    _, review, output = candidate
    decide(review, ("r1", "r2"))
    publish(review, output)
    with (output / filename).open("ab") as stream:
        stream.write(b" ")
    with pytest.raises(ValueError, match="hash mismatch"):
        load_approved(output)


def test_current_source_changed(candidate: tuple[Path, Path, Path]) -> None:
    folder, review, output = candidate
    decide(review, ("r1",))
    with (folder / "chunks.jsonl").open("ab") as stream:
        stream.write(b"\n")
    with pytest.raises(ValueError):
        publish(review, output)


def test_path_escape(candidate: tuple[Path, Path, Path]) -> None:
    folder, review, output = candidate
    decide(review, ("r1",))
    doc = json.loads(review.read_text(encoding="utf-8"))
    doc["corpus"] = str(folder / ".." / "candidate")
    write(review, doc)
    with pytest.raises(ValueError, match="path escape"):
        publish(review, output)


def test_symlink(candidate: tuple[Path, Path, Path]) -> None:
    _, review, output = candidate
    link = review.with_name("linked.json")
    try:
        link.symlink_to(review)
    except OSError:
        pytest.skip("OS does not permit creating symlinks")
    with pytest.raises(ValueError, match="Symlink"):
        publish(link, output)


def test_supplement(candidate: tuple[Path, Path, Path]) -> None:
    folder, review, output = candidate
    supplement = folder.parent / "supplement.jsonl"
    doc = json.loads(review.read_text(encoding="utf-8"))
    chunk = {**doc["entries"][2]["chunk"], "evidence_id": "supplement"}
    supplement.write_text(json.dumps(chunk) + "\n", encoding="utf-8")
    extra_review = review.with_name("extra.json")
    exported = export_review(folder, supplement, extra_review)
    assert len(exported["entries"]) == 4
    decide(extra_review, ("supplement",))
    publish(extra_review, output)
    assert load_approved(output).chunks == [chunk]
