var staticCacheName = "django-pwa-v" + new Date().getTime();
var filesToCache = [
    '/offline/',
    '/static/css/django-pwa-app.css',
    '/static/images/icons/icon-72x72.png',
    '/static/images/icons/icon-96x96.png',
    '/static/images/icons/icon-128x128.png',
    '/static/images/icons/icon-144x144.png',
    '/static/images/icons/icon-152x152.png',
    '/static/images/icons/icon-192x192.png',
    '/static/images/icons/icon-384x384.png',
    '/static/images/icons/icon-512x512.png',
    '/static/images/icons/splash-640x1136.png',
    '/static/images/icons/splash-750x1334.png',
    '/static/images/icons/splash-1242x2208.png',
    '/static/images/icons/splash-1125x2436.png',
    '/static/images/icons/splash-828x1792.png',
    '/static/images/icons/splash-1242x2688.png',
    '/static/images/icons/splash-1536x2048.png',
    '/static/images/icons/splash-1668x2224.png',
    '/static/images/icons/splash-1668x2388.png',
    '/static/images/icons/splash-2048x2732.png'
];

// Cache on install
self.addEventListener("install", event => {
    this.skipWaiting();
    event.waitUntil(
        caches.open(staticCacheName)
            .then(cache => {
                return cache.addAll(filesToCache);
            })
    )
});

// Clear cache on activate
self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(cacheNames => {
            return Promise.all(
                cacheNames
                    .filter(cacheName => (cacheName.startsWith("django-pwa-")))
                    .filter(cacheName => (cacheName !== staticCacheName))
                    .map(cacheName => caches.delete(cacheName))
            );
        })
    );
});

// Serve from Cache
self.addEventListener("fetch", event => {
    // Never intercept anything but GET. Re-issuing event.request replays a body stream
    // that has already been consumed; WebKit drops the multipart payload, so a menu
    // upload reaches Django with an empty request.FILES and the form answers "campo
    // obbligatorio" even though a file was picked (#273).
    if (event.request.method !== "GET") {
        return;
    }
    // Only a top-level navigation may fall back to the offline page. htmx fetches its
    // partials with the same GET method, so answering one of those with the whole
    // /offline/ document made htmx swap that markup into its target — an offline page
    // nested inside the upload modal. Re-throwing instead lets the request fail for real,
    // so htmx fires htmx:sendError and the page stays untouched (#276).
    const isNavigation = event.request.mode === "navigate";
    event.respondWith(
        caches.match(event.request)
            .then(response => {
                return response || fetch(event.request);
            })
            .catch(error => {
                if (isNavigation) {
                    return caches.match('/offline/');
                }
                throw error;
            })
    )
});

// Gestione notifiche push per django-webpush
self.addEventListener("push", function(event) {
  let data = {};
  try {
    data = event.data.json();
  } catch (e) {
    data = { head: "Notifica", body: "Hai una nuova notifica." };
  }
  const options = {
    body: data.body,
    icon: data.icon || "/static/img/notification-bell.png",
    data: { url: data.url || "/" }
  };
  // A tag coalesces a redelivered push into one notification instead of stacking
  // duplicates (mainly an iOS issue); renotify still alerts on a genuine new push.
  if (data.tag) {
    options.tag = data.tag;
    options.renotify = true;
  }
  event.waitUntil(
    self.registration.showNotification(data.head, options)
  );
});

self.addEventListener("notificationclick", function(event) {
  event.notification.close();
  if (event.notification.data && event.notification.data.url) {
    event.waitUntil(clients.openWindow(event.notification.data.url));
  }
});
