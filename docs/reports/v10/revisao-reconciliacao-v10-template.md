# Revisão de Reconciliação de Catálogo — Candidato `v10`

**Data de geração:** 2026-11-16  
**Origem aprovada:** `corpus-consolidado-v9-aprovado-2026-11-12` (SHA-256 manifesto `ea72d7705cccf7a14c359bd67d60807ce5e994ecd541810f1a6d066d33f01a84`)  
**Candidato gerado:** `corpus-consolidado-v10-reconciliada-2026-11-16`  
**SHA-256 do manifesto candidato:** `cc7b3cc1693aea3866819f843d25a9761ef9f8a966fcea60f7132d399b95cd3a`  
**Fingerprint do corpus:** `050506bdf031ef41ae6044a8e8dad6d242b8f8b425e300fd099bfa2306126aea`

---

## O que foi alterado nesta build

1. **Deduplicação determinística de 80 pares de colisão (`catalog.jsonl`: `1.859 → 1.779` apresentações):**
   - Aplicado o inventário de [diagnostico-colisoes-v9-para-v10.md](../v9/diagnostico-colisoes-v9-para-v10.md) unificando espaçamentos (`mg`, `mcg`, `g`, `mL`, `UI`, `%`), acentuação (`arteméter`, `isotretinoína`, `fenitoína`, `nitrofurantoína`, `bupivacaína`) e ordem canônica de sal (`cloridrato de metformina` vs `metformina (cloridrato)`).
2. **Preservação integral da linhagem e texto original:**
   - Todas as **2.114 ocorrências** e **2.114 evidências** permanecem preservadas; apenas `medicine_id` e campos estruturados normalizados da apresentação mesclada foram alinhados ao registro canônico (`raw_text`, `description_cell`, `source_code`, `channel` e páginas inalterados).
3. **Chunks compatíveis nativamente com `one-evidence-v2`:**
   - Verificado que `CHUNK_RECIPE_V2` gera **2.114 textos únicos** (`0` duplicatas entre as 2.114 evidências, eliminando os 20 pares idênticos herdados da `v1`).

---

## Como aprovar após revisão humana

Após conferir a reconciliação e registrar a decisão em `docs/reports/v10/revisao-reconciliacao-v10-jhiovana.md` (incluindo o texto `"pode aprovar a revisao"` e o hash `cc7b3cc1693aea3866819f843d25a9761ef9f8a966fcea60f7132d399b95cd3a`), executar:

```bash
PYTHONPATH=src uv run python -m scripts.approve_v10_release --candidate-sha256 cc7b3cc1693aea3866819f843d25a9761ef9f8a966fcea60f7132d399b95cd3a
```
