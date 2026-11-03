# SUS Cidadão — documentação de estudo da parte de dados

Este documento explica, de forma didática, o que foi feito na frente de Engenharia de Dados do projeto SUS Cidadão, por que cada parte existe e como o trabalho pode ser reproduzido e continuado.

Ele não é uma especificação formal de arquitetura. A ideia é servir como material de estudo e como apoio para apresentar o trabalho ao grupo.

## 1. Qual é o problema que estamos tentando resolver?

O SUS Cidadão precisa responder perguntas sobre medicamentos, locais de atendimento, documentos necessários e orientações de serviços de saúde.

Para responder com segurança, não basta colocar alguns textos em uma aplicação. Primeiro precisamos:

1. encontrar fontes oficiais;
2. preservar exatamente o que foi coletado;
3. registrar quando e de onde veio cada informação;
4. extrair e organizar o conteúdo;
5. revisar as informações antes de apresentá-las ao usuário;
6. deixar claro o que a fonte realmente comprova.

Um exemplo importante: um medicamento aparecer na RENAME ou na REME-DF não prova que ele está disponível hoje em uma unidade específica. A fonte pode provar que o item faz parte de uma relação, mas não necessariamente informar estoque, endereço ou direito individual de retirada.

## 2. O que já foi feito

Até agora, construímos a fundação do pipeline de dados. O trabalho atual já consegue:

- preservar documentos oficiais em formato original;
- guardar a origem e os metadados da coleta;
- calcular um hash para conferir a integridade dos arquivos;
- extrair o texto dos PDFs página por página;
- organizar os resultados em camadas `raw`, `bronze`, `silver` e `gold`;
- gerar um catálogo dos documentos processados;
- repetir o processamento sem sobrescrever artefatos já existentes;
- manter contratos de ingestão e armazenamento separados da implementação concreta.

O pipeline documental já foi executado para cinco PDFs oficiais.

## 3. Fontes coletadas

Os arquivos estão em `data/raw/` e são registrados em `data/manifests/coleta-inicial-pdfs-2026-11-03.json`.

| Identificador | Fonte | Finalidade | Páginas |
|---|---|---|---:|
| F01 | RENAME 2024, 2ª edição | Referência nacional de medicamentos essenciais | 267 |
| F03 | REME-DF, edição de 29/10/2026 | Relação de medicamentos do Distrito Federal | 98 |
| F04 | Elenco do Farmácia Popular | Medicamentos e insumos do programa | 1 |
| F11 | Dicionário de dados de medicamentos da Anvisa | Entender campos e registros da base | 7 |
| F12 | Carta de Serviços do HUB-UnB | Serviços, orientações e atendimento | 86 |

Esses documentos foram baixados de endereços oficiais. O manifesto registra, entre outras informações:

- URL consultada;
- URL final do download;
- data e hora da coleta em UTC;
- status HTTP;
- tipo de conteúdo;
- tamanho do arquivo;
- quantidade de páginas;
- hash SHA-256;
- situação da revisão.

### O que a coleta significa — e o que não significa

Coletar um documento significa que conseguimos preservá-lo e registrar sua origem. Isso não significa que o conteúdo já foi aprovado para uso no produto.

Ainda precisamos revisar a aplicabilidade de cada fonte, conferir versões, interpretar notas e confirmar quais campos podem ser usados com segurança.

Também é importante diferenciar um dicionário de dados da Anvisa de uma base de medicamentos: o arquivo F11 explica campos e registros, mas não substitui o CSV com os dados.

## 4. Como os dados são organizados

O projeto usa uma ideia comum de engenharia de dados: separar o arquivo original dos dados transformados.

```text
data/raw       -> arquivo original coletado
       |
       v
data/bronze    -> cópia processada com metadados e hash
       |
       v
data/silver    -> conteúdo extraído e organizado por página
       |
       v
data/gold      -> catálogo e visões prontas para consumo
```

