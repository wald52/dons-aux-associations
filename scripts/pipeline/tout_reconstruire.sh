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

etape "ce que le site sert"
python3 scripts/pipeline/build_carte.py       | tail -2
python3 scripts/pipeline/build_aggregates.py  | tail -3
python3 scripts/pipeline/build_search_index.py | tail -4
python3 scripts/pipeline/build_couverture.py  | tail -7
python3 scripts/pipeline/build_methode.py     | tail -2

# Les contrôles viennent EN DERNIER : plusieurs d'entre eux comparent l'index
# de recherche à la table canonique, et échoueraient tant qu'il n'est pas
# reconstruit.
etape "contrôles"
python3 scripts/pipeline/verify.py | tail -5
