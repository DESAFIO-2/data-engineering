# SUS Cidadão — Engenharia de Dados e RAG documental

> **Release documental aprovado:** `corpus-consolidado-v7-aprovado-2026-11-11`, com escopo e restrições registrados na [decisão de Jhiovana](docs/reports/revisao-v6-jhiovana.md). A [SPEC do RAG híbrido](docs/specs/SPEC-09-rag-hibrido-v7.md) usa a v7; os resultados exploratórios da v6 não aprovam a recuperação na v7 nem o uso de embeddings. A [SPEC de CEP → UBS](docs/specs/SPEC-10-cep-ubs-privacidade.md) permanece uma frente separada.

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

Para conversar com o **release consolidado v5 aprovado**, use exatamente:

```powershell
uv run python app.py chat --release data/releases/corpus-consolidado-v5-aprovado-2026-11-10
```

O manifesto `consolidated-release-v2` seleciona o fluxo consolidado para `chat`,
`ask`, `search`, `index`, `eval` e `sync-live`. A seleção também respeita
`APP_RAG_RELEASE_DIR`; sem configuração, o padrão continua sendo o lote legado.
`--validated` seleciona o corpus de `data/corpus/` no fluxo ampliado anterior;
**não seleciona o release v5**.

O chat v5 mantém contexto somente em memória e envia os últimos seis turnos
à geração. Aceita esclarecimentos como `850 mg`, `comprimido`, `E em Planaltina?`
e `E na Farmácia Popular?`. Uma nova pergunta com medicamento inicia outro contexto.
Não é necessário saber concentração ou forma para começar: `metformina` lista
as apresentações documentadas, incluindo concentrações, formas e características
de liberação. O chat permite escolher por número ou pelos detalhes conhecidos;
uma única apresentação é identificada sem exigir que o usuário repita seus campos.
Depois de `liraglutida`, pode responder só `Planaltina` ou
`e tem estoque desse remédio em Planaltina?`. A apresentação e a região ficam
no contexto da sessão. Documentação não é uma etapa obrigatória da conversa.
As respostas documentais mostram fonte, versão, página e identificador da evidência.
Concentração e detalhe do dispositivo são tratados separadamente: por exemplo,
`liraglutida 6mg/ml solução injetável` recupera a apresentação com sistema de
aplicação de 3 mL na REME-DF, página 39. Erros próximos de nome, como `liraglutid`,
geram uma sugestão que exige confirmação. Veja a [regressão validada](docs/regressao-liraglutida.md).

Para conversar sem consultar nem sincronizar InfoSaúde:

```powershell
uv run python app.py chat --release data/releases/corpus-consolidado-v5-aprovado-2026-11-10 --documental --strategy lexical
```

Sem `APP_GOOGLE_API_KEY`, o chat responde com resumo e trechos documentais.
Com a chave da **v2**, tenta gerar linguagem natural mesmo quando a busca vetorial
falha. Índice ausente/incompatível ou serviço indisponível gera aviso e fallback
lexical; falha de geração mantém a resposta documental e suas fontes.
Ambiente prevalece sobre `.env`; nunca copie credenciais da v1.
Para construir o índice do mesmo release e modelo:

```powershell
uv run python app.py index --release data/releases/corpus-consolidado-v5-aprovado-2026-11-10
```

Sem `--documental`, o chat sincroniza uma referência inicial do InfoSaúde na
abertura. Os oito códigos dessa etapa **não representam toda a cobertura**.
Cada pedido de estoque com apresentação identificada e região faz uma **nova
consulta** aos painéis públicos UBS e CEAF, descobrindo o produto no catálogo e
validando código, descrição, concentração, forma e dispositivo. Quando houver
código na ocorrência REME-DF, ele também precisa coincidir. Produtos ambíguos,
associações e liberação modificada não são intercambiados automaticamente.

