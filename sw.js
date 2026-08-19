/* Service worker — cache hors-ligne.
 * Les agrégats sont mis en cache dès la première visite : les visites
 * suivantes n'attendent plus le réseau.
 * Bumper CACHE à chaque publication, sinon les visiteurs déjà venus
 * continueraient de voir l'ancienne version.
 */
const CACHE = "dons-associations-v4";
const PRECACHE = [
  "./", "./index.html", "./recherche.html", "./couverture.html", "./methode.html", "./assets/css/style.css",
  "./assets/js/app.js", "./assets/js/recherche.js", "./assets/js/couverture.js",
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

self.addEventListener("fetch", (e) => {
  if (e.request.method !== "GET") return;
  const url = new URL(e.request.url);
  if (url.origin !== self.location.origin) return;
  e.respondWith(caches.match(e.request).then((cache) => cache || fetch(e.request).then((rep) => {
    if (rep.ok && rep.status === 200 && url.pathname.includes("/data/aggregates/")) {
      const copie = rep.clone();
      caches.open(CACHE).then((c) => c.put(e.request, copie));
    }
    return rep;
  })));
});
