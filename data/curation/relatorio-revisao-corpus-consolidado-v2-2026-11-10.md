# Relatório de Revisão Técnica e de Domínio — Release `corpus-consolidado-v2-revisao-2026-11-10`

- **Data da revisão**: `2026-11-10`
- **Release auditado (preservado sem edições)**: `data/releases/corpus-consolidado-v2-revisao-2026-11-10/`
- **Novo release regenerado após curadoria na origem**: `data/releases/corpus-consolidado-v3-revisao-2026-11-10/`
- **Relatório estruturado completo (JSON)**: `data/curation/relatorio-revisao-corpus-consolidado-v2-2026-11-10.json`
- **Fontes oficiais conferidas**:
  - `F01` — RENAME 2024 2ª edição (`data/raw/F01-rename/rename-2024-2ed.pdf`, SHA-256 `49ce46d22cccf3eb7fe2dc3bffc1be4efcdb0ec3dde0bbabbd7ba4fbef6cb0c7`, 243 páginas)
  - `F03` — REME-DF 2026-10-29 (`data/raw/F03-reme-df/reme-df-2026-10-29.pdf`, SHA-256 `1fc52c6ebdc8aa05bd7ea2a840ab6fc64becc8426e9edef4fd07bf72cc5e7588`, 58 páginas)
  - `F04` — Farmácia Popular Elenco 2026-08-31 (`data/raw/F04-farmacia-popular/farmacia-popular-elenco-2026-08-31.pdf`, SHA-256 `15de9dc22ebbd00ad14fefcd1ab0fd48b78ea80e62dbfd700fb94de0a42a1293`, 1 página)
- **Restrição respeitada**: `data/corpus/chunks.jsonl` **não** foi utilizado como evidência e **nenhum** chunk ou embedding foi gerado.

---

## 1. Resumo Executivo e Conclusão

| Critério | Release `v2` (`corpus-consolidado-v2-revisao-2026-11-10`) | Release `v3` (`corpus-consolidado-v3-revisao-2026-11-10`) |
|---|---|---|
| **Integridade técnica (`--verify`)** | Aprovado (`0` divergências de hash/vínculo) | Aprovado (`0` divergências de hash/vínculo) |
| **`catalog.jsonl` (registros)** | `1.885` (`sha256: 0387598d...0a5`) | `1.888` (`sha256: 77dc5ee4...ecb`) |
| **`occurrences.jsonl` (registros)** | `2.115` (`sha256: b2c449f7...56e`) | `2.115` (`sha256: 7eec35c0...7cf`) |
| **`evidencias.jsonl` (registros)** | `2.115` (`sha256: fc91589f...188`) | `2.115` (`sha256: 18730715...398`) |
| **`review-log.jsonl` (entradas)** | `283` (`COR-006`..`COR-288`, faltando `COR-001`..`005`) | `450` (`COR-001`..`COR-450`, sequência íntegra) |
| **Formas inferidas/padronizadas fora da página** | `191` ocorrências (`F03`: `150`, `F04`: `41`) | `0` ocorrências (`form_literal_in_page`: `2115/2115`) |
| **Ocorrências corrigidas (`v2` → `v3`)** | `261` ocorrências com divergência (`214` Alta, `47` Média) | `0` divergências estruturais pendentes |
| **Status no `release.json`** | `pending_review` | `pending_review` |
| **Conclusão da auditoria** | **Não aprovável no estado original (`v2`) / aprovável após correções** | **Aprovável tecnicamente; aguarda sign-off humano de domínio para mudar para `approved`** |

### Decisão Fundamentada
1. **Sobre o release `corpus-consolidado-v2-revisao-2026-11-10` (`v2`)**: **Aprovável após correções** (isto é, **não aprovável** no estado original `v2` para uso direto como fonte de recuperação). Apesar de passar na validação criptográfica e referencial (`publish_consolidated_release.py --verify`), o `v2` contém **261 ocorrências/evidências com divergências de domínio e fidelidade documental** (**214 de gravidade Alta** e **47 de gravidade Média**), incluindo:
   - **41 ocorrências em `F04`** com forma farmacêutica inferida sem respaldo no PDF oficial da Farmácia Popular (inclusive atribuindo `comprimido de liberação prolongada` ao `succinato de metoprolol 25 mg` na linha 24 sem declaração na fonte);
   - **26 ocorrências em `F03`** com vazamento de forma farmacêutica ou truncamento em `active_ingredient` (ex.: `permetrina loçao topica` classificada como `solução injetável`; `produto de cannabis (canabidiol` e `sulfato ferroso (equivalente a` truncados no meio do parêntese);
   - **15 ocorrências em `F03`** com concentração ou forma inventada/divergente da célula `DESCRIÇÃO` (ex.: fórmulas metabólicas para fenilcetonúria nas linhas 481–483 com `lata 400 g a 500 g` e `pó para suspensão oral` ausentes do PDF; `insulina análoga de ação prolongada carpule 3mL` na linha 560 com `100 UI/mL` não declarado no PDF; `gosserrelina 3,6 mg` na linha 515 com `solução injetável` em vez de `implante subcutâneo`);
   - **129 ocorrências em `F03`** com forma farmacêutica truncada pela regex (ex.: `solução para inalação` → `solução`, `comprimido vaginal`/`sublingual`/`dispersível`/`mastigável` → `comprimido`, `suspensão oftálmica`/`nasal` → `suspensão`);
   - **7 ocorrências em `F01`** com asterisco de nota de rodapé (`*`) acoplado a `active_ingredient`/`strength` (`clofazimina *`, `dapsona *`, `rifampicina *`);
   - **71 ocorrências (`36` em `F01` e `35` em `F03`)** com característica de liberação explícita no PDF (`liberação prolongada`, `liberação controlada`, `liberação retardada`, `ação prolongada`), mas com `release_characteristic: null` em `v2`.
2. **Sobre o novo release `corpus-consolidado-v3-revisao-2026-11-10` (`v3`)**: Todas as **261 ocorrências** foram corrigidas na origem pelo fluxo oficial (`scripts/consolidate_corpus.py` → `scripts/validate_consolidated_corpus.py` → `scripts/publish_consolidated_release.py`), mantendo `v2` intacto. Conforme a regra 8 do procedimento, `review_status: approved` nas ocorrências consolidadas **não** aprova automaticamente o release de recuperação, e a promoção de `status` para `approved` exige sign-off de pessoa habilitada (farmacêutico/clínico) sobre as ressalvas estruturais documentadas na Seção 6. Por isso, o `v3` permanece em `status: "pending_review"`.

---

## 2. Procedimentos 1 e 2 — Verificação Técnica Automatizada (`v2` e `v3`)

### 2.1 Execução do Verificador Oficial (`scripts/publish_consolidated_release.py --verify`)
- `python3 scripts/publish_consolidated_release.py --verify data/releases/corpus-consolidado-v2-revisao-2026-11-10` → **OK (exit code 0)**.
- `python3 scripts/publish_consolidated_release.py --verify data/releases/corpus-consolidado-v3-revisao-2026-11-10` → **OK (exit code 0)**.

| Arquivo | Registros (`v2`) | SHA-256 (`v2`) | Registros (`v3`) | SHA-256 (`v3`) |
|---|---:|---|---:|---|
| `catalog.jsonl` | 1.885 | `0387598d5865acde728e6bc27726c02bd841f1d3222dfd5a6f0195706bf140a5` | 1.888 | `77dc5ee4ca9d85707254e5e312a676bacfb9f00a63473dee974f2ec841189ecb` |
| `occurrences.jsonl` | 2.115 | `b2c449f74b6e3e8d2052ad91257fd9ef2ad7286fc7f1ecca1a76c5724f74756e` | 2.115 | `7eec35c02b696045f85c9e2dac54c94be44805d05f5e7f075b5d9a4c93eeb7cf` |
| `evidencias.jsonl` | 2.115 | `fc91589fe8792cf18743671fa09b18a4de4b9948e987f8af6dd5ec13706e0188` | 2.115 | `18730715e689fe92494e5395786af4c909708de8be7b57ed67be045e0ab6e398` |
| `quality_report.json` | — | `9d1e819042a87f4c345958fb569c1c9ff8c4c0f51c7c1d5a1d161d0b5a6dee56` | — | `df6a289e695680db3ed8c1bb9e96e3322a12227ef08ff8c44e4f9bcf162c0097` |

> **Por que `catalog.jsonl` passou de 1.885 (`v2`) para 1.888 (`v3`)?**
> A chave de deduplicação do catálogo é `(item_type, active_ingredient, strength, form, release_characteristic)`. Ao remover as formas inferidas em `F04` (`form: "-"`) e corrigir formas/concentrações em `F03`, as apresentações de `F04` deixaram de colapsar indevidamente com apresentações de `F01`/`F03` que possuíam forma explícita, resultando em 1.888 entradas únicas legítimas.

### 2.2 Checagens Automatizadas sobre as 2.115 Evidências
1. **Unicidade dos IDs**: `2.115` `evidence_id` únicos (`evidence-<24-hex>`) e `2.115` `occurrence_id` únicos (`occ-<24-hex>`), com correspondência bijetiva `1:1` (`0` duplicatas, `0` órfãos).
2. **Vínculo com ocorrência e apresentação (`catalog.jsonl`)**:
   - `2.113` evidências com `item_type: "medicine"` possuem `medicine_id` (`med-<24-hex>`) existente em `catalog.jsonl` e com os mesmos valores de `(active_ingredient, strength, form, release_characteristic)`.
   - `2` evidências com `item_type: "supply"` (`occ-8b27e582e2c9bd191869b342` — `absorvente higiênico`, e `occ-5ea8a977695dbad521b67f97` — `fralda geriátrica`, ambas em `F04`) possuem `medicine_id: null` por desenho do esquema.
3. **Igualdade `text == raw_text`**: Em todas as `2.115/2.115` evidências, `evidencia["text"] == occurrence["raw_text"]` (`0` divergências).
4. **Fonte, versão, hash e página**: Todas as `2.115` evidências conferem exatamente com `data/manifests/coleta-inicial-pdfs-2026-11-03.json`:
   - `F01`: `996` ocorrências, páginas `39..201` (dentro de `1..243`), versão `2024-2ed`.
   - `F03`: `1.078` ocorrências (`source_row_number` `1..1078` sem lacunas), páginas `11..58` (dentro de `1..58`), versão `2026-10-29`.
   - `F04`: `41` ocorrências (`source_row_number` `2..42`), página `1` (dentro de `1..1`), versão `2026-08-31`.
5. **Campos obrigatórios vazios**: `0` campos obrigatórios vazios/nulos em `F01`, `F03` e `F04` (usando `"-"` quando a fonte oficial omite concentração ou forma farmacêutica).
6. **Tipo `medicine` vs `supply`**:
   - Em `F04`, os 39 medicamentos estão como `medicine` e os 2 insumos (`absorvente higiênico` e `fralda geriátrica`) estão como `supply`.
   - **Ressalva de modelagem em `F01` (Baixa)**: existem **27 ocorrências** em `F01` (páginas 111–133, Anexo B/C — `Insumos (Básico)` e `Insumos (Estratégico)`, ex.: `agulha descartável para caneta aplicadora de insulina`, `lanceta para punção digital`, `tira reagente`, `preservativo masculino/feminino`, `diafragma`, `sistema intrauterino liberador de levonorgestrel`) classificadas com `item_type: "medicine"` e incluídas em `catalog.jsonl`. Como o texto e o componente (`context.component: "Insumos (Básico)"`) já identificam que são insumos, isso foi mantido como ressalva para não quebrar contratos de catálogo, devendo ser considerado pelos filtros do consumidor.

---

## 3. Procedimento 3 — Conferência contra os PDFs Originais (Cobertura Real)

Em cumprimento estrito à diretriz de **não apresentar amostragem como revisão integral**, a conferência contra os PDFs originais foi dividida em dois conjuntos disjuntos:

### 3.1 Conjunto de Revisão Integral: **469 ocorrências (22,17% de 2.115)**
- **Distribuição por fonte**: `F01`: **143** | `F03`: **285** | `F04`: **41**.
- **Critério de inclusão (100% revisado linha a linha contra os PDFs)**:
  1. **100% das 41 ocorrências da `F04`** (linhas `2..42`, página 1);
  2. **100% dos 283 registros do `review-log.jsonl` do `v2`** (mais os 5 registros históricos `COR-001`..`COR-005` restaurados e os 162 novos registros `COR-289`..`COR-450` adicionados no `v3`, totalizando **450 entradas** em `data/corpus/review-log.jsonl`);
  3. **100% dos casos com associações medicamentosas (`+`)**: `166` ocorrências (`F01`: 86, `F03`: 73, `F04`: 7);
  4. **100% dos casos com concentrações compostas (`+`)**: `158` ocorrências;
  5. **100% dos casos com característica de liberação (`prolongada`, `controlada`, `retardada`, `ação prolongada`)**: `73` ocorrências inspecionadas (`72` com liberação literal nos PDFs: `F01`: 36, `F03`: 35, `F04`: 1, mais 1 inferência indevida removida em `F04` row 24);
  6. **100% dos casos com texto padronizado, inferido, insumos ou linha em branco**: incluindo todas as 150 formas padronizadas de `F03`, 41 formas inferidas de `F04`, a linha 987 em branco de `F03` e as 7 notas de rodapé `*` de `F01`.

