import re
import json

with open('data/curation/archive/cleaned_descs.json', 'r', encoding='utf-8') as f:
    descs = json.load(f)

with open('data/corpus/experimental/occurrences.jsonl', 'r', encoding='utf-8') as f:
    occs = {json.loads(l)['occurrence_id']: json.loads(l) for l in f if l.strip()}

# All known pharmacological groups in REME-DF
known_groups = [
    'Medicamentos para o manejo da infecção pelo HIV', 'Medicamentos para a saúde da mulher',
    'Medicamentos para o tratamento da toxoplasmose', 'Medicamentos para o tratamento da tuberculose',
    'Medicamentos para o tratamento da malária', 'Medicamentos para o tratamento de tracoma',
    'Medicamentos para o tratamento de infecções fúngicas', 'Medicamentos para o tratamento da hanseníase',
    'Medicamentos para o tratamento da hepatite', 'Medicamentos para o tratamento da doença de chagas',
    'Medicamentos para o tratamento de leishmanioses', 'Medicamentos para o tratamento de influenza',
    'Medicamentos para o tratamento de tabagismo', 'Medicamentos para o tratamento da esquizofrenia',
    'Medicamentos para o tratamento do transtorno afetivo bipolar', 'Medicamentos para o tratamento da dor crônica',
    'Medicamentos para o tratamento da anemia', 'Medicamentos para o tratamento da asma',
    'Medicamentos para o tratamento da dpoc', 'Medicamentos para o tratamento de glaucoma',
    'Medicamentos para o tratamento da osteoporose', 'Medicamentos para o tratamento de artrite',
    'Medicamentos para o tratamento de epilepsia', 'Medicamentos para o tratamento da doença de parkinson',
    'Medicamentos para o tratamento de alzheimer', 'Medicamentos para o tratamento de dislipidemias',
    'Medicamentos para o tratamento de hipertensão', 'Medicamentos para o tratamento de diabetes',
    'Medicamentos homeopáticos ou fitoterápicos', 'Medicamentos que afetam a estrutura óssea e mineralização',
    'Medicamentos que afetam a estrutura óssea', 'Medicamento de compra exclusiva do IHBDF',
    'Todos os outros produtos não terapêuticos', 'Outros preparados dermatológicos',
    'Outros medicamentos do aparelho digestivo e metabolismo', 'Outros preparados antianêmicos',
    'Outros medicamentos sistêmicos para doença obstrutiva das vias aéreas',
    'Outros agentes antineoplásicos', 'Outros preparados ginecológicos', 'Outros analgésicos e antipiréticos',
    'Antibacterianos beta- lactâmicos, penicilinas', 'Antibacterianos beta-lactâmicos, penicilinas',
    'Antibacterianos beta- lactâmicos', 'Antibacterianos beta-lactâmicos',
    'Outros antibacterianos beta-lactâmicos', 'Antibacterianos',
    'Antivirais de ação direta', 'Antivirais para tratamento de infecções por hiv, combinações', 'Antivirais',
    'Anti-infecciosos e antissépticos ginecológicos', 'Anti-infecciosos para uso sistêmico',
    'Anti-infecciosos oftálmicos', 'Anti-infecciosos', 'Antipsoriáticos para uso sistêmico', 'Antipsoriáticos',
    'Antifúngicos para uso sistêmico', 'Antifúngicos para uso dermatológico', 'Antifúngicos',
    'Anti-inflamatórios e antirreumáticos não esteroides', 'Anti-inflamatórios e antirreumáticos',
    'Anti-inflamatórios intestinais', 'Anti-inflamatórios', 'Anti-fibrinolíticos',
    'Agentes antitrombóticos', 'Agentes antineoplásicos', 'Agentes imunossupressores',
    'Agentes antinematódeos', 'Agentes para distúrbio vascular ocular', 'Agentes emulsionantes',
    'Agentes dopaminérgicos', 'Agentes antiprotozoários',
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
    'Produtos terapêuticos', 'Imunoglobulinas', 'Vacinas'
]

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
    'pomada oftálmica', 'pomada dermatológica', 'pomada', 'creme vaginal', 'creme dermatológico', 'creme',
    'gel oftálmico', 'gel vaginal', 'gel', 'loção cremosa', 'loção', 'xarope', 'elixir', 'spray', 'aerossol',
    'enema', 'supositório', 'óvulo', 'adesivo transdérmico', 'adesivo', 'implante',
    'frasco ou bolsa', 'frasco-ampola ou bolsa', 'frasco-ampola', 'ampola', 'tubo', 'bisnaga', 'frasco', 'bolsa', 'pote'
]

