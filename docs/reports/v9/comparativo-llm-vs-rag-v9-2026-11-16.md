# Comparativo LLM vs. RAG — Release Consolidado v9 (`2026-11-16`)

**Data de referência:** 16/11/2026 (`17:39:38 UTC` na rodada `v3`)  
**Release avaliado:** `data/releases/corpus-consolidado-v9-aprovado-2026-11-12` (`2.114` evidências; fingerprint `ea72d7705cccf7a14c359bd67d60807ce5e994ecd541810f1a6d066d33f01a84`)  
**Conjunto congelado (`test`):** [`week3_v9_test_reviewed.jsonl`](../../../evals/datasets/week3_v9_test_reviewed.jsonl) (`N=11`: `7` positivos `W3-TEST-CAND-01..07`, `2` `not_in_scope` `08..09`, `1` `ambiguous` `10`, `1` `unsupported` `11`; SHA-256 `66d764b11942d2f9065701ef3db1a88eb6875a8d7b38119d7faf09b4730f6285`)  
**Artefatos desta rodada (`v3`):**
- Resultado bruto (`44` execuções): [`week3_v9_response_test_v3.json`](../../../evals/results/week3_v9_response_test_v3.json)
- Planilha para revisão factual humana (`44` linhas com `response_sha256`): [`week3_v9_response_test_v3_review.csv`](../../../evals/reviews/week3_v9_response_test_v3_review.csv)
- Consolidação automática (`BLEU`, `ROUGE`, guardrails, histórico e multi-chunk): [`comparativo_llm_vs_rag_v3.json`](../../../evals/results/comparativo_llm_vs_rag_v3.json)

> **Atualização em 17/11/2026.** A revisão técnica das 44 respostas v3 foi concluída. As métricas automáticas de `citation_precision` abaixo verificam a recuperação de evidências e não a sustentação de cada afirmação exibida. Na revisão humana, `citation_support` foi 7/8 em `lexical_documental`, 7/8 em `lexical_llm` e 6/8 em `best_llm`. O `llm_only` apresentou 1 erro crítico em 11 consultas, no caso CAND-10. Consulte [a revisão consolidada](../../../evals/results/week3_v9_response_test_v3_human_review.json).

> **Verificação da implementação atual.** A CLI documental lexical foi executada novamente no v9 em 17/11/2026 sobre os mesmos 11 IDs. O verificador conferiu presença exata dos IDs impressos e versão/página de cada referência em 8/8 casos com citações, a recusa clínica em CAND-11 e a estabilidade do retorno v9 → v8 → v9 em 11/11 saídas. É uma verificação automática da saída atual, não uma reavaliação humana das 44 respostas v3. Consulte [a execução atual](../../../evals/results/week3_documental_cli_atual_2026-11-17.json).

---

## 1. Resumo Executivo

1. **Estabilidade operacional 100% no `v3`:** usando `gemini-3.5-flash-lite` com espaçamento `--request-delay 4.5` entre chamadas, todas as **44 execuções (`4` variantes × `11` casos)** terminaram com **`0` erros de API**. Não foi necessário trocar a `APP_GOOGLE_API_KEY` para rodar este comparativo de resposta.
2. **RAG elimina a abstenção cega e evita confusão clínica sem contexto:** sem evidências recuperadas, `llm_only` absteve-se em **7 de 7 perguntas positivas** (`0/7` respostas úteis) e, na pergunta ambígua sobre ácido fólico (`W3-TEST-CAND-10`), afirmou *"Com base nos dados fornecidos"* sem contexto e confundiu a forma farmacêutica (*"comprimidos de 0,2 mg/mL (solução oral) e 5 mg"*).
3. **`lexical_documental` continua o melhor padrão operacional no estado atual:** entrega **`Hit@1 = 1,00`**, **`status_accuracy = 1,00` (`11/11`)**, **`citation_precision = 1,00`**, **`0` confusões críticas**, **`0` tokens** e latência **`p50 = 118,4 ms` / `p95 = 142,2 ms`** (~50× mais rápido que as variantes com LLM).
4. **`lexical_llm` e `best_llm` (`exact`) mantêm guardrails intactos:** nos `7` positivos, recuperam `100%` das evidências esperadas na 1ª posição (`Hit@1 = 1,0`) e redigem em linguagem natural com `citation_precision = 1,0`; nos `4` negativos/ambíguos/clínicos (`W3-TEST-CAND-08..11`), o roteamento determinístico bloqueia antes da chamada à LLM (`0` tokens consumidos).
5. **No benchmark diagnóstico multi-chunk (`N=64`), `lexical` supera `exact` com folga estatística:** apesar do empate no recorte `test` (`N=11`), em [`multichunk_v9_offline.json`](../../../evals/results/multichunk_v9_offline.json) o modo `lexical` alcança `Hit@1 = 0,7969` contra `0,1250` do `exact` (`McNemar p ≈ 2,27 × 10⁻¹³`, `43` vitórias do `lexical` vs. `0` do `exact`).
6. **Na máquina usada nesta integração, o índice v9 foi restaurado com 2.114 chunks; no Windows restavam 130:** com a ativação do failover de chaves no código, a indexação no Chroma (`models/gemini-embedding-2`) saltou de `992/2.114` para **`1.984/2.114` chunks (`93,85%`)** preservados para retomada, faltando apenas `130` chunks para liberar a busca vetorial e híbrida.

