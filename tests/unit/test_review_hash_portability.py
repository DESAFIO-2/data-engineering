from __future__ import annotations

from hashlib import sha256
from pathlib import Path

from rag.consolidated_evaluation import _review_hash


def test_review_hash_accepts_same_markdown_with_windows_line_endings(tmp_path: Path) -> None:
    path = tmp_path / "review.md"
    path.write_bytes(b"approved\nreviewed\n")
    windows_hash = sha256(b"approved\r\nreviewed\r\n").hexdigest()
    assert _review_hash(path, {windows_hash}) == windows_hash


def test_review_hash_rejects_changed_content(tmp_path: Path) -> None:
    path = tmp_path / "review.md"
    path.write_bytes(b"not approved\n")
    expected = sha256(b"approved\r\n").hexdigest()
    assert _review_hash(path, {expected}) != expected
