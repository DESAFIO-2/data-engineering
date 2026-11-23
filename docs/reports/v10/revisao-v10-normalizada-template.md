# Revisão Humana — Release Candidato `v10` Normalizado

**Candidato:** `corpus-consolidado-v10-normalizada-2026-11-17`
**Origem aprovada:** `corpus-consolidado-v9-aprovado-2026-11-12`
**SHA-256 do manifesto candidato:** `d99e26e52eca0c3b115c9f7d93fa600b2ca4fe39a885cc268c10ff88252e5921`
**Fingerprint do corpus:** `9136a052000b6b921866588aa3d25188fcfc1db8f3dfccf29674ea2221790543`
**Receita de chunks verificada:** `one-evidence-v3:normalized-fields;literal-spelling;F03-description-cell;F03-channel-code;F01-component-atc;F04-indication;source-provenance;no-old-chunks`

---

## 1. Resumo das alterações verificadas

- **Catálogo deduplicado:** `1859` → `1727` apresentações (`132` absorções em `merges.csv`, incluindo as 80 colisões anteriores e 52 variantes ortográficas/de sal/de forma).
- **Literais preservados:** todas as 2.114 ocorrências mantêm `raw_text`, grafia, concentração, forma e canal literais da fonte; campos padronizados ficam exclusivamente em `normalized`.
- **Correções de parser (`corrected_v10_parser`):** `54` registros na `F01` (53 componentes nulos preenchidos pela coluna 4 do `raw_text` e `0/ ,3 mg/mL` → `0,3 mg/mL` conferido na p. 41 do PDF).
- **Canais F03 e chunks v3:** `1077/1077` ocorrências F03 com códigos de canal; `2114/2114` textos únicos de chunk (`p50=328`, `p95=540`, `max=814` caracteres).

---

## 2. Comparativo `v9 × v10` no split `dev` (`exact` / `lexical`)

| Conjunto (split `dev`) | Estratégia | Δ Hit@1 | Δ Hit@5 | Δ MRR@5 | Δ Status |
|---|---|---:|---:|---:|---:|
| `consolidated_v9_reviewed_dev` | `exact` | +0.0000 | +0.0000 | +0.0000 | +0.0000 |
| `consolidated_v9_reviewed_dev` | `lexical` | +0.0000 | +0.0000 | +0.0000 | +0.0000 |
| `week3_v9_dev_draft` | `exact` | +0.0000 | +0.0000 | +0.0000 | +0.0000 |
| `week3_v9_dev_draft` | `lexical` | +0.0000 | +0.0000 | +0.0000 | +0.0000 |
| `multichunk_v9_benchmark_dev` | `exact` | +0.0000 | +0.0000 | +0.0000 | +0.0000 |
| `multichunk_v9_benchmark_dev` | `lexical` | +0.0625 | +0.0000 | +0.0375 | +0.0000 |
| `week3_v10_channel_dev_draft` | `exact` | +0.0000 | +0.0625 | +0.0312 | +0.0625 |
| `week3_v10_channel_dev_draft` | `lexical` | +0.5000 | +0.0625 | +0.3125 | +0.0625 |

---

## 3. Planilhas de revisão humana (F8)

| Arquivo | Registros | Foco de conferência |
|---|---:|---|
| [merges.csv](merges.csv) | 132 | Conferir se cada par absorvido representa a mesma apresentação |
| [vocab_forms.csv](vocab_forms.csv) | 205 | Conferir forma controlada, `package` e `specification` (`confidence=manual`) |
| [vocab_channels.csv](vocab_channels.csv) | 109 | Conferir texto limpo, códigos de canal e notas de rodapé separadas |
| [ingredient_variants.csv](ingredient_variants.csv) | 71 | Conferir grafia canônica RENAME/DCB vs variantes de sal/acento/caixa |
| [parser_corrections.csv](parser_corrections.csv) | 54 | Conferir as 54 correções na F01 contra `raw_text`/PDF |
| [chunks_sample.csv](chunks_sample.csv) | 30 | Amostra estratificada dos chunks `one-evidence-v3` |

---

## 4. Como aprovar após revisão humana

Após preencher as planilhas e registrar a decisão final em `docs/reports/v10/revisao-v10-normalizada-jhiovana.md` contendo literalmente a frase `"pode aprovar a revisao"` e o hash `d99e26e52eca0c3b115c9f7d93fa600b2ca4fe39a885cc268c10ff88252e5921`, executar:

```bash
PYTHONPATH=src uv run python -m scripts.approve_v10_release --candidate-sha256 d99e26e52eca0c3b115c9f7d93fa600b2ca4fe39a885cc268c10ff88252e5921
```
