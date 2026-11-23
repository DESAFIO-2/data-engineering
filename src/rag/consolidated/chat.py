"""Orquestração conversacional para o release consolidado aprovado."""

from __future__ import annotations

import re
from typing import Any

from ingestion.infosaude_live import UBS_URL, sync_snapshot
from rag.core.config import ROOT, Settings
from rag.core.conversation import greeting_reply
from rag.core.providers import google_chat, google_embeddings, is_transient_provider_error
from rag.legacy.live import PRODUCTS, _location_reply, load_snapshot

from .answer import synthesize
from .catalog import (
    candidates,
    options_reply,
    presentation_query,
    stock_candidates,
)
from .guardrails import (
    CLINICAL_BLOCKED_TERMS,
    matches_clinical_guardrail,
    matches_prompt_injection,
)
from .index import open_index
from .live import lookup_stock
from .matching import name_suggestion, normalize
from .release import ConsolidatedRelease
from .search import search
from .state import (
    REGIONS as REGIONS,
)
from .state import (
    SOURCE_NAMES as SOURCE_NAMES,
)
from .state import (
    ConversationState as ConversationState,
)
from .state import (
    region_in as region_in,
)
from .state import (
    stock_intent as stock_intent,
)

__all__ = [
    "BLOCKED",
    "REGIONS",
    "SOURCE_NAMES",
    "ConversationState",
    "_documental",
    "ask",
    "chat",
    "region_in",
    "stock_intent",
    "sync_live",
    "validated_products",
]

BLOCKED = CLINICAL_BLOCKED_TERMS


def validated_products(release: ConsolidatedRelease) -> dict[str, tuple[str, str]]:
    """Load audited external links, tied to this exact approved release fingerprint."""
    import json

    by_fingerprint = ROOT / "data/mappings/ubs" / f"{release.fingerprint}.json"
    legacy = ROOT / "data/mappings/ubs_consolidated.json"
    if by_fingerprint.is_file():
        payload = json.loads(by_fingerprint.read_text(encoding="utf-8"))
        if payload.get("release_fingerprint") != release.fingerprint:
            raise ValueError("Vínculos UBS pertencem a outro release; valide novamente")
    elif legacy.is_file():
        payload = json.loads(legacy.read_text(encoding="utf-8"))
        if payload.get("release_fingerprint") != release.fingerprint:
            return {}
    else:
        return {}
    catalog = {m["medicine_id"]: m for m in release.catalog}
    result = {}
    for link in payload["links"]:
        medicine = catalog.get(link["medicine_id"])
        if link.get("status") != "validated":
            continue
        if not medicine or not link.get("validated_at") or not link.get("source_url"):
            raise ValueError("Vínculo UBS sem proveniência")
        fields = ("active_ingredient", "strength", "form", "release_characteristic")
        if any(link.get(f) != medicine.get(f) for f in fields):
            raise ValueError("Vínculo UBS diverge da apresentação aprovada")
        result[link["medicine_id"]] = (str(link["product_code"]), link["product_description"])
    return result


def sync_live(release: ConsolidatedRelease) -> dict[str, Any]:
    codes = tuple(
        sorted({code for code, _ in (*PRODUCTS.values(), *validated_products(release).values())})
    )
    print(f"Sincronizando InfoSaúde; códigos UBS solicitados: {', '.join(codes)}.")
    snapshot = sync_snapshot(ROOT / "data/gold/infosaude_live_snapshot.json", codes)
    coverage = {str(row.get("i_cod_produto")) for row in snapshot["ubs_stock"]}
    print(
        f"InfoSaúde sincronizado: referência inicial UBS {len(coverage)}/{len(codes)} códigos. "
        "Outros produtos são consultados sob demanda, por código e descrição."
    )
    if not validated_products(release):
        print("Aviso: nenhuma apresentação v5 tem vínculo UBS validado; estoque v5 indisponível.")
    return snapshot


def _documental(result: dict[str, Any]) -> str:
    lines = [str(result["message"])]
    for evidence in result["evidence"]:
        lines.append(f"- {evidence['text']}")
    return "\n".join(lines)