Uma falha de um painel não bloqueia o outro. O cache por apresentação preserva
a data da consulta anterior e é marcado como antigo quando usado após falha;
perguntas e CEP não são persistidos. Para sincronizar a referência inicial separadamente:

```powershell
uv run python app.py sync-live --release data/releases/corpus-consolidado-v5-aprovado-2026-11-10
```

Os códigos UBS `90224` (metformina 500 mg comprimido) e `90226` (850 mg comprimido)
foram consultados no catálogo público e vinculados às apresentações explícitas da
v5 em `data/mappings/ubs_consolidated.json`, com data, descrição e origem. Eles são
sincronizados junto aos seis códigos legados. Para repetir a validação do catálogo:

```powershell
uv run python -m scripts.validate_ubs_metformin
```

O código `13142` de ação prolongada foi encontrado, mas permanece **sem vínculo**:
a ocorrência F04 não informa forma farmacêutica. Associações com outros princípios
ativos não são metformina isolada. Outros itens v5 são descobertos e conferidos
sob demanda; não é preciso incluí-los manualmente nesses oito códigos iniciais.
Liraglutida foi conferida no código `27795`. O código `37352` e a associação com
insulina não são tratados como a mesma apresentação.

O chat pode informar **presença nas versões documentais consultadas** e
**saldo UBS ou situação CEAF retornados pela API**, para apresentações vinculadas. Estoque UBS
é filtrado pela região pedida; ausência de registro não significa saldo zero.
Exibe a hora da consulta e a data da posição do painel separadamente. Consulta
feita agora não significa estoque atualizado em tempo real: se o painel omitir a
data, o chat informa essa limitação, mesmo que retorne zero ou “COM ESTOQUE”.
CEAF e UBS são canais distintos; unidades CEAF de outras regiões são identificadas
explicitamente, sem afirmar qual delas atende o endereço do usuário.
Exibe data de extração, saldo registrado e unidade, com aviso para confirmar antes
de ir. Uma extração com mais de 48 horas é sinalizada como antiga.
**Presença na Farmácia Popular não comprova estoque UBS, nem o contrário.**
A API de CEP/UBS de referência é uma evolução futura: o chat **não pede CEP**,
não resolve endereço e não afirma em qual UBS o usuário será atendido.
Veja a [demonstração real com busca progressiva e estoque](docs/demo-busca-progressiva-estoque.md).

O RAG recupera evidências do corpus para geração com citações. Sem índice,
a recuperação é lexical; com índice compatível, o modo híbrido combina ranking
lexical e vetorial dentro das apresentações já identificadas. Embeddings não
substituem a identificação segura do produto nem consultam estoque. Ainda não há
avaliação comparativa que prove superioridade de uma estratégia neste corpus.

O chat não comprova disponibilidade atual, elegibilidade individual, documentos
obrigatórios, indicação individual, dose ou equivalência/substituição terapêutica.

A [demonstração histórica antes/depois](docs/demo-chat-v5.md) usa as mesmas perguntas,
sem chave e com snapshot público real. A [demonstração com Gemini](docs/demo-chat-v5-modelo.md)
registra geração real com a configuração local da v2, mesmo sem índice vetorial.
Para reproduzir contra o commit anterior
à mudança, substitua `COMMIT_ANTERIOR` pelo hash registrado na demonstração:

```powershell
uv run python -m scripts.demo_consolidated_chat --baseline-ref COMMIT_ANTERIOR
uv run python -m scripts.demo_consolidated_chat --baseline-ref COMMIT_ANTERIOR --live-model --output docs/demo-chat-v5-modelo.md
```

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
não o golden set ampliado. No chat consolidado, `--documental` evita consultar
e sincronizar estoque. O chat legado mantém a sincronização de abertura mesmo
com essa opção. Snapshots não garantem disponibilidade atual. Ver
[integração InfoSaúde](docs/specs/SPEC-05-infosaude-live-api.md).

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
