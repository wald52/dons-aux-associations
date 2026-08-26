/* ============================================================================
 * Recherche croisée — « qui finance cette association ? »
 * ----------------------------------------------------------------------------
 * Le champ de saisie est actif IMMÉDIATEMENT. L'index arrive derrière et
 * complète les résultats en place. La version précédente faisait l'inverse :
 * elle cachait toute la page derrière une phrase grise le temps de télécharger
 * 34,2 Mo de moteur SQL puis 17,7 Mo d'index — 4,5 s en local, sans latence.
 *
 * Tout s'exécute dans le navigateur, aucune requête n'est envoyée à un serveur
 * applicatif : ce qu'on cherche ici ne regarde personne.
 * ========================================================================= */

"use strict";

import {
  $, el, vider, euros, fmtNombre, pluriel, plier, chargerGz, NIVEAUX,
  CAS_DANS_LES_TOTAUX, MOTIFS, motifHorsTotaux,
  lireEtat, ecrireEtat, messageEtat, messageErreur, jauge, enregistrerServiceWorker
} from "./commun.js";
import * as Index from "./index-recherche.js";
import * as Lexique from "./lexique.js";
import * as Export from "./export.js";

var meta = null;
var stats = null;
var couverture = null;
var etat = { q: "", dep: "", cumul: "", dependance: "", a: null };
var dernierResultat = null;

function nomDep(code) {
  if (!code) return null;
  var d = meta && meta.departements.valeurs[code];
  return d ? d[0] + " (" + code + ")" : code;
}

// --- liste de résultats -----------------------------------------------------

function badgeEchelons(f) {
  if (!f.ech || f.ech < 2) return null;
  var b = el("span", "badge" + (f.ech >= 3 ? " fort" : ""));
  b.appendChild(el("b", null, f.ech + " échelons"));
  // Les libellés sont ÉCRITS, pas cachés dans un `title` : au doigt comme au
  // clavier, un `title` n'existe pas.
  b.appendChild(el("span", "badge-detail",
    (f.echelons || []).map(function (e) { return NIVEAUX[e] || e; }).join(" · ")));
  return b;
}

function ligneResultat(f) {
  var li = el("li", "resultat");
  li.tabIndex = 0;
  li.setAttribute("role", "button");
  li.appendChild(el("span", "nom", f.nom));
  li.appendChild(el("span", "montant", euros(f.montant)));
  var d = el("span", "detail");
  var bouts = [nomDep(f.dep) || "département inconnu"];
  if (f.nbv) bouts.push(pluriel(f.nbv, "versement"));
  if (f.a0) bouts.push(f.a0 === f.a1 ? String(f.a0) : f.a0 + "–" + f.a1);
  d.appendChild(document.createTextNode(bouts.join(" · ") + " "));
  var b = badgeEchelons(f);
  if (b) d.appendChild(b);
  li.appendChild(d);

  function ouvrir() { allerVersFiche(f); }
  li.addEventListener("click", ouvrir);
  li.addEventListener("keydown", function (e) {
    if (e.key === "Enter" || e.key === " ") { e.preventDefault(); ouvrir(); }
  });
  return li;
}

async function allerVersFiche(f) {
  var bid = f.bid || await Index.identifiantDuRang(f.rang);
  etat.a = bid;
  ecrireEtat(etat, true);
  await montrerFiche(bid);
}

function filtresActifs() {
  var actifs = [];
  if (etat.dep) actifs.push(["dep", "Département : " + nomDep(etat.dep)]);
  if (etat.cumul) actifs.push(["cumul", etat.cumul + " échelons ou plus"]);
  if (etat.dependance) actifs.push(["dependance", etat.dependance + " % d'un seul financeur"]);
  return actifs;
}

