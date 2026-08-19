/* ============================================================================
 * measure.js — Banc de mesure de performance du site
 * ----------------------------------------------------------------------------
 * Mesure ce que subit réellement un visiteur : octets transférés, nombre de
 * requêtes, premier affichage, moment où les données sont exploitables, et
 * mémoire consommée par l'onglet.
 *
 * Conçu pour rester valable après la refonte : il ne connaît rien de
 * l'architecture interne, il observe le réseau et quelques marqueurs. Les
 * mesures d'aujourd'hui et celles d'après la phase 2 sont donc comparables.
 *
 * Usage :
 *   node scripts/bench/measure.js [--label v0] [--timeout 300] [--port 8099]
 *   node scripts/bench/measure.js --label phase2 --no-cache
 *
 * Sortie : bench/<label>.json  + un résumé lisible sur la console.
 *
 * Prérequis : playwright et http-server installés globalement.
 * ========================================================================= */

const { chromium } = require('playwright');
const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');
const http = require('http');

const ROOT = path.resolve(__dirname, '..', '..');

// ---- arguments -------------------------------------------------------------
const argv = process.argv.slice(2);
function arg(name, fallback) {
  const i = argv.indexOf('--' + name);
  return i !== -1 && argv[i + 1] && !argv[i + 1].startsWith('--') ? argv[i + 1] : fallback;
}
const LABEL = arg('label', 'run');
const TIMEOUT_S = parseInt(arg('timeout', '300'), 10);
const PORT = parseInt(arg('port', '8099'), 10);
const HEADFUL = argv.includes('--headful');

// Marqueur « données prêtes » : la première expression vraie gagne. On en liste
// plusieurs pour que le banc survive au changement d'architecture.
const READY_PROBES = [
  "window.ALL_SUBVENTIONS && window.ALL_SUBVENTIONS.length > 0",      // v0
  "window.__DATA_READY === true",                                      // cible
  "document.querySelector('#totalAmount') && !/^--?$/.test(document.querySelector('#totalAmount').textContent.trim())",
];

// ---- utilitaires -----------------------------------------------------------
const mb = (b) => +(b / 1048576).toFixed(2);
const s = (ms) => (ms == null ? null : +(ms / 1000).toFixed(2));

function waitForServer(port, tries = 60) {
  return new Promise((resolve, reject) => {
    const attempt = (n) => {
      http.get({ host: '127.0.0.1', port, path: '/index.html' }, (res) => {
        res.resume();
        resolve();
      }).on('error', () => {
        if (n <= 0) return reject(new Error('serveur injoignable'));
        setTimeout(() => attempt(n - 1), 250);
      });
    };
    attempt(tries);
  });
}

