# Regressão corrigida: liraglutida na REME-DF

A pergunta válida era rejeitada porque a busca exigia o campo literal inteiro
`6 mg/mL (sistema de aplicação 3 mL)`. A concentração agora pode ser informada
sem o detalhe do dispositivo; a resposta preserva a apresentação completa.
Espaços ao redor de `/` e entre número/unidade não alteram a identificação.
Concentração, unidade ou sistema de aplicação explicitamente divergentes continuam
sem correspondência. Havendo vários dispositivos, o chat pede esclarecimento.
Anotações químicas de equivalência não são descartadas por essa regra.

Validação final: **229 testes passaram**, incluindo **20 regressões novas**.
Ruff, formatação e Mypy passaram nos quatro arquivos Python envolvidos na correção.

`liraglutid` gera uma sugestão de `liraglutida`, sem evidências nem seleção
silenciosa. No chat, `sim` confirma e executa a pergunta corrigida.
O erro de digitação `contsa` não interfere na identificação do medicamento.

## Perguntas exatas reportadas

| Pergunta | Antes | Depois |
|---|---|---|
| liraglutid 6mg/ml | Informe apresentação exata | Você quis dizer liraglutida? |
| liraglutid 6 mg/ml | Informe apresentação exata | Você quis dizer liraglutida? |
| liraglutida 6 mg/ml, com “contsa” | Concentração não localizada | Correspondência F03, página 39 |
| liraglutida 6 mg/mL, com “consta” | Concentração não localizada | Correspondência F03, página 39 |

## Chat real sem chave

Entrada automatizada e geração desabilitada por configuração vazia; sem modelo
simulado, sem nova sincronização. Corpus e evidências reais da v5.

```text
SUS Cidadão — corpus-consolidado-v5-aprovado-2026-11-10. Digite 'sair' para encerrar.
Contexto em memória. Informe medicamento, concentração e forma. Fontes documentais não comprovam estoque UBS ou elegibilidade. Estoque exige vínculo UBS validado. Busca lexical disponível sem índice.

Você: O que contsa na reme-df sobre liraglutid 6mg/ml solução injetável?

Agente: Você quis dizer liraglutida? Responda 'sim' ou informe o nome correto.

Você: sim

Agente: Aviso: APP_GOOGLE_API_KEY ausente; resposta documental utilizada.
liraglutida 6 mg/mL (sistema de aplicação 3 mL) (solução injetável) consta nas fontes: F03. Presença em lista não confirma estoque.
- liraglutida solução injetável 6mg/mL Outros medicamentos do
633. 2 7795 sistema de aplicação 3mL multidoses de aparelho digestivo e Farmácia do Componente Especializado
até 3,0 mg (indicação: controle de peso) metabolismo

Fontes consultadas:
- F03 (REME-DF 2026-10-29), página 39: https://www.saude.df.gov.br/documents/d/saude/reme_df___29_10_2026___final-pdf [evidência evidence-8d4d96cbceb2f870e79e3b16]

Limite desta resposta documental: presença em lista não garante estoque; documentos e elegibilidade não verificados.

Você: sair
Até logo.

```

## Validação com modelo configurado na v2

Executado `app.py ask` com a pergunta correta, o mesmo release, `--documental`
e `--strategy lexical`. O Gemini retornou texto natural identificando liraglutida
6 mg/mL solução injetável, sistema de aplicação de 3 mL, na REME-DF de 29/10/2026,
com referência F03, página 39, e aviso de que presença na lista não garante estoque.
Nenhum índice vetorial foi necessário. A indicação citada pelo modelo corresponde
ao elenco documental e não representa recomendação individual.

Fonte documental: https://www.saude.df.gov.br/documents/d/saude/reme_df___29_10_2026___final-pdf
Evidência: `evidence-8d4d96cbceb2f870e79e3b16`.
