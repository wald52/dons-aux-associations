"""Construit l'index que le NAVIGATEUR interroge (phase 13).

Remplace `build_search_index.py`, dont il reprend intégralement la résolution
d'identité et les règles de cumul — seuls le FORMAT servi et le hachage de
répartition changent.

Pourquoi changer. L'ancien index était servi en Parquet et interrogé par
DuckDB-WASM : la page de recherche téléchargeait 34,2 Mo de moteur puis 17,7 Mo
d'index AVANT d'afficher un champ de saisie. Mesuré 4,5 s en local, sans
latence ; sur un téléphone, des dizaines de secondes et ~50 Mo de données
mobiles. Un moteur SQL généraliste est un prix très élevé pour deux questions :
« quelles associations portent ce nom ? » et « qui finance celle-ci ? ».

Résolution d'identité, INCHANGÉE (voir `build_search_index.py` pour le détail
du raisonnement) :

  1. le SIREN quand il existe ;
  2. à défaut le RNA ;
  3. à défaut le NOM NORMALISÉ **plus le département** — jamais le nom seul.

Quatre sorties :

  data/aggregates/suggest.json.gz          (~0,7 Mo)
      Rang 1 de l'autocomplétion : les 25 000 plus gros bénéficiaires, les
      34 936 communes du référentiel, les 101 départements, les 18 régions.
      Chargé en tâche de fond dès l'accueil : la première lettre tapée répond
      sans attendre quoi que ce soit.

  data/recherche/noms.json.gz              (~4,7 Mo)
      Rang 2 : les 427 451 bénéficiaires, en colonnes parallèles. Arrive
      derrière le rang 1 et COMPLÈTE les résultats en place. `nom_norm` n'y
      est pas : le pliage se refait dans le navigateur (2,6 Mo économisés).

  data/recherche/rna.json.gz               (~0,2 Mo)
      Les RNA, de façon creuse, dans l'ordre des noms. Servi à personne : lu
      par `build_angle_mort.py`, qui a besoin du RNA d'un bénéficiaire même
      quand celui-ci est identifié par son SIREN.

  data/recherche/ids/BBB.json.gz           (512 blocs, ~10 Ko pièce)
      Les `benef_id` par rang alphabétique. Séparés du rang 2 parce qu'ils ne
      servent qu'au moment d'ouvrir une fiche : les embarquer coûterait
      2,7 Mo à toute recherche.

  data/recherche/fiches/NNN.json.gz        (512 shards, ~90 Ko pièce)
      Les versements ligne à ligne, en colonnaire + dictionnaires, PLUS le
      résumé de chaque bénéficiaire. Une fiche est donc AUTOSUFFISANTE : un
      lien partagé l'affiche avec une seule requête, sans jamais charger
      l'index des noms.

Le shard se déduit du `benef_id` seul, par FNV-1a 32 bits. L'ancien hachage
(somme des octets modulo 64) était mal réparti : la somme des codes d'un
identifiant comme `S853318459` tient dans une bande d'environ 80 valeurs, d'où
des shards de 233 Ko face à des shards de 1,66 Mo — un facteur 7 mesuré. Modulo
512 il se serait effondré sur un dixième des shards.

**`shard_of` ici et `shardDe` dans `assets/js/recherche.js` DOIVENT rester
identiques.** `verify.py` le vérifie.

Usage : python3 scripts/pipeline/build_index_navigateur.py
Idempotent.
"""

import collections
import gzip
import hashlib
import io
import json
import os
import re
import shutil
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if __name__ == "__main__":
    # Uniquement en exécution directe : re-emballer stdout au chargement du
    # module casserait la sortie du script qui l'importe (verify.py).
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import pyarrow.dataset as ds

import common as C

ROOT = C.ROOT
CANON = os.path.join(ROOT, "data", "canonical", "subventions")
OUT = os.path.join(ROOT, "data", "recherche")
AGG = os.path.join(ROOT, "data", "aggregates")
REFERENTIEL = os.path.join(ROOT, "data", "referentiel")

