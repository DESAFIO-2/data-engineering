# Especificação funcional — MVP de Engenharia de Dados do SUS Cidadão

Versão: 0.1 · Data: 03/11/2026 · Estado: proposta para revisão da equipe.
Território: Distrito Federal. Horizonte: aproximadamente seis semanas, até meados de dezembro de 2026.

Este documento especifica comportamentos e critérios de aceite; não comprova que funcionalidades, fontes, integrações ou resultados já existam. Não determina banco de dados, framework, biblioteca ou modelo de IA. As metas de avaliação são propostas a calibrar no piloto e congelar antes da avaliação final.

## 1. Resumo do problema

Cidadãos têm dificuldade para localizar informações oficiais sobre medicamentos, canais de dispensação, documentos e preparo de exames. Uma informação correta em determinada lista, versão ou instituição pode não se aplicar a outra. O MVP deve tornar essas diferenças visíveis e apresentar evidências verificáveis, evitando interpretar presença em lista como estoque ou direito individual assegurado.

## 2. Objetivo do MVP

Disponibilizar um recorte pequeno de dados revisados, com origem rastreável, consultas que reconheçam ambiguidades e avaliação reproduzível. Demonstrar separadamente a qualidade dos dados, a recuperação de evidências e a qualidade das respostas, sem depender da escolha do frontend.

## 3. Valor para o usuário

Permitir identificar se uma apresentação consta nas fontes selecionadas, compreender o próximo passo administrativo documentado e consultar orientações de exames aplicáveis ao serviço escolhido. Cada resposta deve permitir conferir a evidência e reconhecer o que ainda precisa ser confirmado. O benefício esperado é melhor compreensão; redução de filas, deslocamentos ou eventos clínicos não está demonstrada.

## 4. Atores

| Ator | Papel e limites |
|---|---|
| Cidadão ou cuidador | Pesquisa, esclarece ambiguidades, confirma campos de imagens e consulta fontes |
| Revisor de conteúdo | Compara registros com fontes, registra decisões e sinaliza dúvidas de domínio |
| Responsável pelos dados | Mantém recorte, versões, proveniência, publicações e relatórios de qualidade |
| Avaliador | Executa o conjunto congelado, classifica resultados e documenta erros |
| Equipe e instrutor | Confirmam escopo, metas, recursos e requisitos da avaliação acadêmica |

A revisão inicial pode contar com profissional de enfermagem convidado. Dúvidas de apresentação farmacêutica e orientações específicas de laboratório exigem evidência aplicável e eventual revisão especializada. Essa participação não constitui validação clínica institucional.

## 5. Escopo e prioridades

**Obrigatório (O):** condição de aceite do MVP. **Desejável (D):** avaliado separadamente e não bloqueia o núcleo. **Futuro (F):** não integra o aceite desta versão.

| Frente | Prioridade | Limite observável |
|---|---|---|
| Medicamentos | O | 30–50 apresentações distintas, revisadas, com composição, concentração e forma identificadas |
| Fontes de medicamentos | O | Recortes de RENAME, REME-DF e Farmácia Popular; versões e cobertura declaradas, sem pressupor sobreposição entre listas |
| Pesquisa | O | Princípio ativo e conjunto fechado de nomes comerciais com vínculos verificados; publicar quantidade e relação de nomes cobertos |
| Acesso | O | Canal, documentos e condições somente quando sustentados por fonte aplicável |
| Exames | O | 5–10 exames com orientação oficial do serviço selecionado |
| Proveniência e atualização | O | Fonte e data de verificação visíveis; versões anteriores identificáveis |
| Avaliação | O | Aproximadamente 60 casos versionados e relatório separado por dimensão |
| Imagem | D | Experimento com embalagens e receitas fictícias; se habilitado, confirmação de campos e proteção das imagens são obrigatórias |
| Trajetória demonstrativa | D | Apenas personagens e dados sintéticos, explicitamente identificados |
| Histórico real e integrações operacionais | F | Dependem de nova definição de escopo e governança |

