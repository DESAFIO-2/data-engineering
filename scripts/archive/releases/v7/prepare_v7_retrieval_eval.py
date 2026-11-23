"""Migrate the technical v6 evaluation set to v7 without claiming human review."""

from __future__ import annotations

import json
import sys
from hashlib import sha256
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "src"))
from rag.consolidated import ConsolidatedRelease, jsonl_bytes  # noqa: E402

SOURCE = ROOT / "evals/datasets/consolidated_v6_agent_reviewed.jsonl"
TARGET = ROOT / "evals/datasets/consolidated_v7_agent_reviewed.jsonl"
RELEASE = ROOT / "data/releases/corpus-consolidado-v7-aprovado-2026-11-11"
EXPECTED_FINGERPRINT = "8399f37f6664f474c18622d912ad9795f04ec199102724cfafbe6e295eeab20b"
CORRECTIONS = {
    "C-F04-023": {
        "relevant_ids": ["evidence-48e616ae9f8df7c435126c21"],
        "migration_note": (
            "Pergunta pede ação prolongada; a referência v6 apontava para a linha "
            "de metformina 500 mg sem essa característica."
        ),
    }
}


def prepare() -> list[dict]:
    release = ConsolidatedRelease.load(RELEASE)
    if release.fingerprint != EXPECTED_FINGERPRINT:
        raise ValueError("Fingerprint v7 inesperado")
    cases = [json.loads(line) for line in SOURCE.read_text(encoding="utf-8").splitlines() if line]
    if len(cases) != 119 or len({case["id"] for case in cases}) != len(cases):
        raise ValueError("Conjunto de origem incompleto ou com IDs duplicados")
    evidence = {item["evidence_id"]: item for item in release.evidence}
    catalog = {item["medicine_id"]: item for item in release.catalog}
    migrated = []
    for case in cases:
        row = dict(case)
        row.update(CORRECTIONS.get(case["id"], {}))
        row["review_status"] = "agent_reviewed"
        row["reviewer"] = "agent_technical_audit"
        row["release_fingerprint"] = release.fingerprint
        if row["expected_status"] == "matched" and not row["relevant_ids"]:
            raise ValueError(f"Caso positivo sem evidência: {row['id']}")
        if row["expected_status"] != "matched" and row["relevant_ids"]:
            raise ValueError(f"Caso não positivo com evidência: {row['id']}")
        references = []
        for eid in row["relevant_ids"]:
            ev = evidence.get(eid)
            if ev is None or (
                row.get("source_id") and ev["source"]["source_id"] != row["source_id"]
            ):
                raise ValueError(f"Referência ausente ou fonte divergente: {row['id']} {eid}")
            med = catalog.get(ev["medicine_id"])
            references.append(
                {
                    "evidence_id": eid,
                    "medicine_id": ev["medicine_id"],
                    "active_ingredient": ev["active_ingredient"],
                    "strength": ev["strength"],
                    "form": ev["form"],
                    "release_characteristic": ev.get("release_characteristic"),
                    "exact_presentation_supported": med["exact_presentation_supported"]
                    if med
                    else None,
                    "source_id": ev["source"]["source_id"],
                    "source_version": ev["source"]["version"],
                    "page": ev["source"]["page"],
                    "source_row_number": ev.get("source_row_number"),
                }
            )
        row["expected_references"] = references
        migrated.append(row)
    families = {
        split: {c["family_id"] for c in migrated if c["split"] == split}
        for split in ("dev", "test")
    }
    if families["dev"] & families["test"]:
        raise ValueError("Famílias vazaram entre dev e test")
    return migrated


def main() -> None:
    cases = prepare()
    raw = jsonl_bytes(cases)
    TARGET.write_bytes(raw)
    print(f"{len(cases)} casos v7; SHA-256 {sha256(raw).hexdigest()}; revisão humana pendente")


if __name__ == "__main__":
    main()
