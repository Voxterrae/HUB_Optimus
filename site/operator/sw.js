const CACHE_NAME = "hub-optimus-operator-v0-8";
const OFFLINE_FALLBACK = "./index.html";
const STATIC_ASSETS = [
  "./manifest.webmanifest",
  "./icon.svg"
];

async function cacheStaticAssets() {
  const cache = await caches.open(CACHE_NAME);
  await cache.addAll(STATIC_ASSETS);
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
  const cached = await caches.match(request);
  if (cached) return cached;

  const response = await fetch(request);
  if (response && response.ok) {
    const cache = await caches.open(CACHE_NAME);
    await cache.put(request, response.clone());
  }

  return response;
}

self.addEventListener("install", (event) => {
  event.waitUntil(cacheStaticAssets());
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(
      keys
        .filter((key) => key !== CACHE_NAME)
        .map((key) => caches.delete(key))
    ))
  );

  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
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

  if (url.pathname.includes("/operator/")) {
    event.respondWith(cacheFirst(event.request));
  }
});
