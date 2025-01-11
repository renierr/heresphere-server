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

self.addEventListener('fetch', event => {
    const url = new URL(event.request.url);

    if (url.pathname === '/share-target') {
        console.log('Service Worker: handling share target');
        event.respondWith((async () => {
            const clientPromise = self.clients.get(event.resultingClientId || event.clientId);
            clientPromise.then(client => {
                if (client) {
                    client.postMessage({
                        type: 'SHARE_TARGET',
                        title: url.searchParams.get('title'),
                        text: url.searchParams.get('text'),
                        sharedUrl: url.searchParams.get('url')
                    });
                }
            });
            return Response.redirect('/', 303);
        })());
    }
});