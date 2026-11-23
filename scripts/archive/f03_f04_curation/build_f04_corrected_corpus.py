"""Build the F04 working corpus from the hash-verified historical snapshot.

Only source-literal, field-level corrections are applied. The historical snapshot
and its restoration proof remain immutable. Running again must reproduce bytes.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "data/corpus/experimental"
DEST = ROOT / "data/corpus/f04"
SOURCE_PDF = ROOT / "data/raw/F04-farmacia-popular/farmacia-popular-elenco-2026-08-31.pdf"
EXPECTED_PDF_SHA256 = "beb2cf59b835e94e2e016b009bd2b17f5d0375ab593db00f983211c2cfbc32b3"

CORRECTIONS = {
    "occ-bd645fca4e10b51f38485f06": {
        "literal": "etinilestradiol 0,03mg + levonorgestrel 0,15mg",
        "before": {"active_ingredient": "etinilestradiol", "strength": None},
        "after": {
            "active_ingredient": "etinilestradiol + levonorgestrel",
            "strength": "0,03mg + 0,15mg",
        },
        "validated_by": "usuário: confirmou perda de componente e decidiu manter combinação",
    },
    "occ-2e237469ad52f38dc54b786e": {
        "literal": "valerato de estradiol 5mg + enantato de noretisterona 50mg",
        "before": {"active_ingredient": "valerato de estradiol", "strength": None},
        "after": {
            "active_ingredient": "valerato de estradiol + enantato de noretisterona",
            "strength": "5mg + 50mg",
        },
        "validated_by": "usuário: confirmou regra das combinações na seção 5",
    },
    "occ-31f830e7fbb52c0353da2946": {
        "literal": "carbidopa 25mg + levodopa 250mg",
        "before": {"active_ingredient": "carbidopa", "strength": None},
        "after": {"active_ingredient": "carbidopa + levodopa", "strength": "25mg + 250mg"},
        "validated_by": "usuário: confirmou regra das combinações na seção 5",
    },
    "occ-e7d83368e51a7cb974fd6bd9": {
        "literal": "cloridrato de benserazida 25mg + levodopa 100mg",
        "before": {"active_ingredient": "cloridrato de benserazida", "strength": None},
        "after": {
            "active_ingredient": "cloridrato de benserazida + levodopa",
            "strength": "25mg + 100mg",
        },
        "validated_by": "usuário: confirmou regra das combinações na seção 5",
    },
    "occ-48e616ae9f8df7c435126c21": {
        "literal": "cloridrato de metformina 500mg - ação prolongada",
        "before": {"release_characteristic": None},
        "after": {"release_characteristic": "ação prolongada"},
        "validated_by": "recomendação técnica aceita pelo usuário; literal conferido no PDF",
    },
}


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def json_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def jsonl_bytes(rows: list[dict]) -> bytes:
    return ("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n").encode("utf-8")


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def main() -> None:
    source_manifest = json.loads((SOURCE / "manifest.json").read_text(encoding="utf-8"))
    for name, info in source_manifest["files"].items():
        assert sha256((SOURCE / name).read_bytes()) == info["sha256"], name
    assert sha256(SOURCE_PDF.read_bytes()) == EXPECTED_PDF_SHA256
    assert not DEST.exists(), f"Destino já existe: {DEST}; não sobrescrever snapshot"

    occurrences = [
        row
        for row in read_jsonl(SOURCE / "occurrences.jsonl")
        if row["source"]["source_id"] == "F04"
    ]
    chunks = [
        row for row in read_jsonl(SOURCE / "chunks.jsonl") if row["source"]["source_id"] == "F04"
    ]
    assert len(occurrences) == 41 and len(chunks) == 42
    assert all(row["source"]["sha256"] == EXPECTED_PDF_SHA256 for row in occurrences + chunks)
    chunk_by_id = {row["evidence_id"]: row for row in chunks}
    review_log = []
    seen = set()
    for row in occurrences:
        oid = row["occurrence_id"]
        if oid not in CORRECTIONS:
            continue
        spec = CORRECTIONS[oid]
        assert row["source"]["page"] == 1
        assert spec["literal"] in row["raw_text"]
        assert any(spec["literal"] in chunk_by_id[cid]["text"] for cid in row["chunk_ids"])
        for field, prior in spec["before"].items():
            assert row.get(field) == prior, (oid, field)
        row.update(spec["after"])
        row["uncertainties"] = [
            u
            for u in row["uncertainties"]
            if u
            not in {
                "strength_unresolved" if "strength" in spec["after"] else "__none__",
            }
        ]
        # Other fields and list membership remain pending. A field check is not
        # approval of the occurrence or the document.
        row["review_status"] = "pending"
        review_log.append(
            {
                "occurrence_id": oid,
                "source_id": "F04",
                "version": row["source"]["version"],
                "page": 1,
                "source_sha256": EXPECTED_PDF_SHA256,
                "source_literal": spec["literal"],
                "fields_validated": list(spec["after"]),
                "before": spec["before"],
                "after": spec["after"],
                "validation": spec["validated_by"],
                "record_status": "pending",
                "reason": (
                    "Somente os campos corrigidos foram validados; contexto, forma, via "
                    "e demais critérios não foram encerrados."
                ),
            }
        )
        seen.add(oid)
    assert seen == set(CORRECTIONS)
    assert all(set(row["chunk_ids"]) <= set(chunk_by_id) for row in occurrences)
    assert len({row["occurrence_id"] for row in occurrences}) == 41
    assert len(chunk_by_id) == 42

    report = {
        "schema_version": "f04-field-corrections-v1",
        "status": "experimental",
        "review_status": "pending",
        "human_verified": False,
        "source_id": "F04",
        "source_version": occurrences[0]["source"]["version"],
        "source_sha256": EXPECTED_PDF_SHA256,
        "occurrences": 41,
        "primary_chunks": 42,
        "catalog_presentations": 0,
        "field_corrections_validated": 5,
        "limitations": [
            "Os cinco conjuntos de campos corrigidos têm evidência literal na página 1 "
            "e validação humana da decisão; não há aprovação integral dos registros.",
            "F04 não declara forma para essas linhas; não foi criada apresentação "
            "de catálogo nem inferida via.",
            "O índice vetorial histórico usa outro fingerprint; este corpus não possui "
            "índice persistente próprio.",
        ],
    }
    payload = {
        "occurrences.jsonl": jsonl_bytes(occurrences),
        "chunks.jsonl": jsonl_bytes(chunks),
        "catalog.jsonl": b"",
        "review-log.jsonl": jsonl_bytes(review_log),
        "report.json": json_bytes(report),
    }
    manifest = {
        "schema_version": "f04-field-corrections-v1",
        "status": "experimental",
        "review_status": "pending",
        "parser_version": source_manifest["parser_version"],
        "derived_from": {
            "path": SOURCE.relative_to(ROOT).as_posix(),
            "manifest_sha256": sha256((SOURCE / "manifest.json").read_bytes()),
            "source_pdf": SOURCE_PDF.relative_to(ROOT).as_posix(),
            "source_pdf_sha256": EXPECTED_PDF_SHA256,
        },
        "files": {
            name: {
                "bytes": len(raw),
                "sha256": sha256(raw),
                **(
                    {
                        "records": len(review_log)
                        if name == "review-log.jsonl"
                        else 41
                        if name == "occurrences.jsonl"
                        else 42
                        if name == "chunks.jsonl"
                        else 0
                    }
                    if name.endswith(".jsonl")
                    else {}
                ),
            }
            for name, raw in payload.items()
        },
    }
    DEST.mkdir(parents=True)
    for name, raw in payload.items():
        (DEST / name).write_bytes(raw)
    (DEST / "manifest.json").write_bytes(json_bytes(manifest))
    print(DEST)


if __name__ == "__main__":
    main()
