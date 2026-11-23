import json
import re
from pathlib import Path
import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('data/curation/archive/cleaned_descs.json', 'r', encoding='utf-8') as f:
    descs = json.load(f)

with open('data/corpus/experimental/occurrences.jsonl', 'r', encoding='utf-8') as f:
    occs = {json.loads(l)['occurrence_id']: json.loads(l) for l in f if l.strip()}

# Load candidate groups
with open('data/curation/archive/all_groups.json', 'r', encoding='utf-8') as f:
    raw_groups = json.load(f)

# Specific known groups to strip from end of description
group_endings = [
    'Inalantes adrenérgicos', 'Imunomoestimulantes', 'Meios de contraste para raios-x, iodados',
    'Outros produtos para o sistema respiratório', 'Antimetabólitos', 'Anti-infecciosos e antissépticos ginecológicos',
    'Anti-infecciosos para uso sistêmico', 'Anti-infecciosos oftálmicos', 'Anti-infecciosos',
    'Antibacterianos beta- lactâmicos, penicilinas', 'Antibacterianos beta-lactâmicos, penicilinas',
    'Antibacterianos beta- lactâmicos', 'Antibacterianos beta-lactâmicos', 'Outros antibacterianos beta-lactâmicos',
    'Antibacterianos', 'Antivirais de ação direta', 'Antivirais para tratamento de infecções por hiv, combinações',
    'Antivirais', 'Antipsoriáticos para uso sistêmico', 'Antipsoriáticos',
    'Antifúngicos para uso sistêmico', 'Antifúngicos para uso dermatológico', 'Antifúngicos',
    'Anti-inflamatórios e antirreumáticos não esteroides', 'Anti-inflamatórios e antirreumáticos',
    'Anti-inflamatórios intestinais', 'Anti-inflamatórios', 'Anti-fibrinolíticos',
    'Agentes antitrombóticos', 'Agentes antineoplásicos', 'Agentes imunossupressores',
    'Agentes antinematódeos', 'Agentes para distúrbio vascular ocular', 'Agentes emulsionantes',
    'Agentes dopaminérgicos', 'Agentes antiprotozoários',
    'Outros agentes antineoplásicos', 'Outros preparados dermatológicos',
    'Outros medicamentos do aparelho digestivo e metabolismo', 'Outros preparados antianêmicos',
    'Outros medicamentos sistêmicos para doença obstrutiva das vias aéreas',
    'Outros analgésicos e antipiréticos', 'Outros preparados ginecológicos', 'Outros medicamentos',
    'Lincosaminas e estreptograminas, macrolídeos', 'Macrolídeos, lincosamidas e estreptograminas',
    'Macrolídeos', 'Aminoglicosídeos', 'Sulfonamidas e trimetoprima', 'Tetraciclinas',
    'Quinolonas', 'Imunossupressores', 'Analgésicos opioides', 'Analgésicos',
    'Anestésicos gerais', 'Anestésicos locais', 'Anestésicos',
    'Antiepilépticos', 'Antiparkinsonianos', 'Antipsicóticos', 'Ansiolíticos',
    'Hipnóticos e sedativos', 'Antidepressivos', 'Psicoestimulantes',
    'Drogas usadas em diabetes', 'Insulinas e análogos',
    'Corticosteroides para uso sistêmico', 'Corticosteroides dermatológicos', 'Corticosteroides',
    'Terapia da tireoide', 'Hormônios tireoidianos', 'Preparações anti-tireoide',
    'Hormônios hipofisários e hipotalâmicos', 'Gonadotropinas e outros estimulantes de ovulação',
    'Preparações nasais', 'Preparações oftálmicas', 'Preparações otológicas',
    'Descongestionantes e outras preparações nasais',
    'Antiparasitários, inseticidas e repelentes', 'Ectoparasiticidas, incluindo escabicidas',
    'Anti-helmínticos', 'Antiprotozoários',
    'Sangue e produtos relacionados', 'Soluções intravenosas', 'Soluções para diálise peritoneal',
    'Substitutos do plasma e soluções para infusão fracionada',
    'Suplementos minerais', 'Vitaminas', 'Vitamina B12 e ácido fólico', 'Ácido ascórbico (vit.c, incluindo associações',
    'Produtos terapêuticos', 'Imunoglobulinas', 'Vacinas',
    'Medicamentos para o manejo da infecção pelo HIV', 'Medicamentos para a saúde da mulher',
    'Medicamentos para o tratamento da toxoplasmose', 'Medicamentos para o tratamento da tuberculose multidrogarresistente',
    'Medicamentos para o tratamento da tuberculose', 'Medicamentos para o tratamento da malária',
    'Medicamentos para o tratamento de tracoma', 'Medicamentos para o tratamento de infecções fúngicas',
    'Medicamentos para o tratamento da hanseníase', 'Medicamentos para o tratamento da hepatite',
    'Medicamentos para o tratamento da doença de chagas', 'Medicamentos para o tratamento de leishmanioses',
    'Medicamentos para o tratamento de influenza', 'Medicamentos para o tratamento de tabagismo',
    'Medicamentos para o tratamento da esquizofrenia', 'Medicamentos para o tratamento do transtorno afetivo bipolar',
    'Medicamentos para o tratamento da dor crônica', 'Medicamentos para o tratamento da anemia',
    'Medicamentos para o tratamento da asma', 'Medicamentos para o tratamento da dpoc',
    'Medicamentos para o tratamento de glaucoma', 'Medicamentos para o tratamento da osteoporose',
    'Medicamentos para o tratamento de artrite', 'Medicamentos para o tratamento de epilepsia',
    'Medicamentos para o tratamento da doença de parkinson', 'Medicamentos para o tratamento de alzheimer',
    'Medicamentos para o tratamento de dislipidemias', 'Medicamentos para o tratamento de hipertensão',
    'Medicamentos para o tratamento de diabetes', 'Medicamentos homeopáticos ou fitoterápicos',
    'Medicamentos que afetam a estrutura óssea e mineralização', 'Medicamentos que afetam a estrutura óssea',
    'Medicamento de compra exclusiva do IHBDF', 'Todos os outros produtos não terapêuticos'
]

