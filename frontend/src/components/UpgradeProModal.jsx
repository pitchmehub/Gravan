import React from 'react'
import { useNavigate } from 'react-router-dom'

/**
 * Modal genérico de upgrade para PRO.
 *
 * Props:
 *   open      – boolean
 *   onClose   – fn()
 *   titulo    – string opcional (default contextual ao preço)
 *   mensagem  – string opcional
 *   ctaLabel  – default "Assinar PRO agora"
 *   contexto  – objeto opcional (ex.: dados da obra que o usuário tentou salvar).
 *               É passado para /planos via state, para a tela poder retomar.
 */
export default function UpgradeProModal({
  open,
  onClose,
  titulo = 'Esta funcionalidade é exclusiva do plano PRO',
  mensagem = 'Assine o plano PRO e tenha acesso a compradores de alto valor, comissão menor (15%) e analytics completo.',
  ctaLabel = 'Assinar PRO agora',
  contexto,
}) {
  const navigate = useNavigate()
  if (!open) return null

  return (
    <div
      data-testid="upgrade-pro-modal"
      onClick={onClose}
      style={{
        position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.55)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        zIndex: 9999, padding: 16,
      }}
    >
      <div
        onClick={e => e.stopPropagation()}
        style={{
          background: '#fff', borderRadius: 16, maxWidth: 460, width: '100%',
          padding: 28, boxShadow: '0 20px 60px rgba(0,0,0,0.3)', textAlign: 'center',
        }}
      >
        <div style={{
          display: 'inline-block', padding: '4px 12px',
          background: 'linear-gradient(135deg, #1e3a8a, #2563eb)', color: '#fff',
          fontSize: 11, fontWeight: 800, letterSpacing: 1.2, borderRadius: 4,
          marginBottom: 16,
        }}>
          PLANO PRO
        </div>

        <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 10, lineHeight: 1.3 }}>
          {titulo}
        </h2>
        <p style={{ color: 'var(--text-muted, #71717A)', fontSize: 14, marginBottom: 22, lineHeight: 1.5 }}>
          {mensagem}
        </p>

        <ul style={{ textAlign: 'left', fontSize: 13, color: '#333', listStyle: 'none', padding: 0, marginBottom: 22 }}>
          <li style={{ padding: '6px 0' }}>✓ Precificação até R$ 10.000 por obra</li>
          <li style={{ padding: '6px 0' }}>✓ Comissão de 15% (em vez de 20%)</li>
          <li style={{ padding: '6px 0' }}>✓ Receba ofertas de exclusividade</li>
          <li style={{ padding: '6px 0' }}>✓ Selo PRO no seu perfil e obras</li>
          <li style={{ padding: '6px 0' }}>✓ Analytics completo de receita e ofertas</li>
        </ul>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          <button
            data-testid="btn-assinar-pro"
            className="btn btn-primary"
            onClick={() => {
              navigate('/planos', { state: contexto ? { contexto } : undefined })
            }}
            style={{ padding: '12px 18px', fontSize: 14, fontWeight: 600 }}
          >
            {ctaLabel}
          </button>
          <button
            type="button"
            onClick={onClose}
            style={{
              background: 'none', border: 'none', color: 'var(--text-muted, #71717A)',
              fontSize: 13, cursor: 'pointer', padding: 8,
            }}
          >
            Agora não
          </button>
        </div>
      </div>
    </div>
  )
}
