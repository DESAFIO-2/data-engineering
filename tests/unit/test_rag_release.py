import json
import shutil
from hashlib import sha256
from pathlib import Path
from typing import Any

import pytest

from scripts.rag_release import ROOT, VERSION, build_release


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_release_has_traceable_exact_records() -> None:
    release = build_release(ROOT)
    folder = ROOT / "data/releases" / VERSION
    medicines = read_jsonl(folder / "medicamentos.jsonl")
    evidence = read_jsonl(folder / "evidencias.jsonl")
    rules = read_jsonl(folder / "regras_acesso.jsonl")
    by_id = {row["evidence_id"]: row for row in evidence}

    assert release["status"] == "approved"
    assert release["review"]["reviewer"] == "Jhiovana"
    assert len(medicines) == 6
    assert len(evidence) == 18
    assert len(rules) == 6
    assert len({m["medicine_id"] for m in medicines}) == len(medicines)
    for medicine in medicines:
        assert medicine["stock_status"] == "não consultado"
        assert medicine["review_status"] == "approved"
        for source_id, listing in medicine["lists"].items():
            proof = by_id[listing["evidence_id"]]
            assert proof["source"]["source_id"] == source_id
            assert proof["source"]["page"] >= 1
            assert proof["source"]["sha256"]
    for rule in rules:
        assert by_id[rule["evidence_id"]]["source"]["source_id"] == "F03"
        assert rule["required_documents"] == "não verificados"
        assert rule["review_status"] == "approved"
    for name, info in release["files"].items():
        assert sha256((folder / name).read_bytes()).hexdigest() == info["sha256"]


def test_release_is_stable_and_distinguishes_presentations() -> None:
    first = build_release(ROOT)["files"]
    second = build_release(ROOT)["files"]
    assert first == second
    medicines = read_jsonl(ROOT / "data/releases" / VERSION / "medicamentos.jsonl")
    matches = [m for m in medicines if m["active_ingredient"] == "sinvastatina"]
    assert {m["strength"] for m in matches} == {"20 mg", "40 mg"}
    assert not [
        m
        for m in medicines
        if m["active_ingredient"] == "sinvastatina" and m["strength"] == "10 mg"
    ]


def test_release_rejects_review_for_changed_curation(tmp_path: Path) -> None:
    for relative in (
        "data/manifests/coleta-inicial-pdfs-2026-11-03.json",
        "data/curation/rag_lote_1.json",
        "data/curation/rag_lote_1_review.json",
    ):
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)
    curation_path = tmp_path / "data/curation/rag_lote_1.json"
    curation = json.loads(curation_path.read_text(encoding="utf-8"))
    curation["items"][0]["strength"] = "10 mg"
    curation_path.write_text(json.dumps(curation), encoding="utf-8")
    with pytest.raises(ValueError, match="revisão humana"):
        build_release(tmp_path)
