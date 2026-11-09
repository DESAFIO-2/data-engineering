# Especificação funcional do MVP de Engenharia de Dados do SUS Cidadão

**Objetivo:** disponibilizar no Distrito Federal um recorte pequeno e revisado de informações oficiais sobre medicamentos, acesso e preparo de exames, com proveniência verificável, tratamento explícito de ambiguidades e avaliação reproduzível. A especificação descreve comportamentos e critérios de aceite; não comprova que funcionalidades, fontes, integrações ou resultados já existam.

**Versão:** 0.1 · **Data:** 03/11/2026 · **Estado:** proposta para revisão da equipe
**Horizonte proposto:** aproximadamente seis semanas, até meados de dezembro de 2026.

Não são definidos banco de dados, framework, biblioteca ou modelo de IA. As metas de avaliação são propostas a calibrar no piloto e congelar antes da avaliação final.

## Etapa 1 — Confirmar objetivo, atores e limites

### Objetivo

Alinhar o problema que o MVP resolve, quem participa e quais alegações o produto pode fazer.

### Requisitos ou regras

- Cidadãos têm dificuldade para localizar informação oficial sobre medicamentos, canais de dispensação, documentos e preparo de exames. A aplicabilidade depende de lista, versão, programa, serviço e instituição.
- O produto deve mostrar evidências verificáveis e não tratar presença em lista como estoque ou direito individual garantido.
- O valor esperado é melhor compreensão do próximo passo documentado. Redução de filas, deslocamentos ou eventos clínicos não está demonstrada.
- Atores: cidadão/cuidador (consulta e esclarece ambiguidades); revisor (compara fontes e registra decisões); responsável pelos dados (recorte, versões e publicação); avaliador (executa e documenta avaliação); equipe/instrutor (confirma escopo, recursos e avaliação acadêmica).
- Revisão inicial pode contar com profissional de enfermagem convidado. Dúvidas farmacêuticas e orientações específicas de laboratório exigem evidência aplicável e eventual revisão especializada; isso não equivale a validação clínica institucional.
- Fora do escopo: diagnóstico/triagem, prescrição, recomendação ou alteração de dose, substituição terapêutica, garantia de estoque, cobertura completa do SUS, prontuário/histórico real, armazenamento permanente de imagens/receitas, integração institucional completa, promessa de benefício clínico, receitas manuscritas como função confiável, validação clínica institucional, áudio e ingestão de documentos pessoais reais.
- Regras de negócio: presença em lista, canal de acesso, elegibilidade individual e estoque são distintos (RN01); correspondência exige identidade e apresentação compatíveis, sem fundir formas, sais, liberação, concentrações ou associações por semelhança (RN02); fonte só sustenta conclusão no território, serviço, programa, público e período aplicáveis (RN03).
- Ausência de informação não significa dispensa de documento, ausência de jejum ou ausência no SUS (RN04). Conflitos requerem análise contextual e revisão registrada; não se escolhe automaticamente a fonte mais recente (RN05).
- Distinguir datas de publicação, vigência, coleta e verificação (RN06). Recomenda-se verificar fontes semanalmente e antes da apresentação; mais de sete dias desde a verificação sinaliza revisão pendente, sem declarar revogação nem prometer atualização pelo órgão (RN07).
- Orientação crítica sem evidência suficiente, aplicável e aprovada exige esclarecimento ou abstenção; é proibido inferir preparo ou dosagem por conhecimento geral (RN08). Instruções em documentos recuperados não alteram regras do sistema nem autorizam exposição de dados (RN09). Ampliar cobertura exige revisão e atualização da cobertura declarada e da avaliação (RN10).

### Critérios de conclusão

- A equipe confirma objetivo, território, atores, limites e a distinção entre informação documentada e resultado operacional.
- O escopo aprovado não implica validação clínica institucional nem benefício clínico comprovado.

## Etapa 2 — Fixar recorte e prioridades

### Objetivo

Definir o conteúdo observável que compõe o aceite do MVP e separar entregas desejáveis e futuras.

### Requisitos ou regras

