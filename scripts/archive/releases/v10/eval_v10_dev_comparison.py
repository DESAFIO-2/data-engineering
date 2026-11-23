"""Run paired v9 vs v10-normalized exact/lexical evaluation on dev splits only (F7)."""

from __future__ import annotations

import json
import re
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from rag.config import ROOT
from rag.consolidated import ConsolidatedRelease, load_chunks, normalize, search
from rag.normalization import fold

sys.path.insert(0, str(ROOT / "scripts"))
from scripts.archive.releases.v10 import approve_v10_release  # noqa: E402
from scripts.ingest.publish_consolidated_release import digest  # noqa: E402

V9_RELEASE = ROOT / "data/releases/corpus-consolidado-v9-aprovado-2026-11-12"
V9_CHUNKS = ROOT / "data/derived/chunks/corpus-consolidado-v9-aprovado-2026-11-12"
V10_CANDIDATE = ROOT / "data/releases/corpus-consolidado-v10-normalizada-2026-11-17"

DATASETS = {
    "consolidated_v9_reviewed_dev": ROOT / "evals/datasets/consolidated_v9_reviewed.jsonl",
    "week3_v9_dev_draft": ROOT / "evals/datasets/week3_v9_dev_draft.jsonl",
    "multichunk_v9_benchmark_dev": ROOT / "evals/datasets/multichunk_v9_benchmark.jsonl",
    "week3_v10_channel_dev_draft": ROOT / "evals/datasets/week3_v10_channel_dev_draft.jsonl",
}
FROZEN_TEST_FILES = (
    ROOT / "evals/datasets/consolidated_v9_reviewed.jsonl",
    ROOT / "evals/datasets/week3_v9_test_reviewed.jsonl",
    ROOT / "evals/datasets/multichunk_v9_benchmark.jsonl",
)


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def _assert_channel_dev_has_no_test_leakage(channel_path: Path) -> None:
    test_families: set[str] = set()
    for path in FROZEN_TEST_FILES:
        for row in _load_jsonl(path):
            if row.get("split") == "test" and row.get("family_id"):
                test_families.add(fold(row["family_id"]))
    for row in _load_jsonl(channel_path):
        if row.get("split") != "dev":
            raise ValueError(f"Conjunto de canais só deve ter split=dev: {row['id']}")
        if fold(row["family_id"]) in test_families:
            raise ValueError(f"Vazamento de família de teste em {row['id']}: {row['family_id']}")


def _explicit_source_filter(question: str) -> str | None:
    query = normalize(question)
    if re.search(r"\b(?:reme|reme-df|f03)\b", query):
        return "F03"
    if "farmacia popular" in query or re.search(r"\bf04\b", query):
        return "F04"
    if re.search(r"\b(?:rename|f01)\b", query):
        return "F01"
    return None


def _run_dev_subset(
    cases: list[dict[str, Any]],
    release: ConsolidatedRelease,
    chunks: list[dict[str, Any]],
    strategy: str,
) -> dict[str, Any]:
    dev_cases = [c for c in cases if c.get("split") == "dev"]
    evidence_by_id = {e["evidence_id"]: e for e in release.evidence}
    chunk_by_ev = {c["evidence_id"]: c for c in chunks}
    records: list[dict[str, Any]] = []
    for case in dev_cases:
        result = search(case["question"], release, chunks, strategy=strategy, top_k=5)
        relevant = set(case.get("relevant_ids") or [])
        found = result.get("evidence", [])
        retrieved = [e["evidence_id"] for e in found]
        rank = next((i for i, eid in enumerate(retrieved, 1) if eid in relevant), None)
        expected_mids = {ref["medicine_id"] for ref in case.get("expected_references", [])}
        returned_mids = {e.get("medicine_id") for e in found}
        presentation_correct = (not expected_mids) or returned_mids == expected_mids
        requested_source = _explicit_source_filter(case["question"])
        critical = result["status"] == "matched" and (
            case["expected_status"] != "matched"
            or (bool(expected_mids) and not presentation_correct)
            or (
                requested_source is not None
                and any(item["source"]["source_id"] != requested_source for item in found)
            )
        )
        citations_ok = [
            evidence_by_id.get(e["evidence_id"]) == e
            and chunk_by_ev.get(e["evidence_id"], {}).get("source") == e["source"]
            and e["source"].get("page") is not None
            and bool(e["source"].get("url"))
            for e in found
        ]
        records.append(
            {
                "id": case["id"],
                "expected_status": case["expected_status"],
                "status": result["status"],
                "status_correct": result["status"] == case["expected_status"],
                "first_relevant_rank": rank,
                "presentation_correct": presentation_correct,
                "critical_confusion": critical,
                "citations_ok": citations_ok,
                "retrieved_evidence_ids": retrieved,
                "expected_evidence_ids": list(relevant),
            }
        )
    positive = [r for r in records if r["expected_status"] == "matched"]
    negative = [r for r in records if r["expected_status"] != "matched"]
    all_cites = [ok for r in records for ok in r["citations_ok"]]
    return {
        "cases": len(records),
        "positive_cases": len(positive),
        "negative_cases": len(negative),
        "status_accuracy": sum(r["status_correct"] for r in records) / len(records),
        "correct_abstention": (
            sum(r["status_correct"] for r in negative) / len(negative) if negative else None
        ),
        "presentation_accuracy": (
            sum(r["presentation_correct"] for r in positive) / len(positive) if positive else None
        ),
        "critical_confusions": sum(r["critical_confusion"] for r in records),
        "citation_precision": sum(all_cites) / len(all_cites) if all_cites else None,
        "hit_at_1": sum(r["first_relevant_rank"] == 1 for r in positive) / len(positive),
        "hit_at_3": sum(
            r["first_relevant_rank"] is not None and r["first_relevant_rank"] <= 3 for r in positive
        )
        / len(positive),
        "hit_at_5": sum(
            r["first_relevant_rank"] is not None and r["first_relevant_rank"] <= 5 for r in positive
        )
        / len(positive),
        "mrr_at_5": sum(
            1 / r["first_relevant_rank"] if r["first_relevant_rank"] else 0 for r in positive
        )
        / len(positive),
        "failures": [
            r
            for r in records
            if not r["status_correct"]
            or r["critical_confusion"]
            or (r["expected_status"] == "matched" and r["first_relevant_rank"] != 1)
        ],
    }


