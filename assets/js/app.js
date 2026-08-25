/* ============================================================================
 * Accueil — un champ, puis une carte qui se comprend.
 * ----------------------------------------------------------------------------
 * Ce que la page servait avant : sept compteurs nationaux, un pavé de 900
 * caractères de méthode, puis une carte dont le sens — elle colore le
 * département où SIÈGENT les associations qui reçoivent, pas la collectivité
 * qui verse — était noyé dans ce pavé. Rien qui concerne le visiteur.
 *
 * Ce qu'elle sert maintenant : un champ unique, qui accepte une association,
 * une commune, un département ou une région et emmène au bon endroit. La
 * carte vient ensuite, avec un titre qui dit ce qu'elle montre, une légende
 * qui porte ses bornes ET son gris, une bascule « total / par habitant », et
 * un fonctionnement au doigt.
 *
 * Le premier écran ne charge toujours que des agrégats précalculés (~110 Ko).
 * L'index de suggestion (0,8 Mo) arrive en tâche de fond, une fois la carte
 * peinte.
 * ========================================================================= */

"use strict";

import {
  $, el, vider, euros, fmtNombre, pluriel, chargerGz, plier,
  lireEtat, ecrireEtat, messageEtat, messageErreur, enregistrerServiceWorker
} from "./commun.js";
import * as Index from "./index-recherche.js";
import * as Suggest from "./suggest.js";
import * as Lexique from "./lexique.js";
import * as Export from "./export.js";

var etat = {
  meta: null, cube: null, carte: null, top: null, denominateur: null,
  annee: "toutes", niveau: "tous", departement: null, region: null,
  vue: "total", fragments: {}, onglet: "beneficiaires"
};

// --- agrégation à la volée sur le cube --------------------------------------

function depsDeLaRegion() {
  if (!etat.region) return null;
  var out = {};
  var v = etat.meta.departements.valeurs;
  Object.keys(v).forEach(function (c) { if (v[c][1] === etat.region) out[c] = true; });
  return out;
}

function parDepartement() {
  var res = {};
  var deps = etat.cube.departements;
  var filtre = depsDeLaRegion();
  for (var code in deps) {
    if (filtre && !filtre[code]) continue;
    var total = [0, 0];
    var annees = deps[code];
    for (var an in annees) {
      if (etat.annee !== "toutes" && an !== etat.annee) continue;
      var niveaux = annees[an];
      for (var niv in niveaux) {
        if (etat.niveau !== "tous" && niv !== etat.niveau) continue;
        total[0] += niveaux[niv][0];
        total[1] += niveaux[niv][1];
      }
    }
    if (total[0]) res[code] = total;
  }
  return res;
}

function population(code) {
  var d = etat.meta.departements.valeurs[code];
  return (d && d[2]) || 0;
}

/** La grandeur portée par la carte, selon la vue choisie. */
function valeurCarte(code, brut) {
  if (etat.vue !== "habitant") return brut;
  var p = population(code);
  return p ? brut / p : null;
}

function totalNational() {
  var total = [0, 0];
  var nat = etat.cube.national;
  if (etat.region) {
    var d = parDepartement();
    Object.keys(d).forEach(function (c) { total[0] += d[c][0]; total[1] += d[c][1]; });
    return total;
  }
  for (var an in nat) {
    if (etat.annee !== "toutes" && an !== etat.annee) continue;
    for (var niv in nat[an]) {
      if (etat.niveau !== "tous" && niv !== etat.niveau) continue;
      total[0] += nat[an][niv][0];
      total[1] += nat[an][niv][1];
    }
  }
  return total;
}

/** Les mêmes dons, tels que la collectivité déclare les avoir PAYÉS.
 *
 *  Ils ne s'ajoutent JAMAIS au voté : quand une collectivité publie les deux,
 *  c'est le même argent. Ils s'affichent à côté, parce qu'une vingtaine de
 *  collectivités — la Loire-Atlantique en entier — ne publient QUE cela, et
 *  les taire les faisait disparaître du site. Aucune de ces sources ne donne
 *  l'adresse du bénéficiaire : le payé n'a donc pas de géographie. */
