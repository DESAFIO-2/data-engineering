import re
import json
from pathlib import Path

content = Path('data/raw/F03-reme-df/reme-df-2026-10-29.txt').read_text(encoding='utf-8')
p12_pos = content.find('--- PÁGINA 12 DE 98 ---')
p60_pos = content.find('--- PÁGINA 60 DE 98 ---')
sub_a = content[p12_pos:p60_pos]

clean_sub_a = re.sub(r'--- PÁGINA \d+ DE \d+ ---\s*', '', sub_a)
clean_sub_a = re.sub(r'^\s*\d+\s*$', '', clean_sub_a, flags=re.MULTILINE)
clean_sub_a = re.sub(r'Subseção “a”: Relação Distrital de Medicamentos - SES-DF\s*', '', clean_sub_a)
clean_sub_a = re.sub(r'Na subseção “a”, a Reme é apresentada.*?(?=ITEM|\d+\.)', '', clean_sub_a, flags=re.DOTALL)

item_regex = re.compile(r'^\s*(\d+)\.\s*$', re.MULTILINE)
matches = list(item_regex.finditer(clean_sub_a))

parsed_items = {}
for i, m in enumerate(matches):
    num = int(m.group(1))
    start = m.end()
    end = matches[i+1].start() if i+1 < len(matches) else len(clean_sub_a)
    block = clean_sub_a[start:end].strip()
    parsed_items[num] = block

with open('data/corpus/experimental/occurrences.jsonl', 'r', encoding='utf-8') as f:
    occs = {json.loads(l)['occurrence_id']: json.loads(l) for l in f if l.strip()}

content_md = Path('.docs/ocorrencias-para-edicao.md').read_text(encoding='utf-8')
lines = content_md.splitlines()

in_table_2 = False
t2_rows = []
for line in lines:
    if line.startswith('## 2. Todas as Ocorrências'):
        in_table_2 = True
        continue
    if in_table_2:
        if line.startswith('## 3.'):
            break
        if line.startswith('|') and not line.startswith('| #') and not line.startswith('| :-'):
            cols = [c.strip() for c in line.split('|')]
            if len(cols) >= 9 and cols[4] == 'F03':
                t2_rows.append(cols)

# Define known forms ordered by specificity
forms_ordered = [
    'pó liofilizado para solução injetável', 'pó liofilizado para suspensão injetável',
    'pó para solução injetável', 'pó para suspensão injetável', 'pó liofilizado injetável',
    'pó liofilizado', 'pó para solução oral', 'pó para suspensão oral', 'pó p/ susp oral',
    'pó para inalação oral', 'pó inalante', 'pó inalatório', 'pó',
    'comprimido revestido de liberação prolongada', 'comprimido de liberação prolongada',
    'comprimido revestido', 'comprimido dispersível', 'comprimido mastigável', 'comprimido sublingual',
    'comprimido', 'cápsula gelatinosa dura', 'cápsula gelatinosa mole', 'cápsula com microgrânulos',
    'cápsula', 'drágea',
    'solução para infusão', 'solução injetável', 'suspensão injetável', 'emulsão injetável',
    'solução para inalação', 'solução para nebulização', 'solução nasal', 'solução oftálmica',
    'solução otológica', 'solução oral', 'solução tópica', 'solução retal', 'solução',
    'suspensão oral', 'suspensão oftálmica', 'suspensão nasal', 'suspensão',
    'pomada oftálmica', 'pomada', 'creme vaginal', 'creme dermatológico', 'creme',
    'gel oftálmico', 'gel vaginal', 'gel', 'loção cremosa', 'loção', 'xarope', 'elixir', 'spray', 'aerossol',
    'enema', 'supositório', 'óvulo', 'adesivo transdérmico', 'adesivo', 'implante',
    'frasco ou bolsa', 'frasco ampola ou bolsa', 'frasco-ampola', 'ampola', 'tubo', 'bisnaga', 'frasco', 'bolsa', 'pote'
]

group_prefixes = [
    'Medicamentos para', 'Antibacterianos', 'Antivirais', 'Anti-infecciosos', 'Antifúngicos',
    'Outros agentes antineoplásicos', 'Antineoplásicos', 'Imunossupressores', 'Analgésicos',
    'Anti-inflamatórios', 'Antipsoriáticos', 'Agentes', 'Outros preparados', 'Vitamina',
    'Anti-fibrinolíticos', 'Sangue e produtos', 'Gonadotropinas', 'Expectorantes',
    'Outros medicamentos', 'Todos os outros produtos', 'Medicamento de compra', 'Insulinas',
    'Preparações antidiabéticas', 'Preparações nasais', 'Preparações oftálmicas',
    'Preparações otológicas', 'Anestésicos', 'Antiepilépticos', 'Antiparkinsonianos',
    'Antipsicóticos', 'Ansiolíticos', 'Hipnóticos e sedativos', 'Antidepressivos',
    'Psicoestimulantes', 'Medicamentos usados em dependência', 'Drogas contra demência',
    'Outros medicamentos do sistema nervoso', 'Antiprotozoários', 'Anti-helmínticos',
    'Suplementos minerais', 'Corticosteroides', 'Terapia da tireoide', 'Hormônios pancreáticos',
    'Reguladores do cálcio', 'Outros hormônios', 'Imunoglobulinas', 'Vacinas',
    'Medicamentos cardiovasculares', 'Diuréticos', 'Betabloqueadores', 'Bloqueadores dos canais de cálcio',
    'Agentes que atuam no sistema renina-angiotensina', 'Agentes modificadores de lipídios',
    'Medicamentos para distúrbios funcionais gastrointestinais', 'Antieméticos',
    'Laxantes', 'Antidiarreicos', 'Antiácidos', 'Outros'
]

