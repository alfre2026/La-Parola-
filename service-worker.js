/* LA PAROLA — service worker
   Strategia "prima la rete, poi la copia salvata":
   - con la connessione l'app carica sempre l'ultima versione pubblicata
     (basta ricaricare index.html sul sito per aggiornare l'app installata);
   - senza connessione, o con rete lentissima, parte dalla copia salvata. */
const PREFIX = "la-parola-";
const CACHE = PREFIX + "v2";
const CORE = ["./", "./index.html"];
const EXTRA = ["./manifest.json", "./icon-192.png", "./icon-512.png", "./icon-maskable-512.png"];
const WAIT_MS = 3000;

const fresh = url => new Request(url, { cache: "reload" });

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

self.addEventListener("fetch", event => {
  const req = event.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;
  const key = url.origin + url.pathname;

  const network = fetch(req, { cache: "no-cache" });

  // Aggiorna la copia salvata ogni volta che la rete risponde bene.
  event.waitUntil(
    network.then(res => {
      if (!res.ok) return;
      const copy = res.clone();
      return caches.open(CACHE).then(cache => cache.put(key, copy));
    }).catch(() => {})
  );

  event.respondWith((async () => {
    const cache = await caches.open(CACHE);
    const saved = (await cache.match(key)) ||
      (req.mode === "navigate" ? await cache.match("./index.html") : undefined);
    if (!saved) return network;
    const timeout = new Promise(resolve => setTimeout(() => resolve(saved), WAIT_MS));
    return Promise.race([network.then(res => (res.ok ? res : saved), () => saved), timeout]);
  })());
});
