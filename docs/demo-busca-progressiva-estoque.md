# Busca progressiva e estoque sob demanda

Execução real com os painéis públicos UBS/CEAF e o Gemini configurado no .env da v2.
Entrada automatizada; sem respostas ou serviços simulados. Consulta de CEP não foi usada.

```text
Sincronizando InfoSaúde; códigos UBS solicitados: 18458, 19847, 694, 695, 90224, 90226, 90380, 90491.
InfoSaúde sincronizado: referência inicial UBS 8/8 códigos. Outros produtos são consultados sob demanda, por código e descrição.
SUS Cidadão — corpus-consolidado-v5-aprovado-2026-11-10. Digite 'sair' para encerrar.
Diga o nome do medicamento e o que souber; eu mostro as concentrações e formas encontradas. Para procurar nas farmácias/UBS, informe sua região. Consulto os painéis públicos UBS e CEAF a cada pedido de estoque. A data do painel pode ser anterior à consulta.

Você: liraglutida

Agente: Encontrei 1 apresentação(ões) com as informações que você passou:
1. liraglutida — 6 mg/mL (sistema de aplicação 3 mL); solução injetável (REME-DF 2026-10-29, página 39).
Você não precisa repetir esses detalhes.
Em qual região você quer procurar nas farmácias/UBS?
Essas são apresentações documentadas, não alternativas terapêuticas nem confirmação de estoque.

Você: e tem estoque desse remédio em planaltina?

Agente: Consultando liraglutida 6 mg/mL (sistema de aplicação 3 mL) (solução injetável) para Planaltina.
UBS — API consultada em 11/11/2026 11:04 BRT.
Apresentação conferida no catálogo UBS: código 27795.
UBS de Planaltina: 20 registros sem data de extração. Os saldos informados são zero, mas não confirmam a posição de hoje.
Fonte UBS: https://info.saude.df.gov.br/saude-do-cidadao/painel-infosaude-farmacias-das-ubs/
Farmácias especializadas (CEAF), consulta separada das UBS:
Não há unidade CEAF identificada como Planaltina nesses registros. As unidades abaixo não são UBS dessa região e não indicam onde você será atendido.
- Asa Sul: o painel informa COM ESTOQUE (código 27795).
- Ceilândia: o painel informa COM ESTOQUE (código 27795).
- Gama: o painel informa COM ESTOQUE (código 27795).
O painel não informa a data dessa posição; não posso confirmar estoque de hoje.
API pública consultada em 11/11/2026 11:04 BRT.
Confirme com a farmácia antes de se deslocar. Fonte: https://info.saude.df.gov.br/saude-do-cidadao/painel-infosaude-farmacias-de-alto-custo/estoque-de-medicamentos/

Você: O que consta na REME-DF sobre liraglutida 6 mg/mL solução injetável?

Agente: Aviso: índice ausente (FileNotFoundError); busca lexical utilizada.
Consta na REME-DF 2026-10-29 (página 39) a apresentação liraglutida 6 mg/mL (sistema de aplicação 3 mL) como solução injetável, classificada em outros medicamentos do aparelho digestivo e metabolismo com indicação para controle de peso. Constar em lista oficial não garante estoque nas unidades. A informação sobre estoques específicos em Planaltina não está disponível neste recorte.

Fontes consultadas:
- F03 (REME-DF 2026-10-29), página 39: https://www.saude.df.gov.br/documents/d/saude/reme_df___29_10_2026___final-pdf [evidência evidence-8d4d96cbceb2f870e79e3b16]

Você: e tem estoque desse remédio em planaltina?

Agente: Consultando liraglutida 6 mg/mL (sistema de aplicação 3 mL) (solução injetável) para Planaltina.
UBS — API consultada em 11/11/2026 11:04 BRT.
Apresentação conferida no catálogo UBS: código 27795.
UBS de Planaltina: 20 registros sem data de extração. Os saldos informados são zero, mas não confirmam a posição de hoje.
Fonte UBS: https://info.saude.df.gov.br/saude-do-cidadao/painel-infosaude-farmacias-das-ubs/
Farmácias especializadas (CEAF), consulta separada das UBS:
Não há unidade CEAF identificada como Planaltina nesses registros. As unidades abaixo não são UBS dessa região e não indicam onde você será atendido.
- Asa Sul: o painel informa COM ESTOQUE (código 27795).
- Ceilândia: o painel informa COM ESTOQUE (código 27795).
- Gama: o painel informa COM ESTOQUE (código 27795).
O painel não informa a data dessa posição; não posso confirmar estoque de hoje.
API pública consultada em 11/11/2026 11:04 BRT.
Confirme com a farmácia antes de se deslocar. Fonte: https://info.saude.df.gov.br/saude-do-cidadao/painel-infosaude-farmacias-de-alto-custo/estoque-de-medicamentos/

Você: sair
Até logo.

```
