/* ============================================================================
 * « Ma commune » — ce que ma commune verse aux associations.
 * ----------------------------------------------------------------------------
 * C'est la chose la plus concrète du site, et elle était la 8ᵉ section d'une
 * page intitulée « Ce que ce site ne sait pas », derrière un menu déroulant de
 * neuf cents entrées, avec la fiche rendue hors écran. Elle a maintenant sa
 * page, son adresse partageable et son champ à autocomplétion.
 *
 * Elle répond pour les 34 829 communes qui déclarent un compte 6574 à la
 * DGFiP — c'est-à-dire presque toutes, qu'elles fassent de l'open data ou non.
 *
 * ATTENTION, la règle qui gouverne cette page : elle dit ce que la commune
 * PAIE. La carte de l'accueil, elle, dit ce que les associations DOMICILIÉES
 * dans un territoire ont REÇU. Ce sont deux géographies opposées, et les
 * afficher côte à côte sans le dire ferait lire de l'argent versé comme de
 * l'argent reçu. Le lien vers le département est donc étiqueté comme un autre
 * point de vue, jamais comme un complément à additionner.
 * ========================================================================= */

"use strict";

import {
  $, el, vider, euros, fmtNombre, chargerGz, plier,
  lireEtat, ecrireEtat, messageEtat, messageErreur, enregistrerServiceWorker
} from "./commun.js";
import * as Index from "./index-recherche.js";
import * as Suggest from "./suggest.js";
import * as Lexique from "./lexique.js";
import * as Export from "./export.js";

var fiches = {};
var denominateur = null;
var meta = null;

function pourcent(v) {
  if (v == null) return "—";
  return (Math.round(v * 10) / 10).toString().replace(".", ",") + " %";
}

function depDuCode(insee) {
  if (!insee) return null;
  if (insee.slice(0, 2) === "97") return insee.slice(0, 3);
  if (insee.slice(0, 2) === "2A" || insee.slice(0, 2) === "2B") return insee.slice(0, 2);
  return insee.slice(0, 2);
}

async function chargerFiches(dep) {
  if (!fiches[dep]) {
    fiches[dep] = await chargerGz("data/aggregates/denominateur-communes/" + dep + ".json.gz");
  }
  return fiches[dep];
}

// --- la fiche ---------------------------------------------------------------

function ligne(cellules, entete) {
  var tr = el("tr");
  cellules.forEach(function (c) {
    if (typeof c === "string") tr.appendChild(el(entete ? "th" : "td", null, c));
    else tr.appendChild(c);
  });
  return tr;
}

function point(hote, titre, contenu) {
  var d = el("div", "point");
  d.appendChild(el("h3", null, titre));
  var p = el("p");
  (Array.isArray(contenu) ? contenu : [contenu]).forEach(function (n) {
    p.appendChild(typeof n === "string" ? document.createTextNode(n) : n);
  });
  d.appendChild(p);
  hote.appendChild(d);
}

