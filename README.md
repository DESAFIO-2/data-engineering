# SUS Cidadão — Engenharia de Dados

Repositório da frente de Engenharia de Dados do projeto acadêmico SUS Cidadão. Ele reúne fontes oficiais, metadados, contratos de ingestão e armazenamento em camadas para produzir dados auditáveis.

## Escopo atual

- catalogar e versionar fontes públicas do SUS;
- extrair texto dos PDFs por página;
- preservar payloads e documentos na Bronze com hash e proveniência;
- extrair texto por página e normalizar registros na Silver;
- publicar catálogo derivado na Gold;
- preparar dados auditáveis para consumidores futuros, sem acoplar a um LLM.

## Estrutura

```text
data/raw/                       documentos oficiais originais
data/manifests/                 hashes e metadados das coletas
docs/                           especificação, fontes e planejamento
src/ingestion/                 conectores e contratos de coleta
src/storage/                   Bronze, Silver e Repository Pattern
src/rag/                       recuperação, Chroma, síntese e CLI
scripts/pipeline.py                pipeline documental raw -> Bronze -> Silver -> Gold
scripts/rag_release.py             publicação do release aprovado
tests/                          testes automatizados
data/{bronze,silver,gold}       dados locais reconstruíveis, ignorados pelo Git
```

## Preparação

Requer Python 3.12 e [uv](https://docs.astral.sh/uv/). As dependências estão em `pyproject.toml`, com versões resolvidas em `uv.lock`:

```bash
uv sync
```

## Arquitetura de ingestão

A fundação atual coleta fontes dinâmicas e preserva os payloads na camada Bronze, normaliza entidades de estoque e farmácias na Silver e produz visões analíticas na Gold. Os contratos estão em `src/ingestion` e `src/storage`. O piloto é o painel InfoSaúde DF de Farmácias de Alto Custo.

Para processar os PDFs já coletados:

```bash
uv run python scripts/pipeline.py
```

O job é idempotente por SHA-256. A especificação normativa está em `docs/engenharia-dados/especificacao-ingestao-dados-vivos.md`.

## RAG híbrido local

O protótipo em `src/rag/` consome somente o release aprovado em `data/releases/rag-lote-1-aprovado-2026-11-05/`. Ele confere aprovação e hashes, identifica exatamente princípio ativo, concentração e forma, e usa Chroma persistente para recuperar evidências da mesma apresentação. As respostas mostram fonte, versão, página e URL. O corpus documental cobre 6 apresentações e 18 evidências; não valida estoque, documentos, elegibilidade, exames ou orientação clínica.

Para perguntas de **estoque UBS e localização**, o agente consulta um snapshot separado do InfoSaúde-DF. `uv run python app.py chat` sincroniza os painéis públicos ao iniciar e grava `data/gold/infosaude_live_snapshot.json` (arquivo local ignorado pelo Git). Se a sincronização falhar, avisa e usa o último snapshot salvo, quando existir. `sync-live` continua disponível para atualização isolada; `ask` usa o snapshot salvo. As respostas informam a data da extração e a fonte; saldo registrado não garante disponibilidade no momento da retirada. O estoque CEAF também é coletado, mas o RAG só relaciona estoque UBS às seis apresentações deste lote. Veja [integração InfoSaúde](docs/infosaude-live-rag.md).

Copie `.env.example` para `.env`, preencha `APP_GOOGLE_API_KEY` e execute na raiz deste repositório:

```bash
uv run python app.py index
uv run python app.py eval
uv run python app.py chat
```

Para inspecionar sem geração, use `uv run python app.py search "sinvastatina 20 mg comprimido consta na REME?"`; `ask` responde uma pergunta com o modelo configurado. O índice em `data/vectorstore/chroma/` é reconstruível e ignorado pelo Git. Veja [arquitetura e limites](docs/rag-hibrido-chromadb.md).

## Qualidade

```bash
uv run ruff format --check .
uv run ruff check .
uv run mypy src tests
uv run pytest
```

## Regra de versionamento

Os dados brutos e seus manifestos são as entradas auditáveis. As camadas Silver e Gold são derivadas e reconstruíveis; dados locais não são enviados ao Git.

A integração com consumidores deve preservar a origem, o timestamp de coleta e a qualidade do dado.
