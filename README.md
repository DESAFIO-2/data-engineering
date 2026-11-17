# SUS Cidadão — Engenharia de Dados e RAG documental

> **Release documental mais recente:** `corpus-consolidado-v9-aprovado-2026-11-12` (2.114 chunks, armazenado via **DVC** em `data/releases/corpus-consolidado-v9-aprovado-2026-11-12.dvc` — exige `uv run dvc pull`). Sem DVC, o padrão local de `.env.example` e `src/rag/config.py` aponta para `data/releases/corpus-consolidado-v5-aprovado-2026-11-10` (aprovado, 2.114 evidências diretamente no Git; o lote legado inicial `data/releases/rag-lote-1-aprovado-2026-11-05` possui apenas 18 evidências). O diretório `corpus-consolidado-v9-claritromicina-normalizada-2026-11-12` está em `pending_review` e **não** é um release aprovado. O histórico de aprovações anteriores (`v5`, `v6`, `v7`, `v8`) e suas restrições estão registrados em [docs/reports/](docs/reports). A [SPEC do RAG híbrido](docs/specs/SPEC-09-rag-hibrido-v7.md) refere-se à frente v7; a [SPEC de CEP → UBS](docs/specs/SPEC-10-cep-ubs-privacidade.md) permanece uma frente separada.

Projeto acadêmico (**Challenge 2 — Big Idea: Qualidade de Vida**) de engenharia de dados auditável e consulta documental no terminal, com ChromaDB, recuperação lexical/vetorial e síntese Gemini. Fontes e respostas representam versões congeladas; presença em lista não garante estoque, elegibilidade individual ou orientação clínica.

## Roadmap e entregáveis por semana

A documentação do projeto está organizada pelo roadmap oficial do Challenge 2 em [docs/entregaveis/](docs/entregaveis/README.md):

| Semana | Foco | Entregável principal | Estado | Pasta |
|---|---|---|---|---|
| 1 | Problema, stakeholders, riscos e métricas | Definições do projeto | Concluído | [semana-01](docs/entregaveis/semana-01/README.md) |
| 2 | Base de conhecimento e recuperação | Primeiro mecanismo RAG | Concluído | [semana-02](docs/entregaveis/semana-02/README.md) |
| 3 | Comparação LLM × RAG | Respostas baseadas em evidências | Revisão consolidada (44 registros) | [semana-03](docs/entregaveis/semana-03/README.md) |
| 4 | Sistema multiagentes | Primeiro sistema multiagentes | Planejado | [semana-04](docs/entregaveis/semana-04/README.md) |
| 5 | Multimodalidade | Agentes multimodais | Planejado | [semana-05](docs/entregaveis/semana-05/README.md) |
| 6 | Integração completa | Aplicação funcional | Planejado | [semana-06](docs/entregaveis/semana-06/README.md) |
| 7 | Testes e refinamento | Relatório final + apresentação | Planejado | [semana-07](docs/entregaveis/semana-07/README.md) |

## Estado atual (12/11/2026 — Semana 3)

- **Corpus consolidado:** `data/releases/corpus-consolidado-v9-aprovado-2026-11-12` (2.114 evidências, via DVC), cobrindo F01 RENAME, F03 REME-DF e F04 Farmácia Popular.
- **Comparação LLM × RAG (Semana 3):** oito cenários (`exact`, `lexical`, `vector`, `hybrid` na busca; `llm_only`, `lexical_documental`, `lexical_llm`, `best_llm` na resposta) executados em desenvolvimento e no conjunto de teste congelado (11 casos), além das métricas RAGAS e métricas complementares de recuperação. **Os resultados da Semana 3 ainda não sustentam alegação de superioridade de LLM ou vetor** porque a revisão consolidada cobre 35 respostas válidas em 44 tentativas, ocorreram falhas `429` da API Gemini (`best_llm`: 5/11; `lexical_llm`: 3/11) e a amostra de teste é pequena. Detalhes em [Semana 3 — LLM × RAG na v9](docs/reports/v9/semana3-llm-rag-v9.md).

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

