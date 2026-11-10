# Resolução das quatro pendências do release consolidado v3

Release gerado: `data/releases/corpus-consolidado-v4-revisao-2026-11-10` (`pending_review`).

1. **F03, linha 987:** a ocorrência `occ-dd3666cce6867d6246aae72f` continua no corpus de origem para conferir a sequência do PDF. Ela foi excluída do catálogo e dos arquivos publicáveis de ocorrências/evidências. `exclusions.jsonl` registra fonte, página, linha, texto literal e motivo.
2. **F04, indicação:** as 41 ocorrências receberam `context.indication` segundo os grupos impressos na página 1 do PDF. As 41 evidências publicadas carregam `indication` em campo próprio; `text` permanece igual a `raw_text`.
3. **F03, colunas misturadas:** `text` preserva a linha original. `description_cell` contém somente a coluna `DESCRIÇÃO`, extraída com PDFKit do retângulo horizontal 123–284 em cada linha. O recorte de 1.078 linhas, incluindo a vazia, está em `f03_descriptions.json` com hash no manifesto; 1.077 descrições não vazias entram nas evidências.
4. **F01, insumos:** as 27 ocorrências da seção `Insumos (Básico)` ou `Insumos (Estratégico)` foram classificadas como `supply`, com `supply_id` próprio e sem `medicine_id`. A decisão individual e seu localizador constam em `data/curation/revisao-tipo-itens-f01-v4.json`. A classificação é da ocorrência nessa seção, não uma afirmação sobre o produto em outras fontes.

O v4 contém 1.860 apresentações no catálogo de medicamentos, 2.114 ocorrências e 2.114 evidências publicáveis: 2.085 medicamentos e 29 insumos. O validador do corpus e os verificadores dos releases v2, v3 e v4 passaram. O v4 permanece em revisão; esta correção técnica não equivale à aprovação de domínio para uso pelo cidadão.
