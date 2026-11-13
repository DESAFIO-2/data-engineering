# SUS Cidadão — Engenharia de Dados e RAG documental

> **Release documental mais recente:** `corpus-consolidado-v9-aprovado-2026-11-12` (2.114 chunks, armazenado via **DVC** em `data/releases/corpus-consolidado-v9-aprovado-2026-11-12.dvc` — exige `uv run dvc pull`). Sem DVC, os releases aprovados disponíveis diretamente no Git são `data/releases/corpus-consolidado-v5-aprovado-2026-11-10` (2.114 evidências) e `data/releases/rag-lote-1-aprovado-2026-11-05` (padrão de `.env.example`). O diretório `corpus-consolidado-v9-claritromicina-normalizada-2026-11-12` está em `pending_review` e **não** é um release aprovado. O histórico de aprovações anteriores (`v5`, `v6`, `v7`, `v8`) e suas restrições estão registrados em [docs/reports/](docs/reports). A [SPEC do RAG híbrido](docs/specs/SPEC-09-rag-hibrido-v7.md) refere-se à frente v7; a [SPEC de CEP → UBS](docs/specs/SPEC-10-cep-ubs-privacidade.md) permanece uma frente separada.

Projeto acadêmico (**Challenge 2 — Big Idea: Qualidade de Vida**) de engenharia de dados auditável e consulta documental no terminal, com ChromaDB, recuperação lexical/vetorial e síntese Gemini. Fontes e respostas representam versões congeladas; presença em lista não garante estoque, elegibilidade individual ou orientação clínica.

## Roadmap e entregáveis por semana

A documentação do projeto está organizada pelo roadmap oficial do Challenge 2 em [docs/entregaveis/](docs/entregaveis/README.md):

| Semana | Foco | Entregável principal | Estado | Pasta |
|---|---|---|---|---|
| 1 | Problema, stakeholders, riscos e métricas | Definições do projeto | Concluído | [semana-01](docs/entregaveis/semana-01/README.md) |
| 2 | Base de conhecimento e recuperação | Primeiro mecanismo RAG | Concluído | [semana-02](docs/entregaveis/semana-02/README.md) |
| 3 | Comparação LLM × RAG | Respostas baseadas em evidências | Em validação (revisão factual pendente) | [semana-03](docs/entregaveis/semana-03/README.md) |
| 4 | Sistema multiagentes | Primeiro sistema multiagentes | Planejado | [semana-04](docs/entregaveis/semana-04/README.md) |
| 5 | Multimodalidade | Agentes multimodais | Planejado | [semana-05](docs/entregaveis/semana-05/README.md) |
| 6 | Integração completa | Aplicação funcional | Planejado | [semana-06](docs/entregaveis/semana-06/README.md) |
| 7 | Testes e refinamento | Relatório final + apresentação | Planejado | [semana-07](docs/entregaveis/semana-07/README.md) |

## Estado atual (12/11/2026 — Semana 3)

- **Corpus consolidado:** `data/releases/corpus-consolidado-v9-aprovado-2026-11-12` (2.114 evidências, via DVC), cobrindo F01 RENAME, F03 REME-DF e F04 Farmácia Popular.
- **Comparação LLM × RAG (Semana 3):** oito cenários (`exact`, `lexical`, `vector`, `hybrid` na busca; `llm_only`, `lexical_documental`, `lexical_llm`, `best_llm` na resposta) executados em desenvolvimento e no conjunto de teste congelado (11 casos), além das métricas RAGAS e métricas complementares de recuperação. **Os resultados da Semana 3 ainda não sustentam alegação de superioridade de LLM ou vetor** porque a revisão factual humana das 44 respostas do conjunto de teste permanece pendente (0/44), ocorreram falhas `429` da API Gemini (`best_llm`: 5/11; `lexical_llm`: 3/11) e a amostra de teste é pequena. Detalhes em [Semana 3 — LLM × RAG na v9](docs/reports/v9/semana3-llm-rag-v9.md).

## Preparação e execução

Na raiz do repositório (`data-engineering/`), com Python 3.12 e `uv` (veja também o [Guia de desenvolvimento e testes](docs/guias/guia-desenvolvimento-e-testes.md)):

```bash
uv sync --frozen --python 3.12
uv run python app.py --help
# Para baixar os releases v7/v8/v9 aprovados (requer acesso OAuth ao Google Drive do DVC):
uv run dvc pull
```

Para indexação vetorial e geração com Gemini, configure localmente `APP_GOOGLE_API_KEY`, `APP_RAG_CHAT_MODEL` e `APP_RAG_EMBEDDING_MODEL` (variáveis de ambiente prevalecem sobre `.env`; nunca exponha credenciais no histórico ou em capturas).

### Consulta e chat no release consolidado

Para conversar com o release aprovado `v9` após `uv run dvc pull` (ou usando `data/releases/corpus-consolidado-v5-aprovado-2026-11-10` sem DVC):

```bash
uv run python app.py chat --release data/releases/corpus-consolidado-v9-aprovado-2026-11-12
```

