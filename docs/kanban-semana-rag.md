# Kanban da semana - Primeiro mecanismo RAG

Período de referência: 3 a 8 de novembro de 2026  
Responsabilidade principal: Engenharia de Dados  
Entrega da semana: primeiro mecanismo RAG consultando fontes oficiais e devolvendo resposta com evidência rastreável.

O objetivo desta semana não é cobrir todos os medicamentos e exames. A entrega mínima deve provar o fluxo completo com um corpus pequeno: documento oficial, extração, fragmentação, indexação, recuperação, resposta e citação.

## Quadro Kanban

### A fazer

| ID | Tarefa | Entregável | Critério de conclusão | Prioridade |
|---|---|---|---|---|
| RAG-01 | Confirmar o recorte do piloto | Lista curta das fontes e dos tipos de pergunta aceitos | RENAME, REME-DF e Farmácia Popular classificados como `usar`, `revisar` ou `não usar`; perguntas do piloto registradas | Alta |
| RAG-02 | Simplificar e conferir a pasta `data/` | PDFs com nomes claros e README atualizado | Cada arquivo possui nome, fonte, versão/data do documento e finalidade; nenhum PDF duplicado ou de versão desconhecida entra no corpus | Alta |
| RAG-03 | Criar manifesto das fontes do corpus | Registro de proveniência | Cada fonte possui URL, título, órgão, versão, data do documento, hash, quantidade de páginas e estado de revisão | Alta |
| RAG-04 | Extrair texto dos PDFs selecionados | Arquivos de texto ou registros intermediários | Texto extraído preserva fonte e número da página; páginas sem texto ou com erro ficam sinalizadas | Alta |
| RAG-05 | Limpar e dividir o conteúdo em trechos | Corpus de chunks | Cada trecho possui `chunk_id`, texto, fonte, versão, página/seção, território e tipo de conteúdo | Alta |
| RAG-06 | Montar o primeiro índice de recuperação | Índice pesquisável | O índice pode ser recriado a partir do corpus e retorna trechos com seus metadados | Alta |
| RAG-07 | Criar busca de referência sem vetores | Baseline textual | As mesmas perguntas podem ser executadas por busca textual para comparação posterior | Média |
| RAG-08 | Definir perguntas de teste da semana | Mini golden set com 10 casos | Casos incluem resposta direta, ambiguidade, ausência de evidência e pergunta sobre estoque; cada caso aponta para evidência esperada | Alta |
| RAG-09 | Avaliar a recuperação | Relatório inicial | Para cada pergunta, registrar os cinco primeiros trechos e marcar se a evidência correta apareceu; calcular Hit@5 com números absolutos | Alta |
| RAG-10 | Integrar recuperação com geração | Demonstração ponta a ponta | Uma pergunta retorna resposta, fonte, página e limitação; o modelo não usa informação fora dos trechos recuperados | Alta |
| RAG-11 | Testar comportamentos seguros | Evidência de testes | O sistema não confunde presença em lista com estoque, pede esclarecimento em caso ambíguo e se abstém sem evidência | Alta |
| RAG-12 | Documentar execução e limitações | Guia curto da entrega | Outro integrante consegue reproduzir a indexação e executar as perguntas; limitações e fontes usadas estão explícitas | Alta |

### Em andamento

| ID | Tarefa | Estado atual | Próximo passo |
|---|---|---|---|
| RAG-01 | Levantamento das fontes oficiais | Fontes principais localizadas e descritas | Fechar quais versões entrarão no corpus desta semana |
| RAG-02 | Organização dos documentos | PDFs já foram coletados, mas a estrutura e possíveis versões duplicadas precisam ser conferidas | Deixar todos os arquivos com nomes simples e registrar qual versão será usada |
| RAG-03 | Proveniência | Existe manifesto inicial de coleta | Acrescentar data/versão do próprio documento e estado de aprovação para o corpus |

### Em revisão

| ID | Tarefa | O que revisar | Responsável sugerido |
|---|---|---|---|
| REV-02 | Aplicabilidade das orientações | Confirmar que regras de um serviço específico não sejam generalizadas para todo o SUS-DF | Revisora de domínio |
| REV-03 | Respostas do mini golden set | Conferir fatos obrigatórios, afirmações proibidas e evidências | Engenharia de Dados + revisora de domínio |

### Concluído

| ID | Tarefa | Evidência |
|---|---|---|
| DONE-01 | Especificação funcional do MVP | `docs/engenharia-dados/especificacao-funcional-mvp.md` |
| DONE-02 | Levantamento inicial de fontes | `docs/engenharia-dados/levantamento-fontes.md` |
| DONE-03 | Coleta inicial de PDFs | Arquivos presentes em `data/` com manifesto inicial |
| REV-01 | Versão da REME-DF definida | Edição de 29/10/2026 selecionada para o corpus; arquivo de 2024 retirado |

## Ordem recomendada por dia

| Dia | Foco | Saída esperada |
|---|---|---|
| Terça-feira | Fechar corpus e versões | Fontes selecionadas, duplicidades resolvidas e manifesto conferido |
| Quarta-feira | Extração e fragmentação | Chunks rastreáveis com página, fonte e versão |
| Quinta-feira | Indexação e recuperação | Busca textual e busca do RAG retornando trechos relevantes |
| Sexta-feira | Geração e testes | Respostas com citações, mini golden set executado e falhas documentadas |
| Fim de semana, se necessário | Ajustes e documentação | Demonstração reproduzível e limitações registradas |

## Definição de pronto da semana

A entrega está pronta quando:

- pelo menos duas fontes oficiais revisadas fazem parte do corpus;
- o índice pode ser reconstruído a partir dos arquivos e configurações versionados;
- dez perguntas do mini golden set foram executadas;
- cada resposta contém fonte e página ou seção da evidência;
- os cinco primeiros resultados contêm a evidência esperada em pelo menos 8 dos 10 casos do piloto;
- perguntas sobre estoque, prescrição ou informação ausente não recebem resposta inventada;
- existe uma demonstração reproduzível executável pelo backend ou pelo terminal;
- todos os erros encontrados estão documentados, mesmo que não tenham sido corrigidos.

O resultado de 8 em 10 é uma meta de piloto para esta semana, não a meta final do projeto. A avaliação final continuará usando o golden set maior definido na especificação funcional.

## O que não precisa entrar nesta entrega

- aplicativo React Native;
- sistema multiagentes;
- leitura de receita real ou manuscrita;
- histórico do paciente;
- integração com estoque em tempo real;
- cobertura completa da RENAME ou REME-DF;
- métricas BLEU e ROUGE como critério de aprovação.

Nesta semana, a prioridade é demonstrar recuperação correta e rastreável. A comparação LLM pura versus RAG e a avaliação mais ampla pertencem à etapa seguinte do roadmap.
