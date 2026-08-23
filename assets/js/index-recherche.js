/* ============================================================================
 * L'index de recherche, côté navigateur — sans moteur SQL.
 * ----------------------------------------------------------------------------
 * Remplace DuckDB-WASM. L'ancienne page téléchargeait 34,2 Mo de moteur puis
 * 17,7 Mo d'index AVANT d'afficher un champ de saisie : 4,5 s en local, sans
 * latence, et des dizaines de secondes sur un téléphone. Un moteur SQL
 * généraliste était un prix très élevé pour deux questions : « quelles
 * associations portent ce nom ? » et « qui finance celle-ci ? ».
 *
 * Trois niveaux, du plus léger au plus complet :
 *
 *   RANG 1  data/aggregates/suggest.json.gz          ~0,8 Mo
 *           Les 25 000 plus gros bénéficiaires, les 34 936 communes, les
 *           départements et les régions. Chargé en tâche de fond dès
 *           l'accueil : la première lettre tapée répond sans rien attendre.
 *
 *   RANG 2  data/recherche/noms.json.gz              ~4,8 Mo
 *           Les 427 451 bénéficiaires. Arrive derrière et COMPLÈTE les
 *           résultats en place, sans recharger la page.
 *
 *   FICHE   data/recherche/fiches/NNN.json.gz        ~0,12 Mo
 *           Un shard sur 512, déduit du seul identifiant. Une fiche est donc
 *           autosuffisante : un lien partagé s'ouvre en une requête, sans
 *           jamais charger l'index des noms.
 *
 * La recherche elle-même est un `indexOf` sur une grande chaîne de noms pliés,
 * construite une fois. Sur 427 451 noms, elle rend la main en quelques
 * millisecondes — un ordre de grandeur plus vite que le moteur qu'elle
 * remplace, pour un dixième du poids.
 * ========================================================================= */

"use strict";

import { chargerGz, plier } from "./commun.js";

var NB_SHARDS = 512;
var NB_BLOCS = 512;

/** Numéro de shard d'un bénéficiaire — FNV-1a 32 bits, modulo 512.
 *
 *  JUMEAU EXACT de `shard_of` dans `scripts/pipeline/build_index_navigateur.py`.
 *  Toute modification ici en exige une là-bas, et réciproquement ; `verify.py`
 *  le vérifie à chaque assemblage.
 *
 *  L'ancien hachage (somme des octets modulo 64) était mal réparti : la somme
 *  des codes d'un identifiant comme `S853318459` tient dans une bande d'environ
 *  80 valeurs. Résultat mesuré : des shards de 233 Ko face à des shards de
 *  1,66 Mo. Modulo 512, il se serait effondré sur un dixième des fichiers. */
export function shardDe(bid) {
  var h = 0x811C9DC5;
  for (var i = 0; i < bid.length; i++) {
    h ^= bid.charCodeAt(i) & 0xFF;
    // Multiplication 32 bits sans perte de précision : `Math.imul`, pas `*`,
    // qui passerait par un double au-delà de 2^53.
    h = Math.imul(h, 0x01000193) >>> 0;
  }
  return h % NB_SHARDS;
}

// --- rang 1 -----------------------------------------------------------------

var rang1 = null;
var promesseRang1 = null;

function decouper(bloc) {
  return {
    noms: bloc.n ? bloc.n.split("\n") : [],
    ids: bloc.i ? bloc.i.split("\n") : [],
    deps: bloc.d ? bloc.d.split("\n") : [],
    m: bloc.m || [], e: bloc.e || [], p: bloc.p || [], x: bloc.x || []
  };
}

/** L'index sert un masque de sept bits plutôt que sept libellés répétés
 *  427 451 fois. On le redéploie ici, une fois par résultat affiché. */
export function echelonsDuMasque(masque, noms) {
  var out = [];
  (noms || ECHELONS).forEach(function (e, k) { if (masque & (1 << k)) out.push(e); });
  return out;
}

var ECHELONS = ["etat", "operateur", "region", "departement", "epci", "commune", "inconnu"];

export function chargerRang1() {
  if (!promesseRang1) {
    promesseRang1 = chargerGz("data/aggregates/suggest.json.gz").then(function (d) {
      var a = decouper(d.associations);
      var c = decouper(d.communes);
      a.plies = a.noms.map(plier);
      c.plies = c.noms.map(plier);
      rang1 = {
        associations: a, communes: c,
        departements: d.departements || [], regions: d.regions || [],
        echelons: d.echelons || ECHELONS,
        total: (d.associations && d.associations.total) || 0
      };
      return rang1;
    });
  }
  return promesseRang1;
}

/** Précharge sans bloquer : l'accueil peint sa carte en 0,07 s, l'index de
 *  suggestion arrive pendant que le lecteur la regarde. */
export function prechargerRang1() {
  var lancer = function () { chargerRang1().catch(function () { /* au focus */ }); };
  if (typeof requestIdleCallback === "function") requestIdleCallback(lancer, { timeout: 3000 });
  else setTimeout(lancer, 1200);
}

