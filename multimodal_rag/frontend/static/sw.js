// Service Worker for Multimodal RAG PWA
const CACHE_NAME = 'multimodal-rag-v1.0.0';
const RUNTIME_CACHE = 'runtime-cache-v1';
const API_CACHE = 'api-cache-v1';

// Resources to cache on install
const STATIC_ASSETS = [
    '/',
    '/static/css/styles.css',
    '/static/js/app.js',
    '/static/manifest.json',
    '/static/images/icon-192x192.png',
    '/static/images/icon-512x512.png'
];

// API endpoints that can be cached
const CACHEABLE_API_ENDPOINTS = [
    '/api/stats',
    '/api/graph/health'
];

// Maximum age for cached API responses (in milliseconds)
const API_CACHE_MAX_AGE = 5 * 60 * 1000; // 5 minutes

// Install event - cache static assets
self.addEventListener('install', (event) => {
    console.log('[Service Worker] Installing...');

    event.waitUntil(
        caches.open(CACHE_NAME)
            .then((cache) => {
                console.log('[Service Worker] Caching static assets');
                return cache.addAll(STATIC_ASSETS);
            })
            .then(() => {
                console.log('[Service Worker] Installation complete');
                return self.skipWaiting(); // Activate immediately
            })
            .catch((error) => {
                console.error('[Service Worker] Installation failed:', error);
            })
    );
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
    console.log('[Service Worker] Activating...');

    event.waitUntil(
        caches.keys()
            .then((cacheNames) => {
                return Promise.all(
                    cacheNames
                        .filter((cacheName) => {
                            // Remove old caches
                            return cacheName !== CACHE_NAME &&
                                cacheName !== RUNTIME_CACHE &&
                                cacheName !== API_CACHE;
                        })
                        .map((cacheName) => {
                            console.log('[Service Worker] Deleting old cache:', cacheName);
                            return caches.delete(cacheName);
                        })
                );
            })
            .then(() => {
                console.log('[Service Worker] Activation complete');
                return self.clients.claim(); // Take control immediately
            })
    );
});

// Fetch event - serve from cache, fallback to network
self.addEventListener('fetch', (event) => {
    const { request } = event;
    const url = new URL(request.url);

    // Skip non-GET requests
    if (request.method !== 'GET') {
        return;
    }

    // Skip chrome-extension and other non-http(s) requests
    if (!url.protocol.startsWith('http')) {
        return;
    }

    // Handle API requests differently
    if (url.pathname.startsWith('/api/')) {
        event.respondWith(handleAPIRequest(request, url));
        return;
    }

    // Handle static assets and pages
    event.respondWith(handleStaticRequest(request));
});

// Handle static asset requests (Cache First strategy)
async function handleStaticRequest(request) {
    try {
        // Try cache first
        const cachedResponse = await caches.match(request);
        if (cachedResponse) {
            console.log('[Service Worker] Serving from cache:', request.url);
            return cachedResponse;
        }

        // Fetch from network
        console.log('[Service Worker] Fetching from network:', request.url);
        const networkResponse = await fetch(request);

        // Cache successful responses
        if (networkResponse.ok) {
            const cache = await caches.open(RUNTIME_CACHE);
            cache.put(request, networkResponse.clone());
        }

        return networkResponse;
    } catch (error) {
        console.error('[Service Worker] Fetch failed:', error);

        // Return offline page for navigation requests
        if (request.mode === 'navigate') {
            const cache = await caches.open(CACHE_NAME);
            const cachedResponse = await cache.match('/');
            if (cachedResponse) {
                return cachedResponse;
            }
        }

        // Return a basic offline response
        return new Response(
            JSON.stringify({
                error: 'Offline',
                message: 'You are currently offline. Please check your internet connection.'
            }),
            {
                status: 503,
                statusText: 'Service Unavailable',
                headers: new Headers({
                    'Content-Type': 'application/json'
                })
            }
        );
    }
}

