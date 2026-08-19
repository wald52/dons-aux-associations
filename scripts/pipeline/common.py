"""Briques partagées par tous les normaliseurs du pipeline.

Règle d'or, reprise de SCHEMA.md : **nul plutôt que faux**. Une valeur
douteuse est écartée et signalée dans `quality_flags`, jamais rafistolée en
silence.
"""

import csv
import gzip
import io
import json
import os
import re
import unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REF_DIR = os.path.join(ROOT, "data", "referentiel")

csv.field_size_limit(10 * 1024 * 1024)

# ---------------------------------------------------------------- texte ----

NBSP = " "


def clean_text(v):
    """Espaces insécables, espaces multiples, guillemets parasites."""
    if v is None:
        return ""
    s = str(v).replace(NBSP, " ").replace(" ", " ")
    s = s.replace("\r", " ").replace("\n", " ")
    s = re.sub(r"\s+", " ", s).strip()
    # Excel préfixe parfois les cellules texte d'une apostrophe.
    if s.startswith("'"):
        s = s[1:].strip()
    return s


def fold(s):
    """Minuscules sans accents — pour comparer des libellés, pas pour stocker."""
    s = unicodedata.normalize("NFD", str(s or ""))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", s).strip().lower()


# Formes juridiques et préfixes qu'on retire pour rapprocher deux graphies du
# même organisme. On ne touche jamais au nom d'origine, seulement à sa version
# normalisée servant au rapprochement.
# On ne retire que ce qui est purement une forme juridique. « Fédération »,
# « Union », « Ligue » ou « Comité » font partie du nom : les retirer ferait
# collisionner « Fédération Française de X » et « Union Française de X ».
_LEGAL_PREFIX = re.compile(
    r"^(association|associations|assoc|asso)\b[\s.]*(?:loi\s*1901)?[\s.]*",
    re.I,
)
_LEGAL_NOISE = re.compile(r"\b(loi\s*1901|declaree|reconnue d'?utilite publique|rup)\b", re.I)


def normalize_name(v):
    """Clé de rapprochement d'un organisme : pliée, sans forme juridique."""
    s = fold(clean_text(v))
    if not s:
        return ""
    s = _LEGAL_NOISE.sub(" ", s)
    s = _LEGAL_PREFIX.sub("", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip().upper()


# -------------------------------------------------------------- nombres ----

_AMOUNT_CLEAN = re.compile(r"[^\d,.\-]")


def parse_amount(v):
    """Montant en euros. Gère « 1 190,00 », « 12500.0 », « 22500 ».

    Retourne None si non interprétable — jamais 0, qui serait un vrai montant.
    """
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return round(float(v), 2)
    s = clean_text(v).replace(" ", "")
    if not s:
        return None
    s = _AMOUNT_CLEAN.sub("", s)
    if not s or s in "-.,":
        return None
    # Décide du séparateur décimal d'après le dernier symbole rencontré.
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".") if s.rfind(",") > s.rfind(".") \
            else s.replace(",", "")
    elif "," in s:
        # « 1,5 » = décimal ; « 1,500 » avec 3 décimales = millier.
        dec = len(s) - s.rfind(",") - 1
        s = s.replace(",", "." if dec in (1, 2) else "")
    try:
        return round(float(s), 2)
    except ValueError:
        return None


_YEAR_RE = re.compile(r"\b(19\d{2}|20\d{2})\b")


def parse_year(v):
    """Extrait une année plausible d'un libellé ou d'un nombre."""
    if v is None:
        return None
    m = _YEAR_RE.search(str(v))
    if not m:
        return None
    y = int(m.group(1))
    return y if 1990 <= y <= 2100 else None


# ------------------------------------------------- identifiants légaux ----


