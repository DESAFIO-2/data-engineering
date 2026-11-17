"""Restaura Chroma em área temporária com os vetores locais do modelo publicado."""

import json
import shutil
from collections import Counter, defaultdict
from pathlib import Path
from tempfile import TemporaryDirectory

from langchain_chroma import Chroma

from rag.config import ROOT
from rag.consolidated import ConsolidatedRelease, index_location, load_chunks, open_index


def main() -> None:
    version = "corpus-consolidado-v9-aprovado-2026-11-12"
    release = ConsolidatedRelease.load(ROOT / "data/releases" / version)
    chunks, manifest = load_chunks(release, ROOT / "data/derived/chunks" / version)
    model = "models/gemini-embedding-2"
    source = index_location(ROOT / "data/vectorstore/chroma", release, manifest, model)
    groups = defaultdict(list)
    occurrences = {o["occurrence_id"]: o for o in release.occurrences}
    for c in chunks:
        groups[c["text"]].append(c)
    duplicates = []
    for group in groups.values():
        if len(group) < 2:
            continue
        rows = [occurrences[c["occurrence_id"]] for c in group]
        duplicates.append(
            [
                dict(
                    evidence=c["evidence_id"],
                    medicine=c["medicine_id"],
                    source=c["source"]["source_id"],
                    page=c["source"]["page"],
                    code=o.get("source_code"),
                    channel=o.get("channel"),
                    row=o.get("source_row_number"),
                )
                for c, o in zip(group, rows, strict=True)
            ]
        )
    with TemporaryDirectory() as directory:
        base = Path(directory)
        copied = base / "snapshot"
        shutil.copytree(source, copied)
        collection = "sus_cidadao_consolidado"
        original = Chroma(collection_name=collection, persist_directory=str(copied))
        restored_path = index_location(base, release, manifest, model)
        restored = Chroma(collection_name=collection, persist_directory=str(restored_path))
        for start in range(0, len(chunks), 128):
            batch = original.get(
                ids=[c["chunk_id"] for c in chunks[start : start + 128]],
                include=["documents", "embeddings", "metadatas"],
            )
            restored._collection.add(
                ids=batch["ids"],
                documents=batch["documents"],
                embeddings=batch["embeddings"],
                metadatas=batch["metadatas"],
            )
            read = restored.get(ids=batch["ids"], include=["documents", "embeddings", "metadatas"])
            assert read["ids"] == batch["ids"]
            assert (
                read["documents"] == batch["documents"] and read["metadatas"] == batch["metadatas"]
            )
            assert (read["embeddings"] == batch["embeddings"]).all()
        shutil.copyfile(source / "index.json", restored_path / "index.json")
        open_index(release, chunks, manifest, base, model, None)
        print(
            json.dumps(
                dict(
                    release=release.fingerprint,
                    model=model,
                    restored_chunks=len(chunks),
                    embedding_calls=0,
                    by_source=Counter(c["source"]["source_id"] for c in chunks),
                    duplicate_groups=duplicates,
                ),
                ensure_ascii=False,
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
