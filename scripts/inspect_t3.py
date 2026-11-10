import json
from pathlib import Path
import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('data/corpus/experimental/occurrences.jsonl', 'r', encoding='utf-8') as f:
    occs = {json.loads(l)['occurrence_id']: json.loads(l) for l in f if l.strip()}

content = Path('.docs/ocorrencias-para-edicao.md').read_text(encoding='utf-8')
lines = content.splitlines()

s3_lines = []
in_s3 = False
for line in lines:
    if line.startswith('## 3.'):
        in_s3 = True
        continue
    if in_s3:
        if line.startswith('## 4.'):
            break
        s3_lines.append(line)

rows = [l for l in s3_lines if l.startswith('|') and not l.startswith('| #') and not l.startswith('| :-')]

print(f"Total rows in Table 3: {len(rows)}")
t3_items = []
for r in rows:
    cols = [c.strip() for c in r.split('|')]
    # cols[1]=#, cols[2]=oid, cols[3]=line, cols[4]=src, cols[5]=page, cols[6]=ing, cols[7]=st, cols[8]=form
    oid = cols[2].replace('`', '')
    occ = occs.get(oid, {})
    t3_items.append({
        'num': int(cols[1]),
        'oid': oid,
        'line': int(cols[3]),
        'src': cols[4],
        'page': int(cols[5]),
        'ing': cols[6],
        'st': cols[7],
        'form': cols[8],
        'raw': occ.get('raw_text', ''),
        'srn': occ.get('source_row_number')
    })

with open('scripts/t3_inspected.json', 'w', encoding='utf-8') as f:
    json.dump(t3_items, f, indent=2, ensure_ascii=False)

print("Saved scripts/t3_inspected.json")
