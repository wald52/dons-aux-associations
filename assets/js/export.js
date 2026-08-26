/* ============================================================================
 * Les exports — sortir les chiffres du site sans leur faire dire autre chose.
 * ----------------------------------------------------------------------------
 * Le site passe son temps à ne pas additionner ce qui n'est pas de même
 * nature : voté et payé sont le même argent vu deux fois, une prestation
 * facturée n'est pas un don, une ligne agrégée n'est pas un versement. À
 * l'écran il le dit — montant grisé, motif écrit à côté.
 *
 * Dans un tableur, une colonne de nombres est une colonne de nombres, et la
 * première chose qu'on en fait est de la sommer. Un export à une seule colonne
 * de montants ferait donc sortir du site exactement le double compte que tout
 * le pipeline existe pour empêcher.
 *
 * D'où la règle de ce module : **un montant par colonne, une colonne par
 * case**. Ce sont les cinq cases de `verify.py` — « toute ligne tombe dans une
 * case et une seule ». Sommer une colonne devient juste par construction, et
 * sommer deux colonnes se voit, puisqu'elles ne portent pas le même nom.
 *
 * Format : CSV, séparateur « ; », BOM UTF-8, décimale française. Un seul
 * format fait correctement plutôt que trois à moitié : le public est français,
 * et un CSV séparé par virgules s'ouvre en une seule colonne dans Excel FR.
 * ========================================================================= */

"use strict";

import { el, plier, CAS_DANS_LES_TOTAUX, motifHorsTotaux, NIVEAUX } from "./commun.js";

/** Un champ contenant le séparateur, un guillemet ou une fin de ligne doit
 *  être protégé — les objets publiés par les collectivités contiennent les
 *  trois. */
function champ(v) {
  if (v == null) return "";
  var s = String(v);
  if (s.indexOf(";") >= 0 || s.indexOf('"') >= 0 || /[\r\n]/.test(s)) {
    return '"' + s.replace(/"/g, '""') + '"';
  }
  return s;
}

/** Un montant, en décimale française et sans séparateur de milliers : lu comme
 *  un nombre par Excel, LibreOffice et Numbers. Vide quand il n'y a pas de
 *  montant — un zéro publié n'est pas une absence. */
export function montant(v) {
  if (v == null) return "";
  return String(Math.round(v * 100) / 100).replace(".", ",");
}

export function csv(colonnes, lignes) {
  var out = ["﻿" + colonnes.map(champ).join(";")];
  lignes.forEach(function (l) { out.push(l.map(champ).join(";")); });
  return out.join("\r\n") + "\r\n";
}

/** Nom de fichier lisible et daté. */
export function nomFichier() {
  var bouts = Array.prototype.slice.call(arguments).filter(Boolean).map(function (b) {
    return plier(b).toLowerCase().replace(/ /g, "-").slice(0, 48);
  });
  var d = new Date();
  var jour = d.getFullYear() + "-" +
    ("0" + (d.getMonth() + 1)).slice(-2) + "-" + ("0" + d.getDate()).slice(-2);
  return bouts.join("-").replace(/-+/g, "-") + "-" + jour + ".csv";
}

export function telecharger(nom, texte) {
  var blob = new Blob([texte], { type: "text/csv;charset=utf-8" });
  var url = URL.createObjectURL(blob);
  var a = el("a");
  a.href = url;
  a.download = nom;
  document.body.appendChild(a);
  a.click();
  a.remove();
  // Sans révocation, le Blob reste en mémoire tant que l'onglet vit — et un
  // export de versements pèse quelques mégaoctets.
  setTimeout(function () { URL.revokeObjectURL(url); }, 4000);
}

/** Un bouton qui ne fabrique le fichier QU'AU CLIC.
 *
 *  Construire d'avance la chaîne d'un export de vingt mille lignes pour un
 *  bouton que personne ne cliquera, ce serait refaire le préchargement de
 *  l'index de suggestion qu'on a précisément retiré après l'avoir mesuré.
 *
 *  `fabrique` peut être asynchrone : l'export des résultats de recherche va
 *  chercher des blocs d'identifiants. */
export function bouton(libelle, fabrique) {
  var b = el("button", "bouton-export", libelle);
  b.type = "button";
  b.addEventListener("click", async function () {
    if (b.disabled) return;
    var initial = b.textContent;
    b.disabled = true;
    b.textContent = "Préparation…";
    try {
      var fichier = await fabrique(function (avancement) {
        b.textContent = "Préparation… " + Math.round(avancement * 100) + " %";
      });
      if (fichier) telecharger(fichier.nom, fichier.texte);
      b.textContent = initial;
    } catch (e) {
      b.textContent = "Échec — réessayer";
      console.error(e);
    } finally {
      b.disabled = false;
    }
  });
  return b;
}

/** Le bouton, plus la phrase qui dit ce que le fichier contient. Sans elle,
 *  l'écart entre les 300 lignes affichées et les 5 321 exportées passe pour un
 *  défaut. */
export function blocExport(libelle, note, fabrique) {
  var bloc = el("div", "bloc-export");
  bloc.appendChild(bouton(libelle, fabrique));
  if (note) bloc.appendChild(el("span", "note-export", note));
  return bloc;
}

// --- versements : une colonne de montant par catégorie ----------------------
//
// L'ordre de `CASES` et celui des colonnes `montant_*` DOIVENT correspondre :
// une case ajoutée d'un seul côté rangerait les montants dans la mauvaise
// colonne sans que rien ne le signale.
//
// `montant_hors_champ_insee_eur` est né avec la phase 15. Il tient à part ce
// que le registre SIRENE écarte — une entreprise, un établissement public —
// de ce que la SOURCE elle-même déclarait hors champ. Les deux sortent des
// totaux, mais pas sur la même autorité, et un tableur doit pouvoir les
// distinguer comme l'écran le fait.

var COLONNES_VERSEMENTS = [
  "annee", "donateur", "echelon", "programme", "objet",
  "montant_vote_eur", "montant_paye_eur", "montant_hors_don_eur",
  "montant_agrege_eur", "montant_hors_champ_eur",
  "montant_hors_champ_insee_eur", "montant_quarantaine_eur",
  "motif_hors_totaux", "nature_du_concours", "source", "url_source"
];

var CASES = ["vote", "paye", "hors_don", "agrege", "hors_champ",
             "hors_champ_insee"];

/** Une ligne de versement, son montant rangé dans la seule colonne qui lui
 *  revient. Le montant en quarantaine est à part : ce n'est pas un euro du
 *  site, c'est une valeur publiée dont l'unité est douteuse. */
function ligneVersement(v) {
  var montants = CASES.map(function (c) {
    return v.cas === c && v.montant != null ? montant(v.montant) : "";
  });
  return [
    v.annee == null ? "" : v.annee,
    v.donateur, NIVEAUX[v.niveau] || v.niveau, v.programme, v.objet
  ].concat(montants).concat([
    montant(v.montant_ecarte),
    motifHorsTotaux(v) || "",
    v.concours,
    v.source, v.url
  ]);
}

export function csvVersements(versements) {
  return csv(COLONNES_VERSEMENTS, versements.map(ligneVersement));
}

export { COLONNES_VERSEMENTS, CAS_DANS_LES_TOTAUX };
