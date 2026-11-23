# Status e Checklist — Integração RAG `v10` Normalizado

**Data:** 2026-11-23  
**Branch:** `feat/integracao-rag-v10`  
**Commits da entrega:** `6aaa77d` (`PR1: F1–F4 + F6`) · `7cc9cb5` (`PR2: F7–F8`) · `2a9a521` (`PR3: aprovação v10 + R1`) · `74abb1e` (`índice vetorial v10 no DVC`) · `0ec6730` (`Etapa 2 vector/hybrid + dev exploratório`) · `ff1421b` (`modo documental sem chamadas ao Google`)  
**Release padrão atual:** `data/releases/corpus-consolidado-v10-aprovado-2026-11-17`  
**Release fingerprint (`release.json` SHA-256):** `7e93955247de1ded77121a00bf1b14c320d782cf21c4d9e9464d4e8f3e24d179`  
**Content fingerprint (`v10`):** `b7c41f04be50102ee4550647f8d9109af42c2cd1d07ef9cbeb78d608c240ac92`

---

## 1. Resumo Consolidado da Entrega `v10`

### Aprovação, Governança, Dados e DVC (`F8`, `H2`, `H3`, `DVC`)
- **Aprovação humana do `v10` (`F8`):** registrado [`revisao-v10-normalizada-jhiovana.md`](revisao-v10-normalizada-jhiovana.md) e gerado o release imutável `corpus-consolidado-v10-aprovado-2026-11-17` (`1.727` apresentações, `2.114` ocorrências) e os `2.114` chunks `one-evidence-v3` (`chunks_sha256`: `d2f415af483ea6700266f8a255db1880d159e0cc140723dbadc7f87f1cb21570`).
- **Fechamento da Semana 3 (`H2` e `H3`):** `44/44` linhas de `evals/reviews/week3_v9_response_test_v3_review.csv` assinadas como `reviewer = "Jhiovana"`, reconsolidadas em `evals/results/week3_v9_response_test_v3_human_review.json`.
- **Índice vetorial completo (`models/gemini-embedding-2`, dimensão `3072`):** **`2.114 / 2.114`** chunks indexados e validados offline em `data/vectorstore/chroma/consolidated/12d2ba555f94ba1a1cd08fa0`.
- **DVC sincronizado no Google Drive:** release aprovado (`corpus-consolidado-v10-aprovado-2026-11-17.dvc`), chunks `v3` (`data/derived/chunks/corpus-consolidado-v10-aprovado-2026-11-17.dvc`) e índice vetorial (`data/vectorstore/chroma/consolidated/12d2ba555f94ba1a1cd08fa0.dvc`, `8 files pushed`).

### Correções Técnicas no RAG, Avaliação e Runtime (`PR3`)
- **Runtime (`src/rag/consolidated.py`):** suporte a `form_alternatives` no filtro de forma, inclusão de `%`, `U`, `mEq` e `L` no guardrail de concentração, tratamento de sufixo `(liberação de ...)` em `strength_core()` (ex.: rivastigmina) e desambiguação de insumos (`supply`) por forma/volume.
- **Vínculos UBS (`R1`):** `src/rag/consolidated_chat.py` carrega `data/mappings/ubs/<release_fingerprint>.json` (`7e939552...json`) com fallback seguro (`{}`), validado ponta a ponta com InfoSaúde-DF ao vivo.
- **Avaliação e CLI:** corrigido cálculo de `critical_confusions` em `scripts/eval_v10_dev_comparison.py`, ajustado `_pres_key()` em `scripts/eval_multichunk_benchmark.py`, habilitado `v10` e `aliases` em `src/rag/consolidated_evaluation.py` e `src/rag/consolidated_cli.py`, e parametrizados `--source` e `--release` em `scripts/week3_ragas.py`.
- **Qualidade de código:** `ruff format --check .`, `ruff check .`, `mypy src tests` e `pytest -m "not dvc"` (`388 passed, 1 skipped`; relatório complementar em [`avaliacoes-v10-2026-11-19.md`](avaliacoes-v10-2026-11-19.md)).

---

## 2. Resultados Finais de Avaliação (`v10`)

### 2.1 Benchmark Consolidado (`evals/datasets/consolidated_v10_reviewed.jsonl`, `split="test"`, `n=28`)

Artefatos: `evals/results/v10_aprovado_consolidated_test_{exact,lexical,vector,hybrid}.json`.

| Estratégia | Hit@1/3/5 (`24` pos.) | MRR@5 | Status Acc (`28`) | Pres. Acc | Confusões Críticas | Abstenção (`4` neg.) | Citações (`29`) | p50 | p95 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **`exact`** | `1,0000` | `1,0000` | `1,0000` | `1,0000` | `0` | `1,0000` | `1,0000` | `92,9 ms` | `119,9 ms` |
| **`lexical` (BM25)** | `1,0000` | `1,0000` | `1,0000` | `1,0000` | `0` | `1,0000` | `1,0000` | `96,3 ms` | `124,3 ms` |
| **`vector` (`gemini-embedding-2`)** | `1,0000` | `1,0000` | `1,0000` | `1,0000` | `0` | `1,0000` | `1,0000` | `661,7 ms` | `914,0 ms` |
| **`hybrid` (RRF `k=60`)** | `1,0000` | `1,0000` | `1,0000` | `1,0000` | `0` | `1,0000` | `1,0000` | `650,0 ms` | `2.257,9 ms` |

