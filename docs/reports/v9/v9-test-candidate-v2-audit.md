# Auditoria do candidato independente v9 — versão 2

**Data:** 12/11/2026. **Estado:** candidato não avaliado; a revisão humana posterior aprovou os 28 casos e o dataset foi congelado. O v1 e sua folha foram preservados sem alterações.

## Correções

O gerador agora escreve `consolidated_v9_test_candidate_v2_unreviewed.jsonl` e `v9-independent-test-review-v2.md`, recusando sobrescrever qualquer um deles. Reformulou as perguntas 006, 017 e 018 para remover repetição e ordem invertida, e 023 para associar cada dose ao princípio ativo correto. A apresentação exibida na folha foi ajustada nesses casos e nos F04 sem forma declarada; os campos e IDs do release aprovado permanecem literais no JSONL. Os 24 positivos conservam suas 29 evidências.

## Verificação de ausência dos negativos

Os PDFs locais foram identificados por SHA-256: F01 `a991dd0934774854dbe087a259a484c21fdf70ad2d27f4af5ba5a5c51a2a15bc`, F03 `299ff632a4e55d1dabbc953dc9c9e09f1cf6bbe2cabef8bf45fec5fbd5139fb6` e F04 `beb2cf59b835e94e2e016b009bd2b17f5d0375ab593db00f983211c2cfbc32b3`. Foi pesquisado o texto extraído de **todas as páginas** de cada PDF, inspecionadas todas as ocorrências do princípio ativo na fonte pertinente e comparado o catálogo do release para a combinação fonte, princípio ativo, concentração e forma. A ausência refere-se à fonte perguntada, não à existência comercial do produto.

| ID | Fonte e pergunta negativa | Apresentações encontradas na fonte | Resultado |
|---|---|---|---|
| 025 | F01: cloridrato de amitriptilina 50 mg comprimido | 25 mg e 75 mg comprimido; PDF pp.102 e 140 | 50 mg comprimido ausente no PDF e no catálogo F01. |
| 026 | F03: abacavir 30 mg/mL solução oral | 20 mg/mL solução oral e 300 mg comprimido; PDF pp.12 e 68 | 30 mg/mL solução oral ausente no PDF e no catálogo F03. |
| 027 | F03: carbamazepina 200 mg/5 mL suspensão oral | 100 mg/5 mL suspensão oral e 200 mg comprimido; PDF p.19 | 200 mg/5 mL suspensão oral ausente no PDF e no catálogo F03. |
| 028 | F04: losartana potássica 100mg | 50mg; PDF p.1 | 100mg ausente no PDF e no catálogo F04. F04 não declara forma farmacêutica, por isso ela não foi inventada na pergunta. |

Os quatro negativos são plausíveis e cobrem as três fontes: um F01, dois F03 e um F04. Essa conferência técnica deve ser repetida pelo revisor humano na folha v2. Nenhum recuperador foi consultado para escolher ou ajustar os casos.

## Integridade e gate

O v2 tem 28 casos, 24 positivos e quatro negativos, e nenhuma família compartilhada com o `dev`. SHA-256 do candidato v2: `0ca276409cd9e46da4665d74513de065cdf7bfb1fc0374070334f591d1970c28`. SHA-256 da folha v2 inicial: `fa27b9ad62be40583925d13d6f0f0941444705c9ddfd7df3e369027859e1a81a`; após as decisões de Jhiovana: `96d523fd3d16832fc539351a530daee0e7b4fb5915207372701002b190459275`. O dataset congelado tem SHA-256 `d66412357e72c7df3fb6975c34773613b8356ff11da67ee114995bd382873b28`. O split `test` ainda não foi executado.
