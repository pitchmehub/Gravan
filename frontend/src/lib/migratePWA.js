export function migratePWA() {
  try {
    const KEY = 'gravan_design1_migrated_v4'
    if (localStorage.getItem(KEY) === '1') return
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.getRegistrations().then(function (regs) {
        regs.forEach(function (r) { r.unregister().catch(function () {}) })
      }).catch(function () {})
    }
    if ('caches' in window) {
      caches.keys().then(function (keys) {
        return Promise.all(keys.map(function (k) { return caches.delete(k) }))
      }).then(function () {
        localStorage.setItem(KEY, '1')
      }).catch(function () { localStorage.setItem(KEY, '1') })
    } else {
      localStorage.setItem(KEY, '1')
    }
  } catch (e) { /* noop */ }
}