| Frente | Prioridade | Limite observável |
|---|---|---|
| Medicamentos | Obrigatória (O) | 30–50 apresentações distintas, revisadas, com composição, concentração e forma identificadas |
| Fontes de medicamentos | O | Recortes de RENAME, REME-DF e Farmácia Popular; declarar versões e cobertura, sem presumir sobreposição |
| Pesquisa | O | Princípio ativo e conjunto fechado de nomes comerciais com vínculos verificados; publicar quantidade e relação de nomes cobertos |
| Acesso | O | Canal, documentos e condições somente quando sustentados por fonte aplicável |
| Exames | O | 5–10 exames com orientação oficial do serviço selecionado |
| Proveniência e atualização | O | Fonte e data de verificação visíveis; versões anteriores identificáveis |
| Avaliação | O | Cerca de 60 casos versionados e relatório separado por dimensão |
| Imagem | Desejável (D) | Experimento com embalagens e receitas fictícias; se habilitado, confirmação de campos e proteção das imagens são obrigatórias |
| Trajetória demonstrativa | D | Personagens e dados sintéticos, identificados explicitamente |
| Histórico real e integrações operacionais | Futuro (F) | Exigem nova definição de escopo e governança |

- Informar o recorte disponível antes ou junto do resultado. Distinguir apresentações cadastradas de fontes integralmente consultáveis.
- Histórias priorizadas: HU01 pesquisa de princípio ativo/apresentação; HU02 canal/documentos sem confundir estoque; HU03 preparo aplicável ao exame e serviço; HU04 esclarecimento de ambiguidade; HU05 fonte e data visíveis; HU06 evidência e revisão; HU07 avaliação repetível; HU08 confirmação de campos de imagem (desejável). Os vínculos de aceite originais são HU01 CA01–CA04/RF01–RF03; HU02 CA05/CA08/RF04–RF05; HU03 CA09–CA11/RF06; HU04 CA01–CA03/RF02; HU05 CA06–CA07/RF07; HU06 CA06/CA17/RF08; HU07 CA18/RF10; HU08 CA12–CA13/RF11.

### Critérios de conclusão

- O conjunto de conteúdo e prioridades é aprovado e a cobertura pode ser declarada sem sugerir completude.
- Imagem e trajetória sintética permanecem separadas do núcleo obrigatório; histórico real e integração operacional não entram neste aceite.

## Etapa 3 — Selecionar fontes e estruturar dados rastreáveis

### Objetivo

Reunir apenas dados cuja origem, versão, aplicabilidade e revisão possam ser verificadas.

### Requisitos ou regras

- Para cada fonte, registrar identificador, órgão, título, URL, natureza, território, público/serviço e condições de reutilização (verificadas ou pendentes).
- Para cada versão, preservar original e hash; registrar identificador, edição declarada, datas conhecidas de publicação/vigência, coleta e verificação, e estado de atualidade.
- Para cada registro, manter identificador, texto original, valores normalizados, fonte/versão, localização reproduzível (página, seção, tabela ou equivalente), revisão e release.
- Medicamento: princípios ativos, quantidades/unidades, concentração, forma, via/liberação quando documentadas e vínculo com cada lista. Marca: nome, vínculo comprovado com composição/apresentação, fonte e revisão; nunca presumir mapeamento.
- Acesso: canal/unidade, território, programa, documentos, condições, contatos/endereço documentados e evidência de cada orientação.
- Exame: nome exato, sinônimos revisados, material, serviço/unidade, documentos, preparo, limites de aplicabilidade e fontes.
- Publicação: versão, fontes incluídas, cobertura, revisões, data, pendências, mudanças e resultado das verificações.
- Campos ausentes na fonte recebem estado e motivo explícitos. Registros insuficientes para identificar medicamento/apresentação ou orientar preparo ficam fora da publicação correspondente. Deve ser verificável o encadeamento resultado → registro/trecho → versão → original.
- Documentos gerais públicos podem ser preservados; isso não autoriza armazenar uploads pessoais.
- Requisitos funcionais: RF01 consultar por princípio ativo e nomes comerciais revisados, separando resultados por fonte/versão; RF07 associar cada orientação factual a fonte, versão, localização e data de verificação, com referência consultável; RF12 reconstruir o conteúdo lógico publicado com os mesmos originais, regras e revisões.
- RNF01: 100% dos registros publicados têm proveniência obrigatória completa; datas desconhecidas têm motivo explícito. RNF02: reprocessar mesmos insumos/revisões preserva registros, vínculos e evidências sem duplicação (IDs de execução podem variar). RNF06: cada alteração aprovada identifica responsável, data, motivo e versão anterior.