function totalPaye() {
  var total = [0, 0];
  var p = etat.cube.paye;
  if (!p || !p.national) return total;
  for (var an in p.national) {
    if (etat.annee !== "toutes" && an !== etat.annee) continue;
    for (var niv in p.national[an]) {
      if (etat.niveau !== "tous" && niv !== etat.niveau) continue;
      total[0] += p.national[an][niv][0];
      total[1] += p.national[an][niv][1];
    }
  }
  return total;
}

function sansDepartement() {
  var total = [0, 0];
  var sd = etat.cube.sans_departement;
  for (var an in sd) {
    if (etat.annee !== "toutes" && an !== etat.annee) continue;
    total[0] += sd[an][0];
    total[1] += sd[an][1];
  }
  return total;
}

// --- carte ------------------------------------------------------------------

// Grandeur continue : UNE seule teinte, du clair au foncé. Jamais d'arc-en-ciel
// — la couleur doit se lire comme un ordre, pas comme des catégories.
var PALETTE = ["--seq-1", "--seq-2", "--seq-3", "--seq-4", "--seq-5"];

/** Seuils par quantiles : une échelle linéaire écraserait tout, Paris pesant
 *  plusieurs fois le département médian. */
function seuils(valeurs) {
  var tri = valeurs.slice().sort(function (a, b) { return a - b; });
  if (!tri.length) return [];
  return [0.2, 0.4, 0.6, 0.8].map(function (q) {
    return tri[Math.floor(q * (tri.length - 1))];
  });
}

function classe(valeur, bornes) {
  for (var i = 0; i < bornes.length; i++) if (valeur <= bornes[i]) return i;
  return bornes.length;
}

function formatValeur(v) {
  if (v == null) return "—";
  return etat.vue === "habitant"
    ? euros(v).replace(/ €$/, " €") + " / hab."
    : euros(v);
}

function dessinerCarte() {
  var svg = $("#carte");
  var donnees = parDepartement();
  var valeurs = [];
  var parCode = {};
  Object.keys(donnees).forEach(function (c) {
    var v = valeurCarte(c, donnees[c][1]);
    if (v != null) { parCode[c] = v; valeurs.push(v); }
  });
  var bornes = seuils(valeurs);

  Array.prototype.forEach.call(svg.querySelectorAll("path[data-dep]"), function (p) {
    var code = p.getAttribute("data-dep");
    var v = parCode[code];
    p.style.fill = v != null
      ? "var(" + PALETTE[classe(v, bornes)] + ")"
      : "var(--seq-vide)";
    p.classList.toggle("actif", etat.departement === code);
    p.classList.toggle("hors-region", !!(etat.region && !(code in donnees)));
    // La valeur est DANS l'étiquette : un lecteur d'écran doit entendre ce que
    // la couleur montre, pas seulement le nom du département.
    var nom = etat.meta.departements.valeurs[code];
    p.setAttribute("aria-label", (nom ? nom[0] : code) + " : " +
      (v != null ? formatValeur(v) : "aucune donnée pour ce filtre"));
  });

  dessinerLegende(bornes, valeurs);
  $("#titre-carte").textContent = etat.vue === "habitant"
    ? "Ce que les associations domiciliées dans chaque département ont reçu, par habitant du département"
    : "Ce que les associations domiciliées dans chaque département ont reçu";
}

/** La légende porte les BORNES, et le gris avec son sens. Sans elles, cinq
 *  carrés bleus n'apprennent rien, et un département gris se lit « zéro »
 *  quand il veut dire « rien de publié sous ce filtre ». */