### 3.2 Conjunto de Amostragem Estratificada: **371 ocorrências de 1.646 elegíveis (22,54% do pool simples)**
- **Pool elegível para amostragem**: as **1.646 ocorrências simples restantes** (`F01`: `853`, `F03`: `793`; `F04`: `0`, pois `F04` foi 100% revisada integralmente).
- **Critério de seleção determinístico (reprodutível via `SHA-256` com semente `'revisao-2026-11-10-v2'`)**:
  1. **Estratificação por `(source_id, page)`**: seleção de pelo menos 2 ocorrências por página de `F01` (cobrindo **todas as 107 páginas de tabela** com itens simples) e pelo menos 2 ocorrências por página de `F03` (cobrindo **todas as 48 páginas de tabela** `11..58`);
  2. **Estratificação complementar por `(source_id, form)`**: garantia de pelo menos 3 ocorrências (ou 100% do estrato, quando `< 3`) para cada forma farmacêutica distinta em cada fonte.
- **Tamanho final da amostra estratificada**: **371 ocorrências** (`F01`: **259** de 853 = `30,36%`; `F03`: **112** de 793 = `14,12%`).
- **Resultado na amostra estratificada de ocorrências simples**: **0 divergências** (`371/371` bateram 100% com o texto literal das células dos PDFs `F01` e `F03`).
- **Cobertura combinada de inspeção direta contra o PDF**: **840 ocorrências (`469 + 371`, equivalente a `39,72%` do corpus total)**, complementada por verificação automatizada de célula/página em **100% (`2.115/2.115`)** dos registros.
  - A lista integral dos **371 IDs sorteados** encontra-se em `data/curation/relatorio-revisao-corpus-consolidado-v2-2026-11-10.json` no campo `coverage.stratified_sample_ids`.

### 3.3 Revisão Integral das 41 Ocorrências da `F04` (Farmácia Popular, Página 1)

No PDF oficial `data/raw/F04-farmacia-popular/farmacia-popular-elenco-2026-08-31.pdf`, a tabela possui apenas duas colunas: **`Indicação`** e **`Princípio Ativo/Insumos`**. Nenhuma linha declara forma farmacêutica. No release `v2`, todas as 41 ocorrências continham formas inferidas externas ao PDF (incluindo `comprimido de liberação prolongada` na linha 24). No release `v3`, todas as 41 ocorrências tiveram `form` corrigido para `"-"` (e `release_characteristic: null` na linha 24):

| Linha | `occurrence_id` / `evidence_id` | Indicação (`context.indication`) | `active_ingredient` | `strength` | `form` (`v2` → `v3`) | `release_characteristic` (`v2` → `v3`) | Indicação no `text` da evidência? |
|---:|---|---|---|---|---|---|---|
| 2 | `occ-3ce4fe73119367200f984907` |  | `brometo de ipratrópio` | `0,02mg` | `solução para inalação oral (aerossol)` → `-` | `null` → `null` | **Não** (apenas em `occurrences.jsonl`) |
| 3 | `occ-44ea3122ec626ffeefc2a019` |  | `brometo de ipratrópio` | `0,25mg` | `solução para inalação (gotas)` → `-` | `null` → `null` | **Não** (apenas em `occurrences.jsonl`) |
| 4 | `occ-66c51d341c410cacdbd244a4` |  | `dipropionato de beclometasona` | `200mcg` | `solução aerossol para inalação oral` → `-` | `null` → `null` | **Não** (apenas em `occurrences.jsonl`) |
| 5 | `occ-8616bec3a9ce97b885f68018` |  | `dipropionato de beclometasona` | `250mcg` | `solução aerossol para inalação oral` → `-` | `null` → `null` | **Não** (apenas em `occurrences.jsonl`) |
| 6 | `occ-882d2f438c02eeca23e676cb` |  | `dipropionato de beclometasona` | `50mcg` | `solução aerossol para inalação oral` → `-` | `null` → `null` | **Não** (apenas em `occurrences.jsonl`) |
| 7 | `occ-e139cbd09a39d7da5be06493` |  | `sulfato de salbutamol` | `100mcg` | `solução aerossol para inalação oral` → `-` | `null` → `null` | **Não** (apenas em `occurrences.jsonl`) |
| 8 | `occ-09b3c17ea49c6c8ae67c2e4d` |  | `sulfato de salbutamol` | `5mg` | `solução para inalação (gotas)` → `-` | `null` → `null` | **Não** (apenas em `occurrences.jsonl`) |
| 9 | `occ-edf8dd6f5a636935088dddea` |  | `cloridrato de metformina` | `500mg` | `comprimido` → `-` | `null` → `null` | **Não** (apenas em `occurrences.jsonl`) |
| 10 | `occ-48e616ae9f8df7c435126c21` |  | `cloridrato de metformina` | `500mg` | `comprimido de liberação prolongada` → `-` | `ação prolongada` → `ação prolongada` | **Não** (apenas em `occurrences.jsonl`) |
| 11 | `occ-5cad8bf5fd4bf3b66565f60b` |  | `cloridrato de metformina` | `850mg` | `comprimido` → `-` | `null` → `null` | **Não** (apenas em `occurrences.jsonl`) |
| 12 | `occ-1720c0bddc635262a2c3f640` |  | `glibenclamida` | `5mg` | `comprimido` → `-` | `null` → `null` | **Não** (apenas em `occurrences.jsonl`) |
| 13 | `occ-8ddfd9df9529d696a2612e89` |  | `insulina humana regular` | `100ui/ml` | `solução injetável` → `-` | `null` → `null` | **Não** (apenas em `occurrences.jsonl`) |
| 14 | `occ-e0fa1e053b0a724181075489` |  | `insulina humana` | `100ui/ml` | `suspensão injetável` → `-` | `null` → `null` | **Não** (apenas em `occurrences.jsonl`) |
| 15 | `occ-4eb20de2a64dfed2e8279acc` |  | `atenolol` | `25mg` | `comprimido` → `-` | `null` → `null` | **Não** (apenas em `occurrences.jsonl`) |
| 16 | `occ-72612f92a939518de17baaa1` |  | `besilato de anlodipino` | `5 mg` | `comprimido` → `-` | `null` → `null` | **Não** (apenas em `occurrences.jsonl`) |
| 17 | `occ-7ed9e237bf18ba04361a3576` |  | `captopril` | `25mg` | `comprimido` → `-` | `null` → `null` | **Não** (apenas em `occurrences.jsonl`) |
| 18 | `occ-8c6afb38cd237a6b4345229c` |  | `cloridrato de propranolol` | `40mg` | `comprimido` → `-` | `null` → `null` | **Não** (apenas em `occurrences.jsonl`) |
| 19 | `occ-55ae1ce56b51b27f32022210` |  | `hidroclorotiazida` | `25mg` | `comprimido` → `-` | `null` → `null` | **Não** (apenas em `occurrences.jsonl`) |
| 20 | `occ-81076ce93e4163086259ef8e` |  | `losartana potássica` | `50mg` | `comprimido` → `-` | `null` → `null` | **Não** (apenas em `occurrences.jsonl`) |
| 21 | `occ-fbcf0015aa8813b069bae2ca` |  | `maleato de enalapril` | `10mg` | `comprimido` → `-` | `null` → `null` | **Não** (apenas em `occurrences.jsonl`) |
| 22 | `occ-b768885458b54f9771fd68e1` |  | `espironolactona` | `25 mg` | `comprimido` → `-` | `null` → `null` | **Não** (apenas em `occurrences.jsonl`) |
| 23 | `occ-c71ac9beefacd5021280b7f8` |  | `furosemida` | `40 mg` | `comprimido` → `-` | `null` → `null` | **Não** (apenas em `occurrences.jsonl`) |
| 24 | `occ-e597b6780d28aa62255f6eec` |  | `succinato de metoprolol` | `25 mg` | `comprimido de liberação prolongada` → `-` | `null` → `null` | **Não** (apenas em `occurrences.jsonl`) |
| 25 | `occ-3e3fc3f2db17a9c68344f2c9` |  | `acetato de medroxiprogesterona` | `150mg` | `suspensão injetável` → `-` | `null` → `null` | **Não** (apenas em `occurrences.jsonl`) |
| 26 | `occ-bd645fca4e10b51f38485f06` |  | `etinilestradiol + levonorgestrel` | `0,03mg + 0,15mg` | `comprimido` → `-` | `null` → `null` | **Não** (apenas em `occurrences.jsonl`) |
| 27 | `occ-1eaef6352086caff666c4e10` |  | `noretisterona` | `0,35mg` | `comprimido` → `-` | `null` → `null` | **Não** (apenas em `occurrences.jsonl`) |
| 28 | `occ-2e237469ad52f38dc54b786e` |  | `valerato de estradiol + enantato de noretisterona` | `5mg + 50mg` | `solução injetável` → `-` | `null` → `null` | **Não** (apenas em `occurrences.jsonl`) |
| 29 | `occ-1d42c31c79d6a6fa09551952` |  | `alendronato de sódio` | `70mg` | `comprimido` → `-` | `null` → `null` | **Não** (apenas em `occurrences.jsonl`) |
| 30 | `occ-11dd751548d5ceaf859d9a75` |  | `sinvastatina` | `10mg` | `comprimido` → `-` | `null` → `null` | **Não** (apenas em `occurrences.jsonl`) |
| 31 | `occ-15d35da6f8e395b14d97041e` |  | `sinvastatina` | `20mg` | `comprimido` → `-` | `null` → `null` | **Não** (apenas em `occurrences.jsonl`) |
| 32 | `occ-1e13d576f93f33e19c79b9e2` |  | `sinvastatina` | `40mg` | `comprimido` → `-` | `null` → `null` | **Não** (apenas em `occurrences.jsonl`) |
| 33 | `occ-31f830e7fbb52c0353da2946` |  | `carbidopa + levodopa` | `25mg + 250mg` | `comprimido` → `-` | `null` → `null` | **Não** (apenas em `occurrences.jsonl`) |
| 34 | `occ-e7d83368e51a7cb974fd6bd9` |  | `cloridrato de benserazida + levodopa` | `25mg + 100mg` | `comprimido ou cápsula` → `-` | `null` → `null` | **Não** (apenas em `occurrences.jsonl`) |
| 35 | `occ-57c2830deb65187a5743c1b3` |  | `maleato de timolol` | `2,5mg` | `solução oftálmica` → `-` | `null` → `null` | **Não** (apenas em `occurrences.jsonl`) |
| 36 | `occ-49b4ce4a23cd3e4e01bf68f5` |  | `maleato de timolol` | `5mg` | `solução oftálmica` → `-` | `null` → `null` | **Não** (apenas em `occurrences.jsonl`) |
| 37 | `occ-4dbafe42e6cc0c7058ecc60a` |  | `budesonida` | `32mcg` | `suspensão para inalação nasal` → `-` | `null` → `null` | **Não** (apenas em `occurrences.jsonl`) |
| 38 | `occ-03bb26a358e97b57f4fd899d` |  | `budesonida` | `50mcg` | `suspensão para inalação nasal` → `-` | `null` → `null` | **Não** (apenas em `occurrences.jsonl`) |
| 39 | `occ-dc03277c309dbb980fe781ca` |  | `dipropionato de beclometasona` | `50mcg/dose` | `suspensão para inalação nasal` → `-` | `null` → `null` | **Não** (apenas em `occurrences.jsonl`) |
| 40 | `occ-7f063f17f3885eb3cdc24d3f` |  | `dapagliflozina` | `10 mg` | `comprimido` → `-` | `null` → `null` | **Não** (apenas em `occurrences.jsonl`) |
| 41 | `occ-8b27e582e2c9bd191869b342` |  | `absorvente higiênico` | `-` | `unidade` → `-` | `null` → `null` | **Não** (apenas em `occurrences.jsonl`) |
| 42 | `occ-5ea8a977695dbad521b67f97` |  | `fralda geriátrica` | `-` | `unidade` → `-` | `null` → `null` | **Não** (apenas em `occurrences.jsonl`) |

---

## 4. Procedimento 4 — Sustentação Declarativa das Evidências e Análise de Domínio

Cada uma das 2.115 evidências foi avaliada quanto ao risco de sustentar afirmações além do declarado pela fonte oficial:

