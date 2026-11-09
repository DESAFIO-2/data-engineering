# Especificação de arquitetura — Engenharia de Dados

**Objetivo:** coletar fontes públicas, preservar originais, normalizar informações e disponibilizar dados auditáveis aos consumidores do produto, sem dependência de RAG, embeddings ou LLM.

**Estado:** vigente · **Escopo:** visão arquitetural da camada de dados do SUS Cidadão.

## Etapa 1 — Preservar fontes e proveniência

### Objetivo

Manter evidência recuperável da origem dos dados processados.

### Requisitos ou regras

- Preservar fonte original e integridade.
- Registrar origem, versão, timestamp UTC e hash.
- Tolerar indisponibilidade transitória e mudanças de schema.
- Histórico temporal de estoque é mantido quando existir fonte oficial.

### Critérios de conclusão

- Um dado processado pode ser relacionado à fonte, versão, coleta e hash correspondentes.

## Etapa 2 — Processar em camadas

### Objetivo

Organizar a transformação desde o payload original até visões consumíveis.

### Requisitos ou regras

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

- Bronze preserva payload e metadados; Silver contém registros tipados e snapshots; Gold contém dados derivados para consumo.
- Desacoplar conectores do motor de persistência.
- Não inferir disponibilidade, elegibilidade ou orientação clínica.

### Critérios de conclusão

- As camadas e responsabilidades estão refletidas no fluxo de dados; Gold é derivada e não substitui a origem auditável.

## Etapa 3 — Integrar especificações relacionadas

### Objetivo

Usar as especificações detalhadas corretas para cada tipo de requisito.

### Requisitos ou regras

- [Especificação de ingestão de dados vivos](SPEC-01-eda-and-sync.md): SDD técnico e ADR de storage.
- [Levantamento de fontes](../levantamento-fontes.md): catálogo e situação das fontes oficiais.
- [Especificação funcional do MVP](SPEC-02-functional-mvp.md): requisitos e comportamento do produto.
- Documentos anteriores foram preservados em `engenharia-dados/historico` apenas para referência; não são normativos.

### Critérios de conclusão

- Decisões arquiteturais detalhadas são consultadas no SDD técnico, fontes no levantamento e comportamento do produto na especificação funcional.
