/* ============================================================================
 * Le lexique — les mots du site, expliqués là où ils s'affichent.
 * ----------------------------------------------------------------------------
 * « Échelon », « voté », « payé », « mandaté », « compte 6574 », « cumul
 * d'échelons », « dépendance » : chacun de ces mots est employé comme
 * ÉTIQUETTE D'INTERFACE, et chacun n'est défini qu'ailleurs, dans le corps
 * d'un paragraphe d'une autre page. Un lecteur qui ne les connaît pas n'a
 * aucun moyen de les apprendre au moment où il en a besoin.
 *
 * Une définition, un seul endroit dans le code. Les pages ne font que poser
 * `data-mot` sur un terme ; ce module l'habille et l'ouvre au clic comme au
 * clavier.
 * ========================================================================= */

"use strict";

import { el, vider } from "./commun.js";

export var MOTS = {
  echelon: ["Échelon",
    "Un niveau d'administration publique : l'État, ses opérateurs (agences " +
    "à budget propre), la région, le département, l'intercommunalité, la " +
    "commune. Le site en distingue sept, la septième étant « donateur non " +
    "identifié » — parce qu'attribuer d'office un versement à l'État quand la " +
    "source ne dit pas qui verse serait inventer."],
  cumul: ["Cumul d'échelons",
    "Le nombre de niveaux différents qui financent la même association. Une " +
    "association financée à la fois par sa commune, son département et l'État " +
    "en cumule trois. C'est une question qu'aucun guichet ne sait poser : " +
    "chaque administration ne connaît que ses propres versements."],
  dependance: ["Dépendance",
    "La part du financement total qui vient d'un seul financeur. Une " +
    "association financée à 95 % par une seule collectivité ne vit pas la même " +
    "vie qu'une association qui en a cinq. Le site ne calcule cette part " +
    "qu'au-delà de 10 000 € reçus : sur trois cents euros touchés une fois, " +
    "elle ne voudrait rien dire."],
  vote: ["Voté",
    "Le montant qu'une collectivité a DÉCIDÉ d'attribuer — la délibération. " +
    "C'est ce qui entre dans les totaux du site."],
  paye: ["Payé",
    "Le montant réellement décaissé, tel qu'il figure au compte administratif. " +
    "Le site l'affiche à côté du voté et ne l'y ajoute JAMAIS : quand une " +
    "collectivité publie les deux, c'est le même argent vu deux fois."],
  mandate: ["Mandaté",
    "L'ordre de payer donné au comptable public. C'est la mesure des balances " +
    "comptables de la DGFiP, et c'est pourquoi elle ne coïncide jamais " +
    "exactement avec le voté : ce ne sont pas les mêmes euros au même moment."],
  compte6574: ["Compte 6574",
    "La ligne comptable « subventions de fonctionnement aux associations et " +
    "autres personnes de droit privé ». Toutes les collectivités la déclarent " +
    "à la DGFiP, qu'elles fassent de l'open data ou non — d'où l'intérêt : " +
    "elle dit combien d'argent échappe au site. Elle ne nomme aucun " +
    "bénéficiaire, et n'est donc jamais additionnée aux versements nominatifs."],
  agregat: ["Ligne agrégée",
    "Un total publié par la source (un poste budgétaire, un « TOTAL 2019 ») " +
    "plutôt qu'une subvention à une association nommée. Affiché, jamais " +
    "sommé avec le détail — ce serait compter deux fois."],
  prestation: ["Prestation facturée",
    "La collectivité achète un service à l'association : il y a une " +
    "contrepartie. Ce n'est pas un soutien, donc pas un don, donc hors des " +
    "totaux — mais la ligne reste visible."],
  quarantaine: ["Quarantaine d'unité",
    "Des montants dont l'unité est manifestement fausse à la source (des " +
    "centimes lus comme des euros, une virgule décalée). Le site les met de " +
    "côté au lieu de les corriger : savoir qu'un chiffre est faux ne dit pas " +
    "quel est le vrai, et réécrire un montant publié par une administration " +
    "n'est pas notre rôle."]
};

var ouvert = null;

function fermer() {
  if (ouvert) {
    ouvert.bulle.remove();
    ouvert.terme.setAttribute("aria-expanded", "false");
    ouvert = null;
  }
}

function ouvrir(terme, cle) {
  var def = MOTS[cle];
  if (!def) return;
  var dejaLa = ouvert && ouvert.terme === terme;
  fermer();
  if (dejaLa) return;
  var bulle = el("span", "bulle-lexique");
  bulle.setAttribute("role", "dialog");
  bulle.setAttribute("aria-label", def[0]);
  bulle.appendChild(el("b", null, def[0]));
  bulle.appendChild(el("span", null, def[1]));
  var f = el("button", "ferme-bulle", "×");
  f.type = "button";
  f.setAttribute("aria-label", "Fermer");
  f.addEventListener("click", fermer);
  bulle.appendChild(f);
  terme.appendChild(bulle);
  terme.setAttribute("aria-expanded", "true");
  ouvert = { terme: terme, bulle: bulle };
}

/** Habille tous les `[data-mot]` d'une racine. Idempotent : rappelable après
 *  chaque rendu sans dupliquer les écouteurs. */
export function poser(racine) {
  var termes = (racine || document).querySelectorAll("[data-mot]:not([data-lexique])");
  Array.prototype.forEach.call(termes, function (t) {
    var cle = t.getAttribute("data-mot");
    if (!MOTS[cle]) return;
    t.setAttribute("data-lexique", "1");
    t.setAttribute("tabindex", "0");
    t.setAttribute("role", "button");
    t.setAttribute("aria-expanded", "false");
    t.setAttribute("aria-label", t.textContent + " — voir la définition");
    t.addEventListener("click", function (e) { e.stopPropagation(); ouvrir(t, cle); });
    t.addEventListener("keydown", function (e) {
      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); e.stopPropagation(); ouvrir(t, cle); }
    });
  });
}

/** Fabrique un terme défini, pour le contenu construit en JavaScript. */
export function mot(cle, texte) {
  var s = el("span", "mot-lexique", texte || (MOTS[cle] ? MOTS[cle][0] : cle));
  s.setAttribute("data-mot", cle);
  return s;
}

document.addEventListener("click", function (e) {
  if (ouvert && !ouvert.terme.contains(e.target)) fermer();
});
document.addEventListener("keydown", function (e) { if (e.key === "Escape") fermer(); });