1. **Afirmações de estoque / disponibilidade física**:
   - Nenhuma evidência declara disponibilidade de estoque em tempo real (`stock_status` não faz parte das evidências do corpus consolidado).
   - **Atenção para consumidores de busca (`F03`, páginas 28, 30, 31, 41, 43, 52)**: 9 itens da REME-DF trazem a expressão administrativa `Unidade de estoque/licitação` na coluna `DESCRIÇÃO` (`occ-4ba6decfddcfcaafcaaa0c6b`, `occ-94ba3be4ffac0ab6dc698395`, `occ-4a762467c4414fc8e6f71b83`, `occ-df34625df60855f39e8d3fb1`, `occ-84323f35852e81ef925884fc`, `occ-e60d1cbef19dcdd5d790cf37`, `occ-3526ff2c0b6030363f9e5361`, `occ-d59fa1c60e49b1eb0fd0f242`, `occ-6107d026901b9534bfdd69cf`). Isso descreve apenas a unidade de medida licitatória (ex.: `g`, `mL`, `UI`), **não** estoque disponível.
2. **Afirmações de elegibilidade clínica / indicação**:
   - **`F04` (lacuna de contexto em `evidencias.jsonl`)**: em `37` das `41` evidências da Farmácia Popular, o campo `text` (`raw_text`) contém apenas a célula da direita (`Princípio Ativo/Insumos`, ex.: `"alendronato de sódio 70mg"` na linha 29 tem `"OSTEOPOROSE alendronato de sódio 70mg"`, mas `"atenolol 25mg"` na linha 13 não traz `"HIPERTENSÃO"` no `text`). A indicação oficial está preservada em `occurrences.jsonl` (`context.indication`), mas **não** no objeto de `evidencias.jsonl`. Recomendação: ao indexar `evidencias.jsonl`, enriquecer o payload com `context.indication` de `occurrences.jsonl`.
   - **`F03` (restrições clínicas literais na coluna `DESCRIÇÃO`)**: 11 itens de `F03` trazem restrição de programa/doença na própria descrição (ex.: `- tuberculose`, `- hanseníase`, `- toxoplasmose`, `- coqueluche`, `- influenza`, `- infecções oportunistas relacionadas ao HIV`, `- maternidade`). Esses qualificadores são literais do PDF oficial e estão preservados em `raw_text`.
3. **Dispensação em unidade específica (`FARMÁCIA` em `F03`) e intercalação multicoluna no `raw_text`**:
   - Em `F03`, a extração geométrica (`reme_rows` em `src/rag/table_extract.py`) recorta a faixa horizontal completa da linha (`x=36..562`), que abrange `ITEM`, `CÓDIGO`, `DESCRIÇÃO`, `GRUPO FARMACOLÓGICO` e `FARMÁCIA` (`AB`, `CE`, `H`, `amb`, `SM`, `IST/AIDS`, `TB`, `HANS`, `ONCO`, `NUT`, `Nefro`, `Urologia`, etc.).
   - Quando uma linha possui múltiplas quebras verticais em colunas diferentes, `extract_text()` intercala palavras de colunas distintas na mesma linha de `raw_text`/`text` (ex.: em `occ-69250d6a59a79d792a83d1a1`, linha 3, p. 12: `"3. MS11126 abatacepte pó liofilizo injetável 250mg frasco medicamentos que atuam sob o CE ampola + seringa descartável sistema imunológico"`).
   - Em `v3`, os campos estruturados (`active_ingredient`, `strength`, `form`, `release_characteristic`, `context.pharmacological_group`, `context.Dispensation_facility`) foram limpos e validados contra o recorte exato de cada coluna do PDF (`x=123..284` e `x=284..398`). Consumidores de RAG devem usar os campos estruturados juntamente com `text`.
4. **Equivalência terapêutica / conversão sal-base e códigos de substituição**:
   - **Equivalência sal-base**: itens com `(equivalente a ...)` são literais do PDF (ex.: `occ-f36f0f2d106edff71e90f70d`, linha 979 de `F03`, corrigido em `v3` para `sulfato ferroso (equivalente a 40 mg de ferro elementar)`, `strength: "40 mg/mL"`, `form: "solução oral gotas"`).
   - **Notas de substituição na coluna `CÓDIGO` de `F03`**: 3 linhas (`occ-f96ef4a1994cf5a11a184774` row 374, `occ-e664b5b7394fb41a2b1ed092` row 707 e `occ-84776c9898723a987b8db9ff` row 1018) trazem observações administrativas da SES-DF na coluna de código (`"90665 em substituição ao 90850"`, `"29150 (substituído pelo código 36962 - carbonato de cálcio + colecalciferol 500mg + 200UI)"`, `"90969 (substituido pelo 35574)"`). Isso reflete substituição cadastral da SES-DF no próprio PDF oficial, **não** equivalência terapêutica universal.
5. **Preparo de exames / agentes diagnósticos**:
   - Em `F03`, itens dos grupos `meios de contraste radiológico` e `agentes de diagnóstico` (ex.: `amidotrizoato`, `ioexol`, `iopamidol`, `gadodiamida`, `fluoresceína`, `azul de metileno`, `tuberculina`) e `macrogol 3350 + bicarbonato de sódio + cloreto de sódio + cloreto de potássio` (`preparações para o trato alimentar e metabolismo`) aparecem apenas com sua descrição e grupo farmacológico oficiais. Nenhuma evidência extrapola instruções de preparo de exame.
6. **Notas de rodapé de página fora do recorte da linha (`F01` e `F03`)**:
   - Em `F01`: páginas 64, 66, 75 (`* Apresentações em blísteres do esquema PQT-U...`), página 88 (`* Medicamentos essenciais para cuidados paliativos...`) e página 129 (`* O diafragma de silicone é distribuído em seis tamanhos...`). Em `v3`, os asteriscos residuais foram removidos dos campos `active_ingredient` e `strength` das 7 ocorrências das páginas 64, 66 e 75.
   - Em `F03`: notas de rodapé nas páginas 26, 28, 30, 31, 32, 41, 43, 47, 52 e 57 (ex.: indisponibilidade temporária de `ciprofibrato`, `danazol`, `flunitrazepam`, `linezolida`; links de unidades de referência de antirretrovirais e tuberculose) ficam no rodapé da página fora do bounding box das linhas individuais.

---

## 5. Procedimentos 5 e 7 — Classificação dos Problemas Encontrados em `v2` e Correções Aplicadas em `v3`

Ao todo, foram identificadas e corrigidas **261 ocorrências** entre `v2` e `v3` (`214` de gravidade **Alta** e `47` de gravidade **Média**), além de **4 ressalvas estruturais/arquiteturais de gravidade Baixa/Média** documentadas para governança de recuperação.

### 5.1 Resumo por Categoria de Problema

| Categoria | Gravidade | Fonte(s) | Qtd. Ocorrências | Ação Executada em `v3` |
|---|---|---|---:|---|
| **C1. Formas farmacêuticas inferidas sem suporte no PDF da Farmácia Popular** | **Alta** | `F04` (p. 1) | `41` | `form` alterado para `"-"` nas 41 ocorrências; `release_characteristic` limpo na linha 24 (`succinato de metoprolol 25 mg`). |
| **C2. Contaminação de forma farmacêutica ou truncamento em `active_ingredient`** | **Alta** | `F03` (pp. 12–56) | `26` | Limpeza do `active_ingredient` e restauração da forma farmacêutica literal da célula `DESCRIÇÃO` (ex.: `permetrina`, `produto de cannabis`, `sulfato ferroso`, `propofol`, `raltegravir`, `abatacepte`, `pó liofilizado`). |
| **C3. Concentração ou forma inventada, truncada ou divergente do PDF** | **Alta** | `F03` (pp. 14–57) | `15` | Correção literal conforme PDF (ex.: fórmulas para fenilcetonúria rows 481–483; insulina análoga row 560; gosserrelina row 515; alfagalsidase row 48; triancinolona row 1042; PQT-u rows 828–829). |
| **C4. Formas farmacêuticas truncadas pela regex frente à coluna `DESCRIÇÃO`** | **Alta** | `F03` (pp. 11–58) | `129` | Restauração dos qualificadores literais (`solução para inalação`, `solução injetável`, `comprimido vaginal/sublingual/dispersível/mastigável`, `suspensão oftálmica/nasal`, `pomada dermatológica`, `solução oral gotas`, etc.). |
| **C5. Preenchimento de `release_characteristic` omitido (+ ajuste de forma em `F03`)** | **Alta** (`3` com forma) / **Média** (`40` só `release_characteristic`) | `F01` (`36`), `F03` (`7` exclusivas + `28` já contadas em C2–C4) | `43` (`3` Alta + `40` Média) | Preenchimento de `release_characteristic` (`liberação prolongada`, `liberação controlada`, `liberação retardada`, `ação prolongada`) em todas as 72 ocorrências literais do corpus (`F01`: 36, `F03`: 35, `F04`: 1). |
| **C6. Asterisco de nota de rodapé (`*`) acoplado a `active_ingredient`/`strength`** | **Média** | `F01` (pp. 64, 66, 75) | `7` | Remoção de `*` em `clofazimina`, `dapsona` e `rifampicina`. |
| **Total de ocorrências corrigidas (`v2` → `v3`)** | **214 Alta / 47 Média** | `F01`: `43`, `F03`: `177`, `F04`: `41` | **`261`** | Regenerado em `data/releases/corpus-consolidado-v3-revisao-2026-11-10` e registrado em `data/corpus/review-log.jsonl` (`COR-001`..`COR-450`). |

### 5.2 Tabelas Detalhadas das Correções Críticas (Categorias C2, C3 e C6 — Completas; C1 na Seção 3.3; C4 e C5 — Lista Completa na Seção 5.3)

#### 5.2.1 Categoria C2 (Alta) — Contaminação ou Truncamento em `active_ingredient` (`F03`, 26 ocorrências)

