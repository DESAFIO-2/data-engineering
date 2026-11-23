# Governança de Dados — `data/`

Esta pasta separa **artefatos versionados** (Git e DVC) de **camadas operacionais reconstruíveis** (gitignored, geradas em runtime).

## 1. Camadas versionadas (Git vs DVC)

| Pasta | Armazenamento | Papel |
|---|---|---|
| `raw/` | Git | Snapshots oficiais imutáveis (PDFs F01/F03/F04 e páginas/fontes complementares) |
| `manifests/` | Git | Manifestos de coleta inicial e proveniência (SHA-256, data, URL) |
| `mappings/` | Git | Vínculos auditados entre apresentações aprovadas e códigos externos UBS |
| `vocab/` | Git | Vocabulários controlados v10 (`ingredients.json`, `forms.json`, `units.json`, `channels.json`) |
| `corpus/experimental/` | Git | Fonte única do corpus experimental (sem espelho duplicado em `data/corpus/`) |
| `curation/` | Git (relatórios leves) + **DVC** (`revisao-corpus-v{1..3}*.json`) | Histórico de revisões e arquivo de caches intermediários (`archive/`) |
| `releases/` | **DVC** (`corpus-consolidado-v2..v10*`) + Git (`rag-lote-1`, 20 KB) | Releases documentais imutáveis com manifestos e hashes verificáveis |
| `derived/chunks/` | **DVC** (`corpus-consolidado-v5..v10*`) | Chunks determinísticos derivados dos releases aprovados |
| `vectorstore/chroma/consolidated/` | **DVC** (índice ativo) | Índices vetoriais ChromaDB reconstruíveis |

## 2. Camadas operacionais Medallion (gitignored / runtime)

As pastas `bronze/`, `silver/` e `gold/` mantêm apenas `.gitkeep` no Git porque armazenam dados locais reconstruíveis em runtime:

- **`bronze/`**: envelopes JSON imutáveis (com SHA-256 e metadados de coleta) gravados por `scripts/ingest/pipeline.py` e por `src/storage/` (`FileBronzeStorage`) durante sincronizações ao vivo do InfoSaúde-DF.
- **`silver/`**: registros estruturados por página (`pipeline.py`) e histórico temporal de estoque em SQLite (`data/silver/estoque.sqlite3`, via `FileSilverStorage` com validação de *schema drift*).
- **`gold/`**: snapshots e caches de leitura rápida consumidos pelo chat em runtime (`infosaude_live_snapshot.json` e `stock_queries/*.json`).

## 3. Sincronização via DVC

Para baixar ou enviar artefatos pesados versionados no remote `compartilhado`:

```bash
uv run dvc pull
uv run dvc push
```

Sem baixar os dados DVC, execute os testes independentes com:

```bash
uv run pytest -m "not dvc"
```
