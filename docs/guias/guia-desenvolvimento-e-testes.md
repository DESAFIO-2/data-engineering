# Guia de Desenvolvimento, Setup Local e Testes

Este guia orienta quem clona o repositório `data-engineering/` pela primeira vez a preparar o ambiente, executar consultas locais com ou sem DVC/API Gemini e rodar a suíte de testes de forma reprodutível.

---

## 1. Pré-requisitos e Setup com `uv`

O projeto usa **Python 3.12** (definido em `.python-version`) e gerenciamento de dependências via **`uv`** (`pyproject.toml` + `uv.lock`).

```bash
# Na raiz de data-engineering/
uv sync --frozen --python 3.12
uv run python app.py --help
```

> **Atenção:** Evite rodar `pytest` diretamente no Python global do sistema (especialmente em versões diferentes da 3.12, como 3.14), pois dependências como `pdfplumber`, `sacrebleu` e `rank-bm25` estão travadas no ambiente virtual do `uv`.

---

## 2. Releases Disponíveis: Git vs. DVC

Nem todos os releases estão presentes no clone inicial do Git:

| Release | Onde está | Status | Uso recomendado |
|---|---|---|---|
| `data/releases/corpus-consolidado-v9-aprovado-2026-11-12` | **DVC** (`.dvc`) | `approved` | Release consolidado mais recente (2.114 evidências). Requer `uv run dvc pull` com acesso OAuth ao Google Drive compartilhado (ver [guia-dvc-drive.md](guia-dvc-drive.md)). |
| `data/releases/corpus-consolidado-v5-aprovado-2026-11-10` | **Git** | `approved` | Alternativa local completa (2.114 evidências) para testes e chat sem acesso ao DVC. |
| `data/releases/rag-lote-1-aprovado-2026-11-05` | **Git** | `approved` | Lote mínimo (6 medicamentos / 18 evidências), padrão de `.env.example` e `src/rag/config.py`. |
| `data/releases/corpus-consolidado-v9-claritromicina-normalizada-2026-11-12` | **Git** | `pending_review` | Candidato pré-aprovação. **Não** use como release aprovado; `ConsolidatedRelease.load()` recusa releases não aprovados. |

Se você tentar executar um comando apontando para `v9-aprovado` sem ter rodado `dvc pull`, a CLI exibirá um erro explícito indicando o ponteiro `.dvc` ausente e os comandos necessários.

---

## 3. Configuração de Variáveis de Ambiente (`.env`)

Copie o modelo e configure apenas localmente (nunca versione `.env`):

```bash
cp .env.example .env
```

- **Sem chave Gemini (`APP_GOOGLE_API_KEY` vazia):** você pode usar `--documental --strategy lexical` ou `exact` normalmente, sem chamadas externas:
  ```bash
  uv run python app.py chat --release data/releases/corpus-consolidado-v5-aprovado-2026-11-10 --documental --strategy lexical
  ```
- **Com chave Gemini (`APP_GOOGLE_API_KEY` preenchida):** necessário apenas para construir/consultar índice vetorial (`vector` / `hybrid`) e síntese LLM.
  - Para construir o índice vetorial antes de usar `vector` ou `hybrid`:
    ```bash
    uv run python app.py index --release data/releases/corpus-consolidado-v5-aprovado-2026-11-10
    ```
  - Na API de busca (`src/rag/consolidated.py::search`), chamar `strategy="vector"` ou `strategy="hybrid"` sem `store` carregado falha explicitamente com `ValueError` (não há fallback silencioso para `lexical`).

---

## 4. Como Executar os Testes e Verificações

### Sem DVC (clone novo, offline)

Os testes que dependem de releases grandes armazenados no DVC (`v7-aprovado`, `v8-aprovado`, `v9-aprovado`) estão marcados com `@pytest.mark.dvc` em `pyproject.toml`. Para rodar toda a suíte independente de DVC:

```bash
uv run pytest -m "not dvc"
```

### Com DVC (suíte completa)

Após autenticar no Google Drive do DVC e baixar os artefatos:

```bash
uv run dvc pull
uv run pytest
```

### Lint e Tipagem

```bash
uv run --no-sync ruff format --check .
uv run --no-sync ruff check .
uv run --no-sync mypy src tests
```

> **Nota sobre `scripts/`:** `scripts/` permanece excluído da formatação/lint padrão do Ruff e dos overrides de tipagem de scripts históricos em `pyproject.toml` para não alterar hashes ou contratos de publicação congelados; todo código em `src/` e `tests/` passa com tipagem estrita (`mypy src tests`).

---

## 5. Guardrails de Escopo Clínico

As regras lexicais de bloqueio clínico e de elegibilidade são compartilhadas entre `src/rag/consolidated.py` (`search()`) e `src/rag/consolidated_chat.py` (`ask()`/`chat()`) via `CLINICAL_BLOCKED_TERMS` e `matches_clinical_guardrail()`.

- Elas bloqueiam perguntas fora do escopo documental (como posologia/dose, efeito colateral, gravidez/gestação, interação medicamentosa, "como usar", elegibilidade e substituição terapêutica).
- **Importante:** regras lexicais são uma barreira determinística limitada, **não** um classificador clínico abrangente.

---

## 6. Revisão Humana e Avaliações da Semana 3

Os resultados automáticos da Semana 3 (`evals/results/week3_v9_*.json`) **não** sustentam alegações de superioridade entre estratégias enquanto:
1. A planilha de revisão factual humana ([evals/reviews/week3_v9_response_test_review.csv](../../evals/reviews/week3_v9_response_test_review.csv)) estiver pendente (0/44 preenchidas);
2. Houver falhas de cota `429` da API Gemini nas respostas geradas;
3. A amostra congelada permanecer pequena (11 casos no teste da Semana 3).

Para consolidar a revisão humana depois que uma pessoa avaliadora preencher integralmente os campos `factual_accuracy`, `fidelity`, `completeness`, `citation_support`, `critical_error`, `abstention_correct`, `reviewer`, `reviewed_at` e `rationale` no CSV:

```bash
PYTHONPATH=src uv run python -m scripts.week3_review \
  --runs evals/results/week3_v9_response_test.json \
  --reviews evals/reviews/week3_v9_response_test_review.csv \
  --output evals/results/week3_v9_response_test_human_review.json
```

> **Observação sobre RAGAS:** `scripts/week3_ragas.py` utiliza dependências isoladas declaradas em PEP 723 (`week3_ragas.py.lock`) e deve ser executado com `uv run --script scripts/week3_ragas.py`, não no ambiente principal.