| ID (`occ-` / `evidence-`) | Fonte / Pág. / Linha | Valor em `v2` (`active_ingredient` / `strength` / `form`) | Valor Correto em `v3` (`active_ingredient` / `strength` / `form` / `release`) | Categoria / Motivo |
|---|---|---|---|---|
| `occ-69250d6a59a79d792a83d1a1` | `F03` p. 12 (row 3) | `abatacepte pó liofilizo` / `250mg` / `injetável` | `abatacepte` / `250mg` / `pó liofilizo injetável` / `None` | F03: Contaminação de forma farmacêutica, truncamento ou paráfrase em active_ingredient |
| `occ-54a81b579a4112c95dc2ef55` | `F03` p. 14 (row 56) | `alfatirotropina pó liófilo` / `1,1 mg` / `injetável` | `alfatirotropina` / `1,1 mg` / `pó liófilo injetável` / `None` | F03: Contaminação de forma farmacêutica, truncamento ou paráfrase em active_ingredient |
| `occ-8f4dd1d5d2682a7cb36f4791` | `F03` p. 16 (row 97) | `anidulafungina pó liófilo para` / `100 mg` / `solução injetável` | `anidulafungina` / `100 mg` / `pó liófilo para solução injetável` / `None` | F03: Contaminação de forma farmacêutica, truncamento ou paráfrase em active_ingredient |
| `occ-9cd002de6ab1f924f380279e` | `F03` p. 20 (row 218) | `cetrorrelix (acetato) pó liófilo` / `0,25 mg` / `injetável` | `cetrorrelix (acetato)` / `0,25 mg` / `pó liófilo injetável` / `None` | F03: Contaminação de forma farmacêutica, truncamento ou paráfrase em active_ingredient |
| `occ-ed2d26a2784e913f3cd92c2b` | `F03` p. 25 (row 321) | `dantroleno (sódico) pó liófilo` / `20 mg` / `injetável` | `dantroleno (sódico)` / `20 mg` / `pó liófilo injetável` / `None` | F03: Contaminação de forma farmacêutica, truncamento ou paráfrase em active_ingredient |
| `occ-ce1ef86a8619398013bbce5c` | `F03` p. 25 (row 324) | `daptomicina pó liófilo` / `500 mg` / `injetável` | `daptomicina` / `500 mg` / `pó liófilo injetável` / `None` | F03: Contaminação de forma farmacêutica, truncamento ou paráfrase em active_ingredient |
| `occ-4772177d670ea6e058ce6e78` | `F03` p. 28 (row 399) | `enfuvirtida (t-20) po liofilizado` / `90 mg/mL` / `solução injetável` | `enfuvirtida (t-20)` / `90 mg/mL` / `pó liofilizado solução injetável` / `None` | F03: Contaminação de forma farmacêutica, truncamento ou paráfrase em active_ingredient |
| `occ-e3076d368193a5939d33130d` | `F03` p. 29 (row 422) | `estreptomicina (sulfato) po liofilizado para` / `1g` / `solução injetável` | `estreptomicina (sulfato)` / `1g` / `pó liofilizado para solução injetável` / `None` | F03: Contaminação de forma farmacêutica, truncamento ou paráfrase em active_ingredient |
| `occ-164563deb661cfb7de918155` | `F03` p. 29 (row 425) | `etanercepte po liofilizado para` / `25mg` / `injetável` | `etanercepte` / `25mg` / `pó liofilizado para injetável` / `None` | F03: Contaminação de forma farmacêutica, truncamento ou paráfrase em active_ingredient |
| `occ-89b1798f87b6fef73e10d024` | `F03` p. 32 (row 481) | `fórmula dietoterápica para fenilcetonúria (acima de 8 anos)` / `lata 400 g a 500 g` / `pó para suspensão oral` | `fórmula dietoterápica para crianças acima de 8 anos de idade portadoras de fenilcetonúria` / `-` / `-` / `None` | F03: Contaminação de forma farmacêutica, truncamento ou paráfrase em active_ingredient |
| `occ-cb99538aad360c68ec43b6cf` | `F03` p. 32 (row 482) | `fórmula dietoterápica para fenilcetonúria (1 a 8 anos)` / `lata 400 g a 500 g` / `pó para suspensão oral` | `fórmula dietoterápica para crianças de 1 a 8 anos de idade portadoras de fenilcetonúria` / `-` / `-` / `None` | F03: Contaminação de forma farmacêutica, truncamento ou paráfrase em active_ingredient |
| `occ-b0b2adb7d79eb231b1207fad` | `F03` p. 32 (row 483) | `fórmula dietoterápica para fenilcetonúria (abaixo de 1 ano)` / `lata 400 g a 500 g` / `pó para suspensão oral` | `fórmula dietoterápica para lactentes de 0 a 1 ano de idade portadores de fenilcetonúria` / `-` / `-` / `None` | F03: Contaminação de forma farmacêutica, truncamento ou paráfrase em active_ingredient |
| `occ-3c6a7ade7457828257915ba8` | `F03` p. 33 (row 492) | `gencitabina (cloridrato) po liofilizado p/` / `1000 mg` / `solução injetável` | `gencitabina (cloridrato)` / `1000 mg` / `pó liofilizado p/ solução injetável` / `None` | F03: Contaminação de forma farmacêutica, truncamento ou paráfrase em active_ingredient |
| `occ-cb2f221f54aa7bded5e3b5cf` | `F03` p. 35 (row 538) | `ifosfamida po liofilizado para` / `2 g` / `solução injetável` | `ifosfamida` / `2 g` / `pó liofilizado para solução injetável` / `None` | F03: Contaminação de forma farmacêutica, truncamento ou paráfrase em active_ingredient |
| `occ-61a689c7573c5ca736785fc2` | `F03` p. 35 (row 542) | `imiglucerase po liófilo` / `400u` / `injetável` | `imiglucerase` / `400u` / `pó liófilo injetável` / `None` | F03: Contaminação de forma farmacêutica, truncamento ou paráfrase em active_ingredient |
| `occ-6e29ffc731a99e0c51becd28` | `F03` p. 37 (row 576) | `isavuconazol pó liófilo para` / `200 mg` / `solução injetável` | `isavuconazol` / `200 mg` / `pó liófilo para solução injetável` / `None` | F03: Contaminação de forma farmacêutica, truncamento ou paráfrase em active_ingredient |
| `occ-93e7ce149a62f0fe4691b61b` | `F03` p. 40 (row 651) | `meropenem po` / `1 g` / `injetável` | `meropenem` / `1 g` / `pó injetável` / `None` | F03: Contaminação de forma farmacêutica, truncamento ou paráfrase em active_ingredient |
| `occ-a21424e47ce4e985dcadfaf9` | `F03` p. 45 (row 771) | `omalizumabe po liofilizado para` / `150 mg` / `solução injetável` | `omalizumabe` / `150 mg` / `pó liofilizado para solução injetável ou solução injetável` / `None` | F03: Contaminação de forma farmacêutica, truncamento ou paráfrase em active_ingredient |
| `occ-21b793f26a82f2626d1f51ca` | `F03` p. 45 (row 773) | `omeprazol po` / `40 mg` / `injetável` | `omeprazol` / `40 mg` / `pó injetável` / `None` | F03: Contaminação de forma farmacêutica, truncamento ou paráfrase em active_ingredient |
| `occ-67f1d7bd5480cdd10e4558be` | `F03` p. 47 (row 808) | `permetrina loçao topica` / `10 mg/mL` / `solução injetável` | `permetrina` / `10 mg/mL` / `loção tópica` / `None` | F03: Contaminação de forma farmacêutica, truncamento ou paráfrase em active_ingredient |
| `occ-ef10d7c80122f262da327f1c` | `F03` p. 48 (row 845) | `produto de cannabis (canabidiol` / `200mg/mL` / `solução oral` | `produto de cannabis (canabidiol)` / `200mg/mL` / `solução oral com seringa dosadora ou solução gotas` / `None` | F03: Contaminação de forma farmacêutica, truncamento ou paráfrase em active_ingredient |
| `occ-5e0ab245d96ae38a847ce9ad` | `F03` p. 48 (row 846) | `produto de cannabis (canabidiol` / `50mg/mL` / `solução oral` | `produto de cannabis (canabidiol)` / `50mg/mL` / `solução oral com seringa dosadora ou solução gotas` / `None` | F03: Contaminação de forma farmacêutica, truncamento ou paráfrase em active_ingredient |
| `occ-b5ab0a0b1dd43f7abf9c6aec` | `F03` p. 49 (row 853) | `propofol emulsao` / `10 mg/mL` / `injetável` | `propofol` / `10 mg/mL` / `emulsão injetável` / `None` | F03: Contaminação de forma farmacêutica, truncamento ou paráfrase em active_ingredient |
| `occ-4b9787ecc83970c801624801` | `F03` p. 49 (row 854) | `propofol emulsao` / `10 mg/mL` / `injetável` | `propofol` / `10 mg/mL` / `emulsão injetável` / `None` | F03: Contaminação de forma farmacêutica, truncamento ou paráfrase em active_ingredient |
| `occ-8b66b9ebbc8bd492ababb54d` | `F03` p. 49 (row 855) | `propofol emulsao` / `20 mg/mL` / `injetável` | `propofol` / `20 mg/mL` / `emulsão injetável` / `None` | F03: Contaminação de forma farmacêutica, truncamento ou paráfrase em active_ingredient |
| `occ-e8d2a28fc0c6c040d3e15944` | `F03` p. 49 (row 869) | `raltegravir granulado para` / `100 mg` / `suspensão oral` | `raltegravir` / `100 mg` / `granulado para suspensão oral` / `None` | F03: Contaminação de forma farmacêutica, truncamento ou paráfrase em active_ingredient |
| `occ-472e3c315d6afe15afe9ff1c` | `F03` p. 50 (row 872) | `remifentanila (cloridrato) po liofilizado para` / `2 mg` / `solução injetável` | `remifentanila (cloridrato)` / `2 mg` / `pó liofilizado para solução injetável` / `None` | F03: Contaminação de forma farmacêutica, truncamento ou paráfrase em active_ingredient |
| `occ-f36f0f2d106edff71e90f70d` | `F03` p. 54 (row 979) | `sulfato ferroso (equivalente a` / `40 mg` / `comprimido revestido` | `sulfato ferroso` / `equivalente a 40 mg de ferro elementar` / `comprimido revestido` / `None` | F03: Contaminação de forma farmacêutica, truncamento ou paráfrase em active_ingredient |
| `occ-318a11b774821a36ea305bf6` | `F03` p. 56 (row 1019) | `tigeciclina po liofilizado para` / `50 mg` / `solução injetável` | `tigeciclina` / `50 mg` / `pó liofilizado para solução injetável` / `None` | F03: Contaminação de forma farmacêutica, truncamento ou paráfrase em active_ingredient |
| `occ-6ac06648435ebbb8f92d2342` | `F03` p. 57 (row 1035) | `toxina botulinica tipo a po liofilizado para` / `100u` / `solução injetável` | `toxina botulínica tipo A` / `100u` / `pó liofilizado para solução injetável` / `None` | F03: Contaminação de forma farmacêutica, truncamento ou paráfrase em active_ingredient |
| `occ-6a160f058098ac3a1c1a3f06` | `F03` p. 57 (row 1037) | `trastuzumabe pó liófilo` / `150 mg` / `injetável` | `trastuzumabe` / `150 mg` / `pó liófilo injetável` / `None` | F03: Contaminação de forma farmacêutica, truncamento ou paráfrase em active_ingredient |
| `occ-a0f115d3838fff52ec47022a` | `F03` p. 59 (row 1068) | `voriconazol po liofilizado para` / `200 mg` / `solução injetável` | `voriconazol` / `200 mg` / `pó liofilizado para solução injetável` / `None` | F03: Contaminação de forma farmacêutica, truncamento ou paráfrase em active_ingredient |

#### 5.2.2 Categoria C3 (Alta) — Concentração ou Forma Inventada, Truncada ou Divergente (`F03`, 15 ocorrências)

| ID (`occ-` / `evidence-`) | Fonte / Pág. / Linha | Valor em `v2` (`active_ingredient` / `strength` / `form`) | Valor Correto em `v3` (`active_ingredient` / `strength` / `form` / `release`) | Categoria / Motivo |
|---|---|---|---|---|
| `occ-cc647daee9433f68e327fd93` | `F03` p. 14 (row 48) | `alfagalsidase` / `1 mg` / `solução injetável` | `alfagalsidase` / `1 mg/mL` / `solução injetável` / `None` | F03: Concentração/forma não declarada ou divergente do texto literal do PDF |
| `occ-288516f4933ddc82d2e01afb` | `F03` p. 18 (row 145) | `betainterferona 1A` / `12.000.000 UI (44 mcg) seringa preenchida` / `solução injetável` | `betainterferona 1A` / `12.000.000 UI (44 mcg) seringa preenchida` / `injetável` / `None` | F03: Concentração/forma não declarada ou divergente do texto literal do PDF |
| `occ-291972901215205d4adbe432` | `F03` p. 18 (row 146) | `betainterferona 1A` / `6.000.000 UI (30 mcg) frasco-ampola + seringa preenchida diluente` / `pó liofilizado para solução injetável` | `betainterferona 1A` / `6.000.000 UI (30 mcg) frasco-ampola + seringa preenchida diluente` / `injetável` / `None` | F03: Concentração/forma não declarada ou divergente do texto literal do PDF |
| `occ-811ad30f693d48862526202b` | `F03` p. 18 (row 147) | `betainterferona 1A` / `6.000.000 UI (22 mcg) seringa preenchida` / `solução injetável` | `betainterferona 1A` / `6.000.000 UI (22 mcg) seringa preenchida` / `injetável` / `None` | F03: Concentração/forma não declarada ou divergente do texto literal do PDF |
| `occ-34c211344aed1ca3c6baa605` | `F03` p. 24 (row 295) | `complexo protrombínico total` / `500 UI a 600 UI (frasco-ampola)` / `pó liofilizado para solução injetável` | `complexo protrombínico total` / `500 UI a 600 UI (frasco-ampola)` / `injetável` / `None` | F03: Concentração/forma não declarada ou divergente do texto literal do PDF |
| `occ-3e214ed6687162dd9b296e5e` | `F03` p. 34 (row 515) | `gosserrelina (acetato)` / `3,6 mg` / `solução injetável (seringa preenchida)` | `gosserrelina (acetato)` / `3,6 mg` / `implante subcutâneo (seringa preenchida)` / `None` | F03: Concentração/forma não declarada ou divergente do texto literal do PDF |
| `occ-e39f9b1b1851765877bfabd9` | `F03` p. 35 (row 548) | `imunoglobulina humana` / `5,0g` / `solução injetável` | `imunoglobulina humana` / `5,0g` / `frasco` / `None` | F03: Concentração/forma não declarada ou divergente do texto literal do PDF |
| `occ-9804085866c3d3a8183e020a` | `F03` p. 36 (row 560) | `insulina análoga de ação prolongada` / `100 UI/mL (carpule 3 mL)` / `solução injetável (carpule)` | `insulina análoga de ação prolongada` / `carpule 3 mL` / `carpule` / `ação prolongada` | F03: Concentração/forma não declarada ou divergente do texto literal do PDF |
| `occ-4bd5f5d42ec8ef95ec152915` | `F03` p. 48 (row 828) | `poliquimioterapia única adulto (PQT-u adulto)` / `blister dose supervisionada e autoadministrada` / `blister (cápsulas e comprimidos)` | `poliquimioterapia única adulto (PQT-u adulto)` / `-` / `-` / `None` | F03: Concentração/forma não declarada ou divergente do texto literal do PDF |
| `occ-390b2fafe9c35c873c13e1db` | `F03` p. 48 (row 829) | `poliquimioterapia única infantil (PQT-u infantil)` / `blister dose supervisionada e autoadministrada` / `blister (cápsulas e comprimidos)` | `poliquimioterapia única infantil (PQT-u infantil)` / `-` / `-` / `None` | F03: Concentração/forma não declarada ou divergente do texto literal do PDF |
| `occ-cb22669dfd85514c6b90e4c5` | `F03` p. 56 (row 1010) | `tenofovir desoproxila (fumarato) + lamivudina` / `300 mg + 300 mg` / `comprimido` | `tenofovir desoproxila (fumarato) + lamivudina` / `300 mg + 300 mg` / `-` / `None` | F03: Concentração/forma não declarada ou divergente do texto literal do PDF |
| `occ-e34170ebed3c19cdf4f5f5d7` | `F03` p. 57 (row 1042) | `triancinolona acetonida` / `1 mg/g (bisnaga 10 g)` / `pomada bucal ou pasta` | `triancinolona acetonida` / `1 mg/mL (bisnaga 10 g)` / `pomada bucal ou pasta` / `None` | F03: Concentração/forma não declarada ou divergente do texto literal do PDF |