function dessinerLegende(bornes, valeurs) {
  var hote = $("#legende");
  vider(hote);
  if (!valeurs.length) {
    hote.appendChild(el("span", "legende-vide", "Aucune donnée sous ce filtre."));
    return;
  }
  var min = Math.min.apply(null, valeurs);
  var max = Math.max.apply(null, valeurs);
  var paliers = [min].concat(bornes).concat([max]);
  var echelle = el("div", "echelle-legende");
  PALETTE.forEach(function (v, i) {
    var pas = el("span", "pas");
    var carre = el("i");
    carre.style.background = "var(" + v + ")";
    pas.appendChild(carre);
    pas.appendChild(el("span", "borne",
      formatValeur(paliers[i]) + (i === PALETTE.length - 1 ? " et plus" : "")));
    echelle.appendChild(pas);
  });
  var vide = el("span", "pas pas-vide");
  var cv = el("i");
  cv.style.background = "var(--seq-vide)";
  vide.appendChild(cv);
  vide.appendChild(el("span", "borne", "aucune donnée"));
  echelle.appendChild(vide);
  hote.appendChild(echelle);

  var note = el("p", "note-legende");
  note.appendChild(document.createTextNode(
    "Cinq classes de même effectif (un cinquième des départements chacune). Un " +
    "département gris ne verse pas zéro : personne n'y a publié sous ce filtre — "));
  var a = el("a", null, "ce que le site ne sait pas");
  a.href = "couverture.html";
  note.appendChild(a);
  note.appendChild(document.createTextNode("."));
  hote.appendChild(note);
}

function construireCarte() {
  var svg = $("#carte");
  svg.setAttribute("viewBox", etat.carte.viewBox);
  var traces = etat.carte.traces;
  var noms = etat.meta.departements.valeurs;

  Object.keys(etat.carte.medaillons || {}).forEach(function (code) {
    var m = etat.carte.medaillons[code];
    var r = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    r.setAttribute("x", m.x); r.setAttribute("y", m.y);
    r.setAttribute("width", m.w); r.setAttribute("height", m.h);
    r.setAttribute("class", "medaillon");
    svg.appendChild(r);
    var t = document.createElementNS("http://www.w3.org/2000/svg", "text");
    t.setAttribute("x", m.x + 2); t.setAttribute("y", m.y + 9);
    t.setAttribute("class", "etiquette-medaillon");
    // Le code seul (« 971 ») ne dit rien à qui ne connaît pas la nomenclature
    // INSEE : les médaillons portent maintenant le nom du territoire. Il est
    // resserré à la largeur du cadre — « Guadeloupe » débordait sur le
    // médaillon voisin.
    t.setAttribute("textLength", Math.max(10, m.w - 4));
    t.setAttribute("lengthAdjust", "spacingAndGlyphs");
    t.textContent = noms[code] ? noms[code][0] : code;
    svg.appendChild(t);
  });

  Object.keys(traces).sort().forEach(function (code) {
    var p = document.createElementNS("http://www.w3.org/2000/svg", "path");
    p.setAttribute("d", traces[code]);
    p.setAttribute("data-dep", code);
    p.setAttribute("tabindex", "0");
    p.setAttribute("role", "button");
    p.addEventListener("click", function () { choisirDepartement(code); });
    p.addEventListener("keydown", function (e) {
      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); choisirDepartement(code); }
    });
    // `pointerevents` plutôt que `mousemove` : sur un téléphone, la carte
    // n'affichait AUCUNE valeur — l'infobulle ne se déclenchait qu'à la
    // souris. Un appui la montre maintenant, puis un second sélectionne.
    p.addEventListener("pointerenter", function (e) { survol(e, code); });
    p.addEventListener("pointermove", function (e) { survol(e, code); });
    p.addEventListener("pointerdown", function (e) { survol(e, code); });
    p.addEventListener("pointerleave", masquerInfobulle);
    p.addEventListener("focus", function () { survolClavier(code, p); });
    p.addEventListener("blur", masquerInfobulle);
    svg.appendChild(p);
  });
}

var infobulle;

function texteInfobulle(code) {
  var d = parDepartement()[code];
  var nom = etat.meta.departements.valeurs[code];
  var v = d ? valeurCarte(code, d[1]) : null;
  return [(nom ? nom[0] : code) + " (" + code + ")",
          d ? formatValeur(v) + " · " + pluriel(d[0], "versement")
            : "aucune donnée pour ce filtre"];
}

