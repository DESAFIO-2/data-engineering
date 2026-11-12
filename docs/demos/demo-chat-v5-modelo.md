# Demonstração reproduzível do chat v5

Baseline: `420d344193c535f80c3150e7c5058c48df8dad22`. Depois: árvore de trabalho. Modo: modelo local configurado na v2.

As mesmas perguntas são fornecidas às três execuções. A seleção v5 anterior falha antes de consumir a primeira pergunta. Entrada automatizada; sem modelo simulado. O estoque usa o snapshot público real salvo localmente, quando presente; a sincronização de abertura é substituída pela reutilização desse snapshot.

Snapshot consultado: `2026-11-11T13:15:18.880661+00:00`.

## Antes: seleção explícita da v5

Saída: 1.

```text
Erro: Registro de aprovação ausente ou divergente

```

## Antes: lote legado

Saída: 0.

```text
Sincronizando estoque e localização do InfoSaúde...
Demonstração: reutilizando o snapshot local; sem nova sincronização.
SUS Cidadão — lote de 6 apresentações. Digite 'sair' para encerrar.
A recuperação documental combina correspondência lexical e busca vetorial; se a vetorial falhar, o chat usa lexical e avisa.
Para estoque, informe medicamento + concentração + forma farmacêutica e, se desejar, a região. Ex.: ‘Tem sinvastatina 40 mg comprimido em Planaltina?’
Formas que pode informar: comprimido, cápsula, líquido, tópico, adesivo, creme, dispositivo, espuma, gel, gotas, inalador, injeção, loção, pomada, pó, spray, supositório. Se a forma não existir no recorte, serão mostradas as opções disponíveis. O estoque ao vivo está disponível apenas para apresentações mapeadas.
Para consultar informações documentais, pergunte pelo medicamento e dado desejado, por exemplo: ‘O que consta na RENAME sobre metformina 500 mg comprimido?’ O chat mantém apenas o contexto desta conversa, em memória.

Você: Oi

Agente: Olá! Posso ajudar a consultar informações do corpus e, quando houver código validado, o estoque do InfoSaúde. Para uma busca mais precisa, informe o medicamento, a concentração e a forma farmacêutica — por exemplo: ‘Tem sinvastatina 40 mg comprimido em Planaltina?’ Formas que você pode informar: comprimido, cápsula, líquido, tópico, adesivo, creme, dispositivo, espuma, gel, gotas, inalador, injeção, loção, pomada, pó, spray, supositório. Vou verificar se a forma existe no recorte; se não existir, informarei as formas disponíveis.

Você: O que consta na RENAME sobre metformina?

Agente: AVISO: Busca vetorial indisponível (ValueError); resultado conferido pela busca lexical.
Não localizado no recorte consultado: seis apresentações.

Você: 850 mg

Agente: AVISO: Busca vetorial indisponível (ValueError); resultado conferido pela busca lexical.
Não localizado no recorte consultado: seis apresentações.

Você: comprimido

Agente: AVISO: Busca vetorial indisponível (ValueError); resultado conferido pela busca lexical.
Não localizado no recorte consultado: seis apresentações.

Você: Tem estoque UBS em Planaltina?

Agente: Não localizado no recorte consultado: seis apresentações.

Você: E na Farmácia Popular?

Agente: AVISO: Busca vetorial indisponível (ValueError); resultado conferido pela busca lexical.
Não localizado no recorte consultado: seis apresentações.

Você: Posso trocar pela de ação prolongada?

Agente: AVISO: Busca vetorial indisponível (ValueError); resultado conferido pela busca lexical.
Não localizado no recorte consultado: seis apresentações.

Você: sair
Até logo.

```

## Depois: chat consolidado v5

Saída: 0.

