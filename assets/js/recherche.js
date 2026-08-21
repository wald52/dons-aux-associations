/* ============================================================================
 * Recherche croisée — moteur SQL dans le navigateur
 * ----------------------------------------------------------------------------
 * DuckDB-WASM interroge deux fichiers Parquet servis statiquement :
 *
 *   beneficiaires.parquet  261 444 bénéficiaires résolus, triés par nom —
 *                          la recherche et le classement des cumuls ;
 *   versements.parquet     1,69 M de versements triés par bénéficiaire,
 *                          en petits row groups : la fiche d'une association
 *                          ne télécharge que les blocs qui la concernent,
 *                          par requêtes HTTP Range.
 *
 * Le moteur (~10 Mo transférés) n'est chargé que sur cette page : le premier
 * écran du site n'en paie jamais le poids. Tout s'exécute dans le navigateur,
 * aucune requête n'est envoyée à un serveur applicatif.
 * ========================================================================= */

import * as duckdb from "../vendor/duckdb/duckdb.mjs";

"use strict";

var conn = null;
var meta = null;
var baseDeDonnees = null;
var shardsCharges = {};

// Les versements sont répartis en 64 shards par bénéficiaire. La fiche d'une
// association télécharge le sien (~400 Ko), une seule fois, puis requête en
// local. Même fonction de répartition que `shard_of` côté pipeline.
var NB_SHARDS = 64;

function shardDe(bid) {
  var somme = 0;
  for (var i = 0; i < bid.length; i++) somme += bid.charCodeAt(i);
  return somme % NB_SHARDS;
}

async function assurerShard(bid) {
  var num = shardDe(bid);
  var nom = ("0" + num).slice(-2);
  if (!shardsCharges[nom]) {
    shardsCharges[nom] = fetch("data/canonical/recherche/versements/" + nom + ".parquet")
      .then(function (r) {
        if (!r.ok) throw new Error("shard " + nom + " : " + r.status);
        return r.arrayBuffer();
      })
      .then(function (buf) {
        return baseDeDonnees.registerFileBuffer("versements-" + nom + ".parquet",
          new Uint8Array(buf));
      });
  }
  await shardsCharges[nom];
  return "versements-" + nom + ".parquet";
}

var NIVEAUX = {
  etat: "État", operateur: "Opérateur de l'État", region: "Région",
  departement: "Département", epci: "Intercommunalité", commune: "Commune",
  inconnu: "Donateur non identifié"
};

// --- utilitaires ------------------------------------------------------------

function $(sel) { return document.querySelector(sel); }
function vider(el) { while (el.firstChild) el.removeChild(el.firstChild); }
function el(tag, cls, texte) {
  var e = document.createElement(tag);
  if (cls) e.className = cls;
  if (texte != null) e.textContent = texte;
  return e;
}

var fmtNombre = new Intl.NumberFormat("fr-FR");

function euros(v) {
  if (v == null) return "—";
  v = Number(v);
  var a = Math.abs(v);
  if (a >= 1e9) return (v / 1e9).toFixed(2).replace(".", ",") + " Md€";
  if (a >= 1e6) return (v / 1e6).toFixed(1).replace(".", ",") + " M€";
  if (a >= 1e4) return fmtNombre.format(Math.round(v / 1e3)) + " k€";
  return fmtNombre.format(Math.round(v)) + " €";
}

/** Même pliage que `normalize_name` côté pipeline : la recherche doit voir
 *  les noms exactement comme l'index les stocke. */
function plier(q) {
  return q.normalize("NFD").replace(/[̀-ͯ]/g, "")
    .replace(/[^a-zA-Z0-9]+/g, " ").trim().replace(/\s+/g, " ").toUpperCase();
}

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

function lignes(resultat) {
  return resultat.toArray().map(function (r) { return r.toJSON(); });
}

async function requete(sql, params) {
  if (!params || !params.length) return lignes(await conn.query(sql));
  var stmt = await conn.prepare(sql);
  try {
    return lignes(await stmt.query.apply(stmt, params));
  } finally {
    await stmt.close();
  }
}

