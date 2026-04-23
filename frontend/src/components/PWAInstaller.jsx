import React, { useEffect, useState } from 'react'

/**
 * Registra o service worker e mostra um prompt discreto pra instalar o app.
 *
 * Uso: <PWAInstaller /> dentro do App root.
 */
export default function PWAInstaller() {
  const [deferredPrompt, setDeferredPrompt] = useState(null)
  const [installed,      setInstalled]      = useState(false)
  const [dismissed,      setDismissed]      = useState(false)

  // 1. Registra o Service Worker + força update quando houver nova versão
  useEffect(() => {
    if (!('serviceWorker' in navigator)) return
    // Em dev não registra (evita cache de HMR)
    if (import.meta.env.DEV) return

    window.addEventListener('load', async () => {
      try {
        const reg = await navigator.serviceWorker.register('/sw.js')

        // Força checar update a cada load (pega novo sw.js rapidamente)
        reg.update().catch(() => {})

        // Se já tem um SW novo esperando, pede pra ele tomar controle
        if (reg.waiting) {
          reg.waiting.postMessage({ type: 'SKIP_WAITING' })
        }

        // Quando um novo SW for instalado, apenas ativa silenciosamente
        reg.addEventListener('updatefound', () => {
          const newWorker = reg.installing
          if (!newWorker) return
          newWorker.addEventListener('statechange', () => {
            if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
              // Novo SW pronto — ativa, mas NÃO recarrega a página
              // (evita reload no meio de submits/navegação do usuário)
              newWorker.postMessage({ type: 'SKIP_WAITING' })
            }
          })
        })

        // NÃO recarregamos automaticamente em 'controllerchange' — o reload
        // no meio de um submit (ex.: cadastrar obra) era percebido como
        // "a página atualizou sozinha". A nova versão entra em vigor na
        // próxima navegação natural do usuário.
      } catch { /* noop */ }
    })
  }, [])

  // 2. Escuta evento de "installable"
  useEffect(() => {
    function onPrompt(e) {
      e.preventDefault()
      // Só mostra o prompt se ainda não foi dispensado nessa sessão
      if (sessionStorage.getItem('pwa_dismissed') === '1') return
      setDeferredPrompt(e)
    }
    function onInstalled() {
      setInstalled(true)
      setDeferredPrompt(null)
    }
    window.addEventListener('beforeinstallprompt', onPrompt)
    window.addEventListener('appinstalled', onInstalled)
    return () => {
      window.removeEventListener('beforeinstallprompt', onPrompt)
      window.removeEventListener('appinstalled', onInstalled)
    }
  }, [])

  async function handleInstall() {
    if (!deferredPrompt) return
    deferredPrompt.prompt()
    await deferredPrompt.userChoice
    setDeferredPrompt(null)
  }

  function dismiss() {
    sessionStorage.setItem('pwa_dismissed', '1')
    setDismissed(true)
  }

  if (installed || dismissed || !deferredPrompt) return null

  return (
    <div style={{
      position: 'fixed',
      bottom: 16, left: 16, right: 16,
      maxWidth: 420, margin: '0 auto',
      padding: 14,
      background: 'linear-gradient(135deg,#BE123C,#09090B)',
      color: '#fff', borderRadius: 14,
      boxShadow: '0 10px 30px rgba(225,29,72,.4)',
      display: 'flex', alignItems: 'center', gap: 12,
      zIndex: 9999,
      animation: 'pwa-slide-up .3s ease-out',
    }}>
      <style>{`
        @keyframes pwa-slide-up {
          from { transform: translateY(40px); opacity: 0 }
          to   { transform: translateY(0);    opacity: 1 }
        }
      `}</style>
      <div style={{
        fontSize: 28, width: 40, height: 40, flexShrink: 0,
        background: 'rgba(255,255,255,.2)', borderRadius: 10,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}>♪</div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 13, fontWeight: 700 }}>Instalar Pitch.me</div>
        <div style={{ fontSize: 11, opacity: .9 }}>Abra direto da tela inicial</div>
      </div>
      <button
        onClick={handleInstall}
        style={{
          background: 'rgba(255,255,255,.12)', color: '#fff',
          border: 'none', padding: '8px 14px', borderRadius: 99,
          fontSize: 13, fontWeight: 700, cursor: 'pointer',
        }}>Instalar</button>
      <button
        onClick={dismiss}
        aria-label="Dispensar"
        style={{
          background: 'transparent', border: 'none', color: '#fff',
          opacity: .6, cursor: 'pointer', fontSize: 20, padding: 4,
        }}>×</button>
    </div>
  )
}