### 2.2 Benchmark Multi-Chunk (`evals/datasets/multichunk_v10_benchmark.jsonl`, `split="test"`, `n=32`)

Artefatos: `evals/results/v10_aprovado_multichunk_test.json` e `evals/results/v10_aprovado_multichunk_test.checkpoint.json`.

| Estratégia | Hit@1 Geral (`32`) | Hit@3 | Hit@5 | MRR@5 (IC 95%) | `literal_clue` (`16`) | `semantic_paraphrase` (`16`) | Confusões Críticas | Erros | p50 | p95 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **`exact`** | `12,5%` (`4/32`) | `90,6%` | `100%` | `0,4714` `[0,40–0,56]` | `0,0%` (`0/16`) | `25,0%` (`4/16`) | `0` | `0` | `224,9 ms` | `253,9 ms` |
| **`lexical` (BM25)** | `78,1%` (`25/32`) | `100%` | `100%` | `0,8802` `[0,80–0,95]` | **`100,0%`** (`16/16`) | `56,25%` (`9/16`) | `0` | `0` | `223,1 ms` | `255,9 ms` |
| **`vector`** | `84,4%` (`27/32`) | `100%` | `100%` | `0,9115` `[0,84–0,98]` | `81,25%` (`13/16`) | `87,5%` (`14/16`) | `0` | `0` | `704,3 ms` | `810,5 ms` |
| **`hybrid` (RRF)** | **`93,75%`** (`30/32`) | **`100%`** | **`100%`** | **`0,9635`** `[0,91–1,00]` | **`93,75%`** (`15/16`) | **`93,75%`** (`15/16`) | **`0`** | **`0`** | `898,5 ms` | `2.601,0 ms` |

- **Comparações pareadas:**
  - `hybrid` vs. `lexical` (geral, `n=32`): `6` vitórias, `1` derrota, `25` empates (`+15,6 pp` em `Hit@1`, McNemar `p = 0,125`; **`+0,0833` em `MRR@5`, IC 95% `[+0,0052, +0,1667]`**).
  - `hybrid` vs. `lexical` (`semantic_paraphrase`, `n=16`): **`6` vitórias, `0` derrotas**, `10` empates (`+37,5 pp` em `Hit@1`, **McNemar `p = 0,03125`**; `+0,1979` em `MRR@5` `[+0,0938, +0,3333]`).
  - `hybrid` vs. `vector` (geral, `n=32`): `3` vitórias, `0` derrotas, `29` empates (`+9,38 pp` em `Hit@1`, `p = 0,25`).
  - `hybrid` vs. `exact` (geral, `n=32`): `26` vitórias, `0` derrotas (`+81,25 pp` em `Hit@1`, `p = 2,98e-08`).

### 2.3 Regressão Ponta a Ponta no Chat (`v10`, `--documental --strategy lexical` e `--strategy hybrid`)

- `Onde retiro cabergolina 0,5 mg comprimido na REME-DF?` → **PASS** (`3` registros F03 p. 19 com canais distintos e trava literal de síntese ativa).
- `amoxicilina 500 mg comprimido REME-DF` → **PASS** (`form_alternatives`: `cápsula ou comprimido`, F03 p. 15).
- `rivastigmina 9 mg adesivo transdérmico REME-DF` → **PASS** (`strength_core`: `9 mg (liberação de 4,6 mg/24 h)`, F03 p. 52, CEAF).
- `metformina 850 mg comprimido estoque UBS` (+ `Ceilândia`) → **PASS** (bloqueio em `--documental`; em modo live, vínculo `R1` código `90226` consultou InfoSaúde-DF com `18` farmácias com saldo positivo em Ceilândia e alerta automático `> 48 horas`).
- `polidocanol 2% REME-DF` → **PASS** (guardrail `%` retornou `Concentração não localizada`).

### 2.4 Comparativo de Respostas LLM × RAG (`evals/results/week3_v10_response_test.json`) + RAGAS 0.4.3 (`evals/results/week3_v10_ragas_test.json`)

Dataset portado para o `v10`: `evals/datasets/week3_v10_test_reviewed.jsonl` (`11` casos revisados, `100%` dos `evidence_id`, `medicine_id` e páginas validados; `git_dirty: false`, `chat_model: gemini-3.5-flash-lite`, `best_strategy: hybrid`).

