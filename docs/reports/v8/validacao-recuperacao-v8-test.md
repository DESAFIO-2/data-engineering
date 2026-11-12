# Gate da recuperação exata e lexical — v8

**Decisão em 11/11/2026: NÃO APROVADO para avançar aos embeddings.** O release documental v8 está aprovado por Jhiovana, mas o gate de recuperação falhou no split `test` por uma confusão crítica sinalizada pelo avaliador nas duas estratégias. O código e o gabarito não foram alterados após a abertura do `test`.

## Proveniência

- Release aprovado: `corpus-consolidado-v8-aprovado-2026-11-11`; SHA-256 do manifesto `d634a75817ff3d16031c45fa664b9075ec426c1b3482581c0ca93f490906cba7`; fingerprint de conteúdo `d522b389b566235c3b59436c7e7055441cace1a30961d5a290f9d9f3bf872df5`.
- Chunks canônicos: 2.114; SHA-256 `239c8cde996679d59b8ae46283f213580c87d2ef9ba3c2df18b74289b28987ec`.
- Dataset v8 revisado: 119 casos, `dev` 91 e `test` 28; SHA-256 `8dfa79d2968aa2aa7acb567c11bc753432b135524674ce5cb23bc7b299078d39`. A revisão da correção tem SHA-256 `183135bb371cd8f4a6b34e55369c57e482e89aa3c190e149e53459b680d3ecae` e incorpora 118 decisões humanas anteriores, cuja planilha tem SHA-256 `704e1e5072c14720b8f1ce64123692cd19ed37dfd5847d556559eca8aa38d103`.
- Código congelado para este teste: SHA-256 `src/rag/consolidated.py` `1ff96eb4e815aed42d696ee9d682c19614e24c0ca320df609784825102be48a3`; `consolidated_cli.py` `6e7c5e548ac297425aa10bc7b9725a71e91f61f57203dc774a59f6b25fd8da14`; `consolidated_evaluation.py` `2c0e4ffa90b8b3d05164bb4888e3f86d0dc4861729b891ea9c796c3d627864a0`. Git HEAD `420d344193c535f80c3150e7c5058c48df8dad22`, com alterações locais ainda não publicadas.
- Pré-verificação: Ruff passou; 276 testes da suíte completa passaram; `dev` teve Hit@5 e MRR@5 de 1,0 para exata e lexical, zero confusões críticas.

## Resultado oficial do split test

| Estratégia | Casos | Positivos | Hit@1 | Hit@3/5 | MRR@5 | Status | Apresentação | Confusões sinalizadas | Citações válidas | p95 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Exata | 28 | 23 | 0,9565 | 1,0000 | 0,9710 | 1,0000 | 0,9565 | **1** | 25/25 | 269,6 ms |
| Lexical | 28 | 23 | 0,9565 | 1,0000 | 0,9710 | 1,0000 | 0,9565 | **1** | 25/25 | 284,9 ms |

F01: 10/10 positivos com Hit@5; F03: 10/10; F04: 3/3. As cinco abstenções esperadas foram corretas. Os [resultados exatos](../../../evals/results/consolidated_v8_exact_test.json) e [lexicais](../../../evals/results/consolidated_v8_lexical_test.json) incluem IDs e tempos por caso. Cada estratégia foi executada uma vez no split `test`.

## Caso que bloqueia o gate

`C-F03-005` pergunta se **claritromicina 500 mg comprimido** consta na REME-DF. O gabarito aponta somente a linha 249, p. 22, descrita como `500mg` para tuberculose. A recuperação retornou antes dela as linhas 247 e 248 da mesma página, descritas como `500 mg` para coqueluche e hanseníase. As três têm o mesmo princípio ativo, dose numérica e forma; diferem na grafia do espaço e no contexto textual/canal. O avaliador conta duas entradas de catálogo com IDs distintos e sinaliza uma confusão crítica de apresentação. Isso **pode ser um defeito da identidade do catálogo ou do gabarito**, em vez de troca real de dose ou forma; é uma hipótese a auditar, não uma correção autorizada pelo resultado de `test`.

O gate exigia Hit@5 ≥ 0,90, MRR@5 ≥ 0,80, zero confusões críticas e 100% das citações verificáveis. Três critérios passaram; **zero confusões falhou**. Preservar estes resultados como teste histórico. Auditar as linhas 247–249, a definição de apresentação e o gabarito em conjunto novo de desenvolvimento; não reescrever o resultado oficial nem ajustar parâmetros usando esta amostra fechada. Após decisão de domínio e nova revisão, criar um novo split de teste independente para uma nova tentativa de gate.

Os ponteiros DVC do release e dos chunks v8 foram criados, e `dvc status` informou dados locais atualizados. Jhiovana confirmou que executou `uv run dvc push` no PowerShell autenticado e que `uv run dvc status -c` informou cache e remoto sincronizados para a v8. A sincronização do armazenamento não altera a decisão do gate de recuperação.
