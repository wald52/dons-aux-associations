# Banc de mesure de performance

Point de référence chiffré pour juger la refonte. Sans lui, on ne saurait pas
si une optimisation a servi.

## Lancer une mesure

```bash
export NODE_PATH=/opt/node22/lib/node_modules   # playwright/http-server globaux
node scripts/bench/measure.js --label v0 --timeout 420
```

| Option | Défaut | Rôle |
|---|---|---|
| `--label` | `run` | nom du relevé → `bench/<label>.json` |
| `--timeout` | `300` | abandon (secondes) si les données ne sont jamais prêtes |
| `--port` | `8099` | port du serveur statique local |
| `--page` | `index.html` | page à mesurer — `recherche.html` a son propre coût d'entrée |
| `--headful` | — | ouvrir un navigateur visible (débogage) |

Le banc n'a **aucune connaissance de l'architecture interne** : il observe le
réseau et attend un marqueur « données prêtes ». Les relevés d'avant et d'après
la refonte sont donc directement comparables. Les marqueurs acceptés sont, dans
l'ordre (`READY_PROBES` dans le script) :

1. `window.ALL_SUBVENTIONS.length > 0` — architecture v0
2. `window.__DATA_READY === true` — **à poser dans l'architecture cible**
3. le compteur « Montant total » cesse d'afficher `--`

## Ce qui est mesuré

- **Octets transférés** — via CDP `Network.loadingFinished`, donc l'octet réel.
- **Requêtes** — nombre et échecs.
- **Premier affichage** (FCP) — quand le visiteur voit quelque chose.
- **Données exploitables** — quand le site sert enfin à quelque chose.
- **Mémoire JS** — tas utilisé et plafond du moteur.

## Relevé de référence — `v0` (18/08/2026)

État : `origin/main` @ `0b14348`, avant toute refonte.

| Mesure | Valeur |
|---|---|
| Octets transférés (brut) | **835,04 Mo** |
| Octets transférés (gzip, = GitHub Pages) | **~73,6 Mo** |
| Requêtes | 171 (1 en échec) |
| Premier affichage | **12,96 s** |
| Données exploitables | **57,75 s** |
| Mémoire JS utilisée | **1 965 Mo** / plafond 3 586 Mo |
| Enregistrements chargés | 1 595 805 |
| Balises `<script>` | 170 |

### Précautions de lecture — important

- **Mesure en local**, latence réseau nulle, 4 cœurs, 16 Go de RAM.
  Sur une vraie connexion et une vraie machine, les temps sont **nécessairement pires**.
- **`http-server` ne compresse pas à la volée**, contrairement à GitHub Pages.
  Les 835 Mo sont l'octet brut ; en ligne, le transfert réel est de ~73,6 Mo
  (ratio ×11,3). Il ne faut donc **pas** annoncer « 835 Mo téléchargés ».
- Le vrai coût n'est pas le transfert mais le **parsing** : le navigateur doit
  décompresser puis parser 835 Mo de JavaScript. C'est ce qui explique les
  57,75 s et les 1 965 Mo de tas, pas les octets sur le fil.
- **1 965 Mo sur un plafond de 3 586 Mo, soit 55 %.** Sur mobile le plafond est
  bien plus bas — l'onglet est tué avant la fin. C'est la mesure la plus grave
  du relevé : elle explique pourquoi le site est inutilisable sur téléphone.
- La requête en échec est Chart.js depuis `cdn.jsdelivr.net`, non joignable
  depuis le conteneur de mesure. Sans effet sur les chiffres de données.
- Le comptage par `grep` du diagnostic initial (1 578 180) sous-estimait de
  1,1 % : **1 595 805** relevé par l'application fait foi.

### Reproductibilité

Deux relevés successifs sur le même état donnent :

