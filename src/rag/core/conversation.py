"""Pequeno contexto em memória e respostas sociais para os chats de terminal."""

from __future__ import annotations

import re

from rag.legacy.retrieval import FORM_EXAMPLES, normalize

GREETINGS = {"oi", "ola", "bom dia", "boa tarde", "boa noite", "e ai", "opa"}


def greeting_reply(message: str) -> str | None:
    normalized = re.sub(r"^[\s!?. ,]+|[\s!?. ,]+$", "", normalize(message))
    if normalized not in GREETINGS:
        return None
    forms = ", ".join(FORM_EXAMPLES)
    return (
        "Olá! Posso ajudar a consultar informações do corpus e, quando houver código "
        "validado, o estoque do InfoSaúde. Para uma busca mais precisa, informe o "
        "medicamento, a concentração e a forma farmacêutica — por exemplo: "
        "‘Tem sinvastatina 40 mg comprimido em Planaltina?’ Formas que você pode informar: "
        f"{forms}. Vou verificar se a forma existe no recorte; se não existir, "
        "informarei as formas disponíveis."
    )


def is_clarification(reply: str | None) -> bool:
    if not reply:
        return False
    text = normalize(reply)
    return any(
        phrase in text
        for phrase in (
            "informe a forma farmaceutica",
            "informe a concentracao",
            "informe um principio ativo",
            "mais de uma apresentacao possivel",
            "apresentacao identificada",
        )
    )


def is_clarification_input(message: str) -> bool:
    text = normalize(message)
    form_choices = {normalize(form) for form in FORM_EXAMPLES}
    form_choices.update(
        {"solucao", "suspensao", "xarope", "injetavel", "solucao oral", "solucao injetavel"}
    )
    if text in form_choices:
        return True
    return bool(
        re.fullmatch(
            r"[\d.,\s/%]+(?:mg|mcg|g|ui|ml)"
            r"(?:\s*/\s*(?:\d+(?:[.,]\d+)?\s*)?(?:ml|g|l))?(?:\s+\w+){0,4}|"
            r"(?:comprimido|capsula|solucao|suspensao|creme|pomada|gel|gotas|"
            r"liquido|topico|adesivo|dispositivo|espuma|inalador|injecao|locao|"
            r"po|spray|supositorio)(?:\s+\w+){0,3}",
            text,
        )
    )


def format_history(history: list[tuple[str, str]]) -> str:
    recent = history[-6:]
    return "\n".join(f"Usuário: {user}\nAssistente: {reply}" for user, reply in recent)