O sistema deve informar o recorte disponível antes ou junto do resultado. A cobertura declarada precisa distinguir apresentações cadastradas de fontes integralmente consultáveis.

## 6. Fora do escopo

Diagnóstico ou triagem clínica; prescrição ou recomendação de medicamentos; alteração de doses; substituição terapêutica; garantia de estoque; cobertura completa dos medicamentos e exames do SUS; prontuário ou histórico real; armazenamento permanente de receitas ou imagens; integração completa com sistemas institucionais; promessa de redução de filas, internações ou melhoria clínica; receitas manuscritas como funcionalidade confiável; validação clínica institucional. Áudio e ingestão de documentos pessoais reais não fazem parte deste recorte.

## 7. Histórias de usuário priorizadas

| ID | Prioridade | História | Aceite associado |
|---|---|---|---|
| HU01 | O | Como cidadão, quero pesquisar princípio ativo e apresentação para verificar sua presença nas fontes selecionadas | CA01–CA04, RF01–RF03 |
| HU02 | O | Como cidadão, quero entender canal e documentos sem confundir isso com estoque | CA05, CA08, RF04–RF05 |
| HU03 | O | Como cidadão, quero preparo de exame somente com exame, serviço e fonte suficientemente identificados | CA09–CA11, RF06 |
| HU04 | O | Como cidadão, quero esclarecer perguntas ambíguas antes de receber uma conclusão | CA01–CA03, RF02 |
| HU05 | O | Como cidadão, quero visualizar fonte e data de cada orientação | CA06–CA07, RF07 |
| HU06 | O | Como revisor, quero localizar a evidência de cada registro e aprovar ou rejeitar seu conteúdo | CA06, CA17, RF08 |
| HU07 | O | Como integrante da equipe, quero repetir uma avaliação versionada e comparar resultados | CA18, RF10 |
| HU08 | D | Como usuário de imagem, quero confirmar nome, concentração e forma antes da consulta | CA12–CA13, RF11 |

## 8. Cenários de aceitação — Dado, Quando, Então

Os cenários são especificações de comportamento, não resultados de testes executados. Casos factuais do golden set deverão instanciá-los com fontes reais revisadas.