| Mesure | Relevé 1 | Relevé 2 | Écart |
|---|---|---|---|
| Octets transférés | 835,04 Mo | 835,04 Mo | 0 % |
| Enregistrements | 1 595 805 | 1 595 805 | 0 % |
| Premier affichage | 12,96 s | 12,85 s | 0,8 % |
| Données exploitables | 57,75 s | 52,99 s | **8,2 %** |

Les octets et les volumes sont déterministes ; les **temps varient de l'ordre
de 10 %** parce qu'ils sont dominés par le parsing, donc par la charge CPU du
moment. Ne pas conclure d'un gain inférieur à 10 % sur un temps : relancer
deux ou trois fois et comparer les ordres de grandeur.

## Relevé après phase 2 — `phase2` (19/08/2026)

| Mesure | v0 | phase 2 | Gain |
|---|---|---|---|
| Octets transférés | ~73,6 Mo | **0,13 Mo** | ×566 |
| Requêtes | 171 | **7** | ×24 |
| Premier affichage | 12,96 s | **0,11 s** | ×118 |
| Données exploitables | 57,75 s | **0,63 s** | ×92 |
| Mémoire JS | 1 965 Mo | **10 Mo** | ×196 |
| Balises `<script>` | 170 | **1** | — |

Les quatre cibles ci-dessous sont atteintes. La mémoire passe de 55 % du
plafond du moteur à 0,3 % : le site cesse d'être hors de portée d'un téléphone.

## Page recherche — phase 13 (23/08/2026)

**DuckDB-WASM est retiré.** Le tableau de la phase 3, ci-dessous, décrit
l'architecture précédente et n'est gardé que comme point de comparaison.

| Mesure | phase 3 (DuckDB) | phase 13 | facteur |
|---|---|---|---|
| Octets transférés | ~48 Mo brut (~25 Mo en ligne) | **6,06 Mo** | ÷4 en ligne |
| Requêtes | 8 | **11** | — |
| Premier affichage | 0,12 s | **0,09 s** | — |
| Champ de saisie utilisable | ~4,5 s | **~0,3 s** | ÷15 |
| Index complet chargé | ~4,5 s | **2,2 s** | ÷2 |
| Recherche par nom | 0,4–1,3 s | **14–51 ms** | ÷30 |
| Fiche d'une association | 0,1–1,4 s | **16–20 ms** | ÷50 |
| Réseau pour une fiche | ~0,9 Mo (shard Parquet) | **~0,12 Mo** | ÷7 |
| Mémoire JS, après GC | non mesurée | **70 Mo** | — |

Trois choses ne se lisent pas dans ce tableau et comptent autant :

- **Le champ de saisie existe tout de suite.** Ce n'est plus « la page apparaît
  au bout de 4,5 s », c'est « le champ accepte la frappe et répond sur les
  25 000 plus gros bénéficiaires, pendant que le reste arrive ». Mesuré :
  première suggestion **502 ms** après que le pointeur a touché le champ,
  frappe de trois lettres comprise.
- **Un lien partagé vers une association ne charge pas l'index.** Il ne
  télécharge que son shard de fiche, ~120 Ko, et rien d'autre — vérifié dans
  l'onglet réseau : quatre requêtes, aucun `.wasm`, aucun `noms.json.gz`.
- **La mémoire brute affichée par le banc (163 Mo) est trompeuse** : elle est
  relevée juste après `JSON.parse`, avant tout ramassage. Après deux passes de
  GC forcé par CDP, le tas retenu est de **70 Mo**, et il ne bouge plus après
  une recherche.

### Le coût de l'accueil n'a pas bougé

C'était la condition : la refonte de la recherche ne devait rien coûter à la
carte. Vérifié — `bench/phase13-accueil.json` :

| Mesure | phase 6a | phase 13 |
|---|---|---|
| Octets transférés | 0,14 Mo | **0,22 Mo** |
| Premier affichage | 0,07 s | **0,06 s** |
| Données exploitables | 0,59 s | **0,59 s** |
| Mémoire JS | 3 Mo | **3 Mo** |

