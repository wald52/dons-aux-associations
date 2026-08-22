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

  // Classes de la vue « part connue ». Six paliers plutôt qu'un dégradé
  // continu : sur 101 départements, 59 sont à ZÉRO et trois dépassent 50 % —
  // un dégradé linéaire écraserait tout le reste dans la même teinte pâle.
  // Les bornes suivent la distribution réelle, elles ne sont pas rondes par
  // esthétique.
  //
  // Le zéro a sa propre couleur, grise et récessive : « le site n'en connaît
  // rien » n'est pas le bas d'une échelle de bleus, c'est une absence. C'est
  // la même distinction que dans l'autre vue entre « aucune donnée » et le
  // reste.
  var CLASSES_PART = [
    { seuil: 0, couleur: "var(--seq-vide)", libelle: "Rien de connu" },
    { seuil: 1, couleur: "var(--seq-1)", libelle: "moins de 1 %" },
    { seuil: 5, couleur: "var(--seq-2)", libelle: "1 à 5 %" },
    { seuil: 25, couleur: "var(--seq-3)", libelle: "5 à 25 %" },
    { seuil: 50, couleur: "var(--seq-4)", libelle: "25 à 50 %" },
    { seuil: Infinity, couleur: "var(--seq-5)", libelle: "50 % et plus" }
  ];

  var etat = {};
  var vueCarte = "etats";

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
      var texte = fmt.format(d.avec_donnees) + " avec données · " +
        fmt.format(d.publie_non_lu) + " publient sans être exploités · " +
        fmt.format(d.sans_donnees) + " sans donnée trouvée";
      if (d.donateurs_dans_les_donnees != null) {
        texte += " — les données ne contiennent que " +
          fmt.format(d.donateurs_dans_les_donnees) + " financeur" +
          (d.donateurs_dans_les_donnees > 1 ? "s" : "") + " à cet échelon";
        if (d.donateurs_non_apparies) {
          texte += ", dont " + fmt.format(d.donateurs_non_apparies) +
            " qu'on n'a pas su rattacher";
        }
      }
      det.appendChild(document.createTextNode(texte));
      bloc.appendChild(det);
      hote.appendChild(bloc);
    });

    dessinerLegende();
  }

  /* ------------------------------------------------------------------------
   * Les deux vues de la carte.
   *
   * « états » répond à « cette collectivité publie-t-elle ? », « part connue »
   * à « et combien nous en échappe-t-il ? ». Ce sont deux questions
   * différentes et deux échelles de nature différente — l'une nominale, l'autre
   * ordonnée — donc jamais la même légende ni le même dégradé.
   * --------------------------------------------------------------------- */

  function classePart(p) {
    if (p == null) return null;
    for (var i = 0; i < CLASSES_PART.length; i++) {
      if (p <= 0 ? i === 0 : p < CLASSES_PART[i].seuil) return CLASSES_PART[i];
    }
    return CLASSES_PART[CLASSES_PART.length - 1];
  }

  function partDuDepartement(code) {
    var d = etat.denominateur && etat.denominateur.communes_par_departement;
    return d ? d[code] : null;
  }

  /** Peinture et description d'un département, selon la vue courante.
   *  Retourne toujours un libellé écrit : la couleur ne porte jamais seule
   *  l'information, ni dans l'infobulle ni pour un lecteur d'écran. */
  function peinture(code) {
    if (vueCarte === "part") {
      var v = partDuDepartement(code);
      var c = classePart(v ? v.part_connue_pct : null);
      if (!c) {
        return { couleur: "var(--seq-vide)", hachure: false,
                 libelle: "aucune commune déclarante", detail: "" };
      }
      return {
        couleur: c.couleur, hachure: false,
        libelle: (v.part_connue_pct === 0 ? "rien de connu"
                  : pourcent(v.part_connue_pct) + " de connu"),
        detail: "les communes déclarent " + montant(v.declare_eur) +
                ", le site en connaît " + montant(v.site_vote_eur) +
                " · " + fmt.format(v.connus) + " commune" +
                (v.connus > 1 ? "s" : "") + " sur " + fmt.format(v.declarants) +
                " déclarante" + (v.declarants > 1 ? "s" : "")
      };
    }
    var d = etat.couverture.departements[code];
    var e = d ? d[0] : "sans_donnees";
    return {
      couleur: ETATS[e].couleur, hachure: ETATS[e].hachure,
      libelle: ETATS[e].libelle,
      detail: d && d[1] ? fmt.format(d[1]) + " versements" : ""
    };
  }

  function dessinerBascule() {
    var hote = $("#bascule-carte");
    if (!hote) return;
    vider(hote);
    // Sans dénominateur, pas de seconde vue : la page reste entière et la
    // bascule disparaît plutôt que d'offrir un bouton qui ne ferait rien.
    if (!etat.denominateur) { hote.hidden = true; return; }
    [["etats", "Ce qui est publié"],
     ["part", "Ce qui nous échappe"]].forEach(function (paire) {
      var b = el("button", null, paire[1]);
      b.type = "button";
      b.setAttribute("aria-pressed", String(vueCarte === paire[0]));
      b.addEventListener("click", function () {
        if (vueCarte === paire[0]) return;
        vueCarte = paire[0];
        dessinerBascule();
        dessinerCarte();
        dessinerLegende();
        dessinerTable();
      });
      hote.appendChild(b);
    });
  }

  function dessinerLegende() {
    var leg = $("#legende-couverture");
    var titre = $("#titre-carte");
    var note = $("#note-carte");
    if (!leg) return;
    vider(leg);
    if (titre) vider(titre);
    if (note) vider(note);

    var entrees = vueCarte === "part"
      ? CLASSES_PART.map(function (c) {
          return { couleur: c.couleur, hachure: false, libelle: c.libelle };
        })
      : Object.keys(ETATS).map(function (k) { return ETATS[k]; });

    entrees.forEach(function (e) {
      var s = el("span", "puce");
      var p = el("i");
      p.style.backgroundColor = e.couleur;
      if (e.hachure) p.classList.add("hachure");
      s.appendChild(p);
      s.appendChild(document.createTextNode(" " + e.libelle));
      leg.appendChild(s);
    });

    if (titre) {
      titre.textContent = vueCarte === "part"
        ? "Part des subventions communales que le site connaît : ce que déclarent "
          + "toutes les communes du département au compte 6574 de la DGFiP, face à "
          + "ce que le site en connaît nommément, sur 2010-2025."
        : "Trois états, jamais confondus : la donnée est là, elle est publiée sans "
          + "être exploitée, ou rien n'a été trouvé.";
    }
    if (note) {
      note.textContent = vueCarte === "part"
        ? "Ni le département lui-même, ni ses intercommunalités, ni la région ne "
          + "sont dans cette part : leurs balances ne remontent qu'à 2019 et "
          + "mélanger deux périodes fausserait le rapport. Une part n'est pas une "
          + "note — le déclaré est un montant mandaté, le connu un montant voté."
        : "Un département coloré n'est pas un département complet : il l'est dès "
          + "qu'une collectivité y publie. La seconde vue dit combien il en manque.";
    }
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
      var pt = peinture(code);
      p.style.fill = pt.hachure ? "url(#hachures)" : pt.couleur;
      if (pt.hachure) p.classList.add("partiel");
      var nom = noms[code] ? noms[code][0] : code;
      p.setAttribute("aria-label", nom + " : " + pt.libelle
        + (pt.detail ? " — " + pt.detail : ""));
      p.addEventListener("mousemove", function (ev) {
        vider(infobulle);
        infobulle.appendChild(el("b", null, nom + " (" + code + ")"));
        infobulle.appendChild(document.createTextNode(
          pt.libelle + (pt.detail ? " · " + pt.detail : "")));
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
   *  obtenir la même chose que la carte. Il suit donc la vue : basculer la
   *  carte sans basculer le tableau laisserait la nouvelle échelle sans son
   *  équivalent écrit. */
  function dessinerTable() {
    var t = $("#table-departements");
    if (!t) return;
    vider(t);
    var noms = etat.meta.departements.valeurs;
    var deps = etat.couverture.departements;
    var part = vueCarte === "part";
    var thead = el("thead");
    var trh = el("tr");
    (part
      ? ["Département", "Part connue", "Communes déclarantes", "Dont connues",
         "Déclaré (6574)", "Connu du site"]
      : ["Département", "État", "Versements", "Montant"]).forEach(function (h) {
      trh.appendChild(el("th", null, h));
    });
    thead.appendChild(trh);
    t.appendChild(thead);
    var tbody = el("tbody");
    Object.keys(noms).sort().forEach(function (code) {
      var tr = el("tr");
      tr.appendChild(el("td", null, (noms[code] ? noms[code][0] : code) + " (" + code + ")"));

      var pt = peinture(code);
      var tdE = el("td");
      var puce = el("span", "puce");
      var i = el("i");
      i.style.backgroundColor = pt.couleur;
      if (pt.hachure) i.classList.add("hachure");
      puce.appendChild(i);
      puce.appendChild(document.createTextNode(" " + pt.libelle));
      tdE.appendChild(puce);
      tr.appendChild(tdE);

      if (part) {
        var v = partDuDepartement(code);
        tr.appendChild(el("td", "num", v ? fmt.format(v.declarants) + " / " +
                                           fmt.format(v.communes) : "—"));
        tr.appendChild(el("td", "num", v ? fmt.format(v.connus) : "—"));
        tr.appendChild(el("td", "num montant", v ? montant(v.declare_eur) : "—"));
        tr.appendChild(el("td", "num montant", v ? montant(v.site_vote_eur) : "—"));
      } else {
        var d = deps[code];
        tr.appendChild(el("td", "num", d && d[1] ? fmt.format(d[1]) : "—"));
        var m = el("td", "num montant");
        m.textContent = d && d[2] ? fmt.format(Math.round(d[2] / 1e6)) + " M€" : "—";
        tr.appendChild(m);
      }
      tbody.appendChild(tr);
    });
    t.appendChild(tbody);
  }

  /* ------------------------------------------------------------------------
   * Le dénominateur : ce que les collectivités déclarent à la DGFiP.
   *
   * Ces montants ne sont JAMAIS ajoutés à ceux du site : ils ne nomment aucun
   * bénéficiaire, et les sommer compterait deux fois le même argent. Ils ne
   * servent qu'à mettre un dénominateur sous la couverture.
   * --------------------------------------------------------------------- */

  function montant(eur) {
    if (!eur) return "—";
    if (Math.abs(eur) >= 1e9) {
      return (eur / 1e9).toFixed(2).replace(".", ",") + " Md€";
    }
    return fmt.format(Math.round(eur / 1e6)) + " M€";
  }

  function pourcent(p) {
    return p == null ? "—" : p.toFixed(1).replace(".", ",") + " %";
  }

  /** Jauge d'une part, avec sa valeur écrite à côté : une barre seule ne dit
   *  rien à qui ne la voit pas, et une part au-dessus de 100 % est réelle. */
  function cellulePart(p) {
    var td = el("td", "num");
    if (p == null) { td.textContent = "—"; return td; }
    var jauge = el("div", "jauge jauge-part");
    var seg = el("i");
    seg.style.width = Math.min(p, 100) + "%";
    seg.style.backgroundColor = "var(--etat-ok)";
    jauge.appendChild(seg);
    td.appendChild(el("span", null, pourcent(p)));
    td.appendChild(jauge);
    return td;
  }

  function ligneTableau(cellules, entete) {
    var tr = el("tr");
    cellules.forEach(function (c) {
      if (c && c.nodeType === 1) { tr.appendChild(c); return; }
      tr.appendChild(el(entete ? "th" : "td", null, c));
    });
    return tr;
  }

  function dessinerDenominateur() {
    var d = etat.denominateur;
    if (!d) return;
    var r = d.resume;

    var hote = $("#denominateur-resume");
    vider(hote);
    var communes = r.commune;
    [[fmt.format(communes.declarants),
      "communes déclarent un compte 6574 sur " + fmt.format(communes.univers) +
      " (" + communes.exercices[0] + "-" + communes.exercices[1] + ")"],
     [montant(communes.declare_eur),
      "déclarés par ces communes sur la période"],
     [montant(communes.site_vote_eur),
      "connus du site, soit " + pourcent(communes.part_connue_pct) + " de ce montant"],
     [fmt.format(communes.connus_du_site),
      "communes dont le site connaît au moins un versement nominatif"]
    ].forEach(function (paire) {
      var bloc = el("div", "compteur");
      bloc.appendChild(el("span", "valeur", paire[0]));
      bloc.appendChild(el("span", "etiquette", paire[1]));
      hote.appendChild(bloc);
    });

    var t = $("#table-denominateur");
    vider(t);
    var thead = el("thead");
    thead.appendChild(ligneTableau(
      ["Échelon", "Exercices", "Collectivités qui déclarent", "Dont connues du site",
       "Déclaré (compte 6574)", "Connu du site (voté)", "Part connue"], true));
    t.appendChild(thead);
    var tbody = el("tbody");
    Object.keys(LIBELLE_NIVEAU).forEach(function (niv) {
      var n = r[niv];
      if (!n) return;
      tbody.appendChild(ligneTableau([
        LIBELLE_NIVEAU[niv],
        n.exercices.length ? n.exercices[0] + "-" + n.exercices[1] : "—",
        fmt.format(n.declarants) + " / " + fmt.format(n.univers),
        fmt.format(n.connus_du_site),
        el("td", "num montant", montant(n.declare_eur)),
        el("td", "num montant", montant(n.site_vote_eur)),
        cellulePart(n.part_connue_pct)
      ]));
    });
    t.appendChild(tbody);

    var res = $("#denominateur-reserves");
    vider(res);
    res.appendChild(el("b", null, "Ce rapprochement est un ordre de grandeur, pas une note. "));
    res.appendChild(document.createTextNode(d.reserves.join(" ")));
    res.appendChild(document.createTextNode(
      " Une part peut dépasser 100 % sans que rien ne soit faux : une collectivité qui vote " +
      "plus qu'elle ne mandate, ou qui publie aussi ses subventions d'investissement, " +
      "dépasse mécaniquement son propre compte 6574. Source : " +
      (d.source.hote || "") + ", " + fmt.format(d.source.lignes || 0) +
      " lignes moissonnées, " + (d.source.licence || "") + "."));
  }

  function dessinerExercices() {
    var d = etat.denominateur;
    var t = $("#table-exercices");
    if (!d || !t) return;
    vider(t);
    var thead = el("thead");
    thead.appendChild(ligneTableau(
      ["Exercice", "Budgets communaux déclarants", "Déclaré (6574)",
       "Le site en connaît (voté)", "Le site en connaît (payé)", "Part connue"], true));
    t.appendChild(thead);
    var tbody = el("tbody");
    var serie = d.par_exercice.commune;
    Object.keys(serie).sort().forEach(function (an) {
      var v = serie[an];
      var part = v.declare_eur ? Math.round(v.site_vote_eur / v.declare_eur * 1000) / 10 : null;
      tbody.appendChild(ligneTableau([
        an,
        el("td", "num", fmt.format(v.budgets)),
        el("td", "num montant", montant(v.declare_eur)),
        el("td", "num montant", montant(v.site_vote_eur)),
        el("td", "num montant", montant(v.site_paye_eur)),
        cellulePart(part)
      ]));
    });
    t.appendChild(tbody);
  }

  /** Les quinze départements où les communes déclarent le plus.
   *
   *  La liste complète des 101 est déjà dans le tableau qui suit la carte,
   *  dès qu'on bascule celle-ci sur « ce qui nous échappe ». La répéter ici
   *  n'apprendrait rien : ce classement-ci répond à une autre question — où
   *  l'argent communal se trouve, et non comment il se répartit. */
  function dessinerDenominateurDepartements() {
    var d = etat.denominateur;
    var t = $("#table-denominateur-departements");
    if (!d || !t || !d.communes_par_departement) return;
    vider(t);
    var noms = etat.meta.departements.valeurs;
    var thead = el("thead");
    thead.appendChild(ligneTableau(
      ["Département", "Communes qui déclarent", "Dont connues du site",
       "Déclaré par les communes", "Connu du site", "Part connue"], true));
    t.appendChild(thead);
    var tbody = el("tbody");
    var codes = Object.keys(d.communes_par_departement).sort(function (a, b) {
      return d.communes_par_departement[b].declare_eur - d.communes_par_departement[a].declare_eur;
    }).slice(0, 15);
    codes.forEach(function (code) {
      var v = d.communes_par_departement[code];
      tbody.appendChild(ligneTableau([
        (noms[code] ? noms[code][0] : code) + " (" + code + ")",
        el("td", "num", fmt.format(v.declarants) + " / " + fmt.format(v.communes)),
        el("td", "num", fmt.format(v.connus)),
        el("td", "num montant", montant(v.declare_eur)),
        el("td", "num montant", montant(v.site_vote_eur)),
        cellulePart(v.part_connue_pct)
      ]));
    });
    t.appendChild(tbody);
  }

  /* ------------------------------------------------------------------------
   * L'angle mort : les organismes tenus de déposer leurs comptes que le site
   * ne reconnaît pas. Le croisement se fait sur les identifiants légaux, et
   * le seuil de 153 000 € mélange dons privés et argent public — d'où un
   * majorant, jamais un décompte d'associations subventionnées oubliées.
   * --------------------------------------------------------------------- */

  function dessinerAngleMort() {
    var a = etat.angleMort;
    if (!a) return;

    var hote = $("#angle-mort-resume");
    vider(hote);
    [[fmt.format(a.organismes), "organismes ont déposé des comptes annuels (" +
      fmt.format(a.depots) + " dépôts)"],
     [fmt.format(a.reconnus), "sont reconnus dans les données du site, par SIREN ou RNA"],
     [fmt.format(a.non_reconnus), "ne le sont pas, soit " +
      pourcent(a.part_non_reconnus_pct) + " des organismes"]
    ].forEach(function (paire) {
      var bloc = el("div", "compteur");
      bloc.appendChild(el("span", "valeur", paire[0]));
      bloc.appendChild(el("span", "etiquette", paire[1]));
      hote.appendChild(bloc);
    });

    var t = $("#table-angle-mort");
    vider(t);
    var thead = el("thead");
    thead.appendChild(ligneTableau(
      ["Nature de l'organisme", "Déposent des comptes", "Reconnus par le site",
       "Part reconnue"], true));
    t.appendChild(thead);
    var tbody = el("tbody");
    Object.keys(a.par_type).forEach(function (type) {
      var v = a.par_type[type];
      var part = v.organismes ? Math.round(v.reconnus / v.organismes * 1000) / 10 : null;
      tbody.appendChild(ligneTableau([
        type,
        el("td", "num", fmt.format(v.organismes)),
        el("td", "num", fmt.format(v.reconnus)),
        cellulePart(part)
      ]));
    });
    t.appendChild(tbody);

    var res = $("#angle-mort-reserves");
    vider(res);
    res.appendChild(el("b", null, "Ce chiffre est un majorant, et le tableau le montre. "));
    res.appendChild(document.createTextNode(
      "Les fonds de dotation, financés par des dons privés, ne sont presque jamais reconnus — " +
      "c'est normal, ils ne reçoivent pas de subventions. " + a.reserves.join(" ") +
      " Source : " + (a.source.dataset || "") + " sur " + (a.source.hote || "") + ", " +
      (a.source.licence || "") + "."));
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
      // Le dénominateur et l'angle mort sont des ajouts : la page doit
      // s'afficher entière même si l'un des deux manque (agrégat pas encore
      // reconstruit). D'où le repli à null plutôt qu'un échec global.
      var res = await Promise.all([
        chargerGz("data/aggregates/couverture.json.gz"),
        chargerGz("data/aggregates/map-departements.json.gz"),
        chargerGz("data/aggregates/meta.json.gz"),
        chargerGz("data/aggregates/denominateur.json.gz").catch(function () { return null; }),
        chargerGz("data/aggregates/angle-mort.json.gz").catch(function () { return null; })
      ]);
      etat.couverture = res[0];
      etat.carte = res[1];
      etat.meta = res[2];
      etat.denominateur = res[3];
      etat.angleMort = res[4];
      etat.moisson = etat.couverture.moisson;
      $("#chargement").remove();
      $("#application").hidden = false;
      dessinerResume();
      dessinerNiveaux();
      dessinerBascule();
      dessinerCarte();
      dessinerTable();
      dessinerDenominateur();
      dessinerExercices();
      dessinerDenominateurDepartements();
      dessinerAngleMort();
      dessinerChantiers();
      window.__DATA_READY = true;
    } catch (e) {
      var c = $("#chargement");
      if (c) c.textContent = "Chargement impossible : " + e.message;
      console.error(e);
    }
  })();
})();