| ID | Dado | Quando | Então |
|---|---|---|---|
| CA01 | Princípio ativo sem concentração, com múltiplas apresentações no recorte | O cidadão pesquisa | Mostrar opções e pedir concentração/forma; não concluir sobre uma apresentação específica |
| CA02 | Concentração ou forma ambígua | Há mais de uma correspondência plausível | Pedir o campo faltante; não selecionar por similaridade sem confirmação |
| CA03 | Nome comercial associado a múltiplos princípios ativos ou apresentações | O nome é pesquisado | Preservar a composição da associação e pedir identificação da apresentação; não tratar cada componente como substituto |
| CA04 | Item não localizado no recorte | A consulta termina | Informar “Não localizado no recorte consultado”, listar cobertura e versões; não afirmar ausência no SUS |
| CA05 | Apresentação encontrada em lista, sem fonte específica de estoque | O usuário pergunta onde retirar | Informar somente canal documentado e “Estoque não consultado”; oferecer canal oficial cadastrado, se houver |
| CA06 | Fontes aplicáveis trazem afirmações incompatíveis sobre o mesmo contexto | A resposta é montada | Exibir conflito e referências; abster-se da conclusão afetada. Diferenças entre programas não são automaticamente conflitos |
| CA07 | Fonte sem data de publicação verificável ou com revisão vencida | A orientação depende dela | Exibir a limitação; permitir apenas informações explicitamente aprovadas para esse estado. Não fornecer preparo crítico sem atualidade/aplicabilidade confirmadas |
| CA08 | Há presença na lista, mas nenhum vínculo verificado com unidade/canal | Perguntam onde retirar | Informar que o local não foi identificado; não deduzir a unidade pela proximidade ou apenas pela lista |
| CA09 | Exame identificado, mas serviço responsável ausente e necessário à aplicabilidade | Perguntam preparo | Pedir o serviço; não atribuir duração de jejum ou material por suposição |
| CA10 | Dois exames têm nomes semelhantes e preparos diferentes | A entrada permite ambos | Apresentar as opções e pedir o nome exato; não combinar preparos |
| CA11 | Orientação válida apenas para uma instituição | Usuário informa outra instituição ou nenhuma | Explicitar o limite institucional; não apresentar a orientação como regra geral do SUS-DF |
| CA12 | Imagem ilegível no experimento | A extração não identifica campos necessários | Pedir nova imagem fictícia ou digitação; não realizar consulta com campos presumidos |
| CA13 | Concentração extraída incorretamente | O usuário vê a prévia | Permitir correção e exigir confirmação de nome, concentração e forma antes de consultar; usar os valores confirmados |
| CA14 | Pergunta pede diagnóstico, dose ou substituição | O sistema identifica pedido fora do escopo | Não fornecer a conduta; explicar o limite e orientar a procurar profissional responsável |
| CA15 | Nenhuma evidência suficiente sustenta a orientação | A recuperação termina | Abster-se, explicar o que falta e indicar fonte/canal cadastrado quando disponível; não preencher com conhecimento não verificado |
| CA16 | Fonte ou serviço externo está indisponível | Uma operação depende desse serviço | Informar indisponibilidade e não confundir com resultado negativo. Se possível, usar somente a última base aprovada, com versão e limite de atualização visíveis |
| CA17 | Uma fonte mudou após a publicação | A equipe detecta a nova versão | Registrar mudança e pendências; não misturar versões silenciosamente. Publicar somente após revisão; se a mudança invalidar orientação crítica anterior, suspendê-la até revisão |
| CA18 | Entradas, configuração e versões de uma avaliação foram preservadas | Outro integrante repete a medição sobre as mesmas saídas | Reproduzir pontuações e contagens, respeitada a precisão declarada. Nova geração é identificada como outra execução |
| CA19 | Nome comercial não verificado no catálogo | O cidadão pesquisa | Informar cobertura insuficiente e pedir princípio ativo/apresentação; não inventar vínculo |
| CA20 | Registro sem evidência localizável | O responsável tenta publicá-lo | Bloquear esse registro e registrar o motivo, sem disponibilizá-lo nas consultas |

## 9. Requisitos funcionais

| ID | Prioridade | Requisito verificável |
|---|---|---|
| RF01 | O | Consultar apresentações por princípio ativo e nomes comerciais revisados; apresentar separadamente o resultado por fonte/versão |
| RF02 | O | Interromper a conclusão quando houver ambiguidade de identidade, concentração, forma ou serviço e solicitar os campos necessários |
| RF03 | O | Diferenciar “consta na versão consultada”, “não localizado no recorte”, “ambíguo” e “consulta indisponível”; não converter falta de dado em negativa universal |
| RF04 | O | Exibir canal, unidade, documentos e condições apenas com vínculo documental aplicável; identificar separadamente informações não encontradas |
| RF05 | O | Exibir o estado do estoque como não consultado nesta versão; permitir encaminhamento a canal oficial verificado, sem reproduzir disponibilidade não integrada |
| RF06 | O | Consultar preparo por exame e serviço; apresentar material, documentos e preparo conforme a evidência, distinguindo ausente de “não exigido” |
| RF07 | O | Associar cada orientação factual à fonte, versão, localização da evidência e data de verificação; permitir consultar a referência |
| RF08 | O | Manter decisões de revisão com responsável, data, resultado e justificativa; impedir publicação de registros rejeitados ou pendentes |
| RF09 | O | Identificar a versão publicada, registrar mudanças entre publicações e manter referência à última versão aprovada; bloquear conteúdo crítico invalidado |
| RF10 | O | Executar avaliação versionada e produzir resultados por caso, dimensão, categoria e divisão, com numeradores, denominadores e erros |
| RF11 | D | Permitir extração experimental de imagens; se habilitada, impedir consulta antes da confirmação dos três campos e oferecer correção manual |
| RF12 | O | Permitir reconstruir o conteúdo lógico publicado a partir dos mesmos originais, regras e decisões de revisão preservados |
| RF13 | O | Excluir perguntas/respostas do golden set do corpus de recuperação, mantendo os documentos oficiais elegíveis |

