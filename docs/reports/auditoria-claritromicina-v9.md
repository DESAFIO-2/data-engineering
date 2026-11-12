# Auditoria da identidade de claritromicina 500 mg — candidato v9

**Estado em 12/11/2026:** Jhiovana aprovou explicitamente a revisão, registrada em [revisao-claritromicina-v9-jhiovana.md](revisao-claritromicina-v9-jhiovana.md). O candidato foi preservado e a [v9 aprovada](../../data/releases/corpus-consolidado-v9-aprovado-2026-11-12/release.json) foi publicada separadamente. A v8 aprovada e os resultados do `test` v8 permanecem intactos. Esta aprovação documental não abre um novo gate de recuperação nem autoriza embeddings.

## Fonte e diagnóstico

Na REME-DF de 29/10/2026, as linhas 247–249 mostram **claritromicina, comprimido, 500 mg**:

| Linha | Página | Código da fonte | Grafia na descrição | Contexto e canal registrados |
|---:|---:|---|---|---|
| 247 | 21 | MSE38470 | `500 mg` | Coqueluche; UBS de referência indicada na própria linha |
| 248 | 21 | MSE38243 | `500 mg` | Hanseníase; Farmácia Escola/HUB, HRAN e CEDIN |
| 249 | 22 | MSE8831 | `500mg` | Tuberculose/SITE-TB; CEDIN |

O PDF local `data/raw/F03-reme-df/reme-df-2026-10-29.pdf` corresponde ao SHA-256 F03 do manifesto v8. As três linhas têm o mesmo princípio ativo, concentração numérica, unidade e forma; códigos, contexto e canais **não foram fundidos**. O construtor histórico do catálogo usou a grafia da concentração como parte da identidade, sem normalizar o espaço antes de `mg`. Por isso a linha 249 recebeu outro `medicine_id`. O caso `C-F03-005` do teste v8 não especifica coqueluche, hanseníase ou tuberculose; as três linhas são evidências documentais pertinentes à pergunta genérica. O avaliador sinalizou confusão porque comparou IDs de catálogo distintos. Essa conclusão deriva da inspeção da fonte, não de um ajuste de limiar para melhorar o teste.

## Correção isolada

O script `scripts/publish_v9_clarithromycin.py` exige o SHA-256 `d634a75817ff3d16031c45fa664b9075ec426c1b3482581c0ca93f490906cba7` do manifesto v8 antes de publicar o candidato [v9](../../data/releases/corpus-consolidado-v9-claritromicina-normalizada-2026-11-12/release.json). Apenas a ocorrência `occ-83202f34ce2ffbeed05ea49d` muda `strength` de `500mg` para `500 mg` e `medicine_id` de `med-018ed18f2ec7fd073407f4e4` para `med-3801ddc7d957468e0916fed0`. A evidência correspondente e o log acompanham a correção. O texto literal `500mg`, código `MSE8831`, página 22, linha 249 e canal SITE-TB ficam preservados. A entrada duplicada sai do catálogo; a entrada canônica passa a referenciar as quatro ocorrências já associadas à apresentação (uma F01 e três F03).

O catálogo passa de **1.860 para 1.859 entradas**; há **2.114 ocorrências e 2.114 evidências**, sem exclusão documental. O pacote pendente tem fingerprint de conteúdo `d65ad02bc66ae9d5c98ffa8475f39e4b5a674254ff9e55abae00c0ef80406faa` e SHA-256 do manifesto `60e8218b7968103940894ed513b062f988b085b0e7b01bcdd65a464442f34614`. O verificador reconstruiu as evidências a partir das ocorrências. A v8 mantém seu manifesto e aprovação originais; a v9 não contém `domain_review.json` e não pode ser carregada como release aprovado.

Verificação do candidato: Ruff passou no publicador e nos testes novos; os três testes específicos e a suíte completa (**279 testes**) passaram. O candidato pendente não recebeu chunks nem embeddings.

O release aprovado tem SHA-256 do manifesto `ea72d7705cccf7a14c359bd67d60807ce5e994ecd541810f1a6d066d33f01a84` e fingerprint de conteúdo `99d4fb04a74463b9cfdd4ea9c08b51a0ef39bb5631be58964209d6041f9e1b20`. Seu `domain_review.json` referencia a decisão humana (SHA-256 `acd85a4445f3220aacfd0e0fd5dea18e901751c25bbcbff181ea6eab452c714a`). Os 2.114 chunks canônicos foram reconstruídos para o novo fingerprint; SHA-256 `f6049cedf006aefd7bbc3d06f2b2fda0de4a906e3d95a1fb6272c08b9ec9da8e`. Release e chunks têm ponteiros DVC locais, e `dvc status` informou dados locais atualizados. Em 12/11/2026, Jhiovana confirmou que executou `uv run dvc push` e `uv run dvc status -c` no PowerShell autenticado e que cache e remoto ficaram sincronizados para a v9. Esta confirmação foi informada pela operadora; não representa uma verificação independente deste ambiente.

Após a publicação da v9 aprovada, Ruff passou nos scripts e testes alterados, quatro testes específicos passaram e a suíte completa terminou com **280 testes aprovados**.

## Limite do escopo

Uma varredura do catálogo v8 pela chave normalizada `(princípio ativo, concentração, forma, liberação)` encontrou **79 pares** de entradas com a mesma chave; os 79 têm concentração igual após remover espaços. A correção acima trata **um par**. Restam 78 candidatos a auditoria, alguns entre F01 e F03 e alguns com grafias de nome diferentes. Não foram fundidos automaticamente: antes disso é preciso verificar sais, associações, forma, liberação e limites de cada fonte. A regra histórica de geração de IDs permanece preservada para reproduzir releases anteriores.

Para um gabarito novo, a pergunta genérica sobre claritromicina 500 mg comprimido deve considerar as três linhas F03 pertinentes. Perguntas específicas de coqueluche, hanseníase e SITE-TB devem conservar código, canal e evidência próprios. O resultado `test` v8 continua histórico; não deve ser reetiquetado nem reexecutado para aprovar o gate. Após revisão humana do candidato e eventual publicação aprovada, preparar um conjunto de desenvolvimento corrigido e **novo teste independente**.

## Decisão de domínio registrada

A instrução “pode aprovar a revisao” de Jhiovana aprovou a normalização de `500mg` para `500 mg` e o vínculo da linha 249 à mesma apresentação documental das linhas 247–248. A decisão se restringe à identidade da apresentação; não afirma equivalência de canais, indicação, elegibilidade ou estoque. O novo release imutável contém o registro de aprovação, com escopo e limitações.