### Critérios de conclusão

- Cada registro candidato tem evidência localizável e proveniência completa; registros pendentes ou insuficientes não são publicados.
- O conteúdo lógico pode ser reconstruído e as versões e alterações são identificáveis.

## Etapa 4 — Aplicar revisão e governar publicações

### Objetivo

Impedir que conteúdo sem evidência, rejeitado, pendente ou invalidado alcance consultas.

### Requisitos ou regras

- RF08: registrar decisão de revisão com responsável, data, resultado e justificativa; impedir publicação de registros rejeitados ou pendentes.
- RF09: identificar a versão publicada, registrar mudanças entre publicações, manter referência à última versão aprovada e bloquear conteúdo crítico invalidado.
- CA17: ao detectar nova versão da fonte, registrar mudanças e pendências, não misturar versões silenciosamente e publicar somente após revisão. Se uma mudança invalidar orientação crítica, suspendê-la até revisão.
- CA20: bloquear registro sem evidência localizável e registrar o motivo.
- RNF03: falha de atualização não torna candidata consultável; verificar cenário de falha e versão retornada.
- A revisão de dúvidas farmacêuticas e de laboratório pode exigir especialista; não alegar validação institucional.

### Critérios de conclusão

- Estados de revisão e histórico de publicação são auditáveis.
- Falha ou pendência preserva a versão aprovada e não expõe conteúdo candidato; orientação crítica invalidada fica suspensa.

## Etapa 5 — Definir consultas e respostas seguras

### Objetivo

Permitir pesquisa útil sem inferir identidade, disponibilidade, elegibilidade ou orientação não sustentada.

### Requisitos ou regras

- RF02 interromper conclusão quando identidade, concentração, forma ou serviço forem ambíguos e pedir os campos necessários. RF03 distinguir “consta na versão consultada”, “não localizado no recorte”, “ambíguo” e “consulta indisponível”; falta de dado não vira negativa universal.
- RF04 mostrar canal, unidade, documentos e condições somente com vínculo documental aplicável e separar o que não foi encontrado. RF05 mostrar estoque como “não consultado nesta versão”; só encaminhar a canal oficial verificado, sem alegar disponibilidade não integrada.
- RF06 consultar preparo por exame e serviço, apresentar material/documentos/preparo conforme evidência e distinguir dado ausente de “não exigido”.
- RF13 excluir perguntas e respostas do golden set do corpus de recuperação; documentos oficiais usados como evidência podem ser incluídos.
- Cenários observáveis:
  - CA01–CA03: princípio ativo sem apresentação, concentração/forma ambígua ou marca associada a várias composições exige opções/esclarecimento; não concluir por similaridade nem tratar componentes como substitutos.
  - CA04: item não localizado gera “Não localizado no recorte consultado”, cobertura e versões; não afirma ausência no SUS.
  - CA05/CA08: presença em lista não prova estoque nem unidade de retirada; informar “Estoque não consultado” e não deduzir unidade por proximidade/lista. Canal oficial só se documentado.
  - CA06: conflito entre fontes aplicáveis ao mesmo contexto é exibido com referências e suspende a conclusão afetada; diferenças entre programas não são automaticamente conflitos.
  - CA07: fonte sem data verificável ou com revisão vencida expõe limitação; preparo crítico não é fornecido sem atualidade e aplicabilidade confirmadas; só se permite conteúdo explicitamente aprovado para esse estado.
  - CA09–CA11: pedir serviço quando necessário, distinguir exames semelhantes e não generalizar orientação institucional para o SUS-DF.
  - CA14–CA15: pedido de diagnóstico, dose ou substituição não recebe conduta; explicar limite e orientar profissional responsável. Sem evidência suficiente, abster-se, explicar o que falta e indicar fonte/canal cadastrado quando houver.
  - CA16: indisponibilidade externa é informada e não se confunde com resultado negativo; se possível, usar apenas última base aprovada, com versão e limite de atualização visíveis.
  - CA19: nome comercial sem vínculo verificado informa cobertura insuficiente e pede princípio ativo/apresentação; não inventa associação.