#### 5.2.3 Categoria C6 (Média) — Asterisco de Nota de Rodapé (`*`) em `F01` (7 ocorrências)

| ID (`occ-` / `evidence-`) | Fonte / Pág. | Valor em `v2` (`active_ingredient` / `strength` / `form`) | Valor Correto em `v3` (`active_ingredient` / `strength` / `form`) | Categoria / Motivo |
|---|---|---|---|---|
| `occ-24bb5cc708bdf9ec14db3e4f` | `F01` p. 64 | `clofazimina` / `50 mg*` / `cápsula` | `clofazimina` / `50 mg` / `cápsula` | F01: Asterisco de nota de rodapé (*) acoplado a princípio ativo/concentração |
| `occ-156a268279dc2ce94c2162da` | `F01` p. 64 | `clofazimina` / `100 mg*` / `cápsula` | `clofazimina` / `100 mg` / `cápsula` | F01: Asterisco de nota de rodapé (*) acoplado a princípio ativo/concentração |
| `occ-bf2e571a98829db41258e934` | `F01` p. 66 | `dapsona*` / `50 mg*` / `comprimido` | `dapsona` / `50 mg` / `comprimido` | F01: Asterisco de nota de rodapé (*) acoplado a princípio ativo/concentração |
| `occ-6a9aafbe040f817ee5e0a943` | `F01` p. 66 | `dapsona*` / `100 mg*` / `comprimido` | `dapsona` / `100 mg` / `comprimido` | F01: Asterisco de nota de rodapé (*) acoplado a princípio ativo/concentração |
| `occ-0449e40e8c3c9732aa285dc5` | `F01` p. 75 | `rifampicina*` / `300 mg*` / `cápsula` | `rifampicina` / `300 mg` / `cápsula` | F01: Asterisco de nota de rodapé (*) acoplado a princípio ativo/concentração |
| `occ-5def59d51aa08a02896fb946` | `F01` p. 75 | `rifampicina*` / `150 mg*` / `cápsula` | `rifampicina` / `150 mg` / `cápsula` | F01: Asterisco de nota de rodapé (*) acoplado a princípio ativo/concentração |
| `occ-a4156cb9abb6e7f6845203ce` | `F01` p. 75 | `rifampicina*` / `20mg/mL` / `suspensão oral` | `rifampicina` / `20mg/mL` / `suspensão oral` | F01: Asterisco de nota de rodapé (*) acoplado a princípio ativo/concentração |

### 5.3 Lista Completa das Demais Ocorrências Corrigidas em `F01` (36 ocorrências de `release_characteristic`) e `F03` (136 ocorrências de Forma / Liberação)