function barreFiltres(hote) {
  var actifs = filtresActifs();
  if (!actifs.length) return;
  var bloc = el("div", "puces-filtres");
  bloc.appendChild(el("span", "puces-titre", "Filtres actifs :"));
  actifs.forEach(function (a) {
    var p = el("button", "puce-filtre", a[1] + " ✕");
    p.type = "button";
    p.setAttribute("aria-label", "Retirer le filtre « " + a[1] + " »");
    p.addEventListener("click", function () {
      etat[a[0]] = "";
      $("#filtre-" + (a[0] === "dep" ? "dep" : a[0])).value = "";
      rafraichir(true);
    });
    bloc.appendChild(p);
  });
  hote.appendChild(bloc);
}

function chercher() {
  var hote = $("#resultats");
  var q = plier(etat.q);
  vider(hote);
  barreFiltres(hote);

  if (q.length > 0 && q.length < 3 && !etat.cumul && !etat.dependance) {
    hote.appendChild(messageEtat("Encore une lettre ou deux — la recherche part de trois caractères.", "conseil"));
    return;
  }
  if (!q && !etat.cumul && !etat.dependance && !etat.dep) { montrerCumuls(hote); return; }

  var res = Index.chercherAssociations(q, {
    dep: etat.dep,
    cumul: etat.cumul ? Number(etat.cumul) : 0,
    dependance: etat.dependance ? Number(etat.dependance) : 0
  }, 50);
  dernierResultat = res;

  if (!res.total) {
    var vide = el("div", "etat-vide");
    vide.appendChild(el("p", null,
      etat.q ? "Aucune association ne porte ce nom dans les données du site."
             : "Aucune association ne répond à ces filtres."));
    var conseils = el("ul", "conseils");
    if (etat.q) {
      conseils.appendChild(el("li", null,
        "Essayez un mot seul : les noms publiés sont souvent abrégés " +
        "(« RESTOS DU COEUR », pas « Les Restaurants du Cœur »)."));
    }
    if (filtresActifs().length) {
      var li = el("li");
      li.appendChild(document.createTextNode("Ou "));
      var b = el("button", "bouton-lien", "retirez les filtres");
      b.type = "button";
      b.addEventListener("click", reinitialiser);
      li.appendChild(b);
      li.appendChild(document.createTextNode("."));
      conseils.appendChild(li);
    }
    var c = couverture && couverture.resume && couverture.resume.commune;
    conseils.appendChild(el("li", null,
      "Une association absente n'est pas une association sans subvention : " +
      (c ? "seules " + fmtNombre.format(c.avec_donnees) + " communes sur " +
           fmtNombre.format(c.univers) + " publient les leurs."
         : "la plupart des communes ne publient pas les leurs.")));
    vide.appendChild(conseils);
    hote.appendChild(vide);
    return;
  }

  var entete = el("p", "compte-resultats");
  entete.appendChild(el("b", null, fmtNombre.format(res.total) +
    (res.total > 1 ? " associations trouvées" : " association trouvée")));
  if (res.total > res.resultats.length) {
    entete.appendChild(document.createTextNode(
      " — les " + res.resultats.length + " premières par montant reçu."));
  }
  if (res.source === "partiel") {
    entete.appendChild(el("span", "note-partielle",
      " Recherche sur les plus gros bénéficiaires seulement ; l'index complet" +
      (stats ? " (" + fmtNombre.format(stats.beneficiaires) + ")" : "") +
      " finit de charger, et les résultats se compléteront seuls."));
  }
  hote.appendChild(entete);
  if (res.source === "complet") hote.appendChild(exportResultats());

  var ul = el("ul", "classement");
  res.resultats.forEach(function (f) { ul.appendChild(ligneResultat(f)); });
  hote.appendChild(ul);
  Lexique.poser(hote);
}

var PLAFOND_EXPORT = 20000;

/** L'export de la liste. Il porte TOUS les résultats, pas les cinquante
 *  affichés — mais il lui faut un identifiant par ligne, et ceux-ci vivent
 *  dans des blocs séparés (835 par fichier) pour ne pas alourdir de 2,7 Mo
 *  chaque recherche. D'où l'avancement pendant qu'ils arrivent. */
