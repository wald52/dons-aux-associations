# DuckDB-WASM — moteur SQL embarqué

`duckdb.mjs` est un bundle esbuild autosuffisant (DuckDB-WASM + Apache Arrow) :
le module npm d'origine importe `apache-arrow` par son nom nu, ce qu'un
navigateur ne sait pas résoudre sans import map. Le worker et le wasm sont
copiés tels quels du paquet `@duckdb/duckdb-wasm` (dist/, variante `eh`). Versionnés dans le
dépôt parce que la CSP du site interdit tout CDN, et qu'un site d'intérêt
public ne doit pas dépendre de la disponibilité d'un tiers.

Chargés PARESSEUSEMENT par `assets/js/recherche.js`, uniquement à l'ouverture
de la page recherche : le premier écran du site n'en paie jamais le poids.

Pour mettre à jour : `npm i @duckdb/duckdb-wasm`, recopier les trois fichiers,
noter la version ici. Version en place : voir `version.txt`.
