# Diagnóstico exploratório da recuperação exata e lexical — v9

**Estado em 12/11/2026:** desenvolvimento concluído para o conjunto migrado; **gate de recuperação ainda fechado**. Nenhum `test` da v9 foi executado. Os 27 casos restantes do `test` v8 são históricos e não constituem teste independente para a v9.

## Entrada e migração

- Release aprovado: `corpus-consolidado-v9-aprovado-2026-11-12`; SHA-256 do manifesto `ea72d7705cccf7a14c359bd67d60807ce5e994ecd541810f1a6d066d33f01a84`; fingerprint de conteúdo `99d4fb04a74463b9cfdd4ea9c08b51a0ef39bb5631be58964209d6041f9e1b20`.
- Chunks canônicos: 2.114; SHA-256 `f6049cedf006aefd7bbc3d06f2b2fda0de4a906e3d95a1fb6272c08b9ec9da8e`.
- [Gabarito exploratório](../../../evals/datasets/consolidated_v9_dev_exploratory.jsonl): SHA-256 `9acef45d40c603565f181dbeb2e3ef4048299b2baaf983cc24441a49e67bfd39`, 119 IDs únicos, 92 em `dev` e 27 casos históricos marcados como `test` e bloqueados. Os estados de revisão foram reiniciados para `agent_reviewed`; nenhuma revisão humana da v9 foi presumida.
- O caso `C-F03-005`, que já havia sido aberto no teste v8, foi movido para `dev`. Sua pergunta genérica de claritromicina 500 mg comprimido agora aceita como relevantes as linhas F03 247, 248 e 249, páginas 21–22. As três compartilham o `medicine_id` corrigido, mas preservam código, contexto e canal próprios. Isso implementa a [aprovação documental de Jhiovana](revisao-claritromicina-v9-jhiovana.md), sem inferir equivalência clínica ou de dispensação.
- O pré-voo da avaliação agora compara cada referência esperada com o release aprovado: princípio ativo, concentração, forma, liberação, ID da apresentação, ID de evidência, linha, fonte, versão e página. Um desvio interrompe a avaliação.

## Resultado em `dev`, `top_k=5`

| Estratégia | Casos | Positivos | Hit@1/3/5 | MRR@5 | Status e apresentação | Confusões críticas | Citações verificáveis | p50/p95 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Exata | 92 | 77 | 1,0000 | 1,0000 | 1,0000 / 1,0000 | 0 | 81/81 | 261/307 ms |
| Lexical | 92 | 77 | 1,0000 | 1,0000 | 1,0000 / 1,0000 | 0 | 81/81 | 263/312 ms |

F01: 31 casos, 29 positivos; F03: 21 casos, 21 positivos; F04: 27 casos, 27 positivos. As 15 abstenções esperadas foram corretas. [Resultado exato](../../../evals/results/consolidated_v9_exact_dev_exploratory.json) e [lexical](../../../evals/results/consolidated_v9_lexical_dev_exploratory.json) trazem status, candidatos, trechos ordenados e tempo por caso. O único ordenamento distinto entre estratégias ocorreu em `C-F03-001`, sem alterar a primeira evidência relevante nem as métricas. Os dois processos foram executados simultaneamente; suas latências não devem ser comparadas diretamente com execuções isoladas.

Esse desempenho é **exploratório**: 91 perguntas vieram do conjunto já conhecido, e a pergunta adicional veio do teste histórico aberto. O conjunto contém muitos enunciados sintéticos próximos dos campos estruturados. Acerto perfeito aqui não demonstra generalização para consultas espontâneas, erros de grafia ou casos difíceis não vistos. A correção aplicada foi de identidade documental e gabarito; não houve ajuste de ranking guiado pelo `test`.

## Reprodutibilidade e próximo gate

O diagnóstico usou Git HEAD `420d344193c535f80c3150e7c5058c48df8dad22` com árvore de trabalho modificada. SHA-256 do recuperador `src/rag/consolidated.py`: `1ff96eb4e815aed42d696ee9d682c19614e24c0ca320df609784825102be48a3`; avaliador **na execução**: `0e144114ac3cd17637327efa32a0fbb6d2092c52a753e0b53dbf782792ebd41b`; CLI **na execução**: `77cb181dba4e46e22d8e5af8e99af1a5788ff584a50f7ef9b3d10188b2b43b48`. Depois da execução, apenas as regras de abertura do novo `test` mudaram no avaliador (`6a4a12de0eeaf63fc7efa8ab733b9db6ab4add8c74a7879465c3c0db1b3dff0b`) e na CLI (`409d4952ee0a0304fec025fdda0ccd954518076d135a5ace0ccb7a4e83bb67b1`); o recuperador, as perguntas e as métricas de `dev` não foram alterados.

Ruff passou nos arquivos alterados, os seis testes específicos da migração e do candidato passaram e a suíte completa terminou com **286 testes aprovados**. Uma tentativa de invocar `--split test` na v9 retornou o erro esperado de teste fechado, sem produzir resultado.

```powershell
uv run python scripts/prepare_v9_retrieval_dev.py
uv run python app.py eval --release data/releases/corpus-consolidado-v9-aprovado-2026-11-12 --dataset evals/datasets/consolidated_v9_dev_exploratory.jsonl --split dev --strategy exact --output evals/results/consolidated_v9_exact_dev_exploratory.json
uv run python app.py eval --release data/releases/corpus-consolidado-v9-aprovado-2026-11-12 --dataset evals/datasets/consolidated_v9_dev_exploratory.jsonl --split dev --strategy lexical --output evals/results/consolidated_v9_lexical_dev_exploratory.json
```

Um [novo candidato independente](../../../evals/datasets/consolidated_v9_test_candidate_unreviewed.jsonl) de 28 casos foi preparado com famílias ausentes de **todo** o conjunto histórico v8: 10 positivos F01, 10 F03, quatro F04 e quatro negativos de concentração. SHA-256 do candidato `c80c9db2fd168d2782fec7fa9c4c780471ae5507a25f8a66e47c85fa72e31d66`. Nenhuma pergunta desse candidato foi enviada ao recuperador. A [folha de revisão](v9-independent-test-review.md) contém pergunta, status, apresentação, evidência e página de cada caso, com colunas pendentes para decisão, revisor, data e justificativa. **As expectativas foram geradas do catálogo e ainda não foram conferidas com os PDFs por Jhiovana; o candidato não é um gabarito aprovado.** O script `scripts/promote_v9_test.py` recusa decisões pendentes ou rejeitadas, verifica as colunas contra o candidato e impede sobrescrever um teste já congelado. A revisão preenchida terá hash vinculado ao gabarito promovido.

Para abrir o novo gate, falta conferir pergunta, status, apresentação, evidência, fonte e página com os PDFs, corrigir eventuais rejeições de forma rastreável, registrar a revisão humana de Jhiovana e congelar dataset/código/parâmetros. Só então executar `test` uma vez por estratégia. Critérios: Hit@5 ≥ 0,90, MRR@5 ≥ 0,80, zero confusões críticas e 100% das citações verificáveis. A CLI bloqueia o `test` v9 enquanto esse novo conjunto e sua revisão não existirem.