def _luhn_ok(digits):
    total, parity = 0, len(digits) % 2
    for i, ch in enumerate(digits):
        d = int(ch)
        if i % 2 == parity:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def valid_siren(v):
    s = re.sub(r"\D", "", clean_text(v) or "")
    if len(s) != 9 or s == "0" * 9:
        return None
    # La Poste (356000000) déroge historiquement à la clé de Luhn.
    return s if (_luhn_ok(s) or s == "356000000") else None


def valid_siret(v):
    s = re.sub(r"\D", "", clean_text(v) or "")
    if len(s) != 14 or s == "0" * 14:
        return None
    if s.startswith("356000000"):
        return s  # La Poste
    return s if _luhn_ok(s) else None


def build_siret(siren, nic):
    """SIRET = SIREN (9) + NIC (5). Le NIC perd souvent ses zéros de tête
    en passant par un tableur : on les restitue avant de valider."""
    si = re.sub(r"\D", "", clean_text(siren) or "")
    ni = re.sub(r"\D", "", clean_text(nic) or "")
    if len(si) != 9 or not ni:
        return None
    return valid_siret(si + ni.zfill(5))


_RNA_RE = re.compile(r"^W[0-9A-Z]{9}$")


def valid_rna(v):
    s = clean_text(v).upper().replace(" ", "")
    return s if _RNA_RE.match(s) else None


# --------------------------------------------------------- géographie ----


def insee_from_parts(dep_code, commune_code):
    """Recompose un code commune INSEE à partir des colonnes COG séparées.

    Métropole : département sur 2 + commune sur 3 (95 + 680 -> 95680).
    Outre-mer : département sur 3 + commune sur 2 (971 + 05 -> 97105).
    """
    d = re.sub(r"\D", "", clean_text(dep_code) or "")
    c = re.sub(r"\D", "", clean_text(commune_code) or "")
    if not d or not c:
        return None
    if len(d) >= 3:
        return (d[:3] + c.zfill(2))[:5]
    return (d.zfill(2) + c.zfill(3))[:5]


def dep_from_insee(insee):
    if not insee or len(insee) < 4:
        return None
    return insee[:3] if insee.startswith(("97", "98")) else insee[:2]


# ------------------------------------------------------- référentiel ----

_REF = {}


def referentiel():
    """Charge (une fois) le référentiel INSEE vendu dans data/referentiel/."""
    if _REF:
        return _REF
    for name in ("communes", "departements", "regions", "epci"):
        path = os.path.join(REF_DIR, f"{name}.json.gz")
        if not os.path.exists(path):
            raise SystemExit(
                f"Référentiel manquant : {path}\n"
                "Lancer d'abord : python3 scripts/pipeline/build_referentiel.py"
            )
        with gzip.open(path, "rt", encoding="utf-8") as f:
            _REF[name] = json.load(f)
    return _REF


def resolve_commune(insee):
    """Retourne (insee, dep_code, reg_code) validés contre le référentiel.

    Le code Corse est corrigé (« 20 » n'existe plus : 2A / 2B). Un code absent
    du référentiel n'est pas inventé : il ressort à None et sera signalé.
    """
    ref = referentiel()
    if not insee:
        return None, None, None
    code = str(insee).strip().upper().zfill(5)
    com = ref["communes"].get(code)
    if not com:
        return None, None, None
    return code, com.get("dep_code"), com.get("reg_code")


def dep_is_known(dep_code):
    return bool(dep_code) and dep_code in referentiel()["departements"]


# ------------------------------------------------------------ lecture ----

ENCODINGS = ("utf-8-sig", "cp1252", "latin-1")
# Colonnes-repères permettant de reconnaître la vraie ligne d'en-tête lorsque
# le fichier commence par un titre de rapport (cas des exports issus de XLSX).
HEADER_HINTS = ("siren", "association", "denomination", "montant", "programme",
                "subvention", "objet")