| ID (`occ-` / `evidence-`) | Fonte / Pág. / Linha | Gravidade | Princípio Ativo (`v3`) | Valor em `v2` (`strength` / `form` / `release`) | Valor Correto em `v3` (`strength` / `form` / `release`) |
|---|---|---|---|---|---|
| `occ-93e7222f1027f71a044ba52c` | `F01` p. 30 (row 3) | Média | `gliclazida` | `30 mg` / `comprimido de liberação prolongada` / `None` | `30 mg` / `comprimido de liberação prolongada` / `liberação prolongada` |
| `occ-ff88337e1297b03e9238567f` | `F01` p. 30 (row 4) | Média | `gliclazida` | `60 mg` / `comprimido de liberação prolongada` / `None` | `60 mg` / `comprimido de liberação prolongada` / `liberação prolongada` |
| `occ-274ce03f729d44431df41699` | `F01` p. 30 (row 10) | Média | `insulina análoga de ação prolongada` | `100 UI/mL` / `solução injetável` / `None` | `100 UI/mL` / `solução injetável` / `ação prolongada` |
| `occ-5a809a0271b5cb1089e755fc` | `F01` p. 30 (row 11) | Média | `insulina análoga de ação prolongada` | `300 UI/mL` / `solução injetável` / `None` | `300 UI/mL` / `solução injetável` / `ação prolongada` |
| `occ-a297adcbdfa89db4f8ea17f1` | `F01` p. 30 (row 12) | Média | `insulina análoga de ação rápida` | `100 UI/mL` / `solução injetável` / `None` | `100 UI/mL` / `solução injetável` / `ação rápida` |
| `occ-aff3afa8e74531a5f1f8798c` | `F01` p. 31 (row 6) | Média | `mesalazina` | `500 mg` / `comprimido de liberação prolongada` / `None` | `500 mg` / `comprimido de liberação prolongada` / `liberação prolongada` |
| `occ-4247506f375048a458297f0c` | `F01` p. 31 (row 12) | Média | `mesalazina` | `2 g` / `granulado revestido de liberação prolongada` / `None` | `2 g` / `granulado revestido de liberação prolongada` / `liberação prolongada` |
| `occ-e959e0616cfb3f72d831f117` | `F01` p. 43 (row 1) | Média | `ácido nicotínico` | `500 mg` / `comprimido de liberação prolongada` / `None` | `500 mg` / `comprimido de liberação prolongada` / `liberação prolongada` |
| `occ-cf622f33f36966f14b315dee` | `F01` p. 44 (row 2) | Média | `bezafibrato` | `400 mg` / `comprimido de liberação prolongada` / `None` | `400 mg` / `comprimido de liberação prolongada` / `liberação prolongada` |
| `occ-18869ed0c4116a5064b71fff` | `F01` p. 46 (row 12) | Média | `fenofibrato` | `250 mg` / `cápsula de liberação retardada` / `None` | `250 mg` / `cápsula de liberação retardada` / `liberação retardada` |
| `occ-3e9b5eedcccf2400202bac8b` | `F01` p. 48 (row 6) | Média | `pentoxifilina` | `400 mg` / `comprimido de liberação prolongada` / `None` | `400 mg` / `comprimido de liberação prolongada` / `liberação prolongada` |
| `occ-2ead66a3708b97ca2e154597` | `F01` p. 49 (row 4) | Média | `succinato de metoprolol` | `25 mg` / `comprimido de liberação prolongada` / `None` | `25 mg` / `comprimido de liberação prolongada` / `liberação prolongada` |
| `occ-6af4a40640c577895c5f8941` | `F01` p. 49 (row 5) | Média | `succinato de metoprolol` | `50 mg` / `comprimido de liberação prolongada` / `None` | `50 mg` / `comprimido de liberação prolongada` / `liberação prolongada` |
| `occ-ed50e8539d6fddec9256a192` | `F01` p. 49 (row 6) | Média | `succinato de metoprolol` | `100 mg` / `comprimido de liberação prolongada` / `None` | `100 mg` / `comprimido de liberação prolongada` / `liberação prolongada` |
| `occ-cae4c93f8886b384242f438c` | `F01` p. 56 (row 8) | Média | `acetato de lanreotida` | `60 mg` / `solução injetável de liberação prolongada` / `None` | `60 mg` / `solução injetável de liberação prolongada` / `liberação prolongada` |
| `occ-d2dbae48a4041709898a2c82` | `F01` p. 56 (row 9) | Média | `acetato de lanreotida` | `90 mg` / `solução injetável de liberação prolongada` / `None` | `90 mg` / `solução injetável de liberação prolongada` / `liberação prolongada` |
| `occ-61cf1f47cf7a3796a3a46037` | `F01` p. 56 (row 10) | Média | `acetato de lanreotida` | `120 mg` / `solução injetável de liberação prolongada` / `None` | `120 mg` / `solução injetável de liberação prolongada` / `liberação prolongada` |
| `occ-8e1f49d65a5f8d5f5dae5085` | `F01` p. 69 (row 9) | Média | `fostensavir trometamol` | `600 mg` / `comprimido de liberação prolongada` / `None` | `600 mg` / `comprimido de liberação prolongada` / `liberação prolongada` |
| `occ-1d0694806edfc7648fa60ca4` | `F01` p. 89 (row 7) | Média | `acetato de leuprorrelina` | `3,75 mg` / `pó para suspensão injetável de liberação prolongada` / `None` | `3,75 mg` / `pó para suspensão injetável de liberação prolongada` / `liberação prolongada` |
| `occ-1c5a57fecafb596905654158` | `F01` p. 89 (row 9) | Média | `acetato de leuprorrelina` | `45 mg` / `pó para suspensão injetável de liberação prolongada` / `None` | `45 mg` / `pó para suspensão injetável de liberação prolongada` / `liberação prolongada` |
| `occ-aaf066c0383ea27fc9ac29c1` | `F01` p. 91 (row 10) | Média | `ciclofosfamida` | `50 mg` / `comprimido de liberação retardada` / `None` | `50 mg` / `comprimido de liberação retardada` / `liberação retardada` |
| `occ-a2c261fb41a546e15cabf88a` | `F01` p. 93 (row 4) | Média | `embonato de triptorrelina` | `11,25 mg` / `pó para suspensão injetável de liberação prolongada` / `None` | `11,25 mg` / `pó para suspensão injetável de liberação prolongada` / `liberação prolongada` |
| `occ-15af4308ff2ee674cfe9d8a2` | `F01` p. 93 (row 5) | Média | `embonato de triptorrelina` | `22,5 mg` / `pó para suspensão injetável de liberação prolongada` / `None` | `22,5 mg` / `pó para suspensão injetável de liberação prolongada` / `liberação prolongada` |
| `occ-04863a28c658364b050359de` | `F01` p. 94 (row 5) | Média | `fumarato de dimetila` | `120 mg` / `cápsula de liberação retardada` / `None` | `120 mg` / `cápsula de liberação retardada` / `liberação retardada` |
| `occ-7568a43cba8051f5d8b87e33` | `F01` p. 94 (row 6) | Média | `fumarato de dimetila` | `240 mg` / `cápsula de liberação retardada` / `None` | `240 mg` / `cápsula de liberação retardada` / `liberação retardada` |
| `occ-7f07ce7ecfe93ff85d8961c4` | `F01` p. 98 (row 5) | Média | `triptorrelina` | `3,75 mg` / `pó para suspensão injetável de liberação prolongada` / `None` | `3,75 mg` / `pó para suspensão injetável de liberação prolongada` / `liberação prolongada` |
| `occ-b0e50127ca3cbcc7fe933819` | `F01` p. 98 (row 6) | Média | `upadacitinibe` | `15 mg` / `comprimido de liberação prolongada` / `None` | `15 mg` / `comprimido de liberação prolongada` / `liberação prolongada` |
| `occ-eb1fa9be27e7db077ad6f5df` | `F01` p. 101 (row 9) | Média | `bromidrato de galantamina` | `8 mg` / `cápsula de liberação prolongada` / `None` | `8 mg` / `cápsula de liberação prolongada` / `liberação prolongada` |
| `occ-b93276b1f060810fbbb1d264` | `F01` p. 101 (row 10) | Média | `bromidrato de galantamina` | `16 mg` / `cápsula de liberação prolongada` / `None` | `16 mg` / `cápsula de liberação prolongada` / `liberação prolongada` |
| `occ-f1b75d8e1b2ef7d0ec44a662` | `F01` p. 101 (row 11) | Média | `bromidrato de galantamina` | `24 mg` / `cápsula de liberação prolongada` / `None` | `24 mg` / `cápsula de liberação prolongada` / `liberação prolongada` |
| `occ-345bbcdfaf853d7bb87148cb` | `F01` p. 102 (row 11) | Média | `cloridrato de biperideno` | `4 mg` / `comprimido de liberação prolongada` / `None` | `4 mg` / `comprimido de liberação prolongada` / `liberação prolongada` |
| `occ-5534b069576114e7d3121e6b` | `F01` p. 103 (row 1) | Média | `cloridrato de bupropiona` | `150 mg` / `comprimido de liberação prolongada` / `None` | `150 mg` / `comprimido de liberação prolongada` / `liberação prolongada` |
| `occ-3f22c54d30b72ebd7f722522` | `F01` p. 111 (row 5) | Média | `sulfato de morfina` | `30 mg` / `cápsula de liberação prolongada` / `None` | `30 mg` / `cápsula de liberação prolongada` / `liberação prolongada` |
| `occ-6040fe1cdfad9e62fec92dd7` | `F01` p. 111 (row 6) | Média | `sulfato de morfina` | `60 mg` / `cápsula de liberação prolongada` / `None` | `60 mg` / `cápsula de liberação prolongada` / `liberação prolongada` |
| `occ-53f3e76f1d88f782d9fd9e45` | `F01` p. 111 (row 7) | Média | `sulfato de morfina` | `100 mg` / `cápsula de liberação prolongada` / `None` | `100 mg` / `cápsula de liberação prolongada` / `liberação prolongada` |
| `occ-494c71bde998ee8187cb6399` | `F01` p. 131 (row 3) | Média | `garra-do-diabo (Harpagophytum procumbens DC. ex Meissn.)` | `30 a 100 mg de harpagosídeo ou 45 a 150 mg de iridoides totais expressos em harpagosídeos (dose diária)` / `comprimido de liberação retardada` / `None` | `30 a 100 mg de harpagosídeo ou 45 a 150 mg de iridoides totais expressos em harpagosídeos (dose diária)` / `comprimido de liberação retardada` / `liberação retardada` |
| `occ-e0344624134cfc2a5c3860b4` | `F03` p. 12 (row 21) | Alta | `ácido zoledrônico` | `4 mg` / `solução injetável` / `None` | `4 mg` / `pó liofilizado ou solução injetável` / `None` |
| `occ-3d16d024a2e7800503a23286` | `F03` p. 13 (row 42) | Alta | `alfadornase` | `1mg/mL` / `solução` / `None` | `1mg/mL` / `solução para inalação` / `None` |
| `occ-ca73917673f1c6b5c6864fa8` | `F03` p. 13 (row 46) | Alta | `alfaepoetina` | `4.000 UI` / `solução injetável` / `None` | `4.000 UI` / `solução injetável ou pó liofilizado` / `None` |
| `occ-35d1cf765c297c040053de8c` | `F03` p. 15 (row 78) | Alta | `amido hidroxietilico` | `6%` / `solução` / `None` | `6%` / `solução coloide injetável` / `None` |
| `occ-6b4361fd678915e9be3e5376` | `F03` p. 15 (row 85) | Alta | `amoxicilina` | `500 mg` / `cápsula` / `None` | `500 mg` / `cápsula ou comprimido` / `None` |
| `occ-866d69eb237d37288aa5d50a` | `F03` p. 16 (row 100) | Alta | `arsenio (trióxido)` | `2mg/mL` / `solução` / `None` | `2mg/mL` / `solução para diluição para infusão` / `None` |
| `occ-8ba2c9995808a8d21ff382ba` | `F03` p. 16 (row 109) | Alta | `artesunato` | `60 mg/mL` / `pó liofilizado para solução injetável` / `None` | `60 mg/mL` / `pó liófilo para injeção endovenosa` / `None` |
| `occ-35f36e4f44b27158aaabe926` | `F03` p. 17 (row 131) | Alta | `beclometasona (dipropionato)` | `250mcg/dose` / `solução` / `None` | `250mcg/dose` / `solução aerossol oral` / `None` |
| `occ-812dec0ab31c1798a5739af4` | `F03` p. 17 (row 132) | Alta | `beclometasona (dipropionato)` | `50mcg/dose` / `solução` / `None` | `50mcg/dose` / `solução aerossol oral` / `None` |
| `occ-d73427eedf5703737538bd3d` | `F03` p. 18 (row 150) | Alta | `betametasona (valerato)` | `0,1% (bisnaga 30 g)` / `creme dermatológico` / `None` | `0,1% (bisnaga 30 g)` / `creme` / `None` |
| `occ-b86e952ae687b2fffb4387c7` | `F03` p. 18 (row 151) | Alta | `bezafibrato` | `400mg` / `comprimido` / `None` | `400mg` / `comprimido de desintegração lenta` / `desintegração lenta` |
| `occ-7d110505887ca3282d5bf2b6` | `F03` p. 18 (row 160) | Alta | `bisacodil` | `5 mg` / `comprimido revestido` / `None` | `5 mg` / `comprimido revestido liberação retardada` / `liberação retardada` |
| `occ-f57cd6e5f1b296f1c7a46ef2` | `F03` p. 18 (row 167) | Alta | `brinzolamida` | `10mg/mL` / `suspensão` / `None` | `10mg/mL` / `suspensão oftálmica` / `None` |
| `occ-8e000650f51764096323787a` | `F03` p. 18 (row 168) | Alta | `bromoprida` | `10mg` / `cápsula` / `None` | `10mg` / `cápsula ou comprimido` / `None` |
| `occ-f8158b9aa5275f734b30ccb4` | `F03` p. 19 (row 170) | Alta | `budesonida` | `32mcg/dose` / `suspensão` / `None` | `32mcg/dose` / `suspensão nasal` / `None` |
| `occ-8cf6acbccb723054a29056f7` | `F03` p. 19 (row 178) | Alta | `bussulfano` | `6mg/ml` / `solução injetável` / `None` | `6mg/ml` / `solução injetável para infusão` / `None` |
| `occ-d2c545d8fcba8b54b9c7e612` | `F03` p. 19 (row 180) | Alta | `butilbrometo de escopolamina` | `10 mg` / `comprimido` / `None` | `10 mg` / `comprimido ou drágea` / `None` |
| `occ-be847818ca8465c1a99934d6` | `F03` p. 20 (row 195) | Alta | `carbonato de cálcio` | `500mg` / `comprimido` / `None` | `500mg` / `comprimido ou drágea` / `None` |
| `occ-4588d95017826e21d88fb8b1` | `F03` p. 20 (row 200) | Alta | `carvão ativado` | `25g` / `pó para suspensão oral (frasco ou envelope)` / `None` | `25g` / `pó frasco ou envelope` / `None` |
| `occ-b1611204646f0aafaed7ec7e` | `F03` p. 20 (row 204) | Alta | `cefalexina` | `500 mg` / `cápsula` / `None` | `500 mg` / `cápsula ou drágea ou comprimido` / `None` |
| `occ-35aa08b03801a03eca1cbd89` | `F03` p. 20 (row 216) | Alta | `cetoconazol` | `2% (bisnaga 30 g)` / `creme dermatológico` / `None` | `2% (bisnaga 30 g)` / `creme` / `None` |
| `occ-8d222dd0f1a881b1fb80d01c` | `F03` p. 21 (row 221) | Alta | `ciclofosfamida` | `50 mg` / `comprimido revestido` / `None` | `50 mg` / `comprimido revestido de liberação retardada` / `liberação retardada` |
| `occ-f0e46ccdbede8cf45c97c8e0` | `F03` p. 22 (row 257) | Alta | `clomipramina (cloridrato)` | `25 mg` / `comprimido` / `None` | `25 mg` / `comprimido ou drágea` / `None` |
| `occ-d150316dbef4acdc4baf18e4` | `F03` p. 22 (row 258) | Alta | `clomipramina` | `75 mg` / `comprimido` / `None` | `75 mg` / `comprimido liberação lenta` / `liberação lenta` |
| `occ-70c5d2679f2f25b5be8e2056` | `F03` p. 23 (row 273) | Alta | `cloreto de sódio` | `0,9 %` / `solução` / `None` | `0,9 %` / `solução não injetável` / `None` |
| `occ-75c60747180854a75232b0ec` | `F03` p. 23 (row 276) | Alta | `clorexidina` | `10 mg/mL (1% - frasco 1000 mL)` / `solução aquosa tópica` / `None` | `10 mg/mL (1% - frasco 1000 mL)` / `solução aquosa` / `None` |
| `occ-419a5ac6ad616e4c5ee5573b` | `F03` p. 23 (row 281) | Alta | `clorpromazina (cloridrato)` | `40 mg/mL` / `solução oral` / `None` | `40 mg/mL` / `solução oral gotas` / `None` |
| `occ-ad3cdf673e78774f946ef9e9` | `F03` p. 23 (row 288) | Alta | `colistimetato sódico` | `1.000.000 UI` / `pó para solução` / `None` | `1.000.000 UI` / `pó para solução inalatória e injetável` / `None` |
| `occ-86851e5df5c8f037bf46e450` | `F03` p. 25 (row 331) | Alta | `deferasirox` | `125mg` / `comprimido` / `None` | `125mg` / `comprimido dispersível` / `None` |
| `occ-9c3b5384a5f4097ffc09491c` | `F03` p. 25 (row 332) | Alta | `deferasirox` | `250mg` / `comprimido` / `None` | `250mg` / `comprimido dispersível` / `None` |
| `occ-ba6f97e3db854aace22af03d` | `F03` p. 25 (row 333) | Alta | `deferasirox` | `500mg` / `comprimido` / `None` | `500mg` / `comprimido dispersível` / `None` |
| `occ-18e40c871223030ec0659ba2` | `F03` p. 26 (row 345) | Alta | `dexametasona` | `0,1 %` / `suspensão` / `None` | `0,1 %` / `suspensão oftálmica` / `None` |
| `occ-f6539210bd2b1171cfd0ad04` | `F03` p. 26 (row 347) | Alta | `dexclorfeniramina` | `2 mg / 5 mL` / `solução oral` / `None` | `2 mg / 5 mL` / `solução oral edulcorada ou xarope` / `None` |
| `occ-0bf91b62dc219e352b8f3d20` | `F03` p. 27 (row 380) | Alta | `doxiciclina` | `100mg` / `comprimido` / `None` | `100mg` / `comprimido dispersível` / `None` |
| `occ-78f705bb22e68d8860cd59d8` | `F03` p. 27 (row 383) | Alta | `doxorrubicina (cloridrato)` | `50 mg` / `solução injetável` / `None` | `50 mg` / `solução injetável ou pó liofilizado para solução injetável` / `None` |
| `occ-4fae93f02b7e7aa68ac424d5` | `F03` p. 28 (row 388) | Alta | `eculizumabe` | `10 mg/mL` / `solução` / `None` | `10 mg/mL` / `solução para diluição para infusão` / `None` |
| `occ-7ea91296e7c8289498633d08` | `F03` p. 30 (row 443) | Alta | `fenobarbital` | `40 mg/mL` / `solução oral` / `None` | `40 mg/mL` / `solução oral gotas` / `None` |
| `occ-f273acace36f36966fe5a7f4` | `F03` p. 31 (row 462) | Alta | `fluoxetina` | `20 mg` / `comprimido` / `None` | `20 mg` / `comprimido ou cápsula` / `None` |
| `occ-6dfb01fa30222e347ed6190d` | `F03` p. 31 (row 467) | Alta | `folinato de cálcio` | `15 mg` / `cápsula` / `None` | `15 mg` / `cápsula ou comprimido` / `None` |
| `occ-cf60948de74eec6e14b837d7` | `F03` p. 32 (row 471) | Alta | `formoterol (fumarato)` | `12mcg/dose` / `cápsula` / `None` | `12mcg/dose` / `cápsula com pó para inalação ou cápsula inalatória` / `None` |
| `occ-c500bcdbb85f9875820c5df8` | `F03` p. 32 (row 473) | Alta | `fosfato de sódio monobásico + fosfato de sódio dibásico` | `(16 g + 6 g)/100 mL (frasco ou bolsa 125 mL a 133 mL)` / `solução retal (enema)` / `None` | `(16 g + 6 g)/100 mL (frasco ou bolsa 125 mL a 133 mL)` / `solução enema` / `None` |
| `occ-379462c069429d4e03b9537c` | `F03` p. 32 (row 487) | Alta | `galantamina (hidrobrometo)` | `8mg` / `cápsula` / `None` | `8mg` / `cápsula de liberação prolongada` / `liberação prolongada` |
| `occ-4b9b47231ac43ec0c3d8f944` | `F03` p. 32 (row 488) | Alta | `galantamina (hidrobrometo)` | `16mg` / `cápsula` / `None` | `16mg` / `cápsula liberação prolongada` / `liberação prolongada` |
| `occ-211cf20753e28ac47b11186d` | `F03` p. 32 (row 489) | Alta | `galantamina (hidrobrometo)` | `24mg` / `cápsula` / `None` | `24mg` / `cápsula liberação prolongada` / `liberação prolongada` |
| `occ-b042234935f17939a393d2ab` | `F03` p. 33 (row 500) | Alta | `glicerina (glicerol)` | `120 mg/mL (12% - frasco ou bolsa 500 mL)` / `solução retal (enema)` / `None` | `120 mg/mL (12% - frasco ou bolsa 500 mL)` / `solução retal/enema` / `None` |
| `occ-f71b7524d95eeeada127ac43` | `F03` p. 33 (row 502) | Alta | `gliclazida` | `30 mg` / `comprimido` / `None` | `30 mg` / `comprimido de liberação prolongada` / `liberação prolongada` |
| `occ-e0e26ff90982cc58abef5e93` | `F03` p. 33 (row 503) | Alta | `gliclazida` | `60 mg` / `comprimido` / `None` | `60 mg` / `comprimido de liberação prolongada` / `liberação prolongada` |
| `occ-1bd990c64b0195b2895e0d10` | `F03` p. 33 (row 514) | Alta | `gosserrelina (acetato)` | `10,80 mg` / `injetável` / `None` | `10,80 mg` / `injetável de liberação prolongada (seringa preenchida)` / `liberação prolongada` |
| `occ-924adb9ef742afde7d707675` | `F03` p. 34 (row 520) | Alta | `haloperidol` | `2 mg/mL` / `solução oral` / `None` | `2 mg/mL` / `solução oral gotas` / `None` |
| `occ-d93113bf5df851095302d72d` | `F03` p. 34 (row 523) | Alta | `hidralazina` | `50mg` / `comprimido` / `None` | `50mg` / `comprimido ou drágea` / `None` |
| `occ-b041f581397e915747485883` | `F03` p. 34 (row 528) | Alta | `hidrocortisona (succinato sodico)` | `100 mg` / `pó para solução` / `None` | `100 mg` / `pó para solução injetável` / `None` |
| `occ-95d83bab1656f199b213eea7` | `F03` p. 35 (row 539) | Alta | `iloprosta` | `10 mcg/mL` / `solução` / `None` | `10 mcg/mL` / `solução para inalação` / `None` |
| `occ-ced93846474bb8c6ce88d487` | `F03` p. 35 (row 540) | Alta | `imatinibe (mesilato)` | `400 mg` / `comprimido revestido` / `None` | `400 mg` / `comprimido revestido ou cápsula` / `None` |
| `occ-d4f04c33b93fb2ba2abf4e71` | `F03` p. 35 (row 541) | Alta | `imatinibe (mesilato)` | `100mg` / `comprimido revestido` / `None` | `100mg` / `comprimido revestido ou cápsula` / `None` |
| `occ-5ff05a19a860eb46c4d2f406` | `F03` p. 35 (row 546) | Alta | `etonogestrel` | `68 mg` / `implante subdérmico (com aplicador)` / `None` | `68 mg` / `implante subdérmico` / `None` |
| `occ-b5c35a3c742d2c9bf8f9efe5` | `F03` p. 35 (row 551) | Alta | `indapamida` | `1,5 mg` / `comprimido` / `None` | `1,5 mg` / `comprimido liberação prolongada` / `liberação prolongada` |
| `occ-72000e08ca435a27afc14d28` | `F03` p. 36 (row 568) | Alta | `insulina humana regular` | `100 UI/mL` / `solução` / `None` | `100 UI/mL` / `solução ou suspensão injetável` / `None` |
| `occ-afa5aff86409b4cde1cce01d` | `F03` p. 36 (row 573) | Alta | `ipratropio (brometo)` | `0,25 mg/mL` / `solução` / `None` | `0,25 mg/mL` / `solução para inalação` / `None` |
| `occ-b9a4722f26ad0093039960e7` | `F03` p. 37 (row 575) | Alta | `isavuconazol` | `100 mg` / `cápsula` / `None` | `100 mg` / `cápsula dura` / `None` |
| `occ-b7353558cc2eb76da72c2258` | `F03` p. 37 (row 579) | Alta | `isossorbida (dinitrato)` | `5 mg` / `comprimido` / `None` | `5 mg` / `comprimido sublingual` / `None` |
| `occ-0d65a0214341f4ea9d89e1d0` | `F03` p. 38 (row 607) | Alta | `levodopa + benserazida (cloridrato)` | `100 mg + 25 mg` / `comprimido, cápsula ou drágea de liberação prolongada` / `None` | `100 mg + 25 mg` / `comprimido ou cápsula ou drágea liberação prolongada` / `liberação prolongada` |
| `occ-fb7a8e20e45fee249b7e040f` | `F03` p. 39 (row 625) | Alta | `lidocaína` | `100mg/mL` / `solução` / `None` | `100mg/mL` / `solução tópica spray` / `None` |
| `occ-8ebc921e055ebb6522f64124` | `F03` p. 40 (row 652) | Alta | `mesalazina` | `500mg` / `comprimido` / `None` | `500mg` / `comprimido de liberação prolongada` / `liberação prolongada` |
| `occ-fcb1728720eb7d181d90bcdd` | `F03` p. 40 (row 653) | Alta | `mesalazina` | `400mg` / `comprimido revestido` / `None` | `400mg` / `comprimido revestido ou comprimido revestido de liberação retardada` / `liberação retardada` |
| `occ-8e53264620866a644d7b485a` | `F03` p. 40 (row 654) | Alta | `mesalazina` | `800mg` / `comprimido revestido` / `None` | `800mg` / `comprimido revestido ou comprimido revestido de liberação retardada` / `liberação retardada` |
| `occ-8d4c9df6f2789ee0f39f16ec` | `F03` p. 40 (row 656) | Alta | `mesalazina` | `2 g` / `grânulo de liberação prolongada (envelope/sachê)` / `None` | `2 g` / `grânulo de liberação prolongada` / `liberação prolongada` |
| `occ-45ad7022d0b91faec952f212` | `F03` p. 41 (row 665) | Alta | `metilfenidato (cloridrato)` | `30mg` / `cápsula` / `None` | `30mg` / `cápsula com microgrânulos de liberação modificada` / `liberação modificada` |
| `occ-21e83d6389de3f5f5f500f4e` | `F03` p. 41 (row 670) | Alta | `metoprolol (succinato)` | `50 mg` / `comprimido` / `None` | `50 mg` / `comprimido de liberação controlada` / `liberação controlada` |
| `occ-1444b3fba1dcc89115c77d24` | `F03` p. 41 (row 671) | Alta | `metoprolol (succinato)` | `25 mg` / `comprimido revestido` / `None` | `25 mg` / `comprimido revestido de liberação controlada` / `liberação controlada` |
| `occ-f82c45b13dec41f13d8cb790` | `F03` p. 42 (row 702) | Alta | `mirtazapina` | `30mg` / `comprimido revestido` / `None` | `30mg` / `comprimido revestido ou comprimido orodispersível` / `None` |
| `occ-d81da7c5c7b546187d94754f` | `F03` p. 42 (row 703) | Alta | `mirtazapina` | `45mg` / `comprimido revestido` / `None` | `45mg` / `comprimido revestido ou comprimido orodispersível` / `None` |
| `occ-2d805034f4e6e3d946c32e7c` | `F03` p. 42 (row 704) | Alta | `misoprostol` | `200 mcg` / `comprimido` / `None` | `200 mcg` / `comprimido vaginal` / `None` |
| `occ-b53f1771a09b6507cac663c4` | `F03` p. 42 (row 705) | Alta | `misoprostol` | `200 mcg` / `comprimido` / `None` | `200 mcg` / `comprimido vaginal` / `None` |
| `occ-2380509ac71a82f85db235b7` | `F03` p. 42 (row 706) | Alta | `misoprostol` | `25 mcg` / `comprimido` / `None` | `25 mcg` / `comprimido vaginal` / `None` |
| `occ-d14aa21adf3192764814dfae` | `F03` p. 42 (row 707) | Alta | `misoprostol` | `25 mcg` / `comprimido` / `None` | `25 mcg` / `comprimido vaginal` / `None` |
| `occ-c2822e9b57c1d86fc22ad93f` | `F03` p. 42 (row 708) | Alta | `mitomicina` | `0,04% (2,5 mL)` / `pó liofilizado (frasco-ampola)` / `None` | `0,04% (2,5 mL)` / `pó liofilizado` / `None` |
| `occ-d31a662beec907cd3e112036` | `F03` p. 42 (row 709) | Alta | `montelucaste (sodico)` | `4 mg` / `comprimido` / `None` | `4 mg` / `comprimido mastigável` / `None` |
| `occ-0553fc12bfa44bdee94e0436` | `F03` p. 42 (row 710) | Alta | `montelucaste (sodico)` | `5 mg` / `comprimido` / `None` | `5 mg` / `comprimido mastigável` / `None` |
| `occ-3906d814250182f3218fbd4c` | `F03` p. 42 (row 713) | Alta | `morfina (sulfato)` | `30mg` / `cápsula` / `None` | `30mg` / `cápsula liberação controlada` / `liberação controlada` |
| `occ-b6e00fd5570f11bbf5da7a43` | `F03` p. 42 (row 714) | Alta | `morfina (sulfato)` | `60mg` / `cápsula` / `None` | `60mg` / `cápsula ou comprimido de liberação controlada` / `liberação controlada` |
| `occ-2ea4c7708d14b13b7bab8ee5` | `F03` p. 42 (row 717) | Alta | `morfina` | `100 mg` / `cápsula` / `None` | `100 mg` / `cápsula liberação controlada` / `liberação controlada` |
| `occ-0b842a68f77c8fe98f279ca2` | `F03` p. 43 (row 725) | Alta | `mycobacterium bovis (bcg)` | `40 mg` / `ampola` / `None` | `40 mg` / `pó liofilizado` / `None` |
| `occ-d6c2a093ea5ca740c22d6cc9` | `F03` p. 43 (row 734) | Alta | `nevirapina` | `200 mg` / `cápsula` / `None` | `200 mg` / `cápsula ou comprimido` / `None` |
| `occ-6f2dc3eb51dcb3002fe500ae` | `F03` p. 44 (row 741) | Alta | `nifedipino` | `10 mg` / `comprimido` / `None` | `10 mg` / `comprimido ou cápsula` / `None` |
| `occ-10ea7805363b328ab9fe715c` | `F03` p. 44 (row 743) | Alta | `nilotinibe` | `200mg` / `cápsula` / `None` | `200mg` / `cápsula gelatinosa dura` / `None` |
| `occ-ef9c0c6b0d7d85c02a99194d` | `F03` p. 44 (row 744) | Alta | `nimodipino` | `30 mg` / `comprimido` / `None` | `30 mg` / `comprimido ou cápsula` / `None` |
| `occ-545286e595c988da6d6fa2ce` | `F03` p. 44 (row 745) | Alta | `nintedanibe (esilato)` | `100 mg` / `cápsula` / `None` | `100 mg` / `cápsula mole` / `None` |
| `occ-545f8bfb5ef8228756528729` | `F03` p. 44 (row 746) | Alta | `nintedanibe (esilato)` | `150 mg` / `cápsula` / `None` | `150 mg` / `cápsula mole` / `None` |
| `occ-250537e61387b7413515878d` | `F03` p. 45 (row 770) | Alta | `óleo mineral` | `100% (frasco 100 mL)` / `óleo para uso oral` / `None` | `100% (frasco 100 mL)` / `óleo` / `None` |
| `occ-81e33e6df2756e23f52fbe54` | `F03` p. 45 (row 774) | Alta | `ondansetrona` | `8 mg` / `comprimido` / `None` | `8 mg` / `comprimido ou comprimido orodispersível` / `None` |
| `occ-2c4cdd92eecda6cae84b133b` | `F03` p. 45 (row 780) | Alta | `oxaliplatina` | `100 mg` / `pó liofilizado ou solução injetável (frasco-ampola)` / `None` | `100 mg` / `injetável` / `None` |
| `occ-9d77ceb4b7f4108bf1d5cebd` | `F03` p. 46 (row 786) | Alta | `oxicodona` | `10mg` / `comprimido revestido` / `None` | `10mg` / `comprimido revestido de liberação controlada` / `liberação controlada` |
| `occ-8b7776be92835d29edb61b76` | `F03` p. 46 (row 787) | Alta | `oxicodona` | `20mg` / `comprimido revestido` / `None` | `20mg` / `comprimido revestido de liberação controlada` / `liberação controlada` |
| `occ-386c6917918eb996e4015fda` | `F03` p. 46 (row 791) | Média | `pancreatina (lipase + amilase + protease)` | `10.000 UI (150 mg)` / `cápsula com microgrânulos de liberação entérica` / `None` | `10.000 UI (150 mg)` / `cápsula com microgrânulos de liberação entérica` / `liberação entérica` |
| `occ-a9315e6344483d7811612fda` | `F03` p. 46 (row 792) | Média | `pancreatina (lipase + amilase + protease)` | `25.000 UI (300 mg)` / `cápsula com microgrânulos de liberação entérica` / `None` | `25.000 UI (300 mg)` / `cápsula com microgrânulos de liberação entérica` / `liberação entérica` |
| `occ-f0f7223fd5ff5341463b0550` | `F03` p. 46 (row 796) | Alta | `parecoxibe` | `40 mg` / `ampola` / `None` | `40 mg` / `pó liofilizado` / `None` |
| `occ-23f49b4f579fd8993a9a0193` | `F03` p. 47 (row 807) | Alta | `pentoxifilina` | `400 mg` / `comprimido revestido` / `None` | `400 mg` / `comprimido revestido ou comprimido revestido de liberação prolongada` / `liberação prolongada` |
| `occ-79e8c80d96747e291babac5e` | `F03` p. 47 (row 814) | Alta | `pirazinamida` | `150 mg` / `comprimido` / `None` | `150 mg` / `comprimido dispersível` / `None` |
| `occ-c46256c1a904b7e76d88799f` | `F03` p. 47 (row 823) | Alta | `pó para solução básica para hemodiálise (sódio + bicarbonato + cloreto + glicose)` | `98 mEq/L + 35 mEq/L + 63 mEq/L + 1 g/L (bolsa plástica 658 g)` / `pó para solução para hemodiálise` / `None` | `98 mEq/L + 35 mEq/L + 63 mEq/L + 1 g/L (bolsa plástica 658 g)` / `pó para solução básica para hemodiálise` / `None` |
| `occ-59976a0284d33f156df57475` | `F03` p. 49 (row 847) | Alta | `progesterona` | `200mg` / `cápsula` / `None` | `200mg` / `cápsula gelatinosa mole` / `None` |
| `occ-50a9569d873e8956d6b621c9` | `F03` p. 49 (row 864) | Alta | `quetiapina` | `300mg` / `comprimido revestido` / `None` | `300mg` / `comprimido revestido liberação prolongada` / `liberação prolongada` |
| `occ-f208f9b0fbdfa9984f6ae66e` | `F03` p. 52 (row 908) | Média | `rivastigmina` | `18 mg (liberação de 9,5 mg/24h)` / `adesivo transdérmico` / `None` | `18 mg (liberação de 9,5 mg/24h)` / `adesivo transdérmico` / `liberação de 9,5 mg/24h` |
| `occ-924b68401c03c4123a26164e` | `F03` p. 52 (row 909) | Média | `rivastigmina` | `9 mg (liberação de 4,6 mg/24h)` / `adesivo transdérmico` / `None` | `9 mg (liberação de 4,6 mg/24h)` / `adesivo transdérmico` / `liberação de 4,6 mg/24h` |
| `occ-5e613d5a17989804827e439e` | `F03` p. 52 (row 922) | Alta | `sais para reidratação oral (NaCl + KCl + citrato + glicose)` | `3,5 g + 1,5 g + 2,9 g + 20 g (para preparo de 1 L)` / `pó para solução oral` / `None` | `3,5 g + 1,5 g + 2,9 g + 20 g (para preparo de 1 L)` / `pó para preparo de 1 litro de solução` / `None` |
| `occ-b0f807a52a2fdbfaeb4e13c8` | `F03` p. 52 (row 924) | Alta | `salbutamol (sulfato)` | `100 mcg/dose` / `solução aerossol para inalação oral` / `None` | `100 mcg/dose` / `spray ou aerossol para inalação oral` / `None` |
| `occ-b3c9c95e8c9426034db9ca30` | `F03` p. 52 (row 925) | Alta | `salmeterol (xinafoato) + fluticasona (propionato)` | `25 mcg/dose + 125 mcg/dose (120 doses + inalador)` / `solução aerossol para inalação oral` / `None` | `25 mcg/dose + 125 mcg/dose (120 doses + inalador)` / `aerossol para inalação` / `None` |
| `occ-c91b4e24768177e887ed16b6` | `F03` p. 52 (row 926) | Alta | `salmeterol (xinafoato) + fluticasona (propionato)` | `50 mcg/dose + 500 mcg/dose (recipiente dosador strip 60 doses)` / `pó inalatório` / `None` | `50 mcg/dose + 500 mcg/dose (recipiente dosador strip 60 doses)` / `pó para inalação` / `None` |
| `occ-648c45d256d209afe121f04d` | `F03` p. 53 (row 930) | Alta | `selante de fibrina` | `1 mL` / `frasco-ampola` / `None` | `1 mL` / `frasco ampola` / `None` |
| `occ-ea3c3a338bd1aa4a3ff232fd` | `F03` p. 53 (row 940) | Alta | `sevoflurano` | `frasco 250 mL` / `solução para inalação` / `None` | `frasco 250 mL` / `solução inalatória` / `None` |
| `occ-949c15370770ba5bc47c6b8f` | `F03` p. 53 (row 945) | Alta | `simeticona` | `75 mg/mL` / `emulsão ou solução oral` / `None` | `75 mg/mL` / `suspensão oral gotas` / `None` |
| `occ-6c9cca4e2c8bdba3c94bc0bc` | `F03` p. 53 (row 954) | Alta | `solução ácida para hemodiálise` | `K=2,0 mEq/L, Ca=2,5 mEq/L, sem glicose (galão 5 L)` / `solução para hemodiálise` / `None` | `K=2,0 mEq/L, Ca=2,5 mEq/L, sem glicose (galão 5 L)` / `solução ácida p/ hemodiálise` / `None` |
| `occ-ca7f6da1914c760234591b70` | `F03` p. 53 (row 955) | Alta | `solução básica para hemodiálise (bicarbonato de sódio)` | `8,4% (galão 5 L)` / `solução para hemodiálise` / `None` | `8,4% (galão 5 L)` / `solução básica` / `None` |
| `occ-d753bb7d688d15dcce4d3ebe` | `F03` p. 54 (row 958) | Alta | `solução ácida para hemodiálise (sódio + potássio + cálcio + magnésio + cloreto + citrato)` | `40 + 2 + 2,5 + 1 + 47,5 + 0,25 mEq/L (frasco 960 mL)` / `solução para hemodiálise` / `None` | `40 + 2 + 2,5 + 1 + 47,5 + 0,25 mEq/L (frasco 960 mL)` / `solução ácida para hemodiálise` / `None` |
| `occ-e8faaface906ddc31f6763e8` | `F03` p. 54 (row 959) | Alta | `solução ácida para hemodiálise (sódio + potássio + cálcio + magnésio + cloreto + citrato)` | `40 + 2 + 3,5 + 1 + 48,5 + 0,35 mEq/L (frasco 960 mL)` / `solução para hemodiálise` / `None` | `40 + 2 + 3,5 + 1 + 48,5 + 0,35 mEq/L (frasco 960 mL)` / `solução ácida para hemodiálise` / `None` |
| `occ-bfc5211a72cc92599c4d348e` | `F03` p. 54 (row 960) | Alta | `solução ácida para hemodiálise (sódio + potássio + cálcio + magnésio + cloreto + citrato)` | `40 + 3 + 2,5 + 1 + 48,5 + 0,25 mEq/L (frasco 960 mL)` / `solução para hemodiálise` / `None` | `40 + 3 + 2,5 + 1 + 48,5 + 0,25 mEq/L (frasco 960 mL)` / `solução ácida para hemodiálise` / `None` |
| `occ-17e61fe79d55fdc27bd22e6b` | `F03` p. 54 (row 969) | Alta | `sugamadex sódico` | `100 mg/mL` / `solução` / `None` | `100 mg/mL` / `solução injetável` / `None` |
| `occ-bbb51e0359fbce48b9214eae` | `F03` p. 54 (row 976) | Alta | `sulfassalazina` | `500mg` / `comprimido revestido` / `None` | `500mg` / `comprimido revestido de liberação retardada` / `liberação retardada` |
| `occ-cd56b7aab2cff5176b586908` | `F03` p. 54 (row 978) | Alta | `sulfato de zinco heptahidratado` | `17,60 mg/mL` / `solução oral` / `None` | `17,60 mg/mL` / `frasco` / `None` |
| `occ-36b8a9522cb455db12695ff2` | `F03` p. 55 (row 981) | Alta | `suplemento alimentar com múltiplos micronutrientes` | `1 g` / `pó para suspensão oral (envelope)` / `None` | `1 g` / `pó` / `None` |
| `occ-e9d2d51d7ddc1d0a1aad71bb` | `F03` p. 55 (row 989) | Alta | `tacrolimo` | `0,3 mg/g` / `pomada` / `None` | `0,3 mg/g` / `pomada dermatológica` / `None` |
| `occ-4b4377f10b7de9c013f30a75` | `F03` p. 55 (row 990) | Alta | `tacrolimo` | `1 mg/g` / `pomada` / `None` | `1 mg/g` / `pomada dermatológica` / `None` |
| `occ-9995b8de9d655e0350ca8c9c` | `F03` p. 55 (row 993) | Alta | `tafamidis` | `61 mg` / `cápsula` / `None` | `61 mg` / `cápsula mole` / `None` |
| `occ-283931a2d704751b9514b970` | `F03` p. 55 (row 1002) | Alta | `tenecteplase` | `40mg` / `pó liofilizado para solução injetável` / `None` | `40mg` / `pó liofilizado` / `None` |
| `occ-ca70d5224391598621048935` | `F03` p. 56 (row 1015) | Alta | `terlipressina (acetato)` | `1 mg` / `pó liofilizado injetável` / `None` | `1 mg` / `pó liofilizado injetável ou solução injetável` / `None` |
| `occ-8310fcb8a7032daee5d6784f` | `F03` p. 57 (row 1021) | Alta | `tioridazina (cloridrato)` | `200 mg` / `comprimido` / `None` | `200 mg` / `comprimido liberação prolongada` / `liberação prolongada` |
| `occ-23af74a5e4a3d7d45c4575ec` | `F03` p. 57 (row 1028) | Alta | `tobramicina` | `300 mg` / `solução` / `None` | `300 mg` / `solução para inalação` / `None` |
| `occ-19885f1caaa3a629474d735f` | `F03` p. 57 (row 1034) | Alta | `toxina botulinica tipo a de clostridium botulinum` | `500u` / `solução injetável` / `None` | `500u` / `pó liofilizado p/ solução injetável` / `None` |
| `occ-119b8a45494057f6d402f1f8` | `F03` p. 58 (row 1044) | Alta | `triptorrelina (embonato)` | `22,5 mg` / `pó liofilizado para suspensão injetável` / `None` | `22,5 mg` / `pó liofilizado para suspensão injetável de liberação prolongada` / `liberação prolongada` |
| `occ-b876bad65fcf7b57f2c2cf3e` | `F03` p. 58 (row 1048) | Alta | `umeclidínio (brometo) + vilanterol (trifenatato)` | `62,5 mcg/dose + 25 mcg/dose (recipiente dosador strip 30 doses)` / `pó inalatório` / `None` | `62,5 mcg/dose + 25 mcg/dose (recipiente dosador strip 30 doses)` / `pó inalante` / `None` |
| `occ-ebcde0ce9f6a22859deb5f6f` | `F03` p. 58 (row 1049) | Alta | `upadacitinibe` | `15mg` / `comprimido revestido` / `None` | `15mg` / `comprimido revestido de liberação prolongada` / `liberação prolongada` |
| `occ-e38e5e5d52281fc96d41d9da` | `F03` p. 58 (row 1054) | Alta | `valproato de sodio` | `250 mg` / `comprimido` / `None` | `250 mg` / `comprimido ou cápsula` / `None` |
| `occ-1d7793fa89c2c7b25d439b83` | `F03` p. 58 (row 1055) | Alta | `valproato de sodio` | `250 mg/5 mL` / `solução oral` / `None` | `250 mg/5 mL` / `solução oral ou xarope` / `None` |
| `occ-f6ea89da0be78741399fc8f3` | `F03` p. 58 (row 1059) | Alta | `vaselina sólida (petrolato)` | `100 %` / `pomada (bisnaga ou tubo)` / `None` | `100 %` / `bisnaga ou tubo` / `None` |