function poserInfobulle(code, x, y) {
  if (!infobulle) infobulle = $("#infobulle");
  var t = texteInfobulle(code);
  vider(infobulle);
  infobulle.appendChild(el("b", null, t[0]));
  infobulle.appendChild(document.createTextNode(t[1]));
  infobulle.classList.add("visible");
  infobulle.style.left = Math.min(x + 14, window.innerWidth - 275) + "px";
  infobulle.style.top = Math.min(y + 14, window.innerHeight - 80) + "px";
}

function survol(e, code) { poserInfobulle(code, e.clientX, e.clientY); }

function survolClavier(code, p) {
  var r = p.getBoundingClientRect();
  poserInfobulle(code, r.left + r.width / 2, r.top + r.height / 2);
}

function masquerInfobulle() {
  if (infobulle) infobulle.classList.remove("visible");
}

/** Sous 620 px, la carte SVG rend les départements plus petits qu'un doigt.
 *  Une liste cherchable la double : elle dit la même chose, en toutes
 *  lettres, et se manie. */
function dessinerListeDepartements() {
  var hote = $("#liste-departements");
  var donnees = parDepartement();
  var noms = etat.meta.departements.valeurs;
  var codes = Object.keys(noms).filter(function (c) {
    return !etat.region || noms[c][1] === etat.region;
  }).sort(function (a, b) {
    return (donnees[b] ? valeurCarte(b, donnees[b][1]) : -1) -
           (donnees[a] ? valeurCarte(a, donnees[a][1]) : -1);
  });
  vider(hote);
  var ul = el("ul", "classement classement-compact");
  codes.forEach(function (c) {
    var li = el("li", "resultat");
    li.tabIndex = 0;
    li.setAttribute("role", "button");
    li.appendChild(el("span", "nom", noms[c][0] + " (" + c + ")"));
    li.appendChild(el("span", "montant",
      donnees[c] ? formatValeur(valeurCarte(c, donnees[c][1])) : "—"));
    li.appendChild(el("span", "detail", donnees[c]
      ? pluriel(donnees[c][0], "versement") : "aucune donnée sous ce filtre"));
    li.addEventListener("click", function () { choisirDepartement(c); });
    li.addEventListener("keydown", function (e) {
      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); choisirDepartement(c); }
    });
    ul.appendChild(li);
  });
  hote.appendChild(ul);
}

// --- compteurs --------------------------------------------------------------

function dessinerCompteurs() {
  var t = totalNational();
  var paye = totalPaye();
  var m = etat.meta;
  var sd = sansDepartement();
  var cases = [
    [euros(t[1]), "de dons votés", "vote"],
    [paye[0] && !etat.region ? euros(paye[1]) : "—", "de dons payés, comptés à part", "paye"],
    [fmtNombre.format(t[0]), "versements recensés", null],
    [fmtNombre.format(m.totaux.beneficiaires_distincts), "bénéficiaires distincts", null]
  ];
  var hote = $("#compteurs");
  vider(hote);
  cases.forEach(function (c) {
    var d = el("div", "compteur");
    d.appendChild(el("span", "valeur", c[0]));
    var e = el("span", "etiquette");
    if (c[2]) {
      e.appendChild(document.createTextNode("de dons "));
      e.appendChild(Lexique.mot(c[2], c[2] === "vote" ? "votés" : "payés"));
      if (c[2] === "paye") e.appendChild(document.createTextNode(", comptés à part"));
    } else {
      e.appendChild(document.createTextNode(c[1]));
    }
    d.appendChild(e);
    hote.appendChild(d);
  });
  Lexique.poser(hote);

  // La part invisible sur la carte, dite en clair plutôt qu'en pourcentage nu.
  var note = $("#note-compteurs");
  vider(note);
  if (t[0]) {
    var part = Math.round(sd[0] / t[0] * 100);
    note.appendChild(document.createTextNode(
      "Sur ces versements, " + part + " % n'indiquent aucun département : ils " +
      "comptent dans les totaux mais ne peuvent pas colorer la carte. "));
    var a = el("a", null, "Pourquoi ?");
    a.href = "methode.html";
    note.appendChild(a);
  }
}

