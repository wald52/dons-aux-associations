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
