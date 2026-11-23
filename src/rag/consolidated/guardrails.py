"""Guardrails lexicais de escopo clínico, documental e proteção contra prompt injection."""

from __future__ import annotations

import re

from .matching import normalize
from .release import ConsolidatedRelease

CLINICAL_BLOCKED_TERMS: tuple[str, ...] = (
    "posso tomar",
    "quanto tomar",
    "como tomar",
    "como devo tomar",
    "como usar",
    "como devo usar",
    "qual dose",
    "qual a dose",
    "qual e a dose",
    "que dose",
    "minha dose",
    "devo tomar",
    "dosagem",
    "posologia",
    "superdosagem",
    "minha dose diaria",
    "sua dose diaria",
    "dose diaria maxima",
    "dose diaria minima",
    "dose diaria recomendada",
    "dose diaria indicada",
    "dose diaria segura",
    "dose diaria ideal",
    "dose maxima",
    "dose minima recomendada",
    "dose minima eficaz",
    "dose minima efetiva",
    "dose recomendada",
    "substituir",
    "substituicao terapeutica",
    "posso trocar",
    "trocar pela",
    "trocar por",
    "trocar esse medicamento",
    "trocar meu medicamento",
    "alterar a dose",
    "aumentar a dose",
    "diminuir a dose",
    "dobrar a dose",
    "reduzir a dose",
    "indicar dose",
    "recomendar dose",
    "dose infantil",
    "dose pediatrica",
    "dose para crianca",
    "quantos comprimidos",
    "quantas gotas",
    "quantas vezes ao dia",
    "de quantas em quantas horas",
    "partir o comprimido",
    "cortar o comprimido",
    "suspender o medicamento",
    "parar de tomar",
    "esqueci de tomar",
    "overdose",
    "prescreva",
    "prescrever",
    "receitar",
    "me receite",
    "equivalencia",
    "equivalencias",
    "equivalente terapeutico",
    "equivalentes terapeuticos",
    "medicamento equivalente",
    "medicamentos equivalentes",
    "tem equivalente",
    "qual o equivalente",
    "qual e o equivalente",
    "e equivalente",
    "sao equivalentes",
    "mesmo efeito",
    "mesma eficacia",
    "diagnostico",
    "indicado para mim",
    "indicada para mim",
    "serve para o meu caso",
    "tenho direito",
    "sou elegivel",
    "posso usar",
    "posso receber",
    "posso misturar",
    "tomar com alcool",
    "misturar com alcool",
    "beber alcool",
    "ingerir alcool",
    "efeito colateral",
    "efeitos colaterais",
    "reacao adversa",
    "reacoes adversas",
    "contraindicacao",
    "contraindicacoes",
    "gravidez",
    "gravida",
    "gravidas",
    "gestacao",
    "gestante",
    "gestantes",
    "amamentacao",
    "amamentando",
    "lactante",
    "interacao medicamentosa",
    "interacoes medicamentosas",
    "interage com",
    "interacao com",
)

CLINICAL_BLOCKED_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(?:trocar|substituir)\b.{1,40}\bpor\b"),
    re.compile(r"\b(?:qual|que|recomende|indique|calcule|ajuste)\b.{0,25}\bdose\b"),
    re.compile(
        r"\b(?:tomar|usar|prescrever|indicar|recomendar|aumentar|diminuir|"
        r"dobrar|reduzir|alterar|exceder)\b.{0,25}\bdose (?:diaria|minima)\b"
    ),
    re.compile(r"(?<!\()\bdose diaria\s+(?:de|para)\b"),
    re.compile(r"\bdose minima\b(?!\s+(?:mortal|necrosante)\b)"),
    re.compile(r"\b(?:devo|posso|preciso)\s+(?:tomar|usar|aplicar|suspender|interromper)\b"),
)

PROMPT_INJECTION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"\b(?:ignore|desconsidere|esqueca|anule)\b.{0,30}"
        r"\b(?:instrucoes|regras|restricoes|limites|diretrizes|sistema)\b"
    ),
    re.compile(
        r"\b(?:system prompt|prompt do sistema|instrucoes internas|"
        r"instrucoes do sistema|regras internas|jailbreak|dan mode|modo desenvolvedor)\b"
    ),
    re.compile(
        r"\b(?:atue|finja|aja|comporte-se|responda)\s+como\s+(?:um|uma)?\s*"
        r"(?:medico|medica|farmaceutico|farmaceutica|prescritor|especialista clinico)\b"
    ),
    re.compile(
        r"\b(?:diga|responda|afirme|garanta|invente)\s+que\s+"
        r"(?:tem|ha|existe|esta)\s+(?:disponivel\s+)?(?:em\s+)?estoque\b"
    ),
    re.compile(r"(?:^|\n)\s*(?:system|developer|assistant)\s*:", re.IGNORECASE),
)

DOCUMENTAL_ONLY_BLOCKED_TERMS: tuple[str, ...] = (
    "estoque",
    "disponibilidade",
    "hoje",
    "documentos",
    "receita",
    "lme",
    "exame",
    "jejum",
)


def matches_clinical_guardrail(question: str, release: ConsolidatedRelease | None = None) -> bool:
    """Detect out-of-scope clinical, dosing, pregnancy, or eligibility queries via lexical rules."""
    query = normalize(question)
    if release and "(dose diaria)" in query:
        listing = re.fullmatch(r"na (rename|reme-df), ha registro de (.+)\?", query)
        if listing:
            source_id = {"rename": "F01", "reme-df": "F03"}[listing[1]]
            for item in release.catalog:
                if source_id not in item["source_ids"]:
                    continue
                forms = [item["form"], *(item.get("literal_forms") or ())]
                if item.get("release_characteristic") and item["form"] != "-":
                    forms.extend(
                        [
                            f"{item['form']} de {item['release_characteristic']}",
                            f"{item['form']} {item['release_characteristic']}",
                        ]
                    )
                if any(
                    listing[2] == normalize(f"{name} {item['strength']} {form}")
                    for name in (item["active_ingredient"], *(item.get("aliases") or ()))
                    for form in forms
                ):
                    return False
    return any(
        re.search(r"\b" + re.escape(term) + r"\b", query) for term in CLINICAL_BLOCKED_TERMS
    ) or any(pattern.search(query) for pattern in CLINICAL_BLOCKED_PATTERNS)


def matches_prompt_injection(question: str) -> bool:
    """Detect prompt-override, role-impersonation, or fabricated-stock injection attempts."""
    query = normalize(question)
    return any(
        pattern.search(question if ":\\s*" in pattern.pattern else query)
        for pattern in PROMPT_INJECTION_PATTERNS
    )


def matches_documental_scope_block(
    question: str, release: ConsolidatedRelease | None = None
) -> bool:
    """Detect queries outside the frozen list-presence scope (clinical, stock, or documents)."""
    query = normalize(question)
    if matches_clinical_guardrail(query, release):
        return True
    return any(
        re.search(r"\b" + re.escape(term) + r"\b", query) for term in DOCUMENTAL_ONLY_BLOCKED_TERMS
    )
