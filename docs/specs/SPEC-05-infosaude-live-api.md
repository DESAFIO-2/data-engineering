# InfoSaúde-DF no RAG

**Objetivo:** Descrever a sincronização dos painéis públicos do InfoSaúde-DF e o uso dos snapshots no RAG.

## 1. Sincronização e snapshot

Ao iniciar `uv run python app.py chat`, o programa sincroniza três painéis públicos do InfoSaúde-DF antes de abrir a conversa: estoque CEAF, estoque UBS e cadastro de unidades. `uv run python app.py sync-live` faz apenas a sincronização; `ask` usa o snapshot salvo. As consultas usam o cabeçalho público `X-PowerBI-ResourceKey` de cada relatório e decodificam o formato DSR do Power BI (`C`, `R`, `Ø` e `ValueDicts`). O snapshot é salvo atomicamente em `data/gold/infosaude_live_snapshot.json`, ignorado pelo Git. Se a atualização do `chat` falhar, ele avisa e usa o último snapshot salvo, se houver. Não há agendamento configurado.

Na verificação de 05/11/2026, os painéis retornaram 857 linhas CEAF, 1.116 linhas UBS para os seis códigos do lote e 228 unidades cadastradas, das quais 171 tinham coordenadas. Esses números podem mudar. O código recusa consultas truncadas ou sem os seis códigos UBS e preserva o snapshot anterior em caso de falha.

## 2. Uso no RAG e limites

### Busca progressiva e consultas sob demanda

O chat consolidado aceita só o nome e lista as concentrações, formas e
características documentadas, sem exigir que o usuário conheça esses campos.
É possível escolher uma opção por número ou por detalhes; apresentação e região
ficam em memória durante a sessão. Uma apresentação única não precisa ser repetida.

Os oito códigos da sincronização inicial são apenas uma referência. Cada pedido
de estoque resolve o produto no catálogo público UBS e faz consulta filtrada ao
estoque UBS, além de consultar o CEAF separadamente. A validação compara princípio
ativo completo, concentração, forma, dispositivo, liberação e código F03 quando
documentado. Sem correspondência segura ou com vários códigos, não se escolhe um
produto por similaridade. A API CEP/UBS de referência não foi integrada.

Os caches por apresentação são gravados atomicamente em
`data/gold/stock_queries/`, sem perguntas ou CEP, vinculados ao fingerprint do
release. Cada canal guarda seu horário de coleta; falha parcial preserva o outro
canal. Se a rede falhar, dados anteriores são identificados como snapshot anterior.
Horário de consulta e data da posição são distintos: campos de data nulos não
permitem confirmar estoque hoje, mesmo em uma resposta recém-consultada.

Na consulta de liraglutida de 11/11/2026, o código `27795` coincidiu com a ocorrência
F03 e com as descrições dos painéis. UBS retornou 20 registros de Planaltina com
saldo zero e data nula; CEAF informou “COM ESTOQUE” em Asa Sul, Ceilândia e Gama,
também sem data da posição. Esses locais são apresentados como CEAF, sem atribuir
ao usuário uma unidade de atendimento. Código `37352` e associação com insulina
foram excluídos dessa correspondência. Ver [execução real](../demos/demo-busca-progressiva-estoque.md).

### Release consolidado v5 (11/11/2026)

`uv run python app.py chat --release data/releases/corpus-consolidado-v5-aprovado-2026-11-10`
seleciona o fluxo consolidado pelo manifesto. Nesse fluxo, `--documental` desativa
também a sincronização de abertura; o comportamento legado continua preservado.

O catálogo UBS é consultado com projeção distinta de código/descrição e filtro
de nome no servidor; consultas truncadas são recusadas. Foram verificados os códigos
`90224` (metformina 500 mg comprimido) e `90226` (850 mg comprimido). Os três vínculos
com apresentações explícitas F01/F03, o catálogo observado, a data e o fingerprint
do release estão em `data/mappings/ubs_consolidated.json`. A sincronização consolidada
inclui esses dois códigos e os seis legados, com cobertura real de 8/8 códigos
na verificação. Se faltar qualquer código solicitado, o snapshot anterior é preservado.

O código `13142` de ação prolongada não foi habilitado: a ocorrência F04 não
documenta a forma. Associações com outros princípios ativos foram excluídas.
`uv run python -m scripts.validate_ubs_metformin` repete a validação pública.

O saldo UBS é filtrado pela região pedida, inclusive quando ela não tem registros
no snapshot. Ausência de registro não é saldo zero. Presença documental na Farmácia
Popular é respondida pela F04 e não comprova estoque UBS ou disponibilidade de dispensação.
Os saldos continuam fora do contexto enviado ao modelo.

O RAG mantém documentos e evidências aprovadas no Chroma. Estoque e endereço são lidos do snapshot no momento da pergunta e respondidos diretamente pelo código, sem passar os saldos ao modelo de linguagem. A associação entre o release e o painel UBS usa código e descrição exata do produto. O agente mostra até cinco unidades com saldo positivo datado, endereço, mapa quando houver coordenadas, data da extração e link da fonte. Se a extração tiver mais de 48 horas, avisa que está desatualizada. Saldos e locais podem mudar; confirme com a unidade antes de ir.

O estoque CEAF é preservado no snapshot para evolução da integração, mas não é associado às seis apresentações do release atual. A consulta de localização pode encontrar unidades por nome ou bairro, sem precisar citar um medicamento. O snapshot não valida elegibilidade, documentos exigidos ou dispensação efetiva.

## 3. Exemplos de consulta

Exemplos após sincronizar:

```bash
uv run python app.py ask "Onde tem estoque de sinvastatina 20 mg comprimido no Plano Piloto?"
uv run python app.py ask "Onde fica UBS 01 DCCP?"
```
