# Corpus ampliado e curadoria

**Objetivo:** Documentar a construção, os limites, a reprodução e a revisão do corpus experimental ampliado.

## 1. O que foi construído

O corpus experimental reúne a união das entradas das três listas congeladas:
RENAME 2024, 2ª edição; REME-DF de 29/10/2026; elenco Farmácia Popular de
31/08/2026. Usa os arquivos originais e hashes do manifesto de coleta inicial.
Texto de todas as 366 páginas está preservado na Silver e representado em chunks.

| Fonte | Páginas do original | Entradas estruturadas | Tratamento |
|---|---:|---:|---|
| RENAME | 267 | 996 | Apêndice A, páginas físicas 26–132, tabelas por coordenadas |
| REME-DF | 98 | 1.078 | Lista principal, páginas 12–59, sequência 1–1078 sem lacunas |
| Farmácia Popular | 1 | 41 | 39 linhas de medicamentos e dois insumos separados |
| Total | 366 | 2.115 | Ocorrências documentais, antes de consolidação |

O catálogo contém **1.651 identidades literais com nome, concentração e forma
preenchidos**. Esse número não corresponde a princípios ativos únicos nem a
equivalências farmacêuticas. Nomes de sais, grafias, concentrações e formas
diferentes permanecem separados. Uma entrada pode ocorrer em mais de uma fonte.

A geração produziu 2.620 chunks das listas. As fontes complementares são
adicionadas explicitamente ao carregar o corpus; seus 108 chunks elevam o total
indexável a 2.728. Fontes complementares têm inventário próprio.

## 2. Estratégia de extração e seus limites

O extrator geométrico usa pdfplumber. Na RENAME, uma célula ausente na linha só
herda o valor de outra célula quando as coordenadas demonstram que ela está
mesclada e cobre aquela linha. Não é um preenchimento cego pelo nome anterior.
Na REME, o número do item e as bordas horizontais delimitam a linha. Descrição,
código e canal são extraídos em colunas separadas, evitando intercalar as palavras
de colunas vizinhas. Foram inspecionadas visualmente amostras RENAME p43 e REME p16.

O Apêndice B da RENAME e as tabelas secundárias da REME continuam acessíveis
nos chunks das páginas, sem serem contados novamente como entradas da lista principal.
Os extratores são específicos dessas versões; outra edição exige reconciliação.

Campos da REME e Farmácia Popular ainda são identificados por regras literais.
Associações, grafias incomuns e concentrações múltiplas podem ficar sem estruturação
completa. A descrição original permanece disponível para revisão. O relatório
contabiliza esses casos; eles não são descartados silenciosamente.

| Fonte | Nome ausente | Concentração não resolvida | Forma não resolvida |
|---|---:|---:|---:|
| RENAME | 0 | 0 | 0 |
| REME | 20 | 154 | 85 |
| Farmácia Popular | 2 | 6 | 41 |

Os dois nomes ausentes no Farmácia Popular incluem insumos. A fonte não identifica
a forma em todas as linhas: o sistema não a completa a partir de suposição.
Zero campos ausentes também não comprova que todos os campos foram extraídos
corretamente. Revisão humana exaustiva e equivalências terminológicas estão pendentes.

## 3. Chunking e metadados

Unidade implementada: **caracteres Unicode**, não tokens do modelo. Limite de
2.000 caracteres e sobreposição de até 240 dentro da mesma página ou linha.
Quebras de linha e espaços são preferidos para cortar os trechos. Cada parte
registra seus offsets, documento, hash do original, versão, página e ID estável.
Linhas de tabela preservam identidade e contexto; trechos longos mantêm o vínculo
com a mesma ocorrência. O manifesto declara os parâmetros efetivos.

Os IDs derivam do conteúdo e da origem. O índice é separado pelo fingerprint do
corpus e modelo de embeddings. Mudança na entrada exige reconstrução controlada;
não é permitido apenas trocar o hash para aprovar conteúdo modificado.

## 4. Arquivos e reprodução

```powershell
uv sync
uv run python scripts/pipeline.py
uv run python -m scripts.build_corpus
```

O pipeline produz Silver local. O gerador verifica hashes dos PDFs e consistência
de páginas/proveniência, então grava `data/corpus/experimental/`:

- `occurrences.jsonl`: linhas originais, campos extraídos, página, caixa geométrica,
  código/canal quando disponíveis, incertezas e vínculos aos chunks. Itens não
  farmacológicos usam `supply_name`; cabeçalhos associados à linha ficam em
  `context.indication`; modificadores de liberação ficam em
  `release_characteristic`. A grafia original permanece em `raw_text`.
- `catalog.jsonl`: consolidação conservadora de identidades completas, com fontes
  e ocorrências associadas; todas permanecem pendentes.
- `chunks.jsonl`: texto indexável de linhas e páginas com localização verificável.
- `report.json`: contagens, lacunas, limites e cobertura.
- `manifest.json`: versão do esquema/extrator, parâmetros e hashes de cada saída.

O conteúdo é determinístico para as mesmas entradas e versões das dependências.
Os arquivos gerados são candidatos versionáveis; a pasta vetorial é reconstruível.
O release anterior aprovado de seis apresentações continua separado.

## 5. Revisão em lotes e critérios de aprovação

Revisar primeiro as 39 linhas do Farmácia Popular, depois a lista principal REME
e a RENAME. Para cada ocorrência, conferir o PDF, a linha completa, notas, nome,
concentração/composição, forma/liberação, código e canal, quando aplicáveis.
Associar fontes somente quando a apresentação for a mesma. Conferir insumos
separadamente e reconciliar todas as páginas das tabelas principais.

Registrar responsável humano, data, decisão, justificativa, IDs revisados e hash
do manifesto. Uma alteração no conteúdo invalida a revisão correspondente.
Rejeições e pendências devem permanecer visíveis no relatório. Fontes auxiliares
precisam de revisão de aplicabilidade, versão, instituição e vigência própria.

**Estado atual:** todo o corpus ampliado permanece experimental. O fluxo de
exportação, revisão e publicação está implementado em `scripts/curate_corpus.py`;
consulte [SPEC-08-publication.md](SPEC-08-publication.md). A exportação inicial contém 2728 decisões pendentes
em `data/curation/revisao-corpus-v1.json`. Nenhuma aprovação humana foi criada.
Após revisão real e publicação, usar `app.py chat --curated DIRETORIO_DO_RELEASE`.
As contagens e os testes técnicos não substituem essa etapa.
