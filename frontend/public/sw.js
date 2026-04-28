/**
 * BlockScope Service Worker
 *
 * Strategy:
 *   - App shell (HTML, JS, CSS bundles)  → Cache-First with network fallback
 *   - API requests (/api/*)              → Network-Only (always fresh data)
 *   - Static assets (images, fonts)      → Stale-While-Revalidate
 *
 * Cache names are versioned so stale caches are purged on activate.
 */

const CACHE_VERSION = 'v1';
const SHELL_CACHE   = `blockscope-shell-${CACHE_VERSION}`;
const STATIC_CACHE  = `blockscope-static-${CACHE_VERSION}`;
const ALL_CACHES    = [SHELL_CACHE, STATIC_CACHE];

// Resources to pre-cache on install (app shell)
const SHELL_URLS = ['/', '/index.html'];

async function getShellAssets() {
  const shellAssets = new Set(SHELL_URLS);

  try {
    const response = await fetch('/index.html', { cache: 'no-store' });
    if (!response.ok) {
      return [...shellAssets];
    }

    const html = await response.text();
    const assetPattern = /(?:src|href)=["'](\/assets\/[^"']+\.(?:js|css))["']/g;
    let match = assetPattern.exec(html);

    while (match) {
      shellAssets.add(match[1]);
      match = assetPattern.exec(html);
    }
  } catch (err) {
    console.warn('[SW] Could not discover shell assets from index.html:', err);
  }

  return [...shellAssets];
}

// ── Install ──────────────────────────────────────────────────────────────────
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(SHELL_CACHE)
      .then(async (cache) => {
        const shellAssets = await getShellAssets();
        await Promise.all(
          shellAssets.map((assetUrl) => (
            cache.add(assetUrl).catch((err) => {
              console.warn('[SW] Pre-cache skipped for', assetUrl, err);
            })
          ))
        );
      })
      .then(() => self.skipWaiting())
  );
});

// ── Activate ─────────────────────────────────────────────────────────────────
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((name) => !ALL_CACHES.includes(name))
          .map((name) => {
            console.info('[SW] Deleting old cache:', name);
            return caches.delete(name);
          })
      );
    }).then(() => {
      // Immediately control all open pages
      return self.clients.claim();
    })
  );
});

// ── Fetch ────────────────────────────────────────────────────────────────────
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET requests
  if (request.method !== 'GET') return;

  // Skip API calls — always go to the network
  if (url.pathname.startsWith('/api/')) {
    return; // browser default (network)
  }

  // ── App shell — HTML navigation requests ─────────────────────────────────
  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request).catch(() => caches.match('/index.html'))
    );
    return;
  }

  // ── JS / CSS bundles — Cache-First ───────────────────────────────────────
  if (
    url.pathname.startsWith('/assets/') &&
    (url.pathname.endsWith('.js') || url.pathname.endsWith('.css'))
  ) {
    event.respondWith(
      caches.match(request).then((cached) => {
        if (cached) return cached;
        return fetch(request).then((networkResponse) => {
          const clone = networkResponse.clone();
          caches.open(SHELL_CACHE).then((cache) => cache.put(request, clone));
          return networkResponse;
        });
      })
    );
    return;
  }

  // ── Static assets (fonts, images) — Stale-While-Revalidate ───────────────
  event.respondWith(
    caches.open(STATIC_CACHE).then((cache) => {
      return cache.match(request).then((cachedResponse) => {
        const networkFetch = fetch(request).then((networkResponse) => {
          cache.put(request, networkResponse.clone());
          return networkResponse;
        }).catch(() => cachedResponse); // fallback to stale on offline

        // Return the cached version while updating in background
        return cachedResponse || networkFetch;
      });
    })
  );
});

// ── Background Sync (for future offline-queue support) ───────────────────────
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});
