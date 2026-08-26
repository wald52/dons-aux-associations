"""Pose la nature juridique INSEE sur chaque ligne de la table canonique.

Phase 15. Le site devinait « association » chaque fois qu'une source ne
déclarait rien. Mesuré : **37,68 Md€ des 148,40 Md€ votés allaient à des
bénéficiaires qui n'en sont pas** — SNCF Voyageurs, l'AFP, le Pass Culture,
l'ASP, le CNC, France Travail, le musée du Louvre.

Ce script ne devine plus : il apparie le SIREN du bénéficiaire au référentiel
`data/referentiel/nature-beneficiaires.parquet` (SIRENE pour la forme juridique,
Journal officiel pour le type déclaré) et pose quatre colonnes.

**Il ne RETOUCHE rien.** `beneficiary_kind` et `beneficiary_kind_provenance`
gardent ce que la source a dit ou ce que le pipeline avait deviné ; le verdict
de l'INSEE voyage à côté, dans ses propres colonnes. On peut donc toujours voir
qui s'était trompé, et le rapport de qualité continue de mesurer la devinette.

Trois valeurs possibles pour `beneficiary_is_associatif`, et la troisième est
la plus importante :

    true   l'INSEE déclare une association ou une fondation ;
    false  l'INSEE déclare autre chose — la ligne sort des totaux ;
    NULL   pas de SIREN, ou SIREN absent de SIRENE. **On ne sait pas**, et ne
           pas savoir n'est pas un « non » : la ligne reste comptée et porte la
           famille « nature non vérifiée ». Cela vaut 23,1 % du montant.
           Exclure ici effacerait des milliers de petites associations
           communales qui n'ont jamais eu de SIRET publié.

Idempotent : rejoué, il réécrit les mêmes valeurs. Il peut donc tourner après
`build_canonical.py` sans précaution particulière.

Usage :
    python3 scripts/pipeline/enrich_nature.py
"""

import collections
import glob
import io
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import common as C

ROOT = C.ROOT
REFERENTIEL = os.path.join(ROOT, "data", "referentiel", "nature-beneficiaires.parquet")
PARTITIONS = os.path.join(ROOT, "data", "canonical", "subventions", "year=*", "*.parquet")
RAPPORT = os.path.join(ROOT, "data", "canonical", "nature-juridique.json")

# Les colonnes du fichier de partition : le schéma canonique moins `year`, qui
# est porté par le nom du répertoire (partitionnement Hive) et non par le
# fichier lui-même.
COLONNES_FICHIER = [c for c in C.CANONICAL_FIELDS if c != "year"]


def charger_referentiel():
    import pyarrow.parquet as pq
    if not os.path.exists(REFERENTIEL):
        raise SystemExit(
            f"{REFERENTIEL} manquant — lancer d'abord "
            "python3 scripts/pipeline/fetch_nature_beneficiaires.py")
    t = pq.read_table(REFERENTIEL)
    siren = t.column("siren").to_pylist()
    cj = t.column("categorie_juridique").to_pylist()
    jo = t.column("type_jo").to_pylist()
    return {s: (c, j) for s, c, j in zip(siren, cj, jo)}


