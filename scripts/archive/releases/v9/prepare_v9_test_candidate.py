"""Prepare an unopened, source-linked v9 test candidate for human review."""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "src"))

from rag.consolidated import ConsolidatedRelease, jsonl_bytes, normalize  # noqa: E402

RELEASE = ROOT / "data/releases/corpus-consolidado-v9-aprovado-2026-11-12"
DEV = ROOT / "evals/datasets/consolidated_v9_dev_exploratory.jsonl"
TARGET = ROOT / "evals/datasets/consolidated_v9_test_candidate_v2_unreviewed.jsonl"
REVIEW = ROOT / "docs/reports/v9/v9-independent-test-review-v2.md"
SOURCE_NAMES = {"F01": "RENAME", "F03": "REME-DF", "F04": "Farmácia Popular"}
NEGATIVES = (
    ("F01", "cloridrato de amitriptilina", "50 mg", "comprimido"),
    ("F03", "abacavir", "30 mg/mL", "solução oral"),
    ("F03", "carbamazepina", "200 mg/5 mL", "suspensão oral"),
    ("F04", "losartana potássica", "100mg", None),
)


def presentation_for_review(ref: dict) -> str:
    """Render a readable presentation without changing approved release fields."""
    ingredient = ref["active_ingredient"]
    if ingredient == "medicamentos homeopáticos":
        return "medicamentos homeopáticos conforme Farmacopeia Homeopática Brasileira vigente"
    if ingredient.startswith("imunoglobulina anti-rho"):
        return (
            "imunoglobulina anti-rho (anti-d) solução injetável de 250 mcg a 300 mcg "
            "em frasco-ampola ou seringa preenchida"
        )
    if ingredient == "solução de ringer com lactato":
        return "solução de ringer com lactato injetável em bolsa ou frasco 500 mL"
    if ingredient == "etinilestradiol + levonorgestrel":
        return "etinilestradiol 0,03mg + levonorgestrel 0,15mg"
    return f"{ingredient} {ref['strength']}" + (
        f" {ref['form']}" if ref["form"] != "-" else ""
    )


def _reference(ev: dict, exact_supported: bool) -> dict:
    return {
        "active_ingredient": ev["active_ingredient"],
        "evidence_id": ev["evidence_id"],
        "exact_presentation_supported": exact_supported,
        "form": ev["form"],
        "medicine_id": ev["medicine_id"],
        "page": ev["source"]["page"],
        "release_characteristic": ev["release_characteristic"],
        "source_id": ev["source"]["source_id"],
        "source_row_number": ev["source_row_number"],
        "source_version": ev["source"]["version"],
        "strength": ev["strength"],
    }


