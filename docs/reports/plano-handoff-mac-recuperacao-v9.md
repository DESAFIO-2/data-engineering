# Plano de continuidade — recuperação exata e lexical da v9

**Estado verificado em 12/11/2026:** o release documental v9 está aprovado, seus 2.114 chunks estão no DVC, e a restauração no Mac foi conferida por hashes, seis testes e confirmação da operadora de `dvc status -c` sincronizado. Jhiovana registrou 28 aprovações na folha v2; o dataset foi congelado com 92 `dev` e 28 `test`. As duas avaliações oficiais foram executadas uma vez e **o gate de recuperação foi reprovado**: Hit@5 e MRR@5 ficaram abaixo dos limiares. Ver [parecer](validacao-recuperacao-v9-test.md). Não iniciar embeddings.

> **Estado do Git:** o código, os gabaritos, relatórios e ponteiros `.dvc` foram publicados na branch `main` do GitHub no commit `16ec4829b1bef0debfd6150fb0ac8e436c68f892` (autor `jhsribeiro`). O release e os chunks seguem no remoto DVC. O repositório separado `Data-Science/` e os arquivos locais de autenticação não entraram no commit. Para reproduzir no Mac, obter `main` atualizado **e** executar `dvc pull`; Git e DVC transportam partes complementares do estado. Não incluir `.env`, `.dvc/config.local`, tokens OAuth nem cache DVC no handoff.

## Checklist do que está feito

- [x] Aprovação humana da correção documental de claritromicina 500 mg comprimido registrada em [revisao-claritromicina-v9-jhiovana.md](revisao-claritromicina-v9-jhiovana.md); linhas F03 247–249 compartilham a apresentação, preservando códigos e canais próprios.
- [x] Release imutável `corpus-consolidado-v9-aprovado-2026-11-12` publicado. SHA-256 do `release.json`: `ea72d7705cccf7a14c359bd67d60807ce5e994ecd541810f1a6d066d33f01a84`.
- [x] 2.114 chunks v9 reconstruídos e validados. SHA-256 do `chunks.jsonl`: `f6049cedf006aefd7bbc3d06f2b2fda0de4a906e3d95a1fb6272c08b9ec9da8e`.
- [x] Ponteiros DVC do release e dos chunks criados; `dvc status` local atualizado; Jhiovana confirmou cache e remoto `compartilhado` sincronizados no Windows. A confirmação remota é da operadora, não de uma checagem independente deste ambiente.
- [x] Gabarito exploratório v9 migrado: 119 casos, sendo 92 em `dev` e 27 do `test` v8 mantidos apenas como histórico. O caso aberto `C-F03-005` passou ao `dev`; suas três evidências F03 são relevantes. SHA-256: `9acef45d40c603565f181dbeb2e3ef4048299b2baaf983cc24441a49e67bfd39`.
- [x] `dev` avaliado com `top_k=5`: exata e lexical tiveram 77/77 positivos com Hit@5 e MRR@5 de 1,0000, 15/15 abstenções corretas, zero confusões críticas e 81/81 citações verificáveis. Resultado **exploratório**, pois são perguntas já conhecidas e majoritariamente sintéticas. Ver [relatório completo](validacao-recuperacao-v9-dev.md).
- [x] Novo [candidato de teste v9](../../evals/datasets/consolidated_v9_test_candidate_unreviewed.jsonl) preparado, com 28 casos de famílias ausentes do benchmark histórico (10 positivos F01, 10 F03, quatro F04 e quatro negativos). SHA-256: `c80c9db2fd168d2782fec7fa9c4c780471ae5507a25f8a66e47c85fa72e31d66`. **Não avaliado e não aprovado.**
- [x] [Folha de revisão dos 28 casos](v9-independent-test-review.md) criada com pergunta, status, apresentação, evidência, página e colunas para decisão humana. O promotor recusa decisões pendentes/rejeitadas e bloqueia sobrescrita do teste congelado.
- [x] Ruff passou nos arquivos alterados; seis testes específicos e **286 testes da suíte completa** passaram.

## Checklist pendente, na ordem