// --- démarrage du moteur ----------------------------------------------------

function etatMoteur(msg) {
  var e = $("#moteur-etat");
  if (e) e.textContent = msg;
}

async function demarrerMoteur() {
  etatMoteur("Chargement du moteur SQL (une dizaine de Mo, une seule fois)…");

  // URL absolues : le worker résout les chemins relatifs contre SA propre
  // position, pas celle de la page — un chemin relatif part donc en 404.
  var bundle = {
    mainModule: new URL("assets/vendor/duckdb/duckdb-eh.wasm", location.href).href,
    mainWorker: new URL("assets/vendor/duckdb/duckdb-browser-eh.worker.js", location.href).href
  };
  var worker = new Worker(bundle.mainWorker);
  var db = new duckdb.AsyncDuckDB(new duckdb.ConsoleLogger(duckdb.LogLevel.WARNING), worker);
  await db.instantiate(bundle.mainModule);

  // Deux régimes de lecture, choisis d'après ce que les requêtes font :
  //  - beneficiaires.parquet (11 Mo) : chaque recherche par nom balaie de
  //    toute façon toute la colonne des noms. Le télécharger UNE fois en
  //    mémoire rend toutes les recherches locales et instantanées.
  //  - versements.parquet (25 Mo) : la fiche d'une association n'a besoin
  //    que de quelques blocs — lecture distante par plages d'octets (Range),
  //    guidée par le tri par bénéficiaire et les petits row groups.
  etatMoteur("Téléchargement de l'index des associations (11 Mo, une seule fois)…");
  var rep = await fetch("data/canonical/recherche/beneficiaires.parquet");
  if (!rep.ok) throw new Error("index bénéficiaires : " + rep.status);
  await db.registerFileBuffer("beneficiaires.parquet",
    new Uint8Array(await rep.arrayBuffer()));
  baseDeDonnees = db;

  conn = await db.connect();

  // L'extension Parquet est chargée depuis NOTRE origine, jamais depuis le
  // CDN duckdb.org : la CSP l'interdit (connect-src 'self'), et un site
  // d'intérêt public ne dépend pas de la disponibilité d'un tiers.
  var repo = new URL("assets/vendor/duckdb/extensions", location.href).href;
  await conn.query("SET custom_extension_repository='" + repo + "'");
  await conn.query("SET autoinstall_extension_repository='" + repo + "'");
  await conn.query("INSTALL parquet; LOAD parquet;");

  meta = await chargerGz("data/aggregates/meta.json.gz");
}

// --- recherche --------------------------------------------------------------

// Ce que le site refuse d'appeler un don, et pourquoi — dit à l'utilisateur,
// pas seulement au code.
var RAISONS_HORS_DON = {
  prestation: "Prestation facturée par l'association : la collectivité achète un " +
    "service, il y a une contrepartie. Ce n'est pas un don, donc hors des totaux.",
  remboursement: "Remboursement de frais ou cotisation d'adhésion : la collectivité " +
    "rend une avance ou paie sa part. Ce n'est pas un soutien, donc hors des totaux.",
  nature: "Aide en nature (locaux, personnel mis à disposition), valorisée en euros " +
    "mais jamais décaissée. Comptée à part pour ne pas gonfler les montants."
};

var SELECTION = "benef_id, nom, siren, rna, dep_code, kind, nb_versements, montant_eur, " +
  "montant_ecarte_eur, annee_min, annee_max, nb_echelons, echelons, nb_donateurs";

