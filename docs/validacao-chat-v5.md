# Validação do chat consolidado — 11/11/2026

## Comparação e comportamento

Antes da mudança, `conversation.py`, `retrieval.py`, `answer.py` e `config.py`
eram idênticos aos da v1. Os testes de conversa, resposta, recuperação, release,
InfoSaúde e provedores também eram iguais. A CLI v2 havia acrescentado o despacho
consolidado para index/search/ask/eval, excluindo chat; o sintetizador ainda exigia
`medicine["lists"]`. A sincronização UBS usava seis códigos fixos.

As transcrições usam a mesma sequência e incluem tanto a tentativa de selecionar
v5 antes da correção (erro antes da primeira entrada) quanto o chat legado:

- [Antes/depois sem chave](demo-chat-v5.md).
- [Antes/depois com Gemini real](demo-chat-v5-modelo.md).

O fluxo v5 pede concentração e forma em turnos sucessivos, mostra metformina 850 mg
na RENAME 2024, página 28, consulta UBS em Planaltina pelo código 90226 e responde
à pergunta seguinte sobre Farmácia Popular pela F04, página 1. A troca por ação
prolongada é bloqueada. Na execução com modelo, a ausência de índice gerou aviso,
mas a geração continuou usando evidências lexicais.

## Consulta pública UBS

A consulta inicial de rede restrita falhou por DNS. A consulta pública permitida
fora dessa restrição funcionou. A projeção de todo o catálogo atingiu o limite
e foi recusada; a consulta com filtro de nome no servidor retornou 13 pares de
código/descrição contendo metformina, incluindo associações que foram excluídas.

Foram habilitados 90224 (500 mg comprimido) e 90226 (850 mg comprimido), com três
vínculos a apresentações explícitas F01/F03. O arquivo de vínculos guarda o catálogo
observado, a fonte, a data e o fingerprint do release. O código 13142 de ação
prolongada permanece excluído porque a ocorrência F04 não informa a forma.

A sincronização real retornou os oito códigos solicitados. Na consulta registrada,
o painel indicava saldo positivo de 850 mg em 15 farmácias de Planaltina, com extração
de 10/11/2026 às 21:16 BRT. Isso é um registro datado, não garantia de estoque atual
nem comprovação de disponibilidade na Farmácia Popular.

## Testes e verificações

Resultado final: **209 testes passaram**, incluindo **52 testes novos** do chat
consolidado. A última execução completa levou 42,93 segundos.

Após o relato sobre liraglutida, a [correção de identificação de apresentações](regressao-liraglutida.md)
acrescentou 20 regressões: **229 testes passaram** na execução completa seguinte.

A evolução para busca progressiva e estoque sob demanda acrescentou mais 22
testes: **251 passaram na suíte completa**. Após os ajustes finais de apresentação,
104 testes direcionados também passaram. Ruff/formatação passaram nos nove arquivos
Python desta evolução; Mypy passou nos sete arquivos verificados. Esta rodada usou
o `.venv` já instalado da própria v2.

Agora o chat aceita só o nome e mostra apresentações, permite escolher por número,
preserva medicamento/região e consulta UBS/CEAF em cada pedido de estoque. A
[demonstração atual](demo-busca-progressiva-estoque.md) usa serviços reais. Os oito
códigos iniciais não são mais a fronteira da consulta. O RAG documental continua
separado do estoque; índices semânticos não são necessários para consultar a API.
Datas nulas nos painéis são expostas como limitação, sem afirmar estoque em tempo real.

Foram acrescentados testes de despacho por manifesto/configuração, conversa,
mudança de região/fonte/medicamento, esclarecimento de liberação, falhas vetoriais,
geração, configuração ausente, vínculos UBS e limites clínicos. Saldos UBS do
histórico são removidos do contexto enviado à geração documental.

Ruff e verificação de formatação passaram nos 11 arquivos Python alterados/novos.
Mypy passou nos nove arquivos novos ou com mudanças funcionais relevantes, exceto
a CLI legada, cujo erro anterior em `_ask` permanece na checagem global.
`git diff --check` passou. Os artefatos foram conferidos contra a chave local:
nenhuma credencial foi encontrada.

As verificações globais ainda registram 344 ocorrências Ruff e 25 erros Mypy em
cinco arquivos anteriores a esta mudança. Esses problemas não foram corrigidos
por estarem fora do fluxo implementado.

A primeira suíte encontrou dois testes dependentes de arquivos silver ignorados
pelo Git e ausentes localmente. Esses arquivos foram reconstruídos dos PDFs locais,
sem alterar releases aprovados, corpus ou snapshots documentais publicados.

O `uv` conseguiu usar cache local, mas a instalação de dependências foi impedida
por DNS. Os testes foram executados com Python 3.12 e as dependências já instaladas
no ambiente virtual da v1, carregando o código **da v2** por `PYTHONPATH=src` e pela
configuração do pytest. Nenhuma credencial da v1 foi lida ou copiada.

Comandos equivalentes em um ambiente v2 com dependências instaladas:

```powershell
uv run pytest -q --basetemp .test-tmp-chat-v5-verification
uv run ruff check src/rag/cli.py src/rag/answer.py src/rag/consolidated.py src/rag/consolidated_cli.py src/rag/consolidated_chat.py src/rag/live.py src/ingestion/infosaude_live.py scripts/validate_ubs_metformin.py scripts/demo_consolidated_chat.py tests/unit/test_consolidated_chat.py tests/unit/test_infosaude_live.py
```