// --- panneau ----------------------------------------------------------------

/** Un classement dont chaque ligne MÈNE quelque part. Les vingt-cinq plus gros
 *  bénéficiaires étaient l'entrée la plus naturelle vers la recherche, et ils
 *  étaient inertes : le cul-de-sac le plus visible du site. */
/** Le classement des bénéficiaires contient des organismes qui ne sont pas des
 *  associations — SNCF Voyageurs, l'AFP, une région. Quand la source ne déclare
 *  pas la nature juridique, le défaut est « association » : c'est le bon côté
 *  où se tromper (exclure à tort effacerait une association réelle), mais le
 *  lecteur doit le savoir en regardant la liste, pas trois pages plus loin. */
function noteNatureDevinee() {
  var p = el("p", "note-panneau");
  p.appendChild(document.createTextNode(
    "Certains noms de cette liste ne sont pas des associations — SNCF, l'AFP, " +
    "une région. Quand la source ne dit pas la nature juridique du bénéficiaire, " +
    "le site suppose « association » plutôt que d'exclure une association réelle. "));
  var a = el("a", null, "Pourquoi ce choix");
  a.href = "methode.html";
  p.appendChild(a);
  p.appendChild(document.createTextNode("."));
  return p;
}

function classement(entrees, limite, versRecherche) {
  var ul = el("ul", "classement");
  entrees.slice(0, limite || 25).forEach(function (e) {
    var li = versRecherche ? el("a", "resultat") : el("li", "resultat");
    if (versRecherche) li.href = "recherche.html#q=" + encodeURIComponent(e[0]);
    li.appendChild(el("span", "nom", e[0]));
    li.appendChild(el("span", "montant", euros(e[2])));
    li.appendChild(el("span", "detail", pluriel(e[1], "versement")));
    ul.appendChild(li);
  });
  return ul;
}

async function choisirDepartement(code) {
  etat.departement = etat.departement === code ? null : code;
  ecrireEtat(etatURL(), false);
  dessinerCarte();
  dessinerListeDepartements();
  await dessinerPanneau();
  var p = $("#panneau");
  if (etat.departement && p.getBoundingClientRect().top > window.innerHeight - 120) {
    p.scrollIntoView({ behavior: "smooth", block: "start" });
  }
}

async function dessinerPanneau() {
  var titre = $("#panneau-titre");
  var sousTitre = $("#panneau-soustitre");
  var corps = $("#panneau-corps");
  vider(corps);

  if (!etat.departement) {
    var nomRegion = etat.region && etat.meta.regions[etat.region];
    titre.textContent = nomRegion || "France entière";
    sousTitre.textContent = nomRegion
      ? "Les départements de la région. Cliquez-en un pour son détail."
      : "Les plus gros bénéficiaires et donateurs, toutes années confondues. Cliquez un département pour son détail.";
    corps.appendChild(classement(
      etat.onglet === "beneficiaires" ? etat.top.beneficiaires : etat.top.donateurs,
      25, etat.onglet === "beneficiaires"));
    if (etat.onglet === "beneficiaires") corps.appendChild(noteNatureDevinee());
    return;
  }

  var code = etat.departement;
  var nom = etat.meta.departements.valeurs[code];
  titre.textContent = (nom ? nom[0] : code) + " (" + code + ")";
  vider(sousTitre);
  sousTitre.appendChild(messageEtat("Chargement du détail…", "chargement"));

  try {
    if (!etat.fragments[code]) {
      etat.fragments[code] = await chargerGz("data/aggregates/departements/" + code + ".json.gz");
    }
    var f = etat.fragments[code];
    vider(sousTitre);
    sousTitre.textContent = euros(f.montant_eur) + " reçus · " +
      pluriel(f.lignes, "versement") + " · " + (f.region || "");
    var entrees = etat.onglet === "beneficiaires" ? f.beneficiaires : f.donateurs;
    corps.appendChild(classement(entrees, 30, etat.onglet === "beneficiaires"));
    if (etat.onglet === "beneficiaires") corps.appendChild(noteNatureDevinee());
    corps.appendChild(Export.blocExport(
      "Télécharger ces " + fmtNombre.format(entrees.length) + " lignes (CSV)",
      "Dons votés uniquement, toutes années confondues — le filtre d'année de " +
      "la carte ne s'y applique pas.",
      function () {
        return {
          nom: Export.nomFichier("departement", code, etat.onglet),
          texte: Export.csv(
            [etat.onglet === "beneficiaires" ? "beneficiaire" : "donateur",
             "nb_versements", "dons_votes_eur"],
            entrees.map(function (e) {
              return [e[0], e[1], Export.montant(e[2])];
            }))
        };
      }));
  } catch (err) {
    vider(sousTitre);
    sousTitre.appendChild(messageErreur("Détail indisponible pour ce département.",
      function () { etat.fragments[code] = null; dessinerPanneau(); }));
  }
}

