# Dados do SUS Cidadão

Esta pasta documenta os conjuntos de dados previstos para o MVP no Distrito Federal: medicamentos, canais de retirada, documentos exigidos e orientações de exames.

**Estado atual:** cinco PDFs oficiais preservados em `raw/`, com origem, URL final, instante de coleta, tamanho, SHA-256 e número de páginas no [manifesto de coleta](manifests/coleta-inicial-pdfs-2026-11-03.json). O pipeline documental já foi executado: `bronze/` contém envelopes por documento/hash, `silver/` contém texto extraído por página e `gold/document_catalog.json` contém o catálogo. A revisão do conteúdo e da aplicabilidade ainda está pendente; o índice de recuperação permanece separado nos artefatos do RAG.

Para reproduzir: `uv run python -m src.sus_cidadao_data.pipeline`. O job é idempotente por SHA-256 e não sobrescreve Bronze/Silver existentes.

Os identificadores F01–F14 correspondem ao [levantamento detalhado de fontes](../docs/engenharia-dados/levantamento-fontes.md). O comportamento esperado está na [especificação funcional do MVP](../docs/engenharia-dados/especificacao-funcional-mvp.md).


## Arquivos coletados

| Fonte | PDF original | Páginas | Tamanho |
|---|---|---:|---:|
| F01 | [rename-2024-2ed.pdf](raw/F01-rename/rename-2024-2ed.pdf) | 267 | 1.39 MiB |
| F03 | [reme-df-2026-10-29.pdf](raw/F03-reme-df/reme-df-2026-10-29.pdf) | 98 | 3.54 MiB |
| F04 | [farmacia-popular-elenco-2026-08-31.pdf](raw/F04-farmacia-popular/farmacia-popular-elenco-2026-08-31.pdf) | 1 | 0.07 MiB |
| F11 | [anvisa-dicionario-medicamentos-v1.pdf](raw/F11-anvisa/anvisa-dicionario-medicamentos-v1.pdf) | 7 | 1.20 MiB |
| F12 | [hub-unb-carta-servicos.pdf](raw/F12-hub-unb/hub-unb-carta-servicos.pdf) | 86 | 19.67 MiB |

Os PDFs foram preservados sem alteração. As pastas usam o identificador e o nome da fonte (por exemplo, `F01-rename`). Os hashes permanecem no manifesto para conferir integridade; novas versões devem receber nomes distintos, sem sobrescrever os originais. Coleta não equivale a aprovação: a edição da carta do HUB ainda exige revisão. O arquivo da Anvisa é um dicionário, não a base CSV de medicamentos.

## 1. Medicamentos e apresentações

### F01 — RENAME: referência nacional