def prepare() -> list[dict]:
    release = ConsolidatedRelease.load(RELEASE)
    dev = [json.loads(line) for line in DEV.read_text(encoding="utf-8").splitlines() if line]
    # Exclude every family already exposed in the v8 benchmark, including its
    # historical test split; none of those cases is a fresh v9 holdout.
    dev_families = {normalize(case["family_id"]) for case in dev}
    evidence_by_med_source: dict[tuple[str, str], list[dict]] = {}
    for ev in release.evidence:
        evidence_by_med_source.setdefault(
            (ev["medicine_id"], ev["source"]["source_id"]), []
        ).append(ev)

    rng = random.Random(20261112)
    selected: list[tuple[str, dict]] = []
    used = set(dev_families)
    for source, count in (("F01", 10), ("F03", 10), ("F04", 4)):
        pool = [
            item
            for item in release.catalog
            if source in item["source_ids"]
            and item["strength"] != "-"
            and (source == "F04" or item["exact_presentation_supported"])
            and (item["medicine_id"], source) in evidence_by_med_source
            and normalize(item["active_ingredient"]) not in dev_families
        ]
        rng.shuffle(pool)
        picked = 0
        for item in pool:
            family = normalize(item["active_ingredient"])
            if family in used:
                continue
            selected.append((source, item))
            used.add(family)
            picked += 1
            if picked == count:
                break
        if picked != count:
            raise ValueError(f"Famílias independentes insuficientes em {source}: {picked}")

    cases = []
    for index, (source, item) in enumerate(selected, 1):
        form = f" {item['form']}" if item["form"] != "-" else ""
        question = (
            f"Na {SOURCE_NAMES[source]}, há registro de {item['active_ingredient']} "
            f"{item['strength']}{form}?"
        )
        if item["active_ingredient"] == "medicamentos homeopáticos":
            question = (
                "Na RENAME, há registro de medicamentos homeopáticos conforme a "
                "Farmacopeia Homeopática Brasileira vigente?"
            )
        elif source == "F03" and item["active_ingredient"].startswith("imunoglobulina anti-rho"):
            question = (
                "Na REME-DF, há registro de imunoglobulina anti-rho (anti-d) "
                "solução injetável de 250 mcg a 300 mcg em frasco-ampola ou seringa preenchida?"
            )
        elif source == "F03" and item["active_ingredient"] == "solução de ringer com lactato":
            question = (
                "Na REME-DF, há registro de solução de ringer com lactato injetável "
                "em bolsa ou frasco de 500 mL, sistema fechado de infusão?"
            )
        elif source == "F04" and item["active_ingredient"] == "etinilestradiol + levonorgestrel":
            question = (
                "Na Farmácia Popular, há registro de etinilestradiol 0,03mg + "
                "levonorgestrel 0,15mg?"
            )
        evs = evidence_by_med_source[(item["medicine_id"], source)]
        cases.append(
            {
                "id": f"V9-NEW-{index:03d}",
                "family_id": normalize(item["active_ingredient"]),
                "split": "test",
                "question": question,
                "source_id": source,
                "expected_status": "matched",
                "expected_references": [
                    _reference(ev, item["exact_presentation_supported"]) for ev in evs
                ],
                "relevant_ids": sorted(ev["evidence_id"] for ev in evs),
                "release_fingerprint": release.fingerprint,
                "review_status": "agent_reviewed",
                "reviewer": "agent_technical_audit",
                "synthetic": True,
            }
        )
    for index, (source, ingredient, strength, form) in enumerate(NEGATIVES, 25):
        family = normalize(ingredient)
        if family not in used:
            raise ValueError(f"Negativo sem família positiva correspondente: {ingredient}")
        if any(
            source in item["source_ids"]
            and normalize(item["active_ingredient"]) == family
            and normalize(item["strength"]) == normalize(strength)
            and (form is None or normalize(item["form"]) == normalize(form))
            for item in release.catalog
        ):
            raise ValueError(f"Negativo presente no catálogo: {ingredient} {strength}")
        presentation = f"{ingredient} {strength}" + (f" {form}" if form else "")
        cases.append(
            {
                "id": f"V9-NEW-{index:03d}",
                "family_id": family,
                "split": "test",
                "question": f"Na {SOURCE_NAMES[source]}, há registro de {presentation}?",
                "source_id": source,
                "expected_status": "not_in_scope",
                "expected_references": [],
                "relevant_ids": [],
                "release_fingerprint": release.fingerprint,
                "review_status": "agent_reviewed",
                "reviewer": "agent_technical_audit",
                "synthetic": True,
            }
        )
    if len(cases) != 28 or {c["family_id"] for c in cases} & dev_families:
        raise ValueError("Candidato não independente do desenvolvimento")
    return cases


def main() -> None:
    if TARGET.exists() or REVIEW.exists():
        raise ValueError("Candidato v2 já existe; preservar a versão para auditoria")
    cases = prepare()
    target_bytes = jsonl_bytes(cases)
    lines = [
        "# Revisão humana do novo teste independente v9 — candidato v2",
        "",
        "**Estado:** candidato v2 não avaliado; nenhuma consulta deste conjunto foi executada. "
        "A aprovação documental da v9 não aprova estas expectativas.",
        "",
        "Para cada caso, conferir pergunta, status, apresentação, evidência, fonte e "
        "página com o PDF oficial. Registrar decisão, nome, data e justificativa em caso "
        "de rejeição. Editar o gabarito somente antes de congelar o teste; uma rejeição "
        "não deve ser convertida silenciosamente em aprovação.",
        "",
        (
            "Fontes: [F01 RENAME 2024](https://www.gov.br/saude/pt-br/composicao/sectics/"
            "rename/publicacoes/relacao-nacional-de-medicamentos-essenciais-2024), "
            "[F03 REME-DF 2026](https://www.saude.df.gov.br/documents/d/saude/"
            "reme_df___29_10_2026___final-pdf), "
            "[F04 Farmácia Popular](https://www.gov.br/saude/pt-br/composicao/sectics/"
            "farmacia-popular/arquivos/elenco-de-medicamentos-e-insumos-pfpb.pdf)."
        ),
        "",
        "| ID | Fonte | Pergunta | Esperado | Apresentação | Evidência e página | Decisão | "
        "Revisor/data | Justificativa se rejeitado |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for case in cases:
        refs = "; ".join(
            f"{ref['evidence_id']} p.{ref['page']} linha {ref['source_row_number']}"
            for ref in case["expected_references"]
        ) or "—"
        presentation = "; ".join(
            sorted(
                {
                    presentation_for_review(ref)
                    for ref in case["expected_references"]
                }
            )
        ) or "—"
        lines.append(
            f"| {case['id']} | {case['source_id']} | {case['question']} | "
            f"{case['expected_status']} | {presentation} | {refs} | Pendente | — | — |"
        )
    TARGET.write_bytes(target_bytes)
    REVIEW.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{len(cases)} casos candidatos; nenhuma execução de test")


if __name__ == "__main__":
    main()
