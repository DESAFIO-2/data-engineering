# Diagnóstico de Colisões de Identidade e Chunks Duplicados (v9 -> v10)

**Gerado em:** 2026-11-13  
**Release analisado (somente leitura, congelado):** `corpus-consolidado-v9-aprovado-2026-11-12`

> [!NOTE]
> Este relatório foi gerado de forma determinística a partir de `data/releases/corpus-consolidado-v9-aprovado-2026-11-12` sem alterar hashes nem arquivos da release congelada `v9`.

## 1. Resumo Executivo

| Indicador no Corpus v9 | Contagem | Resolução Aplicada / Proposta |
|---|---:|---|
| Evidências totais (`evidencias.jsonl`) | 2114 | — |
| Pares de texto de chunk duplicado na receita `one-evidence-v1` | 20 pares (40 evidências) | **Resolvido em código no Dia 2** com `CHUNK_RECIPE_V2` (`one-evidence-v2` inclui proveniência `p. <página>, item <linha>`), resultando em **0 duplicatas** em todas as 2114 evidências. |
| Registros no catálogo (`catalog.jsonl`) | 1859 | — |
| Pares em colisão sob `normalize()` exato | 78 | Candidatos a reconciliação na futura release `v10`. |
| Pares em colisão sob `ingredient_key()` + `normalize()` | 79 | Inclui 1 par extra por ordem de sal (`cloridrato de metformina` vs `metformina (cloridrato)`). |
| Pares em colisão incluindo concentração compactada (`1 g` vs `1g`) | 80 | Conjunto completo recomendado para deduplicação determinística antes da `v10`. |

## 2. Chunks Duplicados na `one-evidence-v1` (20 pares em F03)

Todos os 20 pares duplicados em `v9` são medicamentos da REME-DF (`F03`) que compartilham princípio ativo, concentração, forma e `description_cell`, mas ocupam **linhas/itens distintos da tabela** (por exemplo, `Uso hospitalar` vs `Farmácia do Componente Especializado`). Com a receita versionada `one-evidence-v2` em `src/rag/consolidated.py`, a linha `Proveniência: F03 (p. <página>, item <linha>).` desambigua os 20 pares preservando compatibilidade retroativa com os manifestos `v1` congelados (`v5` a `v9`).

