"""Build a frozen, leak-free multi-chunk ranking benchmark (candidate_chunk_count >= 3)."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from rag.config import ROOT
from rag.consolidated import (
    ConsolidatedRelease,
    ingredient_key,
    load_chunks,
    normalize,
    search,
)

RELEASE_DIR = ROOT / "data/releases/corpus-consolidado-v9-aprovado-2026-11-12"
CHUNKS_DIR = ROOT / "data/derived/chunks/corpus-consolidado-v9-aprovado-2026-11-12"
OUTPUT_PATH = ROOT / "evals/datasets/multichunk_v9_benchmark.jsonl"

# Split strictly disjoint by ingredient_key family_id; target_eid matches a unique chunk text.
_SPEC_CASES: tuple[dict[str, str], ...] = (
    # =========================
    # SPLIT: dev (32 cases)
    # =========================
    # Family: rifampicina (10)
    {
        "id": "MC-DEV-001",
        "split": "dev",
        "clue_kind": "literal_clue",
        "target_eid": "evidence-28dc7d29b48e7780af06e21a",
        "question": "Qual evidência traz rifampicina 300 mg cápsula para tratamento de meningite?",
    },
    {
        "id": "MC-DEV-002",
        "split": "dev",
        "clue_kind": "literal_clue",
        "target_eid": "evidence-0d92ea0f129481f22bb0a685",
        "question": (
            "Sobre rifampicina 300 mg cápsula, qual registro especifica hidradenite supurativa?"
        ),
    },
    {
        "id": "MC-DEV-003",
        "split": "dev",
        "clue_kind": "literal_clue",
        "target_eid": "evidence-eee75379958237d90fe20727",
        "question": (
            "Rifampicina 300 mg cápsula possui indicação documental específica para brucelose?"
        ),
    },
    {
        "id": "MC-DEV-004",
        "split": "dev",
        "clue_kind": "semantic_paraphrase",
        "target_eid": "evidence-c7154e4af18fb8d6c27fdcf6",
        "question": (
            "Para rifampicina 300 mg cápsula, qual registro trata da infecção pulmonar "
            "causada pelo bacilo de Koch (Mycobacterium tuberculosis)?"
        ),
    },
    {
        "id": "MC-DEV-005",
        "split": "dev",
        "clue_kind": "semantic_paraphrase",
        "target_eid": "evidence-f99082f162f9f965ff1bfd36",
        "question": (
            "Para rifampicina 300 mg cápsula, qual evidência refere-se à doença de Hansen "
            "(mal de Hansen / Mycobacterium leprae)?"
        ),
    },
    {
        "id": "MC-DEV-006",
        "split": "dev",
        "clue_kind": "semantic_paraphrase",
        "target_eid": "evidence-0449e40e8c3c9732aa285dc5",
        "question": (
            "Sem se limitar a protocolo estadual, rifampicina 300 mg cápsula consta na "
            "edição nacional de 2024 da lista federal?"
        ),
    },
    {
        "id": "MC-DEV-007",
        "split": "dev",
        "clue_kind": "literal_clue",
        "target_eid": "evidence-02eb2acb08601980ec20b690",
        "question": "Qual evidência da rifampicina 20 mg/mL suspensão oral menciona meningite?",
    },
    {
        "id": "MC-DEV-008",
        "split": "dev",
        "clue_kind": "literal_clue",
        "target_eid": "evidence-77db46b327309899f8d4fc03",
        "question": (
            "Na lista para rifampicina 20 mg/mL suspensão oral com frasco doseador, "
            "qual registro atende brucelose?"
        ),
    },
    {
        "id": "MC-DEV-009",
        "split": "dev",
        "clue_kind": "semantic_paraphrase",
        "target_eid": "evidence-1cff076e8dd38a0f35a78551",
        "question": (
            "Em rifampicina 20 mg/mL suspensão oral, qual item atende pacientes com infecção "
            "micobacteriana pulmonar pelo bacilo de Koch?"
        ),
    },
    {
        "id": "MC-DEV-010",
        "split": "dev",
        "clue_kind": "semantic_paraphrase",
        "target_eid": "evidence-7a7fa583aa05c16ff0d3668a",
        "question": (
            "Em rifampicina 20 mg/mL suspensão oral, qual registro se destina à doença de Hansen?"
        ),
    },
    # Family: artemeter + lumefantrina (4)
    {
        "id": "MC-DEV-011",
        "split": "dev",
        "clue_kind": "literal_clue",
        "target_eid": "evidence-71d350be0b754264c8f0187e",
        "question": (
            "Qual apresentação de arteméter + lumefantrina 20 mg + 120 mg comprimido "
            "corresponde ao blister com 24 comprimidos para 35 kg?"
        ),
    },
    {
        "id": "MC-DEV-012",
        "split": "dev",
        "clue_kind": "literal_clue",
        "target_eid": "evidence-db9de3d69d4730d206d81759",
        "question": (
            "Para arteméter + lumefantrina 20 mg + 120 mg comprimido, qual item refere-se "
            "ao blister com 6 comprimidos faixa 5 a 14 kg?"
        ),
    },
    {
        "id": "MC-DEV-013",
        "split": "dev",
        "clue_kind": "literal_clue",
        "target_eid": "evidence-e231f9b8de316bf9e0ee0151",
        "question": (
            "Qual item de arteméter + lumefantrina 20 mg + 120 mg comprimido traz "
            "embalagem com 12 comprimidos para 15 a 24 kg?"
        ),
    },
    {
        "id": "MC-DEV-014",
        "split": "dev",
        "clue_kind": "literal_clue",
        "target_eid": "evidence-e8ffc3f2974ccbb2d133edec",
        "question": (
            "Qual registro de arteméter + lumefantrina 20 mg + 120 mg comprimido traz "
            "blister com 18 comprimidos na faixa de 25 a 34 kg?"
        ),
    },
    # Family: insulina humana (5)
    {
        "id": "MC-DEV-015",
        "split": "dev",
        "clue_kind": "literal_clue",
        "target_eid": "evidence-05a54563c977e0cf567fea49",
        "question": (
            "Para insulina humana NPH 100 UI/mL suspensão injetável, qual registro descreve "
            "sistemas de aplicação preenchidos 3 mL?"
        ),
    },
    {
        "id": "MC-DEV-016",
        "split": "dev",
        "clue_kind": "semantic_paraphrase",
        "target_eid": "evidence-2584a3c186447c4851f93a2d",
        "question": (
            "Sobre insulina humana NPH 100 UI/mL suspensão injetável, qual item descreve "
            "refil cilíndrico de 3 mL (carpule)?"
        ),
    },
    {
        "id": "MC-DEV-017",
        "split": "dev",
        "clue_kind": "literal_clue",
        "target_eid": "evidence-3d3cb95b8795261e44f6f559",
        "question": (
            "Sobre insulina humana regular 100 UI/mL solução injetável, qual evidência "
            "especifica frasco-ampola 10 mL?"
        ),
    },
    {
        "id": "MC-DEV-018",
        "split": "dev",
        "clue_kind": "semantic_paraphrase",
        "target_eid": "evidence-c77bb855ea383ba51ace09c6",
        "question": (
            "Em insulina humana regular 100 UI/mL solução injetável, qual opção trata de "
            "caneta injetora descartável pronta de 3 mL?"
        ),
    },
    {
        "id": "MC-DEV-019",
        "split": "dev",
        "clue_kind": "literal_clue",
        "target_eid": "evidence-c63167a2a2dd82242a046e55",
        "question": (
            "Qual evidência de insulina humana regular 100 UI/mL solução injetável aponta "
            "carpule 3 mL?"
        ),
    },
    # Family: insulina analoga de acao ultra rapida (2)
    {
        "id": "MC-DEV-020",
        "split": "dev",
        "clue_kind": "literal_clue",
        "target_eid": "evidence-ca22e55603990f4bee996cc3",
        "question": (
            "Qual evidência de insulina análoga de ação ultra rápida 100 UI/mL solução "
            "injetável corresponde a frasco-ampola 10mL?"
        ),
    },
    {
        "id": "MC-DEV-021",
        "split": "dev",
        "clue_kind": "semantic_paraphrase",
        "target_eid": "evidence-4c3a17c7c2814e1dba8326fd",
        "question": (
            "Qual registro de insulina análoga de ação ultra rápida 100 UI/mL solução "
            "injetável menciona contingência pelos códigos 90714 e MS90714 na faixa pediátrica?"
        ),
    },
    # Family: azitromicina (3)
    {
        "id": "MC-DEV-022",
        "split": "dev",
        "clue_kind": "literal_clue",
        "target_eid": "evidence-955e4a459cf33e6aec98b8a2",
        "question": "Qual evidência de azitromicina 500 mg comprimido especifica cólera?",
    },
    {
        "id": "MC-DEV-023",
        "split": "dev",
        "clue_kind": "literal_clue",
        "target_eid": "evidence-6113a50af3b318668752c855",
        "question": "Qual registro de azitromicina 500 mg comprimido trata de tracoma?",
    },
    {
        "id": "MC-DEV-024",
        "split": "dev",
        "clue_kind": "semantic_paraphrase",
        "target_eid": "evidence-6113a50af3b318668752c855",
        "question": (
            "Para azitromicina 500 mg comprimido, qual item atende a infecção ocular crônica "
            "por Chlamydia trachomatis (tracoma)?"
        ),
    },
    # Family: cabergolina (2)
    {
        "id": "MC-DEV-025",
        "split": "dev",
        "clue_kind": "semantic_paraphrase",
        "target_eid": "evidence-12cd0bf4e7f46f63a7e91d39",
        "question": (
            "Qual registro de cabergolina 0,5 mg comprimido destina-se ao bloqueio da "
            "produção de leite materno em puérperas vivendo com HIV?"
        ),
    },
    {
        "id": "MC-DEV-026",
        "split": "dev",
        "clue_kind": "semantic_paraphrase",
        "target_eid": "evidence-5ad7f9f8930840d37b73de24",
        "question": (
            "Qual registro de cabergolina 0,5 mg comprimido pertence exclusivamente à relação "
            "nacional de referência (2ª edição de 2024) sem detalhe estadual?"
        ),
    },
    # Family: acido tranexamico (2)
    {
        "id": "MC-DEV-027",
        "split": "dev",
        "clue_kind": "literal_clue",
        "target_eid": "evidence-0698192840d18b42a21aeee3",
        "question": "Qual item de ácido tranexâmico 250 mg comprimido menciona coagulopatias?",
    },
    {
        "id": "MC-DEV-028",
        "split": "dev",
        "clue_kind": "semantic_paraphrase",
        "target_eid": "evidence-0698192840d18b42a21aeee3",
        "question": (
            "Sobre ácido tranexâmico 250 mg comprimido, qual evidência refere-se a "
            "distúrbios hemorrágicos e alterações da coagulação?"
        ),
    },
    # Family: glicose (3)
    {
        "id": "MC-DEV-029",
        "split": "dev",
        "clue_kind": "literal_clue",
        "target_eid": "evidence-6bed32aa206b1466e3afffca",
        "question": (
            "Qual item de glicose 5 % solução injetável isenta de pvc corresponde ao "
            "volume de 500 mL?"
        ),
    },
    {
        "id": "MC-DEV-030",
        "split": "dev",
        "clue_kind": "literal_clue",
        "target_eid": "evidence-a935df57894d5aef495ab918",
        "question": (
            "Para glicose 5 % solução injetável isenta de pvc, qual registro traz o volume "
            "de 250 mL?"
        ),
    },
    {
        "id": "MC-DEV-031",
        "split": "dev",
        "clue_kind": "literal_clue",
        "target_eid": "evidence-37d792910c0e3216a7af7324",
        "question": (
            "Em glicose 5 % solução injetável, qual opção especifica recipiente de 100 mL?"
        ),
    },
    # Family: filgrastim (1)
    {
        "id": "MC-DEV-032",
        "split": "dev",
        "clue_kind": "semantic_paraphrase",
        "target_eid": "evidence-f06b36f50512a6f4a8712169",
        "question": (
            "Qual evidência de filgrastim 300 mcg solução injetável refere-se apenas à "
            "edição federal de 2024?"
        ),
    },
    # =========================
    # SPLIT: test (32 cases)
    # =========================
    # Family: claritromicina (4)
    {
        "id": "MC-TEST-001",
        "split": "test",
        "clue_kind": "literal_clue",
        "target_eid": "evidence-25d6511151adc3be1b20ddf5",
        "question": "Qual evidência de claritromicina 500 mg comprimido especifica coqueluche?",
    },
    {
        "id": "MC-TEST-002",
        "split": "test",
        "clue_kind": "semantic_paraphrase",
        "target_eid": "evidence-25d6511151adc3be1b20ddf5",
        "question": (
            "Para claritromicina 500 mg comprimido, qual item atende a infecção respiratória "
            "por Bordetella pertussis (tosse comprida)?"
        ),
    },
    {
        "id": "MC-TEST-003",
        "split": "test",
        "clue_kind": "semantic_paraphrase",
        "target_eid": "evidence-440a7b86140f721129cdd834",
        "question": (
            "Para claritromicina 500 mg comprimido, qual registro destina-se à doença de Hansen?"
        ),
    },
    {
        "id": "MC-TEST-004",
        "split": "test",
        "clue_kind": "literal_clue",
        "target_eid": "evidence-83202f34ce2ffbeed05ea49d",
        "question": (
            "Qual evidência de claritromicina 500 mg comprimido especifica uso exclusivo "
            "SITE-TB para tuberculose?"
        ),
    },
    # Family: doxiciclina (4)
    {
        "id": "MC-TEST-005",
        "split": "test",
        "clue_kind": "literal_clue",
        "target_eid": "evidence-b1ddcad9115b41f721c89673",
        "question": "Qual evidência de doxiciclina 100 mg comprimido trata febre maculosa?",
    },
    {
        "id": "MC-TEST-006",
        "split": "test",
        "clue_kind": "semantic_paraphrase",
        "target_eid": "evidence-ba2eb0e9aef7345b3d741099",
        "question": (
            "Para doxiciclina 100 mg comprimido, qual registro atende infecções sexualmente "
            "transmissíveis (IST)?"
        ),
    },
    {
        "id": "MC-TEST-007",
        "split": "test",
        "clue_kind": "literal_clue",
        "target_eid": "evidence-ed2150fce4489ab622bc2c22",
        "question": "Em doxiciclina 100 mg comprimido, qual registro especifica brucelose?",
    },
    {
        "id": "MC-TEST-008",
        "split": "test",
        "clue_kind": "semantic_paraphrase",
        "target_eid": "evidence-b1ddcad9115b41f721c89673",
        "question": (
            "Para doxiciclina 100 mg comprimido, qual evidência refere-se à rickettsiose "
            "transmitida por carrapato-estrela?"
        ),
    },
    # Family: artesunato + mefloquina (4)
    {
        "id": "MC-TEST-009",
        "split": "test",
        "clue_kind": "literal_clue",
        "target_eid": "evidence-280bf43242a7ff435a167d8e",
        "question": (
            "Para artesunato + mefloquina 100 mg + 220 mg comprimido, qual evidência "
            "traz blister c/ 6 comp?"
        ),
    },
    {
        "id": "MC-TEST-010",
        "split": "test",
        "clue_kind": "literal_clue",
        "target_eid": "evidence-b7b50a1946ab2c60d6233953",
        "question": (
            "Para artesunato + mefloquina 100 mg + 220 mg comprimido, qual evidência "
            "traz blister c/ 3 comp?"
        ),
    },
    {
        "id": "MC-TEST-011",
        "split": "test",
        "clue_kind": "literal_clue",
        "target_eid": "evidence-e5f9e3b1abb5ee648cb6c03f",
        "question": (
            "Em artesunato + mefloquina 25 mg + 50 mg comprimido, qual registro indica "
            "blister c/ 6 comp?"
        ),
    },
    {
        "id": "MC-TEST-012",
        "split": "test",
        "clue_kind": "literal_clue",
        "target_eid": "evidence-5f797b2b5a1212625b4ebd74",
        "question": (
            "Em artesunato + mefloquina 25 mg + 50 mg comprimido, qual registro indica "
            "blister c/ 3 comp?"
        ),
    },
    # Family: clofazimina (3)
    {
        "id": "MC-TEST-013",
        "split": "test",
        "clue_kind": "literal_clue",
        "target_eid": "evidence-65905b97ae9369654337b8d4",
        "question": (
            "Qual evidência de clofazimina 100 mg cápsula destina-se à tuberculose no SITE-TB?"
        ),
    },
    {
        "id": "MC-TEST-014",
        "split": "test",
        "clue_kind": "semantic_paraphrase",
        "target_eid": "evidence-b73ed9c7b585a36f158c04fd",
        "question": ("Para clofazimina 100 mg cápsula, qual item destina-se à doença de Hansen?"),
    },
    {
        "id": "MC-TEST-015",
        "split": "test",
        "clue_kind": "semantic_paraphrase",
        "target_eid": "evidence-156a268279dc2ce94c2162da",
        "question": (
            "Qual registro de clofazimina 100 mg cápsula vem da lista nacional de 2024 "
            "sem detalhamento clínico estadual?"
        ),
    },
    # Family: levofloxacino (3)
    {
        "id": "MC-TEST-016",
        "split": "test",
        "clue_kind": "literal_clue",
        "target_eid": "evidence-5a933f8902f3c57f3b890055",
        "question": (
            "Qual evidência de levofloxacino 250 mg comprimido especifica exclusivo SITE-TB "
            "para tuberculose?"
        ),
    },
    {
        "id": "MC-TEST-017",
        "split": "test",
        "clue_kind": "semantic_paraphrase",
        "target_eid": "evidence-c9ca7e93dc9f2bf5ea0d467a",
        "question": (
            "Em levofloxacino 500 mg comprimido, qual registro tem restrição exclusiva ao "
            "sistema especial de tratamento de tuberculose resistente (SITE-TB)?"
        ),
    },
    {
        "id": "MC-TEST-018",
        "split": "test",
        "clue_kind": "semantic_paraphrase",
        "target_eid": "evidence-a75d3d6c7a44dd8886c9bdf1",
        "question": (
            "Sobre levofloxacino 500 mg comprimido, qual evidência pertence apenas à edição "
            "federal de 2024 (lista nacional)?"
        ),
    },
    # Family: itraconazol (2)
    {
        "id": "MC-TEST-019",
        "split": "test",
        "clue_kind": "literal_clue",
        "target_eid": "evidence-f3d808e2a1efa2be4fd1fa20",
        "question": (
            "Qual evidência de itraconazol 100 mg cápsula indica infecções fúngicas sistêmicas?"
        ),
    },
    {
        "id": "MC-TEST-020",
        "split": "test",
        "clue_kind": "semantic_paraphrase",
        "target_eid": "evidence-f3d808e2a1efa2be4fd1fa20",
        "question": (
            "Para itraconazol 100 mg cápsula, qual registro refere-se ao tratamento de "
            "micoses invasivas profundas no organismo?"
        ),
    },
    # Family: pirimetamina (2)
    {
        "id": "MC-TEST-021",
        "split": "test",
        "clue_kind": "literal_clue",
        "target_eid": "evidence-955a7a7cf1fe17e1d32f9997",
        "question": "Qual evidência de pirimetamina 25 mg comprimido especifica toxoplasmose?",
    },
    {
        "id": "MC-TEST-022",
        "split": "test",
        "clue_kind": "semantic_paraphrase",
        "target_eid": "evidence-955a7a7cf1fe17e1d32f9997",
        "question": (
            "Para pirimetamina 25 mg comprimido, qual item atende a infecção pelo protozoário "
            "Toxoplasma gondii?"
        ),
    },
    # Family: prednisona (3)
    {
        "id": "MC-TEST-023",
        "split": "test",
        "clue_kind": "literal_clue",
        "target_eid": "evidence-e893d0e250961336c65ac1c1",
        "question": "Qual evidência de prednisona 5 mg comprimido especifica hanseníase?",
    },
    {
        "id": "MC-TEST-024",
        "split": "test",
        "clue_kind": "semantic_paraphrase",
        "target_eid": "evidence-b2cdc3c9f27addd88b28b70e",
        "question": (
            "Sobre prednisona 20 mg comprimido, qual registro destina-se à doença de Hansen?"
        ),
    },
    {
        "id": "MC-TEST-025",
        "split": "test",
        "clue_kind": "semantic_paraphrase",
        "target_eid": "evidence-ed12d50fd62b10ea5ab408a2",
        "question": (
            "Em prednisona 20 mg comprimido, qual evidência refere-se somente à edição de 2024 "
            "da lista nacional federal?"
        ),
    },
    # Family: benzilpenicilina benzatina (2)
    {
        "id": "MC-TEST-026",
        "split": "test",
        "clue_kind": "literal_clue",
        "target_eid": "evidence-c98c48ebbfca299896b73060",
        "question": (
            "Qual evidência de benzilpenicilina benzatina 1.200.000 UI pó para suspensão "
            "injetável menciona sífilis?"
        ),
    },
    {
        "id": "MC-TEST-027",
        "split": "test",
        "clue_kind": "semantic_paraphrase",
        "target_eid": "evidence-c98c48ebbfca299896b73060",
        "question": (
            "Para benzilpenicilina benzatina 1.200.000 UI pó para suspensão injetável, "
            "qual registro atende a infecção por Treponema pallidum?"
        ),
    },
    # Family: benzilpenicilina potassica (2)
    {
        "id": "MC-TEST-028",
        "split": "test",
        "clue_kind": "semantic_paraphrase",
        "target_eid": "evidence-95feb1e7151d48eeb52c3cb6",
        "question": (
            "Para benzilpenicilina potássica 5.000.000 UI pó para solução injetável, qual "
            "registro trata de neurosífilis ou infecção por Treponema pallidum?"
        ),
    },
    {
        "id": "MC-TEST-029",
        "split": "test",
        "clue_kind": "semantic_paraphrase",
        "target_eid": "evidence-ca5c60a9adc06e6b6668746c",
        "question": (
            "Sobre benzilpenicilina potássica 5.000.000 UI pó para solução injetável, qual "
            "registro vem apenas da relação nacional edição 2024?"
        ),
    },
    # Family: enoxaparina sodica (1)
    {
        "id": "MC-TEST-030",
        "split": "test",
        "clue_kind": "semantic_paraphrase",
        "target_eid": "evidence-17490c8d51d5aaa3d5fc1862",
        "question": (
            "Qual evidência de enoxaparina sódica 60 mg solução injetável tem restrição "
            "exclusiva para especialidade cardiológica?"
        ),
    },
    # Family: cloreto de sodio (2)
    {
        "id": "MC-TEST-031",
        "split": "test",
        "clue_kind": "literal_clue",
        "target_eid": "evidence-f1b4eb8fe12540acfe347187",
        "question": (
            "Em cloreto de sódio 0,9 % solução injetável isenta de pvc, qual evidência "
            "descreve volume de 500 mL?"
        ),
    },
    {
        "id": "MC-TEST-032",
        "split": "test",
        "clue_kind": "literal_clue",
        "target_eid": "evidence-8f3831e5daa294c501110d14",
        "question": (
            "Em cloreto de sódio 0,9 % solução injetável de infusão, qual registro "
            "refere-se ao volume de 1000 mL?"
        ),
    },
)


def build_benchmark(
    release_dir: Path = RELEASE_DIR,
    chunks_dir: Path = CHUNKS_DIR,
    output_path: Path = OUTPUT_PATH,
) -> list[dict[str, Any]]:
    """Build and verify the multi-chunk ranking benchmark JSONL."""
    release = ConsolidatedRelease.load(release_dir)
    chunks, _ = load_chunks(release, chunks_dir)
    ev_by_id = {ev["evidence_id"]: ev for ev in release.evidence}
    chunk_by_eid = {ch["evidence_id"]: ch for ch in chunks}
    text_counts = Counter(ch["text"] for ch in chunks)

    records: list[dict[str, Any]] = []
    dev_families: set[str] = set()
    test_families: set[str] = set()

    for spec in _SPEC_CASES:
        eid = spec["target_eid"]
        ev = ev_by_id[eid]
        if text_counts[chunk_by_eid[eid]["text"]] != 1:
            raise ValueError(f"Alvo com texto de chunk duplicado na v1: {spec['id']} ({eid})")
        result = search(spec["question"], release, chunks, strategy="lexical", top_k=5)
        if result["status"] != "matched":
            raise ValueError(f"Caso {spec['id']} não retornou matched: {result}")
        cand_count = int(result["candidate_chunk_count"])
        if cand_count < 3:
            raise ValueError(f"Caso {spec['id']} tem apenas {cand_count} chunks candidatos (< 3)")
        family_id = ingredient_key(ev["active_ingredient"])
        if spec["split"] == "dev":
            dev_families.add(family_id)
        else:
            test_families.add(family_id)
        records.append(
            {
                "id": spec["id"],
                "split": spec["split"],
                "family_id": family_id,
                "clue_kind": spec["clue_kind"],
                "source_id": ev["source"]["source_id"],
                "presentation": (
                    f"{ev['active_ingredient']} | {ev['strength']} | {normalize(ev['form'])}"
                ),
                "question": spec["question"],
                "expected_status": "matched",
                "relevant_ids": [eid],
                "candidate_chunk_count_verified": cand_count,
                "release_fingerprint": release.fingerprint,
                "synthetic": True,
            }
        )

    overlap = dev_families & test_families
    if overlap:
        raise ValueError(f"Sobreposição de famílias entre dev e test: {sorted(overlap)}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in records)
    output_path.write_text(payload, encoding="utf-8", newline="\n")
    return records


def main() -> None:
    records = build_benchmark()
    by_split = Counter(r["split"] for r in records)
    by_kind = Counter(r["clue_kind"] for r in records)
    min_chunks = min(r["candidate_chunk_count_verified"] for r in records)
    print(
        json.dumps(
            {
                "total": len(records),
                "by_split": dict(by_split),
                "by_clue_kind": dict(by_kind),
                "min_candidate_chunk_count": min_chunks,
                "output": str(OUTPUT_PATH.relative_to(ROOT)),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
