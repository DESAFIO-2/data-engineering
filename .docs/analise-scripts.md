# Análise da pasta scripts — 2026-11-10

Análise estática de todos os 78 arquivos Python e 11 arquivos JSON da pasta. Foram examinados código, imports, referências em src/tests/docs/README e dependências entre artefatos. Os scripts de curadoria não foram executados. Limpeza autorizada e aplicada: os 47 candidatos listados abaixo foram excluídos. Foram preservados 31 scripts e os 11 JSONs. Os scripts históricos permaneceram em seus caminhos originais.

## Recomendação

Manter 15 scripts operacionais ou de diagnóstico reutilizável; preservar 16 scripts de curadoria histórica; retirar 47 scripts exploratórios/protótipos da pasta operacional. Os candidatos à retirada não têm dependência identificada no fluxo atual; isso não garante ausência de uso manual externo.

## Manter

Os comandos documentados e importados por testes são necessários. Os utilitários de consolidação, validação, extração e restauração também devem permanecer, embora alguns precisem de ajustes antes de nova execução.

- `__init__.py`
- `build_corpus.py`
- `build_f04_candidates.py`
- `build_golden_set.py`
- `check_provider.py`
- `collect_sources.py`
- `compare_occurrences.py`
- `consolidate_corpus.py`
- `curate_corpus.py`
- `extract_and_validate_f03_f04.py`
- `package_delivery.py`
- `pipeline.py`
- `rag_release.py`
- `restore_corpus_snapshot.py`
- `validate_consolidated_corpus.py`

## Preservar como histórico de curadoria

Não apagar neste momento. Estes scripts geram artefatos intermediários ou registram regras e correções aplicadas ao corpus. Uma futura transferência para uma pasta de histórico exige ajustar seus caminhos e dependências. Alguns sobrescrevem tabelas ou dados; não devem ser executados em lote.

- `apply_all_table_updates.py`
- `build_curated_f03_final.py`
- `build_curated_t3_all.py`
- `build_f03_data.py`
- `build_f04_corrected_corpus.py`
- `build_refined_154.py`
- `clean_final_st.py`
- `curate_f03_154.py`
- `dump_154_blocks.py`
- `extract_all_groups.py`
- `extract_f03_clean_desc.py`
- `extract_final_clean.py`
- `generate_editable_md.py`
- `inspect_t3.py`
- `refine_descs.py`
- `update_markdown_table2.py`

## Scripts excluídos

Inspeções pontuais, impressões de registros ou protótipos sem resultado persistido identificado. Não são importados pela aplicação nem pelos testes identificados. Os arquivos `test_*.py` desta lista são experimentos: o pytest está configurado para coletar a pasta `tests`. A exclusão proposta não inclui os testes dessa pasta.

`build_curated_154.py` está incompleto: apenas lê dados e atribui variáveis. `build_full_table2_updater.py` e `update_table2_with_pdf_data.py` preparam lógica e imprimem mensagens, sem aplicar a atualização proposta pelo nome.

- `analyze_t3_samples.py`
- `audit_154_flags.py`
- `audit_t2_strength_trim.py`
- `build_curated_154.py`
- `build_full_table2_updater.py`
- `check_factor_items.py`
- `check_final_counts.py`
- `check_ing_digits.py`
- `check_one_occ.py`
- `check_processed_st.py`
- `check_review_154.py`
- `check_s2_f03_rows.py`
- `check_s2_f04.py`
- `check_s2_strictly.py`
- `check_s3_sources.py`
- `check_specific_t3_rows.py`
- `check_srn.py`
- `check_t2_f03_range.py`
- `dump_f03_t3.py`
- `extract_f03_all.py`
- `extract_f03_table2.py`
- `find_s2_lines.py`
- `find_t3_nulls.py`
- `inspect_f01_f04_t2.py`
- `inspect_f03_t2.py`
- `inspect_review_154.py`
- `inspect_specific_descs.py`
- `parse_sub_a.py`
- `print_all_curated.py`
- `print_check.py`
- `print_cleaned.py`
- `print_headings.py`
- `print_t2_header.py`
- `print_t3_samples.py`
- `read_card_1_3.py`
- `test_block_splitting.py`
- `test_desc_extraction.py`
- `test_f03_full_extractor.py`
- `test_parse_f03.py`
- `test_t2_blocks.py`
- `test_t2_clean_strength.py`
- `update_table2_with_pdf_data.py`
- `verify_curated_flags.py`
- `verify_f03_t2_mapping.py`
- `verify_lengths.py`
- `verify_tables_final.py`
- `verify_updated_table2.py`

## Arquivos JSON

Preservar os 11 arquivos por enquanto. Em especial, `curated_f03_final.json` e `curated_t3_all.json` participam da consolidação e não são lixo temporário. Os demais são intermediários da revisão: sua exclusão deve acompanhar uma decisão sobre a preservação da cadeia histórica. Recomenda-se futuramente mover os dados de curadoria para `data/curation/`, atualizando todos os consumidores na mesma alteração.

- `all_154_blocks.json`
- `all_groups.json`
- `cleaned_descs.json`
- `cleaned_strengths_final.json`
- `curated_f03_final.json`
- `curated_t3_all.json`
- `f03_extracted_check.json`
- `f03_processed.json`
- `final_extracted.json`
- `review_154_items.json`
- `t3_inspected.json`

## Pendências antes de publicar

- `consolidate_corpus.py` e vários auxiliares usam `docs/ocorrencias-para-edicao.md`. Referências corrigidas para `.docs/ocorrencias-para-edicao.md`; o documento será incluído explicitamente no commit, apesar da regra geral que ignora `.docs`.
- Preservar os scripts históricos e suas entradas antes de remover diagnósticos ainda não publicados; eles ainda não estão protegidos por um commit remoto.
- `extract_and_validate_f03_f04.py` utiliza `fitz` (PyMuPDF), que não consta nas dependências diretas de `pyproject.toml`; regularizar antes de tratá-lo como comando reproduzível.
- Não executar novamente geradores antigos sobre o corpus validado sem conferir entradas e destino.

## Verificação realizada

Os 78 scripts foram analisados sintaticamente. A execução direcionada de `test_corpus.py`, `test_experimental.py`, `test_experimental_live.py` e `test_experimental_chroma.py` terminou com 71 testes aprovados. Resultado anterior à limpeza; a verificação posterior será registrada abaixo.

## Aplicação da limpeza

- 47 scripts excluídos conforme a lista aprovada.
- 15 scripts operacionais, 16 históricos e 11 JSONs preservados.
- Referências ao documento de curadoria corrigidas, sem executar os geradores nem alterar os dados do corpus.
- A dependência opcional PyMuPDF permanece como pendência do extrator auxiliar.

Verificação após a limpeza: 31 scripts analisados sintaticamente; 5 testes de golden set, empacotamento e release aprovados. Os 71 testes do corpus/chat passaram antes da limpeza.
