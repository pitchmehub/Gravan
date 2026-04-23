import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { usePlayer } from '../contexts/PlayerContext'
import { api } from '../lib/api'

function fmt(cents) {
  return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format((cents ?? 0) / 100)
}

const STATUS = {
  pendente:    { bg: 'var(--warning-bg)', cor: 'var(--warning)', label: 'Aguardando pagamento' },
  confirmada:  { bg: 'var(--success-bg)', cor: 'var(--success)', label: '✓ Confirmada'         },
  cancelada:   { bg: 'var(--error-bg)',   cor: 'var(--error)',   label: '✕ Cancelada'          },
}

export default function Compras() {
  const navigate = useNavigate()
  const { playObra, obra: obraAtual, playing } = usePlayer()
  const [compras, setCompras] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.get('/perfis/me/compras')
      .then(setCompras)
      .catch(() => setCompras([]))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div style={{ padding: 32 }}><p style={{ color: 'var(--text-muted)' }}>Carregando…</p></div>

  return (
    <div style={{ padding: 32, maxWidth: 920 }}>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 24, fontWeight: 800 }}>Minhas compras</h1>
        <p style={{ color: 'var(--text-muted)', fontSize: 14 }}>
          {compras.length} licença{compras.length !== 1 ? 's' : ''} adquirida{compras.length !== 1 ? 's' : ''}
        </p>
      </div>

      {compras.length === 0 ? (
        <div style={{
          padding: 60, textAlign: 'center',
          background: 'var(--surface-2)', borderRadius: 16,
        }}>
          <div style={{ fontSize: 48, opacity: .3, marginBottom: 12 }}>◉</div>
          <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 8 }}>Você ainda não comprou composições</h2>
          <p style={{ color: 'var(--text-muted)', fontSize: 14, marginBottom: 16 }}>
            Explore o catálogo e adquira sua primeira licença.
          </p>
          <button className="btn btn-primary" onClick={() => navigate('/descoberta')}>
            Explorar catálogo
          </button>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {compras.map(c => {
            const isPlaying = obraAtual?.id === c.obra_id && playing
            const badge = STATUS[c.status] ?? STATUS.pendente
            return (
              <div key={c.id} style={{
                padding: 16, background: 'var(--surface)',
                border: '1px solid var(--border)', borderRadius: 12,
                display: 'flex', alignItems: 'center', gap: 14,
              }}>
                {c.audio_path && c.status === 'confirmada' && (
                  <button
                    onClick={() => playObra({
                      id: c.obra_id, nome: c.obra_nome, audio_path: c.audio_path,
                      titular_nome: c.titular_nome,
                    })}
                    style={{
                      width: 44, height: 44, borderRadius: 8,
                      background: 'linear-gradient(135deg,#BE123C,#09090B)',
                      color: '#fff', border: 'none', cursor: 'pointer',
                      fontSize: 14, flexShrink: 0,
                    }}>
                    {isPlaying ? '⏸' : '▶'}
                  </button>
                )}
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 15, fontWeight: 700 }}>{c.obra_nome}</div>
                  <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                    {c.titular_nome} {c.genero && `· ${c.genero}`} · {fmt(c.valor_cents)} · {c.metodo}
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>
                    {new Date(c.created_at).toLocaleString('pt-BR')}
                  </div>
                </div>
                <span style={{
                  fontSize: 11, fontWeight: 600, padding: '4px 12px', borderRadius: 99,
                  background: badge.bg, color: badge.cor,
                }}>{badge.label}</span>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