def ask(
    question: str,
    release: ConsolidatedRelease,
    chunks: list[dict[str, Any]],
    manifest: dict[str, Any],
    settings: Settings,
    cache: dict[str, Any],
    *,
    documental: bool = False,
    strategy: str = "hybrid",
    generate: bool = True,
    history: list[tuple[str, str]] | None = None,
    show_context: bool = False,
    selected_option: dict[str, Any] | None = None,
) -> str:
    from rag.cli import _show

    query = normalize(question)
    if "cep" in query or re.search(r"\b\d{5}-?\d{3}\b", query):
        reply = (
            "A identificação da UBS de referência por CEP ainda não está integrada. "
            "Por enquanto, informe somente a região onde quer procurar o medicamento."
        )
        print(reply)
        return reply
    if matches_prompt_injection(question):
        reply = (
            "Não posso ignorar instruções de segurança, assumir papel clínico "
            "ou afirmar dados fora das fontes oficiais consultadas."
        )
        print(reply)
        return reply
    if matches_clinical_guardrail(question, release):
        reply = (
            "Não posso orientar dose, indicação individual, elegibilidade ou troca de "
            "medicamento, nem afirmar equivalência terapêutica. Consulte um profissional de saúde."
        )
        print(reply)
        return reply
    if "farmacia popular" in query and any(x in query for x in ("estoque", "saldo", "ubs")):
        # Two independently sourced answers; the model never receives live stock as list evidence.
        stock_question = re.sub(r"farmacia popular", "", query)
        print("Estoque UBS:")
        stock_reply = ask(
            stock_question,
            release,
            chunks,
            manifest,
            settings,
            cache,
            documental=documental,
            strategy=strategy,
            generate=False,
        )
        document_question = re.sub(r"\b(estoque|saldo|ubs|hoje|disponibilidade)\b", "", query)
        print("Presença na Farmácia Popular:")
        document_reply = ask(
            document_question,
            release,
            chunks,
            manifest,
            settings,
            cache,
            documental=True,
            strategy=strategy,
            generate=generate,
            history=history,
        )
        return f"Estoque UBS:\n{stock_reply}\nPresença na Farmácia Popular:\n{document_reply}"
    stock = stock_intent(question)
    if stock and selected_option is not None:
        if documental:
            reply = (
                "Estoque não consultado: modo documental ativo. "
                "Presença em lista não comprova saldo."
            )
        elif not region_in(question):
            reply = "Em qual região você quer procurar nas farmácias/UBS?"
        else:
            reply = lookup_stock(
                selected_option, release, region_in(question) or "", validated_products(release)
            )
        print(reply)
        return reply
    if not documental and any(x in query for x in ("onde fica", "endereco", "localizacao", "mapa")):
        snapshot = load_snapshot(ROOT / "data/gold/infosaude_live_snapshot.json")
        reply = (
            _location_reply(question, snapshot) if snapshot else "Cadastro InfoSaúde indisponível."
        )
        print(reply)
        return reply
    lookup = question
    if stock:
        lookup = re.sub(r"\b(estoque|saldo|disponibilidade|hoje|ubs)\b", "", query)
    # Resolve and enforce safety before any provider call.
    options = candidates(lookup, release)
    if stock:
        # Unknown source fields never become stock identities. Known fields may
        # already identify a unique presentation without asking the user to repeat it.
        options = stock_candidates(options)
        if len(options) > 1:
            reply = options_reply(options, release, stock=True)
            print(reply)
            return reply
        if len(options) == 1:
            if documental:
                reply = (
                    "Estoque não consultado: modo documental ativo. "
                    "Presença em lista não comprova saldo."
                )
            elif not region_in(question):
                reply = (
                    f"Encontrei {presentation_query(options[0])}. "
                    "Em qual região você quer procurar nas farmácias/UBS?"
                )
            else:
                reply = lookup_stock(
                    options[0], release, region_in(question) or "", validated_products(release)
                )
            print(reply)
            return reply
    # Run the cheap deterministic/lexical pass first (~36-105 ms) to catch out-of-scope,
    # ambiguous, or guardrail-blocked queries without triggering embeddings or LLM calls.
    result = search(lookup, release, chunks, strategy="lexical", top_k=settings.rag_top_k)
    if options and (
        result["status"] != "matched" or not re.search(r"\d+\s*(mg|mcg|g|ui|ml|%)(?!\w)", query)
    ):
        reply = options_reply(options, release, stock=stock)
        print(reply)
        return reply
    if stock:
        if result["status"] != "matched":
            print(result["message"])
            return str(result["message"])
        if documental:
            reply = (
                "Estoque UBS não consultado: modo documental ativo. "
                "Presença em lista não comprova saldo."
            )
        else:
            reply = "Não consegui identificar uma apresentação segura para consultar estoque. "
            reply += "Informe o nome como aparece na embalagem; posso listar as opções disponíveis."
        print(reply)
        return reply
    if not documental and result["status"] == "matched" and strategy in {"hybrid", "vector"}:
        if not settings.has_google_api_key:
            if not cache.get("no_key_warned"):
                print(
                    "Aviso: APP_GOOGLE_API_KEY ausente; "
                    "busca lexical e resposta documental disponíveis."
                )
                cache["no_key_warned"] = True
        elif not cache.get("vector_disabled"):
            try:
                if "store" not in cache:
                    embeddings = google_embeddings(
                        settings.rag_embedding_model, settings.google_api_keys
                    )
                    cache["store"] = open_index(
                        release,
                        chunks,
                        manifest,
                        ROOT / settings.rag_vector_dir,
                        settings.rag_embedding_model,
                        embeddings,
                    )
                result = search(
                    question, release, chunks, cache["store"], strategy, settings.rag_top_k
                )
            except Exception as exc:
                reason = (
                    "índice ausente"
                    if isinstance(exc, FileNotFoundError)
                    else (
                        "índice/configuração incompatível"
                        if isinstance(exc, ValueError)
                        else "serviço vetorial indisponível"
                    )
                )
                print(f"Aviso: {reason} ({type(exc).__name__}); busca lexical utilizada.")
                cache["vector_disabled"] = True
    reply = _documental(result)
    if (
        generate
        and not documental
        and result["status"] == "matched"
        and not settings.has_google_api_key
        and not cache.get("no_key_warned")
    ):
        print("Aviso: APP_GOOGLE_API_KEY ausente; resposta documental utilizada.")
        cache["no_key_warned"] = True
    if (
        generate
        and not documental
        and result["status"] == "matched"
        and settings.has_google_api_key
    ):
        if not cache.get("generation_disabled"):
            try:
                if "llm" not in cache:
                    cache["llm"] = google_chat(settings.rag_chat_model, settings.google_api_keys)
                model_history = [
                    (
                        user,
                        "Consulta UBS respondida separadamente; "
                        "saldos não são evidência documental.",
                    )
                    if UBS_URL in reply
                    or "Farmácias especializadas (CEAF)" in reply
                    or reply.startswith("Estoque UBS:\n")
                    else (user, reply)
                    for user, reply in (history or [])
                ]
                generated = synthesize(question, result, cache["llm"], model_history)
                if generated.strip() == str(result["message"]).strip():
                    reply = generated
                else:
                    print("Aviso: síntese não verificada. Usando resposta documental.")
            except Exception as exc:
                print(
                    f"Aviso: geração indisponível ({type(exc).__name__}); "
                    "resposta documental utilizada."
                )
                if not is_transient_provider_error(exc):
                    cache["generation_disabled"] = True
    if show_context:
        for i, ev in enumerate(result["evidence"], 1):
            print(f"[{i}] {ev['evidence_id']}: {ev['text']}")
    _show(result, reply, show_limits=False)
    return reply


