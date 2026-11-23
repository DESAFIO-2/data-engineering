"""End-to-end and invariant tests for the v10 normalized candidate release."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from langchain_core.embeddings import DeterministicFakeEmbedding

from rag.catalog_chat import candidates, options_reply, stock_candidates
from rag.config import ROOT
from rag.consolidated import (
    CHUNK_RECIPE_V3,
    ConsolidatedRelease,
    build_index,
    chunk_for,
    load_chunks,
    matches_clinical_guardrail,
    open_index,
    search,
)
from rag.consolidated_live import compatible_product
from rag.normalization import fold, identity_key
from scripts.archive.releases.v10 import approve_v10_release
from scripts.archive.releases.v10 import publish_v10_normalized_candidate as pub_v10
from scripts.ingest.publish_consolidated_release import digest, encoded, lines, read_lines, verify

VOCAB_DIR = ROOT / "data/vocab"
V9_DIR = ROOT / "data/releases/corpus-consolidado-v9-aprovado-2026-11-12"
V10_CANDIDATE = ROOT / "data/releases/corpus-consolidado-v10-normalizada-2026-11-17"


def _make_fixture_v9(base: Path) -> Path:
    """Create a small approved v9-shaped release covering all v10 edge cases."""
    src_dir = base / "v9-fixture"
    src_dir.mkdir(parents=True)

    f01_src = {
        "source_id": "F01",
        "version": "RENAME 2024, 2ª edição",
        "page": 28,
        "url": "https://example.org/f01.pdf",
        "sha256": "a" * 64,
    }
    f03_src = {
        "source_id": "F03",
        "version": "REME-DF 2026-10-29",
        "page": 19,
        "url": "https://example.org/f03.pdf",
        "sha256": "b" * 64,
    }
    f04_src = {
        "source_id": "F04",
        "version": "Farmácia Popular 2026-08-31",
        "page": 1,
        "url": "https://example.org/f04.pdf",
        "sha256": "c" * 64,
    }

    raw_rows = [
        # 1-2: spacing collision (omeprazol 20 mg vs 20mg)
        (
            "occ-ome-f01",
            "med-ome-f01",
            f01_src,
            1,
            "omeprazol",
            "20 mg",
            "cápsula",
            None,
            "Básico",
            "A02BC01",
            None,
            None,
            "medicine",
            "omeprazol | 20 mg | cápsula | Básico | A02BC01",
            {},
        ),
        (
            "occ-ome-f03",
            "med-ome-f03",
            f03_src,
            772,
            "omeprazol",
            "20mg",
            "cápsula",
            None,
            None,
            None,
            "UBS (farmácia ambulatorial)",
            "1234",
            "medicine",
            "772. 1234 omeprazol cápsula 20mg UBS (farmácia ambulatorial)",
            {},
        ),
        # 3-4: salt-order + accent collision (amiodarona)
        (
            "occ-ami-f01",
            "med-ami-f01",
            f01_src,
            2,
            "cloridrato de amiodarona",
            "200 mg",
            "comprimido",
            None,
            None,
            "C01BD01",
            None,
            None,
            "medicine",
            "cloridrato de amiodarona | 200 mg | comprimido | Básico | C01BD01",
            {},
        ),
        (
            "occ-ami-f03",
            "med-ami-f03",
            f03_src,
            70,
            "amiodarona (cloridrato)",
            "200 mg",
            "comprimido",
            None,
            None,
            None,
            "Uso hospitalar e atendimento pré- hospitalar (SAMU)",
            "4321",
            "medicine",
            "70. 4321 amiodarona (cloridrato) comprimido 200 mg SAMU",
            {},
        ),
        # 5: F01 PDF artifact 0/ ,3 mg/mL
        (
            "occ-rin-f01",
            "med-rin-f01",
            f01_src,
            3,
            "solução ringer + lactato",
            "lactato de sódio 3 mg/mL + cloreto de potássio 0/ ,3 mg/mL",
            "solução injetável",
            None,
            "Básico",
            "B05BB01",
            None,
            None,
            "medicine",
            "solução ringer + lactato | lactato de sódio 3 mg/mL + cloreto de potássio "
            "0/ ,3 mg/mL | solução injetável | Básico | B05BB01",
            {},
        ),
        # 6: package_only in F03
        (
            "occ-pol-f03",
            "med-pol-f03",
            f03_src,
            825,
            "polidocanol",
            "1%",
            "ampola",
            None,
            None,
            None,
            "Uso hospitalar",
            "6091",
            "medicine",
            "825. 6091 polidocanol 1% ampola 2 mL Uso hospitalar",
            {},
        ),
        # 7-8: volume packages with strength "-"
        (
            "occ-agu-5",
            "med-agu-5",
            f01_src,
            4,
            "água para injetáveis",
            "-",
            "solução injetável 5 mL",
            None,
            "Básico",
            "V07AB",
            None,
            None,
            "medicine",
            "água para injetáveis | - | solução injetável 5 mL | Básico | V07AB",
            {},
        ),
        (
            "occ-agu-10",
            "med-agu-10",
            f01_src,
            5,
            "água para injetáveis",
            "-",
            "solução injetável 10 mL",
            None,
            "Básico",
            "V07AB",
            None,
            None,
            "medicine",
            "água para injetáveis | - | solução injetável 10 mL | Básico | V07AB",
            {},
        ),
        # 9: descriptor form
        (
            "occ-hom-f01",
            "med-hom-f01",
            f01_src,
            6,
            "medicamentos homeopáticos",
            "Conforme Farmacopeia Homeopática Brasileira vigente",
            "Conforme Farmacopeia Homeopática Brasileira vigente",
            None,
            "Básico",
            "NC",
            None,
            None,
            "medicine",
            "medicamentos homeopáticos | Conforme Farmacopeia Homeopática Brasileira vigente | "
            "Conforme Farmacopeia Homeopática Brasileira vigente | Básico | NC",
            {},
        ),
        # 10: (dose diária) + release
        (
            "occ-gar-f01",
            "med-gar-f01",
            f01_src,
            7,
            "garra-do-diabo (Harpagophytum procumbens DC. ex Meissn.)",
            "30 a 100 mg de harpagosídeo (dose diária)",
            "comprimido de liberação retardada",
            "liberação retardada",
            "Básico",
            "M01AW5009(2)",
            None,
            None,
            "medicine",
            "garra-do-diabo | 30 a 100 mg (dose diária) | comprimido de liberação retardada | "
            "Básico | M01AW5009(2)",
            {},
        ),
        # 11-12: F04 metformin regular vs prolonged (absent form)
        (
            "occ-met-reg",
            "med-met-reg",
            f04_src,
            8,
            "cloridrato de metformina",
            "500mg",
            "-",
            None,
            None,
            None,
            None,
            None,
            "medicine",
            "cloridrato de metformina 500mg",
            {"indication": "DIABETES"},
        ),
        (
            "occ-met-pro",
            "med-met-pro",
            f04_src,
            9,
            "cloridrato de metformina",
            "500mg",
            "-",
            "ação prolongada",
            None,
            None,
            None,
            None,
            "medicine",
            "cloridrato de metformina 500mg - ação prolongada",
            {"indication": "DIABETES"},
        ),
        # 13-14: identical F03 description, distinct channels
        (
            "occ-cab-181",
            "med-cab",
            f03_src,
            181,
            "cabergolina",
            "0,5 mg",
            "comprimido",
            None,
            None,
            None,
            "Uso hospitalar",
            "607",
            "medicine",
            "181. 607 cabergolina comprimido 0,5mg Uso hospitalar",
            {},
        ),
        (
            "occ-cab-182",
            "med-cab",
            f03_src,
            182,
            "cabergolina",
            "0,5 mg",
            "comprimido",
            None,
            None,
            None,
            "Farmácia do Componente Especializado",
            "MS607",
            "medicine",
            "182. MS607 cabergolina comprimido 0,5mg CEAF",
            {},
        ),
        # 15: F01 supply
        (
            "occ-alc-sup",
            None,
            f01_src,
            10,
            "álcool etílico (FN)",
            "70%",
            "solução",
            None,
            "Insumos (Básico)",
            "D08AX08",
            None,
            None,
            "supply",
            "álcool etílico (FN) | 70% | solução | Insumos (Básico) | D08AX08",
            {},
        ),
        # 16: unit 'u' normalization compatibility (100u -> 100 U)
        (
            "occ-tox-f03",
            "med-tox-f03",
            f03_src,
            1035,
            "toxina botulínica tipo A",
            "100u",
            "pó liofilizado para solução injetável",
            None,
            None,
            None,
            "Uso hospitalar",
            "9999",
            "medicine",
            "1035. 9999 toxina botulínica tipo A 100u Uso hospitalar",
            {},
        ),
    ]

    occurrences: list[dict[str, Any]] = []
    descriptions: dict[str, Any] = {}
    by_med: dict[str, list[dict[str, Any]]] = {}
    audit_log: list[dict[str, Any]] = []
    for idx, (
        oid,
        mid,
        src,
        row_num,
        ing,
        strg,
        form,
        rel,
        comp,
        atc,
        chan,
        sc,
        itype,
        raw,
        ctx,
    ) in enumerate(raw_rows, 1):
        occ: dict[str, Any] = {
            "occurrence_id": oid,
            "medicine_id": mid,
            "item_type": itype,
            "source": src,
            "source_row_number": row_num,
            "line_start": row_num if src["source_id"] == "F04" else None,
            "line_end": row_num if src["source_id"] == "F04" else None,
            "active_ingredient": ing,
            "strength": strg,
            "form": form,
            "release_characteristic": rel,
            "component": comp,
            "atc": atc,
            "channel": chan,
            "source_code": sc,
            "context": {"page_chunk_ids": [], **ctx},
            "raw_text": raw,
            "review_status": "approved",
            "uncertainties": [],
        }
        if itype == "supply":
            occ["supply_id"] = "supply-alc"
            occ["supply_name"] = ing
        occurrences.append(occ)
        if mid is not None:
            by_med.setdefault(mid, []).append(occ)
        if src["source_id"] == "F03":
            descriptions[oid] = {
                "column": "DESCRIÇÃO",
                "description": f"{ing} {form} {strg}",
                "page": src["page"],
                "pdf_sha256": src["sha256"],
                "source_row_number": row_num,
                "x0": 100,
                "x1": 200,
            }
        audit_log.append(
            {
                "audit_id": f"AUDIT-{idx:04d}",
                "occurrence_id": oid,
                "source_id": src["source_id"],
                "verification_result": "verified",
                "fields_verified": {"active_ingredient": ing, "strength": strg, "form": form},
            }
        )

    catalog = [
        {
            "medicine_id": mid,
            "active_ingredient": group[0]["active_ingredient"],
            "strength": group[0]["strength"],
            "form": group[0]["form"],
            "release_characteristic": group[0]["release_characteristic"],
            "occurrence_ids": [o["occurrence_id"] for o in group],
            "source_ids": sorted({o["source"]["source_id"] for o in group}),
            "exact_presentation_supported": group[0]["form"] != "-",
            "review_status": "approved",
        }
        for mid, group in by_med.items()
    ]

    from scripts.ingest.publish_consolidated_release import evidence_for

    evidence: list[dict[str, Any]] = [evidence_for(occ, descriptions) for occ in occurrences]
    for ev in evidence:
        ev["review_status"] = "approved"

    files = {
        "catalog.jsonl": lines(catalog),
        "occurrences.jsonl": lines(occurrences),
        "evidencias.jsonl": lines(evidence),
        "exclusions.jsonl": b"",
        "audit_log.jsonl": lines(audit_log),
        "f03_descriptions.json": encoded(descriptions),
        "quality_report.json": encoded({"limitations": ["fixture"]}),
    }
    ev_sha = digest(files["evidencias.jsonl"])
    files["domain_review.json"] = encoded(
        {
            "decision": "approved",
            "date": "2026-11-12",
            "reviewer": "Jhiovana",
            "reviewer_role": "responsável pelo projeto",
            "scope": "fixture",
            "release_version": "fixture-v9",
            "evidence_sha256": ev_sha,
        }
    )
    manifest = {
        "schema_version": "consolidated-release-v2",
        "release_version": "fixture-v9",
        "status": "approved",
        "approval_scope": "fixture",
        "f03_description_extract_sha256": digest(files["f03_descriptions.json"]),
        "files": {
            name: {
                "sha256": digest(data),
                "bytes": len(data),
                **({"records": len(read_lines(data))} if name.endswith(".jsonl") else {}),
            }
            for name, data in files.items()
        },
    }
    for name, data in files.items():
        (src_dir / name).write_bytes(data)
    (src_dir / "release.json").write_bytes(encoded(manifest))
    verify(src_dir)
    return src_dir


def test_end_to_end_publish_approve_chunk_index_and_runtime(tmp_path: Path) -> None:
    v9_fixture = _make_fixture_v9(tmp_path)
    cand_dir = tmp_path / "v10-candidate"
    cand_manifest = pub_v10.write_candidate(
        source=v9_fixture,
        vocab_dir=VOCAB_DIR,
        destination=cand_dir,
        expected_source_sha256=None,
    )
    assert cand_manifest["status"] == "pending_review"
    assert cand_manifest["files"]["catalog.jsonl"]["records"] == 12  # 14 -> 12 (2 merges)

    # Determinism check
    p1, m1 = pub_v10.build(
        source=v9_fixture,
        vocab_dir=VOCAB_DIR,
        version=cand_dir.name,
        expected_source_sha256=None,
        generated_at_utc="2026-11-17T00:00:00+00:00",
    )
    p2, m2 = pub_v10.build(
        source=v9_fixture,
        vocab_dir=VOCAB_DIR,
        version=cand_dir.name,
        expected_source_sha256=None,
        generated_at_utc="2026-11-17T00:00:00+00:00",
    )
    assert p1 == p2 and m1["corpus_fingerprint"] == m2["corpus_fingerprint"]

    cand_sha = digest((cand_dir / "release.json").read_bytes())
    review_md = tmp_path / "review.md"
    review_md.write_text(f"pode aprovar a revisao\nhash: {cand_sha}\n", encoding="utf-8")

    approved_dir = tmp_path / "v10-approved"
    chunks_dir = tmp_path / "chunks"
    approve_v10_release.approve(
        cand_sha,
        source=cand_dir,
        destination=approved_dir,
        chunks_destination=chunks_dir,
        review_path=review_md,
    )
    release = ConsolidatedRelease.load(approved_dir)
    chunks, chunk_manifest = load_chunks(release, chunks_dir)
    assert chunk_manifest["recipe"] == CHUNK_RECIPE_V3
    assert len({c["text"] for c in chunks}) == len(chunks) == 16

    # F01 component fix & 0,3 mg/mL fix verified
    ami_f01 = next(o for o in release.occurrences if o["occurrence_id"] == "occ-ami-f01")
    assert ami_f01["component"] == "Básico"
    rin_f01 = next(o for o in release.occurrences if o["occurrence_id"] == "occ-rin-f01")
    assert "0,3 mg/mL" in rin_f01["strength"] and "0/ ,3" not in rin_f01["strength"]

    # Build vector index with fake embeddings & check channel_codes metadata
    store_dir = tmp_path / "vector"
    embeddings = DeterministicFakeEmbedding(size=32)
    location = build_index(release, chunks, chunk_manifest, store_dir, "fake-model", embeddings)
    store = open_index(release, chunks, chunk_manifest, store_dir, "fake-model", embeddings)
    meta_by_id = dict(zip(store.get()["ids"], store.get()["metadatas"], strict=True))
    assert meta_by_id["chunk-cab-182"]["channel_codes"] == "CEAF"
    assert (location / "index.json").exists()

    # Runtime searches across normalized catalog & v3 chunks
    assert search("omeprazol 20mg capsula", release, chunks)["status"] == "matched"
    assert set(search("omeprazol 20mg capsula", release, chunks)["medicine"]["source_ids"]) == {
        "F01",
        "F03",
    }
    assert (
        search("amiodarona (cloridrato) 200 mg comprimido", release, chunks)["status"] == "matched"
    )
    assert (
        search(
            "toxina botulínica tipo A 100u pó liofilizado para solução injetável REME-DF",
            release,
            chunks,
        )["status"]
        == "matched"
    )

    # Package-only item (ampola)
    assert search("polidocanol 1% ampola REME-DF", release, chunks)["status"] == "matched"
    assert search("polidocanol 1% comprimido REME-DF", release, chunks)["status"] == "not_in_scope"
    assert search("polidocanol 1% REME-DF", release, chunks)["status"] == "ambiguous"

    # Volume package items with strength "-"
    res_vol = search("água para injetáveis solução injetável 10 mL RENAME", release, chunks)
    assert res_vol["status"] == "matched" and res_vol["medicine"]["package"] == "10 mL"
    assert (
        search("água para injetáveis solução injetável RENAME", release, chunks)["status"]
        == "ambiguous"
    )

    # Descriptor form & (dose diária) guardrail bypass
    assert (
        search(
            "Na RENAME, há registro de medicamentos homeopáticos conforme a Farmacopeia "
            "Homeopática Brasileira vigente?",
            release,
            chunks,
        )["status"]
        == "matched"
    )
    q_garra = (
        "Na RENAME, há registro de garra-do-diabo (Harpagophytum procumbens DC. ex Meissn.) "
        "30 a 100 mg de harpagosídeo (dose diária) comprimido de liberação retardada?"
    )
    assert matches_clinical_guardrail(q_garra, release) is False
    assert search(q_garra, release, chunks)["status"] == "matched"

    # Metformin regular vs prolonged kept separate
    assert (
        search("cloridrato de metformina 500 mg Farmácia Popular", release, chunks)["status"]
        == "ambiguous"
    )
    assert (
        search("cloridrato de metformina 500 mg ação prolongada Farmácia Popular", release, chunks)[
            "status"
        ]
        == "matched"
    )

    # Channel ranking distinguishes cabergolina rows in lexical search
    cab = search(
        "Onde retiro cabergolina 0,5 mg comprimido na REME-DF Componente Especializado?",
        release,
        chunks,
        strategy="lexical",
    )
    assert cab["status"] == "matched"
    assert cab["evidence"][0]["occurrence_id"] == "occ-cab-182"

    # Catalog chat & stock compatibility
    opts = candidates("polidocanol 1%", release)
    assert "ampola" in options_reply(opts, release)
    assert len(stock_candidates(candidates("metformina", release))) == 2
    pol_med = next(m for m in release.catalog if m["active_ingredient"] == "polidocanol")
    assert compatible_product(pol_med, "6091", "POLIDOCANOL 1% AMPOLA 2 ML", release)
    met_med = next(
        m for m in release.catalog if m["active_ingredient"] == "cloridrato de metformina"
    )
    assert not compatible_product(met_med, "90224", "METFORMINA 500 MG", release)


@pytest.mark.dvc
def test_v10_normalized_candidate_invariants_and_determinism() -> None:
    if not V10_CANDIDATE.exists():
        pytest.skip("Candidato v10 normalizado não gerado")
    prior = verify(V9_DIR)
    cand = verify(V10_CANDIDATE)
    assert prior["status"] == "approved"
    assert cand["status"] == "pending_review"
    assert cand["files"]["occurrences.jsonl"]["records"] == 2114
    assert cand["files"]["evidencias.jsonl"]["records"] == 2114

    v9_occ = {
        o["occurrence_id"]: o for o in read_lines((V9_DIR / "occurrences.jsonl").read_bytes())
    }
    v10_occ = {
        o["occurrence_id"]: o
        for o in read_lines((V10_CANDIDATE / "occurrences.jsonl").read_bytes())
    }
    v10_aud = {
        a["occurrence_id"]: a
        for a in read_lines((V10_CANDIDATE / "audit_log.jsonl").read_bytes())
        if a.get("occurrence_id")
    }
    parser_fixed = {
        oid for oid, a in v10_aud.items() if a.get("verification_result") == "corrected_v10_parser"
    }
    assert len(parser_fixed) == 54

    literal_fields = (
        "raw_text",
        "active_ingredient",
        "strength",
        "form",
        "channel",
        "source_code",
        "atc",
        "release_characteristic",
        "component",
    )
    for oid, o10 in v10_occ.items():
        o9 = v9_occ[oid]
        for field in literal_fields:
            if oid in parser_fixed and field in ("component", "strength"):
                continue
            assert o10.get(field) == o9.get(field), (oid, field)
        if o10["source"]["source_id"] == "F01":
            assert o10.get("component") is not None
        if o10["source"]["source_id"] == "F03":
            assert o10["normalized"]["channel_codes"]
        assert "atc_invalid" not in o10["normalized"]["review_flags"]

    catalog = read_lines((V10_CANDIDATE / "catalog.jsonl").read_bytes())
    keys = {
        identity_key(v10_occ[m["occurrence_ids"][0]]["normalized"], m["source_ids"])
        for m in catalog
    }
    assert len(keys) == len(catalog)

    folded_ing = {fold(o["normalized"]["active_ingredient"]) for o in v10_occ.values()}
    exact_ing = {o["normalized"]["active_ingredient"] for o in v10_occ.values()}
    assert len(folded_ing) == len(exact_ing)

    evidence = read_lines((V10_CANDIDATE / "evidencias.jsonl").read_bytes())
    v3_chunks = [chunk_for(ev, cand["release_version"], recipe=CHUNK_RECIPE_V3) for ev in evidence]
    assert len({c["text"] for c in v3_chunks}) == len(v3_chunks) == 2114

    ts = cand["generated_at_utc"]
    p1, m1 = pub_v10.build(generated_at_utc=ts)
    assert m1["corpus_fingerprint"] == cand["corpus_fingerprint"]
    for name, data in p1.items():
        assert data == (V10_CANDIDATE / name).read_bytes()


def test_v10_search_alternatives_units_release_rate_supplies_and_aliases() -> None:
    from rag.consolidated import ConsolidatedRelease, search
    from rag.consolidated_evaluation import _trace_candidates

    source_f01 = {
        "source_id": "F01",
        "version": "2024",
        "page": 10,
        "url": "https://example.org/f01",
    }
    source_f03 = {
        "source_id": "F03",
        "version": "2026",
        "page": 20,
        "url": "https://example.org/f03",
    }
    catalog = [
        {
            "medicine_id": "med-amox",
            "active_ingredient": "amoxicilina",
            "aliases": ["amoxicilina"],
            "strength": "500 mg",
            "form": "cápsula ou comprimido",
            "form_alternatives": ["cápsula", "comprimido"],
            "package": None,
            "specification": None,
            "release_characteristic": None,
            "source_ids": ["F03"],
        },
        {
            "medicine_id": "med-poli",
            "active_ingredient": "polidocanol",
            "aliases": ["polidocanol"],
            "strength": "1%",
            "form": "-",
            "package": "ampola",
            "specification": None,
            "release_characteristic": None,
            "source_ids": ["F03"],
        },
        {
            "medicine_id": "med-alfa",
            "active_ingredient": "alfavelaglicerase",
            "aliases": ["alfavelaglicerase"],
            "strength": "400 U",
            "form": "pó liofilizado ou solução injetável",
            "form_alternatives": ["pó liofilizado", "solução injetável"],
            "package": None,
            "specification": None,
            "release_characteristic": None,
            "source_ids": ["F03"],
        },
        {
            "medicine_id": "med-riva",
            "active_ingredient": "rivastigmina",
            "aliases": ["rivastigmina"],
            "strength": "9 mg (liberação de 4,6 mg/24h)",
            "form": "adesivo transdérmico",
            "package": None,
            "specification": None,
            "release_characteristic": "liberação de 4,6 mg/24h",
            "source_ids": ["F03"],
        },
        {
            "medicine_id": "med-met",
            "active_ingredient": "cloridrato de metformina",
            "aliases": ["cloridrato de metformina", "metformina (cloridrato)"],
            "strength": "850 mg",
            "form": "comprimido",
            "package": None,
            "specification": None,
            "release_characteristic": None,
            "source_ids": ["F01", "F03"],
        },
    ]
    occurrences = [
        {
            "occurrence_id": "occ-sup-5",
            "item_type": "supply",
            "active_ingredient": "água para injetáveis",
            "strength": "-",
            "form": "solução injetável 5 mL",
            "package": "5 mL",
            "source": source_f01,
        },
        {
            "occurrence_id": "occ-sup-10",
            "item_type": "supply",
            "active_ingredient": "água para injetáveis",
            "strength": "-",
            "form": "solução injetável 10 mL",
            "package": "10 mL",
            "source": source_f01,
        },
    ]
    evidence: list[dict[str, Any]] = [
        {
            "evidence_id": "ev-amox",
            "occurrence_id": "occ-amox",
            "medicine_id": "med-amox",
            "active_ingredient": "amoxicilina",
            "strength": "500 mg",
            "form": "cápsula ou comprimido",
            "release_characteristic": None,
            "source": source_f03,
        },
        {
            "evidence_id": "ev-poli",
            "occurrence_id": "occ-poli",
            "medicine_id": "med-poli",
            "active_ingredient": "polidocanol",
            "strength": "1%",
            "form": "-",
            "release_characteristic": None,
            "source": source_f03,
        },
        {
            "evidence_id": "ev-alfa",
            "occurrence_id": "occ-alfa",
            "medicine_id": "med-alfa",
            "active_ingredient": "alfavelaglicerase",
            "strength": "400 U",
            "form": "pó liofilizado ou solução injetável",
            "release_characteristic": None,
            "source": source_f03,
        },
        {
            "evidence_id": "ev-riva",
            "occurrence_id": "occ-riva",
            "medicine_id": "med-riva",
            "active_ingredient": "rivastigmina",
            "strength": "9 mg (liberação de 4,6 mg/24h)",
            "form": "adesivo transdérmico",
            "release_characteristic": "liberação de 4,6 mg/24h",
            "source": source_f03,
        },
        {
            "evidence_id": "ev-sup-5",
            "occurrence_id": "occ-sup-5",
            "active_ingredient": "água para injetáveis",
            "strength": "-",
            "form": "solução injetável 5 mL",
            "release_characteristic": None,
            "source": source_f01,
        },
        {
            "evidence_id": "ev-sup-10",
            "occurrence_id": "occ-sup-10",
            "active_ingredient": "água para injetáveis",
            "strength": "-",
            "form": "solução injetável 10 mL",
            "release_characteristic": None,
            "source": source_f01,
        },
    ]
    release = ConsolidatedRelease(
        folder=Path("."),
        manifest={"release_version": "corpus-consolidado-v10-aprovado-2026-11-17"},
        catalog=catalog,
        occurrences=occurrences,
        evidence=evidence,
        fingerprint="test-fp",
    )

    chunks = [
        {
            "chunk_id": f"chunk-{i}",
            "medicine_id": ev["medicine_id"],
            "evidence_id": ev["evidence_id"],
            "text": f"{ev['active_ingredient']} {ev['strength']} {ev['form']}",
            "source": ev["source"],
        }
        for i, ev in enumerate(evidence)
        if "medicine_id" in ev
    ]

    assert search("amoxicilina 500 mg comprimido REME-DF", release, chunks)["status"] == "matched"
    assert search("amoxicilina 500 mg cápsula REME-DF", release, chunks)["status"] == "matched"
    assert search("polidocanol 2% REME-DF", release, chunks)["status"] == "not_in_scope"
    assert search("alfavelaglicerase 200 U REME-DF", release, chunks)["status"] == "not_in_scope"
    assert (
        search("rivastigmina 9 mg adesivo transdérmico REME-DF", release, chunks)["status"]
        == "matched"
    )
    sup_res = search("água para injetáveis solução injetável 10 mL RENAME", release, chunks)
    assert sup_res["status"] == "matched"
    assert sup_res["evidence"][0]["evidence_id"] == "ev-sup-10"
    assert _trace_candidates("metformina (cloridrato) 850 mg comprimido", release) == ["med-met"]
