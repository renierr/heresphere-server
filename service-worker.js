// Install event
self.addEventListener('install', event => {
    console.log('Service Worker installing.');
    self.skipWaiting();
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
    event.waitUntil(clients.claim());
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
    if (event.request.url.endsWith('/share-target')) {
        event.respondWith(
            (async () => {
                const formData = await event.request.formData();
                const title = formData.get('title');
                const text = formData.get('text');
                const url = formData.get('url');

                const allClients = await clients.matchAll({
                    type: 'window',
                    includeUncontrolled: true
                });

                if (allClients.length > 0) {
                    // Send data to the existing client
                    allClients[0].postMessage({
                        type: 'SHARE_TARGET',
                        title,
                        text,
                        sharedUrl: url
                    });
                    allClients[0].focus();
                }

                /*
                const clientPromise = self.clients.get(event.resultingClientId || event.clientId);
                clientPromise.then(client => {
                   if (client) {
                       client.postMessage({
                           type: 'SHARE_TARGET',
                           title,
                           text,
                           sharedUrl: url
                       });
                   }
                });
                */

                return Response.redirect('/', 303);
            })()
        );
    }
});