function exportResultats() {
  var q = plier(etat.q);
  var filtres = {
    dep: etat.dep,
    cumul: etat.cumul ? Number(etat.cumul) : 0,
    dependance: etat.dependance ? Number(etat.dependance) : 0
  };
  var complet = Index.chercherAssociations(q, filtres, PLAFOND_EXPORT);
  var tronque = complet.total > complet.resultats.length;
  return Export.blocExport(
    "Télécharger " + (tronque ? "les " + fmtNombre.format(PLAFOND_EXPORT) + " premières"
                              : "ces " + fmtNombre.format(complet.total)) + " associations (CSV)",
    (tronque ? "Au-delà de " + fmtNombre.format(PLAFOND_EXPORT) + " lignes, l'export " +
       "s'arrête — précisez la recherche pour tout obtenir. " : "") +
    "Une ligne par association, avec le lien vers sa fiche.",
    async function (avancement) {
      var lignes = [];
      for (var i = 0; i < complet.resultats.length; i++) {
        var f = complet.resultats[i];
        var bid = f.bid || await Index.identifiantDuRang(f.rang);
        lignes.push([
          f.nom, bid, f.dep || "", nomDep(f.dep) || "",
          Export.montant(f.montant), f.nbv || "", f.ech || "",
          (f.echelons || []).map(function (e) { return NIVEAUX[e] || e; }).join(" + "),
          f.a0 || "", f.a1 || "", f.part == null ? "" : f.part,
          location.origin + location.pathname + "#a=" + bid
        ]);
        if (i % 400 === 0) avancement(i / complet.resultats.length);
      }
      return {
        nom: Export.nomFichier("associations", etat.q || "toutes",
                               etat.dep ? "dep" + etat.dep : "",
                               etat.cumul ? etat.cumul + "echelons" : ""),
        texte: Export.csv(
          ["nom", "identifiant", "departement_code", "departement",
           "dons_votes_eur", "nb_versements", "nb_echelons", "echelons",
           "annee_min", "annee_max", "part_principal_financeur_pct", "lien"],
          lignes)
      };
    });
}

function montrerCumuls(hote) {
  var res = Index.chercherAssociations("", { cumul: 3 }, 30);
  var intro = el("div", "intro-cumuls");
  intro.appendChild(el("h2", null, "Financées par trois échelons ou plus"));
  var p = el("p", "sous-titre");
  p.appendChild(document.createTextNode(
    fmtNombre.format(nbCumuls) + " associations sont financées par au moins trois "));
  p.appendChild(Lexique.mot("echelon", "échelons"));
  p.appendChild(document.createTextNode(
    " publics différents — question qu'aucun guichet ne sait poser, chaque " +
    "administration ne connaissant que ses propres versements. Voici les " +
    "premières par montant reçu, ou cherchez une association par son nom."));
  intro.appendChild(p);
  hote.appendChild(intro);
  var ul = el("ul", "classement");
  res.resultats.forEach(function (f) { ul.appendChild(ligneResultat(f)); });
  hote.appendChild(ul);
  Lexique.poser(hote);
}

var nbCumuls = 9566;

// --- fiche d'une association ------------------------------------------------

async function montrerFiche(bid) {
  var fiche = $("#fiche");
  $("#resultats").hidden = true;
  $("#bloc-filtres").hidden = true;
  fiche.hidden = false;
  vider(fiche);
  fiche.appendChild(messageEtat("Ouverture de la fiche…", "chargement"));

  var donnees;
  try { donnees = await Index.chargerFiche(bid); }
  catch (e) {
    vider(fiche);
    fiche.appendChild(messageErreur(
      "La fiche n'a pas pu être chargée.", function () { montrerFiche(bid); }));
    fiche.appendChild(lienRetour());
    return;
  }
  vider(fiche);
  if (!donnees) {
    fiche.appendChild(messageEtat(
      "Cette association n'existe pas dans l'index. Le lien vient peut-être " +
      "d'une version antérieure des données.", "info"));
    fiche.appendChild(lienRetour());
    return;
  }
  dessinerFiche(fiche, donnees.resume, donnees.versements);
}

