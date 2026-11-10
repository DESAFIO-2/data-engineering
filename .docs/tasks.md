# Tasks

Atualizado em: 10/11/2026.

Lista de trabalho pendente. Marcar cada item somente após executar e verificar o resultado.

## 1. Analisar a entrega do Samuel e mesclar com o trabalho atual

- [ ] Localizar a entrega do Samuel e registrar sua versão, branch ou commit.
- [ ] Comparar código, dados, documentação e resultados com o projeto atual.
- [ ] Identificar contribuições aproveitáveis, duplicidades e conflitos.
- [ ] Definir o que será incorporado e registrar as decisões.
- [ ] Fazer a integração em uma branch de trabalho, preservando as versões anteriores.
- [ ] Resolver conflitos e verificar os fluxos afetados, incluindo chat e sincronização InfoSaúde.

## 2. Refazer chunks, embeddings e índice vetorial

- [ ] Definir a versão do corpus consolidado que será usada como base.
- [ ] Conferir a validação dos chunks primários e decidir quais fontes complementares entram no novo corpus.
- [ ] Revisar a divisão dos chunks, preservando linhas completas, combinações, concentrações, cabeçalhos e notas necessários.
- [ ] Gerar os novos chunks e conferir IDs, proveniência, páginas, hashes e vínculos com ocorrências e catálogo.
- [ ] Definir e registrar o modelo de embeddings, sua configuração e o custo estimado da execução.
- [ ] Comparar textos e configuração com os vetores existentes para decidir quais embeddings podem ser reaproveitados e quais precisam ser recalculados.
- [ ] Gerar os embeddings necessários e construir um índice versionado.
- [ ] Verificar contagens, conteúdo, filtros por fonte e ausência de registros indevidos no índice.
- [ ] Testar a busca de combinações com e sem `+`, concentrações, formas e características de liberação.
- [ ] Conectar o chat ao novo índice e verificar a sincronização do InfoSaúde na abertura.
- [ ] Registrar como retornar à versão anterior caso a nova apresente problemas.

## 3. Refazer as métricas de avaliação

- [ ] Revisar o conjunto de avaliação conforme a versão final do corpus e os novos IDs de evidência.
- [ ] Validar manualmente perguntas, respostas esperadas e evidências de referência.
- [ ] Separar desenvolvimento e teste, preservando o teste final sem ajustes guiados por seus resultados.
- [ ] Definir métricas e critérios de aceitação para recuperação, resposta, citações, abstenção e segurança.
- [ ] Avaliar recuperação exata, lexical, vetorial e híbrida.
- [ ] Avaliar combinações, concentrações, liberação, fontes distintas e perguntas sem evidência suficiente.
- [ ] Avaliar o estoque separadamente, considerando apresentação mapeada, data da extração, falha de sincronização e uso do snapshot local.
- [ ] Medir latência, erros de API e custo/consumo quando aplicável.
- [ ] Comparar os resultados com a versão anterior e investigar regressões.
- [ ] Salvar resultados reproduzíveis com corpus, índice, modelos, configuração e versão do código utilizados.

## 4. Atualizar as documentações

- [ ] Atualizar o README com instalação, configuração e comandos vigentes de chat, indexação, sincronização e avaliação.
- [ ] Documentar a organização final dos corpora, fontes, versões e estados de revisão.
- [ ] Atualizar o controle de correções, distinguindo campos corrigidos de registros integralmente validados.
- [ ] Documentar a estratégia de chunks, embeddings, índice e reaproveitamento de vetores.
- [ ] Explicar o fluxo do chat e os limites da consulta de estoque no InfoSaúde.
- [ ] Registrar as contribuições incorporadas da entrega do Samuel.
- [ ] Atualizar métricas, resultados, limitações e instruções para reproduzir a avaliação.
- [ ] Revisar links e comandos e identificar documentos históricos que já não descrevem a versão atual.

## Ordem sugerida

Analisar e integrar a entrega do Samuel → definir o corpus final → revisar chunks e vetorização → executar a avaliação → finalizar a documentação. Atualizar o controle de decisões e correções durante todas as etapas.