- Estados de erro: ambíguo (pedir campos); não localizado (declarar cobertura/versões); evidência insuficiente (abster-se da afirmação afetada); conflito (identificar fontes e suspender conclusão); atualidade incerta (limites e datas, bloqueio de preparo crítico); fora de escopo (explicar limite); dependência indisponível (falha explícita e alternativa aprovada quando houver); atualização pendente/rejeitada (não publicar candidata, identificar versão vigente e suspender orientação invalidada).

### Critérios de conclusão

- Cenários CA01–CA11 e CA14–CA16/CA19 têm saídas observáveis conforme regras acima.
- Toda afirmação factual expõe referência verificável; ausência, ambiguidade, conflito e falha têm estados distintos.

## Etapa 6 — Proteger dados e controlar acessos

### Objetivo

Evitar coleta e retenção desnecessárias de dados pessoais ou sensíveis durante consulta, avaliação e experimento.

### Requisitos ou regras

- Não exigir conta, CPF, CNS, endereço pessoal ou histórico de saúde.
- Não persistir perguntas, imagens, receitas ou documentos enviados por padrão, inclusive em observabilidade e serviços externos.
- Imagens experimentais devem ser de embalagens sem identificadores pessoais e receitas fictícias; avisar antes do envio e não aceitar intencionalmente imagens reais de pacientes.
- Dados de avaliação podem ser preservados se sintéticos e revisados; distingui-los do tráfego normal. Se conteúdo pessoal for identificado incidentalmente, interromper o uso, descartar e excluir de corpus, golden set e relatórios.
- Falhas, cancelamentos e fornecedores externos seguem a mesma regra de não retenção; verificar condições do fornecedor antes de transmitir conteúdo potencialmente sensível.
- Restringir alteração de fontes, revisões e publicações aos responsáveis; manter segredos fora de artefatos públicos.
- Trajetórias demonstrativas usam dados sintéticos explicitamente identificados; remover nomes, por si só, não comprova anonimização.
- RNF05: verificar que entradas de uso comum não permanecem em histórico, logs, índices ou arquivos após conclusão/cancelamento, inclusive em falhas. RNF07: consultas não podem alterar fontes, aprovações, golden set ou publicação; verificar tentativa não autorizada.

### Critérios de conclusão

- Não retenção é verificada em sucesso, falha e cancelamento; acessos de escrita são restritos.
- Se imagem for habilitada, o experimento usa somente conteúdo fictício/sintético e exige confirmação dos campos antes da consulta.

## Etapa 7 — Congelar conjunto de avaliação e método

### Objetivo

Medir dados, recuperação e respostas separadamente, preservando reprodutibilidade e impedindo contaminação da avaliação final.

### Requisitos ou regras