function lienRetour() {
  var retour = el("button", "retour", "← Retour aux résultats");
  retour.type = "button";
  retour.addEventListener("click", function () { history.back(); });
  return retour;
}

function dessinerFiche(fiche, b, vers) {
  ficheCourante = b;
  fiche.appendChild(lienRetour());
  fiche.appendChild(el("h2", null, b.nom));

  var ident = [];
  if (b.siren) ident.push("SIREN " + b.siren);
  // Le RNA vient parfois de SIRENE et non de la source : on le dit, plutôt que
  // de laisser croire que le publieur l'avait donné.
  if (b.rna) ident.push("RNA " + b.rna + (b.rna_de_insee ? " (INSEE)" : ""));
  if (b.dep) ident.push(nomDep(b.dep));
  fiche.appendChild(el("p", "sous-titre", ident.join(" · ") ||
    "Sans identifiant national — reconnue par son nom et son département."));

  // La FAMILLE JURIDIQUE, écrite en toutes lettres sous le nom. Une fondation
  // d'entreprise et une association de quartier comptent toutes deux dans les
  // totaux du site, mais ce ne sont pas la même chose : les afficher sans le
  // dire serait exact et trompeur.
  if (b.famille) {
    var hors = b.famille.indexOf("hors périmètre") === 0;
    var inconnue = b.famille === "nature non vérifiée";
    var fam = el("p", "famille-juridique" + (hors ? " hors-perimetre" : ""));
    fam.appendChild(el("span", "puce-famille" +
      (hors ? " hors" : inconnue ? " incertaine" : "")));
    if (hors) {
      fam.appendChild(document.createTextNode(
        "Ce bénéficiaire n'est ni une association ni une fondation."));
      fam.appendChild(el("span", "precision",
        " Le répertoire SIRENE de l'INSEE lui donne une autre forme juridique — " +
        "entreprise, établissement public, syndicat. Ses montants restent " +
        "consultables mais ne comptent dans aucun total du site."));
    } else if (inconnue) {
      fam.appendChild(document.createTextNode("Forme juridique non vérifiée"));
      fam.appendChild(el("span", "precision",
        " — ce bénéficiaire n'a pas d'identifiant qui permette de la vérifier ; " +
        "ses versements restent comptés."));
    } else {
      fam.appendChild(document.createTextNode("Forme juridique : " + b.famille));
      fam.appendChild(el("span", "precision",
        " — d'après le répertoire SIRENE de l'INSEE"));
    }
    fiche.appendChild(fam);
  }

  var stats = el("div", "compteurs");
  var cases = [
    [euros(b.montant), "reçus au total"],
    [fmtNombre.format(b.nbv), b.nbv > 1 ? "versements" : "versement"],
    [String(b.ech), "échelon" + (b.ech > 1 ? "s" : "") + " financeur" + (b.ech > 1 ? "s" : "")],
    [String(b.nbd), "donateur" + (b.nbd > 1 ? "s" : "") + " distinct" + (b.nbd > 1 ? "s" : "")]
  ];
  if (b.part != null) cases.push([Math.round(b.part) + " %", "du principal financeur"]);
  cases.forEach(function (c) {
    var d = el("div", "compteur");
    d.appendChild(el("span", "valeur", c[0]));
    d.appendChild(el("span", "etiquette", c[1]));
    stats.appendChild(d);
  });
  fiche.appendChild(stats);

  if (b.ecarte) {
    var av = el("p", "avertissement");
    av.appendChild(el("b", null, "Montants mis de côté. "));
    av.appendChild(document.createTextNode(euros(b.ecarte) +
      " supplémentaires figurent dans la source mais sont exclus des totaux : "));
    av.appendChild(Lexique.mot("quarantaine", "leur unité est douteuse"));
    av.appendChild(document.createTextNode(". Détail dans "));
    var l = el("a", null, "Sources & méthode");
    l.href = "methode.html";
    av.appendChild(l);
    av.appendChild(document.createTextNode("."));
    fiche.appendChild(av);
  }

  // --- trajectoire et financeurs -------------------------------------------
  // Ne comptent que les DONS VOTÉS — la règle des totaux du site. Y mêler une
  // prestation facturée ou une exécution budgétaire ferait une courbe qui ne
  // veut rien dire.
  var parAn = {}, parDonateur = {};
  vers.forEach(function (v) {
    if (v.cas !== CAS_DANS_LES_TOTAUX || v.montant == null) return;
    var y = v.annee == null ? "?" : String(v.annee);
    parAn[y] = (parAn[y] || 0) + v.montant;
    var k = v.donateur || "—";
    parDonateur[k] = parDonateur[k] || { total: 0, n: 0, niveau: v.niveau };
    parDonateur[k].total += v.montant;
    parDonateur[k].n++;
  });

  var annees = Object.keys(parAn).filter(function (y) { return y !== "?"; }).sort();
  if (annees.length > 1) {
    fiche.appendChild(el("h3", null, "Trajectoire"));
    fiche.appendChild(el("p", "sous-titre",
      "Dons votés, année par année. Une année absente n'est pas un zéro : elle " +
      "peut aussi vouloir dire que le financeur n'a rien publié cette année-là."));
    var max = Math.max.apply(null, annees.map(function (y) { return parAn[y]; }));
    var traj = el("div", "trajectoire");
    annees.forEach(function (y) {
      var ligne = el("div", "annee");
      ligne.appendChild(el("span", "an", y));
      var barre = el("div", "barre");
      var rempli = el("i");
      rempli.style.width = Math.max(1, Math.round(parAn[y] / max * 100)) + "%";
      barre.appendChild(rempli);
      ligne.appendChild(barre);
      ligne.appendChild(el("span", "montant", euros(parAn[y])));
      traj.appendChild(ligne);
    });
    fiche.appendChild(traj);
  }

  fiche.appendChild(el("h3", null, "Financeurs"));
  var ulD = el("ul", "classement");
  Object.keys(parDonateur)
    .sort(function (a, c) { return parDonateur[c].total - parDonateur[a].total; })
    .forEach(function (k) {
      var d = parDonateur[k];
      var li = el("li");
      var nom = el("span", "nom");
      nom.appendChild(document.createTextNode(k + " "));
      nom.appendChild(el("b", "badge", NIVEAUX[d.niveau] || d.niveau));
      li.appendChild(nom);
      li.appendChild(el("span", "montant", euros(d.total)));
      li.appendChild(el("span", "detail", pluriel(d.n, "versement")));
      ulD.appendChild(li);
    });
  fiche.appendChild(ulD);

  fiche.appendChild(tableauVersements(vers));
  Lexique.poser(fiche);
}

