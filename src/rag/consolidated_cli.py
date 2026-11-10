"""Explicit CLI for the approved consolidated release; does not change defaults."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import ROOT, Settings
from .consolidated import (
    ConsolidatedRelease,
    build_chunks,
    build_index,
    load_chunks,
    open_index,
    search,
)


def run(args: Any, settings: Settings) -> int:
    release = ConsolidatedRelease.load(Path(args.release))
    chunk_dir = ROOT / "data/derived/chunks" / release.manifest["release_version"]
    if not chunk_dir.exists():
        build_chunks(release, chunk_dir)
    chunks, manifest = load_chunks(release, chunk_dir)
    if args.command == "index":
        from .providers import google_embeddings

        embeddings = google_embeddings(settings.rag_embedding_model, settings.google_api_key)
        path = build_index(
            release,
            chunks,
            manifest,
            ROOT / settings.rag_vector_dir,
            settings.rag_embedding_model,
            embeddings,
            requests_per_minute=args.embedding_requests_per_minute,
        )
        print(f"Índice consolidado pronto: {path} ({len(chunks)} chunks)")
        return 0
    if args.command in {"search", "ask"}:
        if not args.question:
            raise ValueError("Informe uma pergunta")
        store = None
        if args.strategy in {"vector", "hybrid"} and settings.google_api_key:
            from .providers import google_embeddings

            embeddings = google_embeddings(settings.rag_embedding_model, settings.google_api_key)
            try:
                store = open_index(
                    release,
                    chunks,
                    manifest,
                    ROOT / settings.rag_vector_dir,
                    settings.rag_embedding_model,
                    embeddings,
                )
            except FileNotFoundError:
                if args.strategy == "vector":
                    raise
                print("Índice ainda não gerado; busca lexical usada.")
        result = search(args.question, release, chunks, store, args.strategy, settings.rag_top_k)
        print(result["message"])
        for ev in result["evidence"]:
            src = ev["source"]
            print(
                f"- {src['source_id']} {src['version']}, p. {src['page']}: "
                f"{src['url']} [{ev['evidence_id']}]"
            )
        return 0
    if args.command == "eval":
        if args.dataset is None or args.output is None:
            raise ValueError("Informe --dataset e --output para avaliação consolidada")
        cases = [json.loads(x) for x in Path(args.dataset).read_text().splitlines() if x.strip()]
        store = None
        if args.strategy in {"vector", "hybrid"}:
            from .providers import google_embeddings

            embeddings = google_embeddings(settings.rag_embedding_model, settings.google_api_key)
            store = open_index(
                release,
                chunks,
                manifest,
                ROOT / settings.rag_vector_dir,
                settings.rag_embedding_model,
                embeddings,
            )
        records = []
        for case in cases:
            result = search(
                case["question"], release, chunks, store, args.strategy, settings.rag_top_k
            )
            retrieved = [e["evidence_id"] for e in result["evidence"]]
            relevant = set(case["relevant_ids"])
            rank = next((i for i, eid in enumerate(retrieved, 1) if eid in relevant), None)
            records.append(
                {
                    "id": case["id"],
                    "source_id": case.get("source_id"),
                    "split": case["split"],
                    "expected_status": case["expected_status"],
                    "status": result["status"],
                    "relevant_ids": case["relevant_ids"],
                    "retrieved_ids": retrieved,
                    "first_relevant_rank": rank,
                    "status_correct": result["status"] == case["expected_status"],
                }
            )
        matched = [
            r for r in records if r["expected_status"] == "matched" and r["split"] == args.split
        ]
        selected = [r for r in records if r["split"] == args.split]
        summary = {
            "release_version": release.manifest["release_version"],
            "release_fingerprint": release.fingerprint,
            "embedding_model": settings.rag_embedding_model if store is not None else None,
            "strategy": args.strategy,
            "dataset_sha256": __import__("hashlib")
            .sha256(Path(args.dataset).read_bytes())
            .hexdigest(),
            "split": args.split,
            "cases": len(selected),
            "matched_cases": len(matched),
            "hit_at_5": sum(
                r["first_relevant_rank"] is not None and r["first_relevant_rank"] <= 5
                for r in matched
            )
            / len(matched)
            if matched
            else None,
            "mrr_at_5": sum(
                1 / r["first_relevant_rank"]
                if r["first_relevant_rank"] is not None and r["first_relevant_rank"] <= 5
                else 0
                for r in matched
            )
            / len(matched)
            if matched
            else None,
            "status_accuracy": sum(r["status_correct"] for r in selected) / len(selected)
            if selected
            else None,
            "reviewed_cases": sum(
                c.get("review_status") == "reviewed" and c["split"] == args.split for c in cases
            ),
            "results": selected,
        }
        summary["by_source"] = {
            sid: {
                "cases": len(group),
                "hit_at_5": sum(
                    r["first_relevant_rank"] is not None and r["first_relevant_rank"] <= 5
                    for r in group
                )
                / len(group),
            }
            for sid in ("F01", "F03", "F04")
            if (group := [r for r in matched if r["source_id"] == sid])
        }
        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
        print(
            json.dumps(
                {k: v for k, v in summary.items() if k != "results"}, ensure_ascii=False, indent=2
            )
        )
        return 0
    raise ValueError("Comando não suportado para release consolidado")