def _remap_consolidated_for_v10(
    cases: list[dict[str, Any]],
    v10_release: ConsolidatedRelease,
    id_map: dict[str, str],
) -> list[dict[str, Any]]:
    ev_by_id = {e["evidence_id"]: e for e in v10_release.evidence}
    remapped: list[dict[str, Any]] = []
    for row in cases:
        if row.get("split") != "dev":
            continue
        case = json.loads(json.dumps(row))
        case["release_fingerprint"] = v10_release.fingerprint
        for ref in case.get("expected_references", []):
            ev = ev_by_id[ref["evidence_id"]]
            ref["medicine_id"] = id_map.get(ref["medicine_id"], ref["medicine_id"])
            ref["strength"] = ev["strength"]
        remapped.append(case)
    return remapped


def _eval_release(
    release: ConsolidatedRelease,
    chunks: list[dict[str, Any]],
    chunk_manifest: dict[str, Any],
    *,
    is_v10: bool,
    id_map: dict[str, str] | None = None,
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "release_version": release.manifest["release_version"],
        "release_fingerprint": release.fingerprint,
        "chunk_recipe": chunk_manifest["recipe"],
        "datasets": {},
    }
    cons_cases = _load_jsonl(DATASETS["consolidated_v9_reviewed_dev"])
    if is_v10:
        assert id_map is not None
        cons_cases = _remap_consolidated_for_v10(cons_cases, release, id_map)
    out["datasets"]["consolidated_v9_reviewed_dev"] = {
        strategy: _run_dev_subset(cons_cases, release, chunks, strategy)
        for strategy in ("exact", "lexical")
    }

    for name in (
        "week3_v9_dev_draft",
        "multichunk_v9_benchmark_dev",
        "week3_v10_channel_dev_draft",
    ):
        cases = _load_jsonl(DATASETS[name])
        if is_v10 and name == "week3_v9_dev_draft":
            assert id_map is not None
            cases = _remap_consolidated_for_v10(cases, release, id_map)
        out["datasets"][name] = {
            strategy: _run_dev_subset(cases, release, chunks, strategy)
            for strategy in ("exact", "lexical")
        }
    return out


def main() -> int:
    _assert_channel_dev_has_no_test_leakage(DATASETS["week3_v10_channel_dev_draft"])

    v9_rel = ConsolidatedRelease.load(V9_RELEASE)
    v9_chunks, v9_chunk_manifest = load_chunks(v9_rel, V9_CHUNKS)
    v9_eval = _eval_release(v9_rel, v9_chunks, v9_chunk_manifest, is_v10=False)

    baseline_path = ROOT / "evals/results/v10_baseline_v9_dev.json"
    baseline_path.write_text(
        json.dumps(
            {"evaluated_at_utc": datetime.now(UTC).isoformat(), **v9_eval},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        cand_sha = digest((V10_CANDIDATE / "release.json").read_bytes())
        review_md = tmp_path / "review.md"
        review_md.write_text(f"pode aprovar a revisao\n{cand_sha}\n", encoding="utf-8")
        v10_dir = tmp_path / "v10-dev-eval"
        v10_chunks_dir = tmp_path / "v10-chunks"
        approve_v10_release.approve(
            cand_sha,
            source=V10_CANDIDATE,
            destination=v10_dir,
            chunks_destination=v10_chunks_dir,
            review_path=review_md,
        )
        v10_rel = ConsolidatedRelease.load(v10_dir)
        v10_chunks, v10_chunk_manifest = load_chunks(v10_rel, v10_chunks_dir)
        id_map = json.loads((V10_CANDIDATE / "id_map_v9_v10.json").read_text(encoding="utf-8"))[
            "mappings"
        ]
        v10_eval = _eval_release(
            v10_rel, v10_chunks, v10_chunk_manifest, is_v10=True, id_map=id_map
        )

    deltas: dict[str, dict[str, dict[str, float | None]]] = {}
    for ds_name in v9_eval["datasets"]:
        deltas[ds_name] = {}
        for strategy in ("exact", "lexical"):
            s9 = v9_eval["datasets"][ds_name][strategy]
            s10 = v10_eval["datasets"][ds_name][strategy]
            deltas[ds_name][strategy] = {
                metric: round(s10[metric] - s9[metric], 4)
                if s9.get(metric) is not None and s10.get(metric) is not None
                else None
                for metric in ("hit_at_1", "hit_at_3", "hit_at_5", "mrr_at_5", "status_accuracy")
            }

    comparison = {
        "evaluated_at_utc": datetime.now(UTC).isoformat(),
        "note": "Avaliação restrita aos splits dev (nenhum split test foi executado).",
        "v9": v9_eval,
        "v10_candidate": v10_eval,
        "deltas_v10_minus_v9": deltas,
    }
    comp_path = ROOT / "evals/results/v10_candidate_dev_comparison.json"
    comp_path.write_text(
        json.dumps(comparison, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "baseline": str(baseline_path.relative_to(ROOT)),
                "comparison": str(comp_path.relative_to(ROOT)),
                "deltas": deltas,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