// --- « ce que ces chiffres ne disent pas » ----------------------------------
//
// Le même texte qu'avant, qui est bon — mais découpé. Il formait un seul
// paragraphe de 900 caractères entre les compteurs et la carte : personne ne
// lisait la phrase qui explique ce que la carte montre.

function ajouterPoint(hote, titre, texte) {
  var d = el("div", "point");
  d.appendChild(el("h3", null, titre));
  var p = el("p");
  if (typeof texte === "string") p.appendChild(document.createTextNode(texte));
  else texte.forEach(function (n) {
    p.appendChild(typeof n === "string" ? document.createTextNode(n) : n);
  });
  d.appendChild(p);
  hote.appendChild(d);
}

function dessinerReserves() {
  var hote = $("#reserves");
  vider(hote);
  var q = etat.meta.qualite;
  var t = etat.meta.totaux;

  ajouterPoint(hote, "La carte situe qui REÇOIT, pas qui verse",
    etat.meta.couverture.note + " " +
    fmtNombre.format(etat.meta.couverture.lignes_sans_departement) +
    " versements n'indiquent aucun département : ils comptent dans les totaux, " +
    "mais restent invisibles sur la carte.");

  ajouterPoint(hote, "Voté et payé ne s'additionnent jamais", [
    "Une collectivité publie souvent le même argent deux fois : ce qu'elle a ",
    Lexique.mot("vote", "voté"), ", puis ce qu'elle a ",
    Lexique.mot("mandate", "mandaté"),
    ". Le site affiche les deux côte à côte et ne les somme jamais — " +
    euros(t.dons_payes.montant_eur) + " sont publiés comme payés, et pour une " +
    "vingtaine de collectivités, dont le département de Loire-Atlantique, c'est " +
    "la seule chose qu'elles publient."]);

  var horsDon = t.hors_don || {};
  var libelles = { prestation: "de prestations facturées par l'association",
                   remboursement: "de remboursements et de cotisations",
                   nature: "d'aides en nature (locaux, personnel)" };
  var parts = [], totalHorsDon = 0;
  Object.keys(horsDon).forEach(function (k) {
    parts.push(euros(horsDon[k][1]) + " " + (libelles[k] || k));
    totalHorsDon += horsDon[k][1];
  });
  if (parts.length) {
    ajouterPoint(hote, "Tout argent versé n'est pas un don", [
      "Quand une collectivité achète un service à une association, il y a une " +
      "contrepartie : ce n'est pas un soutien. " + parts.join(", ") + " sont " +
      "ingérés et consultables, mais hors des totaux (" + euros(totalHorsDon) +
      " au total). Voir ", Lexique.mot("prestation", "prestation facturée"), "."]);
  }

  ajouterPoint(hote, "Les doublons entre sources sont retirés",
    fmtNombre.format(q.deduplication.lignes_ecartees) + " lignes ont été retirées (" +
    euros(q.deduplication.montant_ecarte_eur) + ") parce qu'une même subvention " +
    "était publiée par deux sources. Le rapprochement se fait sur le bénéficiaire, " +
    "le donateur, l'exercice, le montant et l'objet — jamais sur un identifiant " +
    "technique, qui ne se croise jamais d'une source à l'autre.");

  Lexique.poser(hote);
}

