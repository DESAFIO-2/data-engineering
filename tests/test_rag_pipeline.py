from sus_cidadao_data.rag.pipeline import (
    Chunk,
    SourceConfig,
    build_sparse_index,
    chunk_page,
    search_index,
)


def source() -> SourceConfig:
    return {
        "source_id": "TESTE",
        "document_id": "documento-teste",
        "title": "Documento de teste",
        "version": "v1",
        "document_date": "2026-11-03",
        "territory": "Distrito Federal",
        "content_type": "medicamentos",
        "path": "fixture.pdf",
        "enabled": True,
    }


def make_chunk(chunk_id: str, text: str, page: int) -> Chunk:
    return Chunk(
        chunk_id=chunk_id,
        text=text,
        source_id="TESTE",
        document_id="documento-teste",
        title="Documento de teste",
        version="v1",
        document_date="2026-11-03",
        territory="Distrito Federal",
        content_type="medicamentos",
        page=page,
        chunk_index_on_page=0,
    )


def test_chunk_page_preserva_proveniencia_e_overlap() -> None:
    chunks = chunk_page(
        "um dois três quatro cinco seis sete",
        source=source(),
        page=12,
        chunk_size_words=4,
        overlap_words=1,
    )

    assert [chunk.text for chunk in chunks] == ["um dois três quatro", "quatro cinco seis sete"]
    assert all(chunk.page == 12 for chunk in chunks)
    assert all(chunk.source_id == "TESTE" for chunk in chunks)
    assert len({chunk.chunk_id for chunk in chunks}) == 2


def test_search_index_prioriza_apresentacao_exata() -> None:
    chunks = [
        make_chunk("metformina", "cloridrato de metformina 500 mg comprimido", 10),
        make_chunk("losartana", "losartana potássica 50 mg comprimido", 11),
        make_chunk("orientacao", "documento oficial com foto e receita válida", 12),
    ]
    index = build_sparse_index(chunks)

    results = search_index("metformina 500 mg", chunks=chunks, index=index, top_k=2)

    assert results[0].chunk.chunk_id == "metformina"
    assert results[0].chunk.page == 10
    assert results[0].score > results[1].score


def test_search_index_retorna_vazio_para_termos_ausentes() -> None:
    chunks = [make_chunk("metformina", "cloridrato de metformina 500 mg", 10)]
    index = build_sparse_index(chunks)

    assert search_index("colonoscopia", chunks=chunks, index=index) == []