- Golden set alvo: 60 casos — 15 presença/apresentação, 15 canal/documentos, 15 exames/preparo, 15 ambiguidade/falta de evidência/fora do escopo. Proposta de divisão: 10 desenvolvimento e 5 finais por categoria (40/20); manter famílias de paráfrases juntas. Se inviável, documentar ajuste e manter categorias cobertas.
- Cada caso registra ID, pergunta, categoria, contexto, fonte/versão e localização, fatos obrigatórios, afirmações proibidas, comportamento esperado (responder/esclarecer/abster-se), resposta de referência, responsável/data de revisão, divisão, versão e criticidade.
- Casos factuais usam documentos reais aprovados, sem dados de pacientes. Perguntas da equipe são rotuladas. Casos comportamentais sem evidência documental apontam para esta especificação e declaram essa condição.
- Congelar casos finais e critérios antes da avaliação. Não ajustar o sistema com resultados finais e declarar reavaliações após ajustes; reservar novos casos quando possível. Versionar correções sem apagar histórico. Perguntas/respostas de referência não entram no índice.
- Avaliar separadamente: extração (campos corretos/campos revisados por tipo, registros completos e itens omitidos); proveniência (completos/publicados); recuperação (Hit@5 por caso respondível e Recall@5 por evidência, sem confundi-los); MRR (posição da primeira evidência, zero quando ausente e limite declarado); correção factual (correta/incorreta/não verificável); fidelidade (afirmações sustentadas pelo contexto recuperado); completude (fatos obrigatórios); citações (referências que sustentam afirmações e afirmações sem referência); esclarecimento/abstenção (acertos e abstenções indevidas); latência (mediana, p95, amostras e falhas); imagens (acerto individual e conjunto de nome/concentração/forma antes de correção, ilegíveis, correções e confirmação).
- Resposta global “correta e suficientemente completa” exige todos os fatos obrigatórios, nenhuma afirmação incorreta/proibida e comportamento esperado. Relatar parciais. Casos sem denominador aplicável ficam “não aplicável”, sem inflar médias. Marcar criticidade antes do teste e revisar se surgir erro novo.
- BLEU e ROUGE-L são opcionais e complementares, com implementação, tokenização, normalização, referências e agregação declaradas; não provam correção factual nem aprovam isoladamente. Não exigir palavras em posições fixas: verificar significado de campos, negações, números e unidades. Se o instrutor exigir outra métrica de posição, definir antes do uso.
- Comparar recuperação, geração com evidências corretas fornecidas e fluxo completo. Avaliação automática por outro modelo é auxiliar; revisão humana é necessária nos casos críticos.
- Por execução preservar versão/divisão do conjunto, fontes e hashes, sistema, configuração de recuperação, fragmentação, quantidade recuperada, modelo/prompt/parâmetros se usados, ambiente, recuperados, saídas, tempos, avaliadores, rubrica, métricas e erros. Não registrar resultados de testes ainda não realizados.
- Imagens são subconjunto identificado com cobertura própria; se não entregues, marcar avaliação “não executada”, não zero ou sucesso.
- RNF08: recalcular métricas sobre saídas congeladas e obter mesmas contagens/valores na precisão declarada. Não se exige texto idêntico em nova geração não determinística; exige-se preservar saídas e condições para auditoria.
- Latência RNF04: medir ponta a ponta, mediana e p95 em segundos, declarando amostras, concorrência, ambiente, falhas e execuções frias/quentes. Fixar limite após piloto e antes do teste final.
- Piloto de impacto do usuário é desejável: 5–8 voluntários, três tarefas fictícias cada; medir sucesso do próximo passo, tempo, compreensão, confusão lista/estoque e facilidade de 1–5. Definir resposta esperada antes, reportar absolutos e limites; se comparar portais, alternar ordem/tarefas equivalentes. Não coletar histórias de saúde nem inferir impacto clínico.

### Critérios de conclusão

- Conjunto e critérios são versionados e congelados antes do teste; casos de referência não contaminam o corpus.
- Cada execução pode ser auditada e as métricas sobre saídas congeladas são reproduzíveis.

## Etapa 8 — Demonstrar aceite do MVP

### Objetivo

Consolidar evidências de verificação para cada requisito obrigatório e decidir aceite segundo metas propostas.

### Requisitos ou regras

| ID | Critério proposto |
|---|---|
| AC01 | 30–50 apresentações e 5–10 exames revisados, com cobertura e serviços explicitados |
| AC02 | 100% dos registros publicados com proveniência completa; nenhuma associação incorreta entre medicamento e apresentação no conjunto de aceite |
| AC03 | Hit@5 ≥ 90% dos casos respondíveis; informar acertos/denominador, Recall@5 e MRR separadamente |
| AC04 | ≥ 90% das respostas a casos respondíveis corretas e suficientemente completas conforme rubrica; reportar os demais comportamentos separadamente |
| AC05 | Nenhuma orientação crítica inventada no conjunto; acerto em todos os casos críticos predefinidos de esclarecimento/abstenção |
| AC06 | Golden set versionado, divisão congelada e nenhuma pergunta/resposta de referência no corpus |
| AC07 | Reprocessamento reproduz conteúdo lógico; avaliação sobre saídas congeladas reproduz métricas; falha de atualização preserva versão aprovada |
| AC08 | Não retenção verificada em sucesso, falha e cancelamento; nenhuma imagem real de paciente na avaliação |
| AC09 | Publicar resultados absolutos e percentuais, latência e cobertura; cada erro tem caso, esperado/observado, gravidade, causa conhecida ou pendente e decisão |

- Todos os requisitos obrigatórios e cenários aplicáveis precisam de evidência de verificação.
- Percentuais não podem ser arredondados de modo a converter reprovação em aprovação. Metas só podem ser calibradas no piloto e antes do teste final, com justificativa registrada. Falha crítica bloqueia aceite mesmo com média global alta. Aprovação não garante segurança universal.
- Imagens e piloto de usuários são entregas desejáveis separadas; suas regras de proteção se tornam obrigatórias se habilitados.