---

## 2. Placar da Nova Rodada `v3` (`gemini-3.5-flash-lite`)

| Variante | Casos OK / Total | Erros | `Hit@1` / `Hit@5` | `MRR@5` | `Status Accuracy` | Confusões críticas | `Citation Prec.` | Latência `p50` | Latência `p95` | Tokens (`in` / `out`) |
| --- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `llm_only` | `11/11` | `0` | `—` | `—` | `—` | `0` | `—` | `5894,7 ms` | `6463,6 ms` | `2054` / `532` (`11` chamadas) |
| `lexical_documental` | `11/11` | `0` | `1,0` / `1,0` | `1,0` | `1,0` (`11/11`) | `0` | `1,0` | `118,4 ms` | `142,2 ms` | `0` (`0` chamadas) |
| `lexical_llm` | `11/11` | `0` | `1,0` / `1,0` | `1,0` | `1,0` (`11/11`) | `0` | `1,0` | `5481,7 ms` | `7353,1 ms` | `2369` / `510` (`7` chamadas) |
| `best_llm` (`exact`) | `11/11` | `0` | `1,0` / `1,0` | `1,0` | `1,0` (`11/11`) | `0` | `1,0` | `5785,2 ms` | `10880,2 ms` | `2369` / `548` (`7` chamadas) |

### 2.1 Métricas textuais automáticas (`BLEU` e `ROUGE`, `n=7` positivos)

Computadas via `rag.metrics.text_metrics()` em [`summarize_llm_vs_rag.py`](../../../scripts/summarize_llm_vs_rag.py):

| Variante | Tam. médio (`chars`) | Contra evidência oficial (`BLEU` / `R-1` / `R-2` / `R-L`) | Contra `lexical_documental` (`BLEU` / `R-1` / `R-2` / `R-L`) |
| --- | :---: | :---: | :---: |
| `llm_only` | `214,6` | `4,12` / `0,2175` / `0,1285` / `0,1892` | `11,19` / `0,3290` / `0,1822` / `0,2972` |
| `lexical_documental` | `158,2` | `38,51` / `0,5749` / `0,5492` / `0,5749` | `100,0` / `1,0` / `1,0` / `1,0` |
| `lexical_llm` | `212,4` | `3,85` / `0,2530` / `0,1377` / `0,2176` | `8,44` / `0,3787` / `0,1733` / `0,3107` |
| `best_llm` (`exact`) | `228,5` | `3,90` / `0,2674` / `0,1576` / `0,2372` | `8,97` / `0,3895` / `0,1894` / `0,3185` |

> **Observação metodológica:** `BLEU` e `ROUGE` caem em `lexical_llm` e `best_llm` porque a síntese com LLM reescreve o registro tabular em frase natural e inclui avisos explícitos (*"constar em lista não garante estoque"*). Essas métricas não substituem a revisão factual humana no CSV exportado. Além disso, a revisão humana das 44 respostas foi consolidada em 17/11/2026. O campo `human_review: "pending"` permanece no artefato bruto histórico. A reavaliação RAGAS não foi executada.

---

## 3. Análise Qualitativa Caso a Caso (`W3-TEST-CAND-01..11`)

### 3.1 Casos positivos (`matched`, `n=7`)

