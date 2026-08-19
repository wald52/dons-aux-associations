/* ============================================================================
 * Dons aux associations — application
 * ----------------------------------------------------------------------------
 * Phase 2 : le site sert un index, pas une base.
 *
 * Au chargement, il ne récupère que des agrégats déjà calculés (~103 Ko
 * gzippés) : de quoi peindre la carte et les compteurs immédiatement. Le
 * détail d'un département n'arrive qu'au clic, sous forme d'un fragment de
 * quelques kilo-octets. L'ancienne version chargeait 835 Mo de JavaScript
 * avant d'afficher quoi que ce soit.
 * ========================================================================= */

(function () {
  "use strict";

  var etat = {
    meta: null, cube: null, carte: null, top: null,
    annee: "toutes", niveau: "tous", departement: null,
    fragments: {}, onglet: "beneficiaires"
  };

  // --- utilitaires --------------------------------------------------------

  /** Charge un .json.gz. Le décompresse dans le navigateur si le serveur ne
   *  l'a pas déjà fait — GitHub Pages sert ces fichiers tels quels. */
  async function chargerGz(url) {
    var reponse = await fetch(url);
    if (!reponse.ok) throw new Error(url + " : " + reponse.status);
    var tampon = await reponse.arrayBuffer();
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

  var fmtEuros = new Intl.NumberFormat("fr-FR", {
    style: "currency", currency: "EUR", maximumFractionDigits: 0
  });
  var fmtNombre = new Intl.NumberFormat("fr-FR");

  function euros(v) {
    if (v == null) return "—";
    var a = Math.abs(v);
    if (a >= 1e9) return (v / 1e9).toFixed(1).replace(".", ",") + " Md€";
    if (a >= 1e6) return (v / 1e6).toFixed(1).replace(".", ",") + " M€";
    if (a >= 1e3) return Math.round(v / 1e3) + " k€";
    return fmtEuros.format(v);
  }

  function $(sel) { return document.querySelector(sel); }

  function vider(el) { while (el.firstChild) el.removeChild(el.firstChild); }

  // --- agrégation à la volée sur le cube ----------------------------------

  /** Somme [lignes, montant] du cube pour le filtre courant, par département. */
  function parDepartement() {
    var res = {};
    var deps = etat.cube.departements;
    for (var code in deps) {
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

  function totalNational() {
    var total = [0, 0];
    var nat = etat.cube.national;
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

  // --- carte ---------------------------------------------------------------

  var PALETTE = ["--carte-1", "--carte-2", "--carte-3", "--carte-4", "--carte-5"];

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

  function dessinerCarte() {
    var svg = $("#carte");
    var donnees = parDepartement();
    var valeurs = Object.keys(donnees).map(function (c) { return donnees[c][1]; });
    var bornes = seuils(valeurs);

    Array.prototype.forEach.call(svg.querySelectorAll("path[data-dep]"), function (p) {
      var code = p.getAttribute("data-dep");
      var d = donnees[code];
      p.style.fill = d
        ? "var(" + PALETTE[classe(d[1], bornes)] + ")"
        : "var(--carte-vide)";
      p.classList.toggle("actif", etat.departement === code);
    });

    var echelle = $("#echelle");
    vider(echelle);
    PALETTE.forEach(function (v) {
      var i = document.createElement("i");
      i.style.background = "var(" + v + ")";
      echelle.appendChild(i);
    });
    $("#legende-min").textContent = valeurs.length ? euros(Math.min.apply(null, valeurs)) : "—";
    $("#legende-max").textContent = valeurs.length ? euros(Math.max.apply(null, valeurs)) : "—";
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
      t.textContent = code;
      svg.appendChild(t);
    });

    Object.keys(traces).sort().forEach(function (code) {
      var p = document.createElementNS("http://www.w3.org/2000/svg", "path");
      p.setAttribute("d", traces[code]);
      p.setAttribute("data-dep", code);
      p.setAttribute("tabindex", "0");
      p.setAttribute("role", "button");
      var nom = noms[code] ? noms[code][0] : code;
      p.setAttribute("aria-label", nom);
      p.addEventListener("click", function () { choisirDepartement(code); });
      p.addEventListener("keydown", function (e) {
        if (e.key === "Enter" || e.key === " ") { e.preventDefault(); choisirDepartement(code); }
      });
      p.addEventListener("mousemove", function (e) { survol(e, code); });
      p.addEventListener("mouseleave", masquerInfobulle);
      svg.appendChild(p);
    });
  }

  var infobulle;

  function survol(e, code) {
    if (!infobulle) infobulle = $("#infobulle");
    var d = parDepartement()[code];
    var nom = etat.meta.departements.valeurs[code];
    infobulle.innerHTML = "";
    var b = document.createElement("b");
    b.textContent = (nom ? nom[0] : code) + " (" + code + ")";
    infobulle.appendChild(b);
    infobulle.appendChild(document.createTextNode(
      d ? euros(d[1]) + " · " + fmtNombre.format(d[0]) + " versements"
        : "aucune donnée pour ce filtre"));
    infobulle.classList.add("visible");
    var x = Math.min(e.clientX + 14, window.innerWidth - 275);
    infobulle.style.left = x + "px";
    infobulle.style.top = (e.clientY + 14) + "px";
  }

  function masquerInfobulle() {
    if (infobulle) infobulle.classList.remove("visible");
  }

  // --- compteurs -----------------------------------------------------------

  function dessinerCompteurs() {
    var t = totalNational();
    var sd = sansDepartement();
    var m = etat.meta;
    var cases = [
      [euros(t[1]), "Montant attribué"],
      [fmtNombre.format(t[0]), "Versements"],
      [fmtNombre.format(m.totaux.beneficiaires_distincts), "Bénéficiaires distincts"],
      [fmtNombre.format(m.totaux.donateurs_distincts), "Donateurs"],
      [m.couverture.departements_avec_donnees + " / " + m.couverture.departements_univers,
        "Départements couverts"],
      [t[0] ? Math.round(sd[0] / (t[0]) * 100) + " %" : "—", "Versements sans géographie"]
    ];
    var hote = $("#compteurs");
    vider(hote);
    cases.forEach(function (c) {
      var d = document.createElement("div");
      d.className = "compteur";
      var v = document.createElement("span"); v.className = "valeur"; v.textContent = c[0];
      var e = document.createElement("span"); e.className = "etiquette"; e.textContent = c[1];
      d.appendChild(v); d.appendChild(e); hote.appendChild(d);
    });
  }

  // --- panneau latéral -----------------------------------------------------

  function classement(entrees, limite) {
    var ul = document.createElement("ul");
    ul.className = "classement";
    entrees.slice(0, limite || 25).forEach(function (e) {
      var li = document.createElement("li");
      var n = document.createElement("span"); n.className = "nom"; n.textContent = e[0];
      var m = document.createElement("span"); m.className = "montant"; m.textContent = euros(e[2]);
      var d = document.createElement("span"); d.className = "detail";
      d.textContent = fmtNombre.format(e[1]) + " versement" + (e[1] > 1 ? "s" : "");
      li.appendChild(n); li.appendChild(m); li.appendChild(d);
      ul.appendChild(li);
    });
    return ul;
  }

  async function choisirDepartement(code) {
    etat.departement = etat.departement === code ? null : code;
    dessinerCarte();
    await dessinerPanneau();
  }

  async function dessinerPanneau() {
    var titre = $("#panneau-titre");
    var sousTitre = $("#panneau-soustitre");
    var corps = $("#panneau-corps");
    vider(corps);

    if (!etat.departement) {
      titre.textContent = "France entière";
      sousTitre.textContent = "Cliquez un département pour son détail.";
      corps.appendChild(classement(
        etat.onglet === "beneficiaires" ? etat.top.beneficiaires : etat.top.donateurs, 25));
      return;
    }

    var code = etat.departement;
    var nom = etat.meta.departements.valeurs[code];
    titre.textContent = (nom ? nom[0] : code) + " (" + code + ")";
    sousTitre.textContent = "Chargement du détail…";

    try {
      if (!etat.fragments[code]) {
        etat.fragments[code] = await chargerGz("data/aggregates/departements/" + code + ".json.gz");
      }
      var f = etat.fragments[code];
      sousTitre.textContent = euros(f.montant_eur) + " · "
        + fmtNombre.format(f.lignes) + " versements · " + (f.region || "");
      corps.appendChild(classement(
        etat.onglet === "beneficiaires" ? f.beneficiaires : f.donateurs, 30));
    } catch (err) {
      sousTitre.textContent = "Détail indisponible pour ce département.";
      console.warn(err);
    }
  }

  // --- contrôles -----------------------------------------------------------

  function remplirFiltres() {
    var selAnnee = $("#filtre-annee");
    etat.meta.annees.forEach(function (a) {
      var o = document.createElement("option"); o.value = a; o.textContent = a;
      selAnnee.appendChild(o);
    });
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
      etat.annee = "toutes"; etat.niveau = "tous"; etat.departement = null;
      selAnnee.value = "toutes"; selNiveau.value = "tous";
      rafraichir();
    });
    Array.prototype.forEach.call(document.querySelectorAll(".onglets button"), function (b) {
      b.addEventListener("click", function () {
        etat.onglet = b.dataset.onglet;
        Array.prototype.forEach.call(document.querySelectorAll(".onglets button"), function (x) {
          x.setAttribute("aria-selected", String(x === b));
        });
        dessinerPanneau();
      });
    });
  }

  function rafraichir() {
    dessinerCompteurs();
    dessinerCarte();
    dessinerPanneau();
  }

  function avertissementQualite() {
    var q = etat.meta.qualite;
    var d = q.deduplication;
    var el = $("#avertissement");
    el.innerHTML = "";
    var b = document.createElement("b");
    b.textContent = "Ce que ces chiffres ne disent pas. ";
    el.appendChild(b);
    el.appendChild(document.createTextNode(
      etat.meta.couverture.note + " " +
      fmtNombre.format(etat.meta.couverture.lignes_sans_departement) +
      " versements n'ont pas de département exploitable et n'apparaissent donc pas sur la carte. " +
      "La déduplication entre sources a retiré " + fmtNombre.format(d.lignes_ecartees) +
      " doublons (" + euros(d.montant_ecarte_eur) + ")."
    ));
  }

  // --- démarrage -----------------------------------------------------------

  async function demarrer() {
    try {
      var res = await Promise.all([
        chargerGz("data/aggregates/meta.json.gz"),
        chargerGz("data/aggregates/cube.json.gz"),
        chargerGz("data/aggregates/map-departements.json.gz"),
        chargerGz("data/aggregates/top.json.gz")
      ]);
      etat.meta = res[0]; etat.cube = res[1]; etat.carte = res[2]; etat.top = res[3];

      $("#chargement").remove();
      $("#application").hidden = false;

      remplirFiltres();
      construireCarte();
      avertissementQualite();
      rafraichir();

      // Marqueur du banc de mesure : les données sont exploitables.
      window.__DATA_READY = true;
    } catch (err) {
      var c = $("#chargement");
      if (c) c.textContent = "Chargement impossible : " + err.message;
      console.error(err);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", demarrer);
  } else {
    demarrer();
  }

  if ("serviceWorker" in navigator) {
    window.addEventListener("load", function () {
      navigator.serviceWorker.register("sw.js").catch(function () { /* sans effet */ });
    });
  }
})();
