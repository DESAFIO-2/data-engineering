import json
import re
from pathlib import Path
import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('scripts/final_extracted.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

with open('scripts/all_groups.json', 'r', encoding='utf-8') as f:
    groups = json.load(f)

# Sort groups by length descending
groups = sorted([g for g in groups if len(g) > 4], key=len, reverse=True)

cleaned_strengths = {}
for oid, info in data.items():
    st = info['resolved_st']
    ing = info['resolved_ing']
    fm = info['resolved_form']
    row_num = info['row_num']
    
    # Strip any group that appears at the end of st
    for g in groups:
        if g.lower() in st.lower():
            idx = st.lower().find(g.lower())
            # only cut if it's near the end or after a dosage pattern
            if idx > 3:
                st = st[:idx].strip()
                
    # Also clean notes like *será substituído...
    if '*será substituído' in st:
        st = st[:st.index('*será substituído')].strip()
    if '* será substituído' in st:
        st = st[:st.index('* será substituído')].strip()
    if 'será substituído pelo código' in st:
        st = st[:st.index('será substituído pelo código')].strip()
        
    # Clean trailing punctuation
    st = re.sub(r'^[,\-\s]+', '', st).strip()
    st = re.sub(r'[,\-\s]+$', '', st).strip()
    st = re.sub(r'\s+', ' ', st)
    
    cleaned_strengths[oid] = {
        'row_num': row_num,
        'page': info['page'],
        'ing': ing,
        'form': fm,
        'strength': st
    }

with open('scripts/cleaned_strengths_final.json', 'w', encoding='utf-8') as f:
    json.dump(cleaned_strengths, f, indent=2, ensure_ascii=False)

print(f"Total cleaned: {len(cleaned_strengths)}")
for oid, item in list(cleaned_strengths.items())[:25]:
    print(f"#{item['row_num']} [{oid}] | Ing: {item['ing']} | Form: {item['form']} | St: {item['strength']}")
