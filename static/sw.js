const CACHE = 'food-diary-v1';

// App shell — pages and assets served by our own server
const SHELL = [
    '/',
    '/login',
    '/static/icons/icon-192.png',
    '/static/icons/icon-512.png',
];

// ── Install: pre-cache the shell ──────────────────────────────────────────────
self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE).then(cache => cache.addAll(SHELL))
    );
    self.skipWaiting();
});

// ── Activate: drop old caches ─────────────────────────────────────────────────
self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(keys =>
            Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
        )
    );
    self.clients.claim();
});

// ── Fetch strategy ────────────────────────────────────────────────────────────
self.addEventListener('fetch', event => {
    const { request } = event;
    const url = new URL(request.url);

    // API calls and report/export: always network, never cache
    if (url.pathname.startsWith('/api/') ||
        url.pathname.startsWith('/report') ||
        request.method !== 'GET') {
        return;
    }

    // External CDN (Tailwind): cache-first
    if (!url.hostname.includes('localhost') && !url.hostname.match(/^192\.|^10\.|^172\./)) {
        event.respondWith(
            caches.match(request).then(cached => cached || fetch(request).then(res => {
                const copy = res.clone();
                caches.open(CACHE).then(c => c.put(request, copy));
                return res;
            }))
        );
        return;
    }

    // App pages: network-first, fall back to cache
    event.respondWith(
        fetch(request)
            .then(res => {
                const copy = res.clone();
                caches.open(CACHE).then(c => c.put(request, copy));
                return res;
            })
            .catch(() => caches.match(request).then(cached => cached || offlinePage()))
    );
});

function offlinePage() {
    return new Response(
        `<!DOCTYPE html><html><head><meta charset="UTF-8">
        <meta name="viewport" content="width=device-width,initial-scale=1">
        <title>Offline — Food Diary</title>
        <style>
            body{font-family:system-ui,sans-serif;display:flex;align-items:center;
                 justify-content:center;min-height:100vh;margin:0;background:#f3f4f6}
            .box{text-align:center;padding:2rem}
            .icon{font-size:3rem;margin-bottom:1rem}
            h1{color:#1f2937;margin:0 0 .5rem}
            p{color:#6b7280}
            button{margin-top:1.5rem;padding:.75rem 1.5rem;background:#22c55e;
                   color:#fff;border:none;border-radius:.5rem;font-size:1rem;cursor:pointer}
        </style></head>
        <body><div class="box">
            <div class="icon">🥗</div>
            <h1>You're offline</h1>
            <p>Connect to your home network to use Food Diary.</p>
            <button onclick="location.reload()">Try again</button>
        </div></body></html>`,
        { headers: { 'Content-Type': 'text/html' } }
    );
}