---

## 6. Procedimento 8 — Pendências e Requisitos para Aprovação Final (`pending_review` → `approved`)

O novo release `data/releases/corpus-consolidado-v3-revisao-2026-11-10` foi mantido com `status: "pending_review"` em `release.json`. Para que o status seja promovido a `approved`, uma pessoa habilitada (revisor farmacêutico/clínico responsável pela governança do corpus) deve registrar a revisão explícita contendo **responsável, data, escopo e decisão sobre as 4 ressalvas arquiteturais abaixo**:

1. **Ressalva R1 (Média) — Linha 987 em branco no PDF da `F03` (`occ-dd3666cce6867d6246aae72f` / `evidence-dd3666cce6867d6246aae72f`, p. 55)**:
   - No PDF oficial da REME-DF, a linha numerada `987.` está completamente em branco (`raw_text: "987."`). Ela é mantida em `occurrences.jsonl` (`active_ingredient: "[linha 987 em branco no PDF]"`) para preservar a invariante de sequência primária `1..1078` exigida pelos testes do projeto (`tests/unit/test_corpus.py`), mas gera uma entrada em `evidencias.jsonl` e `catalog.jsonl`.
   - **Decisão requerida no sign-off**: autorizar filtro de exclusão de `occ-dd3666cce6867d6246aae72f` na etapa de indexação/recuperação ou autorizar sua remoção da publicação de evidências.