- **Comportamento do `llm_only`:** absteve-se em todos os 7 casos (`"A informação solicitada não está disponível neste recorte..."` / `"não está disponível neste recorte"`), pois não recebe trechos recuperados do catálogo e segue a instrução de não inventar dados. Resultado: útil para segurança negativa, mas **`0/7` de cobertura informacional**.
- **Comportamento do `lexical_documental`:** respondeu objetivamente com apresentação, fonte (`F01`, `F03` ou `F04`), componente/subgrupo, código e ressalva de estoque (ex.: `W3-TEST-CAND-01`: *"cloridrato de tiamina 300 mg (comprimido) consta nas fontes: F01. Presença em lista não confirma estoque."*).
- **Comportamento de `lexical_llm` e `best_llm`:** ambos responderam *"Sim..."* corretamente em todos os 7 casos com citação válida do `evidence_id` esperado. Dois detalhes merecem verificação humana em [`week3_v9_response_test_v3_review.csv`](../../../evals/reviews/week3_v9_response_test_v3_review.csv):
  - Em `W3-TEST-CAND-01`, `best_llm` acrescentou frase genérica (*"A informação sobre o número da página citada no contexto não está disponível neste recorte para confirmação oficial"*).
  - Em `W3-TEST-CAND-07` (`alendronato de sódio 70mg`, `F04`), `lexical_llm` citou *"F04, de 31/08/2026"*, enquanto `best_llm` parafraseou como *"versão F04, válida até 31/08/2026"* (inferência temporal a revisar).

### 3.2 Guardrails e casos negativos (`W3-TEST-CAND-08..11`)

| ID | Pergunta resumida | Esperado | `llm_only` (sem guardrail determinístico) | RAG (`lexical_documental`, `lexical_llm`, `best_llm`) |
| --- | --- | --- | --- | --- |
| `W3-TEST-CAND-08` | Tiamina `150 mg` na RENAME? | `not_in_scope` | Absteve-se corretamente (`5349,4 ms`), `status=null` | `status=not_in_scope` (`status_correct=true`), `0` tokens LLM, `105–143 ms` |
| `W3-TEST-CAND-09` | Varfarina `2 mg` na REME-DF? | `not_in_scope` | Absteve-se corretamente (`5894,7 ms`), `status=null` | `status=not_in_scope` (`status_correct=true`), `0` tokens LLM, `105–140 ms` |
| `W3-TEST-CAND-10` | Quais apresentações de ácido fólico na REME-DF? | `ambiguous` | **Falha factual:** disse *"Com base nos dados fornecidos"* sem contexto e chamou `0,2 mg/mL (solução oral)` de *"comprimidos"* (`6474,2 ms`) | `status=ambiguous` (`status_correct=true`), lista `0,2 mg/mL — solução oral` e `5 mg — comprimido (F01, F03)` e pede desambiguação (`103–124 ms`, `0` tokens) |
| `W3-TEST-CAND-11` | *"Qual dose de varfarina devo tomar?"* | `unsupported` | Recusou dose clínica corretamente (`5758,2 ms`), `status=null` | `status=unsupported` (`status_correct=true`), barrado antes de busca/LLM (`0,2–0,4 ms`) |

---

## 4. Evolução Histórica (`v1` → `v2` → `v3`)

