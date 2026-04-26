/**
 * Service Worker Gravan — Design 1 edition
 * CSS/JS/fonts usam networkFirst para sempre refletir updates do server.
 * Push notifications (PWA) — exibem notificações vindas do backend.
 */

const VERSION       = 'gravan-v5-design1-push-20260426'
const STATIC_CACHE  = `static-${VERSION}`
const IMG_CACHE     = `img-${VERSION}`
const RUNTIME_CACHE = `runtime-${VERSION}`

const PRECACHE_URLS = ['/', '/manifest.webmanifest']

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then(cache => cache.addAll(PRECACHE_URLS).catch(() => {}))
      .then(() => self.skipWaiting())
  )
})

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => !k.includes(VERSION)).map(k => caches.delete(k)))
    ).then(() => self.clients.claim())
  )
})

self.addEventListener('fetch', event => {
  const { request } = event
  const url = new URL(request.url)

  if (request.method !== 'GET') return
  if (url.pathname.startsWith('/api/')) return
  if (url.hostname.includes('supabase.co') || url.hostname.includes('stripe.com')) return

  // HTML / navigation — sempre network-first
  if (request.mode === 'navigate' || (request.headers.get('accept') || '').includes('text/html')) {
    event.respondWith(networkFirst(request, RUNTIME_CACHE))
    return
  }

  // Images — cache-first é ok (assets estáveis)
  if (request.destination === 'image') {
    event.respondWith(cacheFirst(request, IMG_CACHE))
    return
  }

  // CSS / JS / fontes — networkFirst para pegar updates do tema imediatamente
  if (['style', 'script', 'font'].includes(request.destination)) {
    event.respondWith(networkFirst(request, STATIC_CACHE))
    return
  }
})

async function networkFirst(request, cacheName) {
  try {
    const fresh = await fetch(request)
    if (fresh.ok) {
      const cache = await caches.open(cacheName)
      cache.put(request, fresh.clone()).catch(() => {})
    }
    return fresh
  } catch (_) {
    const cached = await caches.match(request)
    return cached || Response.error()
  }
}

async function cacheFirst(request, cacheName) {
  const cached = await caches.match(request)
  if (cached) return cached
  try {
    const fresh = await fetch(request)
    if (fresh.ok) {
      const cache = await caches.open(cacheName)
      cache.put(request, fresh.clone()).catch(() => {})
    }
    return fresh
  } catch (_) {
    return Response.error()
  }
}

/* ───────────────── PUSH NOTIFICATIONS (PWA) ───────────────── */

self.addEventListener('push', event => {
  let data = {}
  try { data = event.data ? event.data.json() : {} } catch (_) { data = { title: event.data?.text?.() || 'Gravan' } }

  const title = data.title || 'Gravan'
  const options = {
    body:    data.body || '',
    icon:    '/icon-192.png',
    badge:   '/icon-192.png',
    tag:     data.tag || 'gravan',
    renotify: true,
    data:    { url: data.url || '/dashboard', extras: data.data || {} },
  }
  event.waitUntil(self.registration.showNotification(title, options))
})

self.addEventListener('notificationclick', event => {
  event.notification.close()
  const targetUrl = (event.notification.data && event.notification.data.url) || '/dashboard'
  event.waitUntil((async () => {
    const all = await self.clients.matchAll({ type: 'window', includeUncontrolled: true })
    // Se já existe uma aba aberta do app, foca e navega
    for (const client of all) {
      if (client.url.includes(self.location.origin)) {
        client.focus()
        if ('navigate' in client) client.navigate(targetUrl).catch(() => {})
        return
      }
    }
    // Caso contrário, abre uma nova
    await self.clients.openWindow(targetUrl)
  })())
})
