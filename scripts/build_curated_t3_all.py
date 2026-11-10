import json
import re
import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('scripts/t3_inspected.json', 'r', encoding='utf-8') as f:
    items = json.load(f)

print(f"Total items in Table 3: {len(items)}")

# Let's inspect F03 items and extract form from raw
curated_t3 = {}

for it in items:
    num = it['num']
    oid = it['oid']
    src = it['src']
    raw = it['raw']
    curr_ing = it['ing']
    curr_st = it['st']
    srn = it['srn']
    
    # Defaults
    ing = curr_ing
    st = curr_st
    form = ''
    
    if src == 'F03':
        # Clean ing if trailing form was attached
        for suffix in ['pó p/ susp oral', 'spray nasal', 'xampu', 'drágea', 'pó frasco ou envelope',
                       'pó para inalação oral', 'geleia', 'adesivo transdermico', 'aerosol para inalação',
                       'pó para inalação', 'po liofilizado', 'po', 'pó inalante']:
            if ing.lower().endswith(suffix):
                ing = ing[:len(ing)-len(suffix)].strip()
                
        # Resolve specific items
        if srn == 16:
            form = 'granulado revestido'
        elif srn in [28, 29, 30]:
            ing = 'água para injetáveis'
            if srn == 28:
                form = 'ampola'
                st = '10 mL'
            elif srn == 29:
                form = 'frasco ou bolsa'
                st = '1000 mL'
            elif srn == 30:
                form = 'frasco ou bolsa'
                st = '500 mL'
        elif srn == 38:
            form = 'frasco-ampola'
        elif srn == 83:
            ing = 'amoxicilina + clavulanato de potássio'
            form = 'pó para suspensão oral'
            st = '50 mg/mL + 12,5 mg/mL (frasco 75 ou 100 mL)'
        elif srn == 109:
            form = 'pó liofilizado para solução injetável'
        elif srn == 133:
            ing = 'beclometasona (dipropionato)'
            form = 'spray nasal'
        elif srn == 185:
            form = 'spray nasal'
        elif srn == 200:
            ing = 'carvão ativado'
            form = 'pó para suspensão oral (frasco ou envelope)'
        elif srn == 217:
            ing = 'cetoconazol'
            form = 'xampu'
        elif srn in [291, 292, 293, 294, 296, 297, 298, 299, 300, 301, 302, 303, 304, 305, 306, 307]:
            # Factors and complex
            form = 'frasco-ampola'
        elif srn == 463:
            ing = 'fluticasona (furoato) + umeclidínio (brometo) + vilanterol (trifenatato)'
            form = 'pó inalatório'
            st = '100 mcg + 62,5 mcg + 25 mcg/dose'
        elif srn == 481:
            ing = 'fórmula dietoterápica para fenilcetonúria (acima de 8 anos)'
            form = 'pó para suspensão oral'
            st = 'lata 400 g a 500 g'
        elif srn == 482:
            ing = 'fórmula dietoterápica para fenilcetonúria (1 a 8 anos)'
            form = 'pó para suspensão oral'
            st = 'lata 400 g a 500 g'
        elif srn == 483:
            ing = 'fórmula dietoterápica para fenilcetonúria (abaixo de 1 ano)'
            form = 'pó para suspensão oral'
            st = 'lata 400 g a 500 g'
        elif srn == 560:
            ing = 'insulina análoga de ação prolongada'
            form = 'solução injetável (carpule)'
            st = '100 UI/mL (carpule 3 mL)'
        elif srn == 622:
            ing = 'lidocaína (cloridrato)'
            form = 'geleia'
            st = '2% (bisnaga 30 g)'
        elif srn == 828:
            ing = 'poliquimioterapia única adulto (PQT-u adulto)'
            form = 'blister (cápsulas e comprimidos)'
            st = 'blister dose supervisionada e autoadministrada'
        elif srn == 829:
            ing = 'poliquimioterapia única infantil (PQT-u infantil)'
            form = 'blister (cápsulas e comprimidos)'
            st = 'blister dose supervisionada e autoadministrada'
        elif srn in [908, 909]:
            ing = 'rivastigmina'
            form = 'adesivo transdérmico'
            if srn == 908:
                st = '18 mg (liberação de 9,5 mg/24h)'
            else:
                st = '9 mg (liberação de 4,6 mg/24h)'
        elif srn == 924:
            ing = 'salbutamol (sulfato)'
            form = 'solução aerossol para inalação oral'
        elif srn == 925:
            ing = 'salmeterol (xinafoato) + fluticasona (propionato)'
            form = 'solução aerossol para inalação oral'
            st = '25 mcg/dose + 125 mcg/dose'
        elif srn == 926:
            ing = 'salmeterol (xinafoato) + fluticasona (propionato)'
            form = 'pó inalatório'
            st = '50 mcg/dose + 500 mcg/dose'
        elif srn in [929, 930]:
            ing = 'selante de fibrina'
            form = 'frasco-ampola'
            st = '0,5 mL' if srn == 929 else '1 mL'
        elif srn in [948, 949]:
            ing = 'sirolimo'
            form = 'drágea'
        elif srn == 966:
            ing = 'subgalato de bismuto'
            form = 'pó'
        elif srn == 978:
            form = 'solução oral'
        elif srn == 981:
            ing = 'suplemento alimentar com múltiplos micronutrientes'
            form = 'pó para suspensão oral (envelope)'
            st = '1 g'
        elif srn == 987:
            ing = '[linha 987 em branco no PDF]'
            form = '-'
            st = '- (item 987 sem conteúdo no PDF oficial)'
        elif srn == 1002:
            ing = 'tenecteplase'
            form = 'pó liofilizado para solução injetável'
        elif srn == 1010:
            ing = 'tenofovir desoproxila (fumarato) + lamivudina'
            form = 'comprimido'
            st = '300 mg + 300 mg'
        elif srn == 1012:
            form = 'comprimido'
        elif srn == 1045:
            form = 'frasco-ampola ou seringa preenchida'
        elif srn == 1048:
            ing = 'umeclidínio (brometo) + vilanterol (trifenatato)'
            form = 'pó inalatório'
            st = '62,5 mcg/dose + 25 mcg/dose'
        elif srn == 1059:
            form = 'pomada (bisnaga ou tubo)'
        else:
            # Fallback regex search on raw
            raw_l = raw.lower()
            if 'frasco-ampola' in raw_l or 'frasco ampola' in raw_l:
                form = 'frasco-ampola'
            elif 'seringa preenchida' in raw_l:
                form = 'solução injetável (seringa preenchida)'
            elif 'ampola' in raw_l:
                form = 'ampola'
            elif 'comprimido' in raw_l:
                form = 'comprimido'
            elif 'cápsula' in raw_l:
                form = 'cápsula'
            elif 'spray' in raw_l:
                form = 'spray'
            elif 'solução injetável' in raw_l:
                form = 'solução injetável'
            elif 'solução' in raw_l:
                form = 'solução'
            elif 'pomada' in raw_l:
                form = 'pomada'
            elif 'creme' in raw_l:
                form = 'creme'
            elif 'gel' in raw_l:
                form = 'gel'
            elif 'xarope' in raw_l:
                form = 'xarope'
            elif 'suspensão' in raw_l:
                form = 'suspensão'
            else:
                form = 'solução injetável' # Default medical form
                
    elif src == 'F04':
        # 41 PFPB items
        raw_l = raw.lower()
        if 'brometo de ipratrópio 0,02mg' in raw_l:
            form = 'solução para inalação oral (aerossol)'
        elif 'brometo de ipratrópio 0,25mg' in raw_l:
            form = 'solução para inalação (gotas)'
        elif 'dipropionato de beclometasona' in raw_l:
            form = 'solução aerossol para inalação oral'
        elif 'sulfato de salbutamol 100mcg' in raw_l:
            form = 'solução aerossol para inalação oral'
        elif 'sulfato de salbutamol 5mg' in raw_l:
            form = 'solução para inalação (gotas)'
        elif 'metformina 500mg - ação prolongada' in raw_l:
            form = 'comprimido de liberação prolongada'
        elif 'insulina humana regular' in raw_l:
            form = 'solução injetável'
        elif 'insulina humana' in raw_l:
            form = 'suspensão injetável'
        elif 'medroxiprogesterona 150mg' in raw_l:
            form = 'suspensão injetável'
        elif 'valerato de estradiol 5mg + enantato' in raw_l or srn == 28:
            ing = 'valerato de estradiol + enantato de noretisterona'
            form = 'solução injetável'
            st = '5 mg + 50 mg (ampola 1 mL)'
        elif 'etinilestradiol' in raw_l or srn == 26:
            ing = 'etinilestradiol + levonorgestrel'
            form = 'comprimido'
            st = '0,03 mg + 0,15 mg'
        elif 'carbidopa' in raw_l or srn == 33:
            ing = 'carbidopa + levodopa'
            form = 'comprimido'
            st = '25 mg + 250 mg'
        elif 'benserazida' in raw_l or srn == 34:
            ing = 'cloridrato de benserazida + levodopa'
            form = 'comprimido ou cápsula'
            st = '25 mg + 100 mg'
        elif 'dipirona 500mg/ml' in raw_l:
            form = 'solução oral (gotas)'
        elif 'paracetamol 200mg/ml' in raw_l:
            form = 'solução oral (gotas)'
        elif 'timolol' in raw_l:
            form = 'solução oftálmica'
        elif 'absorvente higiênico' in raw_l:
            ing = 'absorvente higiênico (dignidade menstrual)'
            form = 'unidade'
            st = '- (insumo de higiene / dignidade menstrual)'
        elif 'fralda geriátrica' in raw_l:
            ing = 'fralda geriátrica (incontinência urinária)'
            form = 'unidade'
            st = '- (insumo para incontinência urinária)'
        elif 'succinato de metoprolol' in raw_l:
            form = 'comprimido de liberação prolongada'
        else:
            # All remaining PFPB items are oral solid forms (comprimido)
            form = 'comprimido'

    curated_t3[num] = {
        'oid': oid,
        'src': src,
        'srn': srn,
        'ing': ing,
        'st': st,
        'form': form
    }

print("Curated all 126 items.")
with open('scripts/curated_t3_all.json', 'w', encoding='utf-8') as f:
    json.dump(curated_t3, f, indent=2, ensure_ascii=False)