async function chercher() {
  var q = plier($("#q").value);
  var dep = $("#filtre-dep").value;
  var cumul = $("#filtre-cumul").value;
  var hote = $("#resultats");
  $("#fiche").hidden = true;
  hote.hidden = false;

  if (q.length < 3 && !cumul) {
    vider(hote);
    if (q.length > 0) hote.appendChild(el("p", "chargement", "Au moins trois caractères…"));
    else await montrerCumuls();  // vue par défaut : les cumuls remarquables
    return;
  }

  var sql = "SELECT " + SELECTION + " FROM 'beneficiaires.parquet' WHERE 1=1";
  var params = [];
  if (q.length >= 3) { sql += " AND nom_norm LIKE '%' || ? || '%'"; params.push(q); }
  if (dep) { sql += " AND dep_code = ?"; params.push(dep); }
  if (cumul) { sql += " AND nb_echelons >= " + parseInt(cumul, 10); }
  sql += " ORDER BY montant_eur DESC LIMIT 40";

  vider(hote);
  hote.appendChild(el("p", "chargement", "Recherche…"));
  var rows;
  try { rows = await requete(sql, params); }
  catch (e) { vider(hote); hote.appendChild(el("p", "chargement", "Échec de la requête : " + e.message)); return; }

  vider(hote);
  if (!rows.length) {
    hote.appendChild(el("p", "chargement", "Aucune association trouvée pour ces critères."));
    return;
  }
  hote.appendChild(tableResultats(rows,
    rows.length === 40 ? "40 premiers résultats, par montant décroissant — précisez la recherche pour affiner." : null));
}

/** Vue d'accueil : les cumuls d'échelons les plus marquants. */
async function montrerCumuls() {
  var hote = $("#resultats");
  vider(hote);
  hote.appendChild(el("p", "chargement", "Chargement des cumuls remarquables…"));
  var dep = $("#filtre-dep").value;
  var sql = "SELECT " + SELECTION + " FROM 'beneficiaires.parquet' WHERE nb_echelons >= 3";
  var params = [];
  if (dep) { sql += " AND dep_code = ?"; params.push(dep); }
  sql += " ORDER BY montant_eur DESC LIMIT 30";
  var rows = await requete(sql, params);
  vider(hote);
  var intro = el("div", "intro-cumuls");
  intro.appendChild(el("h2", null, "Les cumuls d'échelons les plus importants"));
  intro.appendChild(el("p", "sous-titre",
    "4 400 associations sont financées par au moins trois échelons publics différents. " +
    "En voici les premières par montant total — ou cherchez une association par son nom."));
  hote.appendChild(intro);
  hote.appendChild(tableResultats(rows, null));
}

function tableResultats(rows, note) {
  var bloc = el("div", "bloc-resultats");
  var ul = el("ul", "classement");
  rows.forEach(function (r) {
    var li = el("li", "resultat");
    li.tabIndex = 0;
    li.setAttribute("role", "button");

    var nom = el("span", "nom", r.nom);
    var m = el("span", "montant", euros(r.montant_eur));
    var d = el("span", "detail");
    var deps = meta.departements.valeurs;
    var nomDep = r.dep_code && deps[r.dep_code] ? deps[r.dep_code][0] + " (" + r.dep_code + ")" : "département inconnu";
    var badges = el("span", "badges");
    var nEch = Number(r.nb_echelons);
    if (nEch >= 2) {
      var b = el("b", "badge" + (nEch >= 3 ? " fort" : ""), nEch + " échelons");
      b.title = String(r.echelons).split(",").map(function (x) { return NIVEAUX[x] || x; }).join(" + ");
      badges.appendChild(b);
    }
    d.appendChild(document.createTextNode(
      nomDep + " · " + fmtNombre.format(Number(r.nb_versements)) + " versement" +
      (Number(r.nb_versements) > 1 ? "s" : "") + " · " +
      (r.annee_min === r.annee_max ? r.annee_min : r.annee_min + "-" + r.annee_max) + " "));
    d.appendChild(badges);

    li.appendChild(nom); li.appendChild(m); li.appendChild(d);
    function ouvrir() { montrerFiche(r); }
    li.addEventListener("click", ouvrir);
    li.addEventListener("keydown", function (e) {
      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); ouvrir(); }
    });
    ul.appendChild(li);
  });
  bloc.appendChild(ul);
  if (note) bloc.appendChild(el("p", "sous-titre", note));
  return bloc;
}

