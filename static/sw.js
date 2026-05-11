const CACHE_NAME = 'lucky-v1';
const ASSETS = [
  '/',
  '/static/app_icon.png',
  'https://cdn.tailwindcss.com',
  'https://cdn.jsdelivr.net/npm/jsbarcode@3.11.0/dist/JsBarcode.all.min.js'
];

// Install Event
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log('Caching assets');
      return cache.addAll(ASSETS);
    })
  );
});

// Activate Event
self.addEventListener('activate', (event) => {
  console.log('Service Worker activated');
});

// Fetch Event
self.addEventListener('fetch', (event) => {
  event.respondWith(
    caches.match(event.request).then((response) => {
      return response || fetch(event.request).catch(() => {
        // Fallback for offline (can be a custom offline.html)
        if (event.request.mode === 'navigate') {
          return caches.match('/');
        }
      });
    })
  );
});