## 10. Requisitos não funcionais mensuráveis

| ID | Requisito e medição |
|---|---|
| RNF01 | 100% dos registros publicados possuem todos os campos obrigatórios de proveniência; datas desconhecidas têm motivo explícito |
| RNF02 | Reprocessamento com os mesmos insumos e revisões mantém registros, vínculos e evidências, sem duplicações; identificadores de execução podem variar |
| RNF03 | Falha de atualização não torna a versão candidata consultável; validar com cenário de falha e verificação da versão retornada |
| RNF04 | Medir latência ponta a ponta mediana e p95 em segundos, com número de amostras, concorrência, ambiente, falhas e execuções frias/quentes declarados. Limite de desempenho depende do piloto e deve ser fixado antes do teste final |
| RNF05 | Nos testes de privacidade, perguntas/imagens de uso comum não permanecem em histórico, logs, índices ou arquivos após conclusão/cancelamento da operação; falhas também são verificadas |
| RNF06 | Toda alteração de conteúdo aprovado permite identificar responsável, data, motivo e versão anterior |
| RNF07 | Consultas de usuário não permitem modificar fontes, aprovações, golden set ou publicação; verificar tentativa de operação não autorizada |
| RNF08 | Repetir o cálculo das métricas sobre saídas congeladas produz as mesmas contagens e valores na precisão informada |

Não se exige texto gerado idêntico em novas execuções de um modelo não determinístico. Exige-se preservar saídas e condições para auditar cada execução.

## 11. Regras de negócio

- RN01: presença em lista, canal de acesso, elegibilidade individual e estoque são conceitos diferentes e não podem ser apresentados como equivalentes.
- RN02: correspondência exige identidade e apresentação compatíveis. Não fundir formas, tipos de liberação, sais, concentrações ou associações por semelhança textual.
- RN03: fonte oficial só sustenta conclusão no território, serviço, programa, público e período aplicáveis.
- RN04: não interpretar ausência de informação como dispensa de documento, ausência de jejum ou ausência de medicamento no SUS.
- RN05: conflito exige análise de contexto; não adotar automaticamente a fonte com data mais recente. Uma resolução precisa de evidência e revisão registrada.
- RN06: diferenciar publicação, vigência, coleta e verificação. Nenhuma dessas datas substitui automaticamente as demais.
- RN07: recomenda-se verificar fontes semanalmente e antes da apresentação; prazo superior a sete dias desde a última verificação gera sinalização de revisão pendente. Isso não declara que a fonte foi revogada nem promete atualização semanal pelo órgão.
- RN08: orientação crítica sem evidência suficiente, aplicável e aprovada exige esclarecimento ou abstenção. É proibido inferir preparo ou dosagem a partir de conhecimento geral.
- RN09: instruções de documentos recuperados são conteúdo de referência, não autorização para alterar regras do sistema ou expor dados.
- RN10: toda ampliação de cobertura exige revisão e atualização da cobertura declarada e da avaliação pertinente.

## 12. Requisitos de dados e proveniência

