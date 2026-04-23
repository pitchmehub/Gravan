import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../lib/api'
import BotaoCurtir from '../components/BotaoCurtir'

export default function Biblioteca() {
  const [items, setItems]     = useState([])
  const [loading, setLoading] = useState(true)
  const [erro, setErro]       = useState('')
  const navigate = useNavigate()

  useEffect(() => { reload() }, [])

  async function reload() {
    try {
      setLoading(true)
      const d = await api.get('/favoritos')
      setItems(d || [])
    } catch (e) { setErro(e.message) }
    finally { setLoading(false) }
  }

  function moeda(cents) {
    return (cents / 100).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
  }

  return (
    <div data-testid="biblioteca-page" style={{ padding: '32px 20px', maxWidth: 1000, margin: '0 auto' }}>
      <header style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700 }}>Minha biblioteca</h1>
        <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>
          As obras que você curtiu ficam salvas aqui para ouvir e licenciar depois.
        </p>
      </header>

      {loading && <p style={{ color: 'var(--text-muted)' }}>Carregando…</p>}
      {erro && <p style={{ color: '#c0392b' }}>⚠ {erro}</p>}

      {!loading && !erro && items.length === 0 && (
        <div data-testid="biblioteca-vazia" style={{
          padding: 48, border: '1px dashed var(--border)', borderRadius: 12,
          textAlign: 'center', color: 'var(--text-muted)', fontSize: 13,
        }}>
          Sua biblioteca está vazia. Curta obras no catálogo — elas aparecerão aqui.
          <div style={{ marginTop: 14 }}>
            <button className="btn btn-primary" onClick={() => navigate('/descoberta')}>Ir para descoberta</button>
          </div>
        </div>
      )}

      {items.length > 0 && (
        <div style={{ display: 'grid', gap: 12 }}>
          {items.map((it, i) => {
            const o = it.obras || {}
            return (
              <div key={it.id || i} data-testid={`biblio-item-${i}`} style={{
                display: 'flex', alignItems: 'center', gap: 16, padding: 14,
                border: '1px solid var(--border)', borderRadius: 12, background: '#fff',
              }}>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontWeight: 600, fontSize: 15 }}>{o.nome || 'Obra removida'}</div>
                  <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                    {o.genero || 'Sem gênero'} · {o.perfis?.nome || '—'}
                    {o.preco_cents ? ` · ${moeda(o.preco_cents)}` : ''}
                  </div>
                </div>
                <BotaoCurtir obraId={o.id} onChange={v => !v && reload()} />
                {o.id && (
                  <button className="btn btn-primary"
                    style={{ fontSize: 12, padding: '6px 12px' }}
                    onClick={() => navigate(`/comprar/${o.id}`)}>
                    Licenciar
                  </button>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
