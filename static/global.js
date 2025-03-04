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

function pwaPostVideoUrl(isStream, videoUrl) {
    const vueInstance = window.vueInstance;
    if (vueInstance) {
        vueInstance.videoUrl = videoUrl;
        vueInstance.postVideoUrl(true);
    }
}

// Function to apply the theme
function applyTheme(theme) {
    document.documentElement.setAttribute('data-bs-theme', theme);
}

document.addEventListener('DOMContentLoaded', () => {
    const storedTheme = localStorage.getItem('theme');
    const prefersDarkScheme = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const defaultTheme = storedTheme || (prefersDarkScheme ? 'dark' : 'light');
    applyTheme(defaultTheme);

    // Initialize the switch state based on the stored theme
    const themeToggle = document.getElementById('theme-toggle');
    themeToggle.checked = defaultTheme === 'dark';

    // Toggle theme and store the selection
    themeToggle.addEventListener('change', () => {
        const newTheme = themeToggle.checked ? 'dark' : 'light';
        applyTheme(newTheme);
        localStorage.setItem('theme', newTheme);
    });

    // scroll back to top button
    const scrollButton = document.getElementById('scroll-to-top');
    scrollButton?.addEventListener('click', () => {
        window.scrollTo({top: 0, behavior: 'smooth'});
    });
    window.addEventListener('scroll', () => {
        if (window.scrollY > 100) {
            scrollButton.classList.remove('d-none');
        } else {
            scrollButton.classList.add('d-none');
        }
    });
    document.getElementById('videoModal')?.addEventListener('hidden.bs.modal', function () {
        try {
            const player = videojs('videoPlayer');
            if (player && typeof player.dispose === 'function') {
                player.dispose();
            }
        } catch (error) {
            console.error('Error stopping the video player:', error);
        }
    });
    document.getElementById('confirmModal')?.addEventListener('hidden.bs.modal', function () {
        const vueInstance = window.vueInstance;
        if (vueInstance) {
            const modalConfirmExtras = document.getElementById('confirmModalExtras');
            if (modalConfirmExtras) {
                modalConfirmExtras.innerHTML = '';
            }
        }
    });
    document.getElementById('similarityModal')?.addEventListener('hidden.bs.modal', function () {
        const vueInstance = window.vueInstance;
        if (vueInstance) {
            console.log('Modal closed');
            vueInstance.currentFile = null;
            vueInstance.similarVideos = null;
        }
    });
    // init the modals - we only use one instance of each modal
    /*
    window.videoModal = new bootstrap.Modal(document.getElementById('videoModal'));
    window.confirmModal = new bootstrap.Modal(document.getElementById('confirmModal'));
    const similarityModalElement = document.getElementById('similarityModal');
    if (similarityModalElement) {
        window.similarityModal = new bootstrap.Modal(similarityModalElement, {backdrop: 'static'});
    }
    */



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

function open_sse_connection() {
    const eventSource = new EventSource('/sse');
    window.addEventListener('beforeunload', () => {
        eventSource.close();
        console.log('EventSource connection closed');
    });
    return eventSource;
}



function navigate(evt, url) {
    evt.preventDefault();
    history.replaceState(null, '', url);
    window.location.href = url;
}

document.querySelectorAll('a.nav-link, a.navbar-brand').forEach(link => {
    link.addEventListener('click', function(e) {
        navigate(e, this.getAttribute('href'));
    });
});