| Conjunto | Conteúdo mínimo |
|---|---|
| Fonte | Identificador, órgão, título, URL, natureza do documento, território, público/serviço e condições de reutilização verificadas ou pendentes |
| Versão da fonte | Identificador, original preservado, hash, edição declarada, datas de publicação/vigência quando conhecidas, coleta e verificação, estado de atualidade |
| Registro | Identificador, texto original, valores normalizados, fonte/versão, página/seção/tabela ou outro localizador reproduzível, revisão e release |
| Apresentação | Princípios ativos e respectivas quantidades/unidades, concentração, forma, via/liberação quando documentadas, vínculo com cada lista |
| Marca | Nome comercial, vínculo com composição/apresentação, fonte comprobatória e revisão; sem mapeamento presumido |
| Acesso | Canal/unidade, território, programa, documentos, condições, contatos/endereço quando documentados e evidência de cada orientação |
| Exame | Nome exato, sinônimos revisados, material, serviço/unidade, documentos, preparo, restrições de aplicabilidade e fontes |
| Publicação | Versão, fontes incluídas, cobertura, revisões, data, pendências, alterações e resultado das verificações |

Campos não informados na fonte recebem estado e motivo explícitos. Registros insuficientes para identificar medicamento/apresentação ou para orientar preparo ficam fora da publicação correspondente. O encadeamento resultado → registro/trecho → versão → original deve ser verificável. Documentos gerais públicos podem ser preservados; isso não autoriza armazenar uploads pessoais.

## 13. Privacidade e segurança

- Não exigir conta, CPF, CNS, endereço pessoal ou histórico de saúde para consultar o MVP.
- Não persistir perguntas, imagens, receitas ou documentos enviados pelo usuário por padrão, inclusive em ferramentas de observabilidade e serviços externos.
- Usar imagens de embalagens sem identificadores pessoais e receitas fictícias; sinalizar o caráter experimental antes do envio. Não aceitar intencionalmente imagens reais de pacientes no experimento.
- Dados de avaliação podem ser preservados por serem casos sintéticos revisados e documentos oficiais; essa exceção deve ser distinguida do tráfego normal de usuários.
- Se conteúdo pessoal for identificado incidentalmente, interromper seu uso e descartá-lo, sem incluí-lo em corpus, golden set ou relatórios.
- Falhas, cancelamentos e serviços externos devem respeitar a mesma regra de não retenção; eventual fornecedor precisa ter condições verificadas antes de receber conteúdo potencialmente sensível.
- Restringir alterações de fontes, revisões e publicações aos responsáveis designados; manter segredos fora de artefatos públicos.
- Demonstrar trajetórias apenas com dados sintéticos identificados como tal; não alegar anonimização apenas por remover nomes.

## 14. Requisitos do golden set

Alvo: 60 casos, sendo 15 de presença/apresentação, 15 de canal/documentos, 15 de exames/preparo e 15 de ambiguidade, falta de evidência e fora do escopo. Proposta de divisão: 10 de desenvolvimento e 5 finais por categoria (40/20), preservando famílias de paráfrases no mesmo grupo. Se o agrupamento impedir essa distribuição, documentar o ajuste e manter cobertura de todas as categorias.

Cada caso registra: identificador; pergunta; categoria; contexto necessário; fonte e versão; localização da evidência; fatos obrigatórios; afirmações proibidas; comportamento esperado (responder, esclarecer ou abster-se); resposta de referência; responsável e data de revisão. Acrescentar divisão, versão do conjunto e marcação de criticidade para cálculo dos critérios de aceite.

Casos factuais são baseados em documentos reais aprovados, sem dados reais de pacientes. Perguntas elaboradas pela equipe são rotuladas dessa forma. Casos comportamentais sem evidência documental direta apontam para a regra desta especificação e identificam explicitamente essa condição, sem inventar fonte clínica.

Congelar os casos finais e critérios antes de avaliá-los. Não usar seus resultados para ajustar o sistema e apresentar nova execução como independente; após ajustes, declarar reavaliação e reservar novos casos quando possível. Versionar correções de referência, sem apagar histórico.

