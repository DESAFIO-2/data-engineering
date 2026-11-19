# Semana 3 — Respostas baseadas em evidências (LLM × RAG)

**Objetivo:** comparar objetivamente LLM sem contexto (`llm_only`), resposta documental sem LLM (`lexical_documental`) e síntese com LLM sobre evidências recuperadas (`lexical_llm` e `best_llm`), medindo recuperação, métricas complementares (RAGAS, Precision@3, precisão micro/recall macro) e revisão humana.

**Foco no roadmap:** Comparação LLM × RAG · **Estado:** Concluído (oito cenários executados em desenvolvimento e no teste congelado + métricas RAGAS medidas; revisão factual humana das 44 respostas v3 validada por Jhiovana e reconsolidada em 18/11/2026).

## 1. Protocolo e cenários comparados

- **Release congelado:** `data/releases/corpus-consolidado-v9-aprovado-2026-11-12` (2.114 chunks).
- **Matriz de busca (4 cenários):** `exact`, `lexical`, `vector`, `hybrid` (`top_k=5`, mesmo filtro estruturado de apresentação).
- **Matriz de resposta (4 cenários):** `llm_only` (Gemini sem evidência), `lexical_documental` (resposta documental sem LLM), `lexical_llm` (síntese sobre busca lexical) e `best_llm` (síntese sobre busca exata).

## 2. Artefatos do entregável

| Tipo | Artefato | Descrição |
|---|---|---|
| Relatório principal | [Semana 3: LLM × RAG na v9](../../reports/v9/semana3-llm-rag-v9.md) | Protocolo completo, resultados de desenvolvimento/teste, RAGAS e pendências |
| Revisão do teste | [Folha de revisão do teste v9](../../reports/v9/semana3-v9-test-review-template.md) | Conferência técnica nas fontes oficiais para o conjunto de teste |
| Executor comparativo | [`scripts/week3_compare.py`](../../../scripts/week3_compare.py) | Execução das matrizes de busca e resposta |
| Executor RAGAS | [`scripts/week3_ragas.py`](../../../scripts/week3_ragas.py) | Medição de Faithfulness, Answer Relevancy, Context Recall e Context Precision |
| Consolidador humano | [`scripts/week3_review.py`](../../../scripts/week3_review.py) | Validação e consolidação da revisão factual humana por hash |
| Lock RAGAS | [`scripts/week3_ragas.py.lock`](../../../scripts/week3_ragas.py.lock) | Dependências travadas (`ragas==0.4.3`, `langchain-community==0.3.31`, `langchain-google-genai==2.1.12`) |
| Datasets | [`evals/datasets/`](../../../evals/datasets) | Conjuntos `week3_v9_dev_draft.jsonl` e conjunto de teste congelado |
| Resultados | [`evals/results/week3_v9_ragas_test.json`](../../../evals/results/week3_v9_ragas_test.json) | Escores, referências e agregados RAGAS no teste congelado |
| Resultados | [`evals/results/week3_v9_complementary_metrics_test.json`](../../../evals/results/week3_v9_complementary_metrics_test.json) | Métricas complementares de recuperação no teste congelado |
| Resultados | [`evals/results/week3_v9_retrieval_test.json`](../../../evals/results/week3_v9_retrieval_test.json) | Resultados de busca no conjunto de teste |
| Resultados | [`evals/results/week3_v9_response_test.json`](../../../evals/results/week3_v9_response_test.json) | Respostas geradas nos 4 cenários de teste |

## 3. Pendências abertas para fechamento

- Concluir e consolidar a revisão factual humana das 44 respostas do conjunto de teste via `scripts/week3_review.py`.
- Registrar a decisão final de recomendação de arquitetura (lexical/documental vs. síntese LLM) após a revisão humana.