| Cenário | Hit@1/3/5 (`7` pos.) | Status (`11`) | Erros API | p95 | RAGAS Context Recall (`7/7`) | RAGAS Context Precision (`7/7`) | RAGAS Faithfulness (`7/7`) | RAGAS Answer Relevancy (`7/7`) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **`llm_only`** | N/A | N/A | `0/11` | `6.819 ms` | N/A | N/A | N/A | `0,0000` |
| **`lexical_documental`** | `1,0000` | **`11/11`** | `0/11` | `389 ms` | `1,0000` | `1,0000` | **`0,6976`** | `0,8413` |
| **`lexical_llm`** | `1,0000` | **`11/11`** | `0/11` | `6.002 ms` | `1,0000` | `1,0000` | `0,5524` | **`0,9458`** |
| **`best_llm` (`hybrid`)** | `1,0000` | **`11/11`** | `0/11` | `6.987 ms` | `1,0000` | `1,0000` | `0,5214` | `0,6717` |

- **Correções confirmadas no teste fechado:** `W3-TEST-CAND-11` (*"Qual dose de varfarina devo tomar?"*) passou a `unsupported` (`11/11` de acerto de status) e `W3-TEST-CAND-10` retornou ambas as evidências de ácido fólico na F03 p. 12.
- **Notas metodológicas e achados de auditoria:**
  - Gerador e juiz RAGAS utilizaram `gemini-3.5-flash-lite` (limitação declarada), com referência formada pelos excertos de `expected_evidence_ids`.
  - `lexical_documental` obteve a maior `Faithfulness` (`0,6976`); nos modos LLM, frases extras de escopo/recorte derrubaram `Faithfulness` e acionaram penalização `noncommittal` em `2/7` casos de `Answer Relevancy` em `best_llm`.
  - Na leitura qualitativa das respostas LLM, foram registradas 3 imprecisões leves de redação (não presentes no modo documental): `CAND-07` (`lexical_llm` escreveu *"vigência até 2026-08-31"* em vez de data de atualização), `CAND-01` (`best_llm` afirmou não ter o número da página) e `CAND-04` (`lexical_llm` misturou compra IHBDF / Farmácia Ambulatorial HBDF).

---

## 3. Checklist da Entrega `v10` (Concluído)

### Etapa 1 — Destravar os últimos 34 chunks vetoriais
- [x] **1.1** Chave GCP rotacionada e cota liberada.
- [x] **1.2** Indexação concluída (`2.114 / 2.114` chunks validados, commit `74abb1e`, `8 files pushed` no DVC).

### Etapa 2 — Fechar as avaliações `vector` e `hybrid` (Métodos de Recuperação)
- [x] **2.1** Avaliado `vector` no consolidado `test` (`1,0000`, `0` confusões críticas).
- [x] **2.2** Avaliado `hybrid` no consolidado `test` (`1,0000`, `0` confusões críticas).
- [x] **2.3** Concluído benchmark multi-chunk com as 4 estratégias (`hybrid` = `93,75%` Hit@1, `0,9635` MRR@5, `p = 0,03125` em paráfrases vs. `lexical`).

### Etapa 3 — Testar e Avaliar o RAG no Chat (`v10`)
- [x] **3.1** Regressão validada em `--documental --strategy lexical`.
- [x] **3.2** Regressão validada em `--strategy hybrid` + estoque vivo InfoSaúde-DF.
- [x] **3.3** Todas as 5 consultas-chave de regressão aprovadas (`cabergolina`, `amoxicilina`, `rivastigmina`, `metformina 850 mg UBS Ceilândia`, `polidocanol 2%`).

### Etapa 4 — Avaliação Comparativa de Respostas + RAGAS (`v10`)
- [x] **4.1** Executado `week3_compare.py` no `v10` (`44/44` sem erros, `11/11` status, `git_dirty: false`).
- [x] **4.2** Executado RAGAS 0.4.3 oficial (`evals/results/week3_v10_ragas_test.json`, `7/7` pontuados por métrica elegível).
- [x] **4.3** Resultados finais commitados e enviados para `origin/feat/integracao-rag-v10`, prontos para PR em `main`.

---

## 4. Próximas Frentes (Pós-Merge do `v10`)

1. **Branch `refactor/repo-organization`:** organização estrutural do repositório, `.gitattributes` (LF) e paths POSIX.
2. **PR seguinte de indexação e corpus (`v11`):**
   - `--seed-index` em `build_index()` (reuso incremental por `sha256(text)` validando `embedding_model`, `embedding_api`, `output_dimensionality` e `task_type`).
   - Coleção Chroma separada para `C01–C17`, Portaria 117/2026 (`F09`) e Exames (`exame_acesso_sisreg`, `exame_documentacao`, `exame_preparo`) com Parent-Child e pré-filtro por metadados.
3. **Pendências paralelas de curadoria (`H4`–`H7`):** revisão de `dev` drafts (`H4`), curadoria de `C01–C17` (`H5`), ampliação de vínculos UBS além da metformina (`H6`) e parecer clínico/farmacêutico (`H7`).
