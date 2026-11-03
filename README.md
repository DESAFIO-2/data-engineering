# SUS Cidadão — Engenharia de Dados

Repositório da frente de Engenharia de Dados do projeto acadêmico SUS Cidadão. Ele reúne fontes oficiais, metadados, contratos de ingestão e armazenamento em camadas para produzir dados auditáveis.

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
src/sus_cidadao_data/ingestion/ e storage/ contratos de ingestão e persistência
tests/                          testes automatizados
data/{bronze,silver,gold}       dados locais reconstruíveis, ignorados pelo Git
```

## Preparação

Requer Python 3.12 e [uv](https://docs.astral.sh/uv/).

```bash
uv sync
```

## Arquitetura de ingestão

A fundação atual coleta fontes dinâmicas e preserva os payloads na camada Bronze, normaliza entidades de estoque e farmácias na Silver e produz visões analíticas na Gold. Os contratos estão em `src/sus_cidadao_data/ingestion` e `src/sus_cidadao_data/storage`. O piloto é o painel InfoSaúde DF de Farmácias de Alto Custo.

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
