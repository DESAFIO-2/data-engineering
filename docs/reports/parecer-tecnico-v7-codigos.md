# Revisão técnica das quatro correções de código F03 na v7

**Data:** 11/11/2026  
**Escopo:** quatro linhas `corrigir_release` da planilha `v6-source-alignment-review.csv`; códigos da tabela principal da REME-DF de 29/10/2026.  
**Resultado técnico:** correções conferidas. **Status de publicação:** `pending_review`.

| Ocorrência | PDF | Item | Códigos visíveis na célula da fonte e publicados na v7 |
| --- | ---: | ---: | --- |
| `occ-a4dfc9d697002029f013cfe2` | p. 13 | 25 | `MS19578, MS38515, MS38516, MS010` |
| `occ-1b4b1af040274b1a3aa0ea9f` | p. 30 | 426 | `MS21833, MS38518` |
| `occ-9273767426e34db70790ce77` | p. 35 | 552 | `MS648, MS38519` |
| `occ-476afabb60223471ac3a02d8` | p. 52 | 907 | `MS38524, MS38520, MS38521` |

As quatro células foram inspecionadas em renderização das páginas do PDF congelado F03. A extração textual independente mostrou os mesmos códigos em linhas separadas. A comparação estrutural de `occurrences.jsonl` v6 → v7 mostrou somente quatro alterações, todas no campo `source_code`, com valores idênticos aos da planilha de revisão. O verificador de release passou para v6 e v7; o manifesto da v6 conserva o SHA-256 `5f0709aa18feb2b9a9fa46bd307100574ddc5541a1db051d9ce6946418575f51`.

A nova comparação fonte → v7 apontou **zero diferenças de código**. As 205 diferenças restantes são exatamente as 205 linhas marcadas `aceitar_normalizacao` na planilha; esta inspeção visual se limita às quatro correções acima e **não reavalia visualmente cada uma das 205 normalizações**. A suíte do repositório passou com 263 testes na execução da revisão.

O fingerprint da v7 é `6140447dc4ccc34f933199a9463e9d9634753eaf6714bc13df76f6b4d34eb066`. O candidato não contém `domain_review.json` e não registra aprovação final de domínio. A decisão de escopo e a autorização para indexação devem ser registradas separadamente por Jhiovana; esta revisão técnica não as substitui.