/** Le dénominateur, en un point de plus — chargé APRÈS le premier écran.
 *
 *  Ces 5 Ko n'ont rien à faire sur le chemin critique. Mais laisser croire que
 *  les totaux du site sont le tout serait pire que de charger un fichier de
 *  plus. */
async function ajouterDenominateur() {
  var d;
  try { d = await chargerGz("data/aggregates/denominateur.json.gz"); }
  catch (e) { return; }
  var c = d && d.resume && d.resume.commune;
  if (!c || !c.declare_eur) return;
  etat.denominateur = c;
  // Les chiffres de l'en-tête viennent de la donnée, jamais d'un nombre écrit
  // dans le HTML : celui-ci se périme en silence à la publication suivante.
  var d1 = $("#nb-declarants");
  if (d1) d1.textContent = fmtNombre.format(c.declarants);
  var d2 = $("#nb-declare");
  if (d2) d2.textContent = euros(c.declare_eur);
  var d3 = $("#nb-connu");
  if (d3) d3.textContent = euros(c.site_vote_eur).replace(/\s?Md€$/, "");
  var hote = $("#reserves");
  if (!hote) return;
  var lien = el("a", null, "Ce qu'on ne sait pas");
  lien.href = "couverture.html";
  ajouterPoint(hote, "Par rapport à quoi ?", [
    "Toutes les communes déclarent à la DGFiP ce qu'elles versent aux associations, " +
    "qu'elles publient ou non, au ",
    Lexique.mot("compte6574", "compte 6574"),
    " : " + fmtNombre.format(c.declarants) + " d'entre elles déclarent " +
    euros(c.declare_eur) + " entre " + c.exercices[0] + " et " + c.exercices[1] +
    ", quand le site en connaît " + euros(c.site_vote_eur) + " — soit " +
    Math.round(c.part_connue_pct) + " %. ", lien, "."]);
  Lexique.poser(hote);
}

// --- contrôles --------------------------------------------------------------

function etatURL() {
  return {
    dep: etat.departement, region: etat.region,
    annee: etat.annee === "toutes" ? "" : etat.annee,
    niveau: etat.niveau === "tous" ? "" : etat.niveau,
    vue: etat.vue === "total" ? "" : etat.vue
  };
}

function remplirFiltres() {
  var selAnnee = $("#filtre-annee");
  // Les années dans l'ordre décroissant, l'exercice inconnu à la fin, et les
  // années postérieures à l'exercice courant regroupées à part : la source les
  // publie (engagements pluriannuels, anomalies de saisie), mais les mêler
  // aux autres faisait choisir « 2036 » par erreur.
  var annees = etat.meta.annees.filter(function (a) { return a !== "inconnue"; });
  var courante = new Date().getFullYear();
  var passees = annees.filter(function (a) { return Number(a) <= courante; }).reverse();
  var futures = annees.filter(function (a) { return Number(a) > courante; }).reverse();
  function groupe(libelle, liste) {
    if (!liste.length) return;
    var g = document.createElement("optgroup");
    g.label = libelle;
    liste.forEach(function (a) {
      var o = document.createElement("option");
      o.value = a; o.textContent = a;
      g.appendChild(o);
    });
    selAnnee.appendChild(g);
  }
  groupe("Exercices", passees);
  groupe("Exercices à venir, publiés par la source", futures);
  groupe("Sans exercice", ["inconnue"]);

  var selNiveau = $("#filtre-niveau");
  etat.meta.niveaux.forEach(function (n) {
    var o = document.createElement("option");
    o.value = n; o.textContent = etat.meta.niveaux_libelles[n] || n;
    selNiveau.appendChild(o);
  });

  selAnnee.addEventListener("change", function (e) {
    etat.annee = e.target.value; rafraichir();
  });
  selNiveau.addEventListener("change", function (e) {
    etat.niveau = e.target.value; rafraichir();
  });
  $("#reinitialiser").addEventListener("click", function () {
    etat.annee = "toutes"; etat.niveau = "tous";
    etat.departement = null; etat.region = null; etat.vue = "total";
    selAnnee.value = "toutes"; selNiveau.value = "tous";
    majBascule(); rafraichir();
  });

  Array.prototype.forEach.call(document.querySelectorAll("#bascule-vue button"), function (b) {
    b.addEventListener("click", function () {
      etat.vue = b.getAttribute("data-vue");
      majBascule(); rafraichir();
    });
  });

  Array.prototype.forEach.call(document.querySelectorAll(".onglets button"), function (b) {
    b.addEventListener("click", function () {
      etat.onglet = b.getAttribute("data-onglet");
      Array.prototype.forEach.call(document.querySelectorAll(".onglets button"), function (x) {
        x.setAttribute("aria-selected", String(x === b));
      });
      dessinerPanneau();
    });
  });
}

