# Relatórios e decisões — Release v10

| Artefato / Release | Estado | Nota |
|---|---|---|
| `corpus-consolidado-v10-reconciliada-2026-11-16` | **Superseded** (substituído, preservado em disco) | Cobria apenas as 80 colisões de identidade e sobrescrevia literais nas 94 ocorrências remapeadas. Substituído pela Opção A (camada aditiva `normalized` + `CHUNK_RECIPE_V3`). Ver [template histórico](revisao-reconciliacao-v10-template.md). |
| `corpus-consolidado-v10-normalizada-2026-11-17` | Em construção (`pending_review` após build) | Preserva os literais do `v9` (exceto 54 correções auditadas de parser na `F01`), adiciona `normalized`, recalcula catálogo via identidade canônica, gera `id_map_v9_v10.json` e usa `CHUNK_RECIPE_V3`. |
