/**
 * Helpers de Web Push (PWA) — assinatura, cancelamento, status.
 */
import { api } from './api'

function urlBase64ToUint8Array(base64String) {
  const padding = '='.repeat((4 - base64String.length % 4) % 4)
  const base64  = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/')
  const raw     = window.atob(base64)
  const out     = new Uint8Array(raw.length)
  for (let i = 0; i < raw.length; i++) out[i] = raw.charCodeAt(i)
  return out
}

export function isPushSupported() {
  return typeof window !== 'undefined'
      && 'serviceWorker' in navigator
      && 'PushManager' in window
      && 'Notification' in window
}

export async function getPushStatus() {
  if (!isPushSupported()) return { supported: false, permission: 'unsupported', subscribed: false }
  let subscribed = false
  try {
    const reg = await navigator.serviceWorker.ready
    const sub = await reg.pushManager.getSubscription()
    subscribed = !!sub
  } catch (_) {}
  return { supported: true, permission: Notification.permission, subscribed }
}

/** Pede permissão e registra a assinatura no backend. */
export async function subscribePush() {
  if (!isPushSupported()) throw new Error('Este navegador não suporta notificações push.')

  // Pede permissão
  let perm = Notification.permission
  if (perm === 'default') perm = await Notification.requestPermission()
  if (perm !== 'granted') throw new Error('Permissão para notificações foi negada.')

  // Pega chave pública do servidor
  const meta = await api.get('/push/public-key')
  if (!meta?.public_key) throw new Error('Push não está configurado no servidor.')

  const reg = await navigator.serviceWorker.ready
  let sub = await reg.pushManager.getSubscription()
  if (!sub) {
    sub = await reg.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(meta.public_key),
    })
  }

  // Envia para o backend
  const json = sub.toJSON()
  await api.post('/push/subscribe', {
    endpoint: json.endpoint,
    keys:     json.keys,
  })
  return true
}

export async function unsubscribePush() {
  if (!isPushSupported()) return false
  const reg = await navigator.serviceWorker.ready
  const sub = await reg.pushManager.getSubscription()
  if (!sub) return true
  try {
    await api.post('/push/unsubscribe', { endpoint: sub.endpoint })
  } catch (_) {}
  await sub.unsubscribe().catch(() => {})
  return true
}

export async function sendTestPush() {
  return api.post('/push/test', {})
}
