# SDD — Visão geral da Engenharia de Dados

**Status:** vigente  
**Escopo:** visão arquitetural da camada de dados do SUS Cidadão

## Objetivo

A Engenharia de Dados coleta fontes públicas, preserva os originais, normaliza informações e disponibiliza dados auditáveis para os consumidores do produto. A camada não depende de RAG, embeddings ou LLM.

## Arquitetura resumida

```text
Fontes oficiais
      ↓
data/raw + manifestos
      ↓
Bronze: payload original, hash e proveniência
      ↓
Silver: dados tipados e snapshots temporais
      ↓
Gold: catálogos e visões analíticas
      ↓
Consumidores do produto
```

## Responsabilidades

- preservar a fonte original e sua integridade;
- registrar origem, versão, timestamp UTC e hash;
- tolerar indisponibilidade transitória e schema drift;
- manter histórico temporal de estoque quando houver fonte oficial;
- desacoplar conectores do motor de persistência;
- não inferir disponibilidade, elegibilidade ou orientação clínica.

## Documentação normativa

- [Especificação de ingestão de dados vivos](engenharia-dados/especificacao-ingestao-dados-vivos.md) — SDD técnico e ADR de storage.
- [Levantamento de fontes](levantamento-fontes.md) — catálogo e situação das fontes oficiais.
- [Especificação funcional do MVP](especificacao-funcional-mvp.md) — requisitos do produto.

Documentos anteriores foram preservados em [engenharia-dados/historico](engenharia-dados/historico) apenas para referência; não são normativos.
