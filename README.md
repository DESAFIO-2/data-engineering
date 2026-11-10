# SUS Cidadão — Engenharia de Dados e RAG documental

Projeto acadêmico de ingestão auditável e consulta documental no terminal,
com Chroma, recuperação lexical/vetorial e síntese Gemini. Fontes e respostas
representam versões congeladas; presença em lista não garante estoque,
elegibilidade individual ou orientação clínica.

## Estado da semana 2

O release aprovado de seis apresentações permanece separado. A expansão exige
`--experimental` e mantém revisão humana pendente. O manifesto complementar
inspecionado registra 17 documentos baixados com hashes distintos; somados às
três listas principais, são 20 fontes coletadas, **não 20 fontes curadas**.
Hash distinto não substitui revisão de pertinência e independência documental.

O corpus schema 2 registra 2.115 ocorrências candidatas, 2.620 chunks limitados
a 2.000 caracteres Unicode (sobreposição máxima 240), 1.651 apresentações
literais completas candidatas e texto de 366 páginas preservado. Esses totais
não representam medicamentos terapeuticamente equivalentes nem curadoria
concluída. Avaliação final, indexação completa, gravação e envio ao Teams
dependem das respectivas evidências; não são declarados concluídos aqui.

## Preparação e primeira consulta

Na raiz do repositório, com Python 3.12 e uv:

```powershell
uv sync --frozen --python 3.12
uv run python app.py --help
uv run python -m scripts.pipeline
uv run python -m scripts.build_corpus
uv run python app.py search "Sinvastatina 20 mg comprimido consta na REME?" --experimental --corpus data/corpus/experimental --supplement data/raw/complementares/chunks.jsonl --strategy lexical --documental --show-context
```

A consulta lexical não exige chave ou índice. Esses comandos pressupõem os
snapshots presentes; a reconstrução regrava o
corpus experimental. Preservar artefatos de uma rodada antes de reconstruir.

Para embeddings e geração, configurar `APP_GOOGLE_API_KEY` localmente, sem
expor a chave no histórico, nas capturas ou no pacote. Os modelos vêm de
`APP_RAG_CHAT_MODEL` e `APP_RAG_EMBEDDING_MODEL`; ambiente prevalece sobre
`.env`. Registrar os modelos efetivos da rodada sem divulgar credenciais.

```powershell
uv run python app.py index --experimental --corpus data/corpus/experimental --supplement data/raw/complementares/chunks.jsonl
uv run python app.py ask "Sinvastatina 20 mg comprimido consta na REME?" --experimental --corpus data/corpus/experimental --supplement data/raw/complementares/chunks.jsonl --strategy hybrid --documental --show-context
uv run python app.py chat --experimental --corpus data/corpus/experimental --supplement data/raw/complementares/chunks.jsonl --strategy hybrid --documental --show-context
```

Para conversar com o **corpus consolidado aprovado** e sincronizar o InfoSaúde
ao iniciar o chat, use:

```powershell
uv run python app.py chat --validated
```

`--validated` carrega as 2.115 ocorrências e os 2.620 chunks primários de
`data/corpus/`, verifica manifesto/relatório e reaproveita os vetores do índice
histórico somente após conferir modelo, IDs e textos. Os 108 chunks
complementares ainda marcados `pending` ficam fora deste chat e não são
enviados como evidência. Não é necessário recalcular embeddings para esses
2.620 textos idênticos.
As ocorrências e apresentações do corpus consolidado estão `approved`, mas
os 2.620 chunks primários ainda têm `review_status: pending`; o chat avisa
isso na abertura. O manifesto aprovado não substitui a validação individual
dos chunks.
Na abertura, sincroniza estoque UBS/CEAF e cadastro de unidades; se a coleta
falhar, avisa e tenta usar o último snapshot local. Consultas de estoque ficam
limitadas às seis apresentações com código UBS validado no release de estoque;
respostas documentais usam o corpus consolidado. A lista documental não comprova
saldo nem disponibilidade. `--experimental` continua selecionando o snapshot
histórico para comparação.

