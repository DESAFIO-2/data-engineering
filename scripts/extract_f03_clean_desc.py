import re
import json
from pathlib import Path

# Load REME-DF text
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
            if len(cols) >= 9:
                t2_rows.append(cols)

# Pharm groups start with these prefixes
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

def extract_desc_clean(row_num):
    block = parsed_items.get(row_num, '')
    lines = [l.strip() for l in block.splitlines() if l.strip()]
    if not lines:
        return ""
    # skip code lines
    idx = 0
    while idx < len(lines):
        line = lines[idx]
        if re.match(r'^(?:(?:MS|MSE|S|M)?\d{3,6}\s*)+$', line, re.IGNORECASE) or (idx == 0 and re.match(r'^(?:MS|MSE)?[A-Z0-9]+$', line)):
            idx += 1
        else:
            break
            
    desc_lines = []
    for l in lines[idx:]:
        # check if line starts a group
        is_group = False
        for gp in group_prefixes:
            if l.startswith(gp):
                is_group = True
                break
        if is_group:
            break
        # also check channel words
        if any(l.startswith(cw) for cw in ['UBS', 'Uso hospitalar', 'Farmácia', 'Policlínica', 'Centro Especializado', 'Hemocentro', 'SAMU', 'para uso interno', 'Uso exclusivo']):
            break
        desc_lines.append(l)
    return " ".join(desc_lines)

f03_results = []
for r in t2_rows:
    if r[4] != 'F03':
        continue
    oid = r[2].replace('`', '')
    occ = occs.get(oid, {})
    row_num = occ.get('source_row_number')
    desc = extract_desc_clean(row_num)
    f03_results.append({
        'oid': oid,
        'row_num': row_num,
        'orig_ing': r[6],
        'orig_form': r[7],
        'desc': desc
    })

print(f"Total F03 extracted: {len(f03_results)}")
with open('scripts/f03_extracted_check.json', 'w', encoding='utf-8') as f:
    json.dump(f03_results, f, indent=2, ensure_ascii=False)
print("Saved scripts/f03_extracted_check.json")
