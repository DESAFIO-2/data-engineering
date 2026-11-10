import json
from pathlib import Path

target_ids = [
    'occ-474c281dae2e99240c1eff36', 'occ-e86fd5ebe1a99a846ba78102', 'occ-32f9c026384ce1b61a6b03a2',
    'occ-405fcd5d37f8cf3fbb357a41', 'occ-adec0f7209079b9611b5cfc9', 'occ-5c8cb5f6e80b2a3a5f8a2027',
    'occ-553b30030ceb12bfa5113db8', 'occ-a5e2f1115e585f9c4709d2a6', 'occ-4ca457d29ba42bb33f3bc64e',
    'occ-4d92ef17e651e44f84976722', 'occ-2464731871295988e078ba92', 'occ-03a0937aee1ee337489ce4b2',
    'occ-da10cf549da731835bc37ec8', 'occ-5fcf182ffbf7611abfc0f3a6', 'occ-028f86f5eeea493b827e852d',
    'occ-f1e102feecbc4cb25d3fa7bf', 'occ-1ef7cf9dc77abebb8e1d3293', 'occ-dfafa515914dc7463e544438',
    'occ-e4905cf7df4cb432da84bc5e', 'occ-b484439c2c62c2f25fc2524a', 'occ-d602377b31174092b7454261',
    'occ-3db1e6b3fa1b49f481358dbb', 'occ-284a142163b46990cfbe4b9e', 'occ-ff71cb89ff14fc3f1da3589b',
    'occ-9008bc50be25d886da1a97d7', 'occ-f6f1c4e7ab95116752ea4111', 'occ-32130e9d6d5c64f6fc6e2a22',
    'occ-4c6e949ff5f6e9c9f688846c', 'occ-b08e56ec4a7d6537ce9745b8', 'occ-850d032622bf9315735f58e4',
    'occ-cbb4fc1f91217e54f0a996da', 'occ-2dca1113b5e80dc65a587eb0', 'occ-df629858ec4bc615d97d02dc',
    'occ-cfb8813bcfe35e1654a938fe', 'occ-7b830d977e203405c1b69562', 'occ-7067d2ca8dcaea73bf1f6fc2',
    'occ-bd645fca4e10b51f38485f06', 'occ-2e237469ad52f38dc54b786e', 'occ-31f830e7fbb52c0353da2946',
    'occ-e7d83368e51a7cb974fd6bd9'
]

# Load all occurrences from experimental
all_occs = {}
with open('data/corpus/experimental/occurrences.jsonl', 'r', encoding='utf-8') as f:
    for line_idx, line in enumerate(f, start=1):
        if not line.strip():
            continue
        d = json.loads(line)
        all_occs[d['occurrence_id']] = (line_idx, line.strip(), d)

# Find all occurrences in experimental where strength is null or form is null
null_strength_all = []
null_form_all = []
for oid, (line_idx, raw_line, d) in all_occs.items():
    s = d.get('strength')
    fm = d.get('form')
    if s is None or s == '' or s == '-':
        null_strength_all.append((oid, line_idx, raw_line, d))
    if fm is None or fm == '':
        null_form_all.append((oid, line_idx, raw_line, d))

matched_targets = [tid for tid in target_ids if tid in all_occs]

md_lines = []
md_lines.append('# Ocorrências com Campos Pendentes para Edição\n')
md_lines.append('> **Arquivo gerado para auditoria e edição direta:** `.docs/ocorrencias-para-edicao.md`  ')
md_lines.append('> **Data de geração:** 09/11/2026  ')
md_lines.append('> **Instruções de Preenchimento:**  ')
md_lines.append('> - **`strength`**: destinado para **quantidade em gramas (g, mg, mcg)**, concentração, dosagem ou volume (ex.: `500 mg`, `10 mg/mL`, `25 g`, `0,03 mg + 0,15 mg`, `10 mL`).  ')
md_lines.append('> - **`form`**: destinado para a forma farmacêutica (ex.: `comprimido`, `solução injetável`, `pomada`, `ampola`, `frasco ou bolsa`).  ')
md_lines.append('> - **`active_ingredient`**: princípio ativo / DCB (ex.: `água para injetáveis`, `cloridrato de metformina`).')
md_lines.append('\n---\n')

