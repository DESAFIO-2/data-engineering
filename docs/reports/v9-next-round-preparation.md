# Preparação da próxima rodada independente da recuperação v9

**Estado em 12/11/2026:** filtro de identidade corrigido em desenvolvimento; candidato novo preparado e **ainda não avaliado**. O gate v9 anterior permanece reprovado e seus dois resultados oficiais seguem intactos. A responsável autorizou expressamente o registro das 28 aprovações em seu nome; o novo dataset foi promovido e congelado antes do `test`.

## Mudança de desenvolvimento

O filtro passou a reconhecer descrições textuais com artigo opcional, liberação retardada distinta de prolongada e convencional, faixas de dose com recipiente, volume com acondicionamento e associações com dose após cada fármaco. Os testes sintéticos de desenvolvimento usam famílias que não aparecem no `test` v9 anterior e verificam também doses, unidades, formas e fontes incompatíveis. O release v9, seus 2.114 chunks, os resultados oficiais v8/v9 e a identidade aprovada das três linhas F03 de claritromicina não foram alterados.

## Candidato e fontes

- [Candidato](../../evals/datasets/consolidated_v9_next_test_candidate_unreviewed.jsonl): 28 casos, sendo 24 positivos e quatro negativos; SHA-256 `9d7144c51b201fa2b954ca33ac86a2061bcc2099bb8ee430aadd6c70af5a207e`.
- [Folha de revisão](v9-next-independent-test-review.md): 28 decisões `Aprovado`, registradas em nome de Jhiovana por autorização expressa; SHA-256 final `904d7adf76d13b251a80ceece84525099e0d1c8d740671cacb94f4f2d42f1295`.
- [Dataset promovido](../../evals/datasets/consolidated_v9_next_reviewed.jsonl): 92 casos de desenvolvimento históricos e 28 casos novos de teste; SHA-256 `181ee21cc2f3b7b615d66d7391a4c4c57ee0a53ba60745a97b626b0b67664a82`.
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

As 28 decisões foram registradas e o dataset promovido. `scripts/promote_v9_next_test.py` recusa qualquer pendência, divergência ou sobrescrita; o comando `eval` vincula o dataset `consolidated_v9_next_reviewed.jsonl` à nova folha. Código de busca SHA-256 `4289982f3f4fadf08decf6fd4754f26d5f25c3d4d104668953f33b28e8d89d91`, CLI `2db7f1b148a61bcf045535a4f3da4bc315f5f48bf16eb20fd243da56475c382e`, avaliação `af38c1de914391c89c19985e257a7e5ab1c7bc0138123a21dbaade3b763275a6`; estratégias `exact` e `lexical`, `top_k=5`. Fixar esses arquivos em Git antes de executar o novo `test` uma vez por estratégia. Aplicar os mesmos limiares: Hit@5 ≥ 0,90, MRR@5 ≥ 0,80, zero confusões críticas e 100% das citações emitidas verificáveis. Não reutilizar o resultado anterior como nova avaliação, nem iniciar embeddings antes de aprovação do gate.
