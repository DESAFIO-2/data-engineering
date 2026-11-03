# SUS Cidadão — Engenharia de Dados

Repositório da frente de Engenharia de Dados do projeto acadêmico SUS Cidadão. Ele reúne as fontes oficiais, seus metadados, o pipeline local de preparação e recuperação RAG e as validações necessárias para produzir resultados auditáveis.

## Escopo atual

- catalogar e versionar fontes públicas do SUS;
- extrair texto dos PDFs por página;
- criar chunks com fonte, versão, página e identificador estável;
- construir um índice local TF-IDF com unigramas e bigramas;
- recuperar evidências para medicamentos com rastreabilidade;
- preparar a avaliação com golden set antes da geração por LLM.

## Estrutura

```text
config/                         configuração das fontes e dos chunks
data/raw/                       documentos oficiais originais
data/manifests/                 hashes e metadados das coletas
docs/                           especificação, fontes e planejamento
src/sus_cidadao_data/rag/       pipeline e interface de linha de comando
tests/                          testes automatizados
.artifacts/rag/                 corpus e índice reconstruíveis, ignorados pelo Git
```

## Preparação

Requer Python 3.12 e [uv](https://docs.astral.sh/uv/).

```bash
uv sync
```

## Construção do índice

```bash
uv run python -m sus_cidadao_data.rag.cli build
```

O comando gera `corpus.jsonl`, `tfidf-index.json` e `build-manifest.json` em `.artifacts/rag/`. O manifesto registra hashes, páginas, chunks e alertas de extração.

## Consulta

```bash
uv run python -m sus_cidadao_data.rag.cli search "metformina 500 mg" --top-k 5
uv run python -m sus_cidadao_data.rag.cli search "losartana 50 mg" --json
```

## Qualidade

```bash
uv run ruff format --check .
uv run ruff check .
uv run mypy src tests
uv run pytest
```

## Regra de versionamento

Os PDFs e seus manifestos são as entradas auditáveis. Os embeddings e índices derivados não são enviados ao Git porque podem ser reconstruídos de maneira determinística. Quando houver mudança em uma fonte ou na estratégia de chunking, o índice deve ser gerado novamente.

A geração de respostas por LLM será integrada depois da criação e validação do golden set. A aplicação deverá sempre apresentar a fonte, a versão e a página usadas na resposta.