var ficheCourante = null;

function tableauVersements(vers) {
  var bloc = el("div", "bloc-versements");
  bloc.appendChild(el("h3", null, "Versements (" + fmtNombre.format(vers.length) + ")"));

  // Chaque ligne hors totaux porte sa raison, ÉCRITE. Elle était auparavant
  // dans un attribut `title` : invisible au doigt, invisible au clavier,
  // invisible à l'impression.
  var raisons = {};
  vers.forEach(function (v) {
    var m = motifHorsTotaux(v);
    if (m) raisons[m] = true;
  });
  var cles = Object.keys(raisons);
  if (cles.length) {
    var legende = el("div", "legende-ecarte");
    legende.appendChild(el("b", null, "Les montants en gris ne comptent pas dans les totaux."));
    var ul = el("ul");
    cles.forEach(function (r) { ul.appendChild(el("li", null, r)); });
    legende.appendChild(ul);
    bloc.appendChild(legende);
  }

  bloc.appendChild(Export.blocExport(
    "Télécharger les " + fmtNombre.format(vers.length) + " versements (CSV)",
    "Le fichier porte tous les versements, pas seulement ceux affichés. Chaque " +
    "montant est dans la colonne de sa catégorie — voté, payé, hors don, " +
    "agrégat, hors champ — pour qu'aucune somme n'additionne deux choses " +
    "différentes.",
    function () {
      return { nom: Export.nomFichier("versements", ficheCourante.nom,
                                      ficheCourante.benef_id),
               texte: Export.csvVersements(vers) };
    }));

  var LIMITE = 300;
  var env = el("div", "table-versements");
  var tbl = el("table");
  var thead = el("thead"), trh = el("tr");
  ["Année", "Donateur", "Objet", "Source", "Montant"].forEach(function (h) {
    trh.appendChild(el("th", null, h));
  });
  thead.appendChild(trh); tbl.appendChild(thead);
  var tbody = el("tbody");
  vers.slice(0, LIMITE).forEach(function (v) {
    var tr = el("tr");
    tr.appendChild(el("td", "num", v.annee == null ? "—" : String(v.annee)));
    var tdD = el("td");
    tdD.appendChild(document.createTextNode(v.donateur || "—"));
    if (v.programme) tdD.appendChild(el("span", "detail", v.programme));
    tr.appendChild(tdD);
    tr.appendChild(el("td", "objet", v.objet || "—"));

    // La source était sélectionnée par la requête et jamais affichée : la
    // promesse « chaque ligne porte l'identifiant de sa source » n'était pas
    // tenue à l'écran.
    var tdS = el("td", "source");
    if (v.url) {
      var a = el("a", null, v.source || "source");
      a.href = v.url;
      a.rel = "noopener";
      a.target = "_blank";
      tdS.appendChild(a);
    } else {
      tdS.appendChild(document.createTextNode(v.source || "—"));
    }
    tr.appendChild(tdS);

    var m = el("td", "num montant");
    if (v.montant != null) m.textContent = euros(v.montant);
    else if (v.montant_ecarte != null) {
      m.textContent = "(" + euros(v.montant_ecarte) + ")";
      m.classList.add("ecarte");
      m.appendChild(el("span", "raison", MOTIFS.quarantaine));
    } else m.textContent = "—";
    var motif = motifHorsTotaux(v);
    if (motif && v.montant != null) {
      m.classList.add("ecarte");
      m.appendChild(el("span", "raison", motif));
    }
    tr.appendChild(m);
    tbody.appendChild(tr);
  });
  tbl.appendChild(tbody);
  env.appendChild(tbl);
  if (vers.length > LIMITE) {
    env.appendChild(el("p", "sous-titre",
      "Les " + LIMITE + " premiers versements sont affichés, sur " +
      fmtNombre.format(vers.length) + ", du plus récent au plus ancien."));
  }
  bloc.appendChild(env);
  return bloc;
}

