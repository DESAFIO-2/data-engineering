"""Pipeline executável raw -> Bronze -> Silver -> Gold para os PDFs coletados."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

from pypdf import PdfReader


def run_document_pipeline(root: Path) -> dict[str, int]:
    manifest = json.loads((root / "data/manifests/coleta-inicial-pdfs-2026-11-03.json").read_text())
    now = datetime.now(UTC).isoformat()
    bronze_count = silver_count = 0
    catalog: list[dict[str, Any]] = []
    for source in manifest["sources"]:
        raw_path = root / "data" / source["path"]
        digest = sha256(raw_path.read_bytes()).hexdigest()
        pages: list[dict[str, Any]] = [
            {"page": n, "text": (page.extract_text() or "").strip()}
            for n, page in enumerate(PdfReader(str(raw_path)).pages, 1)
        ]
        bronze_dir = root / "data/bronze" / source["source_id"] / now[:10].replace("-", "/")
        bronze_dir.mkdir(parents=True, exist_ok=True)
        bronze = bronze_dir / f"{digest}.json"
        if not bronze.exists():
            bronze.write_text(
                json.dumps(
                    {
                        "metadata": {
                            "source_id": source["source_id"],
                            "source_url": source["source_url"],
                            "final_url": source.get("final_url"),
                            "collected_at_utc": source.get("collected_at_utc"),
                            "processed_at_utc": now,
                            "http_status": source.get("http_status"),
                            "content_sha256": digest,
                            "raw_path": source["path"],
                        },
                        "payload": {"format": "pdf", "pages": pages},
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            bronze_count += 1
        silver_dir = root / "data/silver" / source["source_id"]
        silver_dir.mkdir(parents=True, exist_ok=True)
        silver = silver_dir / f"{digest}.jsonl"
        if not silver.exists():
            with silver.open("w", encoding="utf-8") as stream:
                for item in pages:
                    stream.write(
                        json.dumps(
                            {
                                "source_id": source["source_id"],
                                "source_url": source["source_url"],
                                "content_sha256": digest,
                                "page": item["page"],
                                "text": item["text"],
                                "text_length": len(item["text"]),
                                "extracted_at_utc": now,
                            },
                            ensure_ascii=False,
                        )
                        + "\n"
                    )
                    silver_count += 1
        catalog.append(
            {
                "source_id": source["source_id"],
                "title": raw_path.name,
                "source_url": source["source_url"],
                "content_sha256": digest,
                "pages": len(pages),
                "non_empty_pages": sum(bool(p["text"]) for p in pages),
                "silver_path": str(silver.relative_to(root)),
            }
        )
    gold = root / "data/gold"
    gold.mkdir(parents=True, exist_ok=True)
    (gold / "document_catalog.json").write_text(
        json.dumps({"generated_at_utc": now, "documents": catalog}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return {"documents": len(catalog), "bronze": bronze_count, "silver_pages": silver_count}


if __name__ == "__main__":
    print(
        json.dumps(run_document_pipeline(Path(__file__).resolve().parents[2]), ensure_ascii=False)
    )
