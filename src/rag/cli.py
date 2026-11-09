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
from .conversation import greeting_reply, is_clarification, is_clarification_input
from .evaluate import evaluate_retrieval
from .live import PRODUCTS, live_reply, load_snapshot
from .providers import google_chat, google_embeddings
from .release import Release
from .retrieval import FORM_EXAMPLES, retrieve, retrieve_lexical
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
    documental: bool = False,
    show_context: bool = False,
    history: list[tuple[str, str]] | None = None,
) -> str:
    live = (
        None
        if documental
        else live_reply(
            question, release, load_snapshot(ROOT / "data/gold/infosaude_live_snapshot.json")
        )
    )
    if live is not None:
        print(live)
        return live
    vector_error: Exception | None = None
    try:
        if "store" not in cache:
            embeddings = google_embeddings(settings.rag_embedding_model, settings.google_api_key)
            cache["store"] = open_index(
                release, _path(settings.rag_vector_dir), settings.rag_embedding_model, embeddings
            )
        result = retrieve(question, release, cache["store"], settings.rag_top_k)
    except Exception as exc:
        vector_error = exc
        result = retrieve_lexical(question, release, settings.rag_top_k)
    if vector_error is None and result["status"] != "matched":
        lexical = retrieve_lexical(question, release, settings.rag_top_k)
        if lexical["status"] == "matched":
            result = lexical
            vector_error = RuntimeError("busca vetorial sem evidências")
    if vector_error is not None:
        print(
            f"AVISO: Busca vetorial indisponível ({type(vector_error).__name__}); "
            "resultado conferido pela busca lexical."
        )
        if show_context:
            for rank, evidence in enumerate(result["evidence"], 1):
                print(f"[{rank}] {evidence['evidence_id']}: {evidence['text']}")
        _show(result)
        return result["message"]
    if generate and result["status"] == "matched" and "llm" not in cache:
        cache["llm"] = google_chat(settings.rag_chat_model, settings.google_api_key)
    response = synthesize(question, result, cache.get("llm"), history) if generate else None
    if show_context:
        for rank, evidence in enumerate(result["evidence"], 1):
            print(f"[{rank}] {evidence['evidence_id']}: {evidence['text']}")
    _show(result, response)
    return response or result["message"]


def main() -> int:
    settings = get_settings()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("index", "search", "ask", "chat", "eval", "sync-live"))
    parser.add_argument("question", nargs="?")
    corpus_mode = parser.add_mutually_exclusive_group()
    corpus_mode.add_argument(
        "--experimental", action="store_true", help="Usar corpus candidato isolado"
    )
    corpus_mode.add_argument(
        "--curated", type=Path, help="Release ampliado com revisão humana validada"
    )
    parser.add_argument("--corpus", type=Path, default=ROOT / "data/corpus/experimental")
    parser.add_argument("--supplement", type=Path, help="Chunks complementares opcionais")
    parser.add_argument("--release", type=Path, help="Diretório de release aprovado")
    parser.add_argument(
        "--documental",
        action="store_true",
        help="Desativar consulta InfoSaúde nas respostas; chats ainda sincronizam ao iniciar",
    )
    parser.add_argument("--show-context", action="store_true", help="Exibir trechos e ranking")
    parser.add_argument(
        "--strategy",
        choices=("hybrid", "lexical", "vector", "exact"),
        default="hybrid",
        help="Estratégia para ask/search/eval; no chat o modo híbrido é automático",
    )
    parser.add_argument("--dataset", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--split", choices=("dev", "test"), default="dev")
    parser.add_argument("--allow-draft", action="store_true")
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--frozen-dataset-sha256")
    parser.add_argument(
        "--stage", choices=("retrieval", "generation", "end-to-end"), default="end-to-end"
    )
    args = parser.parse_args()
    try:
        if args.experimental or args.curated:
            from .experimental_cli import run

            return run(args, settings)
        if args.dataset or args.output:
            parser.error("A avaliação ampliada exige --experimental; eval simples mantém o lote 1")
        release = Release.load(_path(args.release or settings.rag_release_dir))
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
            _ask(
                args.question,
                release,
                settings,
                {},
                generate=args.command == "ask",
                documental=args.documental,
                show_context=args.show_context,
            )
            return 0
        print("Sincronizando estoque e localização do InfoSaúde...")
        try:
            _sync_live()
        except (ValueError, requests.RequestException) as exc:
            snapshot = load_snapshot(ROOT / "data/gold/infosaude_live_snapshot.json")
            if snapshot is None:
                print(
                    f"Aviso: sincronização indisponível ({type(exc).__name__}); "
                    "sem snapshot local."
                )
            else:
                print(
                    f"Aviso: sincronização indisponível ({type(exc).__name__}); "
                    "usando o snapshot local anterior."
                )
        print(
            "SUS Cidadão — lote de 6 apresentações. Digite 'sair' para encerrar.\n"
            "A recuperação documental combina correspondência lexical e busca vetorial; "
            "se a vetorial falhar, o chat usa lexical e avisa.\n"
            "Para estoque, informe medicamento + concentração + forma farmacêutica e, "
            "se desejar, a região. Ex.: ‘Tem sinvastatina 40 mg comprimido em Planaltina?’\n"
            f"Formas que pode informar: {', '.join(FORM_EXAMPLES)}. "
            "Se a forma não existir no recorte, serão mostradas as opções disponíveis. "
            "O estoque ao vivo está disponível apenas para apresentações mapeadas.\n"
            "Para consultar informações documentais, pergunte pelo medicamento e dado "
            "desejado, por exemplo: ‘O que consta na RENAME sobre metformina 500 mg comprimido?’ "
            "O chat mantém apenas o contexto desta conversa, em memória."
        )
        cache: dict[str, Any] = {}
        history: list[tuple[str, str]] = []
        pending: str | None = None
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
                greeting = greeting_reply(question)
                if greeting:
                    print(f"\nAgente: {greeting}")
                    history.append((question, greeting))
                    continue
                if pending and is_clarification_input(question):
                    question = f"{pending} {question}"
                print("\nAgente: ", end="")
                reply = _ask(
                    question,
                    release,
                    settings,
                    cache,
                    generate=True,
                    documental=args.documental,
                    show_context=args.show_context,
                    history=history,
                )
                pending = question if is_clarification(reply) else None
                history.append((question, reply))
    except (FileNotFoundError, ValueError, ImportError, requests.RequestException) as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1
    except RuntimeError as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(
            f"Dependência indisponível ({type(exc).__name__}); resposta não gerada.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
