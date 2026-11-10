import re
import json

content = open('data/raw/F03-reme-df/reme-df-2026-10-29.txt', encoding='utf-8').read()
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

# Let's inspect the last lines of blocks (pharmacy channel) vs second to last (group)
# In each block, the channel starts with known keywords like UBS, Uso hospitalar, etc.
channel_keywords = [
    'UBS', 'Uso hospitalar', 'Farmácia', 'Policlínica', 'Centro Especializado',
    'Hemocentro', 'SAMU', 'para uso interno nas unidades', 'para uso interno',
    'Uso exclusivo', 'CEDIN', 'HUB', 'Unidades Básicas', 'Programa de Malária'
]

groups_found = set()
for num, block in parsed_items.items():
    lines = [l.strip() for l in block.splitlines() if l.strip()]
    # find where channel starts
    ch_idx = len(lines)
    for idx, l in enumerate(lines):
        if any(l.startswith(ck) for ck in channel_keywords):
            ch_idx = idx
            break
    # the lines before ch_idx (excluding code and description) are the pharmacological group
    # Usually the group is 1-3 lines right before ch_idx
    if ch_idx > 1:
        # candidate group line is at ch_idx - 1 (and possibly ch_idx - 2)
        candidate = lines[ch_idx - 1]
        groups_found.add(candidate)
        if ch_idx > 2:
            groups_found.add(lines[ch_idx - 2] + " " + candidate)

print(f"Total candidate group strings found: {len(groups_found)}")
with open('scripts/all_groups.json', 'w', encoding='utf-8') as f:
    json.dump(sorted(list(groups_found), key=len, reverse=True), f, indent=2, ensure_ascii=False)