// --- contrôles --------------------------------------------------------------

function reinitialiser() {
  etat.q = ""; etat.dep = ""; etat.cumul = ""; etat.dependance = "";
  $("#q").value = "";
  $("#filtre-dep").value = "";
  $("#filtre-cumul").value = "";
  $("#filtre-dependance").value = "";
  rafraichir(false);
}

function rafraichir(empiler) {
  etat.a = null;
  $("#fiche").hidden = true;
  $("#resultats").hidden = false;
  $("#bloc-filtres").hidden = false;
  ecrireEtat(etat, !!empiler);
  chercher();
}

function anti_rebond(fn, ms) {
  var t = null;
  return function () { clearTimeout(t); t = setTimeout(fn, ms); };
}

function appliquerEtatDepuisURL() {
  var u = lireEtat();
  etat.q = u.q || "";
  etat.dep = u.dep || "";
  etat.cumul = u.cumul || "";
  etat.dependance = u.dependance || "";
  etat.a = u.a || null;
  $("#q").value = etat.q;
  $("#filtre-dep").value = etat.dep;
  $("#filtre-cumul").value = etat.cumul;
  $("#filtre-dependance").value = etat.dependance;
  if (etat.a) montrerFiche(etat.a);
  else {
    $("#fiche").hidden = true;
    $("#resultats").hidden = false;
    $("#bloc-filtres").hidden = false;
    chercher();
  }
}