def detect_encoding(path):
    """Encodage du fichier, déterminé sur un échantillon de tête.

    Le décodage se fait en mode incrémental sans `final=True` : une fenêtre de
    taille fixe coupe fatalement un caractère multi-octets en deux, et un
    décodage naïf conclurait à tort que le fichier n'est pas en UTF-8. C'est ce
    qui faisait lire le PLF 2025 en latin-1, avec un en-tête illisible à la clé.
    """
    import codecs
    with open(path, "rb") as f:
        head = f.read(1 << 20)
    for enc in ENCODINGS:
        try:
            codecs.getincrementaldecoder(enc)().decode(head)
            return enc
        except UnicodeDecodeError:
            continue
    return "latin-1"


def detect_delimiter(sample):
    counts = {d: sample.count(d) for d in (";", ",", "\t", "|")}
    return max(counts, key=counts.get) if max(counts.values()) else ";"


def read_rows(path, max_header_scan=12):
    """Itère les lignes d'un CSV en dictionnaires.

    Détecte l'encodage, le séparateur et la ligne d'en-tête réelle (certains
    fichiers commencent par deux ou trois lignes de titre).
    Retourne (en-têtes, générateur de dict).
    """
    enc = detect_encoding(path)
    with open(path, "r", encoding=enc, errors="replace", newline="") as f:
        first = f.readline()
    delim = detect_delimiter(first)

    f = open(path, "r", encoding=enc, errors="replace", newline="")
    reader = csv.reader(f, delimiter=delim)

    header, skipped = None, 0
    for row in reader:
        skipped += 1
        cells = [clean_text(c) for c in row]
        score = sum(1 for c in cells if any(h in fold(c) for h in HEADER_HINTS))
        if score >= 2 and sum(1 for c in cells if c) >= 3:
            header = cells
            break
        if skipped >= max_header_scan:
            break

    if header is None:  # aucun en-tête reconnu : on repart du début
        f.seek(0)
        reader = csv.reader(f, delimiter=delim)
        header = [clean_text(c) for c in next(reader, [])]

    def gen():
        try:
            for row in reader:
                if not any(c.strip() for c in row if c):
                    continue
                yield {header[i] if i < len(header) else f"_col{i}": row[i]
                       for i in range(len(row))}
        finally:
            f.close()

    return header, gen(), {"encoding": enc, "delimiter": delim, "header_line": skipped}


def pick(header, *patterns):
    """Retourne le nom de colonne dont le libellé plié correspond.

    Chaque motif est testé d'abord en égalité, puis en préfixe, puis en
    inclusion — pour que « objet » ne rafle pas « objet de la subvention »
    avant que le motif exact ait eu sa chance.
    """
    folded = [(h, fold(h)) for h in header]
    for test in (lambda f, p: f == p,
                 lambda f, p: f.startswith(p),
                 lambda f, p: p in f):
        for p in patterns:
            pf = fold(p)
            for h, f_ in folded:
                if test(f_, pf):
                    return h
    return None


# --------------------------------------------- extraction des sources JS ----

# Les fichiers `data/sources/*.js` de l'ancien site enveloppent tous un tableau
# JSON dans l'une de cinq formes : `window.__DATA_SOURCES.push({...data:[...]})`,
# `__registerDataSource(id, [...])`, `var DATA_X = [...]`, `window.DATA_X = [...]`
# ou une IIFE contenant `var RAW_DATA = [...]`. Plutôt que de gérer cinq
# grammaires, on repère le premier tableau d'objets et on l'extrait par
# équilibrage des crochets : c'est insensible à l'enveloppe.

# Le générateur historique produit du JSON invalide sur trois fichiers : une
# virgule surnuméraire en tête de tableau (`[\n,{...`), une en queue (`...},\n]`),
# et des tableaux vides `[]`. On tolère les trois plutôt que de perdre les
# 350 000 lignes concernées.
# On cherche d'abord un tableau CONTENANT des objets : plusieurs fichiers
# commencent par `window.__DATA_SOURCES = window.__DATA_SOURCES || [];`, et
# accepter un tableau vide trop tôt ferait manquer les données qui suivent.
_ARRAY_START = re.compile(r"\[\s*,?\s*\{")
_EMPTY_ARRAY = re.compile(r"=\s*\[\s*\]\s*;")
_LEAD_COMMA = re.compile(r"^\[\s*,+")
_TRAIL_COMMA = re.compile(r",\s*\]$")


