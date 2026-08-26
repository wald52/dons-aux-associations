/* ============================================================================
 * verifier_pwa.js — L'application installable, vérifiée dans un vrai navigateur
 * ----------------------------------------------------------------------------
 * `verify.py` contrôle ce qui se lit sur le disque : le manifeste est complet,
 * ses icônes existent, chaque page le déclare, chaque fichier préchargé est là.
 * Ce que le disque ne peut pas dire, c'est si le navigateur en fait quelque
 * chose. Ce banc-là le demande à Chromium :
 *
 *   · le manifeste est servi et lu depuis un SOUS-CHEMIN — le site est publié
 *     sur `…github.io/dons-aux-associations/`, pas à la racine d'un domaine ;
 *     d'où le serveur monté sur le dossier PARENT du dépôt ;
 *   · le service worker s'installe EN ENTIER (`addAll` est atomique : un seul
 *     chemin faux et il n'y a plus ni hors-ligne ni installation, sans erreur
 *     visible nulle part) ;
 *   · le site fonctionne réellement sans réseau — le serveur est TUÉ, pas
 *     simulé hors ligne : `setOffline` de Playwright n'atteint pas toujours
 *     les requêtes émises par le service worker, et un 404 bien réel passerait
 *     alors pour un repli réussi.
 *
 * Usage :
 *   node scripts/bench/verifier_pwa.js [--port 8123]
 *   CHROMIUM_PATH=/chemin/vers/chrome node scripts/bench/verifier_pwa.js
 *
 * Code de sortie 1 si un contrôle échoue.
 * Prérequis : playwright et http-server installés globalement.
 * ========================================================================= */

const { chromium } = require('playwright');
const { spawn } = require('child_process');
const path = require('path');

const ROOT = path.resolve(__dirname, '..', '..');
const argv = process.argv.slice(2);
const arg = (nom, defaut) => {
  const i = argv.indexOf(nom);
  return i >= 0 && argv[i + 1] ? argv[i + 1] : defaut;
};
const PORT = Number(arg('--port', 8123));
const SOUS_CHEMIN = path.basename(ROOT);
const BASE = `http://localhost:${PORT}/${SOUS_CHEMIN}/index.html`;

const echecs = [];
function dit(nom, ok, detail = '') {
  console.log(`  [${ok ? 'OK ' : 'ÉCHEC'}] ${nom}${detail ? '  — ' + detail : ''}`);
  if (!ok) echecs.push(nom);
}

// http-server lancé par `npx` survit à un kill : c'est npx qu'on tue, pas lui.
// On l'appelle donc directement, sinon le site paraîtrait marcher hors ligne
// alors qu'il est simplement resté en ligne.
function servir() {
  let bin;
  try {
    bin = require.resolve('http-server/bin/http-server');
  } catch (e) {
    console.error("http-server introuvable : `npm install -g http-server`," +
                  " puis relancer avec NODE_PATH pointant sur les modules globaux.");
    process.exit(2);
  }
  return spawn(process.execPath, [bin, path.dirname(ROOT), '-p', String(PORT), '-c-1', '--silent'],
               { stdio: 'ignore' });
}

(async () => {
  console.log(`Application installable — contrôle en navigateur (${BASE})\n`);
  const srv = servir();
  await new Promise((r) => setTimeout(r, 2500));

  const nav = await chromium.launch({
    ...(process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {}),
  });
  const page = await (await nav.newContext()).newPage();
  await page.goto(BASE, { waitUntil: 'load' });

  // 1. le manifeste ---------------------------------------------------------
  const man = await page.evaluate(async () => {
    const lien = document.querySelector('link[rel="manifest"]');
    if (!lien) return null;
    const r = await fetch(lien.href);
    return { statut: r.status, corps: await r.json(), url: lien.href };
  });
  dit('manifeste servi et lisible', !!man && man.statut === 200,
      man ? `HTTP ${man.statut}` : 'aucun <link rel="manifest">');
  if (!man) { await nav.close(); srv.kill(); process.exit(1); }

  dit('manifeste : nom, icônes, mode d\'affichage',
      !!(man.corps.name && man.corps.icons.length && man.corps.display),
      `${man.corps.name} — ${man.corps.display}`);

  // 2. les icônes, résolues DEPUIS LE SOUS-CHEMIN ---------------------------
  const icones = await page.evaluate(async (m) => {
    const src = m.corps.icons.concat((m.corps.shortcuts || []).flatMap((s) => s.icons || []));
    const out = [];
    for (const i of src) {
      const u = new URL(i.src, m.url).href;
      out.push([u, (await fetch(u)).status]);
    }
    return out;
  }, man);
  const perdues = icones.filter(([, s]) => s !== 200).map(([u]) => u);
  dit('icônes toutes atteignables', !perdues.length,
      perdues.length ? perdues.join(', ') : `${icones.length} adresses`);

  // 3. le service worker ----------------------------------------------------
  await page.evaluate(() => navigator.serviceWorker.ready);
  await page.waitForFunction(() => !!navigator.serviceWorker.controller, { timeout: 30000 });
  const cache = await page.evaluate(async () => {
    const noms = await caches.keys();
    const c = await caches.open(noms[0]);
    return { noms, n: (await c.keys()).length };
  });
  dit('service worker actif et préchargement complet', cache.n >= 20,
      `${cache.n} entrées dans ${cache.noms.join(', ')}`);

  // 4. hors ligne, pour de bon ---------------------------------------------
  srv.kill();
  await new Promise((r) => setTimeout(r, 1500));

  const visiter = async (url) => {
    try {
      await page.goto(url, { waitUntil: 'load' });
      return { h1: (await page.textContent('h1')) || '', ok: true };
    } catch (e) { return { h1: e.message.split('\n')[0], ok: false }; }
  };

  let v = await visiter(BASE);
  const pret = await page.evaluate(() => window.__DATA_READY === true);
  const traces = await page.evaluate(() => document.querySelectorAll('svg path').length);
  dit('accueil hors ligne : données et carte', v.ok && pret && traces > 90,
      `${v.h1.trim()} — ${traces} tracés`);

  for (const [page_, attendu] of [['commune.html', /commune/i], ['recherche.html', /association/i],
                                  ['couverture.html', /./], ['methode.html', /./]]) {
    const r = await visiter(BASE.replace('index.html', page_));
    dit(`${page_} hors ligne`, r.ok && attendu.test(r.h1), r.h1.trim().slice(0, 60));
  }

  // Installée, l'application n'a pas de barre d'adresse : une navigation qui
  // échoue afficherait la page d'erreur du navigateur sans rien pour en sortir.
  v = await visiter(BASE.replace('index.html', 'adresse-inconnue.html'));
  dit('adresse inconnue hors ligne : repli sur l\'accueil',
      v.ok && /finance les associations/i.test(v.h1), v.h1.trim().slice(0, 60));

  await nav.close();
  console.log(`\n  ${icones.length && echecs.length === 0 ? 'tout est vert' : echecs.length + ' échec(s)'}`);
  process.exit(echecs.length ? 1 : 0);
})();