### 4.1 Raw

`data/raw/` contém os PDFs originais. Eles devem permanecer sem alteração, porque são a evidência do que foi recebido da fonte.

Se uma fonte publicar uma nova versão, a nova versão deve ser guardada como outro artefato, com novos metadados. Não devemos substituir silenciosamente o arquivo antigo.

### 4.2 Bronze

A camada Bronze preserva o conteúdo recebido junto de informações sobre a coleta.

Cada documento recebe um envelope com duas partes principais:

- `metadata`: fonte, URL, datas, status, hash e caminho do arquivo;
- `payload`: conteúdo processado em uma representação inicial, neste caso o PDF dividido em páginas.

A Bronze é importante para auditoria. Se alguém perguntar de onde veio uma informação, podemos voltar ao documento e ao hash que originaram o processamento.

### 4.3 Silver

A Silver contém o texto extraído dos PDFs, separado por página. Ela é mais fácil de consultar e transformar do que o PDF, mas ainda mantém a referência ao documento de origem.

Nesta etapa, o conteúdo ainda não é necessariamente uma tabela perfeita de medicamentos. PDF é um formato de apresentação e pode misturar títulos, tabelas, notas, quebras de linha e cabeçalhos. Por isso, a extração de texto é apenas uma etapa intermediária.

### 4.4 Gold

A Gold é a camada de dados derivados para consumo. Atualmente ela contém `data/gold/document_catalog.json`, que reúne informações como:

- identificador da fonte;
- nome do documento;
- URL;
- hash;
- total de páginas;
- quantidade de páginas não vazias;
- caminho do artefato Silver.

A Gold não deve ser editada manualmente como se fosse a fonte original. Ela deve ser recriada a partir das camadas anteriores.

## 5. Como o pipeline funciona

O ponto de entrada está em:

`src/sus_cidadao_data/pipeline.py`

O fluxo simplificado é:

1. ler o manifesto de coleta;
2. percorrer cada fonte listada;
3. abrir o PDF em `data/raw/`;
4. calcular o SHA-256 do arquivo;
5. extrair o texto das páginas;
6. criar o artefato Bronze se ele ainda não existir;
7. criar os registros Silver por página se ainda não existirem;
8. adicionar o documento ao catálogo Gold;
9. salvar `document_catalog.json`;
10. retornar contagens do processamento.

O pipeline é idempotente. Isso quer dizer que executá-lo novamente com os mesmos arquivos não deve criar cópias duplicadas nem sobrescrever o Bronze e a Silver já existentes.

O hash é usado como identificador do conteúdo. Se o arquivo mudar, o hash também muda, permitindo distinguir versões.

## 6. Organização do código

### `src/sus_cidadao_data/pipeline.py`

Implementa o fluxo atual dos documentos: manifesto, leitura dos PDFs, geração de Bronze, Silver e Gold.

### `src/sus_cidadao_data/ingestion/base.py`

Define o contrato base para conectores de ingestão. A ideia é que um conector saiba coletar uma fonte, mas não precise conhecer detalhes de banco de dados ou da camada de negócio.

### `src/sus_cidadao_data/storage/base.py`

Define interfaces de armazenamento, como Bronze e Silver. Isso evita espalhar uma escolha de tecnologia por todo o sistema.

### `src/sus_cidadao_data/storage/bronze.py`

Contém a implementação local `JsonBronzeStore`, que grava payloads e metadados em JSON.

### `src/sus_cidadao_data/storage/silver.py`

Contém uma implementação inicial em memória para a Silver e serve como ponto de extensão para uma persistência mais completa.

### `tests/`

Contém testes dos contratos de ingestão e do armazenamento Bronze. Os testes ajudam a verificar que a estrutura básica não seja quebrada durante a evolução do projeto.

## 7. Documentos de apoio

Os principais documentos do projeto são:

- `README.md`: visão geral do repositório;
- `data/README.md`: explicação dos dados coletados e como reproduzir o pipeline;
- `docs/levantamento-fontes.md`: levantamento das fontes candidatas e suas limitações;
- `docs/engenharia-dados/especificacao-ingestao-armazenamento.md`: decisões e contratos técnicos da ingestão e do armazenamento;
- `docs/especificacao-funcional-mvp.md`: comportamento esperado do MVP;
- `docs/sdd-arquitetura-engenharia-dados.md`: documentação formal da arquitetura.

Este arquivo complementa esses documentos com uma explicação mais acessível para estudo e apresentação.

## 8. Como reproduzir o processamento

Na raiz do projeto, execute:

```bash
uv run python -m src.sus_cidadao_data.pipeline
```

O comando lê os PDFs já existentes e gera ou atualiza os artefatos derivados.

Para executar os testes:

```bash
uv run pytest -q
```

Se o ambiente `uv` não puder usar o cache padrão por causa de permissões, pode ser usado um cache temporário:

```bash
UV_CACHE_DIR=/tmp/codex-uv-cache uv run pytest -q
```

As pastas `data/bronze`, `data/silver` e `data/gold` são dados derivados locais. Os marcadores `.gitkeep` permanecem no repositório, mas os artefatos gerados não precisam ser versionados junto com o código.

## 9. O que ainda não foi feito

A base atual é uma fundação; ainda não é o conjunto final de dados do produto.

As próximas etapas mais importantes são:

1. extrair tabelas de medicamentos para um formato estruturado;
2. separar princípio ativo, concentração, forma farmacêutica e apresentação;
3. relacionar RENAME, REME-DF e Farmácia Popular sem misturar significados;
4. revisar notas e exceções de dispensação;
5. validar canais de retirada e documentos exigidos;
6. identificar fontes oficiais de unidades e estoque;
7. registrar a data de atualização e a validade de cada informação;
8. criar um pequeno conjunto de exemplos revisados, o chamado golden set;
9. testar duplicidades, campos ausentes, mudanças de layout e versões de documentos;
10. só então disponibilizar as informações para busca e respostas ao usuário.

## 10. Limitações que precisamos comunicar

Para evitar respostas incorretas, o sistema não deve inferir:

- disponibilidade de estoque a partir da presença em um catálogo;
- direito individual de acesso a partir de uma lista de medicamentos;
- existência de atendimento em uma unidade apenas porque a unidade aparece em uma página;
- concentração ou forma farmacêutica quando a fonte não informa claramente;
- atualização atual de uma página usando somente a data do índice;
- equivalência entre versões diferentes de um mesmo documento.

Campos que não aparecem na fonte devem permanecer ausentes ou nulos. É melhor informar que algo não foi localizado do que preencher com uma suposição.

## 11. Como explicar o trabalho ao grupo

Uma explicação curta seria:

> “Nós estruturamos a base de dados do SUS Cidadão começando pelas fontes oficiais. Coletamos cinco PDFs, preservamos os originais e registramos URL, data, status, tamanho e hash para garantir rastreabilidade. Depois criamos um pipeline em camadas: Raw guarda o original, Bronze guarda o conteúdo com metadados, Silver guarda o texto extraído por página e Gold gera um catálogo dos documentos. O pipeline é reproduzível e idempotente. O próximo passo é transformar esse conteúdo em dados estruturados e revisados sobre medicamentos, canais e documentos, sempre deixando claro que um item em uma lista não significa necessariamente estoque disponível.”

## 12. Resumo final

O projeto está em uma etapa saudável: a fundação de coleta, preservação e processamento já existe, as fontes estão identificadas e as limitações estão documentadas.

O trabalho ainda não terminou porque a parte mais importante para o produto é a normalização e validação do conteúdo. A sequência recomendada é começar com um recorte pequeno de medicamentos, produzir registros estruturados e revisados, e só depois ampliar para os demais serviços e para dados de estoque.

