# Parecer do gate de recuperação v9 — teste independente

**Data:** 12/11/2026. **Decisão:** reprovado para avanço à vetorização. O `test` congelado foi executado uma vez por estratégia, sem ajuste posterior do código ou gabarito.

## Rastreabilidade

- Commit do código, candidato, folha aprovada e dataset na execução: `55fd37b8af44e117bfe097ad633873bd4389a35d`.
- Release: `corpus-consolidado-v9-aprovado-2026-11-12`; `release.json` SHA-256 `ea72d7705cccf7a14c359bd67d60807ce5e994ecd541810f1a6d066d33f01a84`.
- Chunks: 2.114; `chunks.jsonl` SHA-256 `f6049cedf006aefd7bbc3d06f2b2fda0de4a906e3d95a1fb6272c08b9ec9da8e`.
- Dataset: `consolidated_v9_reviewed.jsonl` SHA-256 `d66412357e72c7df3fb6975c34773613b8356ff11da67ee114995bd382873b28`; folha v2 SHA-256 `96d523fd3d16832fc539351a530daee0e7b4fb5915207372701002b190459275`.
- Parâmetros: split `test`, `top_k=5`, Python 3.12.16; 28 casos, sendo 24 positivos e quatro negativos. Resultados completos em `evals/results/consolidated_v9_exact_test.json` (SHA-256 `2859d1044cc93fdd054cb38d899e9445975138fec5676992648e9c0e3e0ed1ab`) e `evals/results/consolidated_v9_lexical_test.json` (SHA-256 `f9dc1339c8cf09effabb2d395ddcb4eda8f3120317c18ab1a364341578a09af6`).
- Ambos os JSONs registram `git.dirty=true` devido à alteração preexistente e não relacionada em `data/README.md`; o código e o gabarito avaliados estavam no commit acima. Essa alteração ficou fora do commit e não participa da recuperação.

## Resultados

| Métrica | Exata | Lexical | Gate |
|---|---:|---:|---:|
| Hit@5 (24 positivos) | 19/24 = 0,7917 | 19/24 = 0,7917 | ≥ 0,90 |
| MRR@5 (24 positivos) | 0,7917 | 0,7917 | ≥ 0,80 |
| Confusões críticas | 0 | 0 | 0 |
| Citações verificáveis emitidas | 24/24 | 24/24 | 100% |
| Abstenções corretas (4 negativos) | 4/4 | 4/4 | — |
| Latência p50 / p95 | 25,81 / 28,31 ms | 26,52 / 28,65 ms | — |

| Fonte | Casos (positivos/negativos) | Hit@5 exata | Hit@5 lexical | Erros positivos |
|---|---:|---:|---:|---|
| F01 | 10/1 | 8/10 | 8/10 | 006, 009 |
| F03 | 10/2 | 8/10 | 8/10 | 017, 018 |
| F04 | 4/1 | 3/4 | 3/4 | 023 |

O denominador de citações inclui apenas as citações **emitidas**; os cinco positivos não recuperados não produziram citações. A métrica de citações, portanto, não compensa as falhas de cobertura.

## Erros por caso

As duas estratégias falharam nos mesmos cinco casos antes do ranqueamento: nenhum gerou chunks candidatos para eles. O resultado lexical igual ao exato decorre desse filtro anterior; estes números não demonstram vantagem ou desvantagem do ranqueador lexical.

| Caso | Esperado | Obtido | Diagnóstico observável |
|---|---|---|---|
| 006, F01 homeopáticos | `matched` | `ambiguous` | O filtro pede concentração/forma, embora a pergunta siga a descrição aprovada; os dois campos da fonte contêm a mesma frase. |
| 009, F01 garra-do-diabo | `matched` | `ambiguous` | O filtro pede característica de liberação apesar de a pergunta dizer `liberação retardada`. |
| 017, F03 imunoglobulina anti-Rho | `matched` | `not_in_scope` | Concentração não localizada; o campo aprovado inclui faixa de dose e recipiente. |
| 018, F03 Ringer com lactato | `matched` | `not_in_scope` | Concentração não localizada; o campo aprovado inclui volume e acondicionamento. |
| 023, F04 etinilestradiol + levonorgestrel | `matched` | `not_in_scope` | O filtro pede apresentação exata; a pergunta associa cada fármaco à sua dose na ordem do PDF. |

## Encaminhamento

O gate exige Hit@5 ≥ 0,90, MRR@5 ≥ 0,80, zero confusões críticas e 100% das citações emitidas verificáveis. Ambas as estratégias falharam nos dois primeiros limiares. **Não iniciar embeddings, benchmark vetorial/híbrido, RAGAS ou integração com o agente.** Preservar estes resultados e o teste congelado sem alterações. Investigar o filtro de identidade em desenvolvimento com casos próprios; para uma nova decisão de gate, preparar e aprovar outro teste independente. Não retunar nem reexecutar sobre este `test`.

Na verificação da suíte, 284 testes passaram e dois testes antigos de `test_rag_release.py` falharam porque falta `data/silver/F01/a991dd...jsonl` neste checkout. Os seis testes específicos da v9 e Ruff passaram. Essa falta de dados silver não explica os cinco erros de recuperação observados no release v9 já carregado.
