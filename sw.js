/* Service worker — cache hors-ligne.
 * Les agrégats sont mis en cache dès la première visite : les visites
 * suivantes n'attendent plus le réseau.
 * Bumper CACHE à chaque publication, sinon les visiteurs déjà venus
 * continueraient de voir l'ancienne version.
 */
const CACHE = "dons-associations-v18";
const PRECACHE = [
  "./", "./index.html", "./recherche.html", "./commune.html",
  "./couverture.html", "./methode.html", "./assets/css/style.css",
  "./assets/js/commun.js", "./assets/js/lexique.js",
  "./assets/js/index-recherche.js", "./assets/js/suggest.js",
  "./assets/js/export.js",
  "./assets/js/app.js", "./assets/js/recherche.js",
  "./assets/js/commune.js", "./assets/js/couverture.js",
  "./data/aggregates/meta.json.gz", "./data/aggregates/cube.json.gz",
  "./data/aggregates/map-departements.json.gz", "./data/aggregates/top.json.gz"
];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(PRECACHE)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys()
    .then((noms) => Promise.all(noms.filter((n) => n !== CACHE).map((n) => caches.delete(n))))
    .then(() => self.clients.claim()));
});

// `data/recherche/` est mis en cache au fil de l'eau, comme `data/aggregates/` :
// l'index des noms (5 Mo) et les shards de fiches (~120 Ko) ne se retéléchargent
// pas d'une visite à l'autre. Ils ne sont PAS préchargés : personne ne doit les
// payer avant d'en avoir besoin.
self.addEventListener("fetch", (e) => {
  if (e.request.method !== "GET") return;
  const url = new URL(e.request.url);
  if (url.origin !== self.location.origin) return;
  const cachable = url.pathname.includes("/data/aggregates/") ||
                   url.pathname.includes("/data/recherche/");
  e.respondWith(caches.match(e.request).then((cache) => cache || fetch(e.request).then((rep) => {
    if (rep.ok && rep.status === 200 && cachable) {
      const copie = rep.clone();
      caches.open(CACHE).then((c) => c.put(e.request, copie));
    }
    return rep;
  })));
});