def chat(
    args: Any,
    settings: Settings,
    release: ConsolidatedRelease,
    chunks: list[dict[str, Any]],
    manifest: dict[str, Any],
) -> int:
    if not args.documental:
        try:
            sync_live(release)
        except Exception as exc:
            snapshot = load_snapshot(ROOT / "data/gold/infosaude_live_snapshot.json")
            print(
                f"Aviso: sincronização indisponível ({type(exc).__name__}); "
                + ("usando snapshot anterior." if snapshot else "sem snapshot local.")
            )
    print(
        f"SUS Cidadão — {release.manifest['release_version']}. Digite 'sair' para encerrar.\n"
        "Diga o nome do medicamento e o que souber; "
        "eu mostro as concentrações e formas encontradas. "
        "Para procurar nas farmácias/UBS, informe sua região. "
        "Consulto os painéis públicos UBS e CEAF a cada pedido de estoque. "
        "A data do painel pode ser anterior à consulta."
    )
    state = ConversationState()
    cache: dict[str, Any] = {}
    pending_spelling: str | None = None
    while True:
        try:
            question = input("\nVocê: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nAté logo.")
            return 0
        if normalize(question) in {"sair", "fim", "exit"}:
            print("Até logo.")
            return 0
        if not question:
            continue
        print("\nAgente: ", end="")
        if greeting := greeting_reply(question):
            greeting = (
                "Olá! Qual medicamento você procura? Pode dizer só o nome; "
                "eu mostro as apresentações e ajudo a procurar nas farmácias/UBS da região."
            )
            print(greeting)
            reply = greeting
        elif matches_clinical_guardrail(question, release):
            reply = ask(
                question, release, chunks, manifest, settings, cache, documental=args.documental
            )
        elif "cep" in normalize(question) or re.search(r"\b\d{5}-?\d{3}\b", question):
            reply = ask(
                question, release, chunks, manifest, settings, cache, documental=args.documental
            )
        else:
            if state.options and re.fullmatch(r"\d+[.)]?", normalize(question)):
                choice = int(normalize(question).rstrip(".)"))
                if not 1 <= choice <= len(state.options):
                    print(
                        f"Escolha um número entre 1 e {len(state.options)}, "
                        "ou diga os detalhes que souber."
                    )
                    continue
            if pending_spelling and normalize(question) in {"sim", "isso", "correto", "confirmo"}:
                question = pending_spelling
            pending_spelling = None
            if suggestion := name_suggestion(question, release.catalog):
                reply = (
                    f"Você quis dizer {suggestion[0]}? Responda 'sim' ou informe o nome correto."
                )
                print(reply)
                pending_spelling = suggestion[1]
                state.history.append((question, reply))
                state.history = state.history[-6:]
                continue
            resolved = state.resolve(question, release)
            state.options = candidates(resolved, release)
            if state.intent == "stock":
                state.options = stock_candidates(state.options)
            reply = ask(
                resolved,
                release,
                chunks,
                manifest,
                settings,
                cache,
                documental=args.documental,
                strategy=args.strategy,
                history=state.history,
                show_context=args.show_context,
                selected_option=state.selected_option,
            )
        state.history.append((question, reply))
        state.history = state.history[-6:]
