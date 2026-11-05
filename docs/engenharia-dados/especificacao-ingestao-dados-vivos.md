# SDD — Ingestão de dados vivos e armazenamento temporal

**Projeto:** SUS Cidadão — piloto Farmácias de Alto Custo SES-DF  
**Status:** EM ANÁLISE  
**Versão:** 1.1 — alinhada à implementação local

Esta é a especificação técnica normativa da camada de Engenharia de Dados. A visão resumida para o projeto está em [../sdd-arquitetura-engenharia-dados.md](../sdd-arquitetura-engenharia-dados.md).

## 1. Objetivo e escopo

Esta especificação define a camada de Engenharia de Dados para fontes públicas voláteis, sem dependência de RAG, embeddings ou lógica de resposta. O pipeline preserva a resposta original, permite reprocessamento, controla mudanças de schema e mantém o histórico de estoque.

Princípios: fonte auditável, idempotência por hash, timestamps em UTC, separação Bronze/Silver/Gold e conectores desacoplados do mecanismo de persistência.

## 2. Domínio do piloto

- **Medicamento:** `principio_ativo`, `concentracao` e `forma`, com identificador estável da fonte quando existir.
- **Farmácia/polo:** `polo`, `endereco` e `regiao_administrativa`; polos previstos: Asa Sul, Ceilândia e Gama.
- **Snapshot de estoque:** `id_medicamento`, `id_farmacia`, `data_referencia` UTC, `quantidade` não negativa e status `DISPONIVEL`, `ZERADO` ou `BLOQUEADO`. Snapshots são append-only.

## 3. Arquitetura Medallion

### Bronze — Raw Zone

Preserva payload JSON/XML e metadados em:

```text
data/bronze/{source_name}/YYYY/MM/DD/{payload_sha256}.json
```

O envelope contém `ingestion_id`, `collected_at` UTC, `source_url`, `http_status` e `payload_sha256`. Hashes repetidos geram reconfirmação sem sobrescrever o artefato.

### Silver — Standardized Zone

Valida e tipa registros com Pydantic v2. O modelo de estoque é temporal e permite recuperar o registro mais recente por medicamento e farmácia. Schema drift gera warning estruturado com campos omitidos/desconhecidos; campos obrigatórios inválidos impedem apenas a promoção daquele registro.

### Gold — Business Zone

Camada derivada e recriável, com views de disponibilidade atual por polo, medicamentos zerados, idade da última observação e taxa de ruptura (`ZERADO` / observados). Não recebe escrita manual.

## 4. Contratos de ingestão

`BaseConnector` define `fetch()`, `validate_schema()` e `generate_metadata()`. Também fornece retry exponencial para 429, 500, 502, 503 e 504, além de checkpoint JSON por conector para cursor/página. `validate()` permanece como alias de compatibilidade.

### InfoSaúde DF

O `InfoSaudeDFConnector` prioriza resposta JSON do painel de estoque da SES-DF, sem seletores DOM. Aceita endpoint configurável e oferece fallback por token efêmero para endpoints Power BI. A resposta mínima pode ser uma lista ou conter `data`, `items`, `value` ou `records`.

## 5. Persistência e Repository Pattern

`StorageRepository` expõe `save_bronze(source_name, payload, metadata)`, `save_silver_snapshot(snapshot)` e `get_latest_stock(medicamento, farmacia)`. `FileStorageRepository` é o adaptador inicial; futuros adaptadores DuckDB ou PostgreSQL não exigem mudanças nos conectores.

## 6. ADR-001 — motor de armazenamento

**Status: EM ANÁLISE.**

| Opção | Benefícios | Limitações | Avaliação inicial |
|---|---|---|---|
| DuckDB + Parquet | analítico, portátil e baixo custo | concorrência operacional limitada | forte candidata ao protótipo |
| SQLite | simples, transacional e sem servidor | menor capacidade analítica | adequada a metadados/fixtures |
| PostgreSQL | concorrência e governança maduras | exige infraestrutura | candidata para produção |
| Lakehouse em arquivos | histórico barato e imutável | catálogo e governança adicionais | candidata para escala |

Decisão provisória: manter o adaptador local baseado em arquivos e comparar DuckDB/PostgreSQL com carga real do piloto.

## 7. Pipeline documental executado

`scripts/pipeline.py` processa os PDFs do manifesto. Na execução inicial foram processados 5 documentos e 459 páginas. Bronze contém envelopes JSON, Silver contém registros JSONL por página e Gold contém `document_catalog.json`. O pipeline produz texto e proveniência para recuperação posterior, mas ainda não gera embeddings ou chama LLM.

## 8. Critérios de aceite

- payload original recuperável por hash e data;
- coleta resiliente a falhas transitórias;
- metadados com UUID, UTC, URL, status HTTP e SHA-256;
- deduplicação de payloads idênticos;
- snapshots Silver tipados e temporais;
- warnings de schema drift sem perda silenciosa;
- conector InfoSaúde sem scraping visual;
- persistência substituível via Repository Pattern;
- testes unitários passando.