// --- rang 2 -----------------------------------------------------------------

var rang2 = null;
var promesseRang2 = null;

export function rang2Pret() { return rang2 !== null; }

export function chargerRang2(surProgression) {
  if (!promesseRang2) {
    promesseRang2 = chargerGz("data/recherche/noms.json.gz", surProgression)
      .then(function (d) {
        var noms = d.n.split("\n");
        // Une seule grande chaîne, bornée par « \n », plutôt qu'un tableau de
        // 427 451 chaînes pliées : `indexOf` y court en une passe native, et
        // la position se retraduit en rang par un compte de sauts de ligne
        // précalculé.
        var plies = noms.map(plier);
        rang2 = {
          nb: d.nb, noms: noms, plies: plies,
          gros: "\n" + plies.join("\n") + "\n",
          deps: d.d.split("\n"), m: d.m, e: d.e, v: d.v, a: d.a, b: d.b,
          x: d.x, p: d.p, echelons: d.echelons || ECHELONS
        };
        // Table des rangs par position dans la grande chaîne : construite une
        // fois, elle évite de recompter les sauts de ligne à chaque résultat.
        var debuts = new Int32Array(d.nb);
        var pos = 1;
        for (var i = 0; i < d.nb; i++) { debuts[i] = pos; pos += plies[i].length + 1; }
        rang2.debuts = debuts;
        return rang2;
      });
  }
  return promesseRang2;
}

// --- recherche --------------------------------------------------------------

function fiche2(i) {
  return {
    rang: i, nom: rang2.noms[i], dep: rang2.deps[i] || null,
    montant: rang2.m[i], ech: rang2.e[i], nbv: rang2.v[i],
    a0: rang2.a[i] || null, a1: rang2.a[i] ? rang2.a[i] + rang2.b[i] : null,
    echelons: echelonsDuMasque(rang2.x[i], rang2.echelons),
    part: rang2.p[i] || null
  };
}

function fiche1(i) {
  var a = rang1.associations;
  return {
    rang: -1, bid: a.ids[i], nom: a.noms[i], dep: a.deps[i] || null,
    montant: a.m[i], ech: a.e[i], nbv: null, a0: null, a1: null,
    echelons: echelonsDuMasque(a.x[i], rang1.echelons),
    part: a.p[i] || null
  };
}

/** Cherche une association. `q` est déjà plié.
 *
 *  Le classement met devant ce qui COMMENCE par la requête, puis ce qui la
 *  contient — à l'intérieur de chaque groupe, par montant. L'ancien classement
 *  par montant seul mettait « SNCF VOYAGEURS SA TER CENTRE » devant
 *  « SNCF RESEAU » pour la requête « sncf reseau ». */
export function chercherAssociations(q, filtres, limite) {
  filtres = filtres || {};
  limite = limite || 50;
  var source = rang2 ? "complet" : (rang1 ? "partiel" : "vide");
  if (source === "vide") return { source: source, total: 0, resultats: [] };

  var trouves = [];
  var garde = function (f) {
    if (filtres.dep && f.dep !== filtres.dep) return;
    if (filtres.cumul && f.ech < filtres.cumul) return;
    // Le seuil de 10 000 € du filtre de dépendance est dans le rendu, pas
    // caché ici : `montant` porte déjà les dons votés, et une part n'est
    // servie que lorsqu'elle est mesurable.
    if (filtres.dependance && (!f.part || f.part < filtres.dependance ||
                               f.montant < 10000)) return;
    trouves.push(f);
  };

  if (rang2) {
    var i = q ? rang2.gros.indexOf(q) : -1;
    if (q) {
      // On avance de trouvaille en trouvaille dans la grande chaîne, et l'on
      // retrouve le rang par recherche dichotomique dans la table des débuts.
      while (i >= 0) {
        var r = rangDe(i);
        if (r >= 0) garde(fiche2(r));
        i = rang2.gros.indexOf(q, i + 1);
      }
    } else {
      for (var k = 0; k < rang2.nb; k++) garde(fiche2(k));
    }
  } else {
    var a = rang1.associations;
    for (var j = 0; j < a.plies.length; j++) {
      if (!q || a.plies[j].indexOf(q) >= 0) garde(fiche1(j));
    }
  }

  // La dépendance n'a de sens que sur un financement mesurable ; ce seuil est
  // dit à l'écran, pas seulement ici.
  if (q) {
    // Le rang de préfixe est calculé UNE fois par résultat, pas à chaque
    // comparaison : un tri en appelle O(n log n), et sur une requête large
    // (« amicale » en trouve des milliers) cela se voit.
    trouves.forEach(function (f) { f._prefixe = plier(f.nom).indexOf(q) === 0 ? 0 : 1; });
    trouves.sort(function (x, y) {
      return x._prefixe !== y._prefixe ? x._prefixe - y._prefixe : y.montant - x.montant;
    });
  } else {
    trouves.sort(function (x, y) { return y.montant - x.montant; });
  }
  return { source: source, total: trouves.length, resultats: trouves.slice(0, limite) };
}