### Reprodução acadêmica da auditoria

No clone limpo do commit `8d76f92`, com os seis objetos de release/chunks restaurados pelo DVC, exact e lexical acertaram 11/11 status e recuperaram evidência relevante em 7/7 positivos da Semana 3 (top_k=5). Os intervalos de Wilson de 95% são respectivamente 74–100% e 65–100%. A comparação pareada tem zero diferenças de acerto. Os IDs, resultados por fonte, hashes e latências estão no [registro desta execução](evals/results/week3_v9_retrieval_replay_8d76f92.json).

A [triagem dos cinco casos v9](docs/reports/v9/validacao-recuperacao-v9-test.md) documenta as duas ambiguidades e três ausências antes do ranking. A [análise da v8](docs/reports/v8/validacao-recuperacao-v8-test.md) registra a confusão de apresentação C-F03-005. Na Semana 3, W3-TEST-CAND-11 recebeu `not_in_scope` historicamente e `unsupported` nas duas estratégias da reprodução. Esses testes já conhecidos servem para regressão.

Na demonstração, use o comando de chat v9 com `--documental --strategy lexical` acima. A síntese só é exibida quando coincide com a mensagem produzida a partir da apresentação e das fontes recuperadas. Para revisar as 44 saídas históricas, confira cada afirmação contra a evidência e a página, registre a decisão e a justificativa por afirmação na coluna `rationale`, incluindo divergências adjudicadas. Registre falha de provedor e ausência de resposta explicitamente. O comando de consolidação da Semana 3 vincula cada julgamento ao hash da resposta.

O [caderno de conferência das 44 respostas](docs/reports/v9/conferencia-respostas-semana3.html) reúne pergunta, saída, erro de provedor, evidências recuperadas e referências esperadas por caso e variante.

[Consolidação da revisão factual da Semana 3](evals/results/week3_v9_response_test_human_review.json). Nas três variantes com recuperação, CAND-10 recebeu crédito de citação com IDs de evidência vazios e CAND-11 recebeu crédito de completude ao pedir a apresentação para uma pergunta de dose. A [adjudicação técnica](evals/results/week3_v9_response_test_adjudicado.json) retirou o crédito de citação em CAND-10 e de completude e abstenção em CAND-11 nas três variantes com recuperação. No modo documental, o resultado histórico é 7/8 em sustentação da citação, 10/11 em completude e 3/4 em abstenção.

### Verificação da entrega documental

Execute `PYTHONPATH=src uv run python -m scripts.verify_documental_delivery` após restaurar os releases v8 e v9. O [ensaio da CLI](evals/results/week3_documental_citacoes_rollback.json) registrou texto e latência de cada consulta em modo lexical local. Nos oito casos v9 com referências esperadas, as oito saídas exibiram ID, versão e página. A consulta clínica exibiu a recusa. Na troca v9 → v8 → v9, as 11 respostas finais foram idênticas às primeiras. Essa conferência automática de referências usa as perguntas conhecidas da Semana 3. A revisão independente do conteúdo atualizado continua pendente.

O repositório de armazenamento grava os snapshots validados em `silver/estoque.sqlite3`, sob a raiz informada ao construtor. A chave combina medicamento, farmácia e instante da posição em UTC. Uma nova gravação da mesma chave substitui a posição, e uma coleta anterior à posição corrente continua disponível no histórico.

Na [segunda execução após revisão das citações](evals/results/week3_documental_citacoes_rollback_v2.json), CAND-03 retornou somente a solução bucal a 0,12% e CAND-10 exibiu as duas apresentações da REME-DF com referências de F03. O verificador extrai os IDs efetivamente impressos e exige igualdade com os esperados, inclusive nos casos sem citações. A conferência fornecida pela pessoa revisora sustentou as afirmações dos oito casos contra os registros aprovados do v9, com ressalvas de escopo e registro corrigidas nesta execução. A conferência humana utilizou o JSONL do release, sem inspeção direta das páginas dos PDFs.