As perguntas e respostas de referência não entram no índice de recuperação. Os documentos usados como evidência podem entrar. Imagens constituem subconjunto identificado, com quantidade e cobertura próprias; se a funcionalidade não for entregue, sua avaliação é “não executada”, não nota zero nem sucesso.

## 15. Requisitos de avaliação

| Dimensão | Definição operacional |
|---|---|
| Qualidade da extração | Campos corretos / campos revisados, por tipo de campo; medir também registros completos e itens perdidos no recorte, para não esconder omissões |
| Proveniência | Registros com proveniência obrigatória completa / registros publicados |
| Recuperação | Hit@5: casos respondíveis com ao menos uma evidência válida nos cinco primeiros resultados / casos respondíveis. Recall@5: evidências relevantes recuperadas / evidências relevantes anotadas, por caso; não confundir as duas métricas |
| Posição da evidência | MRR: média do inverso da posição da primeira evidência relevante; zero quando ausente, com limite de resultados declarado |
| Correção factual | Revisão de afirmações como corretas, incorretas ou não verificáveis frente às referências aprovadas; relatar contagens |
| Fidelidade | Afirmações factuais sustentadas pelo contexto efetivamente recuperado / afirmações factuais produzidas |
| Completude | Fatos obrigatórios corretamente apresentados / fatos obrigatórios esperados, por caso |
| Citações | Afirmações citadas com referência que realmente as sustenta / afirmações citadas; relatar também afirmações que exigiam referência e ficaram sem ela |
| Esclarecimento/abstenção | Casos com comportamento correto / casos que exigem cada comportamento; medir separadamente abstenções indevidas em casos respondíveis |
| Latência | Tempo entre envio confirmado e resposta/erro; mediana, p95, amostras e taxa de falhas, sem excluir falhas silenciosamente |
| Imagens | Acerto de nome, concentração e forma antes de correção humana; acerto conjunto dos três campos; casos ilegíveis e correções separados. Medir também cumprimento da confirmação |

Para classificação global de resposta, “correta e suficientemente completa” exige todos os fatos obrigatórios do caso, nenhuma afirmação incorreta/proibida e comportamento esperado. Respostas parcialmente corretas são contadas separadamente. Casos sem afirmações ou sem denominador aplicável recebem “não aplicável”, sem inflar médias.

Orientação crítica inventada inclui preparo, duração, material, dose, substituição ou condição de acesso não sustentada que possa alterar a conduta do usuário. A criticidade é marcada antes do teste e revisada em caso de erro novo.

BLEU e ROUGE-L são opcionais e complementares, reportados em respostas textuais comparáveis, com implementação, tokenização, normalização, referências e agregação declaradas. Não comprovam correção factual e não são critérios isolados de aprovação. Não exigir palavras em posições fixas; campos críticos, negações, números e unidades devem ser verificados pelo significado. Caso o instrutor exija outra métrica de posição, registrar sua definição antes de utilizá-la.

Comparar recuperação e geração separadamente: avaliar localização das evidências; avaliar respostas com evidências corretas fornecidas; avaliar o fluxo completo. Avaliação automática por outro modelo é auxiliar e não substitui revisão humana dos casos críticos.

Cada execução preserva: versão do golden set e divisão, fontes e hashes, versão do sistema, regras/configuração de recuperação, parâmetros de fragmentação e quantidade recuperada, modelo/prompt/parâmetros quando utilizados, ambiente, resultados recuperados, saídas, tempos, avaliadores, rubrica, métricas e erros. Não preencher resultados de testes que ainda não ocorreram.

### Impacto no usuário final — desejável

Piloto exploratório com 5–8 voluntários e três tarefas fictícias por pessoa. Medir sucesso da tarefa (próximo passo identificado corretamente), tempo, compreensão (explicação do próximo passo), confusão entre lista e estoque e facilidade percebida de 1 a 5. Definir resposta esperada antes de observar o participante. Relatar resultados absolutos, dificuldades e limitações da amostra. Se houver comparação com portais oficiais, alternar ordem ou tarefas equivalentes. Não coletar histórias de saúde nem inferir impacto clínico a partir desse piloto.

