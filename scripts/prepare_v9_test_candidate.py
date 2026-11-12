"""Prepare an unopened, source-linked v9 test candidate for human review."""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rag.consolidated import ConsolidatedRelease, jsonl_bytes, normalize  # noqa: E402

RELEASE = ROOT / "data/releases/corpus-consolidado-v9-aprovado-2026-11-12"
DEV = ROOT / "evals/datasets/consolidated_v9_dev_exploratory.jsonl"
TARGET = ROOT / "evals/datasets/consolidated_v9_test_candidate_unreviewed.jsonl"
REVIEW = ROOT / "docs/reports/v9-independent-test-review.md"
SOURCE_NAMES = {"F01": "RENAME", "F03": "REME-DF", "F04": "Farmácia Popular"}


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
    for index, (source, item) in enumerate(selected[:4], 25):
        cases.append(
            {
                "id": f"V9-NEW-{index:03d}",
                "family_id": normalize(item["active_ingredient"]),
                "split": "test",
                "question": (
                    f"A {SOURCE_NAMES[source]} registra {item['active_ingredient']} "
                    "99999 mg nesta apresentação?"
                ),
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
    cases = prepare()
    TARGET.write_bytes(jsonl_bytes(cases))
    lines = [
        "# Revisão humana do novo teste independente v9",
        "",
        "**Estado:** candidato fechado; nenhuma consulta deste conjunto foi executada. "
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
                    f"{ref['active_ingredient']} {ref['strength']} {ref['form']}"
                    for ref in case["expected_references"]
                }
            )
        ) or "—"
        lines.append(
            f"| {case['id']} | {case['source_id']} | {case['question']} | "
            f"{case['expected_status']} | {presentation} | {refs} | Pendente | — | — |"
        )
    REVIEW.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{len(cases)} casos candidatos; nenhuma execução de test")


if __name__ == "__main__":
    main()
