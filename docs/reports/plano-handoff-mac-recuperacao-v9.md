# Plano de continuidade — recuperação exata e lexical da v9

**Estado verificado em 12/11/2026:** o release documental v9 está aprovado, seus 2.114 chunks estão no DVC e Jhiovana confirmou `dvc push`/`dvc status -c` sincronizados no Windows. O diagnóstico de desenvolvimento terminou; **o gate de recuperação continua fechado**. Nenhum caso do novo `test` v9 foi executado. Não iniciar embeddings ainda.

> **Antes de trocar de máquina:** o repositório Windows está na branch `main`, Git HEAD `420d344193c535f80c3150e7c5058c48df8dad22`, mas tem muitas alterações e arquivos novos **sem commit e sem push Git**. O Drive/DVC transporta o release e os chunks, não transporta código, gabaritos, relatórios nem ponteiros `.dvc` ausentes do Git. Portanto, `git pull` no Mac, sozinho, **não reproduzirá este estado**. Registrar em Git e enviar as mudanças necessárias ao remoto, ou transferir a árvore de trabalho por um meio controlado, antes de executar a etapa no Mac. Não incluir `.env`, `.dvc/config.local`, tokens OAuth nem cache DVC no Git ou no handoff.

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

1. [ ] **Transportar o estado para o Mac.** No Windows, revisar `git status`, incluir em Git o código, scripts, relatórios, gabaritos, `.dvc/config` e os dois ponteiros v9 (`data/releases/...v9...dvc` e `data/derived/chunks/...v9...dvc`), além das dependências pertinentes (`pyproject.toml` e `uv.lock`). Há muitas outras alterações preexistentes: revisar o diff antes de qualquer commit e separar o que não pertence ao trabalho. Publicar a revisão Git ou transferir a árvore completa por meio controlado. Não fazer commit de segredos ou dos diretórios de dados geridos pelo DVC.
2. [ ] **Restaurar no Mac.** Obter a revisão Git correspondente, instalar o ambiente com `uv sync --group dev`, configurar o OAuth do DVC **localmente** no Mac e executar `uv run dvc pull` seguido de `uv run dvc status -c`. O cliente OAuth próprio e seu segredo ficam em `.dvc/config.local` do Mac; o arquivo Windows contém também caminhos específicos daquele sistema e não deve ser copiado. Consulte [guia DVC](../guia-dvc-drive.md).
3. [ ] **Conferir hashes no Mac** antes de qualquer avaliação:

   ```bash
   shasum -a 256 data/releases/corpus-consolidado-v9-aprovado-2026-11-12/release.json
   shasum -a 256 data/derived/chunks/corpus-consolidado-v9-aprovado-2026-11-12/chunks.jsonl
   shasum -a 256 evals/datasets/consolidated_v9_test_candidate_unreviewed.jsonl
   uv run dvc status -c
   uv run python -m pytest tests/unit/test_v9_retrieval_dev.py -q
   ```

   Os três hashes esperados estão no checklist concluído acima. Se algum divergir, parar e reconciliar a revisão Git/DVC.
4. [ ] **Revisar o novo gabarito com os PDFs oficiais.** Na [folha de revisão](v9-independent-test-review.md), conferir os 28 casos: pergunta, status, princípio ativo, concentração, forma/liberação, evidências, linha, fonte e página. Registrar `Aprovado` ou `Rejeitado`, `Jhiovana AAAA-MM-DD` e justificativa para cada rejeição. As perguntas foram geradas do catálogo e podem ser fáceis ou artificiais; revisar também se o conjunto testa bem a recuperação. Não aceitar o candidato só porque a v9 documental foi aprovada.
5. [ ] **Tratar rejeições antes de abrir o teste.** Corrigir a especificação do candidato e a fonte da geração com justificativa rastreável; regenerar o candidato e fazer nova revisão completa. `scripts/prepare_v9_test_candidate.py` **sobrescreve** a folha de revisão: não o executar após começar a preencher decisões sem antes preservar a revisão e decidir uma nova versão do candidato. Não usar resultados do recuperador para ajustar esse conjunto.
6. [ ] **Congelar o teste após 28 aprovações humanas.** Executar `uv run python scripts/promote_v9_test.py`. O script compara a folha com o candidato, registra o hash da revisão e escreve `evals/datasets/consolidated_v9_reviewed.jsonl`, com 92 casos `dev` e 28 casos `test`. Não sobrescreve um teste já congelado. Registrar o SHA-256 do dataset, o commit Git, os parâmetros e os hashes do release/chunks.
7. [ ] **Executar o `test` oficial uma vez por estratégia**, com o código e o gabarito congelados. Salvar os dois JSONs sem reexecutar nem ajustar depois de ver o resultado:

   ```bash
   uv run python app.py eval --release data/releases/corpus-consolidado-v9-aprovado-2026-11-12 --dataset evals/datasets/consolidated_v9_reviewed.jsonl --split test --strategy exact --output evals/results/consolidated_v9_exact_test.json
   uv run python app.py eval --release data/releases/corpus-consolidado-v9-aprovado-2026-11-12 --dataset evals/datasets/consolidated_v9_reviewed.jsonl --split test --strategy lexical --output evals/results/consolidated_v9_lexical_test.json
   ```

8. [ ] **Publicar o parecer do gate**, com resultados agregados e por F01/F03/F04, denominadores, erros por caso, latência p50/p95 e rastreabilidade de hashes/commit. Aprovar avanço somente se **Hit@5 ≥ 0,90, MRR@5 ≥ 0,80, zero confusões críticas e 100% das citações verificáveis** no `test` revisado. Se falhar, preservar esse resultado e preparar uma nova rodada independente; não retunar com o mesmo `test`.

## Depois do gate

Somente se a recuperação exata/lexical for aprovada: vetorização dos chunks com configuração e retomada registradas; benchmark vetorial e híbrido contra o mesmo contrato de identidade; avaliação de respostas com RAGAS; depois contrato de estoque com o agente. CEP → UBS continua uma frente separada, condicionada à validação do serviço territorial e dos controles de privacidade. O corpus documental não comprova estoque, elegibilidade, indicação individual nem equivalência terapêutica.
