# Preparação da próxima rodada independente da recuperação v9

**Estado em 12/11/2026:** filtro de identidade corrigido em desenvolvimento; candidato novo preparado e **não avaliado**. O gate v9 anterior permanece reprovado e seus dois resultados oficiais seguem intactos. Não há aprovação humana deste candidato, dataset congelado novo nem execução do novo `test`.

## Mudança de desenvolvimento

O filtro passou a reconhecer descrições textuais com artigo opcional, liberação retardada distinta de prolongada e convencional, faixas de dose com recipiente, volume com acondicionamento e associações com dose após cada fármaco. Os testes sintéticos de desenvolvimento usam famílias que não aparecem no `test` v9 anterior e verificam também doses, unidades, formas e fontes incompatíveis. O release v9, seus 2.114 chunks, os resultados oficiais v8/v9 e a identidade aprovada das três linhas F03 de claritromicina não foram alterados.

## Candidato e fontes

- [Candidato](../../evals/datasets/consolidated_v9_next_test_candidate_unreviewed.jsonl): 28 casos, sendo 24 positivos e quatro negativos; SHA-256 `9d7144c51b201fa2b954ca33ac86a2061bcc2099bb8ee430aadd6c70af5a207e`.
- [Folha de revisão](v9-next-independent-test-review.md): todas as 28 decisões pendentes; SHA-256 inicial `75d52cfe1fd90f61139a42358992fb148963aa6309bb484804e3818d6eb72304`.
- Distribuição: F01 11 positivos e um negativo; F03 dez positivos e dois negativos; F04 três positivos e um negativo. As 21 famílias positivas F01/F03 não constam dos datasets v8/v9 anteriores. As três famílias positivas F04 já ocorreram na v8, mas não no `dev` nem no `test` v9: o release F04 tem 28 famílias e todas já foram usadas historicamente. Esta reutilização foi escolhida pela responsável e limita a independência dessa fonte.
- As 26 referências dos 24 positivos foram comparadas com `evidencias.jsonl` quanto a ID, fonte, página, linha, medicamento, princípio ativo, concentração e forma; os termos de princípio ativo, concentração e forma foram localizados nas páginas indicadas dos PDFs. A revisão humana deve confirmar cada linha e a qualidade das perguntas.
- PDFs auditados: F01 SHA-256 `a991dd0934774854dbe087a259a484c21fdf70ad2d27f4af5ba5a5c51a2a15bc`; F03 `299ff632a4e55d1dabbc953dc9c9e09f1cf6bbe2cabef8bf45fec5fbd5139fb6`; F04 `beb2cf59b835e94e2e016b009bd2b17f5d0375ab593db00f983211c2cfbc32b3`.

## Ausência verificada para os quatro negativos

Foi inspecionado o texto extraído de todas as páginas de cada PDF e cada ocorrência do princípio ativo na fonte perguntada. O catálogo do release também foi consultado por fonte, nome, concentração e forma. A ausência é relativa à lista oficial perguntada.

| Caso | Apresentação ausente | Apresentações documentadas na fonte |
|---|---|---|
| V9-R2-025, F01 | calcitriol 0,5 mcg cápsula | 0,25 mcg cápsula, PDF pp. 27 e 187. |
| V9-R2-026, F03 | digoxina 0,125 mg comprimido | 0,25 mg comprimido, PDF p. 26, item 357. |
| V9-R2-027, F03 | misoprostol 100 mcg comprimido vaginal | 25 mcg e 200 mcg comprimido vaginal, PDF p. 42, itens 704–707. |
| V9-R2-028, F04 | captopril 50mg | 25mg, PDF p. 1, linha 17; a fonte não declara forma farmacêutica. |

## Próximo gate

Jhiovana deve revisar os 28 casos na folha, registrar `Aprovado` ou `Rejeitado`, seu nome e a data. `scripts/promote_v9_next_test.py` recusa qualquer pendência, divergência ou sobrescrita; o comando `eval` vincula o futuro dataset `consolidated_v9_next_reviewed.jsonl` à nova folha. Após 28 aprovações, congelar o dataset e o código em Git, executar o novo `test` uma vez por estratégia e aplicar os mesmos limiares: Hit@5 ≥ 0,90, MRR@5 ≥ 0,80, zero confusões críticas e 100% das citações emitidas verificáveis. Não reutilizar o resultado anterior como nova avaliação, nem iniciar embeddings antes de aprovação.
