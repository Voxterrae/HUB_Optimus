const CACHE_NAME = "hub-optimus-operator-v0-28";
const VERSION_REQUEST = "HUB_OPTIMUS_OPERATOR_SW_VERSION_V1";
const OFFLINE_FALLBACK = "./index.html";
const OAUTH_CALLBACK_FIELDS = [
  "code",
  "state",
  "error",
  "error_description",
  "error_uri",
  "iss",
  "session_state"
];
const STATIC_ASSETS = [
  "./",
  "./index.html",
  "./auth.v1.js",
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
      if (request.mode === "navigate") {
        const navigationUrl = new URL(request.url);
        const isOAuthCallback = OAUTH_CALLBACK_FIELDS.some((field) =>
          navigationUrl.searchParams.has(field)
        );
        if (!isOAuthCallback) {
          await cache.put(OFFLINE_FALLBACK, response.clone());
        }
      } else {
        await cache.put(request, response.clone());
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
  event.waitUntil(cacheStaticAssets());
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(
      keys
        .filter((
          key
        ) => key.startsWith("hub-optimus-operator-") && key !== CACHE_NAME)
        .map((key) => caches.delete(key))
    ))
  );

  self.clients.claim();
});

self.addEventListener("message", (event) => {
  if (event.data?.type !== VERSION_REQUEST) return;
  event.ports?.[0]?.postMessage({ version: CACHE_NAME });
});

self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET") return;

  const url = new URL(event.request.url);

  if (url.origin !== self.location.origin) return;

  if (url.pathname.endsWith("/operator/sw.js")) return;

  if (url.pathname.endsWith("/operator/runtime-config.v1.js")) {
    // Runtime enablement is a kill switch. Never let an older enabled config
    // survive in Cache Storage; a network failure therefore disables auth.
    event.respondWith(fetch(event.request, { cache: "no-store" }));
    return;
  }

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
