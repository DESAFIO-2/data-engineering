"""Explicit human review and immutable, hash-verified corpus publications."""

from __future__ import annotations

import json
from datetime import date
from hashlib import sha256
from pathlib import Path
from typing import Any

from rag.legacy.experimental import Corpus


def _bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()


def _hash(value: Any) -> str:
    return sha256(_bytes(value)).hexdigest()


def _safe(path: Path) -> Path:
    path = path.absolute()
    if ".." in path.parts or any(p.is_symlink() or p.is_junction() for p in (path, *path.parents)):
        raise ValueError(f"Symlink/junction/path escape: {path}")
    return path


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def _read(path: Path) -> Any:
    return json.loads(_safe(path).read_bytes(), object_pairs_hook=_pairs)


def _current(folder: Path, supplement: Path | None) -> Corpus:
    folder = _safe(folder)
    manifest = _read(folder / "manifest.json")
    for name in manifest["files"]:
        if not isinstance(name, str) or not name or any(c in name for c in "/\\:"):
            raise ValueError("Invalid manifest path")
        _safe(folder / name)
    if supplement is not None:
        _safe(supplement)
        _safe(supplement.with_suffix(".manifest.json"))
    return Corpus.load(folder, supplement)


def export_review(corpus: Path, supplement: Path | None, output: Path) -> dict[str, Any]:
    """Export pending decisions only; never replace an existing review."""
    current = _current(corpus, supplement)
    review = {
        "schema_version": 2,
        "corpus": str(_safe(corpus)),
        "supplement": str(_safe(supplement)) if supplement is not None else None,
        "corpus_fingerprint": current.fingerprint,
        "occurrences": current.occurrences,
        "entries": [
            {
                "chunk": c,
                "chunk_sha256": _hash(c),
                "decision": "pending",
                "reviewer": None,
                "date": None,
                "reason": None,
            }
            for c in current.chunks
        ],
    }
    _validate(review)
    with _safe(output).open("xb") as stream:
        stream.write(_bytes(review))
    return review


def _validate(review: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if review.get("schema_version") != 2 or not review.get("corpus_fingerprint"):
        raise ValueError("Invalid review schema/fingerprint")
    chunks: dict[str, dict[str, Any]] = {}
    approved: set[str] = set()
    for entry in review["entries"]:
        chunk = entry["chunk"]
        eid = chunk["evidence_id"]
        if not isinstance(eid, str) or not eid.strip() or eid in chunks:
            raise ValueError("Duplicate/invalid evidence ID")
        if not isinstance(chunk["text"], str) or not chunk["text"].strip():
            raise ValueError("Empty evidence")
        source = chunk["source"]
        if not all(source.get(k) for k in ("source_id", "url", "sha256", "version")):
            raise ValueError("Incomplete source")
        if not source.get("page") and not source.get("section"):
            raise ValueError("Missing source location")
        if entry["chunk_sha256"] != _hash(chunk):
            raise ValueError("Changed chunk/source invalidates review")
        decision = entry["decision"]
        if decision not in ("pending", "approve", "reject"):
            raise ValueError("Invalid decision")
        if decision != "pending":
            for field in ("reviewer", "date", "reason"):
                if not isinstance(entry.get(field), str) or not entry[field].strip():
                    raise ValueError(f"Missing review metadata: {field}")
            parsed = date.fromisoformat(entry["date"])
            if parsed.isoformat() != entry["date"] or parsed > date.today():
                raise ValueError("Invalid review date (YYYY-MM-DD)")
        if decision == "approve":
            approved.add(eid)
        chunks[eid] = chunk
    selected_rows: list[dict[str, Any]] = []
    occurrence_ids: set[str] = set()
    for row in review["occurrences"]:
        oid = row["occurrence_id"]
        if not isinstance(oid, str) or not oid or oid in occurrence_ids:
            raise ValueError("Duplicate/invalid occurrence ID")
        occurrence_ids.add(oid)
        ids = row["chunk_ids"]
        if len(ids) != len(set(ids)) or not set(ids).issubset(chunks):
            raise ValueError("Duplicate/unknown occurrence evidence ID")
        row_ids = [eid for eid in ids if chunks[eid].get("chunk_type") == "row"]
        for eid in row_ids:
            if chunks[eid].get("occurrence_id") != oid or chunks[eid]["source"] != row["source"]:
                raise ValueError("Row evidence does not match occurrence/source")
        if row_ids and set(row_ids).issubset(approved):
            selected_rows.append({**row, "chunk_ids": row_ids})
    return [c for eid, c in chunks.items() if eid in approved], selected_rows


def publish(review: Path, output: Path) -> Path:
    """Validate against current candidate inputs, then create a new release."""
    raw = _safe(review).read_bytes()
    document = json.loads(raw, object_pairs_hook=_pairs)
    chunks, occurrences = _validate(document)
    current = _current(
        Path(document["corpus"]),
        Path(document["supplement"]) if document["supplement"] is not None else None,
    )
    if (
        document["corpus_fingerprint"] != current.fingerprint
        or [e["chunk"] for e in document["entries"]] != current.chunks
        or document["occurrences"] != current.occurrences
    ):
        raise ValueError("Review differs from current corpus text/source/fingerprint")
    if not chunks:
        raise ValueError("No human-approved evidence; nothing published")
    payload = {
        "review.json": raw,
        "chunks.jsonl": b"".join(
            json.dumps(c, ensure_ascii=False).encode() + b"\n" for c in chunks
        ),
        "occurrences.jsonl": b"".join(
            json.dumps(r, ensure_ascii=False).encode() + b"\n" for r in occurrences
        ),
    }
    manifest = {
        "schema_version": 2,
        "status": "approved",
        "corpus_fingerprint": current.fingerprint,
        "files": {name: {"sha256": sha256(data).hexdigest()} for name, data in payload.items()},
    }
    destination = _safe(output)
    destination.mkdir(parents=False, exist_ok=False)
    # Manifest is the commit marker, written last. Failed writes never yield a valid release.
    for name, data in {**payload, "manifest.json": _bytes(manifest)}.items():
        with (destination / name).open("xb") as stream:
            stream.write(data)
    return destination


def load_approved(folder: Path) -> Corpus:
    """Load only a consistent schema-2 publication with recorded human decisions."""
    folder = _safe(folder)
    manifest = _read(folder / "manifest.json")
    if manifest.get("status") != "approved" or manifest.get("schema_version") != 2:
        raise ValueError("Expected approved schema-2 manifest")
    expected = {"review.json", "chunks.jsonl", "occurrences.jsonl"}
    if set(manifest["files"]) != expected:
        raise ValueError("Unexpected/missing release files")
    payload: dict[str, bytes] = {}
    for name in expected:
        payload[name] = _safe(folder / name).read_bytes()
        if sha256(payload[name]).hexdigest() != manifest["files"][name]["sha256"]:
            raise ValueError(f"Release hash mismatch: {name}")
    review = json.loads(payload["review.json"], object_pairs_hook=_pairs)
    approved, selected = _validate(review)
    chunks = [
        json.loads(line, object_pairs_hook=_pairs) for line in payload["chunks.jsonl"].splitlines()
    ]
    occurrences = [
        json.loads(line, object_pairs_hook=_pairs)
        for line in payload["occurrences.jsonl"].splitlines()
    ]
    if (
        not approved
        or chunks != approved
        or occurrences != selected
        or manifest["corpus_fingerprint"] != review["corpus_fingerprint"]
    ):
        raise ValueError("Publication not covered exactly by review")
    return Corpus(folder, chunks, occurrences, _hash(manifest), manifest)
