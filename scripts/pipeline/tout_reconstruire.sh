#!/usr/bin/env bash
# Reconstruit toute la chaîne, des sources moissonnées au site servi.
# Les moissonnages (fetch_*) ne sont PAS rejoués : ils ont leur propre cache.
set -euo pipefail
cd "$(dirname "$0")/../.."

etape() { printf '\n=== %s ===\n' "$1"; }

etape "normalisation des familles"
python3 scripts/pipeline/normalize_plf_jaune.py | tail -3
python3 scripts/pipeline/normalize_legacy.py    | tail -2
python3 scripts/pipeline/normalize_scdl.py      | tail -3
python3 scripts/pipeline/normalize_ods.py       | tail -3

etape "table canonique"
python3 scripts/pipeline/build_canonical.py | tail -20

# La nature juridique du bénéficiaire vient APRÈS l'assemblage : elle s'appuie
# sur les SIREN présents dans la table finale, et le référentiel ne documente
# que ceux-là (4,8 Mo au lieu des 705 du fichier SIRENE complet).
#
# `refresh_rapport.py` repasse ENSUITE, parce que `build_canonical.py` a écrit
# son rapport avant que le verdict de l'INSEE n'existe : sans lui, le rapport
# annoncerait le total d'avant la règle, et `verify.py` le verrait.
etape "nature juridique des bénéficiaires"
python3 scripts/pipeline/fetch_nature_beneficiaires.py | tail -6
python3 scripts/pipeline/enrich_nature.py   | tail -20
python3 scripts/pipeline/refresh_rapport.py | tail -4

etape "ce que le site sert"
python3 scripts/pipeline/build_carte.py       | tail -2
python3 scripts/pipeline/build_aggregates.py  | tail -3
python3 scripts/pipeline/build_index_navigateur.py | tail -7
python3 scripts/pipeline/build_couverture.py  | tail -7

# Le dénominateur et l'angle mort disent ce que le site NE VOIT PAS. Ils ne
# touchent pas à la table canonique et ne sont sommés avec rien ; le second lit
# l'index de recherche, il vient donc après lui. `build_methode.py` les lit tous
# les deux et passe en dernier des constructions.
#
# `build_index_navigateur.py` vient APRÈS `build_aggregates.py` : il lit
# `meta.json.gz` pour nommer les départements et les régions du rang 1 de
# l'autocomplétion.
python3 scripts/pipeline/build_denominateur.py | tail -6
python3 scripts/pipeline/build_fiches_communes.py | tail -4
python3 scripts/pipeline/build_angle_mort.py   | tail -5
python3 scripts/pipeline/build_methode.py     | tail -2

# Les contrôles viennent EN DERNIER : plusieurs d'entre eux comparent l'index
# de recherche à la table canonique, et échoueraient tant qu'il n'est pas
# reconstruit.
etape "contrôles"
python3 scripts/pipeline/verify.py | tail -5
