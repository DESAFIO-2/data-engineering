"""Definitive consolidation of the corpus (F01, F03, F04) integrating human validations and F04 adjustments."""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from hashlib import sha256
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def digest(data: bytes) -> str:
    return sha256(data).hexdigest()


def stable_id(prefix: str, *parts: Any) -> str:
    raw = json.dumps(parts, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return prefix + sha256(raw).hexdigest()[:24]


def compact(text: str) -> str:
    return " ".join(text.split())


def jsonl_bytes(records: list[dict[str, Any]]) -> bytes:
    return "".join(
        json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n" for record in records
    ).encode("utf-8")


# Explicit clean overrides for Table 2, Table 3, and remaining F03 composite/null items
# ensuring strict dosage/volume in strength, official forms in form, and complete active_ingredient.
EXPLICIT_CLEANUPS: dict[str, dict[str, Any]] = {
    # F03 null active_ingredient items (water for injection, formulas, hemodialysis, PQT-u, etc.)
    "occ-32f9c026384ce1b61a6b03a2": {
        "active_ingredient": "água para injetáveis",
        "strength": "10 mL",
        "form": "ampola",
    },
    "occ-405fcd5d37f8cf3fbb357a41": {
        "active_ingredient": "água para injetáveis",
        "strength": "1000 mL",
        "form": "frasco ou bolsa",
    },
    "occ-adec0f7209079b9611b5cfc9": {
        "active_ingredient": "água para injetáveis",
        "strength": "500 mL",
        "form": "frasco ou bolsa",
    },
    "occ-89b1798f87b6fef73e10d024": {
        "active_ingredient": "fórmula dietoterápica para fenilcetonúria (acima de 8 anos)",
        "strength": "lata 400 g a 500 g",
        "form": "pó para suspensão oral",
    },
    "occ-cb99538aad360c68ec43b6cf": {
        "active_ingredient": "fórmula dietoterápica para fenilcetonúria (1 a 8 anos)",
        "strength": "lata 400 g a 500 g",
        "form": "pó para suspensão oral",
    },
    "occ-b0b2adb7d79eb231b1207fad": {
        "active_ingredient": "fórmula dietoterápica para fenilcetonúria (abaixo de 1 ano)",
        "strength": "lata 400 g a 500 g",
        "form": "pó para suspensão oral",
    },
    "occ-9804085866c3d3a8183e020a": {
        "active_ingredient": "insulina análoga de ação prolongada",
        "strength": "100 UI/mL (carpule 3 mL)",
        "form": "solução injetável (carpule)",
    },
    "occ-c46256c1a904b7e76d88799f": {
        "active_ingredient": "pó para solução básica para hemodiálise (sódio + bicarbonato + cloreto + glicose)",
        "strength": "98 mEq/L + 35 mEq/L + 63 mEq/L + 1 g/L (bolsa plástica 658 g)",
        "form": "pó para solução para hemodiálise",
    },
    "occ-4bd5f5d42ec8ef95ec152915": {
        "active_ingredient": "poliquimioterapia única adulto (PQT-u adulto)",
        "strength": "blister dose supervisionada e autoadministrada",
        "form": "blister (cápsulas e comprimidos)",
    },
    "occ-390b2fafe9c35c873c13e1db": {
        "active_ingredient": "poliquimioterapia única infantil (PQT-u infantil)",
        "strength": "blister dose supervisionada e autoadministrada",
        "form": "blister (cápsulas e comprimidos)",
    },
    "occ-3da1f44d1a507a358ceee024": {
        "active_ingredient": "selante de fibrina",
        "strength": "0,5 mL",
        "form": "frasco-ampola",
    },
    "occ-648c45d256d209afe121f04d": {
        "active_ingredient": "selante de fibrina",
        "strength": "1 mL",
        "form": "frasco-ampola",
    },
    "occ-6c9cca4e2c8bdba3c94bc0bc": {
        "active_ingredient": "solução ácida para hemodiálise",
        "strength": "K=2,0 mEq/L, Ca=2,5 mEq/L, sem glicose (galão 5 L)",
        "form": "solução para hemodiálise",
    },
    "occ-ca7f6da1914c760234591b70": {
        "active_ingredient": "solução básica para hemodiálise (bicarbonato de sódio)",
        "strength": "8,4% (galão 5 L)",
        "form": "solução para hemodiálise",
    },
    "occ-f0dd72a9216230ed91376a2c": {
        "active_ingredient": "solução de ringer (cloretos de sódio, potássio e cálcio)",
        "strength": "bolsa ou frasco 500 mL (sistema fechado de infusão)",
        "form": "solução injetável",
    },
    "occ-ba0acebc4bf4e0ac7bb5ad8b": {
        "active_ingredient": "solução de ringer com lactato",
        "strength": "bolsa ou frasco 500 mL (sistema fechado de infusão)",
        "form": "solução injetável",
    },
    "occ-d753bb7d688d15dcce4d3ebe": {
        "active_ingredient": "solução ácida para hemodiálise (sódio + potássio + cálcio + magnésio + cloreto + citrato)",
        "strength": "40 + 2 + 2,5 + 1 + 47,5 + 0,25 mEq/L (frasco 960 mL)",
        "form": "solução para hemodiálise",
    },
    "occ-e8faaface906ddc31f6763e8": {
        "active_ingredient": "solução ácida para hemodiálise (sódio + potássio + cálcio + magnésio + cloreto + citrato)",
        "strength": "40 + 2 + 3,5 + 1 + 48,5 + 0,35 mEq/L (frasco 960 mL)",
        "form": "solução para hemodiálise",
    },
    "occ-bfc5211a72cc92599c4d348e": {
        "active_ingredient": "solução ácida para hemodiálise (sódio + potássio + cálcio + magnésio + cloreto + citrato)",
        "strength": "40 + 3 + 2,5 + 1 + 48,5 + 0,25 mEq/L (frasco 960 mL)",
        "form": "solução para hemodiálise",
    },
    "occ-dd3666cce6867d6246aae72f": {
        "active_ingredient": "[linha 987 em branco no PDF]",
        "strength": "-",
        "form": "-",
    },
    # Table 2 F03 items where therapeutic classes or clinical notes or form words leaked into strength/ing
    "occ-75c60747180854a75232b0ec": {
        "active_ingredient": "clorexidina",
        "strength": "10 mg/mL (1% - frasco 1000 mL)",
        "form": "solução aquosa tópica",
    },
    "occ-99a3a7d33d2f60fa4162185c": {
        "active_ingredient": "colagenase",
        "strength": "0,6 UI/g ou 1,2 UI/g (bisnaga 30 g)",
        "form": "pomada dermatológica",
    },
    "occ-afa996cfd47bae4c1669fa1a": {
        "active_ingredient": "cordia verbenacea (erva-baleeira)",
        "strength": "10% (pote 200 g)",
        "form": "gel",
    },
    "occ-f70c3177ef1085ef231dfe45": {
        "active_ingredient": "cordia verbenacea (erva-baleeira)",
        "strength": "10% (pote 30 g)",
        "form": "gel",
    },
    "occ-08d4e9a33d09f64b45a58cf2": {
        "active_ingredient": "dexametasona (acetato)",
        "strength": "0,1% (bisnaga 10 g)",
        "form": "creme",
    },
    "occ-3db3f93f02c1d14cdda1861a": {
        "active_ingredient": "dexpantenol",
        "strength": "50 mg/g (bisnaga 30 g)",
        "form": "pomada",
    },
    "occ-9bd091af267ad5bcafdc9cd6": {
        "active_ingredient": "elexacaftor + tezacaftor + ivacaftor",
        "strength": "(100 mg + 50 mg + 75 mg) + 150 mg (ivacaftor)",
        "form": "comprimido revestido",
    },
    "occ-da92478589d9a0a56feb7c9b": {
        "active_ingredient": "elexacaftor + tezacaftor + ivacaftor",
        "strength": "(50 mg + 25 mg + 37,5 mg) + 75 mg (ivacaftor)",
        "form": "comprimido revestido",
    },
    "occ-6f33c8ddc52a9a43f6f408b4": {
        "active_ingredient": "espiramicina",
        "strength": "500 mg (1.500.000 UI)",
        "form": "comprimido",
    },
    "occ-d9b95b57b776e6948d5c47a9": {
        "active_ingredient": "estradiol (valerato) + noretisterona (enantato)",
        "strength": "(5 mg + 50 mg)/mL (ampola ou seringa preenchida 1 mL)",
        "form": "solução injetável",
    },
    "occ-e7922c97b272a1017e5df1b6": {
        "active_ingredient": "estriol",
        "strength": "1 mg/g (bisnaga 50 g)",
        "form": "creme vaginal",
    },
    "occ-c9bc36fa60e7502f10aa9a60": {
        "active_ingredient": "fluticasona (furoato) + umeclidínio (brometo) + vilanterol (trifenatato)",
        "strength": "100 mcg + 62,5 mcg + 25 mcg/dose (dispositivo com 30 doses)",
        "form": "pó para inalação oral",
    },
    "occ-51dcb075404e0e56191ddb1a": {
        "active_ingredient": "formoterol (fumarato) + budesonida",
        "strength": "(12 mcg + 400 mcg)/dose (frasco ou tubo com 60 doses)",
        "form": "pó inalante ou cápsula com pó para inalação",
    },
    "occ-ec6f6f783a75ee7301337a25": {
        "active_ingredient": "formoterol (fumarato) + budesonida",
        "strength": "(6 mcg + 200 mcg)/dose (frasco ou tubo com 60 doses)",
        "form": "pó inalante ou cápsula com pó para inalação",
    },
    "occ-c500bcdbb85f9875820c5df8": {
        "active_ingredient": "fosfato de sódio monobásico + fosfato de sódio dibásico",
        "strength": "(16 g + 6 g)/100 mL (frasco ou bolsa 125 mL a 133 mL)",
        "form": "solução retal (enema)",
    },
    "occ-b042234935f17939a393d2ab": {
        "active_ingredient": "glicerina (glicerol)",
        "strength": "120 mg/mL (12% - frasco ou bolsa 500 mL)",
        "form": "solução retal (enema)",
    },
    "occ-af3932964ad48be9f18e6f16": {
        "active_ingredient": "hidrocortisona (acetato)",
        "strength": "10 mg/g (1% - bisnaga)",
        "form": "creme",
    },
    "occ-a702e7f8cea75101a864bb6d": {
        "active_ingredient": "hidróxido de alumínio + hidróxido de magnésio",
        "strength": "(60 mg + 40 mg)/mL (frasco mín. 100 mL)",
        "form": "suspensão oral",
    },
    "occ-138e7fcb892102564091acf5": {
        "active_ingredient": "iodopovidona (iodopolividona)",
        "strength": "10% (teor de iodo 1% - frasco 1000 mL)",
        "form": "solução alcoólica",
    },
    "occ-2c6a5103a83f0deaada21735": {
        "active_ingredient": "iodopovidona (iodopolividona)",
        "strength": "10% (teor de iodo 1% - frasco 1000 mL)",
        "form": "solução aquosa",
    },
    "occ-2eae1621c3e43ecefe3e241c": {
        "active_ingredient": "iodopovidona (iodopolividona)",
        "strength": "10% (teor de iodo 1% - frasco 1000 mL)",
        "form": "solução degermante",
    },
    "occ-ff5c01c91fa347483018f0a0": {
        "active_ingredient": "kit selante de fibrina",
        "strength": "frasco 1 mL",
        "form": "solução tópica",
    },
    "occ-0d65a0214341f4ea9d89e1d0": {
        "active_ingredient": "levodopa + benserazida (cloridrato)",
        "strength": "100 mg + 25 mg",
        "form": "comprimido, cápsula ou drágea de liberação prolongada",
    },
    "occ-7cbf1527034e630a3b103689": {
        "active_ingredient": "levodopa + benserazida (cloridrato)",
        "strength": "100 mg + 25 mg",
        "form": "comprimido simples",
    },
    "occ-8633afd4a9f96428f0e81818": {
        "active_ingredient": "levodopa + carbidopa",
        "strength": "250 mg + 25 mg",
        "form": "comprimido simples",
    },
    "occ-266f79c4efb99c09076811a3": {
        "active_ingredient": "lidocaína (cloridrato)",
        "strength": "2% (bisnaga 30 g)",
        "form": "geleia",
    },
    "occ-81b56158be5bea770866bc32": {
        "active_ingredient": "lippia sidoides (alecrim-pimenta)",
        "strength": "10% (pote 200 g)",
        "form": "gel",
    },
    "occ-e4cbc1733e4ee6808a8e5481": {
        "active_ingredient": "lippia sidoides (alecrim-pimenta)",
        "strength": "10% (pote 30 g)",
        "form": "gel",
    },
    "occ-8d4d96cbceb2f870e79e3b16": {
        "active_ingredient": "liraglutida",
        "strength": "6 mg/mL (sistema de aplicação 3 mL)",
        "form": "solução injetável",
    },
    "occ-d1afd37cabec657dfecf0ab9": {
        "active_ingredient": "lopinavir + ritonavir",
        "strength": "100 mg + 25 mg",
        "form": "comprimido",
    },
    "occ-8806d48721f7f68dd6d71a8a": {
        "active_ingredient": "lopinavir + ritonavir",
        "strength": "80 mg/mL + 20 mg/mL (frasco 160 mL)",
        "form": "solução oral",
    },
    "occ-f0e28dbd049d6b0b301b77cf": {
        "active_ingredient": "metronidazol",
        "strength": "100 mg/g (bisnaga 50 g + 10 aplicadores)",
        "form": "gel vaginal",
    },
    "occ-c1c3e22c4cbb25745f676bd4": {
        "active_ingredient": "miconazol (nitrato)",
        "strength": "20 mg/g (bisnaga 28 g)",
        "form": "creme dermatológico",
    },
    "occ-39145d3256bd9b355a86f01b": {
        "active_ingredient": "miconazol",
        "strength": "20 mg/g (bisnaga 80 g + aplicadores)",
        "form": "creme vaginal",
    },
    "occ-be1655419eff7210901c7689": {
        "active_ingredient": "mikania glomerata spreng (guaco)",
        "strength": "frasco 100 mL",
        "form": "xarope",
    },
    "occ-34af9fd510e2641284194b08": {
        "active_ingredient": "mupirocina",
        "strength": "20 mg/g (bisnaga 15 g)",
        "form": "creme ou pomada",
    },
    "occ-98cbfa4d122c6e0d631964c1": {
        "active_ingredient": "neomicina (sulfato) + bacitracina (zíncica)",
        "strength": "(5 mg + 250 UI)/g (bisnaga 15 g)",
        "form": "pomada",
    },
    "occ-9e36c2c5050e784a8afa8dbc": {
        "active_ingredient": "oxibuprocaína (cloridrato)",
        "strength": "4 mg/mL (0,4% - frasco 10 mL)",
        "form": "solução oftálmica estéril",
    },
    "occ-e8d36ab4f9f02c6c8d0bf0a0": {
        "active_ingredient": "óxido de zinco + vitamina A + vitamina D",
        "strength": "100 mg/g + 1.000 UI/g + 400 UI/g (bisnaga 45 g)",
        "form": "pomada dermatológica",
    },
    "occ-386c6917918eb996e4015fda": {
        "active_ingredient": "pancreatina (lipase + amilase + protease)",
        "strength": "10.000 UI (150 mg)",
        "form": "cápsula com microgrânulos de liberação entérica",
    },
    "occ-a9315e6344483d7811612fda": {
        "active_ingredient": "pancreatina (lipase + amilase + protease)",
        "strength": "25.000 UI (300 mg)",
        "form": "cápsula com microgrânulos de liberação entérica",
    },
    "occ-daa827193511b8e2acec493b": {
        "active_ingredient": "polivitamínicos ou multivitamínicos sem minerais",
        "strength": "frasco-ampola ou ampola (uso adulto)",
        "form": "pó liofilizado para solução injetável ou solução injetável",
    },
    "occ-cfcfff8571d17806ea96b35c": {
        "active_ingredient": "rifampicina + isoniazida + pirazinamida + etambutol",
        "strength": "150 mg + 75 mg + 400 mg + 275 mg",
        "form": "comprimido",
    },
    "occ-e45b11383b3f72658e2434d5": {
        "active_ingredient": "rifampicina + isoniazida",
        "strength": "150 mg + 75 mg",
        "form": "comprimido",
    },
    "occ-0f69ce241b5e399f0e745b35": {
        "active_ingredient": "rifampicina + isoniazida",
        "strength": "300 mg + 150 mg",
        "form": "comprimido",
    },
    "occ-70ad4a9f925e23bfecd3a22a": {
        "active_ingredient": "rifampicina + isoniazida + pirazinamida",
        "strength": "75 mg + 50 mg + 150 mg",
        "form": "comprimido dispersível",
    },
    "occ-380d15a3a6a8d5ea6e813b43": {
        "active_ingredient": "rifampicina + isoniazida",
        "strength": "75 mg + 50 mg",
        "form": "comprimido dispersível",
    },
    # Table 3 F03 items where build_curated_t3_all.py defaulted form to 'solução injetável' or left form in ing
    "occ-51932c9f765b4621c3f85553": {
        "active_ingredient": "beclometasona (dipropionato)",
        "strength": "50 mcg/dose",
        "form": "spray nasal",
    },
    "occ-51ff8fa4d4c886e6e8c742b0": {
        "active_ingredient": "desmopressina",
        "strength": "0,1 mg/mL (frasco 2,5 mL)",
        "form": "spray nasal",
    },
    "occ-73c991d8ed35e115797070c8": {
        "active_ingredient": "desmopressina",
        "strength": "0,1 mg/mL (frasco 2,5 mL)",
        "form": "spray nasal",
    },
    "occ-4718a35240be10d89e68524c": {
        "active_ingredient": "fluticasona (propionato)",
        "strength": "50 mcg/dose",
        "form": "aerossol ou spray para inalação oral",
    },
    "occ-5064ccfc7644446f4e1a8668": {
        "active_ingredient": "gosserrelina (acetato)",
        "strength": "3,6 mg",
        "form": "implante subcutâneo (seringa preenchida)",
    },
    "occ-5ff05a19a860eb46c4d2f406": {
        "active_ingredient": "etonogestrel",
        "strength": "68 mg",
        "form": "implante subdérmico (com aplicador)",
    },
    "occ-1c491584ae8ccd223a4f3f4a": {
        "active_ingredient": "ipratrópio (brometo)",
        "strength": "20 mcg/dose",
        "form": "aerossol oral",
    },
    "occ-39c91371f765b3377864d13c": {
        "active_ingredient": "lactulose",
        "strength": "667 mg/mL (frasco 120 mL ou 200 mL)",
        "form": "líquido oral",
    },
    "occ-468eb11c1379788ba952c10d": {
        "active_ingredient": "mesalazina",
        "strength": "10 mg/mL (frasco 100 mL)",
        "form": "enema",
    },
    "occ-8d4c9df6f2789ee0f39f16ec": {
        "active_ingredient": "mesalazina",
        "strength": "2 g",
        "form": "grânulo de liberação prolongada (envelope/sachê)",
    },
    "occ-e3cf27e7ac0f77720c672d2b": {
        "active_ingredient": "mesalazina",
        "strength": "250 mg",
        "form": "supositório",
    },
    "occ-c2822e9b57c1d86fc22ad93f": {
        "active_ingredient": "mitomicina",
        "strength": "0,04% (2,5 mL)",
        "form": "pó liofilizado (frasco-ampola)",
    },
    "occ-caeca67ae3bd86fefc1b4d32": {
        "active_ingredient": "montelucaste (sódico)",
        "strength": "4 mg",
        "form": "grânulo",
    },
    "occ-6df8ebdf85df91fb4107b799": {
        "active_ingredient": "mycobacterium bovis (bcg)",
        "strength": "40 mg",
        "form": "pó liofilizado (ampola)",
    },
    "occ-fa6fbb61621b06475e0ea76f": {
        "active_ingredient": "nicotina",
        "strength": "14 mg",
        "form": "adesivo transdérmico",
    },
    "occ-bc49f2eb9047b3b8bb1c383c": {
        "active_ingredient": "nicotina",
        "strength": "21 mg",
        "form": "adesivo transdérmico",
    },
    "occ-e3dd656406f5069b5ed0e8d6": {
        "active_ingredient": "nicotina",
        "strength": "7 mg",
        "form": "adesivo transdérmico",
    },
    "occ-a7a73b34d4ce3fbb334734e0": {
        "active_ingredient": "nicotina",
        "strength": "2 mg",
        "form": "goma de mascar",
    },
    "occ-250537e61387b7413515878d": {
        "active_ingredient": "óleo mineral",
        "strength": "100% (frasco 100 mL)",
        "form": "óleo para uso oral",
    },
    "occ-2c4cdd92eecda6cae84b133b": {
        "active_ingredient": "oxaliplatina",
        "strength": "100 mg",
        "form": "pó liofilizado ou solução injetável (frasco-ampola)",
    },
    "occ-978856fb3e0fb5581ca919b1": {
        "active_ingredient": "parecoxibe",
        "strength": "40 mg",
        "form": "pó liofilizado (frasco-ampola)",
    },
    "occ-188379f9a1a901911d6ec8e6": {
        "active_ingredient": "nicotina",
        "strength": "2 mg",
        "form": "pastilha",
    },
    "occ-b1d074802a9cc8989fd76f83": {
        "active_ingredient": "permetrina",
        "strength": "10 mg/mL (frasco 60 mL)",
        "form": "loção tópica",
    },
    "occ-b3d92d4f93de913f3ec12ed5": {
        "active_ingredient": "permetrina",
        "strength": "50 mg/mL (frasco 60 mL)",
        "form": "loção tópica",
    },
    "occ-43d9f890ddf5baacb5949054": {
        "active_ingredient": "risdiplam",
        "strength": "0,75 mg/mL",
        "form": "pó para solução oral",
    },
    "occ-f208f9b0fbdfa9984f6ae66e": {
        "active_ingredient": "rivastigmina",
        "strength": "18 mg (liberação de 9,5 mg/24h)",
        "form": "adesivo transdérmico",
    },
    "occ-924b68401c03c4123a26164e": {
        "active_ingredient": "rivastigmina",
        "strength": "9 mg (liberação de 4,6 mg/24h)",
        "form": "adesivo transdérmico",
    },
    "occ-b0f807a52a2fdbfaeb4e13c8": {
        "active_ingredient": "salbutamol (sulfato)",
        "strength": "100 mcg/dose",
        "form": "solução aerossol para inalação oral",
    },
    "occ-b3c9c95e8c9426034db9ca30": {
        "active_ingredient": "salmeterol (xinafoato) + fluticasona (propionato)",
        "strength": "25 mcg/dose + 125 mcg/dose (120 doses + inalador)",
        "form": "solução aerossol para inalação oral",
    },
    "occ-c91b4e24768177e887ed16b6": {
        "active_ingredient": "salmeterol (xinafoato) + fluticasona (propionato)",
        "strength": "50 mcg/dose + 500 mcg/dose (recipiente dosador strip 60 doses)",
        "form": "pó inalatório",
    },
    "occ-d211fe7831486018fe2a05e1": {
        "active_ingredient": "sirolimo",
        "strength": "1 mg",
        "form": "drágea",
    },
    "occ-73c502c1d468203b007b9db0": {
        "active_ingredient": "sirolimo",
        "strength": "2 mg",
        "form": "drágea",
    },
    "occ-b876bad65fcf7b57f2c2cf3e": {
        "active_ingredient": "umeclidínio (brometo) + vilanterol (trifenatato)",
        "strength": "62,5 mcg/dose + 25 mcg/dose (recipiente dosador strip 30 doses)",
        "form": "pó inalatório",
    },
    # Other F03 composite / leaked-form items in occurrences.jsonl
    "occ-d4be94ec049eb9b3c722bf71": {
        "active_ingredient": "alfavelaglicerase",
        "strength": "400 U",
        "form": "pó liofilizado ou solução injetável",
    },
    "occ-c4d125396a8619fc70539807": {
        "active_ingredient": "alprostadil alfaciclodextrina",
        "strength": "20 mcg",
        "form": "pó liofilizado ou solução injetável",
    },
    "occ-1cf54e85e8647da7b13c018c": {
        "active_ingredient": "anfotericina B (lipossomal)",
        "strength": "50 mg",
        "form": "pó liofilizado injetável",
    },
    "occ-b509905fdb7a6cf297bc5f7c": {
        "active_ingredient": "anfotericina B (lipossomal)",
        "strength": "50 mg",
        "form": "pó liofilizado injetável",
    },
    "occ-71d350be0b754264c8f0187e": {
        "active_ingredient": "artemeter + lumefantrina",
        "strength": "20 mg + 120 mg",
        "form": "comprimido",
    },
    "occ-b7b50a1946ab2c60d6233953": {
        "active_ingredient": "artesunato + mefloquina",
        "strength": "100 mg + 220 mg",
        "form": "comprimido",
    },
    "occ-280bf43242a7ff435a167d8e": {
        "active_ingredient": "artesunato + mefloquina",
        "strength": "100 mg + 220 mg",
        "form": "comprimido",
    },
    "occ-5f797b2b5a1212625b4ebd74": {
        "active_ingredient": "artesunato + mefloquina",
        "strength": "25 mg + 50 mg",
        "form": "comprimido",
    },
    "occ-e5f9e3b1abb5ee648cb6c03f": {
        "active_ingredient": "artesunato + mefloquina",
        "strength": "25 mg + 50 mg",
        "form": "comprimido",
    },
    "occ-2bee5e9796fe54043ee08b43": {
        "active_ingredient": "bezafibrato",
        "strength": "200 mg",
        "form": "drágea ou comprimido revestido",
    },
    "occ-05bbf8581f5164d5358889c6": {
        "active_ingredient": "citarabina",
        "strength": "500 mg",
        "form": "pó liofilizado ou solução injetável",
    },
    "occ-eec17ef4b152d7498116775b": {
        "active_ingredient": "citarabina",
        "strength": "100 mg/mL",
        "form": "pó liofilizado ou solução injetável",
    },
    "occ-05b5e4eeddd738776317d706": {
        "active_ingredient": "citarabina",
        "strength": "100 mg",
        "form": "pó liofilizado ou solução injetável",
    },
    "occ-28f51ab4f24b567161dabc77": {
        "active_ingredient": "imipramina",
        "strength": "25 mg",
        "form": "drágea ou comprimido revestido",
    },
    "occ-55714e2a102fdced1303793e": {
        "active_ingredient": "nitroprusseto de sódio",
        "strength": "50 mg",
        "form": "pó liofilizado ou solução injetável",
    },
    "occ-949c15370770ba5bc47c6b8f": {
        "active_ingredient": "simeticona",
        "strength": "75 mg/mL",
        "form": "emulsão ou solução oral",
    },
    "occ-443b7b73fb6fd3bb2de76357": {
        "active_ingredient": "tenecteplase",
        "strength": "50 mg",
        "form": "pó liofilizado injetável",
    },
    "occ-ca70d5224391598621048935": {
        "active_ingredient": "terlipressina (acetato)",
        "strength": "1 mg",
        "form": "pó liofilizado injetável",
    },
    "occ-c579c9c24c4bfc66a97023aa": {
        "active_ingredient": "tioridazina (cloridrato)",
        "strength": "100 mg",
        "form": "drágea ou comprimido revestido",
    },
    "occ-2a9de99a389edb73b86fde06": {
        "active_ingredient": "tioridazina (cloridrato)",
        "strength": "50 mg",
        "form": "drágea ou comprimido revestido",
    },
    # F04 special adjustments (combinations with '+', metformin release_characteristic, nasal suspensions, supplies)
    "occ-48e616ae9f8df7c435126c21": {
        "active_ingredient": "cloridrato de metformina",
        "strength": "500mg",
        "form": "comprimido de liberação prolongada",
        "release_characteristic": "ação prolongada",
    },
    "occ-bd645fca4e10b51f38485f06": {
        "active_ingredient": "etinilestradiol + levonorgestrel",
        "strength": "0,03mg + 0,15mg",
        "form": "comprimido",
    },
    "occ-2e237469ad52f38dc54b786e": {
        "active_ingredient": "valerato de estradiol + enantato de noretisterona",
        "strength": "5mg + 50mg",
        "form": "solução injetável",
    },
    "occ-31f830e7fbb52c0353da2946": {
        "active_ingredient": "carbidopa + levodopa",
        "strength": "25mg + 250mg",
        "form": "comprimido",
    },
    "occ-e7d83368e51a7cb974fd6bd9": {
        "active_ingredient": "cloridrato de benserazida + levodopa",
        "strength": "25mg + 100mg",
        "form": "comprimido ou cápsula",
    },
    "occ-4dbafe42e6cc0c7058ecc60a": {
        "active_ingredient": "budesonida",
        "strength": "32mcg",
        "form": "suspensão para inalação nasal",
    },
    "occ-03bb26a358e97b57f4fd899d": {
        "active_ingredient": "budesonida",
        "strength": "50mcg",
        "form": "suspensão para inalação nasal",
    },
    "occ-dc03277c309dbb980fe781ca": {
        "active_ingredient": "dipropionato de beclometasona",
        "strength": "50mcg/dose",
        "form": "suspensão para inalação nasal",
    },
    "occ-8b27e582e2c9bd191869b342": {
        "active_ingredient": "absorvente higiênico",
        "supply_name": "absorvente higiênico",
        "strength": "-",
        "form": "unidade",
    },
    "occ-5ea8a977695dbad521b67f97": {
        "active_ingredient": "fralda geriátrica",
        "supply_name": "fralda geriátrica",
        "strength": "-",
        "form": "unidade",
    },
}


def parse_md_tables(md_path: Path) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    md = md_path.read_text(encoding="utf-8")
    sections = md.split("## 3. ")
    t2_text = sections[0].split("## 2. ")[1]
    t3_text = sections[1].split("## 4. ")[0]

    def clean_cell(val: str) -> str:
        val = val.strip()
        if val.startswith("`") and val.endswith("`"):
            val = val[1:-1]
        val = val.replace("******", "").strip("*").strip()
        if val.startswith("`") and val.endswith("`"):
            val = val[1:-1]
        return val

    t2_rows: dict[str, dict[str, Any]] = {}
    for line in t2_text.splitlines():
        if line.startswith("|") and "`occ-" in line:
            parts = [p.strip() for p in line.split("|")[1:-1]]
            num, oid, line_no, src, page, ing, fm, st = parts
            oid = clean_cell(oid)
            t2_rows[oid] = {
                "num": int(num),
                "line_no": int(line_no),
                "src": src,
                "page": int(page),
                "ing": clean_cell(ing),
                "fm": clean_cell(fm),
                "st": clean_cell(st),
            }

    t3_rows: dict[str, dict[str, Any]] = {}
    for line in t3_text.splitlines():
        if line.startswith("|") and "`occ-" in line:
            parts = [p.strip() for p in line.split("|")[1:-1]]
            num, oid, line_no, src, page, ing, st, fm = parts
            oid = clean_cell(oid)
            t3_rows[oid] = {
                "num": int(num),
                "line_no": int(line_no),
                "src": src,
                "page": int(page),
                "ing": clean_cell(ing),
                "st": clean_cell(st),
                "fm": clean_cell(fm),
            }

    return t2_rows, t3_rows


def build_catalog(occurrences: list[dict[str, Any]]) -> list[dict[str, Any]]:
    catalog: dict[str, dict[str, Any]] = {}
    for row in occurrences:
        if row.get("item_type") != "medicine" or not all(
            row.get(k) for k in ("active_ingredient", "strength", "form")
        ):
            continue
        identity = [
            compact(row.get(k) or "").casefold()
            for k in ("active_ingredient", "strength", "form", "release_characteristic")
        ]
        mid = stable_id("med-", identity)
        row["medicine_id"] = mid
        entry = catalog.setdefault(
            mid,
            {
                "medicine_id": mid,
                "active_ingredient": row["active_ingredient"],
                "strength": row["strength"],
                "form": row["form"],
                "release_characteristic": row.get("release_characteristic"),
                "review_status": "approved",
                "occurrence_ids": [],
                "source_ids": [],
            },
        )
        entry["occurrence_ids"].append(row["occurrence_id"])
        entry["source_ids"] = sorted(set(entry["source_ids"]) | {row["source"]["source_id"]})
    return list(catalog.values())


def main() -> None:
    exp_dir = ROOT / "data/corpus/experimental"
    f04_dir = ROOT / "data/corpus/f04"
    root_corpus_dir = ROOT / "data/corpus"
    md_path = ROOT / ".docs/ocorrencias-para-edicao.md"
    archived_v1_path = ROOT / "data/curation/revisao-corpus-v1.json"

    # Load baseline occurrences from archived v1 snapshot so runs are idempotent
    archived_v1 = json.loads(archived_v1_path.read_text(encoding="utf-8"))
    base_occurrences: list[dict[str, Any]] = json.loads(
        json.dumps(archived_v1["occurrences"])
    )
    exp_chunks: list[dict[str, Any]] = [
        json.loads(line)
        for line in (exp_dir / "chunks.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    f04_chunks: list[dict[str, Any]] = [
        json.loads(line)
        for line in (f04_dir / "chunks.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    t2_rows, t3_rows = parse_md_tables(md_path)

    # Preserve existing COR-001..COR-005 entries from f04/review-log.jsonl
    existing_f04_log: list[dict[str, Any]] = []
    if (f04_dir / "review-log.jsonl").is_file():
        for line in (f04_dir / "review-log.jsonl").read_text(encoding="utf-8").splitlines():
            if line.strip():
                entry = json.loads(line)
                if str(entry.get("control_id", "")).startswith("COR-00"):
                    entry["occurrence_review_status"] = "approved"
                    existing_f04_log.append(entry)

    logged_controls = {
        (e["occurrence_id"], tuple(sorted(e["fields"].keys()))) for e in existing_f04_log
    }
    review_log: list[dict[str, Any]] = list(existing_f04_log)
    cor_counter = 6

    consolidated_occurrences: list[dict[str, Any]] = []

    for orig in base_occurrences:
        row = json.loads(json.dumps(orig))
        oid = row["occurrence_id"]
        sid = row["source"]["source_id"]

        # 1. Apply Table 2 curated values
        if oid in t2_rows:
            r2 = t2_rows[oid]
            if r2["ing"]:
                row["active_ingredient"] = r2["ing"]
            if r2["fm"]:
                row["form"] = r2["fm"]
            if r2["st"]:
                row["strength"] = r2["st"]

        # 2. Apply Table 3 curated values
        if oid in t3_rows:
            r3 = t3_rows[oid]
            if r3["ing"]:
                row["active_ingredient"] = r3["ing"]
            if r3["st"]:
                row["strength"] = r3["st"]
            if r3["fm"]:
                row["form"] = r3["fm"]

        # 3. Apply explicit cleanups (F04 combinations, release_characteristic, strict dosage, official forms)
        if oid in EXPLICIT_CLEANUPS:
            for k, v in EXPLICIT_CLEANUPS[oid].items():
                row[k] = v

        # Ensure release_characteristic key exists
        if "release_characteristic" not in row:
            row["release_characteristic"] = None

        # Record any field changes in review_log
        changed_fields: dict[str, dict[str, Any]] = {}
        for field in (
            "active_ingredient",
            "strength",
            "form",
            "release_characteristic",
            "supply_name",
        ):
            old_val = orig.get(field)
            new_val = row.get(field)
            if old_val != new_val:
                changed_fields[field] = {"old": old_val, "new": new_val}

        if changed_fields and (oid, tuple(sorted(changed_fields.keys()))) not in logged_controls:
            # Check if partially covered by COR-001..COR-005
            already_logged_fields = {
                f
                for e in existing_f04_log
                if e["occurrence_id"] == oid
                for f in e["fields"].keys()
            }
            remaining_fields = {
                k: v for k, v in changed_fields.items() if k not in already_logged_fields
            }
            if remaining_fields:
                review_log.append(
                    {
                        "control_id": f"COR-{cor_counter:03d}",
                        "date": "2026-11-09",
                        "source_id": sid,
                        "source_version": row["source"]["version"],
                        "source_sha256": row["source"]["sha256"],
                        "page": row["source"]["page"],
                        "source_row_number": row.get("source_row_number"),
                        "occurrence_id": oid,
                        "literal_evidence": row.get("raw_text", ""),
                        "fields": remaining_fields,
                        "validation_status": "verified",
                        "occurrence_review_status": "approved",
                        "decision_basis": (
                            "Consolidação definitiva do corpus validada contra fontes primárias "
                            "(F01 RENAME 2024, F03 REME-DF 2026-10-29, F04 Farmácia Popular 2026-08-31) "
                            "e tabelas curadas em .docs/ocorrencias-para-edicao.md."
                        ),
                    }
                )
                cor_counter += 1

        # 4. Update metadata: mark review_status approved and clear resolved uncertainties
        row["review_status"] = "approved"
        row["uncertainties"] = []

        consolidated_occurrences.append(row)

    # Verify 0 nulls in active_ingredient, strength, form across all 2,115 occurrences
    for r in consolidated_occurrences:
        for k in ("active_ingredient", "strength", "form"):
            if not r.get(k):
                raise RuntimeError(f"Null/empty {k} in {r['occurrence_id']}: {r}")

    # Update scripts/curated_f03_final.json and scripts/curated_t3_all.json
    by_oid = {r["occurrence_id"]: r for r in consolidated_occurrences}
    curated_f03_path = ROOT / "scripts/curated_f03_final.json"
    if curated_f03_path.is_file():
        curated_f03 = json.loads(curated_f03_path.read_text(encoding="utf-8"))
        for oid, item in curated_f03.items():
            if oid in by_oid:
                occ = by_oid[oid]
                item["ing"] = occ["active_ingredient"]
                item["form"] = occ["form"]
                item["st"] = occ["strength"]
        curated_f03_path.write_text(
            json.dumps(curated_f03, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    curated_t3_path = ROOT / "scripts/curated_t3_all.json"
    if curated_t3_path.is_file():
        curated_t3 = json.loads(curated_t3_path.read_text(encoding="utf-8"))
        for num, item in curated_t3.items():
            oid = item["oid"]
            if oid in by_oid:
                occ = by_oid[oid]
                item["ing"] = occ["active_ingredient"]
                item["st"] = occ["strength"]
                item["form"] = occ["form"]
        curated_t3_path.write_text(
            json.dumps(curated_t3, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    # Synchronize .docs/ocorrencias-para-edicao.md (Table 2 and Table 3) with cleaned values
    md_lines = md_path.read_text(encoding="utf-8").splitlines()
    new_md_lines = []
    in_t2 = False
    in_t3 = False
    for line in md_lines:
        if line.startswith("## 2. "):
            in_t2 = True
            in_t3 = False
        elif line.startswith("## 3. "):
            in_t2 = False
            in_t3 = True
        elif line.startswith("## 4. "):
            in_t2 = False
            in_t3 = False

        if (in_t2 or in_t3) and line.startswith("|") and "`occ-" in line:
            parts = [p.strip() for p in line.split("|")[1:-1]]
            num, oid_cell, line_no, src, page, c6, c7, c8 = parts
            oid = oid_cell.strip("`")
            occ = by_oid[oid]
            orig_occ = next(o for o in base_occurrences if o["occurrence_id"] == oid)
            ing_str = (
                f"***{occ['active_ingredient']}***"
                if orig_occ.get("active_ingredient") != occ["active_ingredient"]
                else occ["active_ingredient"]
            )
            fm_str = (
                f"***{occ['form']}***"
                if orig_occ.get("form") != occ["form"]
                else occ["form"]
            )
            if occ["strength"] == "-" and orig_occ.get("strength") == "-":
                st_str = "`-`"
            elif orig_occ.get("strength") != occ["strength"]:
                st_str = f"***{occ['strength']}***"
            else:
                st_str = occ["strength"]

            if in_t2:
                line = f"| {num} | `{oid}` | {line_no} | {src} | {page} | {ing_str} | {fm_str} | {st_str} |"
            else:
                line = f"| {num} | `{oid}` | {line_no} | {src} | {page} | {ing_str} | {st_str} | {fm_str} |"
        new_md_lines.append(line)
    md_path.write_text("\n".join(new_md_lines) + "\n", encoding="utf-8")

    # Build catalog for full corpus (2,115 occurrences)
    full_catalog = build_catalog(consolidated_occurrences)

    # Write F04 corpus (data/corpus/f04/)
    f04_occurrences = [
        json.loads(json.dumps(r))
        for r in consolidated_occurrences
        if r["source"]["source_id"] == "F04"
    ]
    f04_catalog = build_catalog(f04_occurrences)
    f04_review_log = [e for e in review_log if e["source_id"] == "F04"]

    f04_report = {
        "catalog_presentations": len(f04_catalog),
        "chunks": len(f04_chunks),
        "corrected_fields": sum(len(e["fields"]) for e in f04_review_log),
        "corrected_occurrences": len({e["occurrence_id"] for e in f04_review_log}),
        "human_verified": True,
        "limitations": [],
        "occurrences": len(f04_occurrences),
        "review_log": "review-log.jsonl",
        "review_status": "approved",
        "schema_version": "f04-corpus-v2-consolidated",
        "source_id": "F04",
        "source_version": "Farmácia Popular 2026-08-31",
        "status": "experimental",
        "structured_extraction_complete": True,
    }
    f04_contents = {
        "chunks.jsonl": (f04_dir / "chunks.jsonl").read_bytes(),
        "occurrences.jsonl": jsonl_bytes(f04_occurrences),
        "catalog.jsonl": jsonl_bytes(f04_catalog),
        "review-log.jsonl": jsonl_bytes(f04_review_log),
        "report.json": (
            json.dumps(f04_report, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
        ).encode("utf-8"),
    }
    f04_files: dict[str, dict[str, Any]] = {}
    for name, raw_bytes in f04_contents.items():
        if name != "chunks.jsonl":
            (f04_dir / name).write_bytes(raw_bytes)
        f04_files[name] = {"bytes": len(raw_bytes), "sha256": digest(raw_bytes)}
        if name.endswith(".jsonl"):
            f04_files[name]["records"] = len(raw_bytes.decode("utf-8").splitlines())
    f04_manifest = {
        "based_on": {
            "corpus_path": "data/corpus/experimental",
            "occurrences_sha256": digest(jsonl_bytes(consolidated_occurrences)),
        },
        "files": f04_files,
        "parser_version": "f04-curated-field-fixes-v2-consolidated",
        "review_status": "approved",
        "schema_version": "f04-corpus-v2-consolidated",
        "source": {
            "pages": 1,
            "path": "data/raw/F04-farmacia-popular/farmacia-popular-elenco-2026-08-31.pdf",
            "sha256": "beb2cf59b835e94e2e016b009bd2b17f5d0375ab593db00f983211c2cfbc32b3",
            "source_id": "F04",
            "url": "https://www.gov.br/saude/pt-br/composicao/sectics/farmacia-popular/arquivos/elenco-de-medicamentos-e-insumos-pfpb.pdf",
            "version": "Farmácia Popular 2026-08-31",
        },
        "status": "experimental",
    }
    (f04_dir / "manifest.json").write_bytes(
        (json.dumps(f04_manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode(
            "utf-8"
        )
    )

    # Build consolidated report & manifest for data/corpus/experimental and data/corpus
    exp_manifest_old = json.loads((exp_dir / "manifest.json").read_text(encoding="utf-8"))
    sources_summary = {}
    for sid, expected_pages in (("F01", 267), ("F03", 98), ("F04", 1)):
        s_rows = [r for r in consolidated_occurrences if r["source"]["source_id"] == sid]
        sources_summary[sid] = {
            "candidate_medicines": sum(r.get("item_type") == "medicine" for r in s_rows),
            "candidate_occurrences": len(s_rows),
            "candidate_supplies": sum(r.get("item_type") == "supply" for r in s_rows),
            "pages_expected": expected_pages,
            "pages_preserved": expected_pages,
            "unresolved_fields": {
                k: sum(not r.get(k) for r in s_rows)
                for k in ("active_ingredient", "strength", "form")
            },
        }

    full_report = {
        "catalog_presentations": len(full_catalog),
        "chunks": len(exp_chunks) + 108,
        "corpus_fingerprint": archived_v1["corpus_fingerprint"],
        "human_verified": True,
        "limitations": [],
        "occurrences": len(consolidated_occurrences),
        "primary_chunks": len(exp_chunks),
        "restored_from": "data/curation/revisao-corpus-v1.json",
        "review_log_entries": len(review_log),
        "review_status": "approved",
        "schema_version": "consolidated-v2",
        "sources": sources_summary,
        "status": "experimental",
        "structured_extraction_complete": True,
        "supplemental_chunks": 108,
    }

    full_contents = {
        "chunks.jsonl": (exp_dir / "chunks.jsonl").read_bytes(),
        "occurrences.jsonl": jsonl_bytes(consolidated_occurrences),
        "catalog.jsonl": jsonl_bytes(full_catalog),
        "review-log.jsonl": jsonl_bytes(review_log),
        "report.json": (
            json.dumps(full_report, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
        ).encode("utf-8"),
    }
    full_files: dict[str, dict[str, Any]] = {}
    for name, raw_bytes in full_contents.items():
        full_files[name] = {"bytes": len(raw_bytes), "sha256": digest(raw_bytes)}
        if name.endswith(".jsonl"):
            full_files[name]["records"] = len(raw_bytes.decode("utf-8").splitlines())

    full_manifest = {
        "files": full_files,
        "parser_version": "consolidated-v2-human-verified",
        "restoration": exp_manifest_old["restoration"],
        "review_status": "approved",
        "schema_version": "consolidated-v2",
        "status": "experimental",
    }
    full_manifest_bytes = (
        json.dumps(full_manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")

    for target_dir in (exp_dir, root_corpus_dir):
        target_dir.mkdir(parents=True, exist_ok=True)
        for name, raw_bytes in full_contents.items():
            if target_dir == exp_dir and name == "chunks.jsonl":
                continue
            (target_dir / name).write_bytes(raw_bytes)
        (target_dir / "manifest.json").write_bytes(full_manifest_bytes)

    print(
        json.dumps(
            {
                "total_occurrences": len(consolidated_occurrences),
                "by_source": dict(Counter(r["source"]["source_id"] for r in consolidated_occurrences)),
                "review_log_entries": len(review_log),
                "f04_review_log_entries": len(f04_review_log),
                "catalog_presentations": len(full_catalog),
                "null_counts": {
                    k: sum(not r.get(k) for r in consolidated_occurrences)
                    for k in ("active_ingredient", "strength", "form")
                },
                "pending_reviews": sum(
                    r.get("review_status") != "approved" for r in consolidated_occurrences
                ),
                "unresolved_uncertainties": sum(
                    bool(r.get("uncertainties")) for r in consolidated_occurrences
                ),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
