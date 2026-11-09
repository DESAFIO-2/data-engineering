# InfoSaúde-DF no RAG

**Objetivo:** Descrever a sincronização dos painéis públicos do InfoSaúde-DF e o uso dos snapshots no RAG.

## 1. Sincronização e snapshot

Ao iniciar `uv run python app.py chat`, o programa sincroniza três painéis públicos do InfoSaúde-DF antes de abrir a conversa: estoque CEAF, estoque UBS e cadastro de unidades. `uv run python app.py sync-live` faz apenas a sincronização; `ask` usa o snapshot salvo. As consultas usam o cabeçalho público `X-PowerBI-ResourceKey` de cada relatório e decodificam o formato DSR do Power BI (`C`, `R`, `Ø` e `ValueDicts`). O snapshot é salvo atomicamente em `data/gold/infosaude_live_snapshot.json`, ignorado pelo Git. Se a atualização do `chat` falhar, ele avisa e usa o último snapshot salvo, se houver. Não há agendamento configurado.

Na verificação de 05/11/2026, os painéis retornaram 857 linhas CEAF, 1.116 linhas UBS para os seis códigos do lote e 228 unidades cadastradas, das quais 171 tinham coordenadas. Esses números podem mudar. O código recusa consultas truncadas ou sem os seis códigos UBS e preserva o snapshot anterior em caso de falha.

## 2. Uso no RAG e limites

O RAG mantém documentos e evidências aprovadas no Chroma. Estoque e endereço são lidos do snapshot no momento da pergunta e respondidos diretamente pelo código, sem passar os saldos ao modelo de linguagem. A associação entre o release e o painel UBS usa código e descrição exata do produto. O agente mostra até cinco unidades com saldo positivo datado, endereço, mapa quando houver coordenadas, data da extração e link da fonte. Se a extração tiver mais de 48 horas, avisa que está desatualizada. Saldos e locais podem mudar; confirme com a unidade antes de ir.

O estoque CEAF é preservado no snapshot para evolução da integração, mas não é associado às seis apresentações do release atual. A consulta de localização pode encontrar unidades por nome ou bairro, sem precisar citar um medicamento. O snapshot não valida elegibilidade, documentos exigidos ou dispensação efetiva.

## 3. Exemplos de consulta

Exemplos após sincronizar:

```bash
uv run python app.py ask "Onde tem estoque de sinvastatina 20 mg comprimido no Plano Piloto?"
uv run python app.py ask "Onde fica UBS 01 DCCP?"
```
