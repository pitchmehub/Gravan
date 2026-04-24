/**
 * Service Worker Gravan — Design 1 edition
 * CSS/JS/fonts usam networkFirst para sempre refletir updates do server.
 */

const VERSION       = 'gravan-v3-design1-20260421'
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

  event.respondWith(networkFirst(request, RUNTIME_CACHE))
})

async function networkFirst(request, cacheName) {
  try {
    const res = await fetch(request)
    if (res && res.status === 200 && res.type === 'basic') {
      const cache = await caches.open(cacheName)
      cache.put(request, res.clone()).catch(() => {})
    }
    return res
  } catch {
    const cached = await caches.match(request)
    return cached || caches.match('/') || new Response('Offline', { status: 503 })
  }
}

async function cacheFirst(request, cacheName) {
  const cached = await caches.match(request)
  if (cached) return cached
  try {
    const res = await fetch(request)
    if (res && res.status === 200 && res.type === 'basic') {
      const cache = await caches.open(cacheName)
      cache.put(request, res.clone()).catch(() => {})
    }
    return res
  } catch {
    return new Response('', { status: 504 })
  }
}

self.addEventListener('message', event => {
  if (event.data?.type === 'SKIP_WAITING') self.skipWaiting()
  if (event.data?.type === 'CLEAR_CACHES') {
    event.waitUntil(caches.keys().then(keys => Promise.all(keys.map(k => caches.delete(k)))))
  }
})
