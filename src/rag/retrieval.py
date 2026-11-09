"""Busca exata da apresentação e recuperação vetorial limitada à mesma apresentação."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any

from .release import Release


def normalize(value: str) -> str:
    text = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    text = re.sub(r"(\d)\s*(mg|mcg|ui)\b", r"\1 \2", text.lower())
    return " ".join(text.split())


def _has_term(question: str, term: str) -> bool:
    return re.search(rf"(?<!\w){re.escape(normalize(term))}(?!\w)", question) is not None


FORM_EXAMPLES = (
    "comprimido", "cápsula", "líquido", "tópico", "adesivo", "creme", "dispositivo",
    "espuma", "gel", "gotas", "inalador", "injeção", "loção", "pomada", "pó",
    "spray", "supositório",
)
LIQUID_FORMS = ("liquido", "solucao", "suspensao", "xarope", "gotas")
TOPICAL_FORMS = ("topico", "creme", "espuma", "gel", "locao", "pomada")
FORM_TERMS = tuple(
    dict.fromkeys(
        (*FORM_EXAMPLES, "solução", "suspensão", "xarope", "injetável", "óvulo")
    )
)


def _form_matches(stored_form: str, requested_form: str) -> bool:
    stored = normalize(stored_form)
    requested = normalize(requested_form)
    if requested == "liquido":
        return any(_has_term(stored, term) for term in LIQUID_FORMS)
    if requested == "topico":
        return any(_has_term(stored, term) for term in TOPICAL_FORMS)
    aliases = {
        "capsula": ("capsula",),
        "comprimido": ("comprimido",),
        "injecao": ("injecao", "injetavel", "ampola"),
        "adesivo": ("adesivo", "transdermico"),
        "dispositivo": ("dispositivo", "inalador"),
    }
    terms = aliases.get(requested, (requested,))
    return any(_has_term(stored, term) for term in terms)


def _available_forms(medicines: list[dict[str, Any]]) -> str:
    return ", ".join(dict.fromkeys(medicine["form"] for medicine in medicines))


@dataclass(frozen=True)
class Match:
    status: str
    message: str
    medicine: dict[str, Any] | None = None


def match_medicine(question: str, release: Release) -> Match:
    query = normalize(question)
    candidates = [
        medicine
        for medicine in release.medicines
        if any(
            _has_term(query, name)
            for name in (medicine["active_ingredient"], *medicine.get("aliases", []))
        )
    ]
    if not candidates:
        return Match("not_in_scope", "Não localizado no recorte consultado: seis apresentações.")
    if len({m["active_ingredient"] for m in candidates}) > 1:
        return Match("ambiguous", "Informe um princípio ativo por pergunta.")
    specified_strengths = [m for m in candidates if _has_term(query, m["strength"])]
    if not specified_strengths:
        if re.search(r"\b\d+(?:[.,]\d+)?\s*(?:mg|mcg|ui)\b", query):
            return Match("not_in_scope", "Apresentação não localizada no recorte consultado.")
        choices = ", ".join(sorted({m["strength"] for m in candidates}))
        return Match("ambiguous", f"Informe a concentração. Neste recorte: {choices}.")
    requested_forms = [form for form in FORM_TERMS if _has_term(query, form)]
    available = _available_forms(specified_strengths)
    if not requested_forms:
        return Match(
            "ambiguous",
            f"Informe a forma farmacêutica. Formas disponíveis neste recorte: {available}.",
        )
    specified_forms = [
        medicine
        for medicine in specified_strengths
        if any(_form_matches(medicine["form"], form) for form in requested_forms)
    ]
    if not specified_forms:
        requested = ", ".join(requested_forms)
        return Match(
            "not_in_scope",
            f"A forma {requested} não consta para essa concentração. "
            f"Formas disponíveis neste recorte: {available}.",
        )
    if len(specified_forms) != 1:
        return Match("ambiguous", "Há mais de uma apresentação possível; informe os detalhes.")
    return Match("matched", "Apresentação identificada no recorte.", specified_forms[0])


def retrieve(question: str, release: Release, store: Any, top_k: int = 5) -> dict[str, Any]:
    query = normalize(question)
    if any(_has_term(query, word) for word in ("estoque", "disponibilidade", "tem hoje")):
        return {
            "status": "unsupported",
            "message": "Estoque não consultado neste release.",
            "evidence": [],
        }
    if any(_has_term(query, word) for word in ("documentos", "receita", "lme", "exame", "jejum")):
        return {
            "status": "unsupported",
            "message": "Este release não valida documentos ou exames.",
            "evidence": [],
        }
    if any(
        _has_term(query, word)
        for word in ("posso tomar", "quanto tomar", "substituir", "trocar remedio", "diagnostico")
    ):
        return {
            "status": "blocked",
            "message": (
                "Não posso orientar diagnóstico, dose ou troca de medicamento. "
                "Consulte um profissional de saúde."
            ),
            "evidence": [],
        }
    match = match_medicine(question, release)
    if match.status != "matched":
        return {"status": match.status, "message": match.message, "evidence": []}
    assert match.medicine is not None
    medicine = match.medicine
    exact_ids = {value["evidence_id"] for value in medicine["lists"].values()}
    by_id = {e["evidence_id"]: e for e in release.evidence}
    exact = [by_id[eid] for eid in sorted(exact_ids)]
    docs = store.similarity_search(
        question, k=max(1, top_k), filter={"medicine_id": medicine["medicine_id"]}
    )
    seen = set(exact_ids)
    semantic = []
    for doc in docs:
        eid = doc.metadata.get("evidence_id")
        if (
            eid in by_id
            and eid not in seen
            and by_id[eid]["medicine_id"] == medicine["medicine_id"]
        ):
            semantic.append(by_id[eid])
            seen.add(eid)
    return {
        "status": "matched",
        "message": match.message,
        "medicine": medicine,
        "evidence": exact + semantic,
        "semantic_ids": [doc.metadata.get("evidence_id") for doc in docs],
    }


def retrieve_lexical(question: str, release: Release, top_k: int = 5) -> dict[str, Any]:
    """Deterministic catalog/evidence fallback that never calls embeddings."""
    query = normalize(question)
    if any(_has_term(query, word) for word in ("estoque", "disponibilidade", "tem hoje")):
        return {
            "status": "unsupported",
            "message": "Estoque não consultado neste release.",
            "evidence": [],
        }
    if any(_has_term(query, word) for word in ("documentos", "receita", "lme", "exame", "jejum")):
        return {
            "status": "unsupported",
            "message": "Este release não valida documentos ou exames.",
            "evidence": [],
        }
    if any(
        _has_term(query, word)
        for word in ("posso tomar", "quanto tomar", "substituir", "trocar remedio", "diagnostico")
    ):
        return {
            "status": "blocked",
            "message": (
                "Não posso orientar diagnóstico, dose ou troca de medicamento. "
                "Consulte um profissional de saúde."
            ),
            "evidence": [],
        }
    match = match_medicine(question, release)
    if match.status != "matched":
        return {"status": match.status, "message": match.message, "evidence": []}
    assert match.medicine is not None
    medicine = match.medicine
    ids = {value["evidence_id"] for value in medicine["lists"].values()}
    by_id = {evidence["evidence_id"]: evidence for evidence in release.evidence}
    evidence = [by_id[eid] for eid in sorted(ids) if eid in by_id][:top_k]
    labels = ", ".join(sorted(medicine["lists"]))
    return {
        "status": "matched",
        "message": (
            f"{medicine['active_ingredient']} {medicine['strength']} "
            f"({medicine['form']}) consta nas fontes do release: {labels}."
        ),
        "medicine": medicine,
        "evidence": evidence,
        "semantic_ids": [],
        "retrieval_strategy": "lexical_exact_fallback",
    }
