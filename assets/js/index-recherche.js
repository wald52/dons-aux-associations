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

/** Arme le chargement de l'index de suggestion sur l'INTENTION de s'en servir,
 *  pas sur l'inactivité de la page.
 *
 *  Un préchargement systématique faisait passer l'accueil de 0,14 à 1,05 Mo —
 *  mesuré — pour un fichier dont la plupart des visiteurs n'auront pas l'usage.
 *  Le pointeur qui entre dans le champ, un doigt qui s'y pose ou le focus
 *  précèdent la première lettre de quelques centaines de millisecondes : c'est
 *  exactement le temps qu'il faut. Qui ne touche jamais au champ ne paie rien.
 */
export function armerPrechargement(input) {
  if (!input) return;
  var lance = false;
  var lancer = function () {
    if (lance) return;
    lance = true;
    chargerRang1().catch(function () { /* réessayé à la frappe */ });
  };
  ["pointerenter", "touchstart", "focus"].forEach(function (ev) {
    input.addEventListener(ev, lancer, { once: true, passive: true });
  });
}

// --- rang 2 -----------------------------------------------------------------

var rang2 = null;
var promesseRang2 = null;

export function rang2Pret() { return rang2 !== null; }

/** Une colonne de texte gardée en UNE chaîne, avec ses bornes dans un tableau
 *  typé — et découpée seulement pour les quelques lignes affichées.
 *
 *  Découper d'avance coûtait cher : 427 451 chaînes JavaScript, c'est autant
 *  d'objets à en-tête, et l'onglet montait à 156 Mo. Une chaîne unique plus un
 *  `Int32Array` tient dans la taille des octets eux-mêmes. */
function colonne(brut) {
  var n = 0;
  for (var k = 0; k < brut.length; k++) if (brut.charCodeAt(k) === 10) n++;
  var bornes = new Int32Array(n + 2);
  var i = 0, pos = 0;
  bornes[0] = 0;
  while (true) {
    var j = brut.indexOf("\n", pos);
    if (j < 0) break;
    bornes[++i] = j + 1;
    pos = j + 1;
  }
  bornes[++i] = brut.length + 1;
  return {
    nb: i,
    lire: function (k) { return brut.slice(bornes[k], bornes[k + 1] - 1); },
    longueur: function (k) { return bornes[k + 1] - 1 - bornes[k]; }
  };
}

export function chargerRang2(surProgression) {
  if (!promesseRang2) {
    promesseRang2 = chargerGz("data/recherche/noms.json.gz", surProgression)
      .then(function (d) {
        // Une seule grande chaîne de noms pliés, bornée par « \n » : `indexOf`
        // y court en une passe native — quelques millisecondes sur 427 451
        // noms — et la position se retraduit en rang par dichotomie.
        var brut = colonne(d.n);
        var plies = new Array(d.nb);
        for (var i = 0; i < d.nb; i++) plies[i] = plier(brut.lire(i));
        var gros = "\n" + plies.join("\n") + "\n";
        var debuts = new Int32Array(d.nb);
        var longueurs = new Int32Array(d.nb);
        var pos = 1;
        for (i = 0; i < d.nb; i++) {
          debuts[i] = pos; longueurs[i] = plies[i].length; pos += plies[i].length + 1;
        }
        // Les 427 451 chaînes pliées ont fini leur office : seule la grande
        // chaîne sert désormais, et les longueurs sont dans un tableau typé.
        plies = null;
        // Les colonnes numériques passent en tableaux TYPÉS. Sept tableaux
        // JavaScript de 427 451 nombres, c'est l'essentiel de la mémoire de
        // cette page ; les mêmes en `Int32Array` et `Uint8Array` pèsent le
        // poids de leurs octets, et laissent le JSON d'origine être collecté.
        rang2 = {
          nb: d.nb, brut: brut, gros: gros, debuts: debuts, longueurs: longueurs,
          deps: colonne(d.d),
          m: Float64Array.from(d.m),
          e: Uint8Array.from(d.e),
          v: Int32Array.from(d.v),
          a: Uint16Array.from(d.a),
          b: Uint16Array.from(d.b),
          x: Uint8Array.from(d.x),
          p: Uint8Array.from(d.p),
          echelons: d.echelons || ECHELONS
        };
        d = null;
        return rang2;
      });
  }
  return promesseRang2;
}

// --- recherche --------------------------------------------------------------

function fiche2(i) {
  return {
    rang: i, nom: rang2.brut.lire(i), dep: rang2.deps.lire(i) || null,
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
  if (pos + 1 > d[res] + rang2.longueurs[res]) return -1;
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
// L'ordre est celui que `build_index_navigateur.py` écrit, et les deux DOIVENT
// rester identiques : une clé ajoutée d'un seul côté décale silencieusement
// toutes les suivantes.
var CLES_RESUME = ["nom", "siren", "rna", "dep", "kind", "nbv", "montant",
  "ecarte", "a0", "a1", "ech", "echelons", "nbd", "principal", "part",
  "publient_jusqu_a", "famille"];

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
      // Le verdict des totaux, calculé par le pipeline. Le navigateur ne le
      // recalcule pas : il ne le pourrait pas sans la nature juridique
      // déclarée du bénéficiaire, absente de l'index.
      cas: (d.cas && d.cas[shard.cas[j]]) || "vote",
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
  // On balaie TOUTES les communes avant de trier. S'arrêter aux premières
  // trouvées revenait à les prendre dans l'ordre des codes INSEE : taper
  // « bes » proposait Bessay-sur-Allier, Besson et Besny-et-Loizy, et pas
  // Besançon. Un balayage complet des 34 936 noms coûte deux millisecondes.
  var c = rang1.communes;
  var communes = [];
  for (var i = 0; i < c.plies.length; i++) {
    if (c.plies[i].indexOf(q) === 0) {
      communes.push({ genre: "commune", code: c.ids[i], nom: c.noms[i],
                      dep: c.deps[i], population: c.p[i] });
    }
  }
  // Une commune peuplée avant un hameau homonyme : à requête égale, c'est
  // celle que le lecteur cherche neuf fois sur dix. Et un nom exact passe
  // devant un nom plus long — « Rennes » avant « Rennes-les-Bains ».
  communes.sort(function (a, b) {
    var ea = plier(a.nom) === q ? 0 : 1, eb = plier(b.nom) === q ? 0 : 1;
    if (ea !== eb) return ea - eb;
    return (b.population || 0) - (a.population || 0);
  });
  return out.concat(communes).slice(0, limite || 8);
}

export function communes() { return rang1 ? rang1.communes : null; }
export function totalBeneficiaires() { return rang1 ? rang1.total : 0; }
