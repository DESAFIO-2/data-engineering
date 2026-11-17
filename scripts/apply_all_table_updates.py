import json
import re
from pathlib import Path
import sys
sys.stdout.reconfigure(encoding='utf-8')

# 1. Update build_curated_t3_all logic with the 4 factor items
with open('data/curation/archive/curated_t3_all.json', 'r', encoding='utf-8') as f:
    curated_t3 = json.load(f)

# Fix the 4 factor items
curated_t3['12']['ing'] = 'complexo protrombínico humano'
curated_t3['12']['st'] = '500 UI a 600 UI'

curated_t3['19']['ing'] = 'concentrado de fator VIII para doença de von willebrand'
curated_t3['19']['st'] = '450 UI a 500 UI'

curated_t3['25']['ing'] = 'concentrado plasmático de fator IX'
curated_t3['25']['st'] = '200 UI a 250 UI'

curated_t3['26']['ing'] = 'concentrado plasmático de fator IX'
curated_t3['26']['st'] = '500 UI a 600 UI'

with open('data/curation/archive/curated_t3_all.json', 'w', encoding='utf-8') as f:
    json.dump(curated_t3, f, indent=2, ensure_ascii=False)

# 2. Function to clean Table 2 strength
def clean_t2_strength(st_str):
    val = st_str.replace('***', '').strip()
    if val in ['-', '- (item 987 sem conteúdo no PDF oficial)', '- (insumo de higiene / dignidade menstrual)', '- (insumo para incontinência urinária)']:
        return st_str
    
    # Specific known fixes
    if 'sistema de aplicação 3mL' in val or 'sistema de aplicação 3 mL' in val:
        return '***6 mg/mL (sistema de aplicação 3 mL)***'
    if '150 mg + isoniazida 75 mg + pirazinamida 400 mg + etambutol 275 mg' in val:
        return '***150 mg + 75 mg + 400 mg + 275 mg***'
    if '150 mg + isoniazida 75 mg' in val:
        return '***150 mg + 75 mg***'
    if '300 mg + isoniazida 150 mg' in val:
        return '***300 mg + 150 mg***'
    if '75 mg + isoniazida 50 mg + pirazinamida 150 mg' in val:
        return '***75 mg + 50 mg + 150 mg***'
    if '75 mg + isoniazida 50 mg' in val:
        return '***75 mg + 50 mg***'
    if 'artemeter + lumefantrina' in val or '20 mg + 120 mg' in val:
        return '***20 mg + 120 mg***'
    if '0,03 mg + 0,15 mg blister com 21 comprimidos' in val:
        return '***0,03 mg + 0,15 mg***'
    if '(150 mg x 2) + 100 mg' in val:
        return '***(150 mg x 2) + 100 mg***'

    # General regex clean
    val = re.sub(r'\s*-\s*(?:tuberculose|malária|hiv|hepatite\s*[a-c]|tracoma|covid-19|coagulopatias|deficiencias nutricionais|prevençao de deficiencias nutricionais).*', '', val, flags=re.IGNORECASE)
    val = re.sub(r'\s*\((?:indicação:?\s*[^)]+|covid-19|malária|tuberculose|hiv|coagulopatias|exclusivo\s*[^)]+)\)', '', val, flags=re.IGNORECASE)
    val = re.sub(r'\s*\(blister\s+c/\s*\d+\s+comprimidos\s*-\s*\d+\s*(?:a|-)\s*\d+\s*kg\)', '', val, flags=re.IGNORECASE)
    val = re.sub(r'\s*blister\s+com\s+\d+\s+comprimidos', '', val, flags=re.IGNORECASE)
    val = re.sub(r'multidoses\s+de\s+até\s+[\d,\.]+\s*mg', '', val, flags=re.IGNORECASE)
    val = re.sub(r'\s+dispersível', '', val, flags=re.IGNORECASE)
    val = re.sub(r'\s*\(\s*\)', '', val)
    val = re.sub(r'\s+', ' ', val).strip()
    return f"***{val}***"

# 3. Read markdown content
content = Path('.docs/ocorrencias-para-edicao.md').read_text(encoding='utf-8')
lines = content.splitlines()

# Process line by line
new_lines = []
in_table_2 = False
in_table_3 = False
t3_note_added = False

for line in lines:
    if line.startswith('## 2. Todas as Ocorrências'):
        in_table_2 = True
        in_table_3 = False
        new_lines.append(line)
        continue
    elif line.startswith('## 3. Todas as Ocorrências'):
        in_table_2 = False
        in_table_3 = True
        new_lines.append(line)
        continue
    elif line.startswith('## 4. Bloco Completo'):
        in_table_2 = False
        in_table_3 = False
        new_lines.append(line)
        continue
        
    if in_table_2:
        if line.startswith('|') and not line.startswith('| #') and not line.startswith('| :-'):
            cols = [c.strip() for c in line.split('|')]
            if len(cols) >= 9:
                # cols: ['', num, oid, line, src, page, ing, form, st, '']
                src = cols[4]
                curr_st = cols[8]
                if src in ['F03', 'F04']:
                    cols[8] = clean_t2_strength(curr_st)
                line = " | ".join(cols).strip()
                if not line.startswith('|'):
                    line = "| " + line
                if not line.endswith('|'):
                    line = line + " |"
        new_lines.append(line)
        continue
        
    if in_table_3:
        if line.startswith('Total encontrado:') and not t3_note_added:
            new_lines.append(line)
            new_lines.append('')
            new_lines.append('> [!NOTE]')
            new_lines.append('> **Legenda e Convenção Visual:**')
            new_lines.append('> Todos os valores preenchidos/extraídos diretamente dos documentos oficiais (**REME-DF** `reme-df-2026-10-29.pdf`, **RENAME** `rename-2024-2ed.pdf` e **PFPB** `farmacia-popular-elenco-2026-08-31.pdf`) foram destacados em **_negrito e itálico_** (`***valor***`) para imediata identificação dos dados completados pelo assistente.')
            t3_note_added = True
            continue
            
        if line.startswith('|') and not line.startswith('| #') and not line.startswith('| :-'):
            cols = [c.strip() for c in line.split('|')]
            # Table 3 columns:
            # | # | ID Ocorrência | Linha | Fonte | Pág | Princípio Ativo | Concentração (`strength`) | Valor Atual `form` |
            if len(cols) >= 9:
                num_str = cols[1]
                if num_str in curated_t3:
                    data = curated_t3[num_str]
                    oid = cols[2]
                    src_line = cols[3]
                    src = cols[4]
                    page = cols[5]
                    
                    # Update fields with bold/italic
                    new_ing = f"***{data['ing']}***"
                    new_st = f"***{data['st']}***" if data['st'] != '-' else '-'
                    new_form = f"***{data['form']}***"
                    
                    line = f"| {num_str} | {oid} | {src_line} | {src} | {page} | {new_ing} | {new_st} | {new_form} |"
        new_lines.append(line)
        continue
        
    new_lines.append(line)

final_md = "\n".join(new_lines)
Path('.docs/ocorrencias-para-edicao.md').write_text(final_md, encoding='utf-8')
print("Successfully updated Table 2 and Table 3 in .docs/ocorrencias-para-edicao.md!")
