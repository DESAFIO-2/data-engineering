# Resultado da nova rodada independente de recuperação v9

**Execução única do split `test`:** 12/11/2026, estratégias `exact` e `lexical`, `top_k=5`. Código e gabarito congelados no commit `4444f4ff88fc8a0593820d6eaa45370dba0af0f8` antes da avaliação. O Git foi marcado `dirty` pelo avaliador devido a uma alteração preexistente em `data/README.md`, fora dos arquivos do gate.

- Dataset SHA-256: `181ee21cc2f3b7b615d66d7391a4c4c57ee0a53ba60745a97b626b0b67664a82`; folha SHA-256: `904d7adf76d13b251a80ceece84525099e0d1c8d740671cacb94f4f2d42f1295`.
- Release: `ea72d7705cccf7a14c359bd67d60807ce5e994ecd541810f1a6d066d33f01a84`; chunks SHA-256: `f6049cedf006aefd7bbc3d06f2b2fda0de4a906e3d95a1fb6272c08b9ec9da8e`.
- Resultados integrais: [exact](../../../evals/results/consolidated_v9_next_exact_test.json) e [lexical](../../../evals/results/consolidated_v9_next_lexical_test.json).

## Métricas do gate

| Estratégia | Casos | Positivos | Hit@5 | MRR@5 | Confusões críticas | Citações verificáveis | Abstenção nos negativos |
|---|---:|---:|---:|---:|---:|---:|---:|
| exact | 28 | 24 | 1.00 | 1.00 | 0 | 26/26 (1.00) | 1.00 |
| lexical | 28 | 24 | 1.00 | 1.00 | 0 | 26/26 (1.00) | 1.00 |

**Gate aprovado nas duas estratégias:** Hit@5 ≥ 0,90, MRR@5 ≥ 0,80, zero confusões críticas e 100% das citações emitidas verificáveis. Os quatro negativos foram corretamente recusados em ambas.

## Por fonte

| Estratégia | Fonte | Casos | Positivos | Hit@5 | MRR@5 | Confusões críticas |
|---|---|---:|---:|---:|---:|---:|
| exact | F01 | 12 | 11 | 1.00 | 1.00 | 0 |
| exact | F03 | 12 | 10 | 1.00 | 1.00 | 0 |
| exact | F04 | 4 | 3 | 1.00 | 1.00 | 0 |
| lexical | F01 | 12 | 11 | 1.00 | 1.00 | 0 |
| lexical | F03 | 12 | 10 | 1.00 | 1.00 | 0 |
| lexical | F04 | 4 | 3 | 1.00 | 1.00 | 0 |

## Por caso

| ID | Fonte | Esperado | Exact: status/rank | Lexical: status/rank | Crítica | Citações |
|---|---|---|---|---|---|---|
| V9-R2-001 | F01 | matched | matched/1 | matched/1 | não | 1/1; todas válidas |
| V9-R2-002 | F01 | matched | matched/1 | matched/1 | não | 1/1; todas válidas |
| V9-R2-003 | F01 | matched | matched/1 | matched/1 | não | 1/1; todas válidas |
| V9-R2-004 | F01 | matched | matched/1 | matched/1 | não | 1/1; todas válidas |
| V9-R2-005 | F01 | matched | matched/1 | matched/1 | não | 1/1; todas válidas |
| V9-R2-006 | F01 | matched | matched/1 | matched/1 | não | 1/1; todas válidas |
| V9-R2-007 | F01 | matched | matched/1 | matched/1 | não | 1/1; todas válidas |
| V9-R2-008 | F01 | matched | matched/1 | matched/1 | não | 1/1; todas válidas |
| V9-R2-009 | F01 | matched | matched/1 | matched/1 | não | 1/1; todas válidas |
| V9-R2-010 | F01 | matched | matched/1 | matched/1 | não | 1/1; todas válidas |
| V9-R2-011 | F01 | matched | matched/1 | matched/1 | não | 1/1; todas válidas |
| V9-R2-012 | F03 | matched | matched/1 | matched/1 | não | 1/1; todas válidas |
| V9-R2-013 | F03 | matched | matched/1 | matched/1 | não | 1/1; todas válidas |
| V9-R2-014 | F03 | matched | matched/1 | matched/1 | não | 1/1; todas válidas |
| V9-R2-015 | F03 | matched | matched/1 | matched/1 | não | 2/2; todas válidas |
| V9-R2-016 | F03 | matched | matched/1 | matched/1 | não | 1/1; todas válidas |
| V9-R2-017 | F03 | matched | matched/1 | matched/1 | não | 2/2; todas válidas |
| V9-R2-018 | F03 | matched | matched/1 | matched/1 | não | 1/1; todas válidas |
| V9-R2-019 | F03 | matched | matched/1 | matched/1 | não | 1/1; todas válidas |
| V9-R2-020 | F03 | matched | matched/1 | matched/1 | não | 1/1; todas válidas |
| V9-R2-021 | F03 | matched | matched/1 | matched/1 | não | 1/1; todas válidas |
| V9-R2-022 | F04 | matched | matched/1 | matched/1 | não | 1/1; todas válidas |
| V9-R2-023 | F04 | matched | matched/1 | matched/1 | não | 1/1; todas válidas |
| V9-R2-024 | F04 | matched | matched/1 | matched/1 | não | 1/1; todas válidas |
| V9-R2-025 | F01 | not_in_scope | not_in_scope/— | not_in_scope/— | não | 0/0; todas válidas |
| V9-R2-026 | F03 | not_in_scope | not_in_scope/— | not_in_scope/— | não | 0/0; todas válidas |
| V9-R2-027 | F03 | not_in_scope | not_in_scope/— | not_in_scope/— | não | 0/0; todas válidas |
| V9-R2-028 | F04 | not_in_scope | not_in_scope/— | not_in_scope/— | não | 0/0; todas válidas |

## Interpretação e limite

O gate formal foi cumprido neste conjunto. As perguntas têm estrutura curta e uniforme (“Segundo a fonte, consta ...?”); os negativos alteram a dose de famílias com positivos no mesmo conjunto. Isso reduz a dificuldade do teste e não demonstra, por si só, robustez a linguagem variada. As três famílias positivas F04 já haviam sido usadas na v8, limitação aceita antes da revisão. O resultado v9 anterior permanece histórico e não foi reexecutado. Nenhum índice vetorial ou embedding foi iniciado nesta rodada.
