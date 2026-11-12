# Validação exploratória da recuperação exata e lexical — v7

**Estado em 11/11/2026:** diagnóstico `dev` concluído. Jhiovana registrou a revisão humana dos 119 casos na planilha: 118 aprovações e uma rejeição (`C-F03-003`). O validador confirmou as 119 decisões, nome e data, sem alterações nas colunas de referência; retornou apenas a rejeição ainda não corrigida. `test` oficial e gate de embeddings permanecem fechados.

## Entrada fixada

- Release: `corpus-consolidado-v7-aprovado-2026-11-11`; fingerprint do manifesto `8399f37f6664f474c18622d912ad9795f04ec199102724cfafbe6e295eeab20b`; fingerprint de conteúdo `9ad9a3a7f50dc69005daba390bc2b07fb3710f4e54216faf0dca5cb8b346e327`.
- Chunks: 2.114, um por evidência; SHA-256 `4ff2718d023c81d3b8d991bebc20e4eb68df2bf779ad07fac6bb3147ce855d61`; receita `one-evidence-v1`. O carregador recalcula cada chunk a partir da evidência e rejeita diferenças de conteúdo, ID, fonte e página.
- DVC: release e chunks têm ponteiros separados. Jhiovana confirmou `dvc push` e `dvc status -c` com cache e remoto sincronizados após a inclusão dos chunks. Os ponteiros e o código ainda precisam ser registrados em uma revisão Git compartilhável.
- Dataset técnico v7: 119 perguntas sintéticas, 91 `dev` e 28 `test`; SHA-256 `1419f6bd616e5130765fa444a935ef104d24b1aa2e3920640469292c214b1bde`. Nenhuma foi marcada como revisada por Jhiovana. O caso `C-F04-023` teve a referência corrigida: a pergunta pede metformina de ação prolongada, mas o gabarito v6 apontava a ocorrência sem essa característica. Todas as referências v7 existem no release e têm fonte/página registradas.

## Defeito encontrado na linha de base anterior

O avaliador consolidado usava `Path.read_text()` sem `encoding="utf-8"`. No Windows, isso leu o JSONL UTF-8 como codificação local e corrompeu acentos das perguntas. Com a mesma pergunta e o mesmo release v7, a execução antiga deu Hit@5 `0,4605` e status `0,5495`; após leitura UTF-8 explícita, antes da correção do caso `C-F04-023`, deu Hit@5 `0,9868` e status `1,0`. Assim, os números v6 publicados anteriormente **não são uma medida confiável da qualidade da busca** e precisam de errata se forem citados. A diferença não demonstra melhoria do algoritmo lexical; demonstra correção do avaliador.

## Resultado dev após migração

| Estratégia | Casos | Positivos | Hit@1/3/5 | MRR@5 | Status | Apresentação | Confusões críticas | Citações válidas | p95 busca |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Exata | 91 | 76 | 1,0000 | 1,0000 | 1,0000 | 1,0000 | 0 | 78/78 | 218 ms |
| Lexical | 91 | 76 | 1,0000 | 1,0000 | 1,0000 | 1,0000 | 0 | 78/78 | 244 ms |

F01: 29/29 positivos com Hit@5; F03: 20/20; F04: 27/27. Dos 15 casos não positivos em `dev`, todos tiveram o status esperado. Os arquivos [exata](../../../evals/results/consolidated_v7_exact_dev_exploratory.json) e [lexical](../../../evals/results/consolidated_v7_lexical_dev_exploratory.json) contêm o resultado por pergunta, candidatos documentais, IDs ranqueados, motivo de abstenção, citações e tempo. O commit Git registrado estava com alterações locais; por isso o hash do código precisa ser congelado quando o gate for fechado.

Exata e lexical têm a mesma pontuação porque 70 casos retornaram apenas um chunk candidato e 20 não chegaram ao ranking. Um caso teve três chunks candidatos (`C-F03-001`): a ordem da segunda e terceira evidências diferiu, mas a referência correta ficou em primeiro nas duas estratégias. O modo `exact` agora ordena deterministicamente por fonte, página e ID; o lexical usa BM25 dentro das apresentações permitidas.

Essas perguntas foram geradas majoritariamente com a grafia literal do catálogo. O desempenho perfeito nesse recorte **não comprova** o mesmo resultado para perguntas espontâneas, erros de digitação ou outras formas de descrever medicamentos. Os testes de regressão incluem diferenças de unidade, forma, liberação e fonte; a revisão humana da planilha deve examinar também a representatividade das perguntas.

Verificação local: `pytest -q --basetemp .test-tmp-v7-full` concluiu com **272 testes aprovados**; Ruff e `git diff --check` passaram para os arquivos alterados nesta etapa. A validação de citação acima confere o vínculo estruturado entre resultado, evidência, fonte e página do release; não substitui nova leitura humana de cada PDF.

## Revisão e gate

Na [planilha](v7-retrieval-review.xlsx), Codex conferiu os 119 casos contra as evidências, ocorrências, fonte e página do release, além do texto extraído dos PDFs para os casos com diferenças de grafia ou espaçamento. O caso **`C-F03-003` foi rejeitado**: a pergunta e o campo `strength` do release dizem “500 mg a 600 mg cálcio elementar”, mas a REME-DF 2026, p. 19, linha 194, diz “equivalente a 500 **ou** 600 mg de cálcio”. A redação como intervalo não reproduz a alternativa declarada na fonte. Corrigir o corpus em um novo release/fingerprint e a pergunta/gabarito correspondente; não alterar a v7 aprovada silenciosamente. As outras 118 decisões são aprovações técnicas, incluindo os casos de ambiguidade que exigem apresentar as opções documentadas, sem escolher uma.

Jhiovana registrou `reviewer=Jhiovana` e a data `2026-11-11` nas 119 linhas, mantendo `C-F03-003` rejeitado. O validador deve continuar recusando a emissão do conjunto `reviewed` enquanto essa divergência não for corrigida em novo release e gabarito. Após a correção, emitir nova planilha e registrar a decisão humana para o caso corrigido antes de abrir o `test`.

```powershell
.venv\Scripts\python.exe scripts/validate_v7_retrieval_review.py --review docs/reports/v7-retrieval-review.xlsx --output evals/datasets/consolidated_v7_reviewed.jsonl
```

O validador só produz o conjunto `reviewed` quando todas as 119 linhas estão aprovadas, com identidade da revisora, data e campos de referência preservados. O comando `app.py eval --split test` rejeita o conjunto técnico. Após revisão, congelar código/parâmetros/gabarito, executar `test` uma vez para cada estratégia e aplicar o gate: Hit@5 ≥ 0,90; MRR@5 ≥ 0,80; zero confusões críticas; 100% das citações verificáveis. Resultado abaixo do limite mantém embeddings bloqueados.
