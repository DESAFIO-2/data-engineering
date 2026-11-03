# SDD — Ingestão de fontes dinâmicas e armazenamento

> Documento histórico de contexto. A especificação normativa atualizada está em [especificacao-ingestao-dados-vivos.md](especificacao-ingestao-dados-vivos.md).

**Status:** Em Avaliação  
**Escopo:** fundação de engenharia de dados do SUS Cidadão; sem RAG, embeddings ou lógica de resposta.

## Objetivos e princípios

O pipeline deve coletar fontes vivas ou semiestruturadas, preservar o que foi recebido e permitir reprocessamento determinístico. Conectores não conhecem o banco de dados: dependem dos contratos em `src/sus_cidadao_data/ingestion` e `storage`. Toda coleta recebe `source_id`, URL/página de origem, timestamp UTC, status HTTP quando aplicável, versão do esquema, hash do conteúdo e detalhes de validação.

## Arquitetura em camadas

### Bronze — bruto e auditável

Armazena o payload original (JSON, HTML ou resposta de API) sem normalização, junto de metadados de coleta. O armazenamento é append-only por execução, identificado por hash, com particionamento lógico por `source_id` e data. Falhas de rede e respostas inválidas devem gerar evento de erro com contexto, sem substituir a última coleta válida.

### Silver — normalizado

Transforma Bronze em entidades estáveis e relacionais, mantendo a proveniência. Para o piloto, o núcleo é:

- `medication`: identificador da fonte, nome, princípio ativo, apresentação e unidade;
- `pharmacy`: unidade dispensadora, endereço, município/UF e contatos;
- `stock_snapshot`: medicamento, farmácia, status/quantidade informada, horário da observação e qualidade do dado;
- `ingestion_run`: fonte, início/fim, versão do esquema, contagens, hash e erros.

Campos ausentes permanecem nulos; não se deve inferir “disponível” a partir da simples presença de um medicamento. Cada registro Silver referencia o artefato Bronze de origem.

### Gold — visões analíticas

Visões derivadas, recriáveis a partir da Silver, como disponibilidade por unidade, medicamentos sem atualização recente, cobertura por região e série temporal de estoque. Gold não é fonte de verdade e não deve receber escrita manual.

## Portal piloto: InfoSaúde DF

**Recorte:** Painel de Farmácias de Alto Custo — Estoque de Medicamentos.

1. Descobrir o endpoint ou requisições XHR usadas pelo painel, registrando URL, método, parâmetros e formato; não depender de scraping visual se houver API observável.
2. Executar coleta inicial controlada, respeitando limites do portal e identificando `source_id=infosaude-df-alto-custo`.
3. Persistir a resposta integral em Bronze antes de qualquer parsing. Registrar timestamp UTC, status, headers relevantes não sensíveis, URL, hash e versão do contrato observado.
4. Validar schema mínimo: resposta não vazia, campos de unidade/medicamento reconhecíveis e tipos coerentes. Mudanças de schema interrompem a promoção para Silver e geram alerta.
5. Normalizar nomes e apresentações sem apagar o valor original; mapear a unidade por chave estável quando disponível.
6. Modelar estoque como observação temporal (`stock_snapshot`), nunca como estado permanente. O horário exibido pelo portal e o horário da coleta devem ser distintos.
7. Testar paginação, filtros, duplicidades, encoding, indisponibilidade e respostas parciais. Manter fixtures anonimizadas para testes, sem credenciais ou dados pessoais.

## ADR-001 — tecnologia de persistência

**Status: Em Avaliação.** A aplicação usará Repository Pattern: casos de uso dependem de interfaces de Bronze/Silver, e adaptadores concretos ficam fora do domínio. Assim, a escolha abaixo não fica espalhada pelo código.

| Opção | Vantagens | Riscos/limites | Adequação inicial |
|---|---|---|---|
| DuckDB | Analítico local, Parquet, ótimo para exploração e Gold | Concorrência e operação multiusuário limitadas | Forte candidata para protótipo |
| SQLite | Zero operação, simples, portátil e transacional | Menos recursos analíticos e concorrência limitada | Candidata para metadados/fixtures |
| PostgreSQL | Robusto, concorrente, extensível e pronto para produção | Operação, custo e infraestrutura maiores | Candidata para produção |
| Lakehouse em arquivos | Escala, baixo acoplamento e histórico barato | Governança, catálogo, compactação e concorrência exigem disciplina | Candidata para volume/histórico |

**Decisão provisória:** manter a interface e um adaptador local JSON nesta etapa; comparar DuckDB e PostgreSQL com uma carga real do piloto antes de decidir. O formato de Bronze deve continuar exportável para arquivos, preservando portabilidade para um eventual lakehouse.

## Operação e qualidade

Cada execução deve ser idempotente por hash e chave de observação, observável por contagens Bronze/Silver, taxa de validação, atraso da fonte e idade do último estoque. Segredos ficam fora do repositório. Dados locais em `data/bronze`, `data/silver` e `data/gold` são ignorados pelo Git, exceto os marcadores de diretório.