def extract_js_array(text, start_hint=0):
    """Extrait le premier tableau JSON d'objets trouvé dans du JavaScript.

    Retourne (données, index_de_fin) ou (None, -1). L'équilibrage ignore les
    crochets présents à l'intérieur des chaînes, y compris échappés ; les
    virgules surnuméraires en tête et en queue sont réparées avant décodage.
    """
    m = _ARRAY_START.search(text, start_hint)
    if not m:
        # Aucun objet : la source est peut-être légitimement vide.
        return ([], len(text)) if _EMPTY_ARRAY.search(text) else (None, -1)
    start = m.start()
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch in "[{":
            depth += 1
        elif ch in "]}":
            depth -= 1
            if depth == 0:
                span = text[start:i + 1]
                try:
                    return json.loads(span), i + 1
                except json.JSONDecodeError:
                    pass
                repaired = _TRAIL_COMMA.sub("]", _LEAD_COMMA.sub("[", span))
                try:
                    return json.loads(repaired), i + 1
                except json.JSONDecodeError:
                    return None, -1
    return None, -1


_META_ID = re.compile(r"""\bid\s*:\s*["']([^"']+)["']""")
_META_LABEL = re.compile(r"""\blabel\s*:\s*["']([^"']*)["']""")


def read_legacy_source(path):
    """Lit un fichier `data/sources/*.js` : (identifiant, libellé, lignes)."""
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        text = f.read()
    head = text[:2000]
    src_id = (_META_ID.search(head).group(1) if _META_ID.search(head)
              else os.path.basename(path)[:-3])
    label_m = _META_LABEL.search(head)
    label = label_m.group(1) if label_m else ""
    rows, _ = extract_js_array(text)
    return src_id, label, (rows or [])


# ------------------------------------- rattachement par nom de département ----

_DEP_BY_NAME = {}
# Les fichiers ANCT stockent un NOM de département là où le schéma attend un
# code (« Seine-Saint-Denis », parfois « Préfecture du Nord »). On sait les
# rattacher, ce qui récupère plus de 100 000 lignes autrement sans géographie.
# Appliqué sur la forme PLIÉE (sans accents, sans apostrophes) : une regex
# posée sur le texte d'origine manquerait « Préfecture », accent compris.
_DEP_PREFIX = re.compile(
    r"^(prefecture|prefectures|direction|directions|ddcs|ddcspp|drjscs|dreets|ddets)\b"
    r"[\s\w,-]*?\b(de la|de l|du|des|de|d)\b\s*")


def _dep_key(name):
    s = fold(name).replace("’", "'").replace("'", " ").replace("-", " ")
    return " ".join(s.split())


def dep_by_name(name):
    """Code département à partir d'un libellé. None si non reconnu."""
    if not _DEP_BY_NAME:
        for code, meta in referentiel()["departements"].items():
            _DEP_BY_NAME[_dep_key(meta["nom"])] = code
        # Graphies rencontrées dans les sources qui ne sont pas le nom INSEE.
        for alias, code in {
            "alsace": "67", "corse": "2A", "metropole de lyon": "69",
            "rhone metropole de lyon": "69", "seine st denis": "93",
            "val d oise": "95", "cotes d armor": "22", "cotes du nord": "22",
            "la reunion": "974", "reunion": "974", "guyane francaise": "973",
        }.items():
            _DEP_BY_NAME.setdefault(alias, code)
    raw = clean_text(name)
    if not raw:
        return None
    key = _dep_key(raw)
    hit = _DEP_BY_NAME.get(key)
    if hit:
        return hit
    # « Préfecture de Seine-Saint-Denis » -> « Seine-Saint-Denis »
    stripped = _DEP_PREFIX.sub("", key).strip()
    if stripped and stripped != key:
        return _DEP_BY_NAME.get(stripped)
    return None


