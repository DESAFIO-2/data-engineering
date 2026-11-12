# Documentação do projeto

**Objetivo:** localizar os entregáveis semanais, especificações normativas, relatórios técnicos e guias operacionais do projeto **SUS Cidadão**, mantendo claro o estado de cada informação.

## 1. Entregáveis por semana (Challenge 2)

- [Índice geral dos entregáveis](entregaveis/README.md) — visão consolidada do roadmap de 7 semanas do Challenge 2.
- [Semana 1 — Definições do projeto](entregaveis/semana-01/README.md) — problema, stakeholders, riscos, regras de negócio e métricas.
- [Semana 2 — Primeiro mecanismo RAG](entregaveis/semana-02/README.md) — base de conhecimento, curadoria, releases v5–v9 e recuperação.
- [Semana 3 — Respostas baseadas em evidências](entregaveis/semana-03/README.md) — comparação LLM × RAG, métricas RAGAS e revisão factual.
- [Semana 4 — Primeiro sistema multiagentes](entregaveis/semana-04/README.md) — planejado.
- [Semana 5 — Agentes multimodais](entregaveis/semana-05/README.md) — planejado.
- [Semana 6 — Aplicação funcional](entregaveis/semana-06/README.md) — planejado.
- [Semana 7 — Relatório final + apresentação](entregaveis/semana-07/README.md) — planejado.

## 2. Especificações normativas

- [Especificação funcional do MVP](specs/SPEC-02-functional-mvp.md) — escopo, comportamentos, privacidade e aceite.
- [Arquitetura da Engenharia de Dados](specs/SPEC-00-architecture.md) — visão das camadas e responsabilidades.
- [Ingestão de dados vivos](specs/SPEC-01-eda-and-sync.md) — contratos técnicos e armazenamento temporal; ADR de storage permanece em análise.

## 3. Arquitetura, corpus e fontes

- [Arquitetura do RAG ampliado](specs/SPEC-04-rag-architecture.md)
- [Corpus e curadoria](specs/SPEC-07-corpus-curation.md)
- [Fontes complementares](fontes/fontes-complementares.md)
- [Levantamento inicial de fontes](fontes/levantamento-fontes.md)
- [InfoSaúde-DF no RAG](specs/SPEC-05-infosaude-live-api.md)
- [RAG híbrido com ChromaDB](specs/SPEC-06-chromadb-vectorstore.md)
- [RAG híbrido v7](specs/SPEC-09-rag-hibrido-v7.md)
- [CEP → UBS e privacidade](specs/SPEC-10-cep-ubs-privacidade.md) — frente separada.

## 4. Avaliação, relatórios e publicação

- [Avaliação documental de RAG](specs/SPEC-03-golden-dataset-and-evaluation.md)
- [Semana 3: comparação LLM × RAG na v9](reports/v9/semana3-llm-rag-v9.md) — protocolo, resultados de desenvolvimento/teste, RAGAS e pendências de validação.
- [Revisão e publicação do corpus](specs/SPEC-08-publication.md)
- [Guia de métricas do RAG](../src/rag/README.md)
- Demais auditorias, validações e revisões de releases v6–v9 estão catalogadas no [índice de relatórios](reports/README.md).

## 5. Demonstrações e guias operacionais

- [Índice consolidado v5](demos/indice-consolidado-v5.md)
- [Demonstração chat v5 (antes/depois)](demos/demo-chat-v5.md)
- [Demonstração chat v5 com Gemini](demos/demo-chat-v5-modelo.md)
- [Demonstração busca progressiva e estoque](demos/demo-busca-progressiva-estoque.md)
- [Validação do chat v5](demos/validacao-chat-v5.md)
- [Regressão validada — Liraglutida](demos/regressao-liraglutida.md)
- [Guia de versionamento de dados (DVC + Drive)](guias/guia-dvc-drive.md)

## 6. Padrão editorial

- Cada documento começa com um título descritivo e uma linha **Objetivo**.
- Seções de segundo nível são numeradas em sequência; especificações usam etapas numeradas quando a ordem de entendimento ou execução é relevante.
- Quando aplicável, etapas de especificação usam **Objetivo**, **Requisitos ou regras** e **Critérios de conclusão**.
- Especificações e catálogos mantêm sua forma própria. Não se converte intenção em resultado nem observação em requisito.
- Usar Markdown consistente: níveis de título sem saltos, tabelas com cabeçalho, listas paralelas, comandos em blocos cercados e links relativos entre documentos.
- Declarar dependências, decisões em aberto, limitações e estado de revisão onde forem relevantes. Não preencher lacunas com decisões presumidas.