async function demarrer() {
  meta = await chargerGz("data/aggregates/meta.json.gz");
  stats = await chargerGz("data/recherche/index-stats.json").catch(function () { return null; });
  if (stats) nbCumuls = stats.multi_echelons_3plus;
  // 1,2 Ko, pour une seule phrase — mais une phrase avec un chiffre, et un
  // chiffre écrit dans le HTML se périme en silence.
  couverture = await chargerGz("data/aggregates/couverture.json.gz")
    .catch(function () { return null; });
  if (stats) {
    var ps = $("#part-siren");
    if (ps) {
      ps.textContent = Math.round(100 * (stats.par_cle.S || 0) / stats.beneficiaires) + " %";
    }
  }

  var selDep = $("#filtre-dep");
  var deps = meta.departements.valeurs;
  Object.keys(deps).sort().forEach(function (code) {
    var o = document.createElement("option");
    o.value = code; o.textContent = code + " — " + deps[code][0];
    selDep.appendChild(o);
  });

  $("#q").addEventListener("input", anti_rebond(function () {
    etat.q = $("#q").value;
    rafraichir(false);
  }, 180));
  ["dep", "cumul", "dependance"].forEach(function (cle) {
    $("#filtre-" + cle).addEventListener("change", function (e) {
      etat[cle] = e.target.value;
      rafraichir(false);
    });
  });
  $("#reinitialiser").addEventListener("click", reinitialiser);
  window.addEventListener("popstate", appliquerEtatDepuisURL);
  Lexique.poser(document);

  // Le rang 1 (0,8 Mo) rend le champ utile tout de suite ; le rang 2 (5,1 Mo)
  // arrive derrière et complète les résultats sans que rien ne clignote.
  await Index.chargerRang1();
  appliquerEtatDepuisURL();

  // Qui arrive par un lien partagé vers UNE association n'a rien à faire de
  // l'index des 427 451 noms : on ne le lui télécharge qu'au moment où il
  // touche au champ de recherche. Qui arrive sur la liste, lui, le reçoit
  // tout de suite.
  if (etat.a) {
    ["focus", "input"].forEach(function (ev) {
      $("#q").addEventListener(ev, assurerIndexComplet, { once: true });
    });
    ["dep", "cumul", "dependance"].forEach(function (cle) {
      $("#filtre-" + cle).addEventListener("change", assurerIndexComplet, { once: true });
    });
  } else {
    await assurerIndexComplet();
  }
  window.__DATA_READY = true;
}

var indexCompletLance = false;

async function assurerIndexComplet() {
  if (indexCompletLance) return;
  indexCompletLance = true;
  var hote = $("#etat-index");
  var barre = jauge("Chargement de l'index complet" +
    (stats ? " — " + fmtNombre.format(stats.beneficiaires) + " bénéficiaires" : "") +
    ", une seule fois…");
  hote.appendChild(barre);
  try {
    await Index.chargerRang2(function (part) { barre.avancer(part); });
    vider(hote);
    if (!etat.a) chercher();
  } catch (e) {
    vider(hote);
    indexCompletLance = false;
    hote.appendChild(messageErreur(
      "L'index complet n'a pas pu être chargé ; la recherche porte pour l'instant " +
      "sur les plus gros bénéficiaires seulement.", function () {
        vider(hote); assurerIndexComplet();
      }));
  }
}

demarrer().catch(function (e) {
  var hote = $("#etat-index");
  vider(hote);
  hote.appendChild(messageErreur("Le site n'a pas pu charger ses données (" +
    e.message + ").", function () { location.reload(); }));
});

enregistrerServiceWorker();