function dessinerFiche(code, c, population) {
  var hote = $("#fiche-commune");
  vider(hote);

  var exercices = Object.keys(c.d).sort();
  var declare = 0, vote = 0, paye = 0;
  exercices.forEach(function (a) {
    declare += c.d[a];
    vote += c.v[a] || 0;
    paye += c.p[a] || 0;
  });
  var part = declare > 0 ? Math.round(vote / declare * 1000) / 10 : null;
  var periode = exercices.length
    ? exercices[0] + " et " + exercices[exercices.length - 1] : "—";

  var entete = el("div", "entete-commune");
  entete.appendChild(el("h2", null, c.n));
  var st = el("p", "sous-titre");
  st.appendChild(document.createTextNode("Code INSEE " + code));
  if (population) st.appendChild(document.createTextNode(
    " · " + fmtNombre.format(population) + " habitants"));
  var d = meta && meta.departements.valeurs[depDuCode(code)];
  if (d) st.appendChild(document.createTextNode(" · " + d[0] + " (" + depDuCode(code) + ")"));
  entete.appendChild(st);
  hote.appendChild(entete);

  var compteurs = el("div", "compteurs");
  var cases = [
    [euros(declare), ["mandatés à des associations entre " + periode + ", au ",
      Lexique.mot("compte6574", "compte 6574")]],
    [vote ? euros(vote) : "rien", vote
      ? ["que le site connaît nommément, soit " + pourcent(part) + " de ce montant"]
      : ["que le site connaît nommément de ces versements"]],
    [paye ? euros(paye) : "—", paye
      ? ["publiés comme ", Lexique.mot("paye", "payés"), " — jamais additionnés au voté"]
      : ["aucun montant publié comme payé"]]
  ];
  // Le montant par habitant : c'est la seule façon de comparer sa commune à
  // une autre. Un village de 400 habitants et une métropole de 300 000 ne se
  // comparent pas en euros bruts.
  if (population && declare) {
    cases.push([euros(declare / population / Math.max(1, exercices.length)),
      ["par habitant et par an, en moyenne sur la période"]]);
  }
  cases.forEach(function (paire) {
    var bloc = el("div", "compteur");
    bloc.appendChild(el("span", "valeur", paire[0]));
    var e = el("span", "etiquette");
    paire[1].forEach(function (n) {
      e.appendChild(typeof n === "string" ? document.createTextNode(n) : n);
    });
    bloc.appendChild(e);
    compteurs.appendChild(bloc);
  });
  hote.appendChild(compteurs);

  // La phrase qui manquait au site : dire ce qu'on ne sait pas d'une commune
  // sans laisser croire qu'elle ne verse rien.
  var verdict = el("p", "avertissement");
  if (!vote && !paye) {
    verdict.appendChild(el("b", null, "Le site ne connaît aucun versement de cette commune. "));
    verdict.appendChild(document.createTextNode(
      "Ce n'est pas qu'elle ne subventionne pas : sa comptabilité montre le contraire, " +
      "puisqu'elle déclare " + euros(declare) + " au compte 6574. C'est que ses " +
      "subventions ne sont publiées nulle part que nous ayons trouvé — seules les " +
      "communes de plus de 3 500 habitants y sont tenues, et l'obligation est peu " +
      "suivie. La lacune est du côté de la publication, pas du versement."));
  } else {
    verdict.appendChild(el("b", null, "Ce que le site en connaît, et ce qui lui échappe. "));
    verdict.appendChild(document.createTextNode(
      "Les montants de la colonne « connu » viennent des subventions publiées, " +
      "nom du bénéficiaire par nom du bénéficiaire. Le déclaré, lui, ne nomme " +
      "personne : c'est une ligne de comptabilité. " +
      (part != null && part > 100
        ? "La part dépasse 100 %, et ce n'est pas une erreur : le site connaît des " +
          "montants votés quand la balance porte des montants mandatés, et une " +
          "collectivité vote souvent plus qu'elle ne mandate."
        : "Les deux ne coïncident jamais exactement : le déclaré est mandaté, " +
          "le connu est très majoritairement voté.")));
  }
  hote.appendChild(verdict);

  hote.appendChild(el("h3", null, "Exercice par exercice"));
  var t = el("table");
  var thead = el("thead");
  thead.appendChild(ligne(["Exercice", "Déclaré au compte 6574",
    "Connu du site (voté)", "Connu du site (payé)"], true));
  t.appendChild(thead);
  var tbody = el("tbody");
  exercices.forEach(function (a) {
    tbody.appendChild(ligne([a,
      el("td", "num montant", euros(c.d[a])),
      el("td", "num montant", c.v[a] ? euros(c.v[a]) : "—"),
      el("td", "num montant", c.p[a] ? euros(c.p[a]) : "—")]));
  });
  t.appendChild(tbody);
  var env = el("div", "table-enveloppe");
  env.setAttribute("tabindex", "0");
  env.setAttribute("role", "region");
  env.setAttribute("aria-label", "Détail par exercice");
  env.appendChild(t);
  hote.appendChild(env);

  // Les trois colonnes ne s'additionnent jamais, et le fichier le dit dans le
  // nom même de ses colonnes : mandaté d'un côté, voté et payé de l'autre.
  hote.appendChild(Export.blocExport(
    "Télécharger ce tableau (CSV)",
    "Le déclaré est un montant mandaté, le connu est très majoritairement voté : " +
    "les trois colonnes ne s'additionnent jamais.",
    function () {
      return {
        nom: Export.nomFichier("commune", c.n, code),
        texte: Export.csv(
          ["exercice", "declare_compte_6574_eur", "connu_du_site_vote_eur",
           "connu_du_site_paye_eur"],
          exercices.map(function (a) {
            return [a, Export.montant(c.d[a]),
                    Export.montant(c.v[a] || null), Export.montant(c.p[a] || null)];
          }))
      };
    }));

  // Les réserves : une par point, pas un pavé de sept cents caractères.
  var reserves = el("div", "points points-reserves");
  reserves.appendChild(el("h3", null, "À savoir sur ces chiffres"));
  point(reserves, "Le compte 6574 n'est pas purement associatif",
    ["Il s'intitule « subventions de fonctionnement aux associations et autres " +
     "personnes de droit privé ». Une subvention imputée ailleurs — au 6568, ou " +
     "en investissement au 204 — n'y figure pas."]);
  point(reserves, "Les budgets annexes sont compris",
    ["Ils portent le même SIREN que la commune, et c'est par ce SIREN qu'ils lui " +
     "sont rattachés — la commune le dit donc elle-même, rien n'est deviné."]);

  var pc = (denominateur && denominateur.resume && denominateur.resume.commune) || {};
  var per = pc.exercices || [];
  var attendus = per.length === 2 ? Number(per[1]) - Number(per[0]) + 1 : null;
  if (attendus && exercices.length < attendus) {
    point(reserves, "Une année absente n'est pas un zéro",
      ["Cette commune déclare un montant sur " + exercices.length + " des " +
       attendus + " exercices publiés (" + per[0] + "–" + per[1] + "). La balance " +
       "ne porte une ligne que si le compte a servi : la commune peut n'avoir rien " +
       "versé cette année-là, avoir imputé sa subvention à un autre compte, ou ne " +
       "pas encore exister. Rien dans la donnée ne dit laquelle — nous ne " +
       "reconstituons pas l'historique des communes fusionnées, ce serait le deviner."]);
  }
  if (code === "75056") {
    point(reserves, "Paris a été deux collectivités jusqu'en 2018",
      ["Une commune et un département, fusionnés au 1ᵉʳ janvier 2019 (loi " +
       "n° 2017-257). Cette fiche ne porte que la part communale."]);
  }
  if (!vote && !paye) {
    point(reserves, "« Rien de connu » peut aussi être un défaut d'appariement",
      ["Un versement n'est rattaché à une commune que si le libellé de son financeur " +
       "a pu être rapproché du référentiel INSEE. Un libellé inhabituel échoue à " +
       "s'apparier : l'erreur va toujours vers la sous-estimation, jamais vers " +
       "l'inverse."]);
  }
  hote.appendChild(reserves);

  // L'autre point de vue, nommé comme tel. Ces deux géographies ne
  // s'additionnent pas : l'une regarde qui paie, l'autre qui reçoit.
  var dep = depDuCode(code);
  var autre = el("div", "encart-autre-vue");
  autre.appendChild(el("h3", null, "L'autre bout de la question"));
  var pa = el("p");
  pa.appendChild(document.createTextNode(
    "Cette page dit ce que la commune VERSE. Elle ne dit pas ce que les " +
    "associations de " + c.n + " REÇOIVENT — de leur département, de leur région " +
    "ou de l'État. Ce sont deux géographies opposées, et leurs montants ne " +
    "s'additionnent jamais. "));
  var la = el("a", "bouton", "Ce que les associations du département ont reçu");
  la.href = "index.html#dep=" + dep;
  pa.appendChild(la);
  autre.appendChild(pa);
  hote.appendChild(autre);

  Lexique.poser(hote);
}