// --- fiche d'une association ------------------------------------------------

async function montrerFiche(b) {
  var fiche = $("#fiche");
  $("#resultats").hidden = true;
  fiche.hidden = false;
  vider(fiche);

  var retour = el("button", "retour", "← Retour aux résultats");
  retour.type = "button";
  retour.addEventListener("click", function () {
    fiche.hidden = true; $("#resultats").hidden = false;
  });
  fiche.appendChild(retour);

  fiche.appendChild(el("h2", null, b.nom));
  var ident = [];
  if (b.siren) ident.push("SIREN " + b.siren);
  if (b.rna) ident.push("RNA " + b.rna);
  var deps = meta.departements.valeurs;
  if (b.dep_code && deps[b.dep_code]) ident.push(deps[b.dep_code][0] + " (" + b.dep_code + ")");
  fiche.appendChild(el("p", "sous-titre", ident.join(" · ") ||
    "Sans identifiant national — reconnue par son nom et son département."));

  var stats = el("div", "compteurs");
  [[euros(b.montant_eur), "reçus au total"],
   [fmtNombre.format(Number(b.nb_versements)), "versements"],
   [String(b.nb_echelons), "échelon" + (Number(b.nb_echelons) > 1 ? "s" : "") + " financeur" + (Number(b.nb_echelons) > 1 ? "s" : "")],
   [String(b.nb_donateurs), "donateur" + (Number(b.nb_donateurs) > 1 ? "s" : "") + " distinct" + (Number(b.nb_donateurs) > 1 ? "s" : "")]
  ].forEach(function (c) {
    var d = el("div", "compteur");
    d.appendChild(el("span", "valeur", c[0]));
    d.appendChild(el("span", "etiquette", c[1]));
    stats.appendChild(d);
  });
  fiche.appendChild(stats);
  if (b.montant_ecarte_eur) {
    var av = el("p", "avertissement");
    av.appendChild(el("b", null, "Montants mis de côté. "));
    av.appendChild(document.createTextNode(
      euros(b.montant_ecarte_eur) + " supplémentaires figurent dans la source mais sont " +
      "exclus des totaux : leur unité ou leur vraisemblance est douteuse (cf. rapport de qualité)."));
    fiche.appendChild(av);
  }

  var corps = el("div", "fiche-corps");
  corps.appendChild(el("p", "chargement", "Chargement des versements…"));
  fiche.appendChild(corps);

  var fichier = await assurerShard(b.benef_id);
  var vers = await requete(
    "SELECT year, donor_level, donor_name_raw, donor_program, purpose_raw, " +
    "amount_eur, amount_rejected_eur, granularity, measure, concours, " +
    "source_label, source_url " +
    "FROM '" + fichier + "' WHERE benef_id = ? ORDER BY year DESC, amount_eur DESC",
    [b.benef_id]);
  vider(corps);

  // --- trajectoire : total par année ---------------------------------------
  var parAn = {};
  var parDonateur = {};
  // La trajectoire ne trace que les DONS VOTÉS — la même règle que les totaux
  // du site, celle de `common.py`. Y mêler une prestation facturée ou une
  // exécution budgétaire ferait une courbe qui ne veut rien dire.
  vers.forEach(function (v) {
    if (v.granularity === "aggregate" || v.amount_eur == null) return;
    if (v.concours !== "don" || v.measure === "verse") return;
    var y = v.year == null ? "?" : String(v.year);
    parAn[y] = (parAn[y] || 0) + Number(v.amount_eur);
    var k = v.donor_name_raw || "—";
    parDonateur[k] = parDonateur[k] || { total: 0, n: 0, niveau: v.donor_level };
    parDonateur[k].total += Number(v.amount_eur);
    parDonateur[k].n++;
  });

  var annees = Object.keys(parAn).filter(function (y) { return y !== "?"; }).sort();
  if (annees.length > 1) {
    corps.appendChild(el("h3", null, "Trajectoire"));
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
    corps.appendChild(traj);
  }

  // --- financeurs ----------------------------------------------------------
  corps.appendChild(el("h3", null, "Financeurs"));
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
      li.appendChild(el("span", "detail", fmtNombre.format(d.n) + " versement" + (d.n > 1 ? "s" : "")));
      ulD.appendChild(li);
    });
  corps.appendChild(ulD);

  // --- versements ligne à ligne --------------------------------------------
  corps.appendChild(el("h3", null, "Versements (" + fmtNombre.format(vers.length) + ")"));
  var tableEnv = el("div", "table-versements");
  var LIMITE = 300;
  var tbl = el("table");
  var thead = el("thead");
  var trh = el("tr");
  ["Année", "Donateur", "Objet", "Montant"].forEach(function (h) { trh.appendChild(el("th", null, h)); });
  thead.appendChild(trh); tbl.appendChild(thead);
  var tbody = el("tbody");
  vers.slice(0, LIMITE).forEach(function (v) {
    var tr = el("tr");
    tr.appendChild(el("td", "num", v.year == null ? "—" : String(v.year)));
    var tdD = el("td");
    tdD.appendChild(document.createTextNode((v.donor_name_raw || "—")));
    if (v.donor_program) tdD.appendChild(el("span", "detail", v.donor_program));
    tr.appendChild(tdD);
    tr.appendChild(el("td", "objet", v.purpose_raw || "—"));
    var m = el("td", "num montant");
    if (v.amount_eur != null) m.textContent = euros(v.amount_eur);
    else if (v.amount_rejected_eur != null) {
      m.textContent = "(" + euros(v.amount_rejected_eur) + ")";
      m.title = "Montant publié par la source, exclu des totaux : unité ou vraisemblance douteuse.";
      m.classList.add("ecarte");
    } else m.textContent = "—";
    if (v.granularity === "aggregate") {
      m.title = "Ligne agrégée (total publié par la source), jamais sommée avec les versements individuels.";
      m.classList.add("ecarte");
    } else if (v.concours && v.concours !== "don") {
      // Rien n'est caché : la ligne s'affiche, avec la raison pour laquelle
      // elle ne compte pas comme un don.
      m.title = RAISONS_HORS_DON[v.concours] || "Ce n'est pas un don.";
      m.classList.add("ecarte");
    } else if (v.measure === "verse") {
      m.title = "Montant déclaré PAYÉ (exécution budgétaire). Affiché à part du voté, " +
        "jamais additionné avec lui : c'est souvent le même argent.";
      m.classList.add("ecarte");
    }
    tr.appendChild(m);
    tbody.appendChild(tr);
  });
  tbl.appendChild(tbody);
  tableEnv.appendChild(tbl);
  if (vers.length > LIMITE) {
    tableEnv.appendChild(el("p", "sous-titre",
      "Les " + LIMITE + " premiers versements sont affichés, sur " + fmtNombre.format(vers.length) + "."));
  }
  corps.appendChild(tableEnv);
}

// --- initialisation ---------------------------------------------------------

function anti_rebond(fn, ms) {
  var t = null;
  return function () { clearTimeout(t); t = setTimeout(fn, ms); };
}

(async function () {
  try {
    await demarrerMoteur();
  } catch (e) {
    $("#moteur-etat").textContent =
      "Le moteur de recherche n'a pas pu démarrer (" + e.message + "). " +
      "Un navigateur récent est nécessaire.";
    return;
  }
  $("#moteur-etat").remove();
  $("#application").hidden = false;

  var selDep = $("#filtre-dep");
  var deps = meta.departements.valeurs;
  Object.keys(deps).sort().forEach(function (code) {
    var o = document.createElement("option");
    o.value = code; o.textContent = code + " — " + deps[code][0];
    selDep.appendChild(o);
  });

  $("#q").addEventListener("input", anti_rebond(chercher, 250));
  selDep.addEventListener("change", chercher);
  $("#filtre-cumul").addEventListener("change", chercher);

  await montrerCumuls();
  window.__DATA_READY = true;
})();
