# Decisão humana — correção da claritromicina na v9

**Decisão:** aprovada por Jhiovana, engenharia de dados e responsável pelo projeto, em 12/11/2026.

**Autorização textual nesta conversa:** “pode aprovar a revisao”, em resposta ao pedido de confirmação da normalização de `500mg` para `500 mg` e do vínculo da linha 249 à mesma apresentação das linhas 247–248 da REME-DF.

**Candidato revisado:** `corpus-consolidado-v9-claritromicina-normalizada-2026-11-12`, SHA-256 do manifesto `60e8218b7968103940894ed513b062f988b085b0e7b01bcdd65a464442f34614`; fingerprint de conteúdo `d65ad02bc66ae9d5c98ffa8475f39e4b5a674254ff9e55abae00c0ef80406faa`. O escopo e a evidência técnica constam em [auditoria-claritromicina-v9.md](auditoria-claritromicina-v9.md).

**Escopo da aprovação:** identidade documental da apresentação claritromicina 500 mg comprimido nas linhas F03 247–249. A grafia `500mg` da linha 249 é normalizada no campo estruturado; código, contexto, canal, página, linha e texto literal permanecem próprios de cada ocorrência. A decisão também autoriza publicar o release imutável v9 aprovado para indexação e recuperação de presença documental nas edições congeladas F01/F03/F04, com as restrições herdadas da v8.

**Limites:** não aprova equivalência terapêutica, dispensação entre canais, disponibilidade, elegibilidade, orientação individual ou o desempenho do RAG. Os outros 78 pares de identidade normalizada não receberam decisão. O `test` v8 permanece histórico e não pode ser usado para declarar o gate v9 aprovado. Embeddings dependem de um novo teste independente que satisfaça os critérios do gate.