Les 0,08 Mo de plus sont les modules JavaScript ajoutés (lexique,
autocomplétion, index client). **L'index de suggestion (0,85 Mo) n'y est
pas** : une première version le préchargeait à l'inactivité de la page, et
l'accueil passait à **1,05 Mo** — mesuré, puis retiré. Il se charge maintenant
quand le pointeur entre dans le champ, s'y pose ou lui donne le focus : qui
vient seulement regarder la carte ne le paie jamais, et qui va s'en servir l'a
avant sa première lettre.

## Page recherche (phase 3, architecture retirée)

Coûts mesurés en local, serveur sans gzip (en ligne, le wasm se comprime ~×3) :

| Action | Temps | Réseau |
|---|---|---|
| Démarrage du moteur + index + accueil | ~4,5 s | ~48 Mo brut (~25 Mo en ligne) |
| Recherche par nom | 0,4-1,3 s | **0** (index en mémoire) |
| Fiche d'une association | 0,1-1,4 s | ~0,9 Mo (un shard, puis en cache) |

Ce coût d'entrée ne concernait QUE `recherche.html` ; la carte (`index.html`)
restait à 0,13 Mo / 0,05 s. Mesure de contrôle dans `bench/phase3.json`.

## Après phase 4 (`bench/phase4.json`)

La table a grossi de 19 % (2 012 328 lignes) sans que le premier écran bouge :
0,13 Mo transférés, 0,07 s au premier affichage, 10 Mo de mémoire. C'est la
propriété recherchée — le site sert un index, sa taille ne dépend pas du
volume de données derrière.

## Après phase 6a (`bench/phase6a.json`)

La table a encore grossi de 37,6 % (2 769 440 lignes, 559 sources) et le
premier écran ne bouge toujours pas :

| Mesure | v0 | phase 4 | phase 6a |
|---|---|---|---|
| Octets transférés | 73,6 Mo | 0,13 Mo | **0,14 Mo** |
| Premier affichage | 12,96 s | 0,07 s | **0,07 s** |
| Données exploitables | 57,75 s | 0,13 s | **0,59 s** |
| Mémoire JS | 1 965 Mo | 10 Mo | **3 Mo** |
| Balises `<script>` | 170 | 1 | **1** |

Le premier affichage n'a pas bougé d'un centième de seconde alors que la table
a presque doublé depuis la phase 2 : le coût du site ne suit pas le volume des
données, parce qu'il sert un index précalculé et non une base.

**Une mesure est en recul** : « données exploitables » passe de 0,13 s à
0,59 s. Les agrégats n'ont grossi que de 0,01 Mo, mais les quatre `.json.gz`
mettent 72 ms chacun à revenir contre 18-23 ms en phase 4 — c'est le temps
réseau qui a changé, pas leur taille, et la mesure a été prise sur une machine
qui venait de reconstruire toute la chaîne. À reprendre au calme avant d'en
conclure quoi que ce soit ; on reste à un quart de la cible (< 2 s).

**Rejouer le banc** : `node scripts/bench/measure.js --label <phase>`. Si
Playwright réclame une révision de Chromium absente de la machine, lui
désigner celui qui est là :
`CHROMIUM_PATH=/opt/pw-browsers/chromium-1194/chrome-linux/chrome`.

## Cibles après refonte

| Mesure | v0 | Cible phase 2 |
|---|---|---|
| Octets transférés (gzip) | 73,6 Mo | **< 1 Mo** au premier écran |
| Premier affichage | 12,96 s | **< 1 s** |
| Données exploitables | 57,75 s | **< 2 s** |
| Mémoire JS | 1 965 Mo | **< 150 Mo** |

Poser `window.__DATA_READY = true` dans la nouvelle architecture dès que la
carte et les compteurs sont exploitables, pour garder la comparabilité.