function rangDe(pos) {
  var d = rang2.debuts, lo = 0, hi = d.length - 1, res = -1;
  while (lo <= hi) {
    var mi = (lo + hi) >> 1;
    if (d[mi] <= pos) { res = mi; lo = mi + 1; } else { hi = mi - 1; }
  }
  // Une trouvaille qui déborde sur la ligne suivante n'en est pas une.
  if (res < 0) return -1;
  if (pos + 1 > d[res] + rang2.plies[res].length) return -1;
  return res;
}

/** Identifiant d'un résultat du rang 2, par son rang alphabétique. Les
 *  identifiants sont dans des blocs à part : les embarquer dans l'index des
 *  noms coûterait 2,7 Mo à toute recherche, pour un besoin qui ne survient
 *  qu'au moment d'ouvrir une fiche. */
var blocs = {};
export async function identifiantDuRang(rang) {
  var taille = Math.ceil(rang2.nb / NB_BLOCS);
  var num = Math.floor(rang / taille);
  var nom = ("00" + num).slice(-3);
  if (!blocs[nom]) blocs[nom] = chargerGz("data/recherche/ids/" + nom + ".json.gz");
  var bloc = await blocs[nom];
  return bloc.ids[rang - bloc.debut];
}

// --- fiches -----------------------------------------------------------------

var shards = {};
var CLES_RESUME = ["nom", "siren", "rna", "dep", "kind", "nbv", "montant",
  "ecarte", "a0", "a1", "ech", "echelons", "nbd", "principal", "part",
  "publient_jusqu_a"];

/** Tout ce qu'il faut pour afficher une association : son résumé ET ses
 *  versements ligne à ligne, en une requête d'environ 120 Ko. */
export async function chargerFiche(bid) {
  var num = shardDe(bid);
  var nom = ("00" + num).slice(-3);
  if (!shards[nom]) {
    shards[nom] = chargerGz("data/recherche/fiches/" + nom + ".json.gz");
  }
  var shard = await shards[nom];
  var bids = shard.bid ? shard.bid.split("\n") : [];
  var i = bids.indexOf(bid);
  if (i < 0) return null;

  var resume = {};
  CLES_RESUME.forEach(function (cle, k) { resume[cle] = shard.resume[i][k]; });
  resume.benef_id = bid;

  var debut = shard.off[i];
  var fin = (i + 1 < shard.off.length) ? shard.off[i + 1] : shard.y.length;
  var objets = shard.obj.split("\n");
  var ecartes = {};
  (shard.r.i || []).forEach(function (rang, k) { ecartes[rang] = shard.r.v[k]; });

  var d = shard.dico;
  var versements = [];
  for (var j = debut; j < fin; j++) {
    versements.push({
      annee: shard.y[j] || null,
      montant: shard.m[j],
      montant_ecarte: ecartes[j] != null ? ecartes[j] : null,
      niveau: d.niv[shard.niv[j]] || "inconnu",
      donateur: d.don[shard.don[j]] || "",
      programme: d.prg[shard.prg[j]] || "",
      objet: objets[j] || "",
      granularite: d.gra[shard.gra[j]] || "",
      mesure: d.mes[shard.mes[j]] || "",
      concours: d.con[shard.con[j]] || "",
      source: d.src[shard.src[j]] || "",
      url: d.url[shard.url[j]] || ""
    });
  }
  return { resume: resume, versements: versements };
}

// --- communes et territoires (rang 1 seulement) -----------------------------

export function chercherTerritoires(q, limite) {
  if (!rang1 || !q) return [];
  var out = [];
  rang1.departements.forEach(function (d) {
    if (plier(d[1]).indexOf(q) === 0 || d[0] === q) {
      out.push({ genre: "departement", code: d[0], nom: d[1] });
    }
  });
  rang1.regions.forEach(function (r) {
    if (plier(r[1]).indexOf(q) === 0) out.push({ genre: "region", code: r[0], nom: r[1] });
  });
  var c = rang1.communes;
  for (var i = 0; i < c.plies.length && out.length < (limite || 8) + 4; i++) {
    if (c.plies[i].indexOf(q) === 0) {
      out.push({ genre: "commune", code: c.ids[i], nom: c.noms[i],
                 dep: c.deps[i], population: c.p[i] });
    }
  }
  // Une commune peuplée avant un hameau homonyme : à requête égale, c'est
  // celle que le lecteur cherche neuf fois sur dix.
  out.sort(function (a, b) {
    if (a.genre !== b.genre) return a.genre === "commune" ? 1 : -1;
    return (b.population || 0) - (a.population || 0);
  });
  return out.slice(0, limite || 8);
}

export function communes() { return rang1 ? rang1.communes : null; }
export function totalBeneficiaires() { return rang1 ? rang1.total : 0; }
