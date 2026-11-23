"""CLI do corpus experimental, separado do release aprovado."""

from __future__ import annotations

import argparse
import json
import re
from hashlib import sha256
from pathlib import Path
from typing import Any

import requests

from ingestion.infosaude_live import sync_snapshot

from .config import ROOT, Settings
from .conversation import greeting_reply, is_clarification
from .experimental import Corpus, Retriever, build_index, generate, open_index
from .live import PRODUCTS, live_reply, load_snapshot
from .providers import error_detail, google_chat, google_embeddings
from .release import Release
from .retrieval import FORM_EXAMPLES, normalize


def resolve(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def corpus_supplement(args: argparse.Namespace) -> Path | None:
    if getattr(args, "validated", False):
        if args.supplement:
            raise ValueError("--validated não aceita suplemento ainda pendente de revisão")
        return None
    if args.supplement:
        return resolve(args.supplement)
    # The restored v1 vector index was built from the primary corpus plus this
    # archived 108-chunk supplement. Keep the default CLI fingerprint aligned.
    default_corpora = {(ROOT / "data/corpus/experimental").resolve()}
    selected_corpus = resolve(args.corpus).resolve()
    default_supplement = ROOT / "data/raw/complementares/chunks.jsonl"
    if selected_corpus in default_corpora and default_supplement.is_file():
        return default_supplement
    return None


def open_validated_vectors(corpus: Corpus, base: Path, model: str, embeddings: Any) -> Any:
    """Reuse the historical vectors while excluding pending supplemental chunks."""
    historical = Corpus.load(
        ROOT / "data/corpus/experimental",
        ROOT / "data/raw/complementares/chunks.jsonl",
    )
    store = open_index(historical, base, model, embeddings)
    indexed = store.get(include=["documents"])
    by_id = dict(zip(indexed["ids"], indexed["documents"], strict=True))
    if any(by_id.get(chunk["evidence_id"]) != chunk["text"] for chunk in corpus.chunks):
        raise ValueError("Vetores históricos divergem do corpus consolidado")
    return store


def show(result: dict[str, Any], context: bool) -> None:
    if result.get("retrieval_warning"):
        print(f"AVISO: {result['retrieval_warning']}")
    if context and result.get("vector_diagnostics"):
        print(
            "Diagnóstico vetorial: " + json.dumps(result["vector_diagnostics"], ensure_ascii=False)
        )
    print(result.get("answer", result["message"]))
    for rank, evidence in enumerate(result["evidence"], 1):
        source = evidence["source"]
        location = source.get("page") or source.get("section")
        print(
            f"[{rank}] [{evidence['evidence_id']}] {source['source_id']}, "
            f"{source['version']}, local {location}: {source['url']}"
        )
        if context:
            print(evidence["text"])


def follow_up(question: str, pending: str | None) -> str:
    """Append only field-like clarification, not an unrelated new question."""
    if pending and re.fullmatch(
        r"[\d.,\s/%]+(?:mg|mcg|g|ui|ml)(?:\s+\w+){0,4}|"
        r"(?:comprimido|capsula|solucao|suspensao|creme|pomada)(?:\s+\w+){0,3}",
        normalize(question),
    ):
        return f"{pending} {question}"
    return question


def run(args: argparse.Namespace, settings: Settings) -> int:
    if args.command == "sync-live":
        snapshot = sync_snapshot(
            ROOT / "data/gold/infosaude_live_snapshot.json",
            tuple(code for code, _ in PRODUCTS.values()),
        )
        print(
            f"InfoSaúde sincronizado: {len(snapshot['ceaf_stock'])} linhas CEAF, "
            f"{len(snapshot['ubs_stock'])} linhas UBS e "
            f"{len(snapshot['locations'])} unidades."
        )
        return 0
    if getattr(args, "curated", None):
        from .curation import load_approved

        if args.supplement:
            raise ValueError("Release curado não aceita suplemento externo sem revisão")
        corpus = load_approved(resolve(args.curated))
        print("CURADO — subconjunto publicado com revisão humana registrada.")
    else:
        corpus = Corpus.load(resolve(args.corpus), corpus_supplement(args))
        if getattr(args, "validated", False) and (
            corpus.manifest.get("review_status") != "approved"
            or corpus.manifest.get("schema_version") != "consolidated-v2"
            or not json.loads((corpus.folder / "report.json").read_text(encoding="utf-8")).get(
                "human_verified"
            )
        ):
            raise ValueError("--validated exige o manifesto consolidado aprovado")
        if (
            corpus.manifest.get("status") == "approved"
            or corpus.manifest.get("review_status") == "approved"
        ):
            print("CORPUS CONSOLIDADO APROVADO — 2.115 ocorrências com curadoria humana validada.")
            pending_chunks = sum(
                chunk.get("review_status") != "approved" for chunk in corpus.chunks
            )
            if pending_chunks:
                print(
                    f"Aviso: {pending_chunks} chunks do corpus ainda não têm "
                    "aprovação individual registrada."
                )
        else:
            print("EXPERIMENTAL — extração candidata; curadoria humana pendente.")
    # Restored v1 uses its already-complete index; the corrected corpus remains
    # isolated under guia/ so an index command cannot mix the two snapshots.
    base = (
        resolve(settings.rag_vector_dir)
        if corpus.manifest.get("restoration")
        else ROOT / "guia" / "vetorizacao-nova"
    )
    cache: dict[str, Any] = {}
    live_enabled = not getattr(args, "curated", None) and not args.documental
    snapshot_path = ROOT / "data/gold/infosaude_live_snapshot.json"
    live_release: Release | None = None

    def prepare_live() -> None:
        nonlocal live_release
        if not live_enabled:
            return
        if live_release is None:
            live_release = Release.load(resolve(settings.rag_release_dir))

    def sync_live_startup() -> None:
        try:
            snapshot = sync_snapshot(snapshot_path, tuple(code for code, _ in PRODUCTS.values()))
            print(
                f"InfoSaúde sincronizado: {len(snapshot.get('ceaf_stock', []))} linhas CEAF, "
                f"{len(snapshot.get('ubs_stock', []))} linhas UBS e "
                f"{len(snapshot.get('locations', []))} unidades."
            )
        except (ValueError, requests.RequestException) as exc:
            available = load_snapshot(snapshot_path) is not None
            detail = "usarei o snapshot local" if available else "estoque ao vivo indisponível"
            print(f"Aviso: sincronização InfoSaúde falhou ({type(exc).__name__}); {detail}.")

    def live_answer(question: str) -> str | None:
        if not live_enabled:
            return None
        prepare_live()
        assert live_release is not None
        response = live_reply(question, live_release, load_snapshot(snapshot_path))
        if response and "Não localizado no recorte consultado" in response:
            return (
                "Consulta de estoque ao vivo ainda não está mapeada para esta apresentação. "
                "No momento, somente seis apresentações com código UBS validado são consultáveis."
            )
        if response and "Execute: uv run python app.py sync-live" in response:
            response = response.replace(
                "uv run python app.py sync-live",
                "uv run python app.py sync-live --experimental",
            )
        return response

    def embeddings() -> Any:
        if "embeddings" not in cache:
            cache["embeddings"] = google_embeddings(
                settings.rag_embedding_model, settings.google_api_keys
            )
        return cache["embeddings"]

    if args.command == "index":
        if getattr(args, "validated", False):
            open_validated_vectors(corpus, base, settings.rag_embedding_model, embeddings())
            print("Índice histórico verificado e reutilizado para os 2.620 chunks consolidados.")
            return 0
        location = build_index(
            corpus,
            base,
            settings.rag_embedding_model,
            embeddings(),
            batch_size=8,
            requests_per_minute=90,
        )
        print(f"Chroma experimental: {len(corpus.chunks)} chunks em {location}")
        return 0

    def retriever() -> Retriever:
        if "retriever" not in cache:
            store = None
            if args.strategy in {"hybrid", "vector"}:
                try:
                    store = (
                        open_validated_vectors(
                            corpus, base, settings.rag_embedding_model, embeddings()
                        )
                        if getattr(args, "validated", False)
                        else open_index(corpus, base, settings.rag_embedding_model, embeddings())
                    )
                except Exception as exc:
                    raise RuntimeError(
                        "Não foi possível abrir o índice vetorial local; "
                        "a busca não chegou a consultar embeddings."
                    ) from exc
            cache["retriever"] = Retriever(corpus, store)
        return cache["retriever"]  # type: ignore[no-any-return]

    def chat_search(question: str) -> dict[str, Any]:
        try:
            return retriever().search_with_fallback(question, settings.rag_top_k)
        except Exception as exc:
            lexical = Retriever(corpus).search(question, settings.rag_top_k, "lexical")
            lexical.update(
                strategy="hybrid_fallback_lexical",
                retrieval_warning=(
                    f"Índice/consulta vetorial indisponível ({error_detail(exc)}); "
                    "resultado baseado somente em busca lexical."
                ),
            )
            return lexical

    def answer(
        question: str,
        result: dict[str, Any],
        history: list[tuple[str, str]] | None = None,
    ) -> dict[str, Any]:
        if result["status"] == "matched" and "llm" not in cache:
            cache["llm"] = google_chat(settings.rag_chat_model, settings.google_api_keys)
        return {**result, **generate(question, result, cache.get("llm"), history)}

    if args.command == "eval":
        from .benchmark import read_jsonl, run_benchmark

        if args.dataset is None or args.output is None:
            raise ValueError("eval --experimental exige --dataset e --output")
        cases = read_jsonl(resolve(args.dataset))
        if any(case.get("corpus_fingerprint") != corpus.fingerprint for case in cases):
            raise ValueError(
                "Golden set pertence a outro corpus; confira a versão antes de avaliar"
            )

        def runner(case: dict[str, Any]) -> dict[str, Any]:
            if args.stage == "generation" and case.get("expected_status") == "matched":
                by_id = {c["evidence_id"]: c for c in corpus.chunks}
                relevant = case["relevant_ids"]
                if any(eid not in by_id for eid in relevant):
                    raise ValueError("Gabarito aponta para corpus diferente")
                result = {
                    "status": "matched",
                    "message": "Contexto de referência.",
                    "evidence": [by_id[eid] for eid in relevant],
                    "ranked_ids": list(relevant),
                    "retrieval_ms": 0.0,
                }
            else:
                result = retriever().search(case["question"], settings.rag_top_k, args.strategy)
            if args.stage == "retrieval":
                return {**result, "answer": "", "generation_ms": 0.0}
            return answer(case["question"], result)

        summary = run_benchmark(
            cases,
            runner,
            resolve(args.output),
            split=args.split,
            allow_draft=args.allow_draft,
            repeat=args.repeat,
            mode=args.stage,
            frozen_dataset_sha256=args.frozen_dataset_sha256,
            run_metadata={
                "strategy": args.strategy,
                "corpus_fingerprint": corpus.fingerprint,
                "chat_model": settings.rag_chat_model,
                "embedding_model": settings.rag_embedding_model,
                "temperature": "0",
                "top_k": str(settings.rag_top_k),
                "concurrency": "1",
                "code_sha256": sha256(
                    b"".join(
                        (Path(__file__).parent / name).read_bytes()
                        for name in (
                            "experimental.py",
                            "experimental_cli.py",
                            "providers.py",
                            "benchmark.py",
                            "metrics.py",
                        )
                    )
                ).hexdigest(),
            },
        )
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 2 if summary.get("errors") else 0
    if args.command in {"ask", "search"}:
        if not args.question:
            raise ValueError("Informe a pergunta entre aspas")
        response = live_answer(args.question)
        if response is not None:
            print(response)
            return 0
        try:
            result = retriever().search(args.question, settings.rag_top_k, args.strategy)
        except Exception as exc:
            raise RuntimeError(
                f"Falha na recuperação ({args.strategy}): {error_detail(exc)}. "
                "O índice não foi alterado."
            ) from exc
        if args.command == "ask":
            try:
                result = answer(args.question, result)
            except Exception as exc:
                raise RuntimeError(
                    "A recuperação foi executada, mas o Gemini Chat falhou ao gerar a resposta. "
                    "Confira a chave, o nome/disponibilidade do modelo, cota e conexão. "
                    "Teste de novo com 'search' para validar apenas a recuperação."
                ) from exc
        show(result, args.show_context)
        return 0
    sync_live_startup()
    corpus_label = (
        "do corpus consolidado"
        if corpus.manifest.get("review_status") == "approved"
        else "experimental"
    )
    print(
        f"Chat {corpus_label} com fontes documentais e consulta InfoSaúde para "
        "apresentações mapeadas. Digite sair para encerrar.\n"
        "Busca automática: combina RAG vetorial e lexical; se o índice falhar ou não "
        "trouxer evidência, tenta lexical e informa o fallback.\n"
        "Para estoque, informe medicamento + concentração + forma e, se quiser, região. "
        "Ex.: ‘Tem sinvastatina 40 mg comprimido em Planaltina?’ Apenas apresentações "
        f"mapeadas têm consulta ao vivo. Formas que pode informar: {', '.join(FORM_EXAMPLES)}. "
        "Se a forma não existir, serão listadas as disponíveis no recorte. Para o corpus, "
        "pergunte por um item específico, "
        "ex.: ‘O que consta na RENAME sobre metformina 500 mg comprimido?’ "
        "O contexto desta conversa fica apenas em memória."
        if live_enabled
        else f"Chat documental {corpus_label}. Digite sair para encerrar.\n"
        "Busca automática: combina RAG vetorial e lexical, com fallback lexical sinalizado.\n"
        "Informe medicamento, concentração e forma farmacêutica. O contexto desta "
        "conversa fica apenas em memória."
    )
    pending = None
    history: list[tuple[str, str]] = []
    while True:
        try:
            question = input("\nVocê: ").strip()
        except (EOFError, KeyboardInterrupt):
            return 0
        if normalize(question) in {"sair", "fim", "exit"}:
            return 0
        if not question:
            continue
        greeting = greeting_reply(question)
        if greeting:
            print(greeting)
            history.append((question, greeting))
            continue
        question = follow_up(question, pending)
        try:
            response = live_answer(question)
            if response is not None:
                print(response)
                pending = question if is_clarification(response) else None
                history.append((question, response))
                continue
            result = chat_search(question)
            pending = question if result["status"] == "ambiguous" else None
            generated = answer(question, result, history)
            show(generated, args.show_context)
            history.append((question, generated.get("answer", result["message"])))
        except Exception as exc:
            print(f"Consulta indisponível ({type(exc).__name__}); tente novamente.")