## 16. Estados de erro e comportamentos seguros

| Estado | Saída observável |
|---|---|
| Ambíguo | Solicitação dos campos faltantes, sem conclusão sobre item específico |
| Não localizado no recorte | Limite de cobertura e versões consultadas, sem negativa universal |
| Evidência insuficiente | Abstenção da afirmação afetada e informação do que falta |
| Conflito | Fontes conflitantes identificadas e conclusão suspensa |
| Atualidade não confirmada | Datas conhecidas, motivo e limites; preparo crítico bloqueado quando não validado |
| Fora do escopo | Limite explicado, sem aconselhamento clínico |
| Imagem ilegível/não confirmada | Reenvio ou correção; consulta bloqueada até confirmação |
| Dependência indisponível | Falha explícita; alternativa aprovada quando existente; nunca simular resultado |
| Atualização pendente/rejeitada | Candidata não publicada; versão vigente identificada e eventual orientação invalidada suspensa |

## 17. Critérios de aceite do MVP

Todos os requisitos obrigatórios e cenários aplicáveis devem ter evidência de verificação. O experimento de imagem e o piloto de usuários são entregas desejáveis separadas; suas regras de proteção tornam-se obrigatórias se habilitados.

| ID | Critério proposto |
|---|---|
| AC01 | 30–50 apresentações e 5–10 exames revisados, com cobertura e serviços explicitados |
| AC02 | 100% dos registros publicados com proveniência completa; nenhuma associação incorreta entre medicamento e apresentação no conjunto de aceite |
| AC03 | Hit@5 ≥ 90% dos casos respondíveis; apresentar número de acertos e denominador, além de Recall@5 e MRR separadamente |
| AC04 | ≥ 90% das respostas a casos respondíveis corretas e suficientemente completas, conforme rubrica; reportar avaliação dos demais comportamentos separadamente |
| AC05 | Nenhuma orientação crítica inventada no conjunto avaliado; acerto em todos os casos críticos predefinidos de esclarecimento e abstenção |
| AC06 | Golden set versionado, divisão congelada e nenhuma pergunta/resposta de referência no corpus |
| AC07 | Reprocessamento reproduz conteúdo lógico, avaliação sobre saídas congeladas reproduz métricas e falha de atualização preserva a versão aprovada |
| AC08 | Não retenção de entradas de usuário verificada em sucesso, falha e cancelamento; nenhuma imagem real de paciente no conjunto de avaliação |
| AC09 | Resultados absolutos e percentuais, latência e cobertura publicados; cada erro tem caso, resultado esperado/observado, gravidade, causa conhecida ou pendente e decisão |

Percentuais são calculados sem arredondamento que transforme reprovação em aprovação. Metas só podem ser calibradas no piloto e antes do teste final, com justificativa registrada. Falha crítica bloqueia o aceite mesmo com média global elevada. Aprovação neste conjunto não constitui garantia universal de segurança.

## 18. Hipóteses

H01: será possível obter documentos oficiais suficientes para o recorte dentro do prazo. H02: haverá disponibilidade de revisão de conteúdo. H03: o protótipo informacional poderá ser demonstrado sem dados reais de pacientes. H04: nomes comerciais terão evidências verificáveis para um subconjunto limitado. H05: recursos de execução estarão disponíveis sem contratação obrigatória. Todas dependem de confirmação; não constituem resultados verificados.

## 19. Dependências externas

Disponibilidade e condições de reutilização das fontes oficiais; confirmação de versões e aplicabilidade; colaboração de revisores; decisão sobre exames/serviços e marcas; recursos fornecidos pela residência; contrato de integração com o restante do produto; rubrica acadêmica. A existência de páginas ou painéis não comprova API, exportação automatizada, estoque atual ou acesso a SISREG. Integração institucional não é pré-requisito deste MVP.