COLS = [
    "beneficiary_siren", "beneficiary_rna", "beneficiary_name_norm",
    "beneficiary_name_raw", "beneficiary_dep_code", "beneficiary_kind",
    "donor_level", "donor_name_raw", "donor_program",
    "amount_eur", "amount_rejected_eur", "year", "granularity",
    "measure", "beneficiary_kind_provenance",
    "purpose_raw", "purpose_norm", "source_label", "source_url",
    "quality_flags",
    # Phase 15 — le verdict de l'INSEE et la famille juridique affichée. La
    # famille voyage jusqu'à la fiche : c'est elle qui tient la consigne
    # « bien les différencier pour ne pas que le public se sente trompé ».
    "beneficiary_legal_category", "beneficiary_family", "beneficiary_rna_insee",
    "beneficiary_is_associatif",
]

# Ordre figé des échelons : l'index sert un MASQUE de bits, pas une liste de
# libellés. Sept mots répétés 427 451 fois pèsent ; sept bits ne pèsent rien,
# et le navigateur peut alors AFFICHER quels échelons financent une
# association au lieu de le cacher dans un attribut `title`, inatteignable au
# doigt comme au clavier.
ECHELONS = ["etat", "operateur", "region", "departement", "epci", "commune", "inconnu"]

NB_SHARDS = 512
NB_BLOCS = 512
TAILLE_SUGGEST = 25000

_BLANCS = re.compile(r"[\r\n\t]+")


def nombre(v):
    """Un montant entier s'écrit sans « .0 ». Sur 2,8 millions de lignes, ces
    deux caractères pèsent plus que bien des colonnes.

    Un montant ABSENT reste absent : le confondre avec un zéro publié ferait
    disparaître la différence entre « la source n'a rien mis » et « la source a
    écrit 0 € », qui concerne 79 066 lignes bien réelles."""
    if v is None:
        return None
    v = round(v, 2)
    return int(v) if v == int(v) else v


# Les cinq cases de `verify.py` — « toute ligne tombe dans une case et une
# seule ». L'ordre EST la règle : un agrégat qui serait aussi une prestation
# reste un agrégat, et c'est ainsi que `build_aggregates.py` les compte.
# `hors_champ` et `hors_champ_insee` disent tous deux « le bénéficiaire n'est
# pas une association », mais PAS sur la même autorité, et le lecteur a droit à
# la différence : dans un cas c'est le publieur qui l'écrit, dans l'autre c'est
# le registre national des personnes morales qui le déclare alors que le
# publieur, lui, ne disait rien.
CAS = ["vote", "paye", "hors_don", "agrege", "hors_champ", "hors_champ_insee"]

# La famille affichée pour un bénéficiaire que l'INSEE documente et qui n'est
# NI une association NI une fondation. Ce n'est pas une famille du périmètre :
# c'est la phrase qui explique pourquoi ses montants sont gris.
HORS_PERIMETRE = "hors périmètre — ni association ni fondation"


def cas_du_versement(granularity, measure, kind, kind_provenance, concours,
                     categorie_juridique=None):
    """Dans quelle case tombe ce versement, et donc s'il entre dans les totaux.

    Le verdict voyage AVEC le versement, comme `concours` avant lui, parce que
    le navigateur ne peut pas le recalculer : la nature juridique déclarée du
    bénéficiaire n'est pas dans l'index, et l'y mettre pour cela seul serait
    réimplémenter en JavaScript la règle que `common.py` écrit une fois.
    Mesuré avant de le faire : sans cette colonne, la fiche de COALLIA
    affichait 1 097 498 188 € contre 1 097 476 696 € au pipeline — 21 492 €
    d'écart, trois lignes dont la source DÉCLARE un bénéficiaire non
    associatif."""
    if granularity == "aggregate":
        return "agrege"
    if concours != "don":
        return "hors_don"
    if C.est_associatif(categorie_juridique) is False:
        return "hors_champ_insee"
    if not C.est_un_don(granularity, kind, kind_provenance, concours,
                        categorie_juridique):
        return "hors_champ"
    if measure == "verse":
        return "paye"
    return "vote"


