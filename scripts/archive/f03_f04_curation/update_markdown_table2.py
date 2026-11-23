import json
import re
from pathlib import Path
import sys
sys.stdout.reconfigure(encoding='utf-8')

# 1. Load curated F03 data
with open('data/curation/archive/curated_f03_final.json', 'r', encoding='utf-8') as f:
    curated_f03 = json.load(f)

# 2. Curated F04 data
curated_f04 = {
    'occ-bd645fca4e10b51f38485f06': {
        'ing': 'etinilestradiol + levonorgestrel',
        'form': 'comprimido',
        'st': '0,03 mg + 0,15 mg'
    },
    'occ-2e237469ad52f38dc54b786e': {
        'ing': 'valerato de estradiol + enantato de noretisterona',
        'form': 'solução injetável',
        'st': '5 mg + 50 mg (ampola 1 mL)'
    },
    'occ-31f830e7fbb52c0353da2946': {
        'ing': 'carbidopa + levodopa',
        'form': 'comprimido',
        'st': '25 mg + 250 mg'
    },
    'occ-e7d83368e51a7cb974fd6bd9': {
        'ing': 'cloridrato de benserazida + levodopa',
        'form': 'comprimido ou cápsula',
        'st': '25 mg + 100 mg'
    },
    'occ-8b27e582e2c9bd191869b342': {
        'ing': 'absorvente higiênico (dignidade menstrual)',
        'form': 'unidade',
        'st': '- (insumo de higiene / dignidade menstrual)'
    },
    'occ-5ea8a977695dbad521b67f97': {
        'ing': 'fralda geriátrica (incontinência urinária)',
        'form': 'unidade',
        'st': '- (insumo para incontinência urinária)'
    }
}

# 3. Read markdown content
content = Path('.docs/ocorrencias-para-edicao.md').read_text(encoding='utf-8')
lines = content.splitlines()

s2_start = None
s2_end = None
for i, l in enumerate(lines):
    if l.startswith('## 2. Todas as Ocorrências'):
        s2_start = i
    elif s2_start is not None and l.startswith('## 3.'):
        s2_end = i
        break

if s2_start is None or s2_end is None:
    raise ValueError("Could not find start and end of Section 2 in markdown file!")

# Find table rows inside Section 2
new_s2_lines = []
note_added = False

for idx in range(s2_start, s2_end):
    line = lines[idx]
    
    # Add an explicit note right after the header of Section 2
    if line.startswith('Total encontrado:') and not note_added:
        new_s2_lines.append(line)
        new_s2_lines.append('')
        new_s2_lines.append('> [!NOTE]')
        new_s2_lines.append('> **Legenda e Convenção Visual:**')
        new_s2_lines.append('> Os valores preenchidos/extraídos diretamente dos PDFs oficiais (**REME-DF** `reme-df-2026-10-29.pdf` e **PFPB** `farmacia-popular-elenco-2026-08-31.pdf`) foram inseridos explicitamente em **_negrito e itálico_** (`***valor***`) para que você possa identificar de imediato todos os campos que foram preenchidos pelo assistente durante a extração.')
        note_added = True
        continue
        
    if line.startswith('|') and not line.startswith('| #') and not line.startswith('| :-'):
        cols = [c.strip() for c in line.split('|')]
        # cols: ['', num, oid, line, src, page, ing, form, st, '']
        if len(cols) >= 9:
            row_num = cols[1]
            oid = cols[2].replace('`', '')
            src_line = cols[3]
            src = cols[4]
            page = cols[5]
            curr_ing = cols[6]
            curr_form = cols[7]
            curr_st = cols[8]
            
            if src == 'F03' and oid in curated_f03:
                data = curated_f03[oid]
                new_ing = f"***{data['ing']}***"
                new_form = f"***{data['form']}***"
                new_st = f"***{data['st']}***"
                new_line = f"| {row_num} | `{oid}` | {src_line} | {src} | {page} | {new_ing} | {new_form} | {new_st} |"
                new_s2_lines.append(new_line)
                continue
            elif src == 'F04' and oid in curated_f04:
                data = curated_f04[oid]
                new_ing = f"***{data['ing']}***"
                new_form = f"***{data['form']}***"
                new_st = f"***{data['st']}***"
                new_line = f"| {row_num} | `{oid}` | {src_line} | {src} | {page} | {new_ing} | {new_form} | {new_st} |"
                new_s2_lines.append(new_line)
                continue
    new_s2_lines.append(line)

# Also update the card headers in Section 1 for the 12 selected items so they show the filled values
new_all_lines = lines[:s2_start] + new_s2_lines + lines[s2_end:]

# Update Section 1 cards
all_text = "\n".join(new_all_lines)

# For each item in F03 and F04 that appears in Section 1, update its card fields
for oid, data in {**curated_f03, **curated_f04}.items():
    card_pattern = rf'(### 1\.\d+ `{re.escape(oid)}`.*?\n)(.*?)(?=\n\*\*JSON Formatado)'
    match = re.search(card_pattern, all_text, flags=re.DOTALL)
    if match:
        card_header = match.group(1)
        card_body = match.group(2)
        # Update Princípio Ativo, Concentração, Forma Farmacêutica
        new_body = re.sub(r'(- \*\*Princípio Ativo:\*\* ).*', rf'\g<1>***{data["ing"]}***', card_body)
        new_body = re.sub(r'(- \*\*Concentração \(`strength`\):\*\* ).*', rf'\g<1>***{data["st"]}***', new_body)
        new_body = re.sub(r'(- \*\*Forma Farmacêutica \(`form`\):\*\* ).*', rf'\g<1>***{data["form"]}***', new_body)
        all_text = all_text.replace(match.group(0), card_header + new_body)

Path('.docs/ocorrencias-para-edicao.md').write_text(all_text, encoding='utf-8')
print("Successfully updated .docs/ocorrencias-para-edicao.md with curated F03 and F04 data in Table 2 and Section 1!")