| # | Princípio Ativo | Concentração | Forma | Proveniência Distinta | IDs de Evidência |
|---:|---|---|---|---|---|
| 1 | albumina humana | 20 % | solução injetável | p. 13, itens 33 vs 34 | `evidence-0bebc51066d210b975075854` / `evidence-4298b9e84008e4ddde16417b` |
| 2 | alfainterferona 2B | 5.000.000 UI | injetável | p. 14, itens 51 vs 52 | `evidence-44698413338e0779fa2bebcc` / `evidence-75d1dfdaeeba4e72f6b970a1` |
| 3 | cabergolina | 0,5mg | comprimido | p. 19, itens 181 vs 182 | `evidence-5ddae96dc6f046073c3ace41` / `evidence-c42c31ad4073a025f4cee0ce` |
| 4 | clozapina | 100mg | comprimido | p. 23, itens 282 vs 283 | `evidence-4c46b8e75774a598600a043c` / `evidence-886c9b8b28c63fdb80ddb107` |
| 5 | desmopressina | 0,1 mg/mL (frasco 2,5 mL) | spray nasal | p. 26, itens 340 vs 341 | `evidence-51ff8fa4d4c886e6e8c742b0` / `evidence-73c991d8ed35e115797070c8` |
| 6 | dupilumabe | 200 mg | solução injetável | p. 27, itens 384 vs 386 | `evidence-e97e73e297210b959724c77e` / `evidence-4451710e99473ccd9dabe1cd` |
| 7 | dupilumabe | 300mg | solução injetável | p. 28, itens 385 vs 387 | `evidence-8207632f43cae3534ba837b6` / `evidence-6278f29494bdc026f9e44a39` |
| 8 | enoxaparina sódica | 40 mg | solução injetável | p. 28, itens 403 vs 409 | `evidence-b8aa797501d9a0a02e0e2da6` / `evidence-3cdd6a52cc4d508ed52a4c65` |
| 9 | enoxaparina sódica | 60 mg | solução injetável | p. 28, itens 404 vs 405 | `evidence-0741375b2310786d862d43f0` / `evidence-9428ff389ab37c0973e946f8` |
| 10 | filgrastim | 300mcg | solução injetável | p. 30, itens 447 vs 448 | `evidence-030ab58db7b48a7fb4d22148` / `evidence-252f7b623c671cd6fdce853b` |
| 11 | insulina análoga de ação ultra rápida | 100 UI/mL | solução injetável | p. 35, itens 553 vs 554 | `evidence-af73006fcd56eaad0fb348d6` / `evidence-db88ea210ce57c6a736dbfb3` |
| 12 | insulina humana NPH | 100 UI/mL | suspensão injetável | p. 36, itens 561 vs 562 | `evidence-888195db1421193991ffdab1` / `evidence-297a8ec2ec060ef8d2d38cbf` |
| 13 | metotrexato | 2,5mg | comprimido | p. 41, itens 673 vs 674 | `evidence-70f2442b0cde8ed0ca86f675` / `evidence-f10b6deee70be4400aeeeeb0` |
| 14 | misoprostol | 200 mcg | comprimido vaginal | p. 42, itens 704 vs 705 | `evidence-2d805034f4e6e3d946c32e7c` / `evidence-b53f1771a09b6507cac663c4` |
| 15 | misoprostol | 25 mcg | comprimido vaginal | p. 42, itens 706 vs 707 | `evidence-2380509ac71a82f85db235b7` / `evidence-d14aa21adf3192764814dfae` |
| 16 | quetiapina | 100mg | comprimido | p. 49, itens 858 vs 859 | `evidence-ab3ca864b51b0f226a4d0b44` / `evidence-d8d853e4f0bfd52ef812c051` |
| 17 | quetiapina | 200mg | comprimido | p. 49, itens 860 vs 861 | `evidence-03c0e58bd3f33a1c9b4cd0d5` / `evidence-374ae279682361790afa89c2` |
| 18 | quetiapina | 25mg | comprimido | p. 49, itens 862 vs 863 | `evidence-0c2f075d3f830e3eb57848d6` / `evidence-f257d80a8d8dee0df3fffe15` |
| 19 | sildenafila (citrato) | 20 mg | comprimido revestido | p. 53, itens 941 vs 942 | `evidence-21efd1c21fb1548480f4ba64` / `evidence-f8292d7e350246467c003c14` |
| 20 | ziprasidona | 40 mg | cápsula | p. 59, itens 1075 vs 1076 | `evidence-e3baa79210dbcace4ba7acd8` / `evidence-9e6e8ee3e792d8cefbec735e` |

## 3. Plano de Reconciliação das Colisões de Catálogo para a Release v10 (80 pares)

Todas as colisões abaixo envolvem apenas pares (tamanho máximo de grupo = 2), tipicamente entre `F01` (RENAME, com espaço em `0,25 mcg`, acento em `isotretinoína`) e `F03` (REME-DF, sem espaço em `0,25mcg` ou sem acento em `isotretinoina`). Na preparação da `v10`:

1. Normalizar chave canônica de identidade no consolidador com `ingredient_key(active_ingredient)` + unidade espaçada canônica em `strength` (`normalize(strength)` + separação número/unidade inclusive `g`, `UI`, `%`, `mL`).
2. Fundir `source_ids` em um único `medicine_id` canônico e remapear `medicine_id` nas ocorrências/evidências correspondentes sem perder proveniência textual original.
3. Validar 0 colisões sob a chave canônica antes de gerar os novos chunks com `one-evidence-v2` e vetorizar.