Usar o mesmo corpus, suplemento e modelo ao indexar e consultar. Estratégias:
`hybrid`, `lexical`, `vector`, `exact`; top-k padrão 5. As referências
são verificáveis, mas sua validade não prova fidelidade factual da resposta.

## Avaliação e pacote local

O golden set planejado contém 120 casos sintéticos, 80 dev/40 test. Rascunhos
só podem ser avaliados em dev com `--allow-draft`; teste exige revisão e hash
canônico previamente congelado. Nunca indexar o golden set nem persistir
perguntas pessoais. O [guia de execução](docs/guia-entrega-semana2.md) contém
comandos completos de geração, etapas `retrieval/generation/end-to-end`,
três repetições de performance, critérios e tratamento de falhas.

```powershell
uv run python -m scripts.package_delivery --dry-run
uv run python -m scripts.package_delivery --name semana2-documental-v1.zip
```

O ZIP fica em `output/semana2`, com inventário e hashes internos. Só inclui
árvores/extensões permitidas; exclui `.env`, caches, logs e histórico. Índice
só entra com `--include-index`. Conferir o conteúdo antes de compartilhar.
O script não envia arquivos ao Teams.

## Estrutura e documentação

| Caminho | Papel |
|---|---|
| `data/raw`, `data/manifests` | Snapshots oficiais e proveniência |
| `data/bronze`, `data/silver`, `data/gold` | Camadas derivadas reconstruíveis |
| `data/corpus/experimental` | Corpus candidato, chunks e relatórios |
| `data/releases` | Releases com escopo de aprovação próprio |
| `data/vectorstore` | Índices Chroma reconstruíveis |
| `src/ingestion`, `src/storage` | Conectores e contratos de armazenamento |
| `src/rag` | Recuperação, geração, CLI e avaliação |
| `scripts` | Coleta, construção e empacotamento |
| `evals` | Datasets e resultados sintéticos |
| `tests` | Verificações automatizadas |

- [Plano e critérios de aceite](docs/plano-execucao-semana2.md)
- [Arquitetura e diagrama](docs/arquitetura-rag-ampliado.md)
- [Guia visual de métricas do RAG](src/rag/README.md)
- [Guia reproduzível e entrega](docs/guia-entrega-semana2.md)
- [Fontes complementares e curadoria](docs/fontes-complementares.md)
- [Checkpoint de implementação](docs/CONTINUAR-IMPLEMENTACAO.md)
- [Resultados reais e pendências da execução](docs/relatorio-execucao-semana2.md)
- [Revisão humana e publicação do corpus](docs/revisao-publicacao.md)

## Compatibilidade e qualidade

Sem `--experimental` ou `--curated`, a CLI usa o release aprovado; `--release` permite
selecionar outro release validado. O `eval` legado usa seu dataset próprio,
não o golden set ampliado. `--documental` evita consultar/sincronizar estoque.
O chat legado sem essa opção pode sincronizar InfoSaúde; snapshots não
garantem disponibilidade atual. Ver [integração InfoSaúde](docs/infosaude-live-rag.md).

Comandos de verificação, a executar em ambiente adequado:

```powershell
uv run ruff format --check .
uv run ruff check .
uv run mypy src tests
uv run pytest
```

Resultados devem ser registrados com commit, alterações locais, versões e
escopo. Testes que escrevem releases precisam de isolamento; preservar
alterações compartilhadas. Passar testes não concede aprovação humana aos dados.

Estado em 07/11/2026: corpus ampliado e golden permanecem candidatos; índice
vetorial parcial (984/2728) bloqueado pela cota diária da API. A recuperação
lexical dev atingiu Hit@5 de 96,3%; o chat teve 32 falhas de API em 80 casos.
Detalhes, BLEU/ROUGE e limitações estão no relatório de execução acima.
Após revisão e publicação reais, `app.py chat --curated DIRETORIO --strategy lexical`
carrega o subconjunto aprovado sem alterar o release legado.