// --- chargement d'une commune -----------------------------------------------

async function afficher(code) {
  var hote = $("#fiche-commune");
  vider(hote);
  hote.appendChild(messageEtat("Chargement de la fiche…", "chargement"));
  var dep = depDuCode(code);
  var donnees;
  try { donnees = await chargerFiches(dep); }
  catch (e) {
    vider(hote);
    hote.appendChild(messageErreur(
      "Les données de ce département n'ont pas pu être chargées.",
      function () { fiches[dep] = null; afficher(code); }));
    return;
  }
  var c = donnees.communes[code];
  vider(hote);
  if (!c) {
    hote.appendChild(messageEtat(
      "Cette commune ne déclare aucun compte 6574 sur la période publiée " +
      "(2010-2025). 107 communes sur 34 936 sont dans ce cas : elles n'ont " +
      "jamais fait servir ce compte, ou n'existaient pas encore.", "info"));
    return;
  }
  var pop = 0;
  var ref = Index.communes();
  if (ref) {
    var i = ref.ids.indexOf(code);
    if (i >= 0) pop = ref.p[i];
  }
  dessinerFiche(code, c, pop);
  document.title = c.n + " — ce que ma commune verse aux associations";
}

// --- démarrage --------------------------------------------------------------

function appliquerEtatDepuisURL() {
  var u = lireEtat();
  if (u.insee) {
    $("#cherche-commune").value = "";
    afficher(u.insee);
  } else {
    vider($("#fiche-commune"));
    $("#accueil-commune").hidden = false;
    document.title = "Ma commune — Dons publics aux associations";
  }
  $("#accueil-commune").hidden = !!u.insee;
}

