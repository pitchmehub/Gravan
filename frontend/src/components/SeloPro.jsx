import React from 'react'

/**
 * Selo "PRO" reutilizável para indicar que o compositor é assinante PRO.
 * Renderiza apenas quando `ativo` é true.
 *
 * Props:
 *   ativo  – boolean (obrigatório)
 *   size   – 'sm' | 'md' (default 'sm')
 *   title  – tooltip opcional
 */
export default function SeloPro({ ativo, size = 'sm', title = 'Compositor PRO' }) {
  if (!ativo) return null
  const styles = size === 'md'
    ? { padding: '3px 8px', fontSize: 11 }
    : { padding: '2px 6px', fontSize: 10 }
  return (
    <span
      title={title}
      data-testid="selo-pro"
      style={{
        display: 'inline-block',
        background: 'linear-gradient(135deg, #1e3a8a, #2563eb)',
        color: '#fff',
        fontWeight: 700,
        letterSpacing: 0.8,
        borderRadius: 4,
        verticalAlign: 'middle',
        marginLeft: 6,
        ...styles,
      }}
    >
      PRO
    </span>
  )
}

/**
 * Helper para checar se um perfil tem PRO efetivo (assinatura em dia).
 */
export function isPerfilPro(perfil) {
  if (!perfil) return false
  return (
    perfil.plano === 'PRO' &&
    ['ativa', 'cancelada', 'past_due'].includes(perfil.status_assinatura)
  )
}
