# Dupla revisão técnica do candidato de teste v9

**Data:** 12/11/2026. **Escopo:** revisão independente, sem executar o recuperador nem o split `test`. Este parecer não substitui a aprovação humana de Jhiovana.

## Material e verificações

- Candidato: `evals/datasets/consolidated_v9_test_candidate_unreviewed.jsonl`, SHA-256 `c80c9db2fd168d2782fec7fa9c4c780471ae5507a25f8a66e47c85fa72e31d66`.
- Release: `data/releases/corpus-consolidado-v9-aprovado-2026-11-12`, manifesto SHA-256 `ea72d7705cccf7a14c359bd67d60807ce5e994ecd541810f1a6d066d33f01a84`.
- PDFs locais: F01 SHA-256 `a991dd0934774854dbe087a259a484c21fdf70ad2d27f4af5ba5a5c51a2a15bc`; F03 `299ff632a4e55d1dabbc953dc9c9e09f1cf6bbe2cabef8bf45fec5fbd5139fb6`; F04 `beb2cf59b835e94e2e016b009bd2b17f5d0375ab593db00f983211c2cfbc32b3`.
- São 28 casos: 24 positivos e quatro negativos. F01 tem 14, F03 tem dez, F04 tem quatro. Nenhuma família do candidato coincide com as famílias do dataset exploratório `dev`.
- As 29 referências dos 24 positivos existem em `evidencias.jsonl`, com ID, fonte, página, linha, medicamento, princípio ativo, concentração e forma coerentes com o candidato. Os nomes dos princípios ativos foram localizados nas respectivas páginas dos PDFs. Os casos apontados como problemáticos foram examinados também pelo texto das linhas dos PDFs.

## Segunda decisão por caso

| Casos | Parecer técnico | Verificação e ação |
|---|---|---|
| 001–005 | Aptos à revisão humana | Evidências e apresentações conferem com F01. |
| 006 | Rejeitar a redação | A fonte F01 p.126 repete o mesmo texto nas colunas de concentração e forma; a pergunta repete a frase literalmente e não é uma consulta útil. Substituir o caso ou redigir pergunta específica sem alterar a fonte aprovada. |
| 007–010 | Aptos à revisão humana | Evidências e apresentações conferem com F01. |
| 011–016 | Aptos à revisão humana | Evidências e apresentações conferem com F03; 012 possui duas linhas válidas. |
| 017 | Pendente de reformulação | F03 p.35, item 547, traz solução injetável de 250 a 300 mcg em frasco-ampola ou seringa. O `strength` do release também contém o recipiente, e a pergunta coloca a forma após ele. Ajustar a pergunta no candidato; uma alteração do release exigiria novo processo documental. |
| 018 | Pendente de reformulação | F03 p.53, item 957, traz solução de Ringer com lactato, injetável, em bolsa ou frasco de 500 mL. O `strength` representa volume/acondicionamento. Reescrever a pergunta em ordem natural e preservar a descrição literal da evidência. |
| 019–020 | Aptos à revisão humana | Evidências conferem com F03; 019 aponta corretamente cinco linhas distintas da mesma apresentação. |
| 021–024 | Aptos à revisão humana, com ajuste de exibição | As linhas existem em F04. O documento não informa forma farmacêutica; o `form: "-"` é marcador de ausência. Remover o hífen apenas da apresentação mostrada na folha, sem inferir uma forma. No 023, preferir a redação da fonte: `etinilestradiol 0,03mg + levonorgestrel 0,15mg`, para manter inequívoca a associação entre fármaco e dose. |
| 025–028 | Rejeitar as perguntas | Todos usam `99999 mg nesta apresentação?`, sem forma definida. Não são negativos representativos. Criar negativos plausíveis e explícitos, distribuídos entre F01, F03 e F04; validar a ausência de cada apresentação nos PDFs e no release antes de fixar `not_in_scope`. |

**Contagem corrigida do parecer anterior:** 21 casos tecnicamente aptos à revisão humana, dois pendentes (017–018) e cinco rejeitados (006, 025–028). Os quatro F04 estão entre os 21, com ressalva de apresentação exibida. Isso não representa 21 aprovações humanas.

## Decisão do gate

**Não congelar o candidato atual.** A fonte geradora concatena campos literalmente e cria negativos artificiais apenas em F01. Corrigir a especificação e o gerador, produzir uma nova versão identificável do candidato e revisar novamente os 28 casos com os PDFs. Preservar o candidato e a folha atuais como trilha de auditoria antes de qualquer regeneração, pois `scripts/prepare_v9_test_candidate.py` sobrescreve ambos. As sugestões de apresentações negativas do primeiro parecer não foram tomadas como gabarito: cada ausência precisa de verificação própria. Não executar `scripts/promote_v9_test.py` nem qualquer avaliação `test` até a aprovação humana integral da nova versão.
