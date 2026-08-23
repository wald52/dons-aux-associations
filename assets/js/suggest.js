/* ============================================================================
 * Le champ unique — « une association, une commune, un département ».
 * ----------------------------------------------------------------------------
 * Un site de données publiques n'a pas à demander au visiteur de choisir
 * d'abord une rubrique. Il tape un nom, le site trouve de quoi il s'agit et
 * l'emmène au bon endroit.
 *
 * Trois familles, distinguées par une pastille et jamais mélangées dans le
 * classement : une COMMUNE (ce qu'elle verse), un DÉPARTEMENT ou une RÉGION
 * (ce que ses associations reçoivent), une ASSOCIATION (qui la finance).
 * Ces points de vue sont opposés — l'un regarde le payeur, l'autre le
 * bénéficiaire — et le libellé de chaque suggestion le dit.
 * ========================================================================= */

"use strict";

import { el, vider, euros, fmtNombre, plier } from "./commun.js";
import * as Index from "./index-recherche.js";

var GENRES = {
  association: ["Association", "qui la finance"],
  commune: ["Commune", "ce qu'elle verse"],
  departement: ["Département", "ce que ses associations reçoivent"],
  region: ["Région", "ce que ses associations reçoivent"]
};

/** Installe l'autocomplétion sur un `<input>`.
 *
 *  `options.genres`  familles proposées (par défaut toutes) ;
 *  `options.choisir` appelée avec la suggestion retenue ;
 *  `options.limite`  nombre de suggestions.
 */
export function poser(input, options) {
  options = options || {};
  var genres = options.genres || ["association", "commune", "departement", "region"];
  var limite = options.limite || 8;

  var liste = el("ul", "suggestions");
  liste.id = input.id + "-suggestions";
  liste.setAttribute("role", "listbox");
  liste.hidden = true;
  input.parentNode.appendChild(liste);
  input.setAttribute("role", "combobox");
  input.setAttribute("aria-autocomplete", "list");
  input.setAttribute("aria-expanded", "false");
  input.setAttribute("aria-controls", liste.id);
  input.setAttribute("autocomplete", "off");

  var courant = [];
  var actif = -1;

  function fermer() {
    liste.hidden = true;
    input.setAttribute("aria-expanded", "false");
    input.removeAttribute("aria-activedescendant");
    actif = -1;
  }

  function marquer(i) {
    Array.prototype.forEach.call(liste.children, function (li, k) {
      li.classList.toggle("actif", k === i);
      if (k === i) input.setAttribute("aria-activedescendant", li.id);
    });
    actif = i;
    if (i >= 0 && liste.children[i]) liste.children[i].scrollIntoView({ block: "nearest" });
  }

  function retenir(s) {
    fermer();
    if (options.choisir) options.choisir(s);
  }

  function dessiner(suggestions) {
    courant = suggestions;
    vider(liste);
    if (!suggestions.length) { fermer(); return; }
    suggestions.forEach(function (s, i) {
      var li = el("li");
      li.id = liste.id + "-" + i;
      li.setAttribute("role", "option");
      li.setAttribute("aria-selected", "false");
      var g = GENRES[s.genre] || ["", ""];
      li.appendChild(el("span", "pastille pastille-" + s.genre, g[0]));
      li.appendChild(el("span", "suggestion-nom", s.nom));
      var d = [];
      if (s.genre === "commune") {
        if (s.dep) d.push("dép. " + s.dep);
        if (s.population) d.push(fmtNombre.format(s.population) + " hab.");
      } else if (s.genre === "association") {
        if (s.dep) d.push("dép. " + s.dep);
        if (s.montant) d.push(euros(s.montant) + " reçus");
      }
      d.push(g[1]);
      li.appendChild(el("span", "suggestion-detail", d.join(" · ")));
      li.addEventListener("mousedown", function (e) { e.preventDefault(); retenir(s); });
      li.addEventListener("mouseenter", function () { marquer(i); });
      liste.appendChild(li);
    });
    liste.hidden = false;
    input.setAttribute("aria-expanded", "true");
    marquer(-1);
  }

  async function proposer() {
    var q = plier(input.value);
    if (q.length < 2) { fermer(); return; }
    await Index.chargerRang1();
    var out = [];
    if (genres.indexOf("commune") >= 0 || genres.indexOf("departement") >= 0) {
      out = Index.chercherTerritoires(q, limite).filter(function (t) {
        return genres.indexOf(t.genre) >= 0;
      });
    }
    if (genres.indexOf("association") >= 0) {
      var reste = limite - out.length;
      if (reste > 0) {
        Index.chercherAssociations(q, {}, reste).resultats.forEach(function (f) {
          out.push({
            genre: "association", nom: f.nom, dep: f.dep,
            montant: f.montant, rang: f.rang, bid: f.bid
          });
        });
      }
    }
    dessiner(out);
  }

  var minuteur = null;
  input.addEventListener("input", function () {
    clearTimeout(minuteur);
    minuteur = setTimeout(proposer, 120);
  });
  input.addEventListener("focus", function () { Index.chargerRang1(); });
  input.addEventListener("blur", function () { setTimeout(fermer, 120); });
  input.addEventListener("keydown", function (e) {
    if (liste.hidden) {
      if (e.key === "ArrowDown") { proposer(); e.preventDefault(); }
      return;
    }
    if (e.key === "ArrowDown") { e.preventDefault(); marquer(Math.min(actif + 1, courant.length - 1)); }
    else if (e.key === "ArrowUp") { e.preventDefault(); marquer(Math.max(actif - 1, -1)); }
    else if (e.key === "Enter") {
      if (actif >= 0) { e.preventDefault(); retenir(courant[actif]); }
      else if (options.valider) { e.preventDefault(); fermer(); options.valider(input.value); }
    } else if (e.key === "Escape") { fermer(); }
  });

  return { fermer: fermer, proposer: proposer };
}

/** Où mène une suggestion. Écrit ici pour que les deux champs du site — celui
 *  de l'accueil et celui de « Ma commune » — n'inventent pas deux routages. */
export async function adresseDe(s) {
  if (s.genre === "commune") return "commune.html#insee=" + s.code;
  if (s.genre === "departement") return "index.html#dep=" + s.code;
  if (s.genre === "region") return "index.html#region=" + s.code;
  var bid = s.bid || await Index.identifiantDuRang(s.rang);
  return "recherche.html#a=" + bid;
}
