# Revisão da v6 e decisão de domínio da v7

**Responsável:** Jhiovana, engenharia de dados.  
**Decisão em 11/11/2026:** **v7 aprovada com restrições para indexação e recuperação documental**, por instrução explícita de Jhiovana nesta conversa. A v6 permanece como registro histórico e não recebeu nova aprovação por esta decisão.

## Escopo de revisão

Release candidato: `corpus-consolidado-v6-auditado-2026-11-11`. Escopo possível: presença documental de medicamentos, apresentações e insumos nas versões congeladas F01/F03/F04. Exclui estoque, elegibilidade, indicação individual, equivalência terapêutica e UBS de referência.

Conferir [o relatório original com errata](relatorio-auditoria-corpus-v6.md), [as diferenças por campo](v6-source-alignment-findings.json), a [planilha de revisão](v6-source-alignment-review.csv), o `audit_log.jsonl` e as páginas dos PDFs citadas por cada ocorrência. O verificador relê os PDFs; os caches F01/F03 foram iguais à extração nova na execução de 11/11/2026. A planilha registra 205 decisões `aceitar_normalizacao`, quatro `corrigir_release` e zero pendências, com `Jhiovana` e 11/11/2026 em suas linhas. Este documento registra o resultado técnico da planilha, sem atribuir a ela aprovação final do release.

O [validador](../../../scripts/validate_v6_review.py) exige todas as linhas preenchidas; `corrigir_release` ou `manter_pendente` mantêm o gate da v6 aberto. As quatro correções de separadores de códigos F03 foram incorporadas ao candidato [v7](../../../data/releases/corpus-consolidado-v7-codigos-corrigidos-2026-11-11/release.json), com fingerprint `6140447dc4ccc34f933199a9463e9d9634753eaf6714bc13df76f6b4d34eb066` e status `pending_review`. A conferência nova encontrou 205 diferenças, exatamente as 205 normalizações aceitas na planilha, sem diferenças de código nem diferenças novas. A v6 permanece intacta. A avaliação de recuperação anterior se refere à v6 e deve ser refeita sobre a v7 após aprovação.

As quatro correções também foram [inspecionadas visualmente no PDF F03 e revisadas tecnicamente](../v7/parecer-tecnico-v7-codigos.md). Esse parecer cobre os quatro códigos e a integridade do candidato. A decisão final de escopo foi dada por Jhiovana após essa revisão; o pacote [v7 aprovado](../../../data/releases/corpus-consolidado-v7-aprovado-2026-11-11/release.json) foi publicado separadamente, preservando o candidato e a v6. O registro de autorização está em `domain_review.json` dentro desse pacote.

```powershell
.venv\Scripts\python.exe scripts/validate_v6_review.py --findings docs/reports/v6-source-alignment-findings.json --review docs/reports/v6-source-alignment-review.csv
```

## Registro da decisão

- Release decidido: **`corpus-consolidado-v7-aprovado-2026-11-11`**. Fingerprint de conteúdo: `9ad9a3a7f50dc69005daba390bc2b07fb3710f4e54216faf0dca5cb8b346e327`. SHA-256 do manifesto, usado como fingerprint pelo carregador: `8399f37f6664f474c18622d912ad9795f04ec199102724cfaafbe6e295eeab20b`.
- SHA-256 da planilha de decisões: `9160dec69fe312bc22f2f149789defd411a5c4b87c804b60bae2169ab26e95e3`
- Diferenças aceitas/corrigidas/pendentes: **205/4/0 na planilha; quatro correções presentes na v7; 205 diferenças restantes coincidem com as aceitas**
- Páginas conferidas visualmente nesta revisão técnica: **quatro páginas F03 (13, 30, 35 e 52), correspondentes às quatro correções**. As 205 normalizações restantes foram conferidas por identidade e decisão na planilha, sem inspeção visual individual nesta etapa.
- Decisão: **aprovado com restrições** para indexação e recuperação de presença documental nas edições congeladas F01/F03/F04, com proveniência e limites da fonte.
- Restrições: **sem prova de estoque UBS, disponibilidade na Farmácia Popular, elegibilidade, indicação individual, equivalência terapêutica, intercambialidade ou UBS de referência**. As 79 entradas incompletas do catálogo não confirmam forma ou concentração omitida na fonte. A aprovação do corpus não aprova desempenho do RAG nem do conjunto de avaliação.
- Nome, função e data: **Jhiovana, engenharia de dados e responsável pelo projeto, 11/11/2026**. Autorização textual: “certo, então eu aprovo. Fecho o gate da v7. pode registrar pra mim no documento de revisão [...] e pode iniciar a proxima etapada.”
