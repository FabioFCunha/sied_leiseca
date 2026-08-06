const CACHE_NAME = 'sied-mobile-cache-v1';

// Recursos essenciais para carregar a interface (shell)
const STATIC_ASSETS = [
  '/offline.html',
  '/manifest.json'
];

self.addEventListener('install', (event) => {
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(STATIC_ASSETS);
    })
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(self.clients.claim());
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheName !== CACHE_NAME) {
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
});

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // Regra 1: Bypassar completamente a API e rotas de auth
  if (url.pathname.startsWith('/api/') || url.pathname.startsWith('/auth/')) {
    event.respondWith(fetch(event.request));
    return;
  }

  // Regra 2: Permitir apenas metodos GET e requisições da mesma origem
  if (event.request.method !== 'GET' || url.origin !== location.origin) {
    event.respondWith(fetch(event.request));
    return;
  }

  // Regra 3: Estratégia principal: Network First, fallback offline para navegação HTML
  if (event.request.mode === 'navigate' || event.request.destination === 'document') {
    event.respondWith(
      fetch(event.request)
        .catch(() => {
          return caches.match('/offline.html');
        })
    );
    return;
  }

  // Regra 4: Cache First apenas para fontes, imagens e manifest (arquivos puramente estáticos)
  if (event.request.destination === 'image' || event.request.destination === 'font' || url.pathname.endsWith('.json')) {
    event.respondWith(
      caches.match(event.request).then((cachedResponse) => {
        if (cachedResponse) {
          return cachedResponse;
        }
        return fetch(event.request).then((networkResponse) => {
          if (!networkResponse || networkResponse.status !== 200 || networkResponse.type !== 'basic') {
            return networkResponse;
          }
          const responseToCache = networkResponse.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(event.request, responseToCache);
          });
          return networkResponse;
        }).catch(() => {
          // Ignora a falha de imagem/font
          return new Response('', { status: 408, statusText: 'Request timeout' });
        });
      })
    );
    return;
  }

  // Fallback genérico para scripts/css (Network First)
  event.respondWith(
    fetch(event.request).catch(() => caches.match(event.request))
  );
});
