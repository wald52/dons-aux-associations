/* ============================================================================
 * Fonctions communes aux quatre pages.
 * ----------------------------------------------------------------------------
 * Écrites une fois, ici. Trois copies d'un formateur de montants finissent
 * toujours par diverger, et un site qui affiche « 1,2 M€ » d'un côté et
 * « 1 200 k€ » de l'autre a l'air de ne pas savoir ce qu'il compte.
 * ========================================================================= */

"use strict";

export function $(sel, racine) { return (racine || document).querySelector(sel); }

export function vider(el) { while (el.firstChild) el.removeChild(el.firstChild); }

export function el(tag, cls, texte) {
  var e = document.createElement(tag);
  if (cls) e.className = cls;
  if (texte != null) e.textContent = texte;
  return e;
}

export var fmtNombre = new Intl.NumberFormat("fr-FR");

/** Montant lisible. L'échelle descend jusqu'à l'euro : sur un site qui va du
 *  milliard au millier, arrondir en millions fait lire « 0 M€ » — donc
 *  « rien » — là où un village a versé 1 680 €. */
export function euros(v) {
  if (v == null) return "—";
  v = Number(v);
  var a = Math.abs(v);
  if (a >= 1e9) return (v / 1e9).toFixed(2).replace(".", ",") + " Md€";
  if (a >= 1e6) return (v / 1e6).toFixed(1).replace(".", ",") + " M€";
  if (a >= 1e4) return fmtNombre.format(Math.round(v / 1e3)) + " k€";
  return fmtNombre.format(Math.round(v)) + " €";
}

export function pluriel(n, mot, terminaison) {
  return fmtNombre.format(n) + " " + mot + (n > 1 ? (terminaison || "s") : "");
}

/** Pliage de recherche : sans accents, sans ponctuation, en capitales.
 *
 *  Applique au NOM AFFICHÉ, pas à la clé de rapprochement du pipeline. La
 *  version précédente comparait la saisie à `beneficiary_name_norm`, dont
 *  `normalize_name` retire les formes juridiques : taper « association des
 *  amis de X » ne trouvait donc pas une association qui s'affiche sous ce
 *  nom-là. On plie ce que le lecteur voit. */
export function plier(q) {
  return (q || "")
    // Les ligatures ne se décomposent PAS en NFD : « cœur » se pliait en
    // « c ur », si bien que taper « restos du coeur » — l'exemple donné par le
    // champ lui-même — ne trouvait rien. On les développe d'abord.
    .replace(/œ/g, "oe").replace(/Œ/g, "OE")
    .replace(/æ/g, "ae").replace(/Æ/g, "AE")
    .replace(/ß/g, "ss")
    .normalize("NFD").replace(/[̀-ͯ]/g, "")
    .replace(/[^a-zA-Z0-9]+/g, " ").trim().replace(/\s+/g, " ").toUpperCase();
}

/** Charge un .json.gz. Le décompresse dans le navigateur si le serveur ne
 *  l'a pas déjà fait — GitHub Pages sert ces fichiers tels quels. */
export async function chargerGz(url, surProgression) {
  var reponse = await fetch(url);
  if (!reponse.ok) throw new Error(url + " : " + reponse.status);
  var tampon;
  var total = Number(reponse.headers.get("content-length") || 0);
  if (surProgression && reponse.body && total) {
    var lecteur = reponse.body.getReader();
    var morceaux = [];
    var recu = 0;
    for (;;) {
      var pas = await lecteur.read();
      if (pas.done) break;
      morceaux.push(pas.value);
      recu += pas.value.length;
      surProgression(recu / total);
    }
    tampon = await new Blob(morceaux).arrayBuffer();
  } else {
    tampon = await reponse.arrayBuffer();
  }
  var octets = new Uint8Array(tampon);
  if (octets[0] === 0x1f && octets[1] === 0x8b) {
    if (typeof DecompressionStream === "undefined") {
      throw new Error("Ce navigateur ne sait pas décompresser gzip.");
    }
    var flux = new Blob([tampon]).stream()
      .pipeThrough(new DecompressionStream("gzip"));
    return JSON.parse(await new Response(flux).text());
  }
  return JSON.parse(new TextDecoder().decode(tampon));
}

export var NIVEAUX = {
  etat: "État", operateur: "Opérateur de l'État", region: "Région",
  departement: "Département", epci: "Intercommunalité", commune: "Commune",
  inconnu: "Donateur non identifié"
};

// --- état d'URL -------------------------------------------------------------
//
// Rien n'était partageable : ni un département, ni une année, ni une
// recherche, ni une association. Pour un site dont l'usage est « envoie ce
// lien à ton élu », c'était le manque le plus grave. Tout l'état de page tient
// désormais dans le fragment, en `clé=valeur` séparés par « & ».

export function lireEtat() {
  var etat = {};
  var frag = location.hash.replace(/^#/, "");
  frag.split("&").forEach(function (paire) {
    if (!paire) return;
    var i = paire.indexOf("=");
    if (i < 0) return;
    etat[decodeURIComponent(paire.slice(0, i))] = decodeURIComponent(paire.slice(i + 1));
  });
  return etat;
}

/** Écrit l'état dans l'adresse. `empiler` distingue une navigation (ouvrir une
 *  fiche : le Retour doit revenir en arrière) d'un simple réglage (changer une
 *  année : empiler ferait un historique de vingt entrées inutiles). */
export function ecrireEtat(etat, empiler) {
  var frag = Object.keys(etat)
    .filter(function (k) { return etat[k] != null && etat[k] !== ""; })
    .map(function (k) { return encodeURIComponent(k) + "=" + encodeURIComponent(etat[k]); })
    .join("&");
  var url = location.pathname + location.search + (frag ? "#" + frag : "#");
  if (empiler) history.pushState(null, "", url);
  else history.replaceState(null, "", url);
}

// --- états de page ----------------------------------------------------------
//
// Une même classe servait au chargement, à la validation, au résultat vide et
// à l'erreur fatale : quatre sens, une seule apparence. Chacun a maintenant la
// sienne, et l'erreur porte de quoi réessayer.

export function messageEtat(texte, genre) {
  var p = el("p", "etat etat-" + (genre || "info"));
  if (genre === "chargement") {
    p.appendChild(el("span", "tourniquet"));
    p.setAttribute("role", "status");
  }
  p.appendChild(document.createTextNode(texte));
  return p;
}

export function messageErreur(texte, reessayer) {
  var p = el("p", "etat etat-erreur");
  p.setAttribute("role", "alert");
  p.appendChild(document.createTextNode(texte + " "));
  if (reessayer) {
    var b = el("button", "bouton-lien", "Réessayer");
    b.type = "button";
    b.addEventListener("click", reessayer);
    p.appendChild(b);
  }
  return p;
}

/** Barre de progression déterminée, pour les chargements qui durent. Une
 *  phrase grise immobile ne dit pas si le site avance ou s'il est mort. */
export function jauge(texte) {
  var bloc = el("div", "jauge-chargement");
  bloc.setAttribute("role", "status");
  bloc.appendChild(el("span", "jauge-texte", texte));
  var piste = el("div", "jauge-piste");
  var barre = el("i");
  piste.appendChild(barre);
  bloc.appendChild(piste);
  bloc.avancer = function (part) {
    barre.style.width = Math.round(Math.min(1, Math.max(0, part)) * 100) + "%";
  };
  return bloc;
}

export function enregistrerServiceWorker() {
  if (!("serviceWorker" in navigator)) return;
  window.addEventListener("load", function () {
    navigator.serviceWorker.register("sw.js").catch(function () { /* sans effet */ });
  });
}