### Critérios de conclusão

- AC01–AC09 aplicáveis têm evidências e relatório completo; erros e falhas críticas estão identificados.
- O aceite é decidido com denominadores, limites e ressalvas publicados, sem apresentar resultados não medidos.

## Etapa 9 — Resolver dependências, riscos e decisões pendentes

### Objetivo

Explicitar os itens externos e decisões que condicionam implementação e avaliação sem convertê-los em decisões presumidas.

### Requisitos ou regras

**Dependências e hipóteses a confirmar:** disponibilidade e reutilização das fontes oficiais; versões e aplicabilidade; revisores; seleção de exames/serviços e marcas; recursos da residência; contrato de integração com produto; rubrica acadêmica. Páginas e painéis não comprovam API, exportação automatizada, estoque atual ou acesso a SISREG. Integração institucional não é pré-requisito. Hipóteses não verificadas: documentos suficientes no prazo; revisão disponível; demonstração sem dados reais; evidência para subconjunto de marcas; recursos sem contratação obrigatória.

**Questões em aberto:**

1. Aprovar o recorte obrigatório no DF e sua precedência sobre a visão ampla do README.
2. Confirmar data final, horizonte de seis semanas e responsáveis por revisão, publicação e avaliação.
3. Selecionar apresentações, marcas verificáveis, exames e serviços.
4. Confirmar fontes, versões, aplicabilidade e condições de reutilização antes de publicar.
5. Aprovar imagem como entrega desejável e experimental; confirmar ausência de histórico real e áudio no MVP.
6. Definir revisores para dúvidas farmacêuticas e laboratoriais sem alegar validação institucional.
7. Aprovar frequência semanal/antes da apresentação e tratamento de fonte sem data ou com atualização pendente.
8. Confirmar composição e divisão do golden set (a especificação propõe 60 casos e divisão 40/20; decisões finais sobre revisão e proteção do conjunto permanecem pendentes).
9. Aprovar rubrica, casos críticos, denominadores e metas; esclarecer exigência do instrutor sobre BLEU, ROUGE e “palavras em posições específicas”.
10. Confirmar ambiente e fixar latência após piloto, antes da avaliação final.
11. Decidir se haverá piloto voluntário e como evitar registro de dados identificáveis de saúde.
12. Harmonizar rubrica acadêmica e README com estes critérios antes de avançar além do recorte aprovado.

**Compatibilidade documental:** o README descreve sete semanas, áudio, PDFs de receitas, pipeline multimodal, multiagentes, ferramentas específicas e diferenciação automática de canais. Este documento propõe seis semanas, não fixa arquitetura e limita imagens a experimento fictício; a equipe deve harmonizar a visão ampla antes da implementação. “Bases 100% públicas” não comprova acesso público a dados operacionais do SISREG. A edição citada no README não confirma versão vigente de cada fonte. Arquivos definitivos, marcas, unidades e exames não foram selecionados aqui; não há golden set factual preenchido nem resultados medidos. Nome SUS Cidadão/NavegaSUS e divisão nominal de responsabilidades também aguardam confirmação.

**Riscos e tratamento especificado:** erro de extração/correspondência pode gerar apresentação incorreta (revisão, bloqueio de ambiguidades e teste por campo); serviço errado pode gerar preparo inadequado (exigir aplicabilidade e abster-se); fonte substituída/conflitante pode desatualizar resposta (versionar, revisar e suspender conteúdo invalidado); indisponibilidade exige estado de erro e versão aprovada identificada; exposição de receita é mitigada por imagens fictícias, não retenção e experimento restrito; avaliação contaminada exige separação de casos/famílias e rastreio; revisão insuficiente requer recorte menor e pendências fora da publicação; prazo exige prioridade ao núcleo; métrica lexical pode mascarar erro factual, por isso avaliação factual é independente.

### Critérios de conclusão

- Cada dependência e decisão pendente tem responsável ou confirmação atribuída pela equipe antes do marco afetado.
- Divergências com README e lacunas de evidência permanecem registradas até decisão; nenhuma hipótese é tratada como resultado confirmado.
