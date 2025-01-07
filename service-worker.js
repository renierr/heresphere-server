// Install event
self.addEventListener('install', event => {
  console.log('Service Worker installing.');
  event.waitUntil(
    caches.open('v1').then(cache => {
      return cache.addAll([
        //'/',
        //'/static/index.js',
        //'/static/styles.css',
        '/static/favicon.png',
        '/static/icons/icon-192x192.png',
        '/static/icons/icon-512x512.png'
      ]);
    })
  );
});

// Activate event
self.addEventListener('activate', event => {
  console.log('Service Worker activating.');
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cache => {
          if (cache !== 'v1') {
            console.log('Service Worker: clearing old cache');
            return caches.delete(cache);
          }
        })
      );
    })
  );
});

// Fetch event
/*
self.addEventListener('fetch', event => {
  console.log('Service Worker fetching:', event.request.url);
  event.respondWith(
    caches.match(event.request).then(response => {
      return response || fetch(event.request);
    })
  );
});
*/