1. [x] **Publicar o estado em Git.** O commit `16ec4829b1bef0debfd6150fb0ac8e436c68f892` inclui código, scripts, relatórios, gabaritos, `.dvc/config`, ponteiros v7/v8/v9, `pyproject.toml` e `uv.lock`. O remoto `origin/main` foi confirmado no mesmo hash. Segredos e `Data-Science/` ficaram fora.
2. [x] **Restaurar no Mac.** A revisão Git, o ambiente, o OAuth local e o `dvc pull` foram concluídos. A operadora confirmou `dvc status -c` sincronizado. O cliente OAuth próprio e seu segredo ficam em `.dvc/config.local` do Mac; o arquivo Windows contém também caminhos específicos daquele sistema e não deve ser copiado. Consulte [guia DVC](../guia-dvc-drive.md).
3. [x] **Conferir hashes no Mac** antes de qualquer avaliação:

   ```bash
   shasum -a 256 data/releases/corpus-consolidado-v9-aprovado-2026-11-12/release.json
   shasum -a 256 data/derived/chunks/corpus-consolidado-v9-aprovado-2026-11-12/chunks.jsonl
   shasum -a 256 evals/datasets/consolidated_v9_test_candidate_unreviewed.jsonl
   uv run dvc status -c
   uv run python -m pytest tests/unit/test_v9_retrieval_dev.py -q
   ```

   Os três hashes do v1 conferiram, e os seis testes passaram. Para o candidato v2, consultar o hash em [sua auditoria](v9-test-candidate-v2-audit.md). Se algum hash divergir, parar e reconciliar a revisão Git/DVC.
4. [x] **Revisar o novo gabarito com os PDFs oficiais.** Jhiovana registrou `Aprovado` e `Jhiovana 2026-11-12` para os 28 casos na [folha v2](v9-independent-test-review-v2.md). O promotor conferiu correspondência com o candidato e o release.
5. [x] **Tratar rejeições antes de abrir o teste.** A dupla revisão está em [parecer técnico](dupla-revisao-teste-v9-2026-11-12.md). O gerador foi corrigido e criou o [candidato v2](../../evals/datasets/consolidated_v9_test_candidate_v2_unreviewed.jsonl) e a [folha v2](v9-independent-test-review-v2.md), preservando o v1. A [auditoria v2](v9-test-candidate-v2-audit.md) registra a verificação de ausência dos quatro novos negativos nos PDFs e no catálogo. O gerador recusa sobrescrever o v2.
6. [x] **Congelar o teste após 28 aprovações humanas no v2.** O promotor conferiu a folha v2 e escreveu `evals/datasets/consolidated_v9_reviewed.jsonl`, com 92 casos `dev` e 28 casos `test`. SHA-256 do dataset: `d66412357e72c7df3fb6975c34773613b8356ff11da67ee114995bd382873b28`; folha de revisão: `96d523fd3d16832fc539351a530daee0e7b4fb5915207372701002b190459275`; candidato v2: `0ca276409cd9e46da4665d74513de065cdf7bfb1fc0374070334f591d1970c28`. Release e chunks conservam os hashes dos itens anteriores. Registrar o commit Git que incluir este estado antes de executar o teste oficial.
7. [x] **Executar o `test` oficial uma vez por estratégia**, com o código e o gabarito congelados. Os dois JSONs foram salvos sem reexecução nem ajuste depois de ver o resultado:

   ```bash
   uv run python app.py eval --release data/releases/corpus-consolidado-v9-aprovado-2026-11-12 --dataset evals/datasets/consolidated_v9_reviewed.jsonl --split test --strategy exact --output evals/results/consolidated_v9_exact_test.json
   uv run python app.py eval --release data/releases/corpus-consolidado-v9-aprovado-2026-11-12 --dataset evals/datasets/consolidated_v9_reviewed.jsonl --split test --strategy lexical --output evals/results/consolidated_v9_lexical_test.json
   ```

8. [x] **Publicar o parecer do gate**, com resultados agregados e por F01/F03/F04, denominadores, erros por caso, latência p50/p95 e rastreabilidade de hashes/commit. [Resultado: reprovado](validacao-recuperacao-v9-test.md), com Hit@5 = 0,7917 e MRR@5 = 0,7917 em ambas as estratégias; zero confusões críticas e 24/24 citações emitidas verificáveis. Preservar o resultado e preparar nova rodada independente; não retunar com o mesmo `test`.

## Depois do gate

Somente se a recuperação exata/lexical for aprovada: vetorização dos chunks com configuração e retomada registradas; benchmark vetorial e híbrido contra o mesmo contrato de identidade; avaliação de respostas com RAGAS; depois contrato de estoque com o agente. CEP → UBS continua uma frente separada, condicionada à validação do serviço territorial e dos controles de privacidade. O corpus documental não comprova estoque, elegibilidade, indicação individual nem equivalência terapêutica.

**Nova rodada após a reprovação:** o filtro foi corrigido em desenvolvimento e um [candidato independente novo](v9-next-round-preparation.md) foi preparado. A revisão humana e o novo `test` continuam pendentes. Os resultados oficiais v8/v9 permanecem históricos e não serão reexecutados.