function majBascule() {
  Array.prototype.forEach.call(document.querySelectorAll("#bascule-vue button"), function (b) {
    b.setAttribute("aria-pressed", String(b.getAttribute("data-vue") === etat.vue));
  });
}

function rafraichir() {
  ecrireEtat(etatURL(), false);
  dessinerCompteurs();
  dessinerCarte();
  dessinerListeDepartements();
  dessinerPanneau();
}

function appliquerEtatDepuisURL() {
  var u = lireEtat();
  etat.departement = u.dep || null;
  etat.region = u.region || null;
  etat.annee = u.annee || "toutes";
  etat.niveau = u.niveau || "tous";
  etat.vue = u.vue === "habitant" ? "habitant" : "total";
  $("#filtre-annee").value = etat.annee;
  $("#filtre-niveau").value = etat.niveau;
  majBascule();
  dessinerCompteurs();
  dessinerCarte();
  dessinerListeDepartements();
  dessinerPanneau();
}

// --- champ unique -----------------------------------------------------------

function poserChampUnique() {
  var input = $("#cherche-tout");
  // L'index de suggestion se charge dès que le pointeur approche du champ :
  // le précharger d'office coûtait 0,9 Mo à tout le monde, y compris à qui
  // vient seulement regarder la carte.
  Index.armerPrechargement(input);
  Suggest.poser(input, {
    choisir: async function (s) {
      location.href = await Suggest.adresseDe(s);
    },
    valider: function (texte) {
      if (texte.trim()) location.href = "recherche.html#q=" + encodeURIComponent(texte.trim());
    }
  });
}

// --- démarrage --------------------------------------------------------------

async function demarrer() {
  var res = await Promise.all([
    chargerGz("data/aggregates/meta.json.gz"),
    chargerGz("data/aggregates/cube.json.gz"),
    chargerGz("data/aggregates/map-departements.json.gz"),
    chargerGz("data/aggregates/top.json.gz")
  ]);
  etat.meta = res[0]; etat.cube = res[1]; etat.carte = res[2]; etat.top = res[3];

  $("#chargement").remove();
  $("#application").hidden = false;

  var nv = $("#nb-versements");
  if (nv) nv.textContent = fmtNombre.format(etat.meta.totaux.lignes);

  remplirFiltres();
  construireCarte();
  dessinerReserves();
  appliquerEtatDepuisURL();
  poserChampUnique();
  Lexique.poser(document);
  window.addEventListener("popstate", appliquerEtatDepuisURL);

  // Marqueur du banc de mesure : les données sont exploitables.
  window.__DATA_READY = true;

  ajouterDenominateur();
}

demarrer().catch(function (err) {
  var c = $("#chargement");
  if (c) {
    vider(c);
    c.appendChild(messageErreur(
      "Le site n'a pas pu charger ses données. Vérifiez votre connexion.",
      function () { location.reload(); }));
  }
  console.error(err);
});

enregistrerServiceWorker();