```text
Demonstração: reutilizando o snapshot local; sem nova sincronização.
SUS Cidadão — corpus-consolidado-v5-aprovado-2026-11-10. Digite 'sair' para encerrar.
Contexto em memória. Informe medicamento, concentração e forma. Fontes documentais não comprovam estoque UBS ou elegibilidade. Estoque exige vínculo UBS validado. Busca lexical disponível sem índice.

Você: Oi

Agente: Olá! Posso ajudar a consultar informações do corpus e, quando houver código validado, o estoque do InfoSaúde. Para uma busca mais precisa, informe o medicamento, a concentração e a forma farmacêutica — por exemplo: ‘Tem sinvastatina 40 mg comprimido em Planaltina?’ Formas que você pode informar: comprimido, cápsula, líquido, tópico, adesivo, creme, dispositivo, espuma, gel, gotas, inalador, injeção, loção, pomada, pó, spray, supositório. Vou verificar se a forma existe no recorte; se não existir, informarei as formas disponíveis.

Você: O que consta na RENAME sobre metformina?

Agente: Informe a concentração. Neste recorte: 500 mg, 850 mg.

Você: 850 mg

Agente: Informe a forma farmacêutica. Formas disponíveis: comprimido.

Você: comprimido

Agente: Aviso: índice ausente (FileNotFoundError); busca lexical utilizada.
O cloridrato de metformina 850 mg comprimido consta na versão F01 (RENAME 2024, 2ª edição, componente Básico). Constar em lista não garante estoque. A informação sobre documentos, elegibilidade e estoque não está disponível neste recorte.

Fontes consultadas:
- F01 (RENAME 2024, 2ª edição), página 28: https://www.gov.br/saude/pt-br/composicao/sectics/rename/publicacoes/relacao-nacional-de-medicamentos-essenciais-2024 [evidência evidence-f16957cc6029096a75e2c5af]

Limite desta resposta documental: presença em lista não garante estoque; documentos e elegibilidade não verificados.

Você: Tem estoque UBS em Planaltina?

Agente: O painel UBS registra saldo positivo para METFORMINA (CLORIDRATO) COMPRIMIDO 850 MG (código 90226) em 15 farmácias em Planaltina.
Extração do painel: 10/11/2026 21:16 BRT.
O saldo pode mudar após a extração; confirme na unidade antes de ir.
- UBS 1 PLANALTINA (Planaltina, CNES 5167817) — QUADRA 18 CONJUNTO H AREA ESPECIAL, 01, BURITIS IV ST LESTE, PLANALTINA — mapa: https://www.google.com/maps/search/?api=1&query=-15.617745%2C-47.641095
  Saldo registrado: 4220.
- UBS 10 TAQUARA PLANALTINA (Planaltina, CNES 2804174) — NUCLEO RURAL TAQUARA, QUADRA 1, AREA ESPECIAL, 0, PLANALTINA — mapa: https://www.google.com/maps/search/?api=1&query=-15.629319%2C-47.518272
  Saldo registrado: 1260.
- UBS 11 RAJADINHA PLANALTINA (Planaltina, CNES 0011576) — NUCLEO RURAL RAJADINHA II RUA 2 LOTE 16/17, 16, CHACARA RIACHO DOCE, PLANALTINA — mapa: https://www.google.com/maps/search/?api=1&query=-15.746663%2C-47.662715
  Saldo registrado: 4796.
- UBS 12 BICA DO DER PLANALTINA (Planaltina, CNES 2804123) — RODOVIA DF-128, KM 21, S/N, CAMPUS IFB, PLANALTINA — mapa: https://www.google.com/maps/search/?api=1&query=-15.633893%2C-47.674468
  Saldo registrado: 3850.
- UBS 13 SAO JOSE PLANALTINA (Planaltina, CNES 0011622) — DF 250 NUCLEO RURAL SAO JOSE AREA ESPECIAL, 0, SAO JOSE, PLANALTINA — mapa: https://www.google.com/maps/search/?api=1&query=-15.704136%2C-47.373487
  Saldo registrado: 19370.
Exibindo 5 de 15 farmácias com saldo positivo.
Fonte: https://info.saude.df.gov.br/saude-do-cidadao/painel-infosaude-farmacias-das-ubs/

Você: E na Farmácia Popular?

Agente: O cloridrato de metformina 850 mg consta na versão F04 (Farmácia Popular 2026-08-31). Constar em lista não garante estoque. Informações sobre documentos, elegibilidade e estoque não estão disponíveis neste recorte.

Fontes consultadas:
- F04 (Farmácia Popular 2026-08-31), página 1: https://www.gov.br/saude/pt-br/composicao/sectics/farmacia-popular/arquivos/elenco-de-medicamentos-e-insumos-pfpb.pdf [evidência evidence-5cad8bf5fd4bf3b66565f60b]

Limite desta resposta documental: presença em lista não garante estoque; documentos e elegibilidade não verificados.

Você: Posso trocar pela de ação prolongada?

Agente: Não posso orientar dose, indicação individual, elegibilidade ou troca de medicamento, nem afirmar equivalência terapêutica. Consulte um profissional de saúde.

Você: sair
Até logo.

```
