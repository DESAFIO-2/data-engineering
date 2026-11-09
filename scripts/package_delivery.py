"""Create a local, allowlisted delivery ZIP; never uploads or includes logs."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
ROOT_FILES = {"README.md", "app.py", "pyproject.toml", "uv.lock", ".env.example"}
TREES = {
    "src": {".py"},
    "scripts": {".py"},
    "tests": {".py"},
    "docs": {".md"},
    "data/raw": {".pdf", ".html", ".txt", ".json", ".jsonl"},
    "data/manifests": {".json", ".jsonl"},
    "data/corpus": {".json", ".jsonl"},
    "data/releases": {".json", ".jsonl"},
    "data/curation": {".json", ".jsonl"},
    "guia": {".md"},
    "evals/datasets": {".json", ".jsonl"},
    "evals/results": {".json", ".jsonl", ".csv", ".md"},
}
BLOCKED = re.compile(
    r"(?:^|[._-])(?:logs?|secrets?|credentials?|tokens?|passwords?|personal|private|"
    r"history|transcripts?|sessions?|cache|caches)(?:$|[._-])",
    re.I,
)
SECRET = re.compile(
    rb"AIza[0-9A-Za-z_-]{35}|sk-(?:proj-)?[0-9A-Za-z_-]{32,}|"
    rb"gh[pousr]_[0-9A-Za-z]{30,}|github_pat_[0-9A-Za-z_]{40,}|"
    rb"AKIA[0-9A-Z]{16}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"
)
ASSIGNMENT = re.compile(
    rb"""(?i)["']?(?:api[_-]?key|access[_-]?token|client[_-]?secret|password)["']?"""
    rb"""\s*[:=]\s*["']([^"'\r\n]{8,})["']"""
)
PLACEHOLDERS = (b"example", b"placeholder", b"your_", b"your-", b"changeme", b"dummy")


def excluded(path: Path) -> bool:
    return any(
        part.startswith(".")
        or part == "__pycache__"
        or part == "experimental-corrected-paused-2026-11-08"
        or BLOCKED.search(part)
        for part in path.parts
    )


def safe_files(root: Path, include_index: bool = False) -> list[Path]:
    """Never traverse links/junctions, hidden folders, caches or unlisted trees."""
    found = [root / name for name in sorted(ROOT_FILES) if (root / name).is_file()]
    trees = dict(TREES)
    if include_index:
        trees["data/vectorstore"] = {".json", ".sqlite3", ".bin", ".pickle"}
    for tree, suffixes in trees.items():
        base = root / tree
        if not base.is_dir() or base.is_symlink() or base.is_junction():
            continue
        for directory, dirs, files in os.walk(base, followlinks=False):
            parent = Path(directory)
            dirs[:] = sorted(
                d
                for d in dirs
                if not excluded(Path(d))
                and not (parent / d).is_symlink()
                and not (parent / d).is_junction()
            )
            for name in sorted(files):
                path = parent / name
                relative = path.relative_to(root)
                if not excluded(relative) and path.suffix.lower() in suffixes:
                    found.append(path)
    result = []
    for path in sorted(set(found)):
        if path.is_symlink() or path.is_junction() or not path.resolve().is_relative_to(root):
            raise ValueError("Link or path outside repository refused")
        result.append(path)
    return result


