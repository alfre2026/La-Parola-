/* LA PAROLA — service worker
   Strategia "subito la copia salvata, aggiornamento in sottofondo":
   - l'app si apre all'istante dalla copia salvata, anche con rete lenta o assente;
   - intanto scarica la versione pubblicata e aggiorna la copia salvata;
   - se la pagina è cambiata, avvisa l'app, che propone di aggiornare con un tocco
     (altrimenti la versione nuova parte alla prossima apertura). */
const PREFIX = "la-parola-";
const CACHE = PREFIX + "v2";
const CORE = ["./", "./index.html"];
const EXTRA = ["./manifest.json", "./icon-192.png", "./icon-512.png", "./icon-maskable-512.png"];

const fresh = url => new Request(url, { cache: "reload" });
const tag = res => res && (res.headers.get("etag") || res.headers.get("last-modified"));

self.addEventListener("install", event => {
  event.waitUntil(
    caches.open(CACHE)
      .then(cache => cache.addAll(CORE.map(fresh))
        .then(() => Promise.allSettled(EXTRA.map(url => cache.add(fresh(url))))))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", event => {
  event.waitUntil(
    caches.keys()
      // Elimina solo le vecchie copie di QUESTA app: sullo stesso indirizzo
      // possono convivere altre app, le cui copie non vanno toccate.
      .then(keys => Promise.all(keys.filter(k => k.startsWith(PREFIX) && k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

async function tellClients() {
  const list = await self.clients.matchAll({ type: "window" });
  list.forEach(c => c.postMessage({ type: "update" }));
}

self.addEventListener("fetch", event => {
  const req = event.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;
  const key = url.origin + url.pathname;
  const isPage = req.mode === "navigate" || url.pathname.endsWith("/index.html");

  event.respondWith((async () => {
    const cache = await caches.open(CACHE);
    const saved = (await cache.match(key)) ||
      (req.mode === "navigate" ? await cache.match("./index.html") : undefined);

    // Versione pubblicata, scaricata in sottofondo; aggiorna la copia salvata.
    const update = fetch(req, { cache: "no-cache" }).then(async res => {
      if (!res.ok) return res;
      const before = tag(saved), after = tag(res);
      await cache.put(key, res.clone());
      if (isPage && saved && before && after && before !== after) await tellClients();
      return res;
    });
    event.waitUntil(update.catch(() => {}));

    return saved || update;   // senza copia salvata (primo avvio) si aspetta la rete
  })());
});
