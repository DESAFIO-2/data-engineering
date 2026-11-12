# Baseline exploratório de recuperação v6 — 11/11/2026

> **Errata posterior:** o avaliador consolidado lia o JSONL UTF-8 sem especificar `encoding` no Windows. Isso corrompia acentos das perguntas e reduzia artificialmente as métricas abaixo. Elas documentam a execução histórica, mas não medem de forma confiável a qualidade da recuperação. A causa e o novo diagnóstico exploratório v7 estão em [validação da v7](../v7/validacao-recuperacao-v7-dev.md).

O conjunto `evals/datasets/consolidated_v6_agent_reviewed.jsonl` tem 119 perguntas sintéticas (91 `dev`, 28 `test`) marcadas `agent_reviewed`, não `reviewed` por Jhiovana. Estes números **não são benchmark oficial** nem autorização para vetorizar; servem para localizar defeitos na busca e na referência esperada.

Com o release `corpus-consolidado-v6-auditado-2026-11-11` (fingerprint `5f0709aa18feb2b9a9fa46bd307100574ddc5541a1db051d9ce6946418575f51`) e hash do dataset `7b0316d6161dab24bda3522d71d1e050d80c764a18df17b5e1470cb967608754`, `exact` e `lexical` tiveram os mesmos números em `dev`: 91 casos, 76 positivos esperados, Hit@5 e MRR@5 de **0,4605**, acerto de status de **0,5495**. Por fonte, Hit@5 lexical: F01 **0,3448** (29 casos), F03 **0,1000** (20), F04 **0,8519** (27). O contador `reviewed_cases` do avaliador é zero, coerente com o status `agent_reviewed`.

Há 41 casos positivos sem evidência esperada no top 5; em muitos a busca retorna `ambiguous` ou `not_in_scope` antes de ranquear. Exemplos: `C-F01-001` (clofazimina 100 mg, ambíguo), `C-F03-001` (enoxaparina 60 mg, fora do escopo) e `C-F04-023` (metformina prolongada: status `matched`, mas ID esperado diferente do recuperado). Antes de alterar o retriever, conferir se cada pergunta e ID esperado realmente representam uma apresentação documental única. Embeddings não corrigirão um candidato eliminado por filtro estruturado.

Comandos reproduzíveis:

```powershell
.venv\Scripts\python.exe app.py eval --release data/releases/corpus-consolidado-v6-auditado-2026-11-11 --dataset evals/datasets/consolidated_v6_agent_reviewed.jsonl --output .test-tmp-v6-lexical-dev.json --strategy lexical --split dev --documental
.venv\Scripts\python.exe app.py eval --release data/releases/corpus-consolidado-v6-auditado-2026-11-11 --dataset evals/datasets/consolidated_v6_agent_reviewed.jsonl --output .test-tmp-v6-exact-dev.json --strategy exact --split dev --documental
```

Próximo gate: revisar perguntas/IDs por família; distinguir falha de extração, normalização, ambiguidade real e erro da referência; corrigir sem usar o split `test` para calibração. Reportar novos números apenas após essa revisão.