def inspect_content(relative: Path, content: bytes) -> None:
    """Fail closed on recognizable credentials; never print matching contents."""
    if relative.as_posix() == ".env.example":
        allowed = {
            "APP_GOOGLE_API_KEY",
            "APP_RAG_CHAT_MODEL",
            "APP_RAG_EMBEDDING_MODEL",
            "APP_RAG_RELEASE_DIR",
            "APP_RAG_VECTOR_DIR",
            "APP_RAG_TOP_K",
        }
        for line in content.decode("utf-8-sig").splitlines():
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            key, separator, value = line.partition("=")
            if not separator or key.strip() not in allowed:
                raise ValueError("Unrecognized setting in .env.example")
            if key.strip() == "APP_GOOGLE_API_KEY" and value.strip().strip("\"'"):
                raise ValueError(".env.example must contain an empty API key")
    if SECRET.search(content):
        raise ValueError(f"Credential signature detected: {relative.as_posix()}")
    for match in ASSIGNMENT.finditer(content):
        value = match.group(1).lower()
        if not any(word in value for word in PLACEHOLDERS):
            raise ValueError(f"Possible credential assignment: {relative.as_posix()}")
    if relative.parts[:2] in (("evals", "datasets"), ("evals", "results")):
        if relative.suffix == ".jsonl":
            records = [
                json.loads(line)
                for line in content.decode("utf-8-sig").splitlines()
                if line.strip()
            ]
        elif relative.suffix == ".json":
            value = json.loads(content.decode("utf-8-sig"))
            records = value if isinstance(value, list) else [value]
        else:
            return
        for record in records:
            if not isinstance(record, dict):
                raise ValueError(f"Invalid evaluation record: {relative.as_posix()}")
            if any(key in record for key in ("question", "answer", "reference_answer")):
                if record.get("synthetic") is not True:
                    # Fixed legacy dataset shipped before the synthetic flag existed.
                    legacy = relative.as_posix() == "evals/datasets/retrieval_lote1.jsonl"
                    fields = {"id", "question", "medicine_id", "evidence_id"}
                    if not legacy or set(record) != fields:
                        raise ValueError(f"Unmarked synthetic evaluation: {relative.as_posix()}")


def package(
    root: Path, *, name: str | None = None, include_index: bool = False, dry_run: bool = False
) -> dict[str, object]:
    root = root.resolve(strict=True)
    name = name or f"sus-cidadao-{datetime.now(UTC):%Y%m%dT%H%M%S%fZ}.zip"
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*\.zip", name):
        raise ValueError("Use a simple .zip filename, without directories")
    output_dir = root / "output/semana2"
    for path in (root / "output", output_dir):
        if path.is_symlink() or path.is_junction():
            raise ValueError("Output directory must not be a link")
    destination = output_dir / name
    if destination.exists():
        raise FileExistsError("Package already exists; choose another --name")
    paths = safe_files(root, include_index)
    inventory = []
    # Validate all content before creating an archive. Revalidate bytes when writing.
    for path in paths:
        raw = path.read_bytes()
        relative = path.relative_to(root)
        inspect_content(relative, raw)
        inventory.append(
            {
                "path": relative.as_posix(),
                "bytes": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    manifest = {
        "schema_version": 1,
        "created_at_utc": datetime.now(UTC).isoformat(),
        "include_index": include_index,
        "human_review": "not_granted_by_packaging",
        "files": inventory,
    }
    if dry_run:
        return {"dry_run": True, "destination": str(destination), **manifest}
    output_dir.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".package-", suffix=".tmp", dir=output_dir)
    os.close(descriptor)
    temporary_path = Path(temporary)
    try:
        with ZipFile(temporary_path, "w", compression=ZIP_DEFLATED) as archive:
            for path, record in zip(paths, inventory, strict=True):
                if path.is_symlink() or not path.resolve().is_relative_to(root):
                    raise ValueError("Input path changed during packaging")
                raw = path.read_bytes()
                if hashlib.sha256(raw).hexdigest() != record["sha256"]:
                    raise ValueError("Input changed during packaging; retry after integration")
                inspect_content(path.relative_to(root), raw)
                archive.writestr(str(record["path"]), raw)
            archive.writestr(
                "PACKAGE_MANIFEST.json", json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
            )
        with ZipFile(temporary_path) as archive:
            if archive.testzip() is not None:
                raise ValueError("ZIP integrity verification failed")
        # Exclusive creation prevents overwriting a package created concurrently.
        with destination.open("xb") as target, temporary_path.open("rb") as source:
            while block := source.read(1024 * 1024):
                target.write(block)
    finally:
        temporary_path.unlink(missing_ok=True)
    return {
        "path": str(destination),
        "files": len(inventory),
        "bytes": destination.stat().st_size,
        "sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
        "include_index": include_index,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", help="ZIP filename in output/semana2; existing files refused")
    parser.add_argument("--include-index", action="store_true", help="Include data/vectorstore")
    parser.add_argument("--dry-run", action="store_true", help="Validate and list; write nothing")
    args = parser.parse_args()
    try:
        result = package(
            ROOT, name=args.name, include_index=args.include_index, dry_run=args.dry_run
        )
    except (OSError, ValueError) as exc:
        print(f"Packaging refused ({type(exc).__name__}): {exc}")
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
