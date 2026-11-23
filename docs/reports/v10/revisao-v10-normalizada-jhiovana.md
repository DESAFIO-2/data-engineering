# Revisão Humana — Release Candidato `v10` Normalizado

**Candidato:** `corpus-consolidado-v10-normalizada-2026-11-17`
**Origem aprovada:** `corpus-consolidado-v9-aprovado-2026-11-12`
**SHA-256 do manifesto candidato:** `d99e26e52eca0c3b115c9f7d93fa600b2ca4fe39a885cc268c10ff88252e5921`
**Fingerprint do corpus:** `9136a052000b6b921866588aa3d25188fcfc1db8f3dfccf29674ea2221790543`
**Receita de chunks verificada:** `one-evidence-v3:normalized-fields;literal-spelling;F03-description-cell;F03-channel-code;F01-component-atc;F04-indication;source-provenance;no-old-chunks`
**Revisora:** Jhiovana
**Data:** 2026-11-18

---

## 1. Resumo das alterações verificadas

- **Catálogo deduplicado:** `1859` → `1727` apresentações (`132` absorções em `merges.csv`, incluindo as 80 colisões anteriores e 52 variantes ortográficas/de sal/de forma).
- **Literais preservados:** todas as 2.114 ocorrências mantêm `raw_text`, grafia, concentração, forma e canal literais da fonte; campos padronizados ficam exclusivamente em `normalized`.
- **Correções de parser (`corrected_v10_parser`):** `54` registros na `F01` (53 componentes nulos preenchidos pela coluna 4 do `raw_text` e `0/ ,3 mg/mL` → `0,3 mg/mL` conferido na p. 41 do PDF).
- **Canais F03 e chunks v3:** `1077/1077` ocorrências F03 com códigos de canal; `2114/2114` textos únicos de chunk (`p50=328`, `p95=540`, `max=814` caracteres).

---

## 2. Decisão

Decisão registrada por **Jhiovana** em **2026-11-18**: **pode aprovar a revisao** referente ao candidato `corpus-consolidado-v10-normalizada-2026-11-17` (`d99e26e52eca0c3b115c9f7d93fa600b2ca4fe39a885cc268c10ff88252e5921`), restrita à presença documental nas fontes congeladas F01/F03/F04, camada aditiva `normalized`, vocabulários controlados e correções de parser F01.