## 20. Riscos

| Risco | Consequência | Tratamento funcional |
|---|---|---|
| Erro de extração ou correspondência | Apresentação incorreta | Revisão, bloqueio de ambiguidades e teste por campo |
| Orientação de serviço errado | Preparo inadequado | Exigir aplicabilidade e serviço; abster-se quando insuficiente |
| Fonte substituída ou conflitante | Resposta desatualizada | Versões, revisão periódica e suspensão de conteúdo invalidado |
| Fonte ou recurso indisponível | Falha de consulta | Estado de erro explícito e versão aprovada identificada |
| Exposição de receita | Dados sensíveis retidos/divulgados | Imagens fictícias, não retenção e restrição do experimento |
| Avaliação contaminada | Métricas artificialmente altas | Separação de casos, famílias de perguntas e rastreio de experimentos |
| Revisão insuficiente | Erros de domínio não percebidos | Reduzir recorte e manter pendências fora da publicação |
| Escopo maior que prazo | Entrega incompleta | Priorizar núcleo obrigatório; imagens e trajetórias separadas |
| Métrica lexical alta com erro factual | Falsa confiança | Avaliação factual independente de BLEU/ROUGE |

## 21. Questões em aberto e compatibilidade com o repositório

O README atual descreve sete semanas, áudio, PDFs de receitas, pipeline multimodal, multiagentes, ferramentas específicas e diferenciação automática de canais. Esta especificação propõe seis semanas, não fixa arquitetura e restringe imagens a experimento fictício. Esses itens do README são contexto de uma visão mais ampla, não critérios de aceite desta especificação; a equipe deve harmonizar os documentos antes da implementação.

A expressão “bases 100% públicas” do README não comprova acesso público a dados operacionais do SISREG. Protocolos públicos e sistemas institucionais devem ser tratados separadamente. A edição mencionada no README não confirma, por si só, a versão vigente de cada fonte.

Não foram selecionados nem revisados neste documento os arquivos definitivos, marcas, unidades ou exames; não há golden set factual preenchido ou resultados medidos nesta entrega. O nome SUS Cidadão/NavegaSUS e a divisão nominal de responsabilidades também precisam de confirmação pela equipe.

## 22. Decisões a confirmar pela equipe ou pelo instrutor

1. Aprovar o recorte obrigatório de medicamentos, acesso e exames no DF e sua precedência sobre a visão ampla do README.
2. Confirmar data final, aproximadamente seis semanas de trabalho e responsáveis por revisão, publicação e avaliação.
3. Selecionar as 30–50 apresentações, marcas verificáveis, 5–10 exames e respectivos serviços.
4. Confirmar fontes, versões, aplicabilidade e autorização/condições de reutilização antes de publicar dados.
5. Aprovar imagens como entrega desejável e exclusivamente experimental; confirmar ausência de histórico real e de áudio no MVP.
6. Definir quem revisará dúvidas farmacêuticas e instruções específicas de laboratório, sem alegar validação institucional.
7. Aprovar verificação semanal e antes da apresentação, além do comportamento para fontes sem data ou atualização pendente.
8. Confirmar composição 60/40/20 do golden set, responsáveis pela revisão e proteção do conjunto final contra ajustes oportunistas.
9. Aprovar rubrica, casos críticos, denominadores e metas; esclarecer a exigência do instrutor sobre BLEU, ROUGE e “palavras em posições específicas”.
10. Confirmar ambiente disponível e fixar limite de latência após o piloto, antes da avaliação final.
11. Decidir se haverá piloto com voluntários e como registrar resultados sem dados de saúde identificáveis.
12. Harmonizar a rubrica acadêmica e o README com os critérios deste documento antes de iniciar implementação além do recorte aprovado.