# Sort by length descending
group_endings = sorted(group_endings, key=len, reverse=True)

forms_ordered = [
    'pó liofilizado para solução injetável', 'pó liofilizado para suspensão injetável',
    'pó para solução injetável', 'pó para suspensão injetável', 'pó liofilizado injetável',
    'pó liofilizado', 'pó para solução oral', 'pó para suspensão oral', 'pó p/ susp oral',
    'pó para inalação oral', 'pó inalante ou', 'pó inalante', 'pó inalatório', 'pó',
    'comprimido revestido de liberação prolongada', 'comprimido de liberação prolongada',
    'comprimido revestido', 'comprimido dispersível', 'comprimido mastigável', 'comprimido sublingual',
    'comprimido', 'cápsula gelatinosa dura', 'cápsula gelatinosa mole', 'cápsula com microgrânulos',
    'cápsula', 'drágea',
    'solução para infusão', 'solução injetável', 'suspensão injetável', 'emulsão injetável',
    'solução para inalação', 'solução para nebulização', 'solução nasal', 'solução oftálmica',
    'solução otológica', 'solução oral', 'solução tópica', 'solução retal', 'solução aerossol para inalação oral',
    'solução aerossol', 'solução',
    'suspensão oral', 'suspensão oftálmica', 'suspensão nasal', 'suspensão',
    'pomada oftálmica', 'pomada dermatológica', 'pomada', 'creme vaginal', 'creme dermatológico', 'creme',
    'gel oftálmico', 'gel vaginal', 'gel', 'loção cremosa', 'loção', 'xarope', 'elixir', 'spray', 'aerossol',
    'enema', 'supositório', 'óvulo', 'adesivo transdérmico', 'adesivo', 'implante',
    'frasco ou bolsa', 'frasco-ampola ou bolsa', 'frasco-ampola', 'ampola', 'tubo', 'bisnaga', 'frasco', 'bolsa', 'pote'
]

