"""Indexação, recuperação e conversa no terminal."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import requests

from ingestion.infosaude_live import sync_snapshot
from rag.consolidated.answer import synthesize
from rag.core.config import ROOT, Settings, get_settings
from rag.core.conversation import greeting_reply, is_clarification, is_clarification_input
from rag.core.providers import google_chat, google_embeddings
from rag.legacy.evaluate import evaluate_retrieval
from rag.legacy.live import PRODUCTS, live_reply, load_snapshot
from rag.legacy.release import Release
from rag.legacy.retrieval import FORM_EXAMPLES, retrieve, retrieve_lexical
from rag.legacy.vector import build_index, open_index


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


def _show(result: dict[str, Any], response: str | None = None, *, show_limits: bool = True) -> None:
    print(response or result["message"])
    if result["status"] == "matched":
        print("\nFontes consultadas:")
        for evidence in result["evidence"]:
            source = evidence["source"]
            print(
                f"- {source['source_id']} ({source['version']}), página {source['page']}: "
                f"{source['url']} [evidência {evidence['evidence_id']}]"
            )
        if show_limits:
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
            embeddings = google_embeddings(settings.rag_embedding_model, settings.google_api_keys)
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
        return str(result["message"])
    if generate and result["status"] == "matched" and "llm" not in cache:
        cache["llm"] = google_chat(settings.rag_chat_model, settings.google_api_keys)
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
        "--validated", action="store_true", help="Usar corpus consolidado com revisão aprovada"
    )
    corpus_mode.add_argument(
        "--curated", type=Path, help="Release ampliado com revisão humana validada"
    )
    parser.add_argument("--corpus", type=Path)
    parser.add_argument("--supplement", type=Path, help="Chunks complementares opcionais")
    parser.add_argument("--release", type=Path, help="Diretório de release aprovado")
    parser.add_argument(
        "--documental",
        action="store_true",
        help="Desativar consulta InfoSaúde; chat consolidado também desativa sincronização",
    )
    parser.add_argument("--show-context", action="store_true", help="Exibir trechos e ranking")
    parser.add_argument(
        "--strategy",
        choices=("hybrid", "lexical", "vector", "exact"),
        default="hybrid",
        help="Estratégia para ask/search/eval e chat consolidado; padrão híbrido",
    )
    parser.add_argument("--dataset", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--split", choices=("dev", "test"), default="dev")
    parser.add_argument("--allow-draft", action="store_true")
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--embedding-requests-per-minute", type=int, default=80)
    parser.add_argument("--frozen-dataset-sha256")
    parser.add_argument(
        "--stage", choices=("retrieval", "generation", "end-to-end"), default="end-to-end"
    )
    args = parser.parse_args()
    if args.corpus is None:
        args.corpus = ROOT / "data/corpus/experimental"
    try:
        if args.experimental or args.validated or args.curated:
            from rag.cli.experimental import run

            return run(args, settings)
        if args.dataset or args.output:
            if not args.release:
                parser.error("Informe --release para avaliação consolidada ou use --experimental")
        selected_release = _path(args.release or settings.rag_release_dir)
        if args.command in {"index", "search", "ask", "chat", "sync-live", "eval"}:
            import json

            manifest_path = selected_release / "release.json"
            if not manifest_path.is_file():
                from rag.cli.consolidated import run as run_consolidated

                args.release = selected_release
                return run_consolidated(args, settings)
            manifest = json.loads(manifest_path.read_bytes())
            if manifest.get("schema_version") == "consolidated-release-v2":
                from rag.cli.consolidated import run as run_consolidated

                args.release = selected_release
                return run_consolidated(args, settings)
            print(
                "Aviso: executando no lote legado (18 evidências); "
                "prefira um release consolidado (v5 local ou v9 via DVC).",
                file=sys.stderr,
            )
        release = Release.load(selected_release)
        if args.command == "sync-live":
            _sync_live()
            return 0
        if args.command == "index":
            embeddings = google_embeddings(settings.rag_embedding_model, settings.google_api_keys)
            location = build_index(
                release, _path(settings.rag_vector_dir), settings.rag_embedding_model, embeddings
            )
            print(f"Chroma pronto: {location} ({len(release.evidence)} evidências)")
            return 0
        if args.command == "eval":
            embeddings = google_embeddings(settings.rag_embedding_model, settings.google_api_keys)
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
                    f"Aviso: sincronização indisponível ({type(exc).__name__}); sem snapshot local."
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
        from rag.core.providers import error_detail

        print(
            f"Falha na operação: {error_detail(exc)}",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