def main():
    import pyarrow as pa
    import pyarrow.parquet as pq

    ref = charger_referentiel()
    print(f"référentiel : {len(ref):,} SIREN")

    fichiers = sorted(glob.glob(PARTITIONS))
    if not fichiers:
        raise SystemExit(f"aucune partition sous {PARTITIONS}")

    familles = collections.Counter()
    montants = collections.defaultdict(float)
    verdict = collections.Counter()
    m_verdict = collections.defaultdict(float)
    total_lignes = 0
    t0 = time.time()

    for chemin in fichiers:
        table = pq.read_table(chemin)
        sirens = table.column("beneficiary_siren").to_pylist()
        montant = table.column("amount_eur").to_pylist()
        gran = table.column("granularity").to_pylist()
        mesure = table.column("measure").to_pylist()
        kind = table.column("beneficiary_kind").to_pylist()
        prov = table.column("beneficiary_kind_provenance").to_pylist()
        flags = table.column("quality_flags").to_pylist()
        objet = table.column("purpose_norm").to_pylist()

        cj_col, asso_col, fam_col, jo_col = [], [], [], []
        for i, s in enumerate(sirens):
            cj, type_jo = ref.get(s, (None, None)) if s else (None, None)
            asso = C.est_associatif(cj)
            fam = C.famille_du_beneficiaire(cj, type_jo)
            cj_col.append(cj)
            asso_col.append(asso)
            fam_col.append(fam)
            jo_col.append(type_jo)

            total_lignes += 1
            cle = {True: "associatif", False: "NON associatif"}.get(asso, "non vérifié")
            verdict[cle] += 1
            # On ne compte le montant que là où il entre dans les totaux : c'est
            # la seule mesure qui dit quelque chose sur ce que le site affiche.
            concours = C.nature_du_concours(objet[i] or "",
                                            tuple(flags[i]) if flags[i] else ())
            if C.compte_dans_les_totaux(gran[i], mesure[i], kind[i], prov[i],
                                        concours[0]):
                m_verdict[cle] += montant[i] or 0.0
                if fam:
                    familles[fam] += 1
                    montants[fam] += montant[i] or 0.0

        colonnes = {}
        for nom in COLONNES_FICHIER:
            if nom == "beneficiary_legal_category":
                colonnes[nom] = pa.array(cj_col, pa.int32())
            elif nom == "beneficiary_is_associatif":
                colonnes[nom] = pa.array(asso_col, pa.bool_())
            elif nom == "beneficiary_family":
                colonnes[nom] = pa.array(fam_col, pa.string())
            elif nom == "beneficiary_type_jo":
                colonnes[nom] = pa.array(jo_col, pa.string())
            else:
                colonnes[nom] = table.column(nom)
        sortie = pa.table(colonnes)
        # Écriture atomique : un fichier temporaire puis un renommage, pour
        # qu'une interruption ne laisse jamais une partition tronquée.
        tmp = chemin + ".tmp"
        pq.write_table(sortie, tmp, compression="zstd")
        os.replace(tmp, chemin)

    total_vote = sum(m_verdict.values())
    print(f"\n{total_lignes:,} lignes enrichies en {time.time() - t0:.0f} s")
    print(f"\n{'verdict de l INSEE':22s} {'lignes':>10} {'montant voté':>15}")
    for cle in ("associatif", "NON associatif", "non vérifié"):
        print(f"{cle:22s} {verdict[cle]:10,} {m_verdict[cle] / 1e9:12.2f} Md€")
    # `total_vote` est la somme des trois verdicts, donc le total AVANT que la
    # règle ne s'applique — c'est lui qui doit retrouver les 148,40 Md€
    # historiques, et c'est ce qui prouve que l'enrichissement n'a rien perdu.
    apres_regle = total_vote - m_verdict["NON associatif"]
    print(f"\n>>> total voté AVANT la règle (contrôle) : {total_vote / 1e9:.2f} Md€")
    print(f">>> sorti des totaux par l'INSEE         : "
          f"{m_verdict['NON associatif'] / 1e9:.2f} Md€")
    print(f">>> total voté APRÈS la règle            : {apres_regle / 1e9:.2f} Md€")

    print(f"\n{'famille affichée':46s} {'lignes':>9} {'montant':>13}")
    for fam, n in sorted(familles.items(), key=lambda kv: -montants[kv[0]]):
        print(f"{fam:46s} {n:9,} {montants[fam] / 1e9:10.2f} Md€")

    with open(RAPPORT, "w", encoding="utf-8") as f:
        json.dump({
            "genere_le": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "referentiel": os.path.relpath(REFERENTIEL, ROOT),
            "frontiere": ("associations INSEE 92xx + fondations 9300 — décision "
                          "de l'utilisateur du 26/08/2026"),
            "lignes": total_lignes,
            "verdict": {k: verdict[k] for k in ("associatif", "NON associatif",
                                                "non vérifié")},
            "montant_vote_par_verdict": {k: round(m_verdict[k], 2)
                                         for k in ("associatif", "NON associatif",
                                                   "non vérifié")},
            "total_vote_avant_regle": round(total_vote, 2),
            "total_vote_apres_regle": round(apres_regle, 2),
            "familles": {f: {"lignes": familles[f], "montant": round(montants[f], 2)}
                         for f in sorted(familles, key=lambda x: -montants[x])},
        }, f, ensure_ascii=False, indent=1)
    print(f"\n{RAPPORT} écrit.")


if __name__ == "__main__":
    main()