async function demarrer() {
  meta = await chargerGz("data/aggregates/meta.json.gz");
  denominateur = await chargerGz("data/aggregates/denominateur.json.gz")
    .catch(function () { return null; });

  if (denominateur && denominateur.resume && denominateur.resume.commune) {
    var c = denominateur.resume.commune;
    var r = $("#resume-national");
    vider(r);
    [[fmtNombre.format(c.declarants), "communes déclarent un compte 6574 à la DGFiP, sur " +
      fmtNombre.format(c.univers)],
     [euros(c.declare_eur), "mandatés aux associations entre " + c.exercices[0] +
      " et " + c.exercices[1]],
     [euros(c.site_vote_eur), "que le site connaît nommément, soit " +
      pourcent(c.part_connue_pct)]
    ].forEach(function (paire) {
      var b = el("div", "compteur");
      b.appendChild(el("span", "valeur", paire[0]));
      b.appendChild(el("span", "etiquette", paire[1]));
      r.appendChild(b);
    });
  }

  var couv = await chargerGz("data/aggregates/couverture.json.gz")
    .catch(function () { return null; });
  var cc = couv && couv.resume && couv.resume.commune;
  if (cc) {
    var a = $("#nb-publiantes"), z = $("#nb-univers");
    if (a) a.textContent = fmtNombre.format(cc.avec_donnees);
    if (z) z.textContent = fmtNombre.format(cc.univers);
  }

  var input = $("#cherche-commune");
  Index.armerPrechargement(input);
  await Index.chargerRang1();
  Suggest.poser(input, {
    genres: ["commune"],
    limite: 10,
    choisir: function (s) {
      ecrireEtat({ insee: s.code }, true);
      $("#accueil-commune").hidden = true;
      afficher(s.code);
    }
  });
  window.addEventListener("popstate", appliquerEtatDepuisURL);
  appliquerEtatDepuisURL();
  Lexique.poser(document);
  window.__DATA_READY = true;
}

demarrer().catch(function (e) {
  var hote = $("#fiche-commune");
  vider(hote);
  hote.appendChild(messageErreur("Le site n'a pas pu charger ses données (" +
    e.message + ").", function () { location.reload(); }));
});

enregistrerServiceWorker();
