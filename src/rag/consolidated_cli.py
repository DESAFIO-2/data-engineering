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
    release_path = Path(args.release)
    if not (release_path / "release.json").is_file():
        dvc_pointer = release_path.with_name(release_path.name + ".dvc")
        if dvc_pointer.is_file():
            raise FileNotFoundError(
                f"Release '{release_path}' não encontrado localmente, mas possui ponteiro DVC "
                f"({dvc_pointer.name}). Execute 'uv run dvc pull' para baixar os artefatos "
                "aprovados ou use um release aprovado local (ex.: "
                "data/releases/corpus-consolidado-v5-aprovado-2026-11-10)."
            )
        raise FileNotFoundError(f"Manifesto release.json não encontrado em '{release_path}'.")
    release = ConsolidatedRelease.load(release_path)
    if args.command == "sync-live":
        from .consolidated_chat import sync_live

        sync_live(release)
        return 0
    chunk_dir = ROOT / "data/derived/chunks" / release.manifest["release_version"]
    if not chunk_dir.exists():
        build_chunks(release, chunk_dir)
    chunks, manifest = load_chunks(release, chunk_dir)
    if args.command == "chat":
        from .consolidated_chat import chat

        return chat(args, settings, release, chunks, manifest)
    if args.command == "index":
        from .providers import google_embeddings

        embeddings = google_embeddings(settings.rag_embedding_model, settings.google_api_keys)
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
        from .consolidated_chat import ask

        ask(
            args.question,
            release,
            chunks,
            manifest,
            settings,
            {},
            documental=args.documental,
            strategy=args.strategy,
            generate=args.command == "ask",
            show_context=args.show_context,
        )
        return 0
    if args.command == "eval":
        if args.dataset is None or args.output is None:
            raise ValueError("Informe --dataset e --output para avaliação consolidada")
        path = Path(args.output)
        if (
            release.manifest["release_version"].startswith("corpus-consolidado-v9-")
            and args.split == "test"
            and path.exists()
        ):
            raise ValueError(f"Resultado v9 test já existe; não sobrescrever: {path}")
        if release.manifest["release_version"] in {
            "corpus-consolidado-v7-aprovado-2026-11-11",
            "corpus-consolidado-v8-aprovado-2026-11-11",
            "corpus-consolidado-v9-aprovado-2026-11-12",
        }:
            from .consolidated_evaluation import evaluate

            v8 = release.manifest["release_version"].startswith("corpus-consolidado-v8-")
            v9 = release.manifest["release_version"].startswith("corpus-consolidado-v9-")
            store = None
            if args.strategy in {"vector", "hybrid"}:
                from .providers import google_embeddings

                embeddings = google_embeddings(
                    settings.rag_embedding_model, settings.google_api_keys
                )
                store = open_index(
                    release,
                    chunks,
                    manifest,
                    ROOT / settings.rag_vector_dir,
                    settings.rag_embedding_model,
                    embeddings,
                )
            result = evaluate(
                dataset=Path(args.dataset),
                release=release,
                chunks=chunks,
                chunk_manifest=manifest,
                strategy=args.strategy,
                split=args.split,
                top_k=settings.rag_top_k,
                store=store,
                embedding_model=settings.rag_embedding_model if store is not None else None,
                review_path=ROOT
                / (
                    "docs/reports/v9/v9-next-independent-test-review.md"
                    if Path(args.dataset).name == "consolidated_v9_next_reviewed.jsonl"
                    else "docs/reports/v9/v9-independent-test-review-v2.md"
                )
                if v9
                else ROOT
                / (
                    "docs/reports/v8/v8-calcium-correction-review.xlsx"
                    if v8
                    else "docs/reports/v7/v7-retrieval-review.xlsx"
                ),
                prior_review_path=ROOT / "docs/reports/v7/v7-retrieval-review.xlsx" if v8 else None,
            )
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            print(
                json.dumps(
                    {k: v for k, v in result.items() if k != "results"},
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 0
        cases = [
            json.loads(x)
            for x in Path(args.dataset).read_text(encoding="utf-8").splitlines()
            if x.strip()
        ]
        store = None
        if args.strategy in {"vector", "hybrid"}:
            from .providers import google_embeddings

            embeddings = google_embeddings(settings.rag_embedding_model, settings.google_api_keys)
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
        path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(
            json.dumps(
                {k: v for k, v in summary.items() if k != "results"}, ensure_ascii=False, indent=2
            )
        )
        return 0
    raise ValueError("Comando não suportado para release consolidado")
