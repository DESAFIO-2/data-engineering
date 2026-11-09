# Especificação técnica — Ingestão de dados vivos e armazenamento temporal

**Objetivo:** definir a camada de Engenharia de Dados para fontes públicas voláteis, preservando respostas originais, permitindo reprocessamento, controlando mudanças de schema e mantendo histórico de estoque, sem dependência de RAG, embeddings ou lógica de resposta.

**Projeto:** SUS Cidadão — piloto Farmácias de Alto Custo SES-DF
**Estado:** EM ANÁLISE · **Versão:** 1.1 — alinhada à implementação local
Visão resumida: [SDD de arquitetura da Engenharia de Dados](SPEC-00-architecture.md).

## Etapa 1 — Fixar domínio do piloto

### Objetivo

Definir as entidades e atributos mínimos para o recorte de estoque.

### Requisitos ou regras

- Medicamento: `principio_ativo`, `concentracao`, `forma` e identificador estável da fonte quando houver.
- Farmácia/polo: `polo`, `endereco`, `regiao_administrativa`; polos previstos: Asa Sul, Ceilândia e Gama.
- Snapshot: `id_medicamento`, `id_farmacia`, `data_referencia` UTC, `quantidade` não negativa e status `DISPONIVEL`, `ZERADO` ou `BLOQUEADO`.
- Snapshots são append-only.

### Critérios de conclusão

- Registros do piloto podem ser identificados por medicamento, polo e instante de referência; quantidade e status obedecem ao domínio declarado.

## Etapa 2 — Preservar a resposta original na Bronze

### Objetivo

Manter payload recuperável e deduplicável, sem sobrescrever evidência de coleta.

### Requisitos ou regras

- Caminho: `data/bronze/{source_name}/YYYY/MM/DD/{payload_sha256}.json`.
- Envelope: `ingestion_id`, `collected_at` UTC, `source_url`, `http_status`, `payload_sha256`.
- Hash repetido gera reconfirmação sem sobrescrever o artefato.
- Princípios gerais: fonte auditável, idempotência por hash e timestamps UTC.

### Critérios de conclusão

- Payload original e metadados podem ser recuperados por hash/data; duplicatas não sobrescrevem artefatos existentes.

## Etapa 3 — Validar e tipar na Silver

### Objetivo

Promover registros válidos a snapshots padronizados preservando sinais de mudança de schema.

### Requisitos ou regras

- Validar e tipar com Pydantic v2.
- Modelo temporal permite recuperar registro mais recente por medicamento e farmácia.
- Schema drift gera warning estruturado com campos omitidos/desconhecidos.
- Campos obrigatórios inválidos impedem apenas a promoção daquele registro.

### Critérios de conclusão

- Snapshots Silver são tipados e temporais; schema drift é observável e registros inválidos não são promovidos silenciosamente.

## Etapa 4 — Derivar visões Gold

### Objetivo

Disponibilizar visões de negócio recriáveis a partir dos dados padronizados.

### Requisitos ou regras

- Gold contém views de disponibilidade atual por polo, medicamentos zerados, idade da última observação e taxa de ruptura (`ZERADO` / observados).
- Gold é derivada e não recebe escrita manual.

### Critérios de conclusão

- As visões podem ser recriadas das camadas anteriores e não têm edição manual como fonte de verdade.

## Etapa 5 — Implementar contratos e conector

### Objetivo

Padronizar coleta resiliente e isolar detalhes da fonte.

### Requisitos ou regras

- `BaseConnector` define `fetch()`, `validate_schema()` e `generate_metadata()`; `validate()` permanece alias de compatibilidade.
- Fornecer retry exponencial para HTTP 429, 500, 502, 503 e 504, além de checkpoint JSON por conector para cursor/página.
- `InfoSaudeDFConnector` prioriza resposta JSON do painel SES-DF, sem seletores DOM.
- Aceitar endpoint configurável e fallback por token efêmero para endpoints Power BI.
- Resposta mínima pode ser lista ou conter `data`, `items`, `value` ou `records`.
- Tolerar indisponibilidade transitória e schema drift.

### Critérios de conclusão

- Conector usa resposta estruturada disponível, mantém checkpoint e retries definidos e reporta mudanças de schema.

## Etapa 6 — Persistir por repositório substituível

### Objetivo

Desacoplar o pipeline da tecnologia física de armazenamento.

### Requisitos ou regras

- `StorageRepository` expõe `save_bronze(source_name, payload, metadata)`, `save_silver_snapshot(snapshot)` e `get_latest_stock(medicamento, farmacia)`.
- `FileStorageRepository` é o adaptador inicial.
- Futuros adaptadores DuckDB ou PostgreSQL não devem exigir mudanças nos conectores.
- ADR-001 está **EM ANÁLISE**: DuckDB + Parquet é portátil/analítico e tem limitação de concorrência operacional; SQLite é simples/transacional, com menor capacidade analítica; PostgreSQL oferece concorrência/governança maduras e requer infraestrutura; lakehouse em arquivos tem histórico barato/imútavel, com exigência adicional de catálogo/governança.
- Decisão provisória: manter adaptador local em arquivos e comparar DuckDB/PostgreSQL com carga real do piloto.

### Critérios de conclusão

- Pipeline usa interface de repositório; adaptador local persiste Bronze/Silver e consulta último estoque sem acoplar conectores.
- Decisão final de storage continua pendente até avaliação com carga real.

## Etapa 7 — Verificar operação e critérios de aceite

### Objetivo

Demonstrar integridade, resiliência e comportamento de armazenamento definidos.

### Requisitos ou regras

- Critérios: payload original recuperável por hash/data; coleta resiliente a falhas transitórias; metadados com UUID, UTC, URL, status HTTP e SHA-256; deduplicação; snapshots Silver tipados/temporais; warnings de drift sem perda silenciosa; conector InfoSaúde sem scraping visual; persistência substituível via Repository Pattern.
- O SDD informa que `scripts/pipeline.py` processou 5 documentos e 459 páginas na execução inicial: envelopes JSON na Bronze, registros JSONL por página na Silver e `document_catalog.json` na Gold. É um registro de execução informado, não requisito nem comprovação atual independente.
- O pipeline produz texto e proveniência para recuperação posterior; ainda não gera embeddings ou chama LLM (conforme estado descrito neste documento).
- Testes unitários passando constam como critério declarado no SDD.

### Critérios de conclusão

- Cada critério possui evidência de verificação, incluindo testes unitários conforme exigido pelo SDD.
- Contagens da execução inicial não são tratadas como meta ou como estado atual sem nova verificação.

## Dependências e decisões em aberto

- **Dependências explícitas:** disponibilidade da fonte pública, estabilidade do contrato de resposta, endpoint e token efêmero quando Power BI for usado, infraestrutura de armazenamento para opções candidatas e carga real do piloto para comparação.
- **Decisão pendente:** motor final de armazenamento (ADR-001); a decisão é provisoriamente manter arquivos e comparar DuckDB/PostgreSQL.
- **Compatibilidade:** esta especificação técnica trata ingestão e armazenamento temporal. Regras de produto, aplicabilidade de conteúdo e segurança das respostas estão na [especificação funcional do MVP](SPEC-02-functional-mvp.md); catálogo e situação de fontes estão no [levantamento de fontes](../levantamento-fontes.md).
