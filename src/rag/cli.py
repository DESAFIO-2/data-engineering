"""Indexação, recuperação e conversa no terminal."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import requests

from ingestion.infosaude_live import sync_snapshot

from .answer import synthesize
from .config import ROOT, Settings, get_settings
from .evaluate import evaluate_retrieval
from .live import PRODUCTS, live_reply, load_snapshot
from .providers import google_chat, google_embeddings
from .release import Release
from .retrieval import retrieve
from .vector import build_index, open_index


def _path(value: Path) -> Path:
    return value if value.is_absolute() else (ROOT / value).resolve()


def _sync_live() -> dict[str, Any]:
    snapshot = sync_snapshot(
        ROOT / "data/gold/infosaude_live_snapshot.json",
        tuple(code for code, _ in PRODUCTS.values()),
    )
    print(
        f"InfoSaúde sincronizado: {len(snapshot['ceaf_stock'])} linhas CEAF, "
        f"{len(snapshot['ubs_stock'])} linhas UBS e "
        f"{len(snapshot['locations'])} unidades."
    )
    return snapshot


def _show(result: dict[str, Any], response: str | None = None) -> None:
    print(response or result["message"])
    if result["status"] == "matched":
        print("\nFontes consultadas:")
        for evidence in result["evidence"]:
            source = evidence["source"]
            print(
                f"- {source['source_id']} ({source['version']}), página {source['page']}: "
                f"{source['url']} [evidência {evidence['evidence_id']}]"
            )
        print(
            "\nLimite desta resposta documental: presença em lista não garante estoque; "
            "documentos e elegibilidade não verificados."
        )


def _ask(
    question: str,
    release: Release,
    settings: Settings,
    cache: dict[str, Any],
    *,
    generate: bool,
) -> None:
    live = live_reply(
        question, release, load_snapshot(ROOT / "data/gold/infosaude_live_snapshot.json")
    )
    if live is not None:
        print(live)
        return
    if "store" not in cache:
        embeddings = google_embeddings(settings.rag_embedding_model, settings.google_api_key)
        cache["store"] = open_index(
            release, _path(settings.rag_vector_dir), settings.rag_embedding_model, embeddings
        )
    result = retrieve(question, release, cache["store"], settings.rag_top_k)
    if generate and "llm" not in cache:
        cache["llm"] = google_chat(settings.rag_chat_model, settings.google_api_key)
    response = synthesize(question, result, cache["llm"]) if generate else None
    _show(result, response)


def main() -> int:
    settings = get_settings()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("index", "search", "ask", "chat", "eval", "sync-live"))
    parser.add_argument("question", nargs="?")
    args = parser.parse_args()
    try:
        release = Release.load(_path(settings.rag_release_dir))
        if args.command == "sync-live":
            _sync_live()
            return 0
        if args.command == "index":
            embeddings = google_embeddings(settings.rag_embedding_model, settings.google_api_key)
            location = build_index(
                release, _path(settings.rag_vector_dir), settings.rag_embedding_model, embeddings
            )
            print(f"Chroma pronto: {location} ({len(release.evidence)} evidências)")
            return 0
        if args.command == "eval":
            embeddings = google_embeddings(settings.rag_embedding_model, settings.google_api_key)
            store = open_index(
                release, _path(settings.rag_vector_dir), settings.rag_embedding_model, embeddings
            )
            dataset = ROOT / "evals/datasets/retrieval_lote1.jsonl"
            summary = evaluate_retrieval(dataset, release, store, settings.rag_top_k)
            print(
                f"Match exato: {summary['exact_hits']}/{summary['total']}; "
                f"Hit@{settings.rag_top_k} vetorial: "
                f"{summary['vector_hits']}/{summary['total']}"
            )
            for error in summary["errors"]:
                print(f"- {error}")
            return 0 if not summary["errors"] else 2
        if args.command in ("search", "ask"):
            if not args.question:
                parser.error("Informe a pergunta entre aspas.")
            _ask(args.question, release, settings, {}, generate=args.command == "ask")
            return 0
        print("Sincronizando estoque e localização do InfoSaúde...")
        try:
            _sync_live()
        except (ValueError, requests.RequestException) as exc:
            snapshot = load_snapshot(ROOT / "data/gold/infosaude_live_snapshot.json")
            if snapshot is None:
                print(
                    f"Aviso: sincronização indisponível ({exc}). "
                    "Sem dados locais de estoque/localização."
                )
            else:
                print(f"Aviso: sincronização indisponível ({exc}). Usando o último snapshot salvo.")
        print("SUS Cidadão — lote de 6 apresentações. Digite 'sair' para encerrar.")
        cache: dict[str, Any] = {}
        while True:
            try:
                question = input("\nVocê: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nAté logo.")
                return 0
            if question.lower() in {"sair", "fim", "exit"}:
                print("Até logo.")
                return 0
            if question:
                print("\nAgente: ", end="")
                _ask(question, release, settings, cache, generate=True)
    except (FileNotFoundError, ValueError, ImportError, requests.RequestException) as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
