# SPEC-09 — Recuperação híbrida sobre release consolidado v7 aprovado

**Estado:** gate documental v7 fechado; próxima validação é a qualidade da recuperação exata/lexical e a revisão humana do conjunto de avaliação. A implementação vetorial continua condicionada aos resultados dessa validação.

## Decisão e justificativa

O catálogo identifica apresentações por campos estruturados antes de qualquer ranking. A consulta lexical (BM25) é a linha de base porque nomes, números, unidades, códigos, formas e características de liberação têm significado literal. Embeddings podem recuperar linguagem não literal e reordenar evidências, mas não podem transformar similaridade em equivalência de apresentações. A recuperação híbrida combina os rankings somente dentro do conjunto permitido pelos filtros. Elastic distingue busca lexical, semântica e híbrida por esse tipo de necessidade; Weaviate descreve a fusão lexical/vetorial e a necessidade de fixar pesos explicitamente. Nenhuma dessas referências demonstra ganho no corpus deste projeto.

Referências: [Elastic — Search approaches](https://www.elastic.co/docs/solutions/search/search-approaches); [Weaviate — Hybrid search](https://docs.weaviate.io/weaviate/concepts/search/hybrid-search).

## Gate de entrada e artefatos

- Release aprovado: `corpus-consolidado-v7-aprovado-2026-11-11`, F01/F03/F04. O manifesto contém 2.114 ocorrências/evidências, 1.860 entradas de catálogo e uma exclusão. Fingerprint de conteúdo `9ad9a3a7f50dc69005daba390bc2b07fb3710f4e54216faf0dca5cb8b346e327`; SHA-256 do manifesto `8399f37f6664f474c18622d912ad9795f04ec199102724cfaafbe6e295eeab20b`, usado pelo carregador para vincular índice e release.
- Gate documental fechado: hashes dos três PDFs, correspondência bidirecional página/linha, 205 normalizações aceitas na planilha e quatro códigos F03 corrigidos, vínculos ocorrência–evidência e [decisão de Jhiovana](../reports/revisao-v6-jhiovana.md) registrados. O release aprovado é imutável. Correção futura de conteúdo gera outro release/fingerprint. O vínculo com chunks deve ser validado na etapa de chunking.
- `exact_presentation_supported=false` significa que a fonte omitiu pelo menos concentração ou forma. Isso não proíbe recuperar a ocorrência, mas proíbe confirmar uma apresentação completa que a fonte não descreveu. As contagens de 1.781 completas/79 parciais são de **entradas de catálogo**, não de linhas do PDF.
- `Data-Science/` fornece ideias e código comparador. Seus relatórios anteriores são históricos, de outro corpus e de avaliador que atribui pontuações por regras; não serão usados como prova de desempenho da v7.

## Contrato da camada de dados

Entrada de busca: `{question, release_fingerprint, source_filter?, top_k=5, strategy}`. `source_filter` é opcional e restrito a F01/F03/F04. `strategy` aceita `exact`, `lexical`, `vector`, `hybrid` para experimento; o padrão operacional inicial é `lexical` até o gate de benchmark.

Saída estruturada: `status` (`matched|ambiguous|not_in_scope|unsupported|blocked|error`), `candidate_presentations[]`, `ranked_evidence[]`, `retrieval_strategy_used`, `fallback_reason?`, `timing_ms` e `provenance`. Cada apresentação contém ID, nome literal, concentração, forma, liberação, `exact_presentation_supported`, fontes e campos ausentes. Cada evidência contém ID, occurrence ID, chunk ID, fonte, versão, página, URL, fingerprint e posições lexical/vetorial/final quando disponíveis. Nenhuma resposta documental contém saldo de estoque. Estoque é um objeto separado, com código e descrição validados, canal UBS/CEAF, região, unidade, saldo/status, data do painel, horário da consulta e origem.

## Algoritmo

1. Normalizar caixa, acentos e espaços para procurar candidatos; preservar literais da fonte. Normalização de número/unidade não altera valor nem transforma sal, associação, liberação ou dispositivo em sinônimo. Correspondências divergentes ficam visíveis como opções.
2. Filtrar somente campos fornecidos com segurança. Nome isolado lista todas as apresentações. Ambiguidade pede escolha; ausência de campo na fonte permanece desconhecida. Fonte explicitada restringe a evidência documental.
3. Dentro dos IDs de apresentação elegíveis, executar BM25 e, havendo índice compatível, busca vetorial. Vetores de outros IDs são descartados **antes da fusão**. Para experimentos vetoriais isolados, os mesmos filtros estruturados continuam obrigatórios.
4. Híbrido inicial: `RRF(d) = 1/(60 + rank_lexical(d)) + 1/(60 + rank_vector(d))`, com posição começando em 1, contribuição zero quando ausente, desempate por chunk ID, top 5. Pesos alternativos e limiar de abstenção podem ser calibrados apenas no split `dev`; registrar valores congelados antes de `test`.
5. Índice ausente, incompatível ou serviço vetorial indisponível: retornar ranking lexical com motivo explícito. Não usar um índice de outro fingerprint/modelo. A geração pode continuar com evidências lexicais; falha de geração devolve evidência documental citada.

## DVC e índice

Há um único projeto DVC na raiz de `engenharia-dados`. Rastrear release aceito, chunks canônicos e índice Chroma por fingerprint/modelo/receita; arquivos de código, manifests pequenos, parâmetros e `dvc.lock` ficam em Git. Remoto **Google Drive compartilhado**, apontado pelo ID da pasta (`gdrive://<folder-id>`), com acesso nominal nos dois computadores. OAuth e tokens ficam apenas em armazenamento local do DVC, nunca no Git. Verificar push no Windows e pull no Mac por hash. A autenticação padrão do DVC para Drive pode exigir um cliente OAuth próprio se o aplicativo padrão estiver bloqueado; verificar isso antes de transferir os artefatos. Não incluir perguntas, CEP, endereço, conversas nem snapshots de estoque pessoais no remoto.

Indexação é retomável por chunk ID; validar dimensão, modelo, cardinalidade e IDs exatos antes de publicar marcador. Mudar release, chunking ou modelo exige índice distinto. Os dados DVC e os marcadores devem permitir reconstruir a execução. Referência: [DVC — Google Drive](https://s.dvc.org/user-guide/data-management/remote-storage/google-drive).

## Avaliação e rastreabilidade

- Conjunto sintético revisado, separado por `family_id` entre `dev` e `test`. O conjunto v6 `agent_reviewed` é rascunho técnico até revisão humana registrada e pode ser migrado para v7 somente após conferência dos IDs e expectativas. Incluir nome isolado, dosagem, forma, sal, liberação, associação, grafias, pergunta em linguagem comum, fonte, negativo e evidência parcial. Referências nunca entram no índice.
- A linha de base exploratória v6 (Hit@5 lexical 0,4605 em 76 positivos `dev`) não é transferível para a v7. Reexecutar após revisão do dataset e investigar especialmente F03 e confusões de apresentação antes de adicionar embeddings.
- Rodar as quatro estratégias com mesmas perguntas, release e top 5. Registrar Hit@1/3/5, Recall@5, MRR@5, acerto de apresentação, confusão crítica, abstenção correta, precisão de citação, latência p50/p95 e cobertura de falhas; custos/tokens somente se medidos.
- Artefato por execução: hash do dataset, fingerprint do release, commit Git, hash dos chunks, modelo/dimensão de embeddings, estratégia/parâmetros, versões de ferramentas, IDs ranqueados, status e tempos. Salvar somente perguntas sintéticas. Mostrar por estrato e agregado, com denominadores explícitos e intervalos de confiança quando válidos.
- Após congelar o ranking no `dev`, executar `test` uma vez. Aprovar híbrido apenas com zero confusões críticas e ganho mensurável sobre lexical sem piora material de citações, erros ou latência. Se falhar, manter lexical e publicar o resultado negativo.
- Avaliar geração separadamente, com versão fixada do RAGAS (faithfulness, response relevancy, context recall), mesma evidência por pergunta e revisão humana de afirmações/citações. Métrica automática não valida dose, elegibilidade ou equivalência clínica. Referência: [RAGAS — métricas](https://docs.ragas.io/en/latest/concepts/metrics/available_metrics/).

### Linha de base e critérios de decisão

O único número disponível é [exploratório e pertence à v6](../reports/baseline-recuperacao-v6-dev.md): `dev` com 91 casos, 76 positivos esperados, Hit@5 = MRR@5 = 0,4605 e acerto de status = 0,5495 para `exact` e `lexical`; F01 = 0,3448 (29 positivos), F03 = 0,1000 (20) e F04 = 0,8519 (27). `reviewed_cases=0`. Esses valores indicam falhas a investigar, mas não servem como referência numérica oficial da v7. Uma mesma pontuação para `exact` e `lexical` pode indicar que o filtro de identidade termina a busca antes do ranking; a causa deve ser verificada caso a caso.

Antes de usar o conjunto como teste oficial, Jhiovana deve revisar pergunta, apresentação esperada, evidência/página esperada, status esperado, família e estrato de cada caso. Guardar o CSV/JSONL de decisões e seu hash; congelar `test` após a revisão. Não deslocar casos entre `dev` e `test` por conveniência depois de observar resultados. Erros de referência, negativos falsos, ambiguidade real e erro do recuperador terão etiquetas distintas.

**Definições de medição:** Hit@k = fração dos casos positivos cuja evidência correta aparece nos primeiros k resultados; MRR@5 = média de `1/rank` da primeira evidência correta, zero quando ausente; acerto de status usa todos os casos, inclusive negativos; confusão crítica conta retorno como `matched` de concentração, forma, associação, sal ou liberação diferente da pergunta. Denominadores por fonte e estrato devem acompanhar cada resultado. Medir p50/p95 da busca separadamente de embeddings de consulta e geração. Custo em moeda ou tokens só entra se registrado pela execução.

O gate de qualidade tem duas camadas. Primeiro, **zero confusões críticas** e 100% de citações verificáveis em casos devolvidos como `matched`; uma falha de identidade bloqueia qualquer promoção de estratégia. Segundo, o híbrido deve superar o lexical em Hit@5 ou MRR@5 no `test` revisado, sem piora material de acerto de status, citações ou p95. Registrar comparação pareada por pergunta, denominadores e intervalo por bootstrap quando a amostra permitir; se a diferença for inconclusiva, manter lexical. O tamanho pequeno e a ausência atual de revisão humana impedem uma alegação de superioridade estatística neste momento.

### Ordem operacional após esta spec

1. Configurar DVC localmente e um remoto Drive por ID de pasta compartilhada; verificar `push` no Windows e `pull` no Mac antes de depender dele como única cópia dos artefatos.
2. Gerar chunks canônicos somente da v7 aprovada; conferir cardinalidade, IDs, fonte, versão, página, conteúdo e hash da receita. Falha de qualquer vínculo bloqueia indexação.
3. Rodar exata e BM25 na v7 com o conjunto revisado; classificar os erros por filtro de apresentação, extração, referência, ranqueamento e ambiguidade. Resolver erros de identidade antes de vetorizar.
4. Fixar modelo, dimensão, chunking e parâmetros de embedding em manifesto; vetorizar com retomada por chunk ID e verificar cobertura 1:1 e hashes.
5. Executar exata, lexical, vetorial e híbrida no mesmo split e top-k. Ajustar somente no `dev`; congelar parâmetros e executar `test` uma vez. Publicar resultados positivos ou negativos com métricas por estrato.
6. Avaliar geração com RAGAS e revisão humana de alegações/citações; somente então entregar ao agente o contrato de evidências e, separadamente, o contrato de estoque validado.

## Limites

Presença em lista não comprova estoque ou elegibilidade. A API de estoque é consultada por código e descrição validados, fora do ranking documental, com data do painel distinguida da hora da consulta. O agente cuida de diálogo e esclarecimentos; a camada de dados devolve fatos, proveniência, ambiguidade e falhas sem inventar vínculos.
