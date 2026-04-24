import React, { useEffect, useState } from 'react'

export default function PWAInstall() {
  const [deferredPrompt, setDeferredPrompt] = useState(null)
  const [showPrompt,     setShowPrompt]     = useState(false)
  const [isIOS,          setIsIOS]          = useState(false)

  useEffect(() => {
    // Detecta iOS (iOS não dispara beforeinstallprompt)
    const iOS = /iPad|iPhone|iPod/.test(navigator.userAgent) && !window.MSStream
    setIsIOS(iOS)

    // Verifica se já está instalado
    const isStandalone = window.matchMedia('(display-mode: standalone)').matches ||
                        window.navigator.standalone === true
    if (isStandalone) return

    // Se ja dispensou hoje, nao mostra de novo
    const dispensed = localStorage.getItem('pwa_install_dispensed')
    if (dispensed && Date.now() - Number(dispensed) < 7 * 24 * 60 * 60 * 1000) return

    const handler = (e) => {
      e.preventDefault()
      setDeferredPrompt(e)
      setShowPrompt(true)
    }
    window.addEventListener('beforeinstallprompt', handler)

    // Mostra dica manual para iOS depois de 5s
    if (iOS) {
      setTimeout(() => setShowPrompt(true), 5000)
    }

    return () => window.removeEventListener('beforeinstallprompt', handler)
  }, [])

  async function handleInstall() {
    if (deferredPrompt) {
      deferredPrompt.prompt()
      const { outcome } = await deferredPrompt.userChoice
      if (outcome === 'accepted') setShowPrompt(false)
      setDeferredPrompt(null)
    }
  }

  function dismiss() {
    setShowPrompt(false)
    localStorage.setItem('pwa_install_dispensed', String(Date.now()))
  }

  if (!showPrompt) return null

  return (
    <div style={{
      position: 'fixed',
      bottom: 16, left: 16, right: 16,
      maxWidth: 420, margin: '0 auto',
      background: 'linear-gradient(135deg,#083257,#09090B)',
      color: '#fff', padding: 16,
      borderRadius: 16, boxShadow: '0 12px 40px rgba(12,68,124,.4)',
      zIndex: 2000,
      display: 'flex', alignItems: 'center', gap: 12,
    }}>
      <div style={{
        width: 44, height: 44, borderRadius: 12,
        background: 'rgba(255,255,255,.2)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: 22, flexShrink: 0,
      }}>♪</div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 13, fontWeight: 700 }}>Instalar Gravan</div>
        <div style={{ fontSize: 11, opacity: .9, lineHeight: 1.4 }}>
          {isIOS
            ? 'Toque em [⎋] → "Adicionar à Tela de Início"'
            : 'Adicione à tela inicial para acesso rápido'
          }
        </div>
      </div>
      {!isIOS && (
        <button
          onClick={handleInstall}
          style={{
            background: 'rgba(255,255,255,.12)', color: '#fff',
            border: 'none', padding: '8px 14px', borderRadius: 99,
            fontSize: 12, fontWeight: 700, cursor: 'pointer',
            whiteSpace: 'nowrap',
          }}
        >
          Instalar
        </button>
      )}
      <button
        onClick={dismiss}
        style={{
          background: 'transparent', border: 'none',
          color: 'rgba(255,255,255,.7)', fontSize: 22, cursor: 'pointer',
          padding: 0, width: 24, height: 24,
        }}
      >×</button>
    </div>
  )
}
