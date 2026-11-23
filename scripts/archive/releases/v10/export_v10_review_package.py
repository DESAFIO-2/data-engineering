"""Export F8 human-review CSV spreadsheets and approval template for v10 normalized."""

from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

from rag.config import ROOT
from rag.consolidated import CHUNK_RECIPE_V3, chunk_for

sys.path.insert(0, str(ROOT / "scripts"))
from scripts.ingest.publish_consolidated_release import digest, read_lines  # noqa: E402

V9_DIR = ROOT / "data/releases/corpus-consolidado-v9-aprovado-2026-11-12"
V10_DIR = ROOT / "data/releases/corpus-consolidado-v10-normalizada-2026-11-17"
OUT_DIR = ROOT / "docs/reports/v10"
DEV_COMP = ROOT / "evals/results/v10_candidate_dev_comparison.json"


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})


def export_package(
    v9_dir: Path = V9_DIR, v10_dir: Path = V10_DIR, out_dir: Path = OUT_DIR
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    v9_occ = {
        o["occurrence_id"]: o for o in read_lines((v9_dir / "occurrences.jsonl").read_bytes())
    }
    v10_occ = read_lines((v10_dir / "occurrences.jsonl").read_bytes())
    v10_occ_by_id = {o["occurrence_id"]: o for o in v10_occ}
    v10_cat_by_id = {
        c["medicine_id"]: c for c in read_lines((v10_dir / "catalog.jsonl").read_bytes())
    }
    v10_ev = read_lines((v10_dir / "evidencias.jsonl").read_bytes())
    id_map = json.loads((v10_dir / "id_map_v9_v10.json").read_text(encoding="utf-8"))
    norm_bundle = json.loads((v10_dir / "normalization.json").read_text(encoding="utf-8"))
    quality = json.loads((v10_dir / "quality_report.json").read_text(encoding="utf-8"))
    manifest_sha = digest((v10_dir / "release.json").read_bytes())
    manifest = json.loads((v10_dir / "release.json").read_text(encoding="utf-8"))

    # 1. merges.csv
    merge_rows: list[dict[str, Any]] = []
    for rec in id_map["merged"]:
        can_med = v10_cat_by_id[rec["canonical_medicine_id"]]
        absorbed_oids = set(rec["occurrence_ids"])
        kept_oids = [oid for oid in can_med["occurrence_ids"] if oid not in absorbed_oids]
        pages = sorted(
            {
                f"{v10_occ_by_id[oid]['source']['source_id']}:p.{v10_occ_by_id[oid]['source']['page']}"
                for oid in can_med["occurrence_ids"]
            }
        )
        rules = sorted(
            {
                r
                for oid in can_med["occurrence_ids"]
                for r in v10_occ_by_id[oid]["normalized"]["rules_applied"]
            }
        )
        merge_rows.append(
            {
                "canonical_medicine_id": rec["canonical_medicine_id"],
                "merged_medicine_id": rec["merged_medicine_id"],
                "canonical_label": rec["canonical_label"],
                "before_label": rec["before_label"],
                "before_sources": ", ".join(rec["before_sources"]),
                "canonical_sources": ", ".join(rec["canonical_sources"]),
                "canonical_raw_texts": " || ".join(
                    v10_occ_by_id[oid]["raw_text"].replace("\n", " ") for oid in kept_oids
                ),
                "absorbed_raw_texts": " || ".join(
                    v10_occ_by_id[oid]["raw_text"].replace("\n", " ")
                    for oid in rec["occurrence_ids"]
                ),
                "pages": ", ".join(pages),
                "rules_applied": ", ".join(rules),
                "confidence": "exact_rule",
                "decision": "",
                "notes": "",
            }
        )
    _write_csv(
        out_dir / "merges.csv",
        [
            "canonical_medicine_id",
            "merged_medicine_id",
            "canonical_label",
            "before_label",
            "before_sources",
            "canonical_sources",
            "canonical_raw_texts",
            "absorbed_raw_texts",
            "pages",
            "rules_applied",
            "confidence",
            "decision",
            "notes",
        ],
        merge_rows,
    )

    # 2. vocab_forms.csv
    form_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for occ in v10_occ:
        form_groups[occ["form"]].append(occ)
    form_rows: list[dict[str, Any]] = []
    for lit, group in sorted(form_groups.items(), key=lambda item: (-len(item[1]), item[0])):
        norm = group[0]["normalized"]
        rules = sorted(
            {r for o in group for r in o["normalized"]["rules_applied"] if r.startswith("form_")}
        )
        confidence = "manual" if "form_synonym" in rules else "exact_rule"
        form_rows.append(
            {
                "literal_form": lit,
                "occurrences": len(group),
                "sources": ", ".join(sorted({o["source"]["source_id"] for o in group})),
                "canonical_form": norm["form"] or "",
                "form_kind": norm["form_kind"],
                "release": norm["release"] or "",
                "package": norm["package"] or "",
                "specification": norm["specification"] or "",
                "form_alternatives": " | ".join(norm["form_alternatives"]),
                "rules_applied": ", ".join(rules),
                "confidence": confidence,
                "decision": "",
                "notes": "",
            }
        )
    _write_csv(
        out_dir / "vocab_forms.csv",
        [
            "literal_form",
            "occurrences",
            "sources",
            "canonical_form",
            "form_kind",
            "release",
            "package",
            "specification",
            "form_alternatives",
            "rules_applied",
            "confidence",
            "decision",
            "notes",
        ],
        form_rows,
    )

    # 3. vocab_channels.csv
    chan_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for occ in v10_occ:
        if occ.get("channel"):
            chan_groups[occ["channel"]].append(occ)
    chan_rows: list[dict[str, Any]] = []
    for lit, group in sorted(chan_groups.items(), key=lambda item: (-len(item[1]), item[0])):
        norm = group[0]["normalized"]
        rules = sorted(
            {r for o in group for r in o["normalized"]["rules_applied"] if r.startswith("channel_")}
        )
        chan_rows.append(
            {
                "literal_channel": lit,
                "occurrences": len(group),
                "channel_text": norm["channel_text"] or "",
                "channel_codes": ", ".join(norm["channel_codes"]),
                "channel_note_codes": ", ".join(norm["channel_note_codes"]),
                "channel_notes": " || ".join(norm["channel_notes"]),
                "channel_flags": ", ".join(norm["channel_flags"]),
                "rules_applied": ", ".join(rules),
                "confidence": "exact_rule",
                "decision": "",
                "notes": "",
            }
        )
    _write_csv(
        out_dir / "vocab_channels.csv",
        [
            "literal_channel",
            "occurrences",
            "channel_text",
            "channel_codes",
            "channel_note_codes",
            "channel_notes",
            "channel_flags",
            "rules_applied",
            "confidence",
            "decision",
            "notes",
        ],
        chan_rows,
    )

    # 4. ingredient_variants.csv
    ing_rows: list[dict[str, Any]] = []
    for m in norm_bundle["files"]["ingredients.json"]["content"]["mappings"]:
        ing_rows.append(
            {
                "variant": m["variant"],
                "canonical": m["canonical"],
                "reason": m["reason"],
                "variant_sources": ", ".join(m["variant_sources"]),
                "canonical_sources": ", ".join(m["canonical_sources"]),
                "occurrences": m["occurrences"],
                "confidence": "exact_rule" if m["reason"] in {"case", "accent"} else "manual",
                "decision": "",
                "notes": "",
            }
        )
    _write_csv(
        out_dir / "ingredient_variants.csv",
        [
            "variant",
            "canonical",
            "reason",
            "variant_sources",
            "canonical_sources",
            "occurrences",
            "confidence",
            "decision",
            "notes",
        ],
        ing_rows,
    )

    # 5. parser_corrections.csv
    parser_rows: list[dict[str, Any]] = []
    for corr in quality.get("corrections_applied", []):
        if corr.get("scope") != "corrected_v10_parser":
            continue
        oid = corr["occurrence_id"]
        o10 = v10_occ_by_id[oid]
        o9 = v9_occ[oid]
        parser_rows.append(
            {
                "occurrence_id": oid,
                "source_id": corr["source_id"],
                "page": o10["source"]["page"],
                "source_row_number": o10.get("source_row_number"),
                "field": corr["field"],
                "before": "" if corr["before"] is None else corr["before"],
                "after": corr["after"],
                "raw_text": o9["raw_text"],
                "confidence": "exact_rule",
                "decision": "",
                "notes": "",
            }
        )
    _write_csv(
        out_dir / "parser_corrections.csv",
        [
            "occurrence_id",
            "source_id",
            "page",
            "source_row_number",
            "field",
            "before",
            "after",
            "raw_text",
            "confidence",
            "decision",
            "notes",
        ],
        parser_rows,
    )

    # 6. chunks_sample.csv (30 stratified chunks)
    ev_by_oid = {e["occurrence_id"]: e for e in v10_ev}
    samples: list[tuple[str, str]] = []
    picked: set[str] = set()

    def _pick(stratum: str, predicate: Any, limit: int) -> None:
        count = 0
        for occ in v10_occ:
            oid = occ["occurrence_id"]
            if oid in picked:
                continue
            if predicate(occ):
                picked.add(oid)
                samples.append((stratum, oid))
                count += 1
                if count >= limit:
                    break

    _pick(
        "f03_duplicate_desc_distinct_channel",
        lambda o: (
            o["source"]["source_id"] == "F03"
            and o["source_code"] in {"607", "MS607", "4630", "MS4630", "1038", "MS1038"}
        ),
        6,
    )
    _pick(
        "f03_channel_with_notes",
        lambda o: o["source"]["source_id"] == "F03" and bool(o["normalized"]["channel_notes"]),
        4,
    )
    _pick(
        "f03_package_only",
        lambda o: (
            o["source"]["source_id"] == "F03" and o["normalized"]["form_kind"] == "package_only"
        ),
        3,
    )
    _pick(
        "f03_salt_alias_merged",
        lambda o: (
            o["source"]["source_id"] == "F03"
            and "ingredient_vocab" in o["normalized"]["rules_applied"]
        ),
        3,
    )
    _pick(
        "f01_component_fixed",
        lambda o: (
            o["source"]["source_id"] == "F01"
            and v9_occ[o["occurrence_id"]].get("component") is None
        ),
        4,
    )
    _pick(
        "f01_atc_special",
        lambda o: (
            o["source"]["source_id"] == "F01"
            and o["normalized"]["atc"]["kind"] in {"herbal", "multiple", "not_classified"}
        ),
        3,
    )
    _pick(
        "f01_supply", lambda o: o["source"]["source_id"] == "F01" and o["item_type"] == "supply", 2
    )
    _pick(
        "f04_medicine_and_prolonged",
        lambda o: o["source"]["source_id"] == "F04" and o["item_type"] == "medicine",
        3,
    )
    _pick(
        "f04_supply", lambda o: o["source"]["source_id"] == "F04" and o["item_type"] == "supply", 2
    )

    sample_rows: list[dict[str, Any]] = []
    for stratum, oid in samples[:30]:
        ev = ev_by_oid[oid]
        ch = chunk_for(ev, manifest["release_version"], recipe=CHUNK_RECIPE_V3)
        sample_rows.append(
            {
                "stratum": stratum,
                "chunk_id": ch["chunk_id"],
                "source_id": ch["source"]["source_id"],
                "page": ch["source"]["page"],
                "item_type": ch["item_type"],
                "channel_codes": ", ".join(ch["channel_codes"]),
                "char_len": len(ch["text"]),
                "chunk_text": ch["text"],
                "decision": "",
                "notes": "",
            }
        )
    _write_csv(
        out_dir / "chunks_sample.csv",
        [
            "stratum",
            "chunk_id",
            "source_id",
            "page",
            "item_type",
            "channel_codes",
            "char_len",
            "chunk_text",
            "decision",
            "notes",
        ],
        sample_rows,
    )

    # 7. Approval template
    dev_block = ""
    if DEV_COMP.exists():
        comp = json.loads(DEV_COMP.read_text(encoding="utf-8"))
        lines_md = [
            "| Conjunto (split `dev`) | Estratégia | Δ Hit@1 | Δ Hit@5 | Δ MRR@5 | Δ Status |",
            "|---|---|---:|---:|---:|---:|",
        ]
        for ds_name, strats in comp["deltas_v10_minus_v9"].items():
            for strat, m in strats.items():
                lines_md.append(
                    f"| `{ds_name}` | `{strat}` | {m['hit_at_1']:+.4f} "
                    f"| {m['hit_at_5']:+.4f} | {m['mrr_at_5']:+.4f} "
                    f"| {m['status_accuracy']:+.4f} |"
                )
        dev_block = "\n".join(lines_md)

    norm_sum = quality["normalization_summary"]
    template = "\n".join(
        [
            "# Revisão Humana — Release Candidato `v10` Normalizado",
            "",
            f"**Candidato:** `{manifest['release_version']}`",
            f"**Origem aprovada:** `{v9_dir.name}`",
            f"**SHA-256 do manifesto candidato:** `{manifest_sha}`",
            f"**Fingerprint do corpus:** `{manifest['corpus_fingerprint']}`",
            f"**Receita de chunks verificada:** `{CHUNK_RECIPE_V3}`",
            "",
            "---",
            "",
            "## 1. Resumo das alterações verificadas",
            "",
            (
                f"- **Catálogo deduplicado:** `{norm_sum['catalog_before']}` → "
                f"`{norm_sum['catalog_after']}` apresentações (`{norm_sum['merged_entries']}` "
                "absorções em `merges.csv`, incluindo as 80 colisões anteriores e 52 "
                "variantes ortográficas/de sal/de forma)."
            ),
            (
                "- **Literais preservados:** todas as 2.114 ocorrências mantêm `raw_text`, "
                "grafia, concentração, forma e canal literais da fonte; campos padronizados "
                "ficam exclusivamente em `normalized`."
            ),
            (
                f"- **Correções de parser (`corrected_v10_parser`):** "
                f"`{norm_sum['parser_corrections']}` registros na `F01` (53 componentes nulos "
                "preenchidos pela coluna 4 do `raw_text` e `0/ ,3 mg/mL` → `0,3 mg/mL` "
                "conferido na p. 41 do PDF)."
            ),
            (
                f"- **Canais F03 e chunks v3:** "
                f"`{norm_sum['f03_channels_with_codes']}/{norm_sum['f03_occurrences']}` "
                f"ocorrências F03 com códigos de canal; `{norm_sum['chunk_unique_texts']}/2114` "
                f"textos únicos de chunk (`p50={norm_sum['chunk_p50_chars']}`, "
                f"`p95={norm_sum['chunk_p95_chars']}`, `max={norm_sum['chunk_max_chars']}` "
                "caracteres)."
            ),
            "",
            "---",
            "",
            "## 2. Comparativo `v9 × v10` no split `dev` (`exact` / `lexical`)",
            "",
            dev_block or "_Execute `scripts/eval_v10_dev_comparison.py` antes da revisão._",
            "",
            "---",
            "",
            "## 3. Planilhas de revisão humana (F8)",
            "",
            "| Arquivo | Registros | Foco de conferência |",
            "|---|---:|---|",
            (
                f"| [merges.csv](merges.csv) | {len(merge_rows)} "
                "| Conferir se cada par absorvido representa a mesma apresentação |"
            ),
            (
                f"| [vocab_forms.csv](vocab_forms.csv) | {len(form_rows)} "
                "| Conferir forma controlada, `package` e `specification` (`confidence=manual`) |"
            ),
            (
                f"| [vocab_channels.csv](vocab_channels.csv) | {len(chan_rows)} "
                "| Conferir texto limpo, códigos de canal e notas de rodapé separadas |"
            ),
            (
                f"| [ingredient_variants.csv](ingredient_variants.csv) | {len(ing_rows)} "
                "| Conferir grafia canônica RENAME/DCB vs variantes de sal/acento/caixa |"
            ),
            (
                f"| [parser_corrections.csv](parser_corrections.csv) | {len(parser_rows)} "
                "| Conferir as 54 correções na F01 contra `raw_text`/PDF |"
            ),
            (
                f"| [chunks_sample.csv](chunks_sample.csv) | {len(sample_rows)} "
                "| Amostra estratificada dos chunks `one-evidence-v3` |"
            ),
            "",
            "---",
            "",
            "## 4. Como aprovar após revisão humana",
            "",
            (
                "Após preencher as planilhas e registrar a decisão final em "
                "`docs/reports/v10/revisao-v10-normalizada-jhiovana.md` contendo literalmente "
                f'a frase `"pode aprovar a revisao"` e o hash `{manifest_sha}`, executar:'
            ),
            "",
            "```bash",
            (
                "PYTHONPATH=src uv run python -m scripts.approve_v10_release "
                f"--candidate-sha256 {manifest_sha}"
            ),
            "```",
            "",
        ]
    )
    (out_dir / "revisao-v10-normalizada-template.md").write_text(template, encoding="utf-8")

    return {
        "merges": len(merge_rows),
        "vocab_forms": len(form_rows),
        "vocab_channels": len(chan_rows),
        "ingredient_variants": len(ing_rows),
        "parser_corrections": len(parser_rows),
        "chunks_sample": len(sample_rows),
        "manifest_sha256": manifest_sha,
    }


def main() -> int:
    summary = export_package()
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