def dep_from_code_or_name(value):
    """Interprète un champ « département » qui peut porter un code ou un nom.

    Retourne (code, provenance) où provenance vaut "code", "nom" ou None.
    Les marqueurs d'absence de l'ancien site ("00", "", "0") ressortent à None :
    la règle est nul plutôt que faux.
    """
    v = clean_text(value).upper()
    if not v or v in ("00", "0", "NA", "N/A", "-"):
        return None, None
    if len(v) <= 3:
        code = v.zfill(2) if v.isdigit() and len(v) == 1 else v
        if code == "20":
            return None, None  # « 20 » n'existe plus : 2A ou 2B, indécidable
        if dep_is_known(code):
            return code, "code"
        if v.isdigit():
            return None, None
        # Court mais non numérique : c'est peut-être un nom (« Var », « Ain »,
        # « Lot », « Cher »…). On ne s'arrête donc pas à l'échec du code.
    named = dep_by_name(v)
    return (named, "nom") if named else (None, None)


# --------------------------------------------- taxonomie des donateurs ----

# Les onze valeurs de `entity.type` de l'ancien site vers les sept valeurs
# closes de SCHEMA.md. Les doublons (state/ministere, department/departement,
# commune/city, epci/metropole) faisaient apparaître l'État en deux entrées
# distinctes dans le menu du site.
DONOR_LEVEL_MAP = {
    "state": "etat", "ministere": "etat", "ministère": "etat",
    "region": "region", "région": "region",
    "department": "departement", "departement": "departement", "département": "departement",
    "epci": "epci", "metropole": "epci", "métropole": "epci",
    "commune": "commune", "city": "commune", "ville": "commune",
    # Établissements publics à budget propre : les fondre dans `etat`
    # compterait deux fois. Une CCI n'est pas un opérateur de l'État au sens
    # strict, mais elle en partage la propriété qui compte ici — un budget
    # distinct de celui des collectivités.
    "operator": "operateur", "operateur": "operateur", "cci": "operateur",
}

# Libellés de donateur qui ne désignent personne : l'attribuant n'a pas été
# récupéré de la source. Les classer « État » gonflerait l'État (cf. SCHEMA.md).
_DONOR_PLACEHOLDER = {
    "source data.gouv.fr", "collectivite", "collectivité", "commune", "ville",
    "departement", "département", "region", "région", "epci", "etat", "état",
    "attribuant", "non renseigne", "non renseigné", "", "-",
}


def donor_level_of(raw_type, donor_name):
    """(niveau, non_attribué) — niveau canonique du donateur."""
    if fold(donor_name) in _DONOR_PLACEHOLDER:
        return "inconnu", True
    lvl = DONOR_LEVEL_MAP.get(fold(raw_type or ""))
    if lvl:
        return lvl, False
    n = fold(donor_name)
    for needle, lvl in (("ministere", "etat"), ("etat", "etat"), ("prefecture", "etat"),
                        ("region", "region"), ("departement", "departement"),
                        ("conseil general", "departement"),
                        ("metropole", "epci"), ("communaute", "epci"), ("agglomeration", "epci"),
                        ("syndicat", "epci"), ("mairie", "commune"), ("ville de", "commune"),
                        ("commune de", "commune")):
        if needle in n:
            return lvl, False
    return "inconnu", True


# ------------------------------------------------------------ nature ----

# Un objet réduit à un numéro de compte du plan comptable M14/M52/M57
# (« 6574.00 ») n'est pas une subvention nominative mais une ligne de budget.
_ACCOUNT_CODE = re.compile(r"^\d{4,7}([.,]\d{1,2})?$")
_BUDGET_WORDS = re.compile(
    r"subv\w*\.?\s+(de\s+)?fonct|subventions? (aux|de fonctionnement)|"
    r"autres personnes (de )?droit prive", re.I)
