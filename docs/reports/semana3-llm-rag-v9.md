# Semana 3 — LLM × RAG no SUS Cidadão

**Data limite:** 13/11/2026. **Estado:** quatro buscas concluídas em desenvolvimento; decisão final condicionada à revisão humana e a um conjunto independente congelado.

## Produto e hipótese

O produto responde perguntas documentais sobre a presença de apresentações nas listas F01 RENAME, F03 REME-DF e F04 Farmácia Popular. Presença na lista não demonstra estoque, elegibilidade, indicação ou dose individual. A hipótese principal é que recuperar a apresentação exata e citar a fonte reduz respostas sem sustentação. A hipótese secundária é que embeddings ou síntese com LLM podem melhorar a utilidade sem criar confusões de apresentação.

## Material e protocolo

- Release: `data/releases/corpus-consolidado-v9-aprovado-2026-11-12`; fingerprint `ea72d7705cccf7a14c359bd67d60807ce5e994ecd541810f1a6d066d33f01a84`.
- Chunks: 2.114 evidências; SHA-256 `f6049cedf006aefd7bbc3d06f2b2fda0de4a906e3d95a1fb6272c08b9ec9da8e`.
- Desenvolvimento: [`week3_v9_dev_draft.jsonl`](../../evals/datasets/week3_v9_dev_draft.jsonl), 12 perguntas sintéticas. Nove positivas foram reescritas a partir do conjunto exploratório v9; há uma ambígua, uma de segurança e uma negativa de concentração plausível. A negativa foi conferida no catálogo do release; a conferência nos PDFs e a revisão humana do conjunto ainda precisam ser registradas.
- O teste independente v9 anterior, de 28 casos, já foi executado para `exact` e `lexical` e permanece [histórico](validacao-recuperacao-v9-next-test.md). Ele não será reutilizado para selecionar a configuração da Semana 3.
- Novo candidato de teste: [`week3_v9_test_candidate_unreviewed.jsonl`](../../evals/datasets/week3_v9_test_candidate_unreviewed.jsonl), com 11 perguntas separadas do desenvolvimento desta semana. A [folha de revisão](semana3-v9-test-review-template.md) contém conferência técnica nas fontes oficiais, mas a decisão humana ainda está pendente. O executor exige revisão vinculada e hash congelado antes de aceitar `--split test`.
- Todas as buscas usam a mesma pergunta, release, filtro estruturado de apresentação, `top_k=5` e código. O índice vetorial deve passar pela checagem de fingerprint, modelo, IDs, textos, contagem e dimensão de embeddings. Uma falha de índice impede a execução vetorial; não é contada como resultado lexical.
- Na matriz de respostas, o Gemini e o prompt ficam fixos. O cenário sem contexto recebe apenas a pergunta e a regra de declarar incerteza; os cenários RAG recebem as evidências recuperadas. O executor grava pergunta, resposta, IDs, latência, falha e uso de tokens quando disponível, sem dados de pacientes.

## Oito cenários

| Matriz | Cenário | O que isola |
|---|---|---|
| Busca | `exact` | Identidade estruturada e ordem determinística |
| Busca | `lexical` | BM25 após filtro de apresentação |
| Busca | `vector` | Embedding após o mesmo filtro |
| Busca | `hybrid` | Fusão lexical/vetorial após o mesmo filtro |
| Resposta | `llm_only` | Gemini sem evidência recuperada |
| Resposta | `lexical_documental` | Evidência e resposta documental sem LLM |
| Resposta | `lexical_llm` | Efeito da síntese sobre evidência lexical |
| Resposta | `best_llm` | Efeito da síntese sobre a melhor busca segura distinta da lexical; neste ensaio, a busca exata |

## Medição e revisão

Busca: Hit@1/3/5 e MRR@5 sobre casos positivos; acerto de status sobre todos; confusão crítica quando `matched` aponta apresentação diferente ou responde um negativo; citações verificáveis sobre as citações emitidas; falhas e latências p50/p95. Exibir denominadores, fonte e comparação pareada por pergunta.

Resposta: revisão humana por `(cenário, ID, hash da resposta)` com correção factual, fidelidade, completude, suporte de citação, abstenção e erro crítico. `null` significa não avaliado ou não aplicável. BLEU e ROUGE podem aparecer como apoio, mas não substituem a revisão. Uma resposta sem evidência recuperada não recebe crédito por citação, ainda que mencione uma fonte de memória.

