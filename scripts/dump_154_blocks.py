import json
import re
from pathlib import Path
import sys
sys.path.append('.')
sys.stdout.reconfigure(encoding='utf-8')

from scripts.curate_f03_154 import parsed_items, f03_rows, occs

results = []
for t2_idx, oid, srn, page, ing, form in f03_rows:
    block = parsed_items.get(srn, '')
    lines = [l.strip() for l in block.splitlines() if l.strip()]
    one_line = " ".join(lines)
    results.append({
        't2_idx': t2_idx,
        'oid': oid,
        'srn': srn,
        'page': page,
        'curr_ing': ing,
        'curr_form': form,
        'raw_block': one_line
    })

print(f"Total items: {len(results)}")
with open('scripts/all_154_blocks.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print("Saved scripts/all_154_blocks.json")