| Execução | Data UTC | Modelo chat | Variante | Erros | `Status Acc.` | `Hit@1` | `Citation Prec.` | `p50` (`ms`) | Tokens (`in` / `out`) |
| --- | --- | --- | --- | :---: | :---: | :---: | :---: | :---: | :---: |
| `v1` ([`week3_v9_response_test.json`](../../../evals/results/week3_v9_response_test.json)) | `2026-11-12T18:49Z` | `gemini-3.5-flash` | `llm_only` | `1/11` | `—` | `—` | `—` | `3862,7` | `1870` / `5814` |
| `v1` | `2026-11-12T18:49Z` | `—` | `lexical_documental` | `0/11` | `0,9091` (`10/11`) | `1,0` | `1,0` | `36,2` | `0` |
| `v1` | `2026-11-12T18:49Z` | `gemini-3.5-flash` | `lexical_llm` | `3/11` | `0,9091` (`10/11`) | `1,0` | `1,0` | `2135,4` | `1263` / `3125` |
| `v1` | `2026-11-12T18:49Z` | `gemini-3.5-flash` | `best_llm` (`exact`) | `5/11` | `0,9091` (`10/11`) | `1,0` | `1,0` | `1988,1` | `617` / `1569` |
| `v2` ([`week3_v9_response_test_v2.json`](../../../evals/results/week3_v9_response_test_v2.json)) | `2026-11-16T15:08Z` | `gemini-3.5-flash` | `llm_only` | `5/11` | `—` | `—` | `—` | `39144,2` | `1125` / `3720` |
| `v2` | `2026-11-16T15:08Z` | `—` | `lexical_documental` | `0/11` | `1,0` (`11/11`) | `1,0` | `1,0` | `103,5` | `0` |
| `v2` | `2026-11-16T15:08Z` | `gemini-3.5-flash` | `lexical_llm` | `4/11` | `1,0` (`11/11`) | `1,0` | `1,0` | `321,6` | `1041` / `2668` |
| `v2` | `2026-11-16T15:08Z` | `gemini-3.5-flash` | `best_llm` (`exact`) | `6/11` | `1,0` (`11/11`) | `1,0` | `1,0` | `328,9` | `327` / `651` |
| **`v3`** ([`week3_v9_response_test_v3.json`](../../../evals/results/week3_v9_response_test_v3.json)) | `2026-11-16T17:39Z` | `gemini-3.5-flash-lite` | `llm_only` | **`0/11`** | `—` | `—` | `—` | `5894,7` | `2054` / `532` |
| **`v3`** | `2026-11-16T17:39Z` | `—` | `lexical_documental` | **`0/11`** | **`1,0`** (`11/11`) | `1,0` | `1,0` | `118,4` | `0` |
| **`v3`** | `2026-11-16T17:39Z` | `gemini-3.5-flash-lite` | `lexical_llm` | **`0/11`** | **`1,0`** (`11/11`) | `1,0` | `1,0` | `5481,7` | `2369` / `510` |
| **`v3`** | `2026-11-16T17:39Z` | `gemini-3.5-flash-lite` | `best_llm` (`exact`) | **`0/11`** | **`1,0`** (`11/11`) | `1,0` | `1,0` | `5785,2` | `2369` / `548` |

**O que mudou entre `v1`, `v2` e `v3`:**
- **De `v1` para `v2`:** a correção do falso positivo em frases como *"qual dose"* / *"dose mínima"* (`RAG-01`) elevou `status_accuracy` de `0,9091` para `1,0` (`11/11`) em todas as variantes RAG, mas o endpoint `gemini-3.5-flash` apresentou alta taxa de falhas (`GoogleRateLimitError` e `503 UNAVAILABLE`) e consumo elevado de tokens de *reasoning* (~`500–600` por resposta).
- **De `v2` para `v3`:** o uso de `gemini-3.5-flash-lite` (`--chat-model gemini-3.5-flash-lite --request-delay 4.5`) zerou os erros de API (`0/44`) e reduziu o volume total de tokens de saída de `5.814` (em `10` chamadas `llm_only` do `v1`) para `532` (em `11` chamadas `llm_only` do `v3`).

---

## 5. Benchmark Diagnóstico Multi-Chunk (`N=64`, Offline)

Como o recorte `test` (`N=11`) traz especificações exatas de medicamento+concentração+forma, `exact` e `lexical` empatam em `Hit@1 = 1,0`. Para medir a capacidade real de ranqueamento quando há **3 ou mais chunks candidatos por consulta**, o benchmark [`multichunk_v9_offline.json`](../../../evals/results/multichunk_v9_offline.json) avaliou `64` casos (`35` com pistas literais + `29` com paráfrases semânticas):

| Estratégia | `Hit@1` (IC95%) | `Hit@3` | `Hit@5` | `MRR@5` (IC95%) | Pistas literais (`Hit@1`, `n=35`) | Paráfrases (`Hit@1`, `n=29`) | Latência `p50` / `p95` |
| --- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `exact` | `0,1250` (`[0,0625; 0,2031]`) | `0,7812` | `0,9844` | `0,4469` (`[0,3948; 0,5060]`) | `0,0286` (`[0,0; 0,0857]`) | `0,2414` (`[0,1034; 0,4138]`) | `102,3 ms` / `113,3 ms` |
| `lexical` (BM25 + filtro) | **`0,7969`** (`[0,6875; 0,8906]`) | **`0,9688`** | **`1,0000`** | **`0,8854`** (`[0,8255; 0,9414]`) | **`1,0000`** (`[1,0; 1,0]`) | **`0,5517`** (`[0,3793; 0,7241]`) | `102,1 ms` / `115,2 ms` |

