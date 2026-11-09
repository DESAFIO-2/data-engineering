# Documentação do projeto

**Objetivo:** localizar a documentação técnica e normativa do projeto, mantendo claro o estado de cada informação.

## 1. Especificações normativas

- [Especificação funcional do MVP](specs/SPEC-02-functional-mvp.md) — escopo, comportamentos, privacidade e aceite.
- [Arquitetura da Engenharia de Dados](specs/SPEC-00-architecture.md) — visão das camadas e responsabilidades.
- [Ingestão de dados vivos](specs/SPEC-01-eda-and-sync.md) — contratos técnicos e armazenamento temporal; ADR de storage permanece em análise.

## 2. Arquitetura, corpus e fontes

- [Arquitetura do RAG ampliado](specs/SPEC-04-rag-architecture.md)
- [Corpus e curadoria](specs/SPEC-07-corpus-curation.md)
- [Fontes complementares](fontes-complementares.md)
- [Levantamento inicial de fontes](levantamento-fontes.md)
- [InfoSaúde-DF no RAG](specs/SPEC-05-infosaude-live-api.md)
- [RAG híbrido com ChromaDB](specs/SPEC-06-chromadb-vectorstore.md)

## 3. Avaliação e publicação

- [Avaliação documental de RAG](specs/SPEC-03-golden-dataset-and-evaluation.md)
- [Revisão e publicação do corpus](specs/SPEC-08-publication.md)

## 4. Padrão editorial

- Cada documento começa com um título descritivo e uma linha **Objetivo**.
- Seções de segundo nível são numeradas em sequência; especificações usam etapas numeradas quando a ordem de entendimento ou execução é relevante.
- Quando aplicável, etapas de especificação usam **Objetivo**, **Requisitos ou regras** e **Critérios de conclusão**.
- Especificações e catálogos mantêm sua forma própria. Não se converte intenção em resultado nem observação em requisito.
- Usar Markdown consistente: níveis de título sem saltos, tabelas com cabeçalho, listas paralelas, comandos em blocos cercados e links relativos entre documentos.
- Declarar dependências, decisões em aberto, limitações e estado de revisão onde forem relevantes. Não preencher lacunas com decisões presumidas.