def texte(v):
    """Un champ destiné à une colonne jointe par « \\n » ne peut pas en
    contenir : une seule fin de ligne dans un objet décalerait tout le reste."""
    return _BLANCS.sub(" ", v).strip() if v else ""


def shard_of(bid):
    """Numéro de shard d'un bénéficiaire — FNV-1a 32 bits, modulo 512.

    Jumeau exact de `shardDe` dans `assets/js/recherche.js`. Toute
    modification ici en exige une là-bas, et réciproquement.
    """
    h = 0x811C9DC5
    for o in bid.encode("ascii"):
        h = ((h ^ o) * 0x01000193) & 0xFFFFFFFF
    return h % NB_SHARDS


def benef_id(siren, rna, norm, dep):
    """Identifiant stable et court du bénéficiaire résolu."""
    if siren:
        return "S" + siren
    if rna:
        return "R" + rna
    return "N" + hashlib.sha1(f"{norm}|{dep or ''}".encode("utf-8")).hexdigest()[:12]


def ecrire_gz(chemin, objet):
    """Écrit un JSON gzippé, de façon reproductible : `mtime=0` sans quoi deux
    exécutions du même script produiraient deux fichiers différents."""
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    brut = json.dumps(objet, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    with gzip.GzipFile(chemin, "wb", compresslevel=9, mtime=0) as f:
        f.write(brut)
    return len(brut), os.path.getsize(chemin)


class Dictionnaire:
    """Répertoire des valeurs d'une colonne. Un shard porte quelques milliers
    de lignes pour quelques dizaines de donateurs et de sources : les stocker
    une fois et n'écrire que des indices divise le fichier par trois."""

    def __init__(self):
        self.valeurs = []
        self._index = {}

    def code(self, v):
        v = texte(v)
        c = self._index.get(v)
        if c is None:
            c = len(self.valeurs)
            self._index[v] = c
            self.valeurs.append(v)
        return c


def charger_referentiel():
    chemin = os.path.join(REFERENTIEL, "communes.json.gz")
    if not os.path.exists(chemin):
        return {}
    with gzip.open(chemin, "rt", encoding="utf-8") as f:
        return json.load(f)


def main():
    print("Construction de l'index de navigateur\n")
    table = ds.dataset(CANON, format="parquet", partitioning="hive").to_table(columns=COLS)
    n = table.num_rows
    col = {c: table.column(c).to_pylist() for c in COLS}

    # ------------------------------------------------------------------ 1 --
    # Résolution d'identité et cumuls. Reprise mot pour mot de
    # `build_search_index.py` : ces règles sont de la doctrine, pas du code
    # d'affichage, et les réécrire serait le meilleur moyen de les faire
    # diverger.
    ids = []
    groups = collections.defaultdict(lambda: {
        "noms": collections.Counter(), "deps": collections.Counter(),
        "kinds": collections.Counter(), "familles": collections.Counter(),
        "n": 0, "montant": 0.0, "ecarte": 0.0, "annees": set(),
        "echelons": set(), "donateurs": set(),
        "par_donateur": collections.Counter(),
        "siren": None, "rna": None, "rna_insee": None, "norm": None,
        "src_disait_asso": False,
    })
    natures = []
    cas = []
    dernier_exercice_donateur = {}
    for i in range(n):
        bid = benef_id(col["beneficiary_siren"][i], col["beneficiary_rna"][i],
                       col["beneficiary_name_norm"][i], col["beneficiary_dep_code"][i])
        ids.append(bid)
        g = groups[bid]
        g["noms"][col["beneficiary_name_raw"][i]] += 1
        if col["beneficiary_dep_code"][i]:
            g["deps"][col["beneficiary_dep_code"][i]] += 1
        g["kinds"][col["beneficiary_kind"][i]] += 1
        if (col["beneficiary_is_associatif"][i] is False
                and col["beneficiary_kind_provenance"][i] == "declared"
                and col["beneficiary_kind"][i] == "association"):
            g["src_disait_asso"] = True
        if not g["rna_insee"] and col["beneficiary_rna_insee"][i]:
            g["rna_insee"] = col["beneficiary_rna_insee"][i]
        if col["beneficiary_family"][i]:
            g["familles"][col["beneficiary_family"][i]] += 1
        elif col["beneficiary_legal_category"][i] is not None:
            # Le bénéficiaire EST documenté, et l'INSEE dit qu'il n'est pas une
            # association. Rester muet serait le pire des cas : quelqu'un qui
            # cherche « SNCF Voyageurs » verrait ses montants grisés sans
            # savoir pourquoi. On le dit donc, en toutes lettres.
            g["familles"][HORS_PERIMETRE] += 1
        g["n"] += 1
        nature = C.nature_du_concours(col["purpose_norm"][i],
                                      col["quality_flags"][i])[0]
        natures.append(nature)
        cas.append(cas_du_versement(
            col["granularity"][i], col["measure"][i], col["beneficiary_kind"][i],
            col["beneficiary_kind_provenance"][i], nature,
            col["beneficiary_legal_category"][i]))
        # Le cumul suit le VERDICT, pas une seconde lecture de la règle : un
        # seul point de décision par ligne, donc aucune divergence possible
        # entre ce que l'index somme et ce que la fiche affichera.
        # `verify.py` recoupe de son côté avec `compte_dans_les_totaux`.
        if cas[-1] == "vote":
            g["montant"] += col["amount_eur"][i] or 0.0
            ident = C.identite_donateur(col["donor_name_raw"][i]) or "?"
            g["par_donateur"][ident] += col["amount_eur"][i] or 0.0
            if col["year"][i]:
                precedent = dernier_exercice_donateur.get(ident)
                if precedent is None or col["year"][i] > precedent:
                    dernier_exercice_donateur[ident] = col["year"][i]
        g["ecarte"] += col["amount_rejected_eur"][i] or 0.0
        if col["year"][i]:
            g["annees"].add(col["year"][i])
        g["echelons"].add(col["donor_level"][i])
        if col["donor_name_raw"][i]:
            g["donateurs"].add(col["donor_name_raw"][i])
        g["siren"] = g["siren"] or col["beneficiary_siren"][i]
        g["rna"] = g["rna"] or col["beneficiary_rna"][i]
        g["norm"] = g["norm"] or col["beneficiary_name_norm"][i]

    print(f"  {n:,} versements -> {len(groups):,} bénéficiaires résolus")

    resume = {}
    for bid, g in groups.items():
        annees = sorted(g["annees"])
        total_donateurs = sum(g["par_donateur"].values())
        principal, montant_principal = (g["par_donateur"].most_common(1) or [(None, 0.0)])[0]
        part = (round(100.0 * montant_principal / total_donateurs, 1)
                if total_donateurs > 0 else None)
        # Jusqu'à quel exercice ses financeurs publient-ils encore ? Une
        # information brute, offerte au lecteur, PAS un verdict — cf. le
        # commentaire de `build_search_index.py` sur l'indicateur de
        # « décrochage » essayé puis abandonné.
        dernier_financeur = max(
            (dernier_exercice_donateur.get(d) or 0 for d in g["par_donateur"]),
            default=0)
        resume[bid] = {
            "nom": texte(g["noms"].most_common(1)[0][0]),
            "nom_norm": g["norm"] or "",
            "siren": g["siren"],
            # Le RNA de la source d'abord ; celui de SIRENE seulement à défaut,
            # et la fiche dit alors d'où il vient. Le site ne remplace jamais un
            # identifiant publié par un autre — il complète ce qui manquait.
            "rna": g["rna"] or g["rna_insee"],
            "rna_de_insee": 1 if (not g["rna"] and g["rna_insee"]) else 0,
            # La source déclarait « association » et l'INSEE dit non. On ne le
            # cache pas : « fidélité maximale à la source » veut qu'on dise ce
            # qu'elle a écrit, même quand on ne la suit pas.
            "src_contredit": 1 if g["src_disait_asso"] else 0,
            "dep": g["deps"].most_common(1)[0][0] if g["deps"] else None,
            "kind": g["kinds"].most_common(1)[0][0],
            # La famille juridique, telle qu'elle sera AFFICHÉE. Consigne de
            # l'utilisateur du 26/08/2026 : ces familles comptent toutes, mais
            # elles doivent être différenciées, « pour ne pas que le public se
            # sente trompé ».
            "famille": g["familles"].most_common(1)[0][0] if g["familles"] else "",
            "nbv": g["n"],
            "montant": round(g["montant"], 2),
            "ecarte": round(g["ecarte"], 2) or None,
            "a0": annees[0] if annees else None,
            "a1": annees[-1] if annees else None,
            "ech": len(g["echelons"]),
            "echelons": ",".join(sorted(g["echelons"])),
            "masque": sum(1 << k for k, e in enumerate(ECHELONS) if e in g["echelons"]),
            "nbd": len(g["donateurs"]),
            "principal": principal,
            "part": part,
            "publient_jusqu_a": dernier_financeur or None,
        }

    # L'ordre de tri est celui de la LISTE DE RÉSULTATS et celui des blocs
    # d'identifiants : les deux doivent être le même, sinon le rang d'un
    # résultat ne désigne plus le bon identifiant.
    ordre = sorted(resume, key=lambda b: (resume[b]["nom_norm"], b))

    # ------------------------------------------------------------------ 2 --
    # Rang 2 : tous les bénéficiaires, en colonnes parallèles.
    if os.path.exists(OUT):
        shutil.rmtree(OUT)
    noms = {
        "nb": len(ordre),
        "n": "\n".join(resume[b]["nom"] for b in ordre),
        "d": "\n".join(resume[b]["dep"] or "" for b in ordre),
        "m": [round(resume[b]["montant"]) for b in ordre],
        "e": [resume[b]["ech"] for b in ordre],
        "v": [resume[b]["nbv"] for b in ordre],
        "a": [resume[b]["a0"] or 0 for b in ordre],
        # Amplitude plutôt qu'année de fin : de petits entiers se compressent
        # beaucoup mieux qu'une seconde colonne d'années.
        "b": [(resume[b]["a1"] or 0) - (resume[b]["a0"] or 0) for b in ordre],
        "x": [resume[b]["masque"] for b in ordre],
        # La dépendance : part du principal financeur, en points. 0 vaut
        # « pas mesurable » — une association sans don voté n'en a pas.
        "p": [int(resume[b]["part"] or 0) for b in ordre],
        "echelons": ECHELONS,
    }
    brut, gzt = ecrire_gz(os.path.join(OUT, "noms.json.gz"), noms)

    # Les RNA, à part et de façon creuse. Ils ne servent PAS au navigateur —
    # la fiche porte déjà le sien — mais à `build_angle_mort.py`, qui compare
    # les comptes déposés au Journal officiel à ce que le site reconnaît. Le
    # SIREN, lui, se relit dans l'identifiant ; le RNA d'un bénéficiaire déjà
    # identifié par son SIREN ne se relit nulle part, et l'oublier ferait
    # tomber la reconnaissance de 69 954 RNA à 23.
    rna_i, rna_v = [], []
    for rang, b in enumerate(ordre):
        if resume[b]["rna"]:
            rna_i.append(rang)
            rna_v.append(resume[b]["rna"])
    ecrire_gz(os.path.join(OUT, "rna.json.gz"), {"i": rna_i, "v": rna_v})
    print(f"  noms.json.gz            {len(ordre):>9,} lignes  "
          f"{gzt/1048576:6.2f} Mo gz ({brut/1048576:.1f} Mo bruts)")

    # ------------------------------------------------------------------ 3 --
    # Blocs d'identifiants, par rang alphabétique.
    taille_bloc = -(-len(ordre) // NB_BLOCS)
    for b in range(NB_BLOCS):
        tranche = ordre[b * taille_bloc:(b + 1) * taille_bloc]
        ecrire_gz(os.path.join(OUT, "ids", f"{b:03d}.json.gz"),
                  {"debut": b * taille_bloc, "ids": tranche})
    print(f"  ids/BBB.json.gz         {NB_BLOCS:>9} blocs   "
          f"{taille_bloc} identifiants par bloc")

    # ------------------------------------------------------------------ 4 --
    # Fiches : versements ligne à ligne + résumé, shardés par le bénéficiaire.
    par_shard = collections.defaultdict(list)
    for i in range(n):
        par_shard[shard_of(ids[i])].append(i)

    tailles = []
    for num in range(NB_SHARDS):
        lignes = par_shard.get(num, [])
        # Trié par bénéficiaire puis par année décroissante : chaque fiche
        # occupe une plage contiguë, et le client n'a qu'un début et une
        # longueur à retenir.
        lignes.sort(key=lambda i: (ids[i], -(col["year"][i] or 0),
                                   -(col["amount_eur"][i] or 0)))
        d_donateur, d_programme = Dictionnaire(), Dictionnaire()
        d_source, d_url, d_niveau = Dictionnaire(), Dictionnaire(), Dictionnaire()
        d_gran, d_mesure, d_concours = Dictionnaire(), Dictionnaire(), Dictionnaire()
        bids, debuts = [], []
        precedent = None
        for rang, i in enumerate(lignes):
            if ids[i] != precedent:
                precedent = ids[i]
                bids.append(precedent)
                debuts.append(rang)
        ecartes_i, ecartes_v = [], []
        for rang, i in enumerate(lignes):
            if col["amount_rejected_eur"][i]:
                ecartes_i.append(rang)
                ecartes_v.append(nombre(col["amount_rejected_eur"][i]))
        shard = {
            "shard": num,
            "bid": "\n".join(bids),
            "off": debuts,
            "resume": [[resume[b]["nom"], resume[b]["siren"], resume[b]["rna"],
                        resume[b]["dep"], resume[b]["kind"], resume[b]["nbv"],
                        round(resume[b]["montant"]),
                        round(resume[b]["ecarte"]) if resume[b]["ecarte"] else 0,
                        resume[b]["a0"] or 0, resume[b]["a1"] or 0,
                        resume[b]["ech"], resume[b]["echelons"], resume[b]["nbd"],
                        resume[b]["principal"] or "", resume[b]["part"],
                        resume[b]["publient_jusqu_a"] or 0,
                        resume[b]["famille"], resume[b]["rna_de_insee"],
                        resume[b]["src_contredit"]] for b in bids],
            "y": [col["year"][i] or 0 for i in lignes],
            "m": [nombre(col["amount_eur"][i]) for i in lignes],
            # Creux : 30 255 lignes sur 2,8 millions portent un montant écarté.
            # Une colonne pleine de zéros coûterait plus que la donnée.
            "r": {"i": ecartes_i, "v": ecartes_v},
            "niv": [d_niveau.code(col["donor_level"][i]) for i in lignes],
            "don": [d_donateur.code(col["donor_name_raw"][i]) for i in lignes],
            "prg": [d_programme.code(col["donor_program"][i]) for i in lignes],
            "obj": "\n".join(texte(col["purpose_raw"][i]) for i in lignes),
            "gra": [d_gran.code(col["granularity"][i]) for i in lignes],
            "mes": [d_mesure.code(col["measure"][i]) for i in lignes],
            "con": [d_concours.code(natures[i]) for i in lignes],
            "cas": [CAS.index(cas[i]) for i in lignes],
            "src": [d_source.code(col["source_label"][i]) for i in lignes],
            "url": [d_url.code(col["source_url"][i]) for i in lignes],
            "dico": {
                "niv": d_niveau.valeurs, "don": d_donateur.valeurs,
                "prg": d_programme.valeurs, "gra": d_gran.valeurs,
                "mes": d_mesure.valeurs, "con": d_concours.valeurs,
                "cas": CAS,
                "src": d_source.valeurs, "url": d_url.valeurs,
            },
        }
        _, taille = ecrire_gz(os.path.join(OUT, "fiches", f"{num:03d}.json.gz"), shard)
        tailles.append(taille)
    tri = sorted(tailles)
    print(f"  fiches/NNN.json.gz      {n:>9,} lignes  "
          f"{sum(tailles)/1048576:6.1f} Mo gz en {NB_SHARDS} shards "
          f"(médiane {tri[NB_SHARDS//2]/1024:.0f} Ko, max {max(tailles)/1024:.0f} Ko)")

    # ------------------------------------------------------------------ 5 --
    # Rang 1 : ce qui répond à la première lettre tapée, sur l'accueil.
    #
    # Les associations y sont les plus grosses par montant — pas les plus
    # « pertinentes » : un classement par montant est vérifiable, un
    # classement par popularité serait une opinion. Les communes, elles, y
    # sont TOUTES : personne ne cherche « sa » commune parmi les plus grosses.
    gros = sorted(ordre, key=lambda b: -resume[b]["montant"])[:TAILLE_SUGGEST]
    gros.sort(key=lambda b: (resume[b]["nom_norm"], b))
    communes = charger_referentiel()
    codes = sorted(communes)
    with gzip.open(os.path.join(AGG, "meta.json.gz"), "rt", encoding="utf-8") as f:
        meta = json.load(f)
    suggest = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "associations": {
            "n": "\n".join(resume[b]["nom"] for b in gros),
            "i": "\n".join(gros),
            "d": "\n".join(resume[b]["dep"] or "" for b in gros),
            "m": [round(resume[b]["montant"]) for b in gros],
            "e": [resume[b]["ech"] for b in gros],
            "x": [resume[b]["masque"] for b in gros],
            "p": [int(resume[b]["part"] or 0) for b in gros],
            "total": len(ordre),
        },
        "communes": {
            "n": "\n".join(texte(communes[c]["nom"]) for c in codes),
            "i": "\n".join(codes),
            "d": "\n".join(communes[c].get("dep_code") or "" for c in codes),
            "p": [communes[c].get("population") or 0 for c in codes],
        },
        "echelons": ECHELONS,
        "departements": [[c, v[0]] for c, v in
                         sorted(meta["departements"]["valeurs"].items())],
        "regions": [[c, v] for c, v in sorted(meta["regions"].items())],
    }
    brut, gzt = ecrire_gz(os.path.join(AGG, "suggest.json.gz"), suggest)
    print(f"  suggest.json.gz         {len(gros):>9,} assoc. + "
          f"{len(codes):,} communes  {gzt/1024:.0f} Ko gz")

    # ------------------------------------------------------------------ 6 --
    ech = collections.Counter(resume[b]["ech"] for b in ordre)
    stats = {
        "beneficiaires": len(ordre),
        "par_cle": dict(collections.Counter(b[0] for b in ordre)),
        "par_nb_echelons": {str(k): ech[k] for k in sorted(ech)},
        "multi_echelons_3plus": sum(v for k, v in ech.items() if k >= 3),
        "versements": n,
        "shards": NB_SHARDS,
        "blocs": NB_BLOCS,
    }
    with open(os.path.join(OUT, "index-stats.json"), "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"\n  cumuls >=3 échelons : {stats['multi_echelons_3plus']:,}")
    print(f"  -> data/recherche/ et data/aggregates/suggest.json.gz")


if __name__ == "__main__":
    main()
