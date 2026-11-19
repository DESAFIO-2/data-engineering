# Avaliações RAG v10 — 2026-11-19

Release: `corpus-consolidado-v10-aprovado-2026-11-17`.

Fingerprint: `7e93955247de1ded77121a00bf1b14c320d782cf21c4d9e9464d4e8f3e24d179`.
Índice ChromaDB: 2.114/2.114 chunks, `models/gemini-embedding-2` (3.072 dimensões).

## Recuperação consolidada, split test

Dataset: `evals/datasets/consolidated_v10_reviewed.jsonl` (28 casos com revisão registrada).

| Estratégia | Hit@1 | Hit@5 | Acurácia de status | Acurácia de apresentação | Confusões críticas |
| --- | ---: | ---: | ---: | ---: | ---: |
| Exact | 1,00 | 1,00 | 1,00 | 1,00 | 0 |
| Lexical | 1,00 | 1,00 | 1,00 | 1,00 | 0 |
| Vector | 1,00 | 1,00 | 1,00 | 1,00 | 0 |
| Hybrid | 1,00 | 1,00 | 1,00 | 1,00 | 0 |

Resultados novos: `evals/results/v10_aprovado_consolidated_test_vector.json` e `evals/results/v10_aprovado_consolidated_test_hybrid.json`. Os resultados `exact` e `lexical` já estavam versionados.

## Benchmark multi-chunk, split test

Dataset: `evals/datasets/multichunk_v10_benchmark.jsonl` (32 casos por estratégia).

| Estratégia | Hit@1 | Hit@3 | Hit@5 | Confusões críticas |
| --- | ---: | ---: | ---: | ---: |
| Exact | 4/32 | 0,9062 | 1,00 | 0 |
| Lexical | 25/32 | 1,00 | 1,00 | 0 |
| Vector | 27/32 | 1,00 | 1,00 | 0 |
| Hybrid | 30/32 | 1,00 | 1,00 | 0 |

Relatório: `evals/results/v10_aprovado_multichunk_test.json`. A comparação pareada no próprio relatório inclui intervalos de confiança e McNemar; a amostra é pequena, então diferenças pontuais não devem ser tratadas como conclusão geral para outras perguntas.

## Respostas do chat, split dev exploratório

O dataset `week3_v9_test_reviewed.jsonl` tem fingerprint v9 e não pode ser usado como teste fechado v10. Foi criada uma amostra de 12 casos **dev** do dataset consolidado v10 em `evals/datasets/week3_v10_response_dev_exploratory.jsonl` (9 positivos e 3 negativos/ambíguos). A comparação usa `gemini-3.1-flash-lite`, pois o modelo padrão `gemini-3.5-flash` retornou HTTP 503 por alta demanda durante a execução.

As quatro variantes (`llm_only`, `lexical_documental`, `lexical_llm`, `best_llm` com busca híbrida) concluíram 12/12 casos sem erros. As três variantes com recuperação tiveram Hit@1, acurácia de status e precisão de citação iguais a 1,00 nos campos calculáveis. Essas métricas medem a recuperação e as citações; **não substituem a revisão humana da qualidade das respostas**. O relatório marca `human_review: pending`.

Relatório: `evals/results/week3_v10_response_dev_exploratory.json`.

## Verificações de código

`ruff check`, `ruff format --check`, `mypy src tests` e `pytest -m 'not dvc'` passaram após as correções de portabilidade do hash de revisão e cache de embeddings por pergunta. Resultado do pytest: 388 passed, 1 skipped, 38 deselected.