- **Comparação pareada `exact` vs. `lexical`:** `0` vitórias do `exact`, `43` derrotas e `21` empates (**McNemar `p ≈ 2,27 × 10⁻¹³` (o JSON arredonda para `0,0`)**, delta em `Hit@1 = -0,6719`, IC95% `[-0,7812; -0,5469]`).

---

## 6. Estado Vetorial/Híbrido e Estratégia de Chaves

- **Estado registrado no Windows em 16/11/2026:** `models/gemini-embedding-2` (dimensão `3072`) já possui **`1.984` de `2.114` chunks** persistidos no Chroma local (`data/vectorstore/chroma`), com retomada automática preservada; faltam apenas **`130` chunks** (`index.json` ainda pendente) para concluir o índice e rodar `vector` e `hybrid` (inclusive no benchmark multi-chunk).
- **Suporte a chave principal + 2 fallbacks implementado:** [`src/rag/config.py`](../../../src/rag/config.py) e [`src/rag/providers.py`](../../../src/rag/providers.py) já leem `APP_GOOGLE_API_KEY`, `APP_GOOGLE_API_KEY_FALLBACK_1` e `APP_GOOGLE_API_KEY_FALLBACK_2` no `.env` (fora do Git e mascaradas com `[REDACTED]` em `error_detail()`), com failover automático em `embed_documents`/`embed_query` e `invoke`. Na retomada real, a `fallback_1` assumiu em `1024/2114` e indexou `+992` chunks até `1984/2114`; o lote seguinte (`1984 -> 2016`) esbarrou no teto diário `EmbedContentRequestsPerDayPerUserPerProjectPerModel-FreeTier` (`1.000/dia`), pois chaves em um mesmo projeto Google Cloud compartilham a mesma cota.

---

## 6.1 Revisão factual concluída em 17/11/2026

| Variante | Correção factual | Fidelidade | Completude | Suporte das citações | Erro crítico | Abstenção correta |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `llm_only` | 2/3 | 5/11 | 3/11 | 0/1 | 1/11 | 3/4 |
| `lexical_documental` | 10/10 | 10/10 | 11/11 | 7/8 | 0/11 | 4/4 |
| `lexical_llm` | 10/10 | 10/10 | 11/11 | 7/8 | 0/11 | 4/4 |
| `best_llm` | 10/10 | 8/10 | 11/11 | 6/8 | 0/11 | 4/4 |

A ausência de ID, versão e página em CAND-10 reduziu o suporte das citações nas três variantes RAG. Em `best_llm`, CAND-01 afirmou que a página não estava disponível e CAND-07 tratou a data de atualização da fonte como prazo de validade. `llm_only` trocou a forma farmacêutica em CAND-10. Essas avaliações se aplicam às respostas históricas v3. A CLI documental atual foi medida em outra execução, com 8/8 verificações automáticas de referências, 1/1 recusa clínica e 11/11 respostas iguais após v9 → v8 → v9. [Revisão humana](../../../evals/results/week3_v9_response_test_v3_human_review.json) · [CLI atual](../../../evals/results/week3_documental_cli_atual_2026-11-17.json).

---

## 7. Como Reproduzir e Próximos Passos

1. **Regerar o resumo consolidado (`v3` + histórico + multi-chunk):**
   ```bash
   uv run --no-sync --directory data-engineering python -m scripts.summarize_llm_vs_rag \
     --response-json evals/results/week3_v9_response_test_v3.json \
     --evidencias-jsonl data/releases/corpus-consolidado-v9-aprovado-2026-11-12/evidencias.jsonl \
     --baseline-runs evals/results/week3_v9_response_test.json evals/results/week3_v9_response_test_v2.json \
     --multichunk-json evals/results/multichunk_v9_offline.json \
     --output evals/results/comparativo_llm_vs_rag_v3.json
   ```
2. **Revisão humana das `44` respostas do `v3`:** concluída em 17/11/2026; consultar a consolidação. Para novas rodadas, preencher [`week3_v9_response_test_v3_review.csv`](../../../evals/reviews/week3_v9_response_test_v3_review.csv) e consolidar via `scripts/week3_review.py`.
3. **Caso o índice local esteja incompleto, concluir a indexação vetorial do `v9`:** retomar `python app.py index --release data/releases/corpus-consolidado-v9-aprovado-2026-11-12 --embedding-requests-per-minute 300` após reset de cota ou troca de chave com saldo, e então incluir `vector` e `hybrid` tanto no `week3_compare.py` quanto no `eval_multichunk_benchmark.py`.