def clean_desc_final(text):
    t = text
    # strip channel words
    for cw in ['UBS (farmácia interna)', 'UBS (farmácia ambulatorial)', 'UBS', 'Uso hospitalar', 'Farmácia', 'Policlínica', 'Centro Especializado', 'Hemocentro', 'SAMU', 'para uso interno nas unidades', 'para uso interno', 'Uso exclusivo']:
        if cw in t:
            t = t[:t.index(cw)].strip()
            
    # strip known groups
    for kg in sorted(known_groups, key=len, reverse=True):
        if kg.lower() in t.lower():
            # cut before group
            idx = t.lower().index(kg.lower())
            t = t[:idx].strip()
            
    # also strip generic group patterns
    m_grp = re.search(r'\b(Medicamentos|Antibacterianos|Antivirais|Anti-infecciosos|Anti-inflamatórios|Outros agentes|Outros preparados|Agentes|Lincosaminas|Imunossupressores|Anestésicos|Antipsicóticos|Antidepressivos|Corticosteroides|Hormônios|Sangue|Suplementos|Vitaminas|Todos os outros produtos)\b.*$', t, re.IGNORECASE)
    if m_grp:
        # check if it's not part of the active ingredient name
        # active ingredients don't usually start with these words except 'ácido' etc.
        grp_start = m_grp.start()
        # if after position 10, it's almost certainly the group column
        if grp_start > 15:
            t = t[:grp_start].strip()
            
    # clean punctuation
    t = re.sub(r'^[,\-\s]+', '', t).strip()
    t = re.sub(r'[,\-\s]+$', '', t).strip()
    return t

final_extracted = {}
for oid, (row_num, text) in descs.items():
    occ = occs.get(oid, {})
    ing_curr = occ.get('active_ingredient') or ''
    form_curr = occ.get('form') or ''
    
    cleaned = clean_desc_final(text)
    
    # 1. Resolve ingredient
    resolved_ing = ing_curr
    if not ing_curr or ing_curr == '*[NULL]*':
        if 'água para injetáveis' in cleaned.lower():
            resolved_ing = 'água para injetáveis'
        elif 'amoxicilina' in cleaned.lower():
            resolved_ing = 'amoxicilina + clavulanato de potássio'
        elif row_num == 987:
            resolved_ing = '[linha 987 sem conteúdo no PDF oficial]'
    elif ing_curr.endswith('pó p/ susp oral'):
        resolved_ing = ing_curr.replace('pó p/ susp oral', '').strip()
    elif ing_curr.endswith('pó para inalação oral'):
        resolved_ing = ing_curr.replace('pó para inalação oral', '').strip()
    elif ing_curr.endswith('pó inalante ou'):
        resolved_ing = ing_curr.replace('pó inalante ou', '').strip()
    elif ing_curr.endswith('pó inalatório'):
        resolved_ing = ing_curr.replace('pó inalatório', '').strip()
        
    # 2. Resolve form
    resolved_form = form_curr
    if not form_curr or form_curr == '*[NULL]*' or form_curr == 'None':
        for f in forms_ordered:
            if f in cleaned.lower():
                resolved_form = f
                break
    elif form_curr == 'pó p/ susp oral':
        resolved_form = 'pó para suspensão oral'
    elif form_curr == 'injetável':
        if 'solução injetável' in cleaned.lower():
            resolved_form = 'solução injetável'
        elif 'pó para solução injetável' in cleaned.lower():
            resolved_form = 'pó para solução injetável'
        elif 'suspensão injetável' in cleaned.lower():
            resolved_form = 'suspensão injetável'
    if row_num == 987:
        resolved_form = '-'
        
    # 3. Resolve strength
    rem = cleaned
    if resolved_ing and resolved_ing != '[linha 987 sem conteúdo no PDF oficial]':
        rem = re.sub(re.escape(resolved_ing), '', rem, flags=re.IGNORECASE).strip()
    if resolved_form and resolved_form != '-':
        rem = re.sub(rf'\b{re.escape(resolved_form)}\b', '', rem, flags=re.IGNORECASE).strip()
    code = occ.get('source_code', '')
    if code:
        rem = re.sub(rf'\b{re.escape(code)}\b', '', rem, flags=re.IGNORECASE).strip()
    rem = re.sub(r'^[,\-\s]+', '', rem).strip()
    rem = re.sub(r'[,\-\s]+$', '', rem).strip()
    rem = re.sub(r'\s+', ' ', rem)
    
    if row_num == 987:
        rem = '- (item 987 sem conteúdo no PDF oficial)'
    elif not rem:
        rem = cleaned
        
    final_extracted[oid] = {
        'row_num': row_num,
        'page': occ.get('source', {}).get('page'),
        'resolved_ing': resolved_ing,
        'resolved_form': resolved_form,
        'resolved_st': rem,
        'cleaned_desc': cleaned
    }

with open('data/curation/archive/final_extracted.json', 'w', encoding='utf-8') as f:
    json.dump(final_extracted, f, indent=2, ensure_ascii=False)
print("Saved data/curation/archive/final_extracted.json")