2. **Ressalva R2 (Média) — Ausência de `context.indication` no texto de 37 das 41 evidências de `F04` (`evidencias.jsonl`)**:
   - Apenas 4 evidências de `F04` (linhas 29, 40, 41 e 42) trazem a indicação no `text`, enquanto as outras 37 guardam a indicação somente em `occurrences.jsonl` (`context.indication`).
   - **Decisão requerida no sign-off**: definir se o indexador consumirá `occurrences.jsonl` + `evidencias.jsonl` em conjunto ou se o esquema de `evidencias.jsonl` deve incluir o campo `context`.
3. **Ressalva R3 (Média) — Intercalação multicoluna no `raw_text`/`text` de `F03`**:
   - Devido ao recorte de linha inteira (`x=36..562`), o `text` bruto de linhas multilinha em `F03` intercala palavras de `DESCRIÇÃO`, `GRUPO FARMACOLÓGICO` e `FARMÁCIA`.
   - **Decisão requerida no sign-off**: validar que o pipeline de recuperação utilizará os campos estruturados limpos (`active_ingredient`, `strength`, `form`, `release_characteristic`) ao lado do `text` bruto.
4. **Ressalva R4 (Baixa) — 27 insumos do Anexo B/C da `F01` tipados como `item_type: "medicine"`**:
   - **Decisão requerida no sign-off**: confirmar se os 27 itens com `context.component` em `{"Insumos (Básico)", "Insumos (Estratégico)"}` devem permanecer como `item_type: "medicine"` ou migrar para `item_type: "supply"` em uma próxima revisão de esquema.
