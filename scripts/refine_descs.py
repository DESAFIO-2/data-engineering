import json
import re
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
            if len(cols) >= 9 and cols[4] == 'F03':
                t2_rows.append(cols)

# We can find the exact channels from occurrences.jsonl for each occurrence!
# In occurrences.jsonl, occ['channel'] is already known for almost all occurrences!
# So any text matching or following occ['channel'] can be cleanly cut off!

# Let's inspect the remaining trailing groups
# Let's see what trailing texts appear
cleaned_descs = {}
for r in t2_rows:
    oid = r[2].replace('`', '')
    occ = occs.get(oid, {})
    row_num = occ.get('source_row_number')
    block = parsed_items.get(row_num, '')
    lines_b = [l.strip() for l in block.splitlines() if l.strip()]
    
    # skip code lines
    idx = 0
    while idx < len(lines_b):
        line = lines_b[idx]
        if re.match(r'^(?:(?:MS|MSE|S|M)?\d{3,6}\s*)+$', line, re.IGNORECASE) or (idx == 0 and re.match(r'^(?:MS|MSE)?[A-Z0-9]+$', line)):
            idx += 1
        else:
            break
            
    # From idx onwards, let's find where channel starts
    ch = occ.get('channel')
    full_text = " ".join(lines_b[idx:])
    
    # If channel in full_text, cut before channel
    if ch and ch in full_text:
        full_text = full_text[:full_text.index(ch)].strip()
    elif ch:
        # try first word of channel if >= 5 chars
        ch_word = ch.split()[0]
        if len(ch_word) >= 5 and ch_word in full_text:
            full_text = full_text[:full_text.index(ch_word)].strip()
            
    cleaned_descs[oid] = (row_num, full_text)

with open('scripts/cleaned_descs.json', 'w', encoding='utf-8') as f:
    json.dump(cleaned_descs, f, indent=2, ensure_ascii=False)
print("Saved scripts/cleaned_descs.json")
