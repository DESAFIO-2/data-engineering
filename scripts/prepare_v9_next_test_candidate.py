"""Prepare a new, unopened v9 holdout after the first official gate failed."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rag.consolidated import ConsolidatedRelease, jsonl_bytes, normalize  # noqa: E402

RELEASE = ROOT / "data/releases/corpus-consolidado-v9-aprovado-2026-11-12"
PRIOR_DATASETS = (
    ROOT / "evals/datasets/consolidated_v8_reviewed.jsonl",
    ROOT / "evals/datasets/consolidated_v9_reviewed.jsonl",
)
TARGET = ROOT / "evals/datasets/consolidated_v9_next_test_candidate_unreviewed.jsonl"
REVIEW = ROOT / "docs/reports/v9/v9-next-independent-test-review.md"
SOURCE_NAMES = {"F01": "RENAME", "F03": "REME-DF", "F04": "Farmácia Popular"}

# F01/F03 families are absent from both prior datasets. F04 has no unused
# families in this release; these three are absent from the current v9 dataset
# but appeared historically in v8. The review sheet states that limitation.
POSITIVE_SPECS = (
    ("F01", "calcitriol", "0,25 mcg", "cápsula"),
    ("F01", "cloridrato de metoclopramida", "10 mg", "comprimido"),
    ("F01", "cloridrato de ondansetrona", "4 mg", "comprimido orodispersível"),
    ("F01", "dicloridrato de sapropterina", "100 mg", "comprimido solúvel"),
    ("F01", "galsulfase", "5 mg", "solução injetável"),
    ("F01", "glicerol", "120 mg/mL", "solução retal"),
    ("F01", "gliclazida", "30 mg", "comprimido de liberação prolongada"),
    ("F01", "hidróxido de alumínio", "230 mg", "comprimido"),
    ("F01", "imiglucerase", "400 U", "pó para solução injetável"),
    ("F01", "lactulose", "667 mg/mL", "xarope"),
    ("F01", "nistatina", "100.000 UI/mL", "suspensão oral"),
    ("F03", "carvedilol", "3,125 mg", "comprimido"),
    ("F03", "digoxina", "0,25 mg", "comprimido"),
    ("F03", "epinefrina", "1 mg/mL", "solução injetável"),
    ("F03", "misoprostol", "25 mcg", "comprimido vaginal"),
    ("F03", "levotiroxina sódica", "25 mcg", "comprimido"),
    ("F03", "prednisona", "5 mg", "comprimido"),
    ("F03", "aciclovir", "200 mg", "comprimido"),
    ("F03", "fluconazol", "150 mg", "cápsula"),
    ("F03", "lopinavir + ritonavir", "100 mg + 25 mg", "comprimido"),
    ("F03", "metronidazol", "400 mg", "comprimido"),
    ("F04", "captopril", "25mg", "-"),
    ("F04", "furosemida", "40 mg", "-"),
    ("F04", "acetato de medroxiprogesterona", "150mg", "-"),
)
NEGATIVE_SPECS = (
    ("F01", "calcitriol", "0,5 mcg", "cápsula"),
    ("F03", "digoxina", "0,125 mg", "comprimido"),
    ("F03", "misoprostol", "100 mcg", "comprimido vaginal"),
    ("F04", "captopril", "50mg", "-"),
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


def _question(source: str, name: str, strength: str, form: str) -> str:
    presentation = f"{name} {strength}" + (f" {form}" if form != "-" else "")
    return f"Segundo a {SOURCE_NAMES[source]}, consta {presentation}?"


def presentation_for_review(case: dict) -> str:
    return "; ".join(
        sorted(
            {
                f"{ref['active_ingredient']} {ref['strength']}"
                + (f" {ref['form']}" if ref["form"] != "-" else "")
                for ref in case["expected_references"]
            }
        )
    ) or "—"


def prepare() -> list[dict]:
    release = ConsolidatedRelease.load(RELEASE)
    old = [
        json.loads(line)
        for path in PRIOR_DATASETS
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    ]
    old_families = {normalize(case["family_id"]) for case in old}
    current_dev = {
        normalize(case["family_id"])
        for case in old
        if case["split"] == "dev" and case["release_fingerprint"] == release.fingerprint
    }
    current_test = {
        normalize(case["family_id"])
        for case in old
        if case["split"] == "test" and case["release_fingerprint"] == release.fingerprint
    }
    catalog = {
        (
            source,
            normalize(item["active_ingredient"]),
            normalize(item["strength"]),
            normalize(item["form"]),
        ): item
        for item in release.catalog
        for source in item["source_ids"]
    }
    evidence_by_key: dict[tuple[str, str], list[dict]] = {}
    for ev in release.evidence:
        evidence_by_key.setdefault((ev["medicine_id"], ev["source"]["source_id"]), []).append(ev)

    cases = []
    selected_families = set()
    for index, (source, name, strength, form) in enumerate(POSITIVE_SPECS, 1):
        family = normalize(name)
        key = (source, family, normalize(strength), normalize(form))
        item = catalog.get(key)
        if item is None or (item["medicine_id"], source) not in evidence_by_key:
            raise ValueError(f"Apresentação sem evidência no release: {key}")
        if family in selected_families or (source != "F04" and family in old_families):
            raise ValueError(f"Família não independente: {key}")
        if source == "F04" and family in current_dev | current_test:
            raise ValueError(f"Família F04 já usada no teste/desenvolvimento v9: {name}")
        selected_families.add(family)
        evs = evidence_by_key[(item["medicine_id"], source)]
        cases.append(
            {
                "id": f"V9-R2-{index:03d}",
                "family_id": family,
                "split": "test",
                "question": _question(source, name, strength, form),
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
                "family_reused_from_v8": source == "F04",
            }
        )
    for index, (source, name, strength, form) in enumerate(NEGATIVE_SPECS, 25):
        family = normalize(name)
        key = (source, family, normalize(strength), normalize(form))
        if family not in selected_families or key in catalog:
            raise ValueError(f"Negativo sem par positivo ou presente no release: {key}")
        cases.append(
            {
                "id": f"V9-R2-{index:03d}",
                "family_id": family,
                "split": "test",
                "question": _question(source, name, strength, form),
                "source_id": source,
                "expected_status": "not_in_scope",
                "expected_references": [],
                "relevant_ids": [],
                "release_fingerprint": release.fingerprint,
                "review_status": "agent_reviewed",
                "reviewer": "agent_technical_audit",
                "synthetic": True,
                "family_reused_from_v8": source == "F04",
            }
        )
    if len(cases) != 28 or len({case["id"] for case in cases}) != 28:
        raise ValueError("Novo candidato exige 28 IDs únicos")
    return cases


def main() -> None:
    if TARGET.exists() or REVIEW.exists():
        raise ValueError("Novo candidato já existe; preservar para auditoria")
    cases = prepare()
    lines = [
        "# Revisão humana — nova rodada independente de recuperação v9",
        "",
        "**Estado:** candidato não avaliado; nenhuma pergunta foi enviada ao recuperador. "
        "As famílias F01/F03 são inéditas frente aos datasets v8/v9. As três famílias "
        "F04 já apareceram na v8, pois o release não contém famílias F04 inéditas; "
        "elas não aparecem no desenvolvimento ou teste v9 congelado.",
        "",
        "Conferir cada pergunta, status, apresentação e evidência nos PDFs oficiais. "
        "Registrar Aprovado ou Rejeitado, revisor/data e justificativa de rejeição. "
        "Este parecer técnico não substitui a decisão humana. Não executar o split test.",
        "",
        "Fontes: [F01 RENAME 2024](https://www.gov.br/saude/pt-br/composicao/sectics/"
        "rename/publicacoes/relacao-nacional-de-medicamentos-essenciais-2024), "
        "[F03 REME-DF 2026](https://www.saude.df.gov.br/documents/d/saude/"
        "reme_df___29_10_2026___final-pdf), "
        "[F04 Farmácia Popular](https://www.gov.br/saude/pt-br/composicao/sectics/"
        "farmacia-popular/arquivos/elenco-de-medicamentos-e-insumos-pfpb.pdf).",
        "",
        "| ID | Fonte | Pergunta | Esperado | Apresentação | Evidência e página | "
        "Decisão | Revisor/data | Justificativa se rejeitado |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for case in cases:
        refs = "; ".join(
            f"{ref['evidence_id']} p.{ref['page']} linha {ref['source_row_number']}"
            for ref in case["expected_references"]
        ) or "—"
        presentations = presentation_for_review(case)
        lines.append(
            f"| {case['id']} | {case['source_id']} | {case['question']} | "
            f"{case['expected_status']} | {presentations} | {refs} | Pendente | — | — |"
        )
    TARGET.write_bytes(jsonl_bytes(cases))
    REVIEW.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("28 casos candidatos; split test não executado")


if __name__ == "__main__":
    main()