- **Responsável:** Ministério da Saúde.
- **Fonte:** [publicações da RENAME](https://www.gov.br/saude/pt-br/composicao/sectics/rename/publicacoes/).
- **Arquivo localizado:** [RENAME 2024, 2ª edição](https://www.gov.br/saude/pt-br/composicao/sectics/rename/publicacoes/relacao-nacional-de-medicamentos-essenciais-2024), PDF de 267 páginas, com 2025 na folha de rosto.
- **Dados de interesse:** princípios ativos, concentrações, formas farmacêuticas, componentes e notas associados aos itens das tabelas.
- **Uso:** verificar se uma apresentação consta na edição consultada e comparar com as outras listas.
- **Limite:** não comprova estoque, unidade de retirada ou elegibilidade individual.
- **Pendente:** conferir notas, alterações posteriores e os campos do recorte selecionado; original já coletado.

### F02 e F03 — REME-DF: relação distrital

- **Responsável:** Secretaria de Saúde do Distrito Federal (SES-DF).
- **Página de referência (F02):** [REME-DF](https://www.saude.df.gov.br/reme-df).
- **Arquivo selecionado (F03):** [REME-DF de 29/10/2026](raw/F03-reme-df/reme-df-2026-10-29.pdf), PDF de 98 páginas (`https://www.saude.df.gov.br/documents/d/saude/reme_df___29_10_2026___final-pdf`).
- **Dados de interesse:** medicamentos e apresentações, níveis de atenção, seções e notas que contextualizam a dispensação na rede distrital.
- **Uso:** consultar presença na relação do DF e apoiar a identificação do canal de atendimento quando documentado.
- **Limite:** itens hospitalares, de emergência ou em aquisição não podem ser apresentados automaticamente como disponíveis para retirada ambulatorial.
- **Pendente:** extração tabular e revisão das notas de dispensação da edição 2026. A versão de 2024 foi retirada do repositório e não deve entrar no corpus.

### F04 — Elenco do Farmácia Popular

- **Responsável:** Ministério da Saúde.
- **Fonte:** [elenco de medicamentos e insumos](https://www.gov.br/saude/pt-br/composicao/sectics/farmacia-popular/arquivos/elenco-de-medicamentos-e-insumos-pfpb.pdf).
- **Formato/versão identificados:** PDF de uma página, atualizado em 31/08/2026.
- **Dados de interesse:** princípios ativos, associações, quantidades declaradas e insumos do programa.
- **Uso:** verificar presença no elenco e iniciar a seleção do pequeno lote de medicamentos do MVP.
- **Limite:** algumas linhas não explicitam todos os campos necessários para identificar uma apresentação. Insumos e medicamentos devem permanecer diferenciados; dados ausentes não serão inferidos.
- **Pendente:** conferência visual e complementação documental de forma, concentração ou liberação quando necessário. Não misturar com o arquivo anterior de 2025.

## 2. Canais de retirada e documentos necessários

### F05 — Regras de acesso ao Farmácia Popular

- **Fonte:** [página do programa](https://www.gov.br/saude/pt-br/composicao/sectics/farmacia-popular), Ministério da Saúde, HTML.
- **Dados de interesse:** documentos, condições administrativas e regras de representação descritas nas seções de acesso.
- **Uso:** explicar o que apresentar para o cenário documentado.
- **Limite:** não decide direito individual e não informa estoque. Endereços de farmácias credenciadas no DF ainda não foram validados.
- **Pendente:** revisar regras completas, exceções, referências e datas; localizar o cadastro de estabelecimentos se o produto precisar indicar endereços.

### F06 — Farmácias da rede e atenção primária

- **Fontes:** [índice de farmácias](https://www.saude.df.gov.br/farmacias/) e [farmácias das UBS](https://www.saude.df.gov.br/farmacias-unidade-basica-de-saude/), SES-DF, HTML.
- **Dados de interesse:** tipos de farmácia e instruções de atendimento; unidades, contatos e documentos somente quando efetivamente publicados.
- **Uso:** orientar sobre o canal de atenção primária.
- **Limite:** uma UBS existir ou estar próxima não prova que dispensa determinado medicamento.
- **Pendente:** revisão completa e vínculo documentado entre apresentação, canal e unidade.

### F07 — Farmácias da atenção secundária

- **Fonte:** [policlínicas, CAPS e Farmácia Escola](https://www.saude.df.gov.br/farmacias-atencao-secundaria/), SES-DF, HTML.
- **Dados de interesse:** orientações por serviço, requisitos e locais documentados.
- **Uso:** explicar canais da atenção secundária no recorte selecionado.
- **Limite:** requisitos de um serviço não valem automaticamente para os demais.
- **Pendente:** revisar página e anexos correspondentes aos medicamentos escolhidos.

### F08 — Componente especializado

- **Fonte localizada:** [componente especializado](https://www.saude.df.gov.br/componente-especializado/), SES-DF.
- **Dados pretendidos:** documentos e fluxos específicos do componente especializado.
- **Uso previsto:** orientar o acesso quando houver evidência para o medicamento e contexto selecionados.
- **Estado:** a leitura retornou timeout durante a pesquisa; conteúdo ainda não validado.
- **Limite:** não generalizar exigências como LME para todos os medicamentos ou canais.

### F09 — Norma distrital de dispensação

- **Fonte:** [Portaria SES-DF nº 117, de 20/02/2026](https://www.sinj.df.gov.br/sinj/Norma/2fc01aa935834c729138eea708b7a9bd/Portaria_117_20_02_2026.html), texto compilado no SINJ, HTML.
- **Dados de interesse:** artigos que fundamentam documentos, condições e exceções administrativas nas farmácias ambulatoriais.
- **Uso:** conferir as orientações extraídas das páginas de atendimento.
- **Limite:** não utilizar disposições de prescrição para gerar aconselhamento clínico.
- **Pendente:** confirmar alterações e aplicabilidade, registrando o artigo que sustenta cada regra selecionada.

## 3. Vocabulário e nomes comerciais

### F10 — DCB: nomes padronizados de substâncias

- **Responsável:** Anvisa.
- **Fonte:** [Denominações Comuns Brasileiras](https://www.gov.br/anvisa/pt-br/assuntos/farmacopeia/dcb).
- **Dados de interesse:** denominações e identificadores disponíveis na consolidação selecionada.
- **Uso:** padronizar nomes e reduzir diferenças de escrita entre fontes.
- **Limite:** identificar uma substância não identifica sua apresentação, marca ou equivalência terapêutica.
- **Estado:** página localizada; biblioteca vinculada retornou 403. Consolidação vigente ainda não coletada.

### F11 — Cadastro de medicamentos registrados

- **Responsável:** Anvisa.
- **Fontes:** [diretório de dados](https://dados.anvisa.gov.br/dados/) e [dicionário localizado](https://dados.anvisa.gov.br/dados/Documentacao_e_Dicionario_de_Dados_Registros_Validos_Medicamento_V1.pdf).
- **Recurso candidato:** `DADOS_ABERTOS_MEDICAMENTOS.csv`, mencionado em página oficial da Anvisa; não baixado nem perfilado.
- **Dados pretendidos:** vínculos entre produto comercial, substâncias e registro, conforme o esquema efetivamente disponível.
- **Uso:** apoiar um conjunto limitado de nomes comerciais revisados.
- **Limite:** os campos e a granularidade ainda não foram confirmados. Registro sanitário não comprova presença nas listas do SUS, nem autoriza correspondência automática de apresentação.
- **Pendente:** obter o CSV e revisar o dicionário já coletado; conferir situação de registro, datas, campos e necessidade de fontes complementares.

## 4. Exames e acesso aos serviços

### F12 — Carta de serviços do HUB-UnB

- **Responsável:** Hospital Universitário de Brasília, em portal federal.
- **Fonte:** [Carta de serviços aos usuários](https://www.gov.br/hubrasil/pt-br/hospitais-universitarios/regiao-centro-oeste/hub-unb/acesso-a-informacao/acoes-e-programas/Cartadeserviosaosusurios_HUBUnB1.pdf), PDF.
- **Dados identificados:** documentos para realização de exames, na página impressa 43; orientação para seguir o preparo informado no agendamento, na página 42.
- **Uso:** responder sobre documentação no HUB e reconhecer quando falta orientação específica de preparo.
- **Limite:** o trecho inspecionado não estabelece horas de jejum por exame. Não aplicar regras do HUB a outras instituições.
- **Pendente:** confirmar edição e obter instruções específicas dos exames/serviços escolhidos.

### F13 — Protocolos de acesso da SES-DF

- **Fonte:** [protocolos de acesso vigentes](https://www.saude.df.gov.br/acesso-vigentes), índice HTML com links e intervalos de vigência.
- **Dados de interesse:** procedimento, fluxo de encaminhamento, requisitos e aplicabilidade nos documentos selecionados.
- **Uso:** orientar o caminho administrativo de acesso a exames e serviços.
- **Limite:** protocolo de acefsso não equivale a instrução de preparo. O índice não fornece acesso operacional ao SISREG.
- **Estado:** índice inspecionado; PDFs individuais ainda não revisados.

**Lacuna atual:** não há 5–10 exames com preparo homologado. Precisamos escolher os serviços e obter suas instruções oficiais. A base não deve preencher essa lacuna com regras genéricas ou conteúdo de outra instituição.

## 5. Estoque: referência, sem integração

### F14 — Painéis e dados abertos do DF

- **Fontes localizadas:** [painel de estoque](https://info.saude.df.gov.br/saude-do-cidadao/painel-infosaude-farmacias-de-alto-custo/estoque-de-medicamentos/) e [dados abertos](https://info.saude.df.gov.br/transparencia-e-prestacao-de-contas/dados-abertos/).
- **Uso previsto:** encaminhar ao canal oficial após verificar seu funcionamento.
- **Pendente:** cobertura de unidades, periodicidade, significado dos campos e possibilidade de exportação. Nenhuma API foi confirmada.
- **Regra do MVP:** exibir “Estoque não consultado”; presença em lista ou existência de um painel não confirma disponibilidade física.

## 6. Fontes que não devem alimentar orientações gerais

| Referência do levantamento | Motivo |
|---|---|
| X01 — POMED/CBMDF | Público e serviço específicos; não representa o atendimento geral do SUS-DF |
| X02 — Nota nº 9/2024 sobre LF-LAM | Contexto especializado; não usar suas instruções para outros exames de urina |
| X03 — Outras cidades, fontes privadas e notícias | Não substituem a fonte oficial aplicável ao serviço selecionado |

Os links e detalhes das exclusões estão no levantamento. Esses documentos podem embasar testes de não generalização, mas não devem ser incorporados inadvertidamente ao corpus de respostas do MVP.

## 7. Dados que serão produzidos pelo projeto

Os campos abaixo são os dados pretendidos, não um esquema já implementado nem a garantia de que todas as fontes os contenham.

| Conjunto derivado | O que representa | Campos principais |
|---|---|---|
| Apresentações | Identidade completa do item consultado | Princípios ativos, quantidades/unidades, concentração, forma e liberação quando documentada |
| Presença nas listas | Relação entre item e edição de uma lista | Apresentação, fonte, versão, seção e página |
| Nomes comerciais | Correspondências revisadas | Marca, apresentação/composição, evidência e revisão |
| Canais de acesso | Caminho administrativo documentado | Programa, canal, unidade quando conhecida, documentos, condições e aplicabilidade |
| Exames | Orientação vinculada a exame e serviço | Nome exato, material, serviço, documentos e preparo documentado |
| Trechos para recuperação | Passagens revisadas de documentos | Texto, fonte/versão, localizador, território, serviço e validade quando conhecida |
| Golden set | Perguntas e referências para avaliação | Categoria, contexto, evidências, fatos obrigatórios/proibidos, comportamento esperado, resposta de referência, divisão e revisão |
| Resultados de avaliação | Evidência do desempenho observado | Caso, execução, saída, evidências recuperadas, métricas, tempo e erros |

O golden set deve ficar separado dos documentos usados na recuperação. Suas perguntas e respostas não podem entrar no índice. Resultados só serão registrados após execução; metas não são resultados medidos.

## 8. Proveniência mínima por coleta e registro

| Campo | Finalidade |
|---|---|
| Identificador da fonte | Relacionar o arquivo ao catálogo F01–F14 |
| Órgão, título e URL original/final | Identificar origem e eventuais redirecionamentos |
| Edição ou versão declarada | Saber qual documento foi usado |
| Publicação e vigência, quando conhecidas | Distinguir quando foi publicado e quando se aplica |
| Data/hora da coleta e da verificação | Registrar quando o projeto obteve e conferiu a fonte |
| Arquivo original, formato, tamanho e SHA-256 | Preservar e identificar o conteúdo exato recebido |
| Página, seção, tabela ou artigo | Localizar a evidência de cada informação derivada |
| Território, serviço e público | Evitar aplicação fora de contexto |
| Estado, responsável e data da revisão | Separar conteúdo pendente, aprovado e rejeitado |
| Versão da publicação do projeto | Reproduzir o conjunto usado em uma consulta ou avaliação |

Quando uma informação não estiver disponível, registrar o motivo. Não substituir data de publicação por coleta nem interpretar campo ausente como “não exigido”. Originais de versões diferentes devem permanecer distinguíveis.

## 9. Organização prevista da pasta

`raw/` e `manifests/` já contêm a coleta inicial indicada acima. Os demais diretórios são propostos e ainda não foram criados.

| Diretório proposto | Conteúdo |
|---|---|
| `raw/` | Originais públicos preservados por fonte e versão |
| `manifests/` | Metadados de coleta, hashes e identificação de versões |
| `interim/` | Extrações intermediárias ainda não aprovadas |
| `quarantine/` | Registros com problemas ou ambiguidades, fora da publicação |
| `processed/` | Dados normalizados e revisados |
| `releases/` | Conjuntos aprovados e identificados por versão |
| `evaluation/` | Golden set e resultados, separados do corpus de recuperação |

Antes de versionar arquivos brutos, verificar tamanho e condições de redistribuição. A decisão de armazenamento não altera a necessidade de preservar os originais e seus hashes.

## 10. Regras para uso e atualização

- Somente conteúdo revisado pode sustentar respostas ao cidadão.
- F01, F03, F04, o dicionário de F11 e F12 já foram coletados. A F03 de 29/10/2026 foi escolhida para o corpus; priorizar agora sua revisão de conteúdo e a coleta das regras administrativas.
- Verificar as fontes semanalmente e antes da demonstração, conforme proposta da especificação. Isso não significa que os órgãos atualizem os dados semanalmente.
- Registrar mudanças e revisar a nova versão antes de substituir a publicação aprovada.
- Não armazenar dados reais de pacientes, receitas pessoais, documentos de identificação ou histórico de saúde nesta pasta.
- Para testes de imagem, utilizar embalagens sem identificação pessoal e receitas fictícias.
- Não inferir estoque, elegibilidade, preparo, dosagem ou substituição terapêutica a partir de semelhança textual.
