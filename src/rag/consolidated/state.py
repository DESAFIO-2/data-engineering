"""Estado conversacional, detecção de região administrativa e intenção de estoque."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from rag.core.conversation import is_clarification_input

from .catalog import catalog_item_name_matches, presentation_query
from .matching import normalize
from .release import ConsolidatedRelease

SOURCE_NAMES = {"F01": "RENAME", "F03": "REME DF", "F04": "Farmácia Popular"}
# Administrative regions are recognized independently of rows returned for a product.
REGIONS = (
    "Planaltina",
    "Ceilândia",
    "Taguatinga",
    "Samambaia",
    "Gama",
    "Guará",
    "Sobradinho",
    "Sobradinho II",
    "Varjão",
    "SIA",
    "SCIA",
    "Sudoeste Octogonal",
    "Brazlândia",
    "Paranoá",
    "São Sebastião",
    "Santa Maria",
    "Recanto das Emas",
    "Riacho Fundo II",
    "Riacho Fundo",
    "Núcleo Bandeirante",
    "Candangolândia",
    "Lago Sul",
    "Lago Norte",
    "Cruzeiro",
    "Sudoeste",
    "Águas Claras",
    "Vicente Pires",
    "Itapoã",
    "Estrutural",
    "Fercal",
    "Park Way",
    "Jardim Botânico",
    "Plano Piloto",
    "Arniqueira",
    "Sol Nascente",
    "Pôr do Sol",
    "Arapoanga",
    "Água Quente",
)


def region_in(question: str) -> str | None:
    query = normalize(question)
    known = next(
        (
            r
            for r in sorted(REGIONS, key=len, reverse=True)
            if re.search(r"\b" + re.escape(normalize(r)) + r"\b", query)
        ),
        None,
    )
    if known:
        return known
    requested = re.search(r"\bem\s+([^?!.]+)", question, re.I)
    return requested.group(1).strip() if requested else None


def stock_intent(question: str) -> bool:
    query = normalize(question)
    return "farmacia popular" not in query and (
        query.startswith("tem ")
        or any(
            x in query
            for x in (
                "estoque",
                "saldo",
                "onde encontro",
                "onde tem",
                "disponivel",
                "disponibilidade",
                "qual farmacia tem",
                "quais farmacias tem",
                "qual farmacia possui",
            )
        )
    )


@dataclass
class ConversationState:
    presentation: str = ""
    source: str | None = None
    region: str | None = None
    intent: str = "documental"
    history: list[tuple[str, str]] = field(default_factory=list)
    options: list[dict[str, Any]] = field(default_factory=list)
    selected_option: dict[str, Any] | None = None

    def resolve(self, question: str, release: ConsolidatedRelease) -> str:
        query = normalize(question)
        choice = re.fullmatch(r"(?:opcao\s*)?(\d+)[.)]?", query)
        if choice and self.options:
            index = int(choice.group(1)) - 1
            if 0 <= index < len(self.options):
                self.selected_option = self.options[index]
                self.presentation = presentation_query(self.selected_option)
                question = self.presentation
                query = normalize(question)
                chosen = True
            else:
                return "opção inválida"
        else:
            chosen = False
            self.selected_option = None
        new_medicine = any(catalog_item_name_matches(query, m) for m in release.catalog)
        followup = is_clarification_input(question) or query.startswith(("e ", "na ", "no "))
        stock_followup = bool(
            re.fullmatch(
                r"(?:tem\s+)?(?:estoque|saldo)(?:\s+ubs)?(?:\s+(?:em|no|na)\s+.+)?[?!.]*",
                query,
            )
        )
        region = region_in(question)
        regional_followup = region is not None and query.strip(" ?!.,") in {
            normalize(region),
            "em " + normalize(region),
            "e em " + normalize(region),
            "e na " + normalize(region),
            "na " + normalize(region),
        }
        anaphor = any(
            term in query
            for term in ("desse remedio", "esse remedio", "desse medicamento", "dele", "dela")
        )
        if new_medicine and not chosen:
            self.presentation = question
            self.source = None
            # A location and stock request remain useful when the user changes
            # the medicine; the presentation and source do not.
            self.options = []
        elif chosen:
            pass
        elif self.presentation and (
            followup
            or stock_followup
            or regional_followup
            or anaphor
            or any(x in query for x in ("liberacao", "prolongada", "convencional", "imediata"))
        ):
            # Keep identity, replace source/region/intent independently.
            if is_clarification_input(question):
                if re.search(r"\d+\s*(?:mg|mcg|g|ui|ml)\b", query):
                    self.presentation = re.sub(
                        r"\d+(?:[.,]\d+)?\s*(?:mg|mcg|g|ui|ml)"
                        r"(?:\s*/\s*(?:\d+(?:[.,]\d+)?\s*)?(?:ml|g|l))?\b",
                        "",
                        self.presentation,
                        flags=re.I,
                    )
                self.presentation += " " + question
            elif any(x in query for x in ("prolongada", "convencional", "imediata")):
                self.presentation = (
                    re.sub(
                        r"(?:acao |liberacao )?(?:prolongada|convencional|imediata)",
                        "",
                        normalize(self.presentation),
                    )
                    + " "
                    + question
                )
        else:
            self.presentation = ""
            self.source = None
            self.region = None
            self.intent = "documental"
            self.options = []
        for source, label in SOURCE_NAMES.items():
            if normalize(label) in query or (source == "F03" and "reme" in query):
                self.source = source
                self.intent = "documental"
        if region := region_in(question):
            self.region = region
            if regional_followup and not any(
                term in query for term in ("rename", "reme", "farmacia popular")
            ):
                self.intent = "stock"
        if stock_intent(question):
            self.intent = "stock"
        identity = self.presentation or question
        # Original question can contain an old list name. Source is a separate slot.
        for label in (
            "farmácia popular",
            "farmacia popular",
            "rename",
            "reme df",
            "reme-df",
            "reme",
        ):
            identity = re.sub(re.escape(label), "", identity, flags=re.I)
        previous_region = region_in(self.presentation)
        if previous_region:
            identity = re.sub(re.escape(previous_region), "", identity, flags=re.I)
        identity = re.sub(
            r"\b(estoque|saldo|ubs|hoje|disponibilidade|disponivel)\b", "", normalize(identity)
        )
        identity = re.sub(r"^tem\s+", "", identity)
        if "farmacia popular" in query and any(x in query for x in ("estoque", "saldo", "ubs")):
            return f"{identity} estoque UBS e Farmácia Popular {self.region or ''}"
        if self.intent == "stock":
            return f"{identity} estoque em {self.region or ''}"
        return f"{identity} {SOURCE_NAMES.get(self.source or '', '')}"