def clean_item_text(block):
    lines = [l.strip() for l in block.splitlines() if l.strip()]
    if not lines: return ""
    idx = 0
    while idx < len(lines):
        line = lines[idx]
        if re.match(r'^(?:(?:MS|MSE|S|M)?\d{3,6}\s*)+$', line, re.IGNORECASE) or (idx == 0 and re.match(r'^(?:MS|MSE)?[A-Z0-9]+$', line)):
            idx += 1
        else:
            break
    desc_lines = []
    for l in lines[idx:]:
        if any(l.startswith(gp) for gp in group_prefixes):
            break
        if any(l.startswith(cw) for cw in ['UBS', 'Uso hospitalar', 'Farmácia', 'Policlínica', 'Centro Especializado', 'Hemocentro', 'SAMU', 'para uso interno', 'Uso exclusivo']):
            break
        desc_lines.append(l)
    return " ".join(desc_lines)

# Process all 154 F03 items and write full inspection to JSON
f03_processed = {}
for r in t2_rows:
    oid = r[2].replace('`', '')
    occ = occs.get(oid, {})
    row_num = occ.get('source_row_number')
    block = parsed_items.get(row_num, '')
    desc = clean_item_text(block)
    
    orig_ing = r[6]
    orig_form = r[7]
    
    # 1. Resolve Active Ingredient
    new_ing = orig_ing
    if 'NULL' in orig_ing:
        if 'água para injetáveis' in desc.lower():
            new_ing = 'água para injetáveis'
        elif 'amoxicilina' in desc.lower():
            new_ing = 'amoxicilina + clavulanato de potássio'
    elif orig_ing.endswith('pó p/ susp oral'):
        new_ing = orig_ing.replace('pó p/ susp oral', '').strip()
    elif orig_ing.endswith('pó para inalação oral'):
        new_ing = orig_ing.replace('pó para inalação oral', '').strip()
    elif orig_ing.endswith('pó inalante ou'):
        new_ing = orig_ing.replace('pó inalante ou', '').strip()
    elif orig_ing.endswith('pó inalatório'):
        new_ing = orig_ing.replace('pó inalatório', '').strip()
        
    # 2. Resolve Form
    new_form = orig_form
    desc_lower = desc.lower()
    if 'NULL' in orig_form or orig_form == 'None' or not orig_form:
        for f in forms_ordered:
            if f in desc_lower:
                new_form = f
                break
    elif orig_form == 'pó p/ susp oral':
        new_form = 'pó para suspensão oral'
    elif orig_form == 'injetável':
        if 'solução injetável' in desc_lower:
            new_form = 'solução injetável'
        elif 'pó para solução injetável' in desc_lower:
            new_form = 'pó para solução injetável'
        elif 'suspensão injetável' in desc_lower:
            new_form = 'suspensão injetável'
            
    # 3. Resolve Strength
    # Remove ingredient and form with boundaries
    remainder = desc
    clean_ing = new_ing.replace('*', '').strip()
    # Remove code if still present
    code = occ.get('source_code', '')
    if code:
        remainder = re.sub(rf'\b{re.escape(code)}\b', '', remainder, flags=re.IGNORECASE).strip()
    # Remove ingredient
    remainder = re.sub(re.escape(clean_ing), '', remainder, flags=re.IGNORECASE).strip()
    # Remove form
    clean_form = new_form.replace('*', '').strip()
    if clean_form and 'NULL' not in clean_form:
        remainder = re.sub(rf'\b{re.escape(clean_form)}\b', '', remainder, flags=re.IGNORECASE).strip()
        
    # Cleanup remainder
    remainder = re.sub(r'^[,\-\s]+', '', remainder).strip()
    remainder = re.sub(r'[,\-\s]+$', '', remainder).strip()
    # clean extra internal whitespace
    remainder = re.sub(r'\s+', ' ', remainder)
    
    # If remainder is empty or just punctuation, fallback to raw_text regex or desc
    if not remainder:
        remainder = desc
        
    f03_processed[oid] = {
        'row_num': row_num,
        'page': occ.get('source', {}).get('page'),
        'resolved_ing': new_ing,
        'resolved_form': new_form,
        'resolved_st': remainder,
        'raw_desc': desc
    }

with open('data/curation/archive/f03_processed.json', 'w', encoding='utf-8') as f:
    json.dump(f03_processed, f, indent=2, ensure_ascii=False)
print("Saved data/curation/archive/f03_processed.json successfully!")