# « TOTAL 2019 » en guise de bénéficiaire : un total de budget déguisé en
# association (constaté chez commune-bar-le-duc, 7 lignes, 196,9 M€ à elles
# seules pour une ville de 15 000 habitants).
_TOTAL_NAME = re.compile(r"^\s*(total|totaux)\b", re.I)


# Aucune attribution unique de subvention publique française n'atteint dix
# milliards d'euros : au-delà, la valeur n'est pas un montant. Le cas rencontré
# est un SIRET recopié dans la colonne montant par un convertisseur défaillant
# (3 lignes de `communes-pays-loire`, à 78 962 milliards chacune). On ne corrige
# pas la valeur — on la signale et on l'exclut des totaux.
AMOUNT_IMPLAUSIBLE = 1e10


def amount_is_implausible(amount):
    return amount is not None and abs(amount) >= AMOUNT_IMPLAUSIBLE


def looks_aggregate(purpose, beneficiary_name):
    """Vrai si la ligne décrit un poste budgétaire et non une attribution."""
    p = clean_text(purpose)
    if p and _ACCOUNT_CODE.match(p.replace(" ", "")):
        return True
    name = clean_text(beneficiary_name)
    if _TOTAL_NAME.match(name):
        return True
    return bool(_BUDGET_WORDS.search(name))


# ------------------------------------------------- schéma canonique ----

import pyarrow as pa  # noqa: E402  (import tardif : common.py sert aussi sans pyarrow)

# Unique définition du schéma de SCHEMA.md. Tous les normaliseurs l'importent,
# pour qu'aucun ne puisse diverger silencieusement des autres.
CANONICAL_SCHEMA = pa.schema([
    ("row_id", pa.string()), ("business_key", pa.string()),
    ("beneficiary_name_raw", pa.string()), ("beneficiary_name_norm", pa.string()),
    ("beneficiary_siret", pa.string()), ("beneficiary_siren", pa.string()),
    ("beneficiary_rna", pa.string()), ("beneficiary_kind", pa.string()),
    ("beneficiary_commune_insee", pa.string()), ("beneficiary_dep_code", pa.string()),
    ("beneficiary_reg_code", pa.string()), ("beneficiary_address_raw", pa.string()),
    ("donor_name_raw", pa.string()), ("donor_name_norm", pa.string()),
    ("donor_siren", pa.string()), ("donor_level", pa.string()),
    ("donor_commune_insee", pa.string()), ("donor_dep_code", pa.string()),
    ("donor_reg_code", pa.string()), ("donor_program", pa.string()),
    ("amount_eur", pa.float64()), ("amount_rejected_eur", pa.float64()), ("year", pa.int32()), ("year_provenance", pa.string()),
    ("date_convention", pa.string()),
    ("purpose_raw", pa.string()), ("purpose_norm", pa.string()),
    ("granularity", pa.string()), ("is_convention", pa.bool_()),
    ("quality_flags", pa.list_(pa.string())), ("confidence", pa.string()),
    ("source_id", pa.string()), ("source_label", pa.string()), ("source_url", pa.string()),
    ("source_row_ref", pa.string()), ("source_family", pa.string()),
    ("license", pa.string()), ("ingested_at", pa.string()),
])
CANONICAL_FIELDS = [f.name for f in CANONICAL_SCHEMA]


def business_key(siret, name_norm, donor_norm, year, amount, purpose_norm):
    """Clé métier de SCHEMA.md — identité d'une subvention entre sources."""
    import hashlib
    parts = [siret or name_norm or "", donor_norm or "", str(year or ""),
             f"{amount:.2f}" if amount is not None else "", (purpose_norm or "")[:120]]
    return hashlib.sha1("||".join(parts).encode("utf-8")).hexdigest()[:20]
