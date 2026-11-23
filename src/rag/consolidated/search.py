"""Motor de busca e ranqueamento (exact, lexical BM25, vector e hybrid RRF)."""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any

from .guardrails import matches_documental_scope_block, matches_prompt_injection
from .index import _vector_ranks
from .matching import (
    _form_matches,
    _matching_supplies,
    _presentation_form_matches,
    ingredient_key,
    is_form_absent,
    item_form_display,
    item_form_label,
    item_name_matches,
    name_suggestion,
    normalize,
    strength_core,
    strength_matches,
)
from .release import ConsolidatedRelease


def bm25_rank(question: str, chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Rank only already compatible candidates; never choose an identity by score."""
    query = set(re.findall(r"\w+", normalize(question)))
    documents = [Counter(re.findall(r"\w+", normalize(c["text"]))) for c in chunks]
    average = sum(sum(doc.values()) for doc in documents) / len(documents)
    scores = []
    for chunk, doc in zip(chunks, documents, strict=True):
        length = sum(doc.values())
        score = 0.0
        for term in query:
            frequency = doc[term]
            if not frequency:
                continue
            found = sum(term in other for other in documents)
            idf = math.log(1 + (len(documents) - found + 0.5) / (found + 0.5))
            score += (
                idf * frequency * 2.5 / (frequency + 1.5 * (1 - 0.75 + 0.75 * length / average))
            )
        scores.append((score, chunk))
    return [chunk for _, chunk in sorted(scores, key=lambda x: (-x[0], x[1]["chunk_id"]))]


def search(
    question: str,
    release: ConsolidatedRelease,
    chunks: list[dict[str, Any]],
    store: Any = None,
    strategy: str = "lexical",
    top_k: int = 5,
) -> dict[str, Any]:
    if strategy not in {"exact", "lexical", "vector", "hybrid"} or not 1 <= top_k <= 20:
        raise ValueError("Estratégia ou top_k inválido")
    if strategy in {"vector", "hybrid"} and store is None:
        raise ValueError(
            f"Estratégia '{strategy}' exige índice vetorial carregado (store); "
            "execute 'index' ou use 'lexical'/'exact'."
        )
    query = normalize(question)
    if matches_documental_scope_block(query, release) or matches_prompt_injection(question):
        return {
            "status": "unsupported",
            "evidence": [],
            "message": (
                "Este release informa somente presença nas listas, sem estoque, "
                "elegibilidade ou orientação clínica."
            ),
        }
    source_filter = None
    if re.search(r"\b(?:reme|reme-df)\b", query) or re.search(r"\bf03\b", query):
        source_filter = "F03"
    elif "farmacia popular" in query or re.search(r"\bf04\b", query):
        source_filter = "F04"
    elif re.search(r"\brename\b", query) or re.search(r"\bf01\b", query):
        source_filter = "F01"
    if "insumo" in query:
        supplies = _matching_supplies(query, release, source_filter)
        if len(supplies) != 1:
            return {
                "status": "ambiguous" if supplies else "not_in_scope",
                "evidence": [],
                "message": "Informe o insumo e sua apresentação exata.",
            }
        item = supplies[0]
        ev = next(e for e in release.evidence if e["occurrence_id"] == item["occurrence_id"])
        return {
            "status": "matched",
            "evidence": [ev],
            "message": (
                f"{item['active_ingredient']} consta como insumo em "
                f"{item['source']['source_id']}. Presença em lista não confirma disponibilidade."
            ),
        }
    names = [
        m
        for m in release.catalog
        if item_name_matches(query, m) and (not source_filter or source_filter in m["source_ids"])
    ]
    if names:
        identities = {ingredient_key(m["active_ingredient"]) for m in names}
        longest_identity = max(identities, key=len)
        if any(identity not in longest_identity for identity in identities):
            return {
                "status": "ambiguous",
                "evidence": [],
                "message": "Informe um princípio ativo ou uma associação documentada por pergunta.",
            }
        longest_name = max(len(normalize(m["active_ingredient"])) for m in names)
        names = [m for m in names if len(normalize(m["active_ingredient"])) == longest_name]
    if names:
        strengths = [
            m
            for m in names
            if m["strength"] == "-"
            or any(
                strength_matches(query, m["strength"], candidate)
                for candidate in (m["active_ingredient"], *(m.get("aliases") or ()))
            )
        ]
        if not strengths:
            if not re.search(r"\d+(?:[.,]\d+)?\s*(?:(?:mg|mcg|g|ui|meq|ml|u|l)\b|%)", query):
                options = sorted(
                    names,
                    key=lambda m: (
                        normalize(m["strength"]),
                        normalize(item_form_label(m)),
                        normalize(m.get("release_characteristic") or ""),
                        m["medicine_id"],
                    ),
                )
                refs: dict[str, list[str]] = {m["medicine_id"]: [] for m in options}
                cited = []
                for ev in release.evidence:
                    source = ev["source"]
                    mid = ev["medicine_id"]
                    if mid in refs and (not source_filter or source["source_id"] == source_filter):
                        refs[mid].append(
                            f"{source['source_id']} ({source['version']}), "
                            f"página {source['page']} [{ev['evidence_id']}]"
                        )
                        cited.append(ev)
                return {
                    "status": "ambiguous",
                    "evidence": cited,
                    "candidate_presentations": options,
                    "message": "Apresentações documentadas: "
                    + "; ".join(
                        f"{m['strength']} — {item_form_display(m)}"
                        + (
                            f" — {m['release_characteristic']}"
                            if m.get("release_characteristic")
                            else ""
                        )
                        + f" ({'; '.join(refs[m['medicine_id']])})"
                        for m in options
                    )
                    + ". Qual concentração ou forma você procura?",
                }
            return {
                "status": "not_in_scope",
                "evidence": [],
                "message": (
                    "Concentração não localizada para este princípio ativo nas listas consultadas."
                ),
            }
        matches = [m for m in strengths if _presentation_form_matches(query, m)]
        missing_volume = not matches and any(
            m["form"] != "-"
            and m.get("package")
            and m["strength"] == "-"
            and _form_matches(query, m["form"])
            for m in strengths
        )
        known_form_mentioned = any(
            normalize(lbl) in query
            for m in release.catalog
            if not is_form_absent(m)
            for lbl in (
                item_form_label(m),
                *(m.get("literal_forms") or ()),
                *(m.get("form_alternatives") or ()),
            )
        )
        if not matches and (missing_volume or not known_form_mentioned):
            return {
                "status": "ambiguous",
                "evidence": [],
                "message": "Informe a forma farmacêutica. Formas disponíveis: "
                + ", ".join(sorted({item_form_display(m) for m in strengths}))
                + ".",
            }
        prolonged = "prolongada" in query
        delayed = "retardada" in query
        if prolonged and not any(
            "prolongada" in normalize(m.get("release_characteristic") or "") for m in matches
        ):
            return {
                "status": "not_in_scope",
                "evidence": [],
                "message": (
                    "Ação prolongada não documentada para esta apresentação na fonte solicitada."
                ),
            }
        if any(m.get("release_characteristic") for m in matches):
            explicit_regular = "convencional" in query or "imediata" in query
            if prolonged or delayed or explicit_regular:
                requested_characteristic = (
                    "prolongada" if prolonged else "retardada" if delayed else None
                )
                matches = [
                    m
                    for m in matches
                    if (
                        requested_characteristic in normalize(m.get("release_characteristic") or "")
                        if requested_characteristic
                        else not m.get("release_characteristic")
                    )
                ]
            elif len({m.get("release_characteristic") for m in matches}) > 1:
                return {
                    "status": "ambiguous",
                    "evidence": [],
                    "message": (
                        "Informe a característica de liberação: convencional ou ação prolongada. "
                        "Não são consideradas equivalentes."
                    ),
                }
        if matches:
            if (
                len({normalize(m["strength"]) for m in matches}) > 1
                and len({strength_core(m["strength"]) for m in matches}) == 1
            ):
                return {
                    "status": "ambiguous",
                    "evidence": [],
                    "message": "Há mais de um dispositivo documentado. Informe qual: "
                    + "; ".join(sorted({m["strength"] for m in matches}))
                    + ".",
                }
            longest_strength = max(len(normalize(m["strength"])) for m in matches)
            matches = [m for m in matches if len(normalize(m["strength"])) == longest_strength]
            longest_form = max(
                len(normalize(item_form_label(m))) if not is_form_absent(m) else 0 for m in matches
            )
            matches = [
                m
                for m in matches
                if (len(normalize(item_form_label(m))) if not is_form_absent(m) else 0)
                == longest_form
            ]
    else:
        matches = []
    if not matches:
        supplies = _matching_supplies(query, release, source_filter)
        if len(supplies) == 1:
            item = supplies[0]
            ev = next(e for e in release.evidence if e["occurrence_id"] == item["occurrence_id"])
            return {
                "status": "matched",
                "evidence": [ev],
                "message": (
                    f"{item['active_ingredient']} consta como insumo em "
                    f"{item['source']['source_id']}. "
                    "Presença em lista não confirma disponibilidade."
                ),
            }
    if not names and not matches:
        if suggestion := name_suggestion(question, release.catalog):
            return {
                "status": "ambiguous",
                "evidence": [],
                "message": f"Você quis dizer {suggestion[0]}? Confirme o nome antes da consulta.",
                "suggested_question": suggestion[1],
            }
    if len(matches) != 1 and (
        not matches
        or len(
            {
                (
                    ingredient_key(m["active_ingredient"]),
                    normalize(m["strength"]),
                    normalize(item_form_label(m)),
                    normalize(m.get("package") or ""),
                    normalize(m.get("release_characteristic") or ""),
                )
                for m in matches
            }
        )
        != 1
    ):
        return {
            "status": "ambiguous" if matches else "not_in_scope",
            "evidence": [],
            "message": (
                "Informe apresentação exata: princípio ativo, concentração e forma "
                "quando documentadas."
            ),
        }
    med = matches[0]
    match_ids = {m["medicine_id"] for m in matches}
    selected = [c for c in chunks if c["medicine_id"] in match_ids]
    if source_filter:
        selected = [c for c in selected if c["source"]["source_id"] == source_filter]
    if not selected:
        return {
            "status": "not_in_scope",
            "evidence": [],
            "message": "Esta apresentação não consta na fonte solicitada.",
        }
    lexical = bm25_rank(question, selected)
    if strategy in {"vector", "hybrid"}:
        if store is None:
            raise ValueError(
                f"Estratégia '{strategy}' exige índice vetorial carregado (store); "
                "execute 'index' ou use 'lexical'/'exact'."
            )
        allowed = {c["chunk_id"] for c in selected}
        vec_k = min(max(top_k * 3, 10), len(selected))
        ranks = _vector_ranks(question, store, match_ids, allowed, vec_k)
        if strategy == "vector":
            selected = sorted(selected, key=lambda c: ranks.get(c["chunk_id"], 10**6))
        else:
            lrank = {c["chunk_id"]: i for i, c in enumerate(lexical)}
            selected = sorted(
                selected,
                key=lambda c: (
                    1 / (60 + lrank[c["chunk_id"]])
                    + (1 / (60 + ranks[c["chunk_id"]]) if c["chunk_id"] in ranks else 0)
                ),
                reverse=True,
            )
    elif strategy == "exact":
        selected = sorted(
            selected,
            key=lambda c: (
                c["source"]["source_id"],
                c["source"]["page"],
                c["evidence_id"],
            ),
        )
    else:
        selected = lexical
    evidence_by_id = {e["evidence_id"]: e for e in release.evidence}
    sources = sorted({c["source"]["source_id"] for c in selected[:top_k]})
    return {
        "status": "matched",
        "medicine": med,
        "equivalent_medicine_ids": sorted(match_ids),
        "candidate_presentation_ids": sorted(match_ids),
        "candidate_chunk_count": len(selected),
        "ranked_chunk_ids": [c["chunk_id"] for c in selected[:top_k]],
        "evidence": [evidence_by_id[c["evidence_id"]] for c in selected[:top_k]],
        "message": (
            f"{med['active_ingredient']} {med['strength']} "
            f"({item_form_display(med)}"
            f"{'; ' + med['release_characteristic'] if med.get('release_characteristic') else ''}) "
            "consta nas fontes: "
            f"{', '.join(sources)}. Presença em lista não confirma estoque."
        ),
    }