md_lines.append('## 1. Ocorrências Citadas Diretamente na Mensagem\n')
md_lines.append('Abaixo estão os dados integrais das ocorrências solicitadas encontradas no arquivo `data/corpus/experimental/occurrences.jsonl` (incluindo as 3 de água para injetáveis e os pares de combinações).\n')

for idx, tid in enumerate(matched_targets, start=1):
    line_idx, raw_line, d = all_occs[tid]
    ing = d.get('active_ingredient')
    st = d.get('strength')
    fm = d.get('form')
    src = d.get('source', {})
    page = src.get('page')
    src_id = src.get('source_id')
    raw_text = d.get('raw_text', '').replace('\n', ' ')

    md_lines.append(f'### 1.{idx} `{tid}` (Linha {line_idx} de `experimental/occurrences.jsonl`)')
    md_lines.append(f'- **Fonte:** `{src_id}` (página {page})')
    md_lines.append(f'- **Princípio Ativo:** `{ing}`')
    md_lines.append(f'- **Concentração (`strength`):** `{st}`')
    md_lines.append(f'- **Forma Farmacêutica (`form`):** `{fm}`')
    md_lines.append(f'- **Canal:** `{d.get("channel")}`')
    md_lines.append(f'- **Texto Bruto no PDF:** > *{raw_text}*\n')

    md_lines.append('**JSON Formatado (Editável):**')
    md_lines.append('```json')
    md_lines.append(json.dumps(d, ensure_ascii=False, indent=2))
    md_lines.append('```\n')

    md_lines.append('**Linha Integral JSONL (Linha única original):**')
    md_lines.append('```jsonl')
    md_lines.append(raw_line)
    md_lines.append('```\n')
    md_lines.append('---\n')

# Section 2: Null strength table
md_lines.append('## 2. Todas as Ocorrências com `strength` Nulo ou Vazio na Base Experimental\n')
md_lines.append(f'Total encontrado: **{len(null_strength_all)} ocorrências**.\n')
md_lines.append('| # | ID Ocorrência | Linha | Fonte | Pág | Princípio Ativo | Forma Farmacêutica | Valor Atual `strength` |')
md_lines.append('| :---: | :--- | :---: | :---: | :---: | :--- | :--- | :---: |')
for i, (oid, lnum, rline, d) in enumerate(null_strength_all, start=1):
    src = d.get('source', {})
    ing = d.get('active_ingredient') or '*[NULL]*'
    fm = d.get('form') or '*[NULL]*'
    st = d.get('strength')
    md_lines.append(f'| {i} | `{oid}` | {lnum} | {src.get("source_id")} | {src.get("page")} | {ing} | {fm} | `{st}` |')

md_lines.append('\n---\n')

md_lines.append('\n---\n')

# Section 3: Null form table
md_lines.append('## 3. Todas as Ocorrências com `form` Nulo ou Vazio na Base Experimental\n')
md_lines.append(f'Total encontrado: **{len(null_form_all)} ocorrências**.\n')
md_lines.append('| # | ID Ocorrência | Linha | Fonte | Pág | Princípio Ativo | Concentração (`strength`) | Valor Atual `form` |')
md_lines.append('| :---: | :--- | :---: | :---: | :---: | :--- | :--- | :---: |')
for i, (oid, lnum, rline, d) in enumerate(null_form_all, start=1):
    src = d.get('source', {})
    ing = d.get('active_ingredient') or '*[NULL]*'
    st = d.get('strength') or '*[NULL]*'
    fm = d.get('form')
    md_lines.append(f'| {i} | `{oid}` | {lnum} | {src.get("source_id")} | {src.get("page")} | {ing} | {st} | `{fm}` |')

md_lines.append('\n---\n')

# Section 4: Raw JSONL blocks for all null items to facilitate batch editing
md_lines.append('## 4. Bloco com Todas as Linhas JSONL para Cópia e Edição em Massa\n')
md_lines.append('As linhas abaixo estão em formato JSONL puro (uma linha por registro). Você pode editar os campos diretamente e colar no arquivo original:\n')
md_lines.append('```jsonl')
seen = set()
for oid, lnum, rline, d in null_strength_all + null_form_all:
    if oid not in seen:
        seen.add(oid)
        md_lines.append(rline)
md_lines.append('```\n')

# Write output
out_file = Path('.docs/ocorrencias-para-edicao.md')
out_file.write_text('\n'.join(md_lines), encoding='utf-8')
print(f'File written successfully: {out_file} ({out_file.stat().st_size:,} bytes)')
