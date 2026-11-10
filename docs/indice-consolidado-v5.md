# Índice do release consolidado v5

Fonte única: `data/releases/corpus-consolidado-v5-aprovado-2026-11-10`. O índice representa apenas presença nas listas F01/F03/F04; não responde sobre estoque, elegibilidade, unidade específica, dose ou equivalência terapêutica.

## Artefatos

- `data/derived/chunks/corpus-consolidado-v5-aprovado-2026-11-10/chunks.jsonl`: 2.114 chunks, um por evidência aprovada. `literal_text` preserva a evidência; `text` usa campos estruturados para busca. A célula `DESCRIÇÃO` da F03 e a indicação da F04 entram somente onde documentadas.
- `manifest.json` no mesmo diretório fixa o fingerprint do release, a receita de chunking e o hash dos chunks. O gerador recusa saída preexistente; `load_chunks` confere cada registro.
- O Chroma fica em `data/vectorstore/chroma/consolidated/<hash>`, isolado por release, chunks, modelo e API de embedding. `index.json` só é gravado após verificar todos os IDs, textos e dimensões.

## Comandos

Após instalar as dependências do projeto (`uv sync`) e configurar `APP_GOOGLE_API_KEY` em `.env`:

```bash
uv run python app.py index --release data/releases/corpus-consolidado-v5-aprovado-2026-11-10
uv run python app.py search "sinvastatina 20 mg comprimido consta na REME DF?" --release data/releases/corpus-consolidado-v5-aprovado-2026-11-10 --strategy hybrid
uv run python app.py eval --release data/releases/corpus-consolidado-v5-aprovado-2026-11-10 --strategy hybrid --dataset evals/datasets/consolidated_v5_draft.jsonl --split test --output evals/results/consolidated_v5_hybrid_draft.json
```

A indexação é retomável: uma nova execução grava apenas chunks ausentes. Uma falha de cota 429 recebe tentativas com espera; outras falhas interrompem a execução sem marcador de índice completo.

## Avaliação e ativação

O conjunto `consolidated_v5_draft.jsonl` contém perguntas sintéticas e **ainda exige revisão humana**. Antes de ativar o v5, revisar cada caso, congelar a versão de teste, executar as quatro estratégias (`exact`, `lexical`, `vector`, `hybrid`) e aplicar `scripts/check_consolidated_gate.py` aos quatro resultados. O gate exige Hit@5 ≥ 0,90, MRR@5 ≥ 0,80, status correto em todos os casos e conjunto de teste integralmente revisado. Até lá, `APP_RAG_RELEASE_DIR` continua apontando para o lote 1.

O release anterior permanece disponível para retorno. A alteração do padrão do aplicativo só ocorre após o gate passar e uma verificação ponta a ponta com o novo índice.
