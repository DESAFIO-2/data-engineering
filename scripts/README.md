# Scripts — `engenharia-dados`

Os scripts do repositório são organizados por ciclo de vida para separar rotinas ativas de artefatos históricos congelados:

- [`ingest/`](ingest/): coleta de fontes oficiais, pipeline documental, construção/curadoria de corpus e publicação/aprovação de releases consolidados.
- [`eval/`](eval/): geração de golden sets, benchmarks multi-chunk, comparativos LLM vs RAG (incluindo `week3_ragas.py` + `week3_ragas.py.lock` PEP 723), gates e empacotamento de entregas.
- [`archive/`](archive/): scripts históricos pontuais preservados apenas para rastreabilidade e testes de regressão:
  - [`archive/f03_f04_curation/`](archive/f03_f04_curation/): extração e curadoria inicial de F03/F04.
  - [`archive/releases/`](archive/releases/): migrações, revisões e promoções específicas das versões `v6`, `v7`, `v8`, `v9` e `v10`.

> **RAGAS isolado:** `scripts/eval/week3_ragas.py` usa lockfile PEP 723 (`week3_ragas.py.lock` no mesmo diretório) e deve ser executado com `uv run --script scripts/eval/week3_ragas.py`.
