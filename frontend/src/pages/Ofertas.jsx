import { useEffect, useState } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { api } from '../lib/api'

function fmt(cents) {
  return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format((cents ?? 0) / 100)
}

const STATUS_STYLE = {
  pendente:  { bg: '#FEF3C7', color: '#92400E' },
  aceita:    { bg: '#D1FAE5', color: '#065F46' },
  recusada:  { bg: '#FEE2E2', color: '#991B1B' },
  expirada:  { bg: '#F3F4F6', color: '#6B7280' },
}

export default function Ofertas() {
  const { perfil } = useAuth()
  const isCompositor = perfil?.role === 'compositor'

  const [ofertas,  setOfertas]  = useState([])
  const [loading,  setLoading]  = useState(true)
  const [respondendo, setRespondendo] = useState(null)

  useEffect(() => {
    const endpoint = isCompositor ? '/catalogo/ofertas/recebidas' : '/catalogo/ofertas/enviadas'
    api.get(endpoint)
      .then(setOfertas)
      .finally(() => setLoading(false))
  }, [isCompositor])

  async function responder(ofertaId, status) {
    setRespondendo(ofertaId)
    try {
      const updated = await api.patch(`/catalogo/ofertas/${ofertaId}/responder`, { status })
      setOfertas(prev => prev.map(o => o.id === ofertaId ? { ...o, ...updated } : o))
    } catch (e) {
      alert(e.message)
    } finally {
      setRespondendo(null)
    }
  }

  if (loading) return <p className="text-muted">Carregando ofertas…</p>

  return (
    <div style={{ maxWidth: 720 }}>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 22, fontWeight: 600 }}>
          {isCompositor ? 'Ofertas Recebidas' : 'Minhas Ofertas'}
        </h1>
        <p className="text-muted">
          {isCompositor
            ? 'Contrapropostas de intérpretes para suas obras'
            : 'Acompanhe o status das suas contrapropostas'}
        </p>
      </div>

      {ofertas.length === 0 && (
        <div className="card" style={{ textAlign: 'center', padding: 40 }}>
          <p style={{ fontSize: 32, marginBottom: 8 }}>✉</p>
          <p className="text-muted">Nenhuma oferta encontrada.</p>
        </div>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {ofertas.map(oferta => {
          const s = STATUS_STYLE[oferta.status] ?? STATUS_STYLE.expirada
          return (
            <div key={oferta.id} className="card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 10 }}>
                <div>
                  <div style={{ fontWeight: 600, fontSize: 15 }}>
                    {oferta.obras?.nome ?? '—'}
                  </div>
                  <div className="text-muted" style={{ fontSize: 13 }}>
                    {isCompositor
                      ? `De: ${oferta.perfis?.nome ?? oferta.interprete_id}`
                      : `Preço original: ${fmt(oferta.obras?.preco_cents)}`}
                    {' · '}
                    {new Date(oferta.created_at).toLocaleDateString('pt-BR')}
                  </div>
                </div>
                <span style={{
                  padding: '3px 12px', borderRadius: 99, fontSize: 12, fontWeight: 500,
                  background: s.bg, color: s.color,
                }}>
                  {oferta.status}
                </span>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: oferta.mensagem ? 10 : 0 }}>
                <div>
                  <div className="text-muted" style={{ fontSize: 12 }}>Valor ofertado</div>
                  <div style={{ fontSize: 18, fontWeight: 700, color: 'var(--brand)' }}>
                    {fmt(oferta.valor_cents)}
                  </div>
                </div>
                {oferta.obras?.preco_cents && (
                  <div>
                    <div className="text-muted" style={{ fontSize: 12 }}>Preço original</div>
                    <div style={{ fontSize: 14, color: 'var(--text-secondary)' }}>
                      {fmt(oferta.obras.preco_cents)}
                    </div>
                  </div>
                )}
              </div>

              {oferta.mensagem && (
                <div style={{
                  background: 'var(--surface-2)', borderRadius: 'var(--radius-md)',
                  padding: '8px 12px', fontSize: 13, color: 'var(--text-secondary)',
                  marginBottom: 10,
                }}>
                  "{oferta.mensagem}"
                </div>
              )}

              {/* Ações para compositor */}
              {isCompositor && oferta.status === 'pendente' && (
                <div style={{ display: 'flex', gap: 8 }}>
                  <button
                    className="btn btn-primary btn-sm"
                    disabled={respondendo === oferta.id}
                    onClick={() => responder(oferta.id, 'aceita')}
                  >
                    ✓ Aceitar
                  </button>
                  <button
                    className="btn btn-danger btn-sm"
                    disabled={respondendo === oferta.id}
                    onClick={() => responder(oferta.id, 'recusada')}
                  >
                    × Recusar
                  </button>
                </div>
              )}

              {oferta.responded_at && (
                <div className="text-muted" style={{ fontSize: 12, marginTop: 8 }}>
                  Respondida em {new Date(oferta.responded_at).toLocaleDateString('pt-BR')}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