| # | Critério | Causa Principal | Registro A | Registro B |
|---:|---|---|---|---|
| 1 | ``normalize()`` | Espaçamento em concentração | `med-405caba5bc63a6108c7017d7` (abatacepte / 125 mg/mL / solução injetável / F01) | `med-aae015db69bd70a50a9adc96` (abatacepte / 125mg/mL / solução injetável / F03) |
| 2 | ``normalize()`` | Espaçamento em concentração | `med-f78b91bc0f892743c06f88c8` (acitretina / 10 mg / cápsula / F01) | `med-a04bde5878ea3252810e4b82` (acitretina / 10mg / cápsula / F03) |
| 3 | ``normalize()`` | Espaçamento em concentração | `med-970bf4554e043194e231a7e5` (acitretina / 25 mg / cápsula / F01) | `med-ead77d5f36a6bcd4bde57680` (acitretina / 25mg / cápsula / F03) |
| 4 | ``normalize()`` | Espaçamento em concentração | `med-d870cf77969fb0cc1af604df` (adalimumabe / 40 mg / solução injetável / F01) | `med-7910937da04d575c44d61fb4` (adalimumabe / 40mg / solução injetável / F03) |
| 5 | ``normalize()`` | Acentuação/pontuação no princípio ativo | `med-a1fa49ec2dfc874e69e3251e` (arteméter + lumefantrina / 20 mg + 120 mg / comprimido / F01) | `med-5f1b0ab09065e08e76513882` (artemeter + lumefantrina / 20 mg + 120 mg / comprimido / F03) |
| 6 | ``normalize()`` | Espaçamento em concentração | `med-7ba52348003a64c23004cf67` (atenolol / 100 mg / comprimido / F01) | `med-2b82a18b29314aabc3c15867` (atenolol / 100mg / comprimido / F03) |
| 7 | ``normalize()`` | Espaçamento em concentração | `med-2f74c244d8e62d2f5083ccdb` (azatioprina / 50 mg / comprimido / F01) | `med-62b99a7a166584d34604dc84` (azatioprina / 50mg / comprimido / F03) |
| 8 | ``normalize()`` | Espaçamento em concentração | `med-27af06578013c30dff85dc2d` (azitromicina / 250 mg / comprimido / F01) | `med-cdc2fecdcf3fceffecdd0ef7` (azitromicina / 250mg / comprimido / F03) |
| 9 | ``normalize()`` | Espaçamento em concentração | `med-e2fb3ef5820acfccd72abeca` (bedaquilina / 100 mg / comprimido / F01) | `med-f280d3b2a20c85afb96b5b9f` (bedaquilina / 100mg / comprimido / F03) |
| 10 | ``normalize()`` | Acentuação/pontuação no princípio ativo | `med-729d51f075316c6966bcbdb5` (bupivacaína (cloridrato) / 5 mg/mL / solução injetável / F03) | `med-8903be7c79ddff63da9848a1` (bupivacaina (cloridrato) / 5 mg/mL / solução injetável / F03) |
| 11 | ``normalize()`` | Espaçamento em concentração | `med-0a2b0a3819d03b0b49e1a088` (cabergolina / 0,5 mg / comprimido / F01) | `med-3c60fbef6f105cc2ffae9d99` (cabergolina / 0,5mg / comprimido / F03) |
| 12 | ``normalize()`` | Espaçamento em concentração | `med-b78926c606d53702b1bb8b07` (calcitriol / 0,25 mcg / cápsula / F01) | `med-26b6329dc583e533b4cd1529` (calcitriol / 0,25mcg / cápsula / F03) |
| 13 | ``compact_strength`` | Espaçamento em concentração | `med-020abbf9e9933c089c342c8b` (ceftriaxona / 1 g / pó para solução injetável / F01) | `med-3c5507f836260154e8bd4836` (ceftriaxona / 1g / pó para solução injetável / F03) |
| 14 | ``normalize()`` | Espaçamento em concentração | `med-2b827a39a5950f1dca9c640c` (ceftriaxona / 500 mg / pó para solução injetável / F01) | `med-76c17850a7e70af44d8a1556` (ceftriaxona / 500mg / pó para solução injetável / F03) |
| 15 | ``normalize()`` | Espaçamento em concentração | `med-bf6dee0143b1d408f3e4aba4` (certolizumabe pegol / 200 mg/mL / solução injetável / F01) | `med-a3eb9cf3bc576ea376aacc98` (certolizumabe pegol / 200mg/mL / solução injetável / F03) |
| 16 | ``normalize()`` | Espaçamento em concentração | `med-06978a354a8272fa72c7c9e4` (ciclosporina / 100 mg / cápsula / F01) | `med-acfdad1235a6a1da65ea0b4a` (ciclosporina / 100mg / cápsula / F03) |
| 17 | ``normalize()`` | Espaçamento em concentração | `med-9b111ef34fa81cfa4c5008a7` (ciclosporina / 25 mg / cápsula / F01) | `med-1f40e2e392f13b80a4facd57` (ciclosporina / 25mg / cápsula / F03) |
| 18 | ``normalize()`` | Espaçamento em concentração | `med-afb12d7653fc0a7e59cd9a74` (ciprofibrato / 100 mg / comprimido / F01) | `med-acf48f0bcb058843d9104c18` (ciprofibrato / 100mg / comprimido / F03) |
| 19 | ``normalize()`` | Espaçamento em concentração | `med-0187315fff1c4b826a7efde4` (clobazam / 10 mg / comprimido / F01) | `med-299e8532899f162ddef73ed5` (clobazam / 10mg / comprimido / F03) |
| 20 | ``normalize()`` | Espaçamento em concentração | `med-002ef83c0f39ef5512df2212` (clofazimina / 100 mg / cápsula / F01) | `med-f3ecbf59e6eab24eb5d1a08b` (clofazimina / 100mg / cápsula / F03) |
| 21 | ``normalize()`` | Espaçamento em concentração | `med-88b51fa0006a4bb2ca5c5813` (clofazimina / 50 mg / cápsula / F01) | `med-0f0e7a6eedd53df5be94fc3b` (clofazimina / 50mg / cápsula / F03) |
| 22 | ``ingredient_key()`` | Ordem de sal / notação química | `med-1b798f53028c21c756ee7163` (cloridrato de metformina / 850 mg / comprimido / F01) | `med-bdd705733bfb24fb04aa974e` (metformina (cloridrato) / 850 mg / comprimido / F03) |
| 23 | ``normalize()`` | Espaçamento em concentração | `med-c749c012eda4076b68687c07` (clozapina / 100 mg / comprimido / F01) | `med-58d027ea2db072ae214b3616` (clozapina / 100mg / comprimido / F03) |
| 24 | ``normalize()`` | Espaçamento em concentração | `med-eaebf1bc4192cb2c036b01a9` (clozapina / 25 mg / comprimido / F01) | `med-97b317ed6f466e36e1a08862` (clozapina / 25mg / comprimido / F03) |
| 25 | ``normalize()`` | Espaçamento em concentração | `med-0373401e07447bb095336d69` (dapsona / 100 mg / comprimido / F01) | `med-59b8cf0d209f2e54f7af455b` (dapsona / 100mg / comprimido / F03) |
| 26 | ``normalize()`` | Espaçamento em concentração | `med-c392199167ac6ba44f258d82` (delamanida / 50 mg / comprimido / F01) | `med-200bfc848ad194814f423cdc` (delamanida / 50mg / comprimido / F03) |
| 27 | ``normalize()`` | Espaçamento em concentração | `med-995fe1b4ec0ef8f4cb3cef12` (desmopressina / 4 mcg/mL / solução injetável / F03) | `med-f0fc07188b32d12a311e662e` (desmopressina / 4mcg/mL / solução injetável / F03) |
| 28 | ``normalize()`` | Espaçamento em concentração | `med-fd0a479868862cec2a221435` (dipirona / 500 mg / comprimido / F01) | `med-757419805f67a098c2e0b50e` (dipirona / 500mg / comprimido / F03) |
| 29 | ``normalize()`` | Espaçamento em concentração | `med-779e4f3a7e8210419cd5835b` (dipirona / 500 mg/mL / solução oral / F01) | `med-eb61f7637ac2bdd8492eab28` (dipirona / 500 mg / mL / solução oral / F03) |
| 30 | ``normalize()`` | Espaçamento em concentração | `med-c612864c35012ca22c1f88a6` (etossuximida / 50 mg/mL / xarope / F01) | `med-2c7dbd200c3760730542eff8` (etossuximida / 50mg/mL / xarope / F03) |
| 31 | ``normalize()`` | Espaçamento em concentração | `med-323873bd4debc57c22934d79` (etravirina / 200 mg / comprimido / F01) | `med-921519fa84c623f58ffae6b9` (etravirina / 200mg / comprimido / F03) |
| 32 | ``normalize()`` | Espaçamento em concentração | `med-b58ba7c7aa0ce5d8e6f12cdf` (everolimo / 0,5 mg / comprimido / F01) | `med-3f6c00307817d044bb8e013f` (everolimo / 0,5mg / comprimido / F03) |
| 33 | ``normalize()`` | Espaçamento em concentração | `med-f504e6bd1ac678cbb3dd96ef` (everolimo / 0,75 mg / comprimido / F01) | `med-b23331038f9b7784b6a0e494` (everolimo / 0,75mg / comprimido / F03) |
| 34 | ``normalize()`` | Espaçamento em concentração | `med-cbc8e8e725e16f835f344c22` (everolimo / 1 mg / comprimido / F01) | `med-479e94d1f230c599a7b122c3` (everolimo / 1mg / comprimido / F03) |
| 35 | ``normalize()`` | Acentuação/pontuação no princípio ativo | `med-30c418efd2e5ed52eb6c8dfc` (fenitoína / 100 mg / comprimido / F01) | `med-7781a8353ae0b97ef9c88689` (fenitoina / 100 mg / comprimido / F03) |
| 36 | ``normalize()`` | Acentuação/pontuação no princípio ativo | `med-e4eb2bcbcec2f95cba00c3aa` (fenitoína / 50 mg/mL / solução injetável / F01) | `med-f4aa0ea8b460b812e4b066ad` (fenitoina / 50 mg/mL / solução injetável / F03) |
| 37 | ``normalize()`` | Espaçamento em concentração | `med-965c581d8dcdc2187071bad6` (filgrastim / 300 mcg / solução injetável / F01) | `med-61296d8ec75f3592cb0d2f19` (filgrastim / 300mcg / solução injetável / F03) |
| 38 | ``normalize()`` | Espaçamento em concentração | `med-280a79947c8de1314a6db29f` (finasterida / 5 mg / comprimido / F01) | `med-5c95ff386f3d4a4d800199f3` (finasterida / 5mg / comprimido / F03) |
| 39 | ``normalize()`` | Espaçamento em concentração | `med-28e3b3b4bf0ea4b4df35bd67` (flucitosina / 500 mg / cápsula / F01) | `med-20795daba31db8a505f05646` (flucitosina / 500mg / cápsula / F03) |
| 40 | ``normalize()`` | Espaçamento em concentração | `med-6c64e29b803b8b434b9f3d5d` (gabapentina / 300 mg / cápsula / F01) | `med-40f4675f1c31f27dc71ad4d4` (gabapentina / 300mg / cápsula / F03) |
| 41 | ``normalize()`` | Espaçamento em concentração | `med-3ae531a28b7a3160317d6be2` (gabapentina / 400 mg / cápsula / F01) | `med-1d3f81399ef4a138bda453d1` (gabapentina / 400mg / cápsula / F03) |
| 42 | ``normalize()`` | Espaçamento em concentração | `med-f52fc22c3a9b2dbe13c337e9` (genfibrozila / 600 mg / comprimido / F01) | `med-7fc90af26a33504c50ecc505` (genfibrozila / 600mg / comprimido / F03) |
| 43 | ``normalize()`` | Espaçamento em concentração | `med-8f0948d47f39539b3cdfc196` (glecaprevir + pibrentasvir / 100 mg + 40 mg / comprimido / F01) | `med-f94d94408b31c059eea17bb8` (glecaprevir + pibrentasvir / 100mg + 40mg / comprimido / F03) |
| 44 | ``normalize()`` | Espaçamento em concentração | `med-6e77a2f47bb1e5947a215da9` (ibuprofeno / 50 mg/mL / suspensão oral / F01) | `med-94d7b6fb992d54031e24406c` (ibuprofeno / 50mg/mL / suspensão oral / F03) |
| 45 | ``normalize()`` | Espaçamento em concentração | `med-088dc8b6c77ef9a4a4269fac` (isoniazida / 100 mg / comprimido / F01) | `med-fab8798ae2ac107f4f922709` (isoniazida / 100mg / comprimido / F03) |
| 46 | ``normalize()`` | Espaçamento em concentração | `med-05dd747ddc3fa4eed7f016a1` (isoniazida / 300 mg / comprimido / F01) | `med-98989a91abd1e909840afaff` (isoniazida / 300mg / comprimido / F03) |
| 47 | ``normalize()`` | Acentuação/pontuação no princípio ativo | `med-ea5cb70b627f3c724fc46542` (isotretinoína / 20 mg / cápsula / F01) | `med-b1c1c19f9e58953a05bdd2d6` (isotretinoina / 20mg / cápsula / F03) |
| 48 | ``normalize()`` | Espaçamento em concentração | `med-facdec455ab37477ce764d97` (lamotrigina / 100 mg / comprimido / F01) | `med-fe434f7df5edeb221e949056` (lamotrigina / 100mg / comprimido / F03) |
| 49 | ``normalize()`` | Espaçamento em concentração | `med-b8336f7ce8a541bdb82e7df6` (lamotrigina / 25 mg / comprimido / F01) | `med-63eb65086c222e5bf22d13ce` (lamotrigina / 25mg / comprimido / F03) |
| 50 | ``normalize()`` | Espaçamento em concentração | `med-85d051b67724980b65967975` (leflunomida / 20 mg / comprimido / F01) | `med-7e9eb6cc0eb859cc91a83efb` (leflunomida / 20mg / comprimido / F03) |
| 51 | ``normalize()`` | Espaçamento em concentração | `med-7e6c7e495b76d68914d9eb4a` (levetiracetam / 100 mg/mL / solução oral / F01) | `med-9f4303f6a40899c6bf423dd9` (levetiracetam / 100mg/mL / solução oral / F03) |
| 52 | ``normalize()`` | Espaçamento em concentração | `med-6ac405b6d034f2045a0c90e8` (levofloxacino / 500 mg / comprimido / F01,F03) | `med-9e76f4d70c6d6dea44b36b2d` (levofloxacino / 500mg / comprimido / F03) |
| 53 | ``normalize()`` | Espaçamento em concentração | `med-45ee0ad1ceee5478d5966252` (mesalazina / 500 mg / comprimido de liberação prolongada / F01) | `med-02669fb819b7469af7d1fa7f` (mesalazina / 500mg / comprimido de liberação prolongada / F03) |
| 54 | ``normalize()`` | Espaçamento em concentração | `med-c0c98ec2206900cd45b4fe5b` (metotrexato / 2,5 mg / comprimido / F01) | `med-302c2940cbfdf7f28c6f76f0` (metotrexato / 2,5mg / comprimido / F03) |
| 55 | ``normalize()`` | Espaçamento em concentração | `med-c62b2d0b632937c4a13dcd6f` (metronidazol / 250 mg / comprimido / F01) | `med-a853aa922b5cd03842927e89` (metronidazol / 250mg / comprimido / F03) |
| 56 | ``normalize()`` | Espaçamento em concentração | `med-1047d1b9dd2c10de7d2dccf6` (micofenolato de mofetila / 500 mg / comprimido / F01) | `med-61c97fc806b241fa2397466c` (micofenolato de mofetila / 500mg / comprimido / F03) |
| 57 | ``normalize()`` | Espaçamento em concentração | `med-9bb405052350144957f5b39e` (nevirapina / 10 mg/mL / suspensão oral / F01,F03) | `med-c4eb75487bcae2a7ff2f4d5f` (nevirapina / 10mg/mL / suspensão oral / F03) |
| 58 | ``normalize()`` | Acentuação/pontuação no princípio ativo | `med-aa3806a40c83789c44494487` (nitrofurantoína / 100 mg / cápsula / F01) | `med-92c00eed4139a7086240d64b` (nitrofurantoina / 100 mg / cápsula / F03) |
| 59 | ``normalize()`` | Acentuação/pontuação no princípio ativo | `med-e3f3ad05217b6660d3d02e3f` (nitrofurantoína / 5 mg/mL / suspensão oral / F01) | `med-1b23ea098c3f2e0a113d96dc` (nitrofurantoina / 5 mg/mL / suspensão oral / F03) |
| 60 | ``normalize()`` | Espaçamento em concentração | `med-3972e4b584e3a6d29afff629` (ofloxacino / 400 mg / comprimido / F01) | `med-28f8aaf58f22c2de0dee1816` (ofloxacino / 400mg / comprimido / F03) |
| 61 | ``normalize()`` | Espaçamento em concentração | `med-b9862ef67aa2edc4f84b7597` (olanzapina / 10 mg / comprimido / F01) | `med-adf8d5f0ffb7d88bdb58b883` (olanzapina / 10mg / comprimido / F03) |
| 62 | ``normalize()`` | Espaçamento em concentração | `med-1e674ac8e4be904a6b837e3e` (omeprazol / 20 mg / cápsula / F01) | `med-f4a777cb6dc9de1fb09877a8` (omeprazol / 20mg / cápsula / F03) |
| 63 | ``normalize()`` | Espaçamento em concentração | `med-fb8a072bc356437b480bf65b` (pirazinamida / 500 mg / comprimido / F01) | `med-580021af8476e320bfe10bc7` (pirazinamida / 500mg / comprimido / F03) |
| 64 | ``normalize()`` | Espaçamento em concentração | `med-222020e3b631c11910c2cf96` (pirimetamina / 25 mg / comprimido / F01) | `med-454c07044ce3382517674618` (pirimetamina / 25mg / comprimido / F03) |
| 65 | ``normalize()`` | Espaçamento em concentração | `med-6cb00584c44d21cb597d5aff` (praziquantel / 600 mg / comprimido / F01) | `med-a1a07fb489712e617a8bf9fb` (praziquantel / 600mg / comprimido / F03) |
| 66 | ``normalize()`` | Espaçamento em concentração | `med-6a8e4cbd2a45a23ed2aa5afc` (pretomanida / 200 mg / comprimido / F01) | `med-97e3754364a101bdfab3fa79` (pretomanida / 200mg / comprimido / F03) |
| 67 | ``normalize()`` | Espaçamento em concentração | `med-4fba79df5b8e26d1c1f3b185` (ribavirina / 250 mg / cápsula / F01) | `med-d716cc471755e84b7509cc2f` (ribavirina / 250mg / cápsula / F03) |
| 68 | ``normalize()`` | Espaçamento em concentração | `med-3000bf8f237cc9bec01bcf7d` (rifampicina / 300 mg / cápsula / F01) | `med-4d6553ade1988627f78b367d` (rifampicina / 300mg / cápsula / F03) |
| 69 | ``normalize()`` | Espaçamento em concentração | `med-35bc91d53aab8a454e525633` (rifapentina / 150 mg / comprimido / F01) | `med-625f317c2b9585c50d41d341` (rifapentina / 150mg / comprimido / F03) |
| 70 | ``normalize()`` | Espaçamento em concentração | `med-95bbd1048bc6d314fe09bf86` (riluzol / 50 mg / comprimido / F01) | `med-866e1a85f50cf19da86de731` (riluzol / 50mg / comprimido / F03) |
| 71 | ``normalize()`` | Espaçamento em concentração | `med-3ea3fd76303596d4b1f27020` (risperidona / 1 mg/mL / solução oral / F01) | `med-b4974c181213908c53c99b2e` (risperidona / 1mg/mL / solução oral / F03) |
| 72 | ``normalize()`` | Espaçamento em concentração | `med-56185fbe2540cef26c699818` (rituximabe / 500 mg / solução injetável / F03) | `med-0ba54a08db566b65c74bda7d` (rituximabe / 500mg / solução injetável / F03) |
| 73 | ``normalize()`` | Espaçamento em concentração | `med-2601315748f92c129a091efd` (sofosbuvir / 400 mg / comprimido / F01) | `med-737e6f708880481a9d20e143` (sofosbuvir / 400mg / comprimido / F03) |
| 74 | ``normalize()`` | Espaçamento em concentração | `med-d9ec903caae2677cb847c8a7` (sulfadiazina / 500 mg / comprimido / F01) | `med-cfc760a7cdf946803f9a7cba` (sulfadiazina / 500mg / comprimido / F03) |
| 75 | ``normalize()`` | Espaçamento em concentração | `med-59641ab1b2804a6bc7612521` (tacrolimo / 1 mg / cápsula / F01) | `med-044570d62914f92261629551` (tacrolimo / 1mg / cápsula / F03) |
| 76 | ``normalize()`` | Espaçamento em concentração | `med-9acb59a3c0391b1dbcc40b8c` (tacrolimo / 5 mg / cápsula / F01) | `med-5cb7581badbaf71905691ef1` (tacrolimo / 5mg / cápsula / F03) |
| 77 | ``normalize()`` | Espaçamento em concentração | `med-fed73c706d734409e79fd194` (tafamidis meglumina / 20 mg / cápsula / F01) | `med-c3769c7b9143d00defdbb1d7` (tafamidis meglumina / 20mg / cápsula / F03) |
| 78 | ``normalize()`` | Espaçamento em concentração | `med-4d1adafb58035b8a129dac93` (terizidona / 250 mg / cápsula / F01) | `med-4093d20f921165aa523ba3c0` (terizidona / 250mg / cápsula / F03) |
| 79 | ``normalize()`` | Espaçamento em concentração | `med-8360fe29d0752e60d21b8f00` (ustequinumabe / 45 mg / solução injetável / F01) | `med-cb59036159d448f88b7f9a53` (ustequinumabe / 45mg / solução injetável / F03) |
| 80 | ``normalize()`` | Acentuação/pontuação no princípio ativo | `med-dc17d4a75a9682b920730749` (valproato de sódio / 500 mg / comprimido / F01) | `med-6046a40f546f41a927814617` (valproato de sodio / 500 mg / comprimido / F03) |