// ---- programme principal ---------------------------------------------------
(async () => {
  // 1. serveur statique local, gzip actif (comme GitHub Pages)
  const server = spawn(
    'npx', ['--yes', 'http-server', ROOT, '-p', String(PORT), '--gzip', '--brotli', '-c-1', '--silent'],
    { stdio: 'ignore', detached: false }
  );
  const stopServer = () => { try { server.kill('SIGKILL'); } catch (_) {} };
  process.on('exit', stopServer);

  await waitForServer(PORT);

  // Chromium est fourni par l'environnement (PLAYWRIGHT_BROWSERS_PATH) ; on
  // laisse Playwright le résoudre plutôt que de figer un chemin.
  const browser = await chromium.launch({
    headless: !HEADFUL,
    args: ['--no-sandbox', '--disable-dev-shm-usage'],
  });

  const context = await browser.newContext();
  const page = await context.newPage();

  // 2. comptage réseau via CDP : encodedDataLength = octets réellement transférés
  const cdp = await context.newCDPSession(page);
  await cdp.send('Network.enable');

  const net = { requests: 0, transferred: 0, decoded: 0, byType: {}, failed: 0, slowest: [] };
  const urlOf = new Map();
  const startedAt = new Map();

  cdp.on('Network.requestWillBeSent', (e) => {
    net.requests++;
    urlOf.set(e.requestId, e.request.url);
    startedAt.set(e.requestId, e.timestamp);
  });

  cdp.on('Network.loadingFinished', (e) => {
    const url = urlOf.get(e.requestId) || '';
    const bytes = e.encodedDataLength || 0;
    net.transferred += bytes;

    const ext = (url.split('?')[0].match(/\.([a-z0-9]+)$/i) || [, 'autre'])[1].toLowerCase();
    const b = (net.byType[ext] = net.byType[ext] || { n: 0, bytes: 0 });
    b.n++; b.bytes += bytes;

    const t0 = startedAt.get(e.requestId);
    if (t0 != null) {
      net.slowest.push({ url: url.replace(/^https?:\/\/[^/]+/, ''), ms: Math.round((e.timestamp - t0) * 1000), bytes });
    }
  });

  cdp.on('Network.loadingFailed', () => { net.failed++; });

  // 3. navigation + mesure
  const t0 = Date.now();
  const result = {
    label: LABEL,
    date: new Date().toISOString(),
    url: `http://127.0.0.1:${PORT}/index.html`,
    timeoutSeconds: TIMEOUT_S,
  };

  let navError = null;
  try {
    await page.goto(result.url, { waitUntil: 'commit', timeout: TIMEOUT_S * 1000 });
  } catch (e) {
    navError = String(e.message).split('\n')[0];
  }

  // premier affichage (FCP), sans bloquer si jamais il n'arrive pas
  let fcp = null;
  try {
    fcp = await page.evaluate(() => new Promise((resolve) => {
      const seen = performance.getEntriesByName('first-contentful-paint')[0];
      if (seen) return resolve(seen.startTime);
      new PerformanceObserver((list, obs) => {
        const e = list.getEntriesByName('first-contentful-paint')[0];
        if (e) { obs.disconnect(); resolve(e.startTime); }
      }).observe({ type: 'paint', buffered: true });
      setTimeout(() => resolve(null), 30000);
    }));
  } catch (_) { /* page occupée : FCP non mesurable */ }

  // attente « données prêtes »
  const deadline = t0 + TIMEOUT_S * 1000;
  let ready = false;
  let readyMs = null;
  const expr = READY_PROBES.join(' || ');
  while (Date.now() < deadline) {
    try {
      if (await page.evaluate(`Boolean(${expr})`)) { ready = true; readyMs = Date.now() - t0; break; }
    } catch (_) { /* contexte bloqué par le parsing : on retente */ }
    await new Promise((r) => setTimeout(r, 500));
  }

  // 4. relevés finaux — best effort, la page peut être saturée
  const probe = async (fn, fallback = null) => {
    try { return await page.evaluate(fn, { timeout: 15000 }); } catch (_) { return fallback; }
  };

  result.timings = {
    firstContentfulPaintSeconds: s(fcp),
    dataReadySeconds: ready ? s(readyMs) : null,
    dataReady: ready,
    wallClockSeconds: s(Date.now() - t0),
  };

  result.network = {
    requests: net.requests,
    failed: net.failed,
    transferredMB: mb(net.transferred),
    byType: Object.fromEntries(
      Object.entries(net.byType)
        .sort((a, b) => b[1].bytes - a[1].bytes)
        .slice(0, 8)
        .map(([k, v]) => [k, { requests: v.n, MB: mb(v.bytes) }])
    ),
    heaviest: net.slowest.sort((a, b) => b.bytes - a.bytes).slice(0, 5)
      .map((r) => ({ url: r.url, MB: mb(r.bytes), ms: r.ms })),
  };

  const heap = await probe(() => (performance.memory ? {
    usedMB: Math.round(performance.memory.usedJSHeapSize / 1048576),
    limitMB: Math.round(performance.memory.jsHeapSizeLimit / 1048576),
  } : null));
  result.memory = heap;

  result.data = await probe(() => ({
    records: window.ALL_SUBVENTIONS ? window.ALL_SUBVENTIONS.length : null,
    scriptTags: document.querySelectorAll('script[src]').length,
  }), { records: null, scriptTags: null });

  if (navError) result.navigationError = navError;

  // 5. sortie
  const outDir = path.join(ROOT, 'bench');
  fs.mkdirSync(outDir, { recursive: true });
  const outFile = path.join(outDir, `${LABEL}.json`);
  fs.writeFileSync(outFile, JSON.stringify(result, null, 2) + '\n');

  const t = result.timings;
  console.log('');
  console.log(`  MESURE « ${LABEL} »  —  ${new Date().toLocaleString('fr-FR')}`);
  console.log('  ' + '-'.repeat(58));
  console.log(`  Octets transférés .......... ${result.network.transferredMB} Mo`);
  console.log(`  Requêtes ................... ${result.network.requests}${net.failed ? ` (${net.failed} en échec)` : ''}`);
  console.log(`  Premier affichage .......... ${t.firstContentfulPaintSeconds ?? 'non atteint'} s`);
  console.log(`  Données exploitables ....... ${t.dataReady ? t.dataReadySeconds + ' s' : `NON ATTEINT en ${TIMEOUT_S} s`}`);
  console.log(`  Mémoire JS ................. ${heap ? heap.usedMB + ' Mo' : 'non relevée'}`);
  console.log(`  Enregistrements ............ ${result.data.records ?? 'n/a'}`);
  console.log(`  Balises <script> ........... ${result.data.scriptTags ?? 'n/a'}`);
  console.log('  ' + '-'.repeat(58));
  console.log(`  -> ${path.relative(ROOT, outFile)}`);
  console.log('');

  await browser.close();
  stopServer();
  process.exit(0);
})().catch((e) => {
  console.error('Échec du banc :', e);
  process.exit(1);
});