Para conversar em modo estritamente documental (sem consultar nem sincronizar InfoSaúde-DF) e com busca lexical (sem necessidade de chave ou índice vetorial):

```bash
uv run python app.py chat --release data/releases/corpus-consolidado-v9-aprovado-2026-11-12 --documental --strategy lexical
```

Para construir o índice vetorial ChromaDB de um release:

```bash
uv run python app.py index --release data/releases/corpus-consolidado-v9-aprovado-2026-11-12
```

O manifesto `consolidated-release-v2` seleciona o fluxo consolidado para `chat`, `ask`, `search`, `index`, `eval` e `sync-live` (também configurável por `APP_RAG_RELEASE_DIR`). Estratégias disponíveis: `exact`, `lexical`, `vector`, `hybrid` (`top_k=5` por padrão). As estratégias `vector` e `hybrid` exigem índice vetorial construído (`app.py index`); na API de busca (`search()`), a ausência de `store` gera erro explícito (sem fallback silencioso para `lexical`).

### Dados vivos (InfoSaúde-DF) e privacidade

Sem `--documental`, o chat sincroniza uma referência inicial do InfoSaúde-DF na abertura e realiza consultas sob demanda aos painéis públicos UBS e CEAF após identificação segura da apresentação (concentração, forma, sal e dispositivo validados; associações e liberação modificada não são intercambiadas automaticamente).

- Presença em lista (RENAME, REME-DF, Farmácia Popular) não comprova estoque, elegibilidade individual ou orientação clínica.
- Perguntas e CEP não são persistidos. A API de referência CEP → UBS é frente separada ([SPEC-10](docs/specs/SPEC-10-cep-ubs-privacidade.md)).
- Veja a [demonstração com busca progressiva e estoque](docs/demos/demo-busca-progressiva-estoque.md) e a [regressão validada da liraglutida](docs/demos/regressao-liraglutida.md).

## Avaliação (Semana 3)

Para reproduzir os comparativos da Semana 3 a partir da raiz:

```bash
PYTHONPATH=src uv run python -m scripts.week3_compare --matrix retrieval --release data/releases/corpus-consolidado-v9-aprovado-2026-11-12 --dataset evals/datasets/week3_v9_dev_draft.jsonl --output evals/results/week3_v9_retrieval_dev.json
PYTHONPATH=src uv run python -m scripts.week3_compare --matrix response --best-strategy exact --release data/releases/corpus-consolidado-v9-aprovado-2026-11-12 --dataset evals/datasets/week3_v9_dev_draft.jsonl --output evals/results/week3_v9_response_dev.json
uv run --script scripts/week3_ragas.py
```

Para consolidar a revisão factual humana das respostas de teste após o preenchimento da planilha de revisão:

```bash
PYTHONPATH=src uv run python -m scripts.week3_review --runs evals/results/week3_v9_response_test.json --reviews evals/reviews/week3_v9_response_test_review.csv --output evals/results/week3_v9_response_test_human_review.json
```

## Estrutura do repositório

| Caminho | Papel |
|---|---|
| `data/raw`, `data/manifests` | Snapshots oficiais e proveniência |
| `data/bronze`, `data/silver`, `data/gold` | Camadas derivadas reconstruíveis |
| `data/releases` | Releases consolidados versionados (DVC) |
| `data/vectorstore` | Índices ChromaDB reconstruíveis |
| `src/ingestion`, `src/storage` | Conectores e contratos de armazenamento |
| `src/rag` | Recuperação, geração, CLI e avaliação |
| `scripts` | Coleta, curadoria, publicação e avaliação |
| `evals` | Datasets, revisões e resultados de avaliação |
| `docs` | Índice, entregáveis por semana, especificações e relatórios |
| `tests` | Verificações automatizadas |

### Links principais da documentação

- [Índice geral da documentação](docs/README.md)
- [Entregáveis por semana (Challenge 2)](docs/entregaveis/README.md)
- [Especificação funcional do MVP (SPEC-02)](docs/specs/SPEC-02-functional-mvp.md)
- [Arquitetura da Engenharia de Dados (SPEC-00)](docs/specs/SPEC-00-architecture.md)
- [Arquitetura do RAG (SPEC-04)](docs/specs/SPEC-04-rag-architecture.md)
- [InfoSaúde-DF no RAG (SPEC-05)](docs/specs/SPEC-05-infosaude-live-api.md)
- [Guia visual de métricas do RAG](src/rag/README.md)
- [Semana 3: comparação LLM × RAG na v9](docs/reports/v9/semana3-llm-rag-v9.md)

## Verificação de qualidade

```bash
uv run ruff format --check .
uv run ruff check .
uv run mypy src tests
# Suíte unitária independente de DVC (funciona em clone novo sem Google Drive):
uv run pytest -m "not dvc"
# Suíte completa (requer `uv run dvc pull` prévio):
uv run pytest
```

Consulte o [Guia de desenvolvimento e testes](docs/guias/guia-desenvolvimento-e-testes.md) para detalhes de setup, DVC, guardrails e reprodução de avaliações. Passar nos testes automatizados verifica contratos de código e regressões técnicas; não concede aprovação humana aos dados nem valida afirmações clínicas.
