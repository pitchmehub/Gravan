import React, { useEffect, useState } from 'react'
import { api } from '../lib/api'

/**
 * Botão de curtir (favoritar) para uma obra.
 * Optimistic UI + sincroniza com o backend.
 */
export default function BotaoCurtir({ obraId, size = 18, onChange }) {
  const [favoritada, setFav]   = useState(false)
  const [loading, setLoading]  = useState(false)

  useEffect(() => {
    let cancelled = false
    if (!obraId) return
    api.get(`/favoritos/status/${obraId}`)
      .then(d => { if (!cancelled) setFav(!!d?.favoritada) })
      .catch(() => {})
    return () => { cancelled = true }
  }, [obraId])

  async function toggle(e) {
    e?.stopPropagation?.()
    if (loading) return
    const next = !favoritada
    setFav(next); setLoading(true)
    try {
      if (next) await api.post(`/favoritos/${obraId}`, {})
      else      await api.delete(`/favoritos/${obraId}`)
      onChange?.(next)
    } catch (err) {
      setFav(!next)
      alert('Não foi possível atualizar a curtida: ' + err.message)
    } finally { setLoading(false) }
  }

  return (
    <button
      data-testid={`curtir-${obraId}`}
      aria-label={favoritada ? 'Descurtir' : 'Curtir'}
      onClick={toggle}
      style={{
        background: 'transparent', border: 'none', cursor: 'pointer',
        padding: 4, display: 'inline-flex', alignItems: 'center',
        color: favoritada ? 'var(--brand)' : 'var(--text-muted)',
        transition: 'transform .15s',
      }}
      onMouseEnter={e => { e.currentTarget.style.transform = 'scale(1.15)' }}
      onMouseLeave={e => { e.currentTarget.style.transform = 'scale(1)' }}
    >
      <svg width={size} height={size} viewBox="0 0 24 24" fill={favoritada ? 'currentColor' : 'none'} stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/>
      </svg>
    </button>
  )
}
