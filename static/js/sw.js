// =============================================================================
// Author:       George Papasotiriou
// Date Created: March 28, 2026
// Project:      TrendMart E-Commerce Platform
// File:         static/js/sw.js
// Description:  Service Worker for TrendMart PWA (Progressive Web App).
//               Implements a network-first strategy for HTML pages and a
//               cache-first strategy for static assets (CSS/JS/images).
//               Caches Unsplash product images for offline viewing.
//               Excluded from caching: admin, AI chat, and cart mutation URLs.
// =============================================================================

// Cache version — increment this string whenever static assets change
// so the activate event can purge the old cache automatically.
const CACHE_NAME = 'trendmart-v1';

// List of URLs to pre-cache during the service worker install phase.
// These are the minimum files needed to serve the shell of the app offline.
const STATIC_ASSETS = [
  '/',
  '/static/css/main.css',
  '/static/js/main.js',
  '/products/',
  '/offline/',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(STATIC_ASSETS.map(url => new Request(url, { cache: 'reload' }))).catch(() => {});
    }).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  if (event.request.method !== 'GET') return;
  const url = new URL(event.request.url);

  if (url.pathname.startsWith('/admin') ||
      url.pathname.startsWith('/ai/') ||
      url.pathname.includes('/add/') ||
      url.pathname.includes('/cart/') ||
      url.pathname.includes('/checkout/')) {
    return;
  }

  if (event.request.destination === 'image' && url.hostname.includes('unsplash')) {
    event.respondWith(
      caches.open(CACHE_NAME).then(async (cache) => {
        const cached = await cache.match(event.request);
        if (cached) return cached;
        try {
          const response = await fetch(event.request);
          if (response.ok) cache.put(event.request, response.clone());
          return response;
        } catch {
          return new Response('', { status: 503 });
        }
      })
    );
    return;
  }

  if (event.request.destination === 'document') {
    event.respondWith(
      fetch(event.request)
        .catch(() => caches.match('/') || caches.match(event.request))
    );
    return;
  }

  event.respondWith(
    caches.match(event.request).then(cached => cached || fetch(event.request))
  );
});

// ── Web Push: receive push event ────────────────────────────────────────────
self.addEventListener('push', (event) => {
  let data = { title: 'TrendMart', body: 'You have a new notification!', url: '/' };
  try {
    if (event.data) data = { ...data, ...event.data.json() };
  } catch (_) {}

  event.waitUntil(
    self.registration.showNotification(data.title, {
      body: data.body,
      icon: '/static/img/icon-192.png',
      badge: '/static/img/icon-72.png',
      data: { url: data.url || '/' },
      vibrate: [100, 50, 100],
      requireInteraction: false,
    })
  );
});

// ── Web Push: click on notification ─────────────────────────────────────────
self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const targetUrl = event.notification.data?.url || '/';
  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then((windowClients) => {
      for (const client of windowClients) {
        if (client.url.includes(self.location.origin) && 'focus' in client) {
          client.navigate(targetUrl);
          return client.focus();
        }
      }
      return clients.openWindow(targetUrl);
    })
  );
});
