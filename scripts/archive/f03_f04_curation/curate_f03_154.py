import json
import re
from pathlib import Path
import sys
sys.stdout.reconfigure(encoding='utf-8')

# Read REME-DF text
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

# Read Table 2 F03 entries
md_content = Path('.docs/ocorrencias-para-edicao.md').read_text(encoding='utf-8')
s2_lines = []
in_s2 = False
for line in md_content.splitlines():
    if line.startswith('## 2.'):
        in_s2 = True
        continue
    if in_s2:
        if line.startswith('## 3.'):
            break
        s2_lines.append(line)

rows = [l for l in s2_lines if l.startswith('|') and not l.startswith('| #') and not l.startswith('| :-')]

f03_rows = []
for r in rows:
    cols = [c.strip() for c in r.split('|')]
    if cols[4] == 'F03':
        oid = cols[2].replace('`', '')
        occ = occs.get(oid, {})
        srn = occ.get('source_row_number')
        f03_rows.append((int(cols[1]), oid, srn, int(cols[5]), cols[6], cols[7]))

print(f"Loaded {len(f03_rows)} F03 items from Table 2.")
