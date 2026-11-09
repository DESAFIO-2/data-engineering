"""Rebuild the archived v1 corpus snapshot without changing the source export."""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from hashlib import sha256
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rag.experimental import rows  # noqa: E402


def jsonl_bytes(records: list[dict[str, Any]]) -> bytes:
    return "".join(
        json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n" for record in records
    ).encode("utf-8")


def main() -> None:
    source = ROOT / "data/curation/revisao-corpus-v1.json"
    supplement_path = ROOT / "data/raw/complementares/chunks.jsonl"
    target = ROOT / "data/corpus/experimental-v1-restored-3b320bf2"
    if target.exists():
        raise SystemExit(f"Destino já existe; não sobrescrevendo: {target}")
    archived = json.loads(source.read_text(encoding="utf-8"))
    archived_entries = archived["entries"]
    all_exported = [entry["chunk"] for entry in archived_entries]
    primary = [chunk for chunk in all_exported if chunk.get("chunk_type")]
    supplemental = [chunk for chunk in all_exported if not chunk.get("chunk_type")]
    supplement = rows(supplement_path)
    old_by_id = {chunk["evidence_id"]: chunk for chunk in supplemental}
    current_by_id = {chunk["evidence_id"]: chunk for chunk in supplement}
    if old_by_id.keys() != current_by_id.keys() or any(
        old_by_id[eid]["text"] != current_by_id[eid]["text"]
        or old_by_id[eid]["source"] != current_by_id[eid]["source"]
        for eid in old_by_id
    ):
        raise SystemExit("Suplemento atual não corresponde ao snapshot v1; restauração cancelada")
    occurrences = archived["occurrences"]
    catalog: dict[str, dict[str, Any]] = {}
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in occurrences:
        if row.get("medicine_id") and row.get("item_type") == "medicine":
            grouped[row["medicine_id"]].append(row)
    for medicine_id, matching in grouped.items():
        first = matching[0]
        catalog[medicine_id] = {
            "medicine_id": medicine_id,
            "active_ingredient": first.get("active_ingredient"),
            "strength": first.get("strength"),
            "form": first.get("form"),
            "review_status": "pending",
            "occurrence_ids": [row["occurrence_id"] for row in matching],
            "source_ids": sorted({row["source"]["source_id"] for row in matching}),
        }
    report = {
        "schema_version": "restored-v1",
        "status": "experimental",
        "review_status": "pending",
        "human_verified": False,
        "restored_from": "data/curation/revisao-corpus-v1.json",
        "corpus_fingerprint": archived["corpus_fingerprint"],
        "occurrences": len(occurrences),
        "primary_chunks": len(primary),
        "supplemental_chunks": len(supplement),
        "chunks": len(primary) + len(supplement),
        "catalog_presentations": len(catalog),
        "limitations": [
            "Reconstituted historical snapshot; not human-reviewed or approved",
            "Historical identity proven against the hash-verified archived review export",
        ],
    }
    files: dict[str, dict[str, Any]] = {}
    contents = {
        "chunks.jsonl": jsonl_bytes(primary),
        "occurrences.jsonl": jsonl_bytes(occurrences),
        "catalog.jsonl": jsonl_bytes(list(catalog.values())),
        "report.json": (
            json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
        ).encode("utf-8"),
    }
    for name, content in contents.items():
        records = len(catalog) if name == "catalog.jsonl" else None
        if name == "chunks.jsonl":
            records = len(primary)
        elif name == "occurrences.jsonl":
            records = len(occurrences)
        files[name] = {"sha256": sha256(content).hexdigest(), "bytes": len(content)}
        if records is not None:
            files[name]["records"] = records
    manifest = {
        "schema_version": "restored-v1",
        "status": "experimental",
        "review_status": "pending",
        "parser_version": "historical-v1-reconstruction",
        "files": files,
        "restoration": {
            "corpus_fingerprint": archived["corpus_fingerprint"],
            "source_path": "data/curation/revisao-corpus-v1.json",
            "source_sha256": sha256(source.read_bytes()).hexdigest(),
            "method": (
                "chunk/occurrence and provenance equality against archived export; "
                "index ID/content verification"
            ),
        },
    }
    target.mkdir(parents=True)
    for name, content in contents.items():
        (target / name).write_bytes(content)
    (target / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"target": str(target), **report}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
