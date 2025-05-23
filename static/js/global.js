if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/service-worker.js').then(registration => {
            console.log('Service Worker registered with scope:', registration.scope);
            registration.update();

            // Listen for the waiting service worker
            registration.addEventListener('updatefound', () => {
                const newWorker = registration.installing;
                newWorker.addEventListener('statechange', () => {
                    if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                        newWorker.postMessage({action: 'skipWaiting'});
                    }
                });
            });
        }).catch(error => {
            console.log('Service Worker registration failed:', error);
        });

        // Listen for the controlling service worker to change
        navigator.serviceWorker.addEventListener('controllerchange', () => {
            window.location.reload();
        });
    });

    navigator.serviceWorker.addEventListener('message', event => {
        console.log('Service Worker message:', event.data);
        if (event.data.type === 'SHARE_TARGET') {
            const sharedUrl = event.data.sharedUrl;
            if (sharedUrl) {
                // Trigger the stream function with the shared URL
                pwaPostVideoUrl(true, sharedUrl);
            }
        }
    });
}

import { videoUrl } from "helper";
function pwaPostVideoUrl(isStream, videoUrlParam) {
    videoUrl(videoUrlParam, isStream);
}

document.addEventListener('DOMContentLoaded', () => {

    // swipe listener for select (up/down) to select option
    const applySelectOptionSwipeHandler = (selectElement) => {
        if (selectElement.dataset.hammerApplied) {
            return;
        }
        const hammer = new Hammer(selectElement);
        hammer.get('swipe').set({direction: Hammer.DIRECTION_VERTICAL});
        hammer.on('swipe', (event) => {
            if (event.direction === Hammer.DIRECTION_UP) {
                selectElement.selectedIndex = Math.max(0, selectElement.selectedIndex - 1);
            } else if (event.direction === Hammer.DIRECTION_DOWN) {
                selectElement.selectedIndex = Math.min(selectElement.length - 1, selectElement.selectedIndex + 1);
            }
            selectElement.dispatchEvent(new Event('change', {bubbles: true}));
        });
        selectElement.dataset.hammerApplied = 'true';
    };
    document.querySelectorAll('select').forEach(applySelectOptionSwipeHandler);

    // Create a MutationObserver to watch for new select elements
    const observer = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
            mutation.addedNodes.forEach((node) => {
                if (node.tagName === 'SELECT') {
                    applySelectOptionSwipeHandler(node);
                } else if (node.querySelectorAll) {
                    node.querySelectorAll('select').forEach(applySelectOptionSwipeHandler);
                }
            });
        });
    });
    observer.observe(document.body, {childList: true, subtree: true});
});
