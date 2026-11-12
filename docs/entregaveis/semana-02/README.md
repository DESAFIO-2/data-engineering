# Semana 2 — Primeiro mecanismo RAG

**Objetivo:** consolidar a base de conhecimento, o pipeline de ingestão/curadoria, a indexação vetorial/lexical e os primeiros mecanismos de recuperação e consulta documental do **SUS Cidadão**.

**Foco no roadmap:** Base de conhecimento e recuperação · **Estado:** Concluído (base evoluída em releases auditados de `v5` a `v9`).

## 1. Base de conhecimento e pipeline de dados

- **Fontes principais:** F01 RENAME, F03 REME-DF e F04 Farmácia Popular, preservadas em `data/raw/` com manifestos de proveniência em `data/manifests/` e transformações em camadas (`data/bronze/`, `data/silver/`, `data/gold/`).
- **Releases consolidados:** evolução auditada desde `corpus-consolidado-v5-aprovado-2026-11-10` até `corpus-consolidado-v9-aprovado-2026-11-12` (2.114 chunks em `data/releases/`), com controle de versão de dados via DVC ([guia DVC](../../guias/guia-dvc-drive.md)).
- **Dados vivos (InfoSaúde-DF):** integração desacoplada dos painéis públicos UBS e CEAF para consulta sob demanda de estoque por código validado (`src/ingestion/infosaude_live.py`, `src/rag/consolidated_live.py`), sem inferir disponibilidade em tempo real.

## 2. Mecanismo de recuperação e chat documental

- **Estratégias de busca:** `exact` (identidade estruturada determinística), `lexical` (BM25 após filtro de apresentação), `vector` (embeddings no ChromaDB) e `hybrid` (fusão lexical/vetorial).
- **Identificação segura de apresentação:** concentração, forma farmacêutica, sal e dispositivo são tratados separadamente antes da recuperação de evidências, exigindo confirmação em ambiguidades.
- **Execução no terminal:** `app.py` com suporte a `search`, `ask`, `chat`, `index`, `eval` e `sync-live`.

## 3. Artefatos de referência

| Categoria | Artefato | Descrição |
|---|---|---|
| Arquitetura RAG | [SPEC-04: Arquitetura do RAG](../../specs/SPEC-04-rag-architecture.md) | Fluxo de recuperação e síntese |
| Dados vivos | [SPEC-05: InfoSaúde-DF no RAG](../../specs/SPEC-05-infosaude-live-api.md) | Regras de consulta aos painéis UBS e CEAF |
| Vetor | [SPEC-06: RAG híbrido com ChromaDB](../../specs/SPEC-06-chromadb-vectorstore.md) | Indexação e validação de índice vetorial |
| Curadoria | [SPEC-07: Corpus e curadoria](../../specs/SPEC-07-corpus-curation.md) | Regras de extração, normalização e revisão |
| Publicação | [SPEC-08: Revisão e publicação](../../specs/SPEC-08-publication.md) | Governança de publicação de releases |
| Híbrido v7 | [SPEC-09: RAG híbrido v7](../../specs/SPEC-09-rag-hibrido-v7.md) | Especificação da frente híbrida na v7 |
| Índice e demos | [Índice consolidado v5](../../demos/indice-consolidado-v5.md) | Referência do fluxo consolidado v5 |
| Demonstração | [Demo chat v5](../../demos/demo-chat-v5.md) | Comparativo antes/depois sem chave |
| Demonstração | [Demo chat v5 com modelo](../../demos/demo-chat-v5-modelo.md) | Geração com Gemini sobre o release v5 |
| Demonstração | [Demo busca progressiva e estoque](../../demos/demo-busca-progressiva-estoque.md) | Fluxo de esclarecimento e consulta InfoSaúde |
| Validação | [Validação chat v5](../../demos/validacao-chat-v5.md) | Verificações do chat consolidado v5 |
| Regressão | [Regressão liraglutida](../../demos/regressao-liraglutida.md) | Caso de regressão de dispositivo/concentração |
| Relatórios v6–v9 | [Auditoria corpus v6](../../reports/v6/relatorio-auditoria-corpus-v6.md) | Auditoria de qualidade e alinhamento |
| Relatórios v6–v9 | [Validação recuperação v9 dev](../../reports/v9/validacao-recuperacao-v9-dev.md) | Gate de recuperação no release v9 |
