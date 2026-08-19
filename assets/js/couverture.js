/* ============================================================================
 * Page de couverture — ce que le site sait et ne sait pas.
 *
 * Sur un sujet d'argent public, taire les lacunes est pire que les afficher :
 * un lecteur qui prend une carte incomplète pour une carte complète en tire
 * des conclusions fausses. Cette page existe pour rendre ce risque impossible.
 * ========================================================================= */

(function () {
  "use strict";

  // États, pas séries : ce sont des statuts. Deux d'entre eux passent sous le
  // seuil de contraste de 3:1 sur fond clair — d'où le relief obligatoire,
  // fourni ici par la légende, la hachure de l'état intermédiaire et le
  // tableau qui répète la carte en toutes lettres.
  var ETATS = {
    donnees: { libelle: "Données présentes", couleur: "var(--etat-ok)", hachure: false },
    publie_non_lu: { libelle: "Publie, mais non exploité", couleur: "var(--etat-partiel)", hachure: true },
    sans_donnees: { libelle: "Aucune donnée trouvée", couleur: "var(--etat-vide)", hachure: false }
  };
  var LIBELLE_NIVEAU = {
    commune: "Communes", epci: "Intercommunalités",
    departement: "Départements", region: "Régions"
  };

  var etat = {};

  async function chargerGz(url) {
    var r = await fetch(url);
    if (!r.ok) throw new Error(url + " : " + r.status);
    var buf = await r.arrayBuffer();
    var o = new Uint8Array(buf);
    if (o[0] === 0x1f && o[1] === 0x8b) {
      var flux = new Blob([buf]).stream().pipeThrough(new DecompressionStream("gzip"));
      return JSON.parse(await new Response(flux).text());
    }
    return JSON.parse(new TextDecoder().decode(buf));
  }

  var fmt = new Intl.NumberFormat("fr-FR");
  function $(s) { return document.querySelector(s); }
  function vider(e) { while (e.firstChild) e.removeChild(e.firstChild); }
  function el(t, c, x) {
    var e = document.createElement(t);
    if (c) e.className = c;
    if (x != null) e.textContent = x;
    return e;
  }

  function dessinerResume() {
    var r = etat.couverture.resume;
    var hote = $("#resume");
    vider(hote);
    Object.keys(LIBELLE_NIVEAU).forEach(function (niv) {
      var d = r[niv];
      if (!d) return;
      var bloc = el("div", "compteur");
      bloc.appendChild(el("span", "valeur", d.avec_donnees + " / " + fmt.format(d.univers)));
      var etiquette = LIBELLE_NIVEAU[niv];
      if (d.part_population_couverte != null) {
        etiquette += " — " + String(d.part_population_couverte).replace(".", ",") + " % de la population";
      }
      bloc.appendChild(el("span", "etiquette", etiquette));
      hote.appendChild(bloc);
    });
  }

  function dessinerNiveaux() {
    var r = etat.couverture.resume;
    var hote = $("#niveaux");
    vider(hote);
    Object.keys(LIBELLE_NIVEAU).forEach(function (niv) {
      var d = r[niv];
      if (!d) return;
      var bloc = el("div", "barre-couverture");
      bloc.appendChild(el("h3", null, LIBELLE_NIVEAU[niv]));

      var jauge = el("div", "jauge");
      [["donnees", d.avec_donnees], ["publie_non_lu", d.publie_non_lu],
       ["sans_donnees", d.sans_donnees]].forEach(function (paire) {
        if (!paire[1]) return;
        var seg = el("i");
        seg.style.width = (paire[1] / d.univers * 100) + "%";
        seg.style.backgroundColor = ETATS[paire[0]].couleur;
        if (ETATS[paire[0]].hachure) seg.classList.add("hachure");
        seg.title = ETATS[paire[0]].libelle + " : " + fmt.format(paire[1]);
        jauge.appendChild(seg);
      });
      bloc.appendChild(jauge);

      var det = el("p", "detail-couverture");
      det.appendChild(document.createTextNode(
        fmt.format(d.avec_donnees) + " avec données · " +
        fmt.format(d.publie_non_lu) + " publient sans être exploités · " +
        fmt.format(d.sans_donnees) + " sans donnée trouvée"));
      bloc.appendChild(det);
      hote.appendChild(bloc);
    });

    var leg = $("#legende-couverture");
    vider(leg);
    Object.keys(ETATS).forEach(function (k) {
      var s = el("span", "puce");
      var p = el("i");
      p.style.backgroundColor = ETATS[k].couleur;
      if (ETATS[k].hachure) p.classList.add("hachure");
      s.appendChild(p);
      s.appendChild(document.createTextNode(" " + ETATS[k].libelle));
      leg.appendChild(s);
    });
  }

  function dessinerCarte() {
    var svg = $("#carte");
    svg.setAttribute("viewBox", etat.carte.viewBox);
    vider(svg);

    // Motif de hachures : sur fond clair, l'ocre de l'état intermédiaire passe
    // sous le seuil de contraste. La texture fournit le second canal, qui
    // survit au daltonisme, à l'impression et au contraste forcé.
    var NS = "http://www.w3.org/2000/svg";
    var defs = document.createElementNS(NS, "defs");
    var motif = document.createElementNS(NS, "pattern");
    motif.setAttribute("id", "hachures");
    motif.setAttribute("width", "5"); motif.setAttribute("height", "5");
    motif.setAttribute("patternUnits", "userSpaceOnUse");
    motif.setAttribute("patternTransform", "rotate(45)");
    var fond = document.createElementNS(NS, "rect");
    fond.setAttribute("width", "5"); fond.setAttribute("height", "5");
    fond.setAttribute("fill", "var(--etat-partiel)");
    var trait = document.createElementNS(NS, "line");
    trait.setAttribute("x1", "0"); trait.setAttribute("y1", "0");
    trait.setAttribute("x2", "0"); trait.setAttribute("y2", "5");
    trait.setAttribute("stroke", "rgba(0,0,0,.34)");
    trait.setAttribute("stroke-width", "2");
    motif.appendChild(fond); motif.appendChild(trait);
    defs.appendChild(motif); svg.appendChild(defs);
    var deps = etat.couverture.departements;
    var noms = etat.meta.departements.valeurs;
    var infobulle = $("#infobulle");

    Object.keys(etat.carte.medaillons || {}).forEach(function (code) {
      var m = etat.carte.medaillons[code];
      var r = document.createElementNS("http://www.w3.org/2000/svg", "rect");
      r.setAttribute("x", m.x); r.setAttribute("y", m.y);
      r.setAttribute("width", m.w); r.setAttribute("height", m.h);
      r.setAttribute("class", "medaillon");
      svg.appendChild(r);
    });

    Object.keys(etat.carte.traces).sort().forEach(function (code) {
      var p = document.createElementNS("http://www.w3.org/2000/svg", "path");
      p.setAttribute("d", etat.carte.traces[code]);
      var d = deps[code];
      var e = d ? d[0] : "sans_donnees";
      p.style.fill = ETATS[e].hachure ? "url(#hachures)" : ETATS[e].couleur;
      if (ETATS[e].hachure) p.classList.add("partiel");
      var nom = noms[code] ? noms[code][0] : code;
      p.setAttribute("aria-label", nom + " : " + ETATS[e].libelle);
      p.addEventListener("mousemove", function (ev) {
        vider(infobulle);
        infobulle.appendChild(el("b", null, nom + " (" + code + ")"));
        infobulle.appendChild(document.createTextNode(
          ETATS[e].libelle + (d && d[1] ? " · " + fmt.format(d[1]) + " versements" : "")));
        infobulle.classList.add("visible");
        infobulle.style.left = Math.min(ev.clientX + 14, window.innerWidth - 270) + "px";
        infobulle.style.top = (ev.clientY + 14) + "px";
      });
      p.addEventListener("mouseleave", function () { infobulle.classList.remove("visible"); });
      svg.appendChild(p);
    });
  }

  /** Le tableau EST le relief exigé : une couleur sous 3:1 ne peut pas porter
   *  seule l'information, et un lecteur au clavier ou en lecture d'écran doit
   *  obtenir la même chose que la carte. */
  function dessinerTable() {
    var t = $("#table-departements");
    if (!t) return;
    vider(t);
    var noms = etat.meta.departements.valeurs;
    var deps = etat.couverture.departements;
    var thead = el("thead");
    var trh = el("tr");
    ["Département", "État", "Versements", "Montant"].forEach(function (h) {
      trh.appendChild(el("th", null, h));
    });
    thead.appendChild(trh);
    t.appendChild(thead);
    var tbody = el("tbody");
    Object.keys(noms).sort().forEach(function (code) {
      var d = deps[code];
      var e = d ? d[0] : "sans_donnees";
      var tr = el("tr");
      tr.appendChild(el("td", null, (noms[code] ? noms[code][0] : code) + " (" + code + ")"));
      var tdE = el("td");
      var puce = el("span", "puce");
      var i = el("i");
      i.style.backgroundColor = ETATS[e].couleur;
      if (ETATS[e].hachure) i.classList.add("hachure");
      puce.appendChild(i);
      puce.appendChild(document.createTextNode(" " + ETATS[e].libelle));
      tdE.appendChild(puce);
      tr.appendChild(tdE);
      tr.appendChild(el("td", "num", d && d[1] ? fmt.format(d[1]) : "—"));
      var m = el("td", "num montant");
      m.textContent = d && d[2] ? fmt.format(Math.round(d[2] / 1e6)) + " M€" : "—";
      tr.appendChild(m);
      tbody.appendChild(tr);
    });
    t.appendChild(tbody);
  }

  function dessinerChantiers() {
    var hote = $("#chantiers");
    vider(hote);
    var r = etat.couverture.resume;
    var m = etat.moisson || {};
    var items = [
      ["Le moissonnage automatique", (m.jeux_retenus || 0) + " jeux de données retenus sur " +
        (m.jeux_examines || 0) + " examinés sur data.gouv.fr, soit " +
        fmt.format(m.fichiers_retenus || 0) + " fichiers. Chaque nouveau millésime publié " +
        "par une collectivité sera repris sans modification du code."],
      ["Les communes", "C'est la lacune principale : " + fmt.format(r.commune.sans_donnees) +
        " communes sur " + fmt.format(r.commune.univers) + " n'ont aucune donnée. La plupart " +
        "ne publient pas — seules celles de plus de 3 500 habitants y sont tenues, et " +
        "l'obligation est peu suivie."],
      ["Les fichiers repérés mais non lus", fmt.format(
        r.commune.publie_non_lu + r.epci.publie_non_lu + r.departement.publie_non_lu +
        r.region.publie_non_lu) + " collectivités publient un jeu de subventions dont rien " +
        "d'exploitable n'a pu être tiré : format tableur non standard, colonnes absentes, " +
        "lien mort. Cette lacune-là est de notre côté et peut être réduite."]
    ];
    items.forEach(function (it) {
      var b = el("div", "chantier");
      b.appendChild(el("h3", null, it[0]));
      b.appendChild(el("p", null, it[1]));
      hote.appendChild(b);
    });
  }

  (async function () {
    try {
      var res = await Promise.all([
        chargerGz("data/aggregates/couverture.json.gz"),
        chargerGz("data/aggregates/map-departements.json.gz"),
        chargerGz("data/aggregates/meta.json.gz")
      ]);
      etat.couverture = res[0];
      etat.carte = res[1];
      etat.meta = res[2];
      etat.moisson = etat.couverture.moisson;
      $("#chargement").remove();
      $("#application").hidden = false;
      dessinerResume();
      dessinerNiveaux();
      dessinerCarte();
      dessinerTable();
      dessinerChantiers();
      window.__DATA_READY = true;
    } catch (e) {
      var c = $("#chargement");
      if (c) c.textContent = "Chargement impossible : " + e.message;
      console.error(e);
    }
  })();
})();