items_for_review = []
for oid, (row_num, full_text) in descs.items():
    occ = occs.get(oid, {})
    t = full_text.strip()
    
    # 1. Clean code prefixes
    t = re.sub(r'^(?:(?:MS|MSE|S|M)?\d{3,6}\*?\s*)+', '', t, flags=re.IGNORECASE).strip()
    
    # 2. Clean substitution note
    if '*será substituído' in t:
        t = t[:t.index('*será substituído')].strip()
    if '* será substituído' in t:
        t = t[:t.index('* será substituído')].strip()
    if 'será substituído pelo código' in t:
        t = t[:t.index('será substituído pelo código')].strip()
        
    # 3. Clean trailing group
    for ge in group_endings:
        if ge.lower() in t.lower():
            idx = t.lower().rfind(ge.lower())
            if idx > 15:
                t = t[:idx].strip()
                break
                
    # 4. Clean trailing channel remnants
    for cw in ['UBS', 'Uso hospitalar', 'Farmácia', 'Policlínica', 'Centro Especializado', 'Hemocentro', 'SAMU', 'para uso interno nas unidades', 'para uso interno', 'Uso exclusivo']:
        if cw.lower() in t.lower():
            idx = t.lower().rfind(cw.lower())
            if idx > 15:
                t = t[:idx].strip()
                
    t = re.sub(r'^[,\-\s]+', '', t).strip()
    t = re.sub(r'[,\-\s]+$', '', t).strip()
    t = re.sub(r'\s+', ' ', t)
    
    # Resolve ingredient
    orig_ing = occ.get('active_ingredient') or ''
    res_ing = orig_ing
    if not orig_ing or orig_ing == '*[NULL]*':
        if 'água para injetáveis' in t.lower():
            res_ing = 'água para injetáveis'
        elif 'amoxicilina' in t.lower():
            res_ing = 'amoxicilina + clavulanato de potássio'
        elif row_num == 987:
            res_ing = '[linha 987 em branco no PDF]'
    elif orig_ing.endswith('pó p/ susp oral'):
        res_ing = orig_ing.replace('pó p/ susp oral', '').strip()
    elif orig_ing.endswith('pó para inalação oral'):
        res_ing = orig_ing.replace('pó para inalação oral', '').strip()
    elif orig_ing.endswith('pó inalante ou'):
        res_ing = orig_ing.replace('pó inalante ou', '').strip()
    elif orig_ing.endswith('pó inalatório'):
        res_ing = orig_ing.replace('pó inalatório', '').strip()
        
    # Resolve form
    orig_form = occ.get('form') or ''
    res_form = orig_form
    if not orig_form or orig_form == '*[NULL]*' or orig_form == 'None':
        for f in forms_ordered:
            if re.search(rf'\b{re.escape(f)}\b', t, re.IGNORECASE):
                res_form = f
                break
    elif orig_form == 'pó p/ susp oral':
        res_form = 'pó para suspensão oral'
    elif orig_form == 'injetável':
        if 'solução injetável' in t.lower():
            res_form = 'solução injetável'
        elif 'pó para solução injetável' in t.lower():
            res_form = 'pó para solução injetável'
        elif 'suspensão injetável' in t.lower():
            res_form = 'suspensão injetável'
    if row_num == 987:
        res_form = '-'
        
    # Resolve strength
    st = t
    if res_ing and res_ing != '[linha 987 em branco no PDF]':
        st = re.sub(re.escape(res_ing), '', st, flags=re.IGNORECASE).strip()
    if res_form and res_form != '-':
        st = re.sub(rf'\b{re.escape(res_form)}\b', '', st, flags=re.IGNORECASE).strip()
    st = re.sub(r'^[,\-\s]+', '', st).strip()
    st = re.sub(r'[,\-\s]+$', '', st).strip()
    st = re.sub(r'\s+', ' ', st)
    
    if row_num == 987:
        st = '- (item 987 sem conteúdo no PDF oficial)'
    elif not st:
        st = t
        
    items_for_review.append({
        'oid': oid,
        'row_num': row_num,
        'page': occ.get('source', {}).get('page'),
        'orig_ing': orig_ing,
        'res_ing': res_ing,
        'orig_form': orig_form,
        'res_form': res_form,
        'res_st': st,
        't': t
    })

with open('data/curation/archive/review_154_items.json', 'w', encoding='utf-8') as f:
    json.dump(items_for_review, f, indent=2, ensure_ascii=False)

print(f"Generated review for {len(items_for_review)} items.")
