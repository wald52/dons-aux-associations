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
import functools
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


# Toutes les années d'un libellé, pour distinguer « subventions_2016.csv »
# (une seule année, exploitable) de « subventions 2008-2012 » (ambigu).
_ANNEES_LIBELLE = re.compile(r"(?<!\d)((?:19|20)\d{2})(?!\d)")


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


def read_rows(path, max_header_scan=12, valide=None):
    """Itère les lignes d'un CSV en dictionnaires.

    Détecte l'encodage, le séparateur et la ligne d'en-tête réelle (certains
    fichiers commencent par deux ou trois lignes de titre).
    Retourne (en-têtes, générateur de dict).

    `valide` est un prédicat facultatif — en pratique `porte_des_subventions` —
    qui dit si une ligne de cellules est déjà un en-tête utilisable. Quand la
    PREMIÈRE ligne l'est, elle gagne sans discussion. Sans cette réserve, le
    repérage par mots-repères peut préférer une ligne de DONNÉES : l'en-tête de
    la Ville de Montreuil, `organisation;montant;thematique;type`, ne porte
    qu'un seul mot-repère, tandis que chacune de ses lignes en porte deux
    (« ASSOCIATION … » et « Subventions de fonctionnement … »). Le fichier
    entrait alors avec un nom d'association pour en-tête, et ses 270 lignes
    étaient toutes écartées pour « montant illisible ».
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
        if skipped == 1 and valide is not None and valide(cells)[0]:
            header = cells
            break
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


# Le SIREN d'une collectivité dit son niveau, par construction : l'INSEE
# réserve des tranches par catégorie juridique. C'est infiniment plus sûr que
# le nom — vérifié sur le corpus : tous les 21x sont des communes, tous les
# 22x des départements, les 200x/24x des groupements.
_SIREN_TRANCHE = {"21": "commune", "22": "departement", "23": "region",
                  "24": "epci", "25": "epci", "26": "epci", "27": "epci"}

# Services déconcentrés de l'État, tels qu'ils se nomment dans les données de
# la politique de la ville : préfectures et directions départementales versent
# des crédits d'État, pas des crédits locaux. Les laisser en « inconnu »
# ferait disparaître 130 000 versements de la lecture par échelon.
_SIGLES_ETAT = ("dgcl", "cget", "prefecture", "pref ", "pref-", "prefet", "prefd",
                "sous-pref", "ddets", "ddetspp", "dreets", "deets", "ddcs", "ddcspp",
                "drjscs", "ddjscs", "drac", "dihal", "dilcrah", "ddt ", "dreal",
                # Écrits en toutes lettres, ces services DÉCONCENTRÉS de l'État
                # contiennent le mot « régionale » — et le repli par nom, qui
                # cherche « region » en sous-chaîne, en faisait des RÉGIONS.
                # « Direction régionale des affaires culturelles des Pays de la
                # Loire » créditait ainsi une région de 363,59 M€ d'argent
                # d'État. Une région, elle, ne s'appelle jamais « direction ».
                "direction regionale", "direction interregionale",
                "direction departementale", "direction interdepartementale")
_SIGLES_OPERATEUR = ("agence de l'eau", "agence de l eau", "ademe", "ars ",
                     "agence nationale", "caisse nationale", "office francais")


def donor_level_from_siren(siren):
    """Niveau déduit du SIREN, ou None. Le référentiel prime sur la tranche :
    un SIREN en 200… peut être un EPCI comme un établissement public de
    coopération culturelle, et seul le référentiel les sépare."""
    if not siren or len(siren) != 9:
        return None
    if siren in referentiel()["epci"]:
        return "epci"
    tranche = _SIREN_TRANCHE.get(siren[:2])
    if tranche:
        return tranche
    if siren.startswith("20"):
        # Tranche des établissements publics de coopération : sans confirmation
        # du référentiel EPCI, c'est un opérateur, pas une intercommunalité.
        return "operateur"
    return None


def code_departement_du_siren(siren):
    """Code INSEE du département derrière un SIREN de département, ou None.

    Le SIREN d'un département vaut 22 + son code, par construction INSEE :
    222400012 est la Dordogne. Deux exceptions vérifiées sur le corpus :
    l'outre-mer porte un code sur trois chiffres (229710015 → 971), et Mayotte
    garde son rang DGFiP 985 alors que son code INSEE est 976.

    IL N'EXISTE PAS D'ÉQUIVALENT POUR LES RÉGIONS, et c'est le piège : le
    SIREN d'une région est bâti sur le département de son CHEF-LIEU, pas sur
    son code. La Région Île-de-France est 237500079 — lire « 75 » comme un
    code de région en fait la Nouvelle-Aquitaine. Les régions fusionnées de
    2016 commencent d'ailleurs par 20 (Normandie : 200053403). Une région se
    reconnaît donc par son nom, jamais par son SIREN.
    """
    if not siren or len(siren) != 9 or not siren.startswith("22"):
        return None
    code = siren[2:5] if siren[2:5].startswith("97") else siren[2:4]
    return "976" if code == "985" else code


def donor_level_of(raw_type, donor_name, donor_siren=None):
    """(niveau, non_attribué) — niveau canonique du donateur.

    Ordre de confiance : le SIREN d'abord (règle de construction INSEE), le
    type déclaré ensuite, le nom en dernier recours.
    """
    par_siren = donor_level_from_siren(donor_siren)
    if par_siren:
        return par_siren, False
    if fold(donor_name) in _DONOR_PLACEHOLDER:
        return "inconnu", True
    lvl = DONOR_LEVEL_MAP.get(fold(raw_type or ""))
    if lvl:
        return lvl, False
    n = fold(donor_name)
    if any(sig in n for sig in _SIGLES_ETAT):
        return "etat", False
    if any(sig in n for sig in _SIGLES_OPERATEUR):
        return "operateur", False
    # Sigles d'intercommunalité tels qu'ils se signent : « CA Grand Paris Sud »,
    # « CC Adour Madiran ». Testés sur le premier mot, pour ne pas confondre
    # avec une abréviation au milieu d'un libellé.
    premier = n.split(" ")[0] if n else ""
    if premier in ("ca", "cc", "cu", "ct", "sivu", "sivom", "smo", "epci"):
        return "epci", False
    for needle, lvl in (("ministere", "etat"), ("etat", "etat"), ("prefecture", "etat"),
                        ("region", "region"), ("departement", "departement"),
                        ("conseil general", "departement"),
                        ("metropole", "epci"), ("communaute", "epci"), ("agglomeration", "epci"),
                        ("agglopolys", "epci"), ("syndicat", "epci"), ("ccas", "commune"),
                        ("centre communal d action sociale", "commune"),
                        ("mairie", "commune"), ("ville de", "commune"), ("ville du", "commune"),
                        ("ville d", "commune"), ("commune de", "commune"),
                        ("commune du", "commune"), ("commune d", "commune")):
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
    ("granularity", pa.string()), ("measure", pa.string()),
    ("beneficiary_kind_provenance", pa.string()), ("is_convention", pa.bool_()),
    ("quality_flags", pa.list_(pa.string())), ("confidence", pa.string()),
    ("source_id", pa.string()), ("source_label", pa.string()), ("source_url", pa.string()),
    ("source_row_ref", pa.string()), ("source_family", pa.string()),
    ("license", pa.string()), ("ingested_at", pa.string()),
])
CANONICAL_FIELDS = [f.name for f in CANONICAL_SCHEMA]


# ------------------------------------- nature du concours ------------------
#
# TOUT ARGENT VERSÉ À UNE ASSOCIATION N'EST PAS UN DON. Une collectivité qui
# écrit « prestation facturée par l'association » ACHÈTE un service : il y a une
# contrepartie, la somme n'est pas un soutien. Un remboursement de frais avancés
# ou la cotisation d'adhésion que la collectivité paie ne soutiennent rien non
# plus. Et une mise à disposition de locaux est un vrai soutien, mais pas de
# l'argent décaissé : l'additionner à des euros fausse le total.
#
# Quatre natures, donc, et une seule est un don. Comme partout ailleurs ici :
# **rien n'est jeté**. Les trois autres restent dans la table, restent
# consultables, et sont comptées à part.
NATURES_DU_CONCOURS = ("don", "prestation", "remboursement", "nature")

# Mots de liaison : on les retire avant d'apparier, pour que « mise à
# disposition » et « mise a dispositions de » se lisent pareil.
_LIAISONS_OBJET = frozenset(("a", "au", "aux", "de", "du", "des", "d", "en", "et",
                             "le", "la", "les", "l", "par", "pour", "sur", "ou"))

# L'appariement se fait sur des SUITES DE MOTS, jamais sur des sous-chaînes.
# « SOUTIEN AUX MANUFACTURES ET MÉTIERS D'ART » contient « factur » sans être une
# facture, et « DÉMARCHE QUALITÉ » contient « marche » sans être un marché
# public. Une sous-chaîne aurait sorti ces subventions bien réelles du champ.
_OBJETS_NATURE = (
    ("mise", "disposition"), ("prestation", "nature"), ("prestations", "nature"),
    ("aide", "nature"), ("aides", "nature"), ("avantage", "nature"),
    ("avantages", "nature"), ("valorisation", "nature"),
)
_OBJETS_PRESTATION = (
    ("prestation",), ("prestations",),
    ("facture",), ("factures",), ("facturee",), ("facturees",), ("facture",),
    ("marche", "public"), ("marches", "publics"), ("marche", "publics"),
    ("delegation", "service", "public"),
)
_OBJETS_REMBOURSEMENT = (
    ("remboursement",), ("remboursements",), ("rembourse",), ("remboursee",),
    ("cotisation",), ("cotisations",), ("adhesion",),
)

# Volontairement ABSENTS de ces listes, après relecture du corpus :
#   « achat »      — « SUBVENTION POUR ACHAT D'ACTIF IMMOBILISÉ » est un don qui
#                    finance un achat FAIT PAR l'association, pas un achat de la
#                    collectivité. 215 lignes auraient été sorties à tort.
#   « honoraires » — même ambiguïté.
#   « délégation » seul — « 2ᵉ délégation » désigne une tranche de crédits.


def _suite_de_mots(mots, motif):
    """Le motif apparaît-il comme une suite de mots consécutifs ?"""
    n = len(motif)
    return any(tuple(mots[i:i + n]) == motif for i in range(len(mots) - n + 1))


def nature_du_concours(purpose_norm, quality_flags=()):
    """(nature, provenance) — ce que la somme paie, et d'où on le sait.

    La provenance vaut « declaree » quand la source elle-même qualifie la ligne
    (colonne `nature` du SCDL, d'où le drapeau `aide_en_nature`), « deduite »
    quand nous ne faisons que la lire dans l'objet, et « defaut » quand rien ne
    dit le contraire d'un don.

    On penche toujours du même côté : dans le doute, c'est un don. Sortir à tort
    une subvention du champ l'efface ; l'y laisser à tort laisse une ligne
    visible, signalée et corrigeable.
    """
    if quality_flags and "aide_en_nature" in quality_flags:
        return "nature", "declaree"
    return _nature_de_l_objet(purpose_norm or "")


# Les objets se répètent énormément (« FONCTIONNEMENT » revient 25 109 fois) :
# sans mémoïsation, classer 2,7 M de lignes coûte des minutes pour recalculer
# quelques dizaines de milliers de réponses distinctes.
@functools.lru_cache(maxsize=None)
def _nature_de_l_objet(purpose_norm):
    mots = [m for m in re.findall(r"[a-z0-9]+", fold(purpose_norm))
            if m not in _LIAISONS_OBJET]
    if not mots:
        return "don", "defaut"
    # L'ordre compte : « PRESTATION EN NATURE » est une aide en nature avant
    # d'être une prestation.
    for nature, motifs in (("nature", _OBJETS_NATURE),
                           ("prestation", _OBJETS_PRESTATION),
                           ("remboursement", _OBJETS_REMBOURSEMENT)):
        if any(_suite_de_mots(mots, m) for m in motifs):
            return nature, "deduite"
    return "don", "defaut"


# Ce qui entre dans les totaux affichés du site, défini UNE SEULE FOIS — comme
# le schéma et la clé métier — pour qu'aucun script ne puisse compter autrement
# qu'un autre.
#
#   granularity == "aggregate"  une ligne de budget déjà somme d'autres lignes ;
#                               l'additionner aux attributions compte deux fois.
#   kind        != association  le publieur DÉCLARE un bénéficiaire qui n'est pas
#                               une association. Hors du périmètre du site.
#   concours    != don          il y a une contrepartie (prestation facturée,
#                               remboursement, cotisation) ou la somme n'est pas
#                               décaissée (aide en nature). Ce n'est pas un don.
#
# Rien n'est jeté pour autant : ces lignes restent dans la table canonique et
# restent consultables. Elles ne sont simplement pas sommées ici.
def est_un_don(granularity, kind, kind_provenance, concours):
    """Ligne retenue comme don individuel à une association — voté OU payé."""
    if granularity == "aggregate":
        return False
    # Une nature seulement DEVINÉE ne suffit pas à exclure : se tromper en
    # excluant efface une association réelle, se tromper en incluant laisse une
    # ligne de trop qui reste visible et corrigeable. On penche du bon côté.
    if kind_provenance == "declared" and kind not in (None, "association"):
        return False
    return concours == "don"


# VOTÉ et PAYÉ ne s'additionnent JAMAIS, mais on ne cache plus le payé.
#
# Une collectivité publie souvent le même argent deux fois : ce qu'elle a voté,
# puis ce qu'elle a mandaté (annexe au compte administratif). Les additionner la
# compterait deux fois. La règle a longtemps été « le payé sort des totaux » —
# mesuré le 21/08/2026, cela retirait 1,86 Md€ que RIEN ne dédoublait, dont la
# totalité du département de Loire-Atlantique, qui ne publie que ses paiements.
#
# On ne choisit donc plus : le site affiche DEUX totaux côte à côte, et
# `compte_dans_les_totaux` reste le total par défaut — les dons votés.
def compte_dans_les_totaux(granularity, measure, kind, kind_provenance, concours):
    return measure != "verse" and est_un_don(granularity, kind, kind_provenance, concours)


# Les mêmes règles, pour les scripts qui interrogent le Parquet en SQL.
# `concours` n'étant pas une colonne stockée mais une lecture de l'objet, le SQL
# ne connaît que la part déclarée : les scripts qui ont besoin de la règle
# complète passent par la fonction Python ci-dessus.
SQL_EST_UN_DON = (
    "granularity IS DISTINCT FROM 'aggregate' "
    "AND NOT (beneficiary_kind_provenance = 'declared' "
    "         AND beneficiary_kind IS NOT NULL "
    "         AND beneficiary_kind <> 'association')"
)
SQL_COMPTE_DANS_LES_TOTAUX = (
    SQL_EST_UN_DON + " AND measure IS DISTINCT FROM 'verse'"
)



# Un compte de publication n'est pas une personne morale. Sur data.gouv.fr, les
# fichiers budgétaires de la Ville de Rennes sont déposés par un compte nommé
# « Rennes Métropole en accès libre » : faute de colonne d'attribuant, le site
# créditait l'EPCI de 396 M€ versés par la COMMUNE, et ces lignes ne se
# dédupliquaient pas avec les mêmes données publiées sur le portail — deux
# donateurs différents, donc deux clés métier.
_COMPTES_DE_PUBLICATION = ("acces libre", "open data", "opendata",
                           "donnees ouvertes", "portail")

# Formes juridiques qu'on retire avant de confronter un nom au référentiel.
_FORMES_COLLECTIVITE = ("ville de", "ville d", "commune de", "commune d",
                        "mairie de", "mairie d", "departement de",
                        "departement du", "departement d", "region")


def est_un_compte_de_publication(nom):
    """Vrai si ce libellé nomme un compte open data et non une collectivité."""
    t = fold(nom or "")
    return bool(t) and any(m in t for m in _COMPTES_DE_PUBLICATION)


def _noms_du_referentiel():
    global _NOMS_REFERENTIEL
    try:
        return _NOMS_REFERENTIEL
    except NameError:
        pass
    ref = referentiel()
    noms = set()
    for cle in ("communes", "departements", "regions", "epci"):
        for v in ref.get(cle, {}).values():
            n = fold(v.get("nom") or "")
            if len(n) >= 4:
                noms.add(n)
    _NOMS_REFERENTIEL = noms
    return noms


def collectivite_du_libelle(*libelles):
    """Collectivité nommée dans un titre de jeu, ou None.

    Ne sert QUE de dernier recours, quand le fichier ne porte aucune colonne
    d'attribuant et que le compte qui publie n'est pas une personne morale.
    Rien n'est deviné : un segment n'est retenu que s'il correspond EXACTEMENT
    à un nom du référentiel INSEE, une fois sa forme juridique retirée. Un
    titre qui ne nomme personne rend None, et l'appelant garde son repli.
    """
    noms = _noms_du_referentiel()
    for libelle in libelles:
        brut = str(libelle or "")
        # Le tiret ne coupe que s'il est SUIVI d'une espace : « CA 2011- Ville de
        # Rennes » se coupe, « Noyal-Châtillon-sur-Seiche » reste entier.
        segments = [x.strip() for x in re.split(r"\s*[-–|]\s+|[|]", brut) if x.strip()]
        # Puis TOUS les groupes de 1 à 4 mots contigus : la collectivité est
        # parfois au milieu du titre (« Subventions Besançon 2008-2012 ») ou à
        # sa fin (« … aux associations Noyal-Châtillon-sur-Seiche »). Le filtre
        # n'est pas la position mais le référentiel : seul un nom qui EXISTE à
        # l'INSEE est retenu.
        mots = brut.split()
        segments += [" ".join(mots[i:i + k])
                     for k in range(1, 5) for i in range(len(mots) - k + 1)]
        for seg in segments:
            t = fold(seg)
            for forme in _FORMES_COLLECTIVITE:
                if t.startswith(forme + " "):
                    t = t[len(forme) + 1:]
                    break
            if t in noms:
                return seg
    return None


# ------------------------------------- identité d'un donateur --------------
#
# Une même collectivité ne se nomme pas pareil d'une publication à l'autre :
# « CONSEIL DEPARTEMENTAL DE LA SOMME » et « DEPARTEMENT DE LA SOMME », « VILLE
# DE TOULOUSE » et « MAIRIE DE TOULOUSE », « COMMUNE D IFFENDIC » et « COMMUNE
# DE IFFENDIC ». La clé métier comparait ces libellés tels quels : deux
# publications d'une même collectivité ne se croisaient donc JAMAIS, et leurs
# doublons restaient dans les totaux.
#
# L'identité se lit en deux temps : la FORME juridique donne le niveau, les
# mots restants donnent le noyau du nom.

# On retire les prépositions, qui varient avec l'élision (« COMMUNE D IFFENDIC »
# contre « COMMUNE DE IFFENDIC »), mais JAMAIS les articles : ils font partie du
# nom. « Baule » dans le Loiret et « La Baule » en Loire-Atlantique sont deux
# communes distinctes, et les confondre effacerait les subventions de l'une.
# Les retirer n'apporterait rien par ailleurs : « DEPARTEMENT DE LA SOMME » et
# « CONSEIL DEPARTEMENTAL DE LA SOMME » gardent l'article tous les deux.
_VIDES_DONATEUR = frozenset(("de", "du", "des", "d", "et", "aux", "au", "a", "en"))

# Ordonné du plus spécifique au plus général : « conseil departemental » doit
# gagner avant « departement », sans quoi le noyau garderait « conseil ».
_FORMES_DONATEUR = (
    (("conseil", "departemental"), "departement"),
    (("conseil", "departementale"), "departement"),
    (("conseil", "general"), "departement"),
    (("departement",), "departement"),
    (("conseil", "regional"), "region"),
    (("region",), "region"),
    (("communaute", "agglomeration"), "epci"),
    (("communaute", "communes"), "epci"),
    (("communaute", "urbaine"), "epci"),
    (("metropole",), "epci"),
    (("ville",), "commune"),
    (("mairie",), "commune"),
    (("commune",), "commune"),
)

# Sigles d'intercommunalité tels qu'elles se signent, en tête de libellé.
_SIGLES_EPCI = {"ca": "epci", "cc": "epci", "cu": "epci", "ct": "epci"}

# Premier mot de chaque forme : sert à trouver où commence la collectivité dans
# le libellé d'un de ses services.
_TETES_FORME = frozenset(forme[0] for forme, _ in _FORMES_DONATEUR)

# FUSIONS DE COLLECTIVITÉS — deux entités n'en font plus qu'une à partir d'une
# date, et c'est la loi qui le dit. Avant cette date les distinguer n'est pas
# une erreur : c'est la vérité de l'époque, chacune ayant son budget propre.
#
#   Paris — la commune de Paris et le département de Paris ont fusionné en une
#   collectivité unique à statut particulier, « Ville de Paris », le
#   1er janvier 2019 (loi n° 2017-257 du 28 février 2017 relative au statut de
#   Paris et à l'aménagement métropolitain : art. 8 pour l'entrée en vigueur,
#   art. 10 pour la substitution dans tous les droits et obligations).
#   Ce que publie la Ville le confirme ligne à ligne : son jeu « subventions
#   votées » porte les deux collectivités de 2013 à 2018, et une seule ensuite.
#
# (niveau absorbé, noyau absorbé, niveau absorbant, noyau absorbant, 1re année)
FUSIONS_COLLECTIVITES = (
    ("departement", "paris", "commune", "paris", 2019),
)


def _mots_donateur(nom_norm):
    return [m for m in re.findall(r"[a-z0-9]+", fold(nom_norm or ""))
            if m not in _VIDES_DONATEUR]


def identite_donateur(nom_norm, annee=None):
    """Identité canonique d'un donateur — « commune:paris », « departement:somme ».

    Sert UNIQUEMENT à la clé métier : `donor_name_raw` reste ce que la source a
    publié. Un libellé qu'on ne sait pas décomposer se rend tel quel, plié — on
    ne rapproche jamais deux donateurs sur une ressemblance vague.
    """
    mots = _mots_donateur(nom_norm)
    if not mots:
        return ""

    # Une DIRECTION est un service interne, jamais une personne morale : le
    # donateur est la collectivité qu'elle sert. « Direction des Finances et
    # des Achats - Ville de Paris », c'est la Ville de Paris. On ne coupe que
    # sur « direction » : un CCAS, une régie ou un syndicat sont, eux, des
    # entités distinctes de leur commune et ne doivent pas y être fondus.
    if mots[0] == "direction":
        # On coupe au DERNIER mot de forme : « direction des finances et des
        # achats ville de paris » doit rendre « ville paris », pas « finances
        # achats ville paris ». Couper au premier indice qui contient encore
        # une forme plus loin garderait tout le nom du service.
        for i in range(len(mots) - 1, 0, -1):
            if mots[i] in _TETES_FORME:
                mots = mots[i:]
                break

    niveau = None
    for forme, lvl in _FORMES_DONATEUR:
        if all(m in mots for m in forme):
            niveau, mots = lvl, [m for m in mots if m not in forme]
            break
    if niveau is None and mots[0] in _SIGLES_EPCI:
        niveau, mots = _SIGLES_EPCI[mots[0]], mots[1:]

    noyau = " ".join(mots)
    if not noyau:
        return fold(nom_norm or "")
    if niveau is None:
        return noyau

    if annee is not None:
        for absorbe, n_absorbe, absorbant, n_absorbant, depuis in FUSIONS_COLLECTIVITES:
            if niveau == absorbe and noyau == n_absorbe and annee >= depuis:
                niveau, noyau = absorbant, n_absorbant
                break
    return f"{niveau}:{noyau}"


def fusion_de_collectivite(nom_norm, annee):
    """Niveau corrigé quand une fusion a eu lieu, sinon None.

    Un versement de 2021 attribué au « département de Paris » nomme une entité
    qui n'existait plus : le niveau affiché doit dire commune. Le libellé
    publié, lui, n'est pas retouché.
    """
    if annee is None:
        return None
    mots = _mots_donateur(nom_norm)
    if not mots:
        return None
    niveau = None
    for forme, lvl in _FORMES_DONATEUR:
        if all(m in mots for m in forme):
            niveau, mots = lvl, [m for m in mots if m not in forme]
            break
    noyau = " ".join(mots)
    for absorbe, n_absorbe, absorbant, n_absorbant, depuis in FUSIONS_COLLECTIVITES:
        if niveau == absorbe and noyau == n_absorbe and annee >= depuis:
            return absorbant
    return None


def business_key(siret, name_norm, donor_norm, year, amount, purpose_norm):
    """Clé métier de SCHEMA.md — identité d'une subvention entre sources.

    Le donateur y entre par son IDENTITÉ, pas par son libellé : sans cela deux
    publications de la même collectivité ne se dédupliquent jamais.
    """
    import hashlib
    # Le NOM d'abord, le SIRET seulement à défaut. Prendre le SIRET en premier
    # rendait la clé instable entre sources : la Ville de Paris publie le SIRET
    # dans un jeu et pas dans l'autre, si bien que la même subvention — même
    # bénéficiaire, même montant, même objet — produisait deux clés et restait
    # comptée deux fois. Le nom, lui, est présent partout.
    # Deux organismes homonymes peuvent alors partager une clé : c'est la
    # déduplication qui refuse de les fondre quand leurs SIRET se contredisent.
    parts = [name_norm or siret or "", identite_donateur(donor_norm, year),
             str(year or ""),
             f"{amount:.2f}" if amount is not None else "", (purpose_norm or "")[:120]]
    return hashlib.sha1("||".join(parts).encode("utf-8")).hexdigest()[:20]


# ------------------------------------- reconnaissance des colonnes ----------
#
# Les publications réelles ne respectent jamais tout à fait le standard SCDL :
# « Nom association », « Réalisé (en numéraire) », « nomBeneficiere »… La
# reconnaissance se fait donc sur les MOTS du libellé, jamais sur une
# sous-chaîne — « Nom ETS attribuant la subvention » contient « subvention »
# sans être un montant, et « Nature juridique de l'organisme » contient
# « organisme » sans être un bénéficiaire.
#
# Chaque rôle est décrit par des motifs ordonnés du plus spécifique au plus
# général, plus une liste de mots qui DISQUALIFIENT la colonne.

_MOTS_COLONNE = re.compile(r"[a-z0-9]+")


_CAMEL = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")


def mots_colonne(libelle):
    """Mots significatifs d'un libellé de colonne, pliés.

    Le camelCase est découpé avant pliage : le standard SCDL nomme ses colonnes
    `nomBeneficiaire`, `idAttribuant`, `dateConvention`. Sans ce découpage,
    chaque libellé resterait un seul mot collé, introuvable par les motifs.
    """
    return tuple(_MOTS_COLONNE.findall(fold(_CAMEL.sub(" ", str(libelle or "")))))


# Dans un motif, ce jeton tient la place d'un exercice : il n'apparie que les
# mots qui sont une année plausible. Il sert aux colonnes qui datent leur propre
# montant — `bp_2012`, `ca_2013` chez la Ville de Rennes — où l'intitulé change
# à chaque millésime et où aucun motif figé ne peut tenir.
EXERCICE = "<exercice>"


def _est_exercice(mot):
    return len(mot) == 4 and mot.isdigit() and 1990 <= int(mot) <= 2100


# Motifs si généraux qu'ils ne valent QUE si le libellé de colonne se réduit à
# eux. `associations` désigne la colonne des associations quand c'est tout ce
# que la colonne s'appelle ; dans « Subv.d'équipement - provision pour
# associations sportives », le mot n'est qu'un mot d'une phrase — et cette
# phrase-là est une LIGNE DE DONNÉES que le détecteur d'en-tête a prise pour un
# en-tête (Ville de Rennes, CA 2017). Sans cette réserve, le correctif qui
# rouvre Fleury-sur-Orne et Issy-les-Moulineaux fait entrer en même temps deux
# fichiers dont les « colonnes » n'en sont pas.
MOTIFS_STRICTS = frozenset({
    ("associations",), ("organisation",), ("destinataire",), ("destinataires",),
    ("liborgabenef",), ("libelle",),
})


# (motifs retenus, mots disqualifiants)
ROLES_COLONNES = {
    "beneficiaire": (
        [("nom", "beneficiaire"), ("nom", "beneficiere"), ("nom", "association"),
         ("nom", "organisme", "beneficiaire"), ("raison", "sociale"),
         ("beneficiaire",), ("beneficiaires",), ("beneficiere",),
         ("denomination",), ("association",), ("organisme",), ("structure",),
         ("nom", "tiers"),
         # Plusieurs portails nomment le bénéficiaire `tiers` tout court
         # (Ville de Grenoble, Région Bretagne). Le motif est très général,
         # d'où les disqualifiants `insee`, `commune`, `ville`, `adresse`,
         # `postal` : sans eux, il attraperait `tiers_commune_insee` et le
         # bénéficiaire serait lu dans un code géographique.
         ("tiers",),
         # Quatre graphies relevées dans les jeux ÉCARTÉS des manifestes, donc
         # mesurées et non supposées (cf. RESTE-A-FAIRE.md §1d) :
         #   `beneficiare`   faute de frappe de la Ville de Rennes, dans ses
         #                   comptes administratifs d'équipement ;
         #   `organismes`    Agglopolys et la Ville de Blois — le singulier
         #                   était reconnu, le pluriel non ;
         #   `attributaires` celui à qui la subvention est attribuée, Blois 2018 ;
         #   `noms`          Blois 2023, pluriel du repli le plus général.
         # Gain mesuré : 10 jeux, 0 régression sur les 876 jeux de colonnes
         # connus. Dont une collectivité et une intercommunalité NOUVELLES.
         ("beneficiare",), ("organismes",), ("attributaire",), ("attributaires",),
         ("noms",),
         # Cinq graphies de plus, relevées dans les jeux ÉCARTÉS des manifestes
         # du 22/08/2026 et vérifiées SUR LA DONNÉE, pas sur le libellé seul :
         #   `liborgabenef`   « libellé organisme bénéficiaire », Région
         #                    Île-de-France, 22 958 versements ;
         #   `organisation`   Ville de Montreuil ;
         #   `destinataire(s)` Ville de Saint-Maur-des-Fossés ;
         #   `associations`   Fleury-sur-Orne, Issy-les-Moulineaux,
         #                    Noyal-Châtillon-sur-Seiche. Le singulier était
         #                    reconnu depuis toujours, le pluriel non.
         # Tous STRICTS (cf. MOTIFS_STRICTS) : ce sont des mots trop courants
         # pour être cherchés au milieu d'une phrase.
         ("liborgabenef",), ("organisation",),
         ("destinataire",), ("destinataires",), ("associations",),
         ("nom",),
         # EN TOUT DERNIER, et STRICT. Les documents budgétaires de la Ville de
         # Rennes (`sous_fonction;libelle;bp_2013`) et les financements de la
         # DRAC des Pays de la Loire n'ont pas d'autre colonne de bénéficiaire
         # que `libelle`. Le motif ne vaut que si la colonne s'appelle
         # exactement ainsi : partout ailleurs, `libelle` désigne l'objet, et
         # c'est d'ailleurs un DISQUALIFIANT du rôle « montant ».
         ("libelle",)],
        # « financeur » disqualifie : `organismes_financeurs` est celui qui
        # PAIE. Sans lui, le motif `organismes` lisait le bénéficiaire dans la
        # colonne du donateur — une inversion silencieuse.
        ("attribuant", "attribuants", "financeur", "financeurs",
         "demandeur", "dataset", "prenom", "categorie", "nature",
         "juridique", "type", "code", "numero", "siret", "siren", "id",
         "insee", "commune", "ville", "adresse", "postal"),
    ),
    "montant": (
        [("montant", "vote"), ("montant", "accorde"), ("montant", "attribue"),
         ("montant", "subvention"), ("montant", "total"), ("montant", "euros"),
         ("realise", "numeraire"), ("montant",), ("subvention", "euros"),
         # Grenoble-Alpes Métropole intitule sa colonne de montant
         # `total_en_euros`, `total_euros` : trois millésimes (2017, 2018,
         # 2021) sortaient pour ce seul mot. Le disqualifiant « nature »
         # protège les colonnes de valorisation en nature, qui portent
         # souvent le même « total ».
         ("total", "euros"), ("total", "euro"),
         # La Ville de Rennes date la colonne elle-même : `bp_2012` (budget
         # primitif), `ca_2013` (compte administratif). L'étape budgétaire
         # seule serait un motif bien trop court — c'est l'exercice accolé qui
         # fait la preuve qu'il s'agit d'un montant.
         ("bp", EXERCICE), ("ca", EXERCICE), ("br", EXERCICE), ("bs", EXERCICE),
         ("credit", "vote"), ("aide", "montant"), ("subventions",), ("subvention",),
         # EN DERNIER, et c'est le point : `mandate` désigne un montant PAYÉ, à
         # ne préférer à aucun autre. Grand Paris Sud publie `MONTANT ATTRIBUE`
         # ET `MANDATE` dans le même fichier — mis en tête, ce motif aurait fait
         # lire le payé là où l'attribué était disponible.
         #   `Mandaté`          Département de Maine-et-Loire, 17 756 lignes ;
         #   `MANDATE`          Grand Paris Sud ;
         #   `mt_mandate_budg`  GrandSoissons Agglomération ;
         #   `mtsubv`           Région Île-de-France, avec `liborgabenef`.
         ("mtsubv",), ("mandate",),
         # Les documents budgétaires (budget primitif, compte administratif)
         # nomment leur colonne d'argent par l'étape, pas par « montant » :
         #   `realise_de_l_annee`  ce qui a été exécuté (Rennes, Vezin-le-Coquet) ;
         #   `budget_de_l_annee`   ce qui a été voté ;
         #   `somme`               le cumul par tiers d'un compte administratif.
         ("realise", "annee"), ("budget", "annee"), ("somme",)],
        ("attribuant", "nom", "objet", "nature", "date", "pourcentage", "taux",
         "nombre", "dossier", "reference", "libelle", "type", "prestation"),
    ),
    "attribuant": (
        # `nom collectivite` AVANT `collectivite` : les fichiers de balance
        # budgétaire portent les deux, et la première ne contient que la
        # catégorie (« COMMUNE ») quand la seconde nomme la collectivité
        # (« Ville de Rennes », « VEZIN-LE-COQUET »). Le motif court gagnait, et
        # le donateur devenait « COMMUNE » — donc générique, donc remplacé par le
        # compte qui publie sur data.gouv.fr.
        [("nom", "attribuant"), ("nom", "ets", "attribuant"), ("attribuant",),
         ("nom", "collectivite"), ("collectivite",), ("financeur",)],
        # « code » disqualifie : GrandSoissons Agglomération publie une colonne
        # `Code Collectivité` qui ne contient que « 1 ». Sans ce mot, le motif
        # `collectivite` y lisait le donateur, et 172 subventions entraient au
        # nom d'un donateur appelé « 1 » — l'intercommunalité restait invisible.
        ("beneficiaire", "siret", "siren", "id", "numero", "code"),
    ),
    "siret_beneficiaire": (
        [("id", "beneficiaire"), ("siret", "beneficiaire"), ("numero", "siret"),
         ("siret",), ("sirenbeneficiaire",)],
        ("attribuant", "attributaire"),
    ),
    "rna_beneficiaire": ([("rna", "beneficiaire"), ("numero", "rna"), ("rna",)], ("attribuant",)),
    "objet": (
        [("objet", "subvention"), ("objet", "dossier"), ("objet",), ("intitule",),
         ("libelle", "subvention"), ("description",)],
        ("date", "montant", "nature"),
    ),
    # `publication` vient en dernier : c'est le libellé du compte administratif
    # de Paris (« CA 2018 »), seul endroit où l'exercice soit écrit. Sans lui,
    # 67 413 lignes restaient sans année.
    "annee": ([("annee", "budgetaire"), ("annee", "decision"), ("exercice",),
               ("millesime",), ("annee",), ("publication",)], ("date",)),
    "date_convention": ([("date", "convention"), ("date", "decision"),
                         ("dateconvention",)], ()),
    "nature": ([("nature", "subvention"), ("nature",)], ("juridique", "beneficiaire")),
    # Quand la source DÉCLARE la nature juridique du bénéficiaire, elle vaut
    # mieux que notre devinette sur le nom : c'est le publieur qui sait si
    # « Paris Habitat » est une association ou un établissement public.
    "nature_beneficiaire": (
        [("nature", "juridique", "beneficiaire"), ("categorie", "beneficiaire"),
         ("nature", "juridique"), ("type", "beneficiaire"),
         ("categorie", "juridique")],
        ("attribuant", "subvention", "montant"),
    ),
}

# Natures juridiques telles que les publieurs les écrivent, ramenées à notre
# vocabulaire. Ce qui n'est reconnu par aucun motif reste `None` : on ne devine
# pas à partir d'un libellé qu'on ne comprend pas.
_NATURES_BENEFICIAIRE = (
    ("association", ("association", "associatif", "loi 1901", "loi de 1901",
                     "fondation", "organisme a but non lucratif", "obnl")),
    ("public_body", ("etablissement public", "etablissements publics",
                     "etablissement de droit public", "collectivite",
                     "commune", "departement", "region", "syndicat mixte",
                     "chambre consulaire", "gip", "epic", "epa")),
    ("company", ("entreprise", "societe", "sarl", "sas", "sa ", "eurl",
                 "commercant", "artisan", "cooperative", "sem", "spl")),
    ("individual", ("personne physique", "personnes physiques", "particulier",
                    "particuliers", "menage")),
)


def kind_from_nature(libelle):
    """Nature du bénéficiaire DÉCLARÉE par la source, ou None.

    Le publieur sait ce que nous ne saurions deviner d'un nom : que
    « Paris Habitat » est un établissement public et non une association.
    Quand il l'écrit, sa parole prime sur notre heuristique.
    """
    t = fold(libelle or "")
    if not t:
        return None
    for kind, motifs in _NATURES_BENEFICIAIRE:
        if any(m in t for m in motifs):
            return kind
    return None


# Une même collectivité publie souvent ses subventions deux fois : ce qu'elle a
# VOTÉ, et ce qu'elle a effectivement VERSÉ (annexe au compte administratif).
# C'est le même argent vu deux fois. Les additionner double la collectivité, on
# les distingue donc par `measure` et seul « attribue » entre dans les totaux.
_MOTS_VERSE = ("compte administratif", "subventions versees", "subventions verses",
               "mandatees", "mandate", "paiements", "versements effectues")
# « CA 2014 » est un compte administratif écrit en abrégé — la Ville de Rennes
# ne l'écrit JAMAIS en toutes lettres. Sans ce motif, le site comptait le budget
# primitif ET son exécution du même exercice comme deux subventions votées :
# Rennes 2012 pesait 74,56 M€ pour un budget associatif d'environ 54 M€.
# Le sigle seul serait bien trop court ; c'est l'exercice accolé qui fait la
# preuve, exactement comme le motif de colonne `("ca", EXERCICE)`.
_CA_EXERCICE = re.compile(r"\bca[ ._-]?(19|20)\d{2}\b")


def measure_of(*libelles):
    """« verse » si le libellé désigne une exécution budgétaire, sinon « attribue ».

    On lui passe le titre du jeu, le nom du fichier, **et le libellé de la
    colonne de montant**. Cette dernière est le témoin le plus direct qui soit :
    une colonne qui s'appelle `Mandaté` porte de l'argent PAYÉ, quoi que dise le
    titre du jeu. Le Département de Maine-et-Loire publie ainsi 17 756
    mandatements sous un titre qui ne dit que « Subventions aux associations ».
    Mesuré le 23/08/2026 : la colonne ne fait basculer **aucun** des jeux déjà
    retenus, elle ne tranche que pour ceux que la phase 11 rouvre.
    """
    # Les séparateurs sont ramenés à l'espace ICI, et seulement ici. Le même
    # fichier lu par le portail s'appelle `subventions_versees` et lu par
    # data.gouv.fr « Subventions versées » : sans cela, Fleury-sur-Orne était
    # « voté » d'un côté et « payé » de l'autre, pour la même donnée. Le
    # résultat négatif du §4a ne portait pas là-dessus : il disait de ne pas
    # toucher à `fold` lui-même, dont dépend toute la reconnaissance.
    brut = " ".join(fold(x or "") for x in libelles)
    t = brut.replace("_", " ").replace("-", " ")
    if _CA_EXERCICE.search(brut) or _CA_EXERCICE.search(t):
        return "verse"
    return "verse" if any(m in t for m in _MOTS_VERSE) else "attribue"


# Colonnes qui trahissent une aide EN NATURE : ce sont des valorisations de
# locaux ou de personnel, pas des euros décaissés. Les sommer avec des
# versements fausserait les totaux.
MOTS_AIDE_EN_NATURE = (("total", "aide", "nature"), ("prestations", "nature"),
                       ("mise", "disposition", "locaux"), ("aide", "nature"),
                       # La Ville de Grenoble dit « avantages en nature » là où
                       # d'autres disent « aides » : sans ce mot, ses quatre
                       # fichiers de valorisations étaient écartés pour
                       # « aucune colonne de montant », un motif qui cache la
                       # vraie raison dans le manifeste.
                       ("avantages", "nature"), ("avantage", "nature"))


def _correspond(mots, motif, disqualifiants):
    if any(d in mots for d in disqualifiants):
        return False
    # Un motif strict ne vaut que si la colonne ne s'appelle QUE comme lui.
    if motif in MOTIFS_STRICTS:
        return list(mots) == list(motif)
    if all(any(_est_exercice(x) for x in mots) if m is EXERCICE else m in mots
           for m in motif):
        return True
    # Les exports Opendatasoft écrivent les colonnes tout en minuscules et sans
    # séparateur : `nombeneficiaire`, `idattribuant`, `dateconvention`. Le
    # découpage camelCase ne peut rien pour eux, il faut donc reconnaître aussi
    # le motif accolé. Sans cela, la Région Bretagne voyait son bénéficiaire
    # cherché dans `tiers_commune_insee`.
    return len(motif) > 1 and "".join(motif) in mots


def trouver_colonne(entete, role):
    """Nom de la colonne jouant ce rôle dans un en-tête, ou None.

    Les motifs sont essayés dans l'ordre : le premier motif qui trouve une
    colonne gagne, donc le plus spécifique l'emporte sur le plus général.
    """
    motifs, disqualifiants = ROLES_COLONNES[role]
    mots_par_colonne = [(c, mots_colonne(c)) for c in entete if c]
    for motif in motifs:
        for colonne, mots in mots_par_colonne:
            if _correspond(mots, motif, disqualifiants):
                return colonne
    return None


def annee_du_libelle(*libelles):
    """Année lue dans un titre de fichier ou de jeu, quand aucune colonne ne la porte.

    Beaucoup de collectivités publient **un fichier par exercice** et ne
    répètent pas l'année dans les lignes : `subventions_grenoble_2016.csv`,
    « Subventions accordées en 2019 ». Ces fichiers entraient sans année —
    160 sources, 160 210 lignes et 4,1 Md€ hors de toute lecture par
    millésime. Pire, l'année faisant partie de la clé métier, une source sans
    année ne se déduplique pas avec la même donnée publiée ailleurs avec son
    année : Grenoble-Alpes Métropole était ainsi comptée deux fois, pour
    72,5 M€.

    On n'accepte qu'une **seule** année distincte dans le libellé. « Subventions
    2008-2012 » ou « CA 2019 - BP 2020 » ne disent pas de quel exercice il
    s'agit : deviner serait inventer, la ligne reste alors sans année. Les
    libellés sont essayés dans l'ordre reçu — le nom du fichier avant le titre
    du jeu, du plus précis au plus général.

    L'année ainsi obtenue n'est pas publiée dans la ligne : elle est déduite,
    et `year_provenance` doit le dire (« inferred »).
    """
    for libelle in libelles:
        annees = {int(a) for a in _ANNEES_LIBELLE.findall(str(libelle or ""))
                  if 1990 <= int(a) <= 2100}
        if len(annees) == 1:
            return annees.pop()
    return None


def porte_des_subventions(entete):
    """(vrai/faux, raison) — cet en-tête décrit-il bien des subventions ?"""
    benef = trouver_colonne(entete, "beneficiaire")
    if not benef:
        return False, "aucune colonne de bénéficiaire"
    montant = trouver_colonne(entete, "montant")
    if not montant:
        tous = [mots_colonne(c) for c in entete if c]
        if any(all(m in mots for m in motif) for motif in MOTS_AIDE_EN_NATURE for mots in tous):
            return False, "aides en nature (valorisations, pas des versements)"
        return False, "aucune colonne de montant"
    # Une seule et même colonne ne peut pas être à la fois le bénéficiaire et le
    # montant. Quand elle l'est, ce n'est pas un en-tête : c'est le titre du
    # rapport, lu comme une ligne de colonnes — « VILLEMOMBLE - SUBVENTIONS AUX
    # ASSOCIATIONS - ANNEE 2012 » suivi de deux cellules vides. Le fichier
    # entrait sans que rien ne le signale.
    if benef == montant:
        return False, "en-tête d'une seule colonne (titre du rapport, pas un en-tête)"
    return True, None