// Handle API requests (Network First with cache fallback)
async function handleAPIRequest(request, url) {
    const isCacheable = CACHEABLE_API_ENDPOINTS.some(endpoint =>
        url.pathname.startsWith(endpoint)
    );

    try {
        // Try network first
        const networkResponse = await fetch(request);

        // Cache successful GET requests for cacheable endpoints
        if (networkResponse.ok && isCacheable) {
            const cache = await caches.open(API_CACHE);
            const responseToCache = networkResponse.clone();

            // Add timestamp to check cache freshness
            const headers = new Headers(responseToCache.headers);
            headers.set('sw-cache-time', Date.now().toString());

            const cachedResponse = new Response(
                await responseToCache.blob(),
                {
                    status: responseToCache.status,
                    statusText: responseToCache.statusText,
                    headers: headers
                }
            );

            cache.put(request, cachedResponse);
        }

        return networkResponse;
    } catch (error) {
        console.log('[Service Worker] Network failed, trying cache:', url.pathname);

        // If network fails, try cache
        if (isCacheable) {
            const cachedResponse = await caches.match(request);

            if (cachedResponse) {
                const cacheTime = cachedResponse.headers.get('sw-cache-time');
                const isExpired = cacheTime &&
                    (Date.now() - parseInt(cacheTime)) > API_CACHE_MAX_AGE;

                if (!isExpired) {
                    console.log('[Service Worker] Serving from API cache:', url.pathname);
                    return cachedResponse;
                } else {
                    console.log('[Service Worker] Cached API response expired');
                }
            }
        }

        // Return error response
        return new Response(
            JSON.stringify({
                error: 'Offline',
                message: 'Unable to fetch data. Please check your internet connection.',
                cached: false
            }),
            {
                status: 503,
                statusText: 'Service Unavailable',
                headers: new Headers({
                    'Content-Type': 'application/json'
                })
            }
        );
    }
}

// Handle background sync for offline uploads
self.addEventListener('sync', (event) => {
    console.log('[Service Worker] Background sync triggered:', event.tag);

    if (event.tag === 'sync-uploads') {
        event.waitUntil(syncUploadQueue());
    }
});

// Sync queued uploads when back online
async function syncUploadQueue() {
    try {
        const cache = await caches.open('upload-queue');
        const requests = await cache.keys();

        console.log(`[Service Worker] Syncing ${requests.length} queued uploads`);

        for (const request of requests) {
            try {
                await fetch(request);
                await cache.delete(request);
                console.log('[Service Worker] Synced upload:', request.url);
            } catch (error) {
                console.error('[Service Worker] Failed to sync upload:', error);
            }
        }
    } catch (error) {
        console.error('[Service Worker] Sync failed:', error);
    }
}

// Handle push notifications (for future features)
self.addEventListener('push', (event) => {
    console.log('[Service Worker] Push received');

    let notificationData = {
        title: 'Multimodal RAG',
        body: 'You have a new notification',
        icon: '/static/images/icon-192x192.png',
        badge: '/static/images/icon-72x72.png'
    };

    if (event.data) {
        try {
            notificationData = event.data.json();
        } catch (error) {
            notificationData.body = event.data.text();
        }
    }

    event.waitUntil(
        self.registration.showNotification(notificationData.title, {
            body: notificationData.body,
            icon: notificationData.icon,
            badge: notificationData.badge,
            vibrate: [200, 100, 200],
            data: notificationData.data
        })
    );
});

// Handle notification clicks
self.addEventListener('notificationclick', (event) => {
    console.log('[Service Worker] Notification clicked');
    event.notification.close();

    event.waitUntil(
        clients.openWindow(event.notification.data?.url || '/')
    );
});

// Listen for messages from the main thread
self.addEventListener('message', (event) => {
    console.log('[Service Worker] Message received:', event.data);

    if (event.data.type === 'SKIP_WAITING') {
        self.skipWaiting();
    }

    if (event.data.type === 'CLEAR_CACHE') {
        event.waitUntil(
            caches.keys().then((cacheNames) => {
                return Promise.all(
                    cacheNames.map((cacheName) => caches.delete(cacheName))
                );
            })
        );
    }

    if (event.data.type === 'CACHE_URLS') {
        event.waitUntil(
            caches.open(RUNTIME_CACHE).then((cache) => {
                return cache.addAll(event.data.urls);
            })
        );
    }
});

console.log('[Service Worker] Script loaded');
