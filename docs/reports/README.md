# Relatórios, auditorias e revisões (`docs/reports/`)

**Objetivo:** catalogar todos os relatórios técnicos, auditorias de corpus, validações de recuperação e planilhas de revisão humana do projeto **SUS Cidadão**, organizados por fase e versão de release.

> **Nota de organização:** os arquivos desta pasta são mantidos em seus caminhos planos originais porque são referenciados diretamente por código (`src/rag/consolidated_cli.py`), testes (`tests/unit/`), scripts de publicação/promoção (`scripts/`) e manifestos de releases congelados.

## 1. Release v10 (Candidato) — Reconciliação de catálogo e chunks v2

| Arquivo | Papel |
|---|---|
| [revisao-reconciliacao-v10-template.md](v10/revisao-reconciliacao-v10-template.md) | Folha de revisão técnica da reconciliação dos 80 pares de colisão no candidato `v10` |

## 2. Semana 3 — Comparação LLM × RAG (v9)

| Arquivo | Papel |
|---|---|
| [semana3-llm-rag-v9.md](v9/semana3-llm-rag-v9.md) | Relatório principal da Semana 3 (protocolo dos 8 cenários, desenvolvimento, teste, RAGAS e pendências) |
| [semana3-v9-test-review-template.md](v9/semana3-v9-test-review-template.md) | Conferência técnica nas fontes oficiais para o conjunto de teste da Semana 3 |

## 2. Release v9 — Claritromicina, recuperação e gates independentes

| Arquivo | Papel |
|---|---|
| [auditoria-claritromicina-v9.md](v9/auditoria-claritromicina-v9.md) | Auditoria técnica da normalização de claritromicina na v9 |
| [revisao-claritromicina-v9-jhiovana.md](v9/revisao-claritromicina-v9-jhiovana.md) | Aprovação humana da revisão de claritromicina para publicação da v9 |
| [validacao-recuperacao-v9-dev.md](v9/validacao-recuperacao-v9-dev.md) | Validação de recuperação no conjunto de desenvolvimento v9 |
| [v9-independent-test-review.md](v9/v9-independent-test-review.md) | Revisão técnica inicial do candidato de teste independente v9 |
| [v9-independent-test-review-v2.md](v9/v9-independent-test-review-v2.md) | Revisão v2 do candidato de teste independente v9 |
| [v9-test-candidate-v2-audit.md](v9/v9-test-candidate-v2-audit.md) | Auditoria do candidato v2 de teste independente v9 |
| [validacao-recuperacao-v9-test.md](v9/validacao-recuperacao-v9-test.md) | Resultado da validação de recuperação no teste v9 |
| [dupla-revisao-teste-v9-2026-11-12.md](v9/dupla-revisao-teste-v9-2026-11-12.md) | Registro da dupla revisão do conjunto de teste v9 |
| [v9-next-round-preparation.md](v9/v9-next-round-preparation.md) | Preparação da rodada adicional (`next`) de teste independente v9 |
| [diagnostico-colisoes-v9-para-v10.md](v9/diagnostico-colisoes-v9-para-v10.md) | Inventário determinístico dos 20 pares de chunks duplicados (`v1`) e 80 colisões de catálogo na `v9` para a `v10` |
| [v9-next-independent-test-review.md](v9/v9-next-independent-test-review.md) | Revisão técnica dos 28 casos da rodada `next` na v9 |
| [validacao-recuperacao-v9-next-test.md](v9/validacao-recuperacao-v9-next-test.md) | Resultado da validação de recuperação no holdout `next` da v9 |
| [plano-pos-gate-v9-lexical.md](v9/plano-pos-gate-v9-lexical.md) | Plano de avaliação pós-gate lexical na v9 |
| [plano-handoff-mac-recuperacao-v9.md](v9/plano-handoff-mac-recuperacao-v9.md) | Plano de handoff para execução e recuperação v9 |

## 3. Release v8 — Correção de cálcio e item F03-194

| Arquivo | Papel |
|---|---|
| [correcao-f03-194-v8.md](v8/correcao-f03-194-v8.md) | Documentação da correção do item F03-194 (cálcio) na v8 |
| [v8-calcium-correction-review.xlsx](v8/v8-calcium-correction-review.xlsx) | Planilha de revisão da correção de cálcio na v8 |
| [validacao-recuperacao-v8-test.md](v8/validacao-recuperacao-v8-test.md) | Validação de recuperação no conjunto de teste congelado v8 |

## 4. Release v7 — Códigos de origem e gate de recuperação

| Arquivo | Papel |
|---|---|
| [parecer-tecnico-v7-codigos.md](v7/parecer-tecnico-v7-codigos.md) | Parecer técnico sobre códigos de origem na v7 |
| [v7-source-alignment-findings.json](v7/v7-source-alignment-findings.json) | Achados estruturados de alinhamento com as fontes na v7 |
| [v7-retrieval-review.xlsx](v7/v7-retrieval-review.xlsx) | Planilha de revisão do gate de recuperação v7 |
| [validacao-recuperacao-v7-dev.md](v7/validacao-recuperacao-v7-dev.md) | Validação de recuperação em desenvolvimento na v7 |

## 5. Release v6 — Auditoria inicial e alinhamento com fontes

| Arquivo | Papel |
|---|---|
| [relatorio-auditoria-corpus-v6.md](v6/relatorio-auditoria-corpus-v6.md) | Relatório de auditoria integral do corpus v6 |
| [revisao-v6-jhiovana.md](v6/revisao-v6-jhiovana.md) | Decisão e restrições registradas na revisão humana v6 |
| [baseline-recuperacao-v6-dev.md](v6/baseline-recuperacao-v6-dev.md) | Baseline exploratório de recuperação em desenvolvimento na v6 |
| [v6-source-alignment-findings.json](v6/v6-source-alignment-findings.json) | Achados de alinhamento com fontes na v6 |
| [v6-source-alignment-review.csv](v6/v6-source-alignment-review.csv) | Planilha de revisão de alinhamento com fontes na v6 |
