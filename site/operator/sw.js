const CACHE_NAME = "hub-optimus-operator-v0-28";
const PRIVATE_OPERATOR_ORIGIN = "https://api.huboptimus.dev";
const IS_PRIVATE_OPERATOR_ORIGIN = self.location.origin === PRIVATE_OPERATOR_ORIGIN;
const OFFLINE_FALLBACK = "./index.html";
const STATIC_ASSETS = [
  "./",
  "./index.html",
  "./i18n.v1.js",
  "./learning-candidate.v1.js",
  "./learning-store.v1.js",
  "./schemas/operator_learning_candidate.v1.schema.json",
  "./manifest.webmanifest",
  "./manifest.en.webmanifest",
  "./manifest.es.webmanifest",
  "./manifest.de.webmanifest",
  "./manifest.ru.webmanifest",
  "./manifest.he.webmanifest",
  "./manifest.zh-Hans.webmanifest",
  "./icon.svg",
  "./og.svg",
  "../assets/brand/hub-optimus-logo-lockup.png"
];
const STATIC_ASSET_URLS = new Set(
  STATIC_ASSETS.map((asset) => new URL(asset, self.location.href).href)
);

async function cacheStaticAssets() {
  const cache = await caches.open(CACHE_NAME);
  const requests = STATIC_ASSETS.map((asset) => new Request(
    new URL(asset, self.location.href).href,
    { cache: "reload" }
  ));
  await cache.addAll(requests);
}

async function networkFirst(request) {
  const cache = await caches.open(CACHE_NAME);

  try {
    const response = await fetch(request, { cache: "no-store" });

    if (response && response.ok) {
      await cache.put(request, response.clone());

      if (request.mode === "navigate") {
        await cache.put(OFFLINE_FALLBACK, response.clone());
      }
    }

    return response;
  } catch {
    return caches.match(request).then((cached) => (
      cached || caches.match(OFFLINE_FALLBACK)
    ));
  }
}

async function cacheFirst(request) {
  const cache = await caches.open(CACHE_NAME);
  const cached = await cache.match(request);
  if (cached) return cached;

  const response = await fetch(request);
  if (response && response.ok) {
    await cache.put(request, response.clone());
  }

  return response;
}

self.addEventListener("install", (event) => {
  event.waitUntil(
    IS_PRIVATE_OPERATOR_ORIGIN
      ? Promise.resolve()
      : cacheStaticAssets()
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    (async () => {
      const keys = await caches.keys();
      await Promise.all(keys
        .filter((key) => (
          key.startsWith("hub-optimus-operator-") &&
          (IS_PRIVATE_OPERATOR_ORIGIN || key !== CACHE_NAME)
        ))
        .map((key) => caches.delete(key)));
      if (IS_PRIVATE_OPERATOR_ORIGIN) {
        await self.registration.unregister();
      }
      await self.clients.claim();
    })()
  );
});

self.addEventListener("fetch", (event) => {
  // The authenticated console must never work from an offline shell after a
  // session expires or is deliberately closed. NGINX is its only source.
  if (IS_PRIVATE_OPERATOR_ORIGIN) return;
  if (event.request.method !== "GET") return;

  const url = new URL(event.request.url);

  if (url.origin !== self.location.origin) return;

  if (url.pathname.endsWith("/operator/sw.js")) return;

  if (
    event.request.mode === "navigate" ||
    url.pathname.endsWith("/operator/") ||
    url.pathname.endsWith("/operator/index.html")
  ) {
    event.respondWith(networkFirst(event.request));
    return;
  }

  if (
    url.pathname.includes("/operator/") ||
    STATIC_ASSET_URLS.has(url.href)
  ) {
    event.respondWith(cacheFirst(event.request));
  }
});
