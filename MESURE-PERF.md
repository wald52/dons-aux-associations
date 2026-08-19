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

## Page recherche (phase 3)

Coûts mesurés en local, serveur sans gzip (en ligne, le wasm se comprime ~×3) :

| Action | Temps | Réseau |
|---|---|---|
| Démarrage du moteur + index + accueil | ~4,5 s | ~48 Mo brut (~25 Mo en ligne) |
| Recherche par nom | 0,4-1,3 s | **0** (index en mémoire) |
| Fiche d'une association | 0,1-1,4 s | ~0,9 Mo (un shard, puis en cache) |

Ce coût d'entrée ne concerne QUE `recherche.html` ; la carte (`index.html`)
reste à 0,13 Mo / 0,05 s. Mesure de contrôle dans `bench/phase3.json`.

## Cibles après refonte

| Mesure | v0 | Cible phase 2 |
|---|---|---|
| Octets transférés (gzip) | 73,6 Mo | **< 1 Mo** au premier écran |
| Premier affichage | 12,96 s | **< 1 s** |
| Données exploitables | 57,75 s | **< 2 s** |
| Mémoire JS | 1 965 Mo | **< 150 Mo** |

Poser `window.__DATA_READY = true` dans la nouvelle architecture dès que la
carte et les compteurs sont exploitables, pour garder la comparabilité.