## Critério de escolha

Rejeitar qualquer configuração com confusão crítica ou citação emitida não verificável. Entre as seguras, comparar utilidade revisada, abstenção, falhas e p95. Adotar vetor ou LLM apenas diante de ganho observável sobre a linha lexical/documental, sem piora material. Se o conjunto independente for pequeno ou a revisão estiver pendente, recomendar a configuração lexical/documental como padrão provisório e declarar que a superioridade não foi demonstrada.

## Reprodução e links

Código: [`scripts/week3_compare.py`](../../scripts/week3_compare.py), [consolidador de revisão humana](../../scripts/week3_review.py), avaliador consolidado em [`src/rag/consolidated_evaluation.py`](../../src/rag/consolidated_evaluation.py), [repositório](https://github.com/DESAFIO-2/engenharia-dados). Configurar `APP_GOOGLE_API_KEY`, `APP_RAG_CHAT_MODEL` e `APP_RAG_EMBEDDING_MODEL` localmente, sem registrar a chave. Rodar a partir da raiz:

```bash
PYTHONPATH=src uv run python -m rag.cli index --release data/releases/corpus-consolidado-v9-aprovado-2026-11-12
PYTHONPATH=src uv run python -m scripts.week3_compare --matrix retrieval --release data/releases/corpus-consolidado-v9-aprovado-2026-11-12 --dataset evals/datasets/week3_v9_dev_draft.jsonl --output evals/results/week3_v9_retrieval_dev.json
PYTHONPATH=src uv run python -m scripts.week3_compare --matrix response --best-strategy lexical --release data/releases/corpus-consolidado-v9-aprovado-2026-11-12 --dataset evals/datasets/week3_v9_dev_draft.jsonl --output evals/results/week3_v9_response_dev.json
```

Os resultados de desenvolvimento aparecem abaixo. Uma rodada final exige **outro conjunto independente**, revisão humana documentada e hash congelado antes da primeira execução; não se atribui revisão humana automaticamente aos casos derivados.

Depois de preencher integralmente a folha de respostas e conferir os hashes, consolidar a revisão:

```bash
PYTHONPATH=src uv run python -m scripts.week3_review --runs evals/results/week3_v9_response_dev.json evals/results/week3_v9_response_dev_exact_llm.json --regression evals/results/week3_v9_entacapona_response_after_fix.json --reviews evals/reviews/week3_v9_response_dev_after_fix_review.csv --output evals/results/week3_v9_human_review.json
```

Na planilha, preencher as seis notas com `true` ou `false`; deixar vazio somente quando o critério não se aplicar ou não tiver sido avaliado. `critical_error=true` significa falha grave. O comando exige revisor, data, justificativa e vínculo de hash para cada uma das 48 respostas; um campo de nota vazio não vira aprovação automática.

## Resultados de desenvolvimento: respostas

Artefatos por caso: [três cenários iniciais](../../evals/results/week3_v9_response_dev.json) e [busca exata + Gemini](../../evals/results/week3_v9_response_dev_exact_llm.json). Folha para revisão factual das quatro configurações, com a resposta da entacapona atualizada após a correção e hash de cada texto: [`week3_v9_response_dev_after_fix_review.csv`](../../evals/reviews/week3_v9_response_dev_after_fix_review.csv). As demais respostas vieram da primeira execução; a planilha identifica o texto exato que deve ser revisado. O primeiro ensaio repetiu lexical + Gemini em `best_llm`; essa repetição permanece no artefato bruto para auditoria, mas foi **excluída** da comparação de quatro configurações distintas.

| Cenário | Status correto | Hit@5 de evidência | Citações verificáveis | Erros de API | p95 total |
|---|---:|---:|---:|---:|---:|
| LLM sem contexto | N/A | N/A | N/A | 1/12 | 14.691 ms |
| Lexical documental | 11/12 | 8/9 | 10/10 | 0/12 | 52 ms |
| Lexical + Gemini | 11/12 | 8/9 | 10/10 | 1/12 | 14.740 ms |
| Exata + Gemini, melhor alternativa distinta | 11/12 | 8/9 | 10/10 | 0/12 | 34.413 ms |

Esta matriz completa precede a correção da pontuação descrita abaixo. O caso W3-DEV-02 (“Existe entacapona 200 mg...”) é positivo no release, mas retornou `not_in_scope` antes da correção. Houve uma falha `GoogleRateLimitError` em cada um dos cenários LLM sem contexto e lexical + Gemini; exata + Gemini não falhou com a terceira chave. A precisão de citações acima mede **as evidências recuperadas**, não se cada frase produzida pelo Gemini ficou bem sustentada; essa última avaliação depende da planilha humana. O ensaio não sustenta afirmar que a LLM melhorou a resposta.

## Resultados de desenvolvimento: busca exata e lexical

Artefatos por caso: [exata e lexical](../../evals/results/week3_v9_retrieval_dev_exact_lexical.json), [vetorial e híbrida](../../evals/results/week3_v9_retrieval_dev_vector_hybrid.json). As quatro estratégias foram executadas com as mesmas 12 perguntas após a validação do índice completo.

| Estratégia | Hit@1/3/5 | MRR@5 | Status correto | Confusões críticas | Citações verificáveis | p95 total |
|---|---:|---:|---:|---:|---:|---:|
| Exata | 8/9 | 0,889 | 11/12 | 0 | 10/10 | 40 ms |
| Lexical | 8/9 | 0,889 | 11/12 | 0 | 10/10 | 36 ms |
| Vetorial | 8/9 | 0,889 | 11/12 | 0 | 10/10 | 688 ms |
| Híbrida | 8/9 | 0,889 | 11/12 | 0 | 10/10 | 581 ms |

Por fonte, Hit@5 foi F01 2/3, F03 3/3 e F04 3/3 em todas as estratégias. O caso W3-DEV-02 falhou **antes do ranking** em todos os modos; embeddings não corrigiram a identificação estruturada da apresentação. Nesta amostra, vetor e híbrido não elevaram recuperação nem status e tiveram p95 cerca de 16 a 19 vezes maior que lexical. A comparação de latência é de execução sequencial pequena, sem intervalo de confiança; não estima carga de produção.

### Correção da falha e nova rodada de desenvolvimento

A checagem de concentração rejeitava a vírgula de enumeração após “200 mg” em “200 mg, comprimido”. O código passou a aceitá-la sem aceitar “20 mg” ou um número colado após a vírgula. O gabarito e as 12 perguntas permaneceram iguais. Resultados por caso da nova rodada: [exata/lexical](../../evals/results/week3_v9_retrieval_dev_exact_lexical_v2.json) e [vetorial/híbrida](../../evals/results/week3_v9_retrieval_dev_vector_hybrid_v2.json).

| Estratégia após correção | Hit@1/3/5 | Status correto | Confusões críticas | Citações verificáveis | p95 total |
|---|---:|---:|---:|---:|---:|
| Exata | 9/9 | 12/12 | 0 | 11/11 | 36 ms |
| Lexical | 9/9 | 12/12 | 0 | 11/11 | 37 ms |
| Vetorial | 9/9 | 12/12 | 0 | 11/11 | 943 ms |
| Híbrida | 9/9 | 12/12 | 0 | 11/11 | 558 ms |

Um [ensaio direcionado da entacapona](../../evals/results/week3_v9_entacapona_response_after_fix.json) repetiu os quatro cenários de resposta após a correção. Os três cenários com recuperação passaram de `not_in_scope` para `matched`, com evidência verificável; LLM sem contexto continuou sem evidência. As outras 11 respostas não foram repetidas depois da correção. A matriz completa de respostas acima deve ser lida como linha de base anterior à melhoria.

### Bloqueio do índice vetorial

A indexação do modelo configurado localmente, `gemini-embedding-2`, parou em 992/2.114 e depois em 1.984/2.114 chunks com `429 RESOURCE_EXHAUSTED`: a API informou limite de **1.000 solicitações diárias de embedding no plano gratuito** para cada chave usada. Uma terceira chave fornecida pela responsável concluiu os 130 restantes. O marcador `index.json` foi criado após conferir IDs, textos, contagem e dimensão de todos os 2.114 vetores. A execução mostrou que o índice é retomável, mas também que a cota gratuita de uma chave não comportou a construção integral no mesmo dia.

## Decisão atual

**Padrão provisório: busca lexical com resposta documental.** Após a correção, as quatro buscas empataram nas métricas de qualidade desta amostra, e lexical manteve p95 muito menor que vetor/híbrido. A resposta documental foi o cenário completo sem falha de API na matriz de respostas anterior à correção. A decisão final depende da revisão humana e do teste independente congelado. Não declarar superioridade estatística com 12 casos de desenvolvimento.
