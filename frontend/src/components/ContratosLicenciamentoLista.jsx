import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../lib/api'

export default function ContratosLicenciamento() {
  const [items, setItems]     = useState([])
  const [loading, setLoading] = useState(true)
  const [erro, setErro]       = useState('')
  const [sincronizando, setSincronizando] = useState(false)
  const navigate = useNavigate()

  async function reload() {
    try {
      setLoading(true)
      const d = await api.get('/contratos/licenciamento')
      setItems(d || [])
    } catch (e) { setErro(e.message) }
    finally { setLoading(false) }
  }
  useEffect(() => { reload() }, [])

  async function sincronizar() {
    setSincronizando(true)
    try {
      const res = await api.post('/contratos/licenciamento/sincronizar', {})
      if (res?.sincronizados > 0) {
        alert(`✓ ${res.sincronizados} contrato(s) gerado(s) com sucesso!`)
        await reload()
      } else if (res?.total_transacoes === 0) {
        alert('Você ainda não tem nenhuma venda ou compra confirmada na plataforma.')
      } else {
        alert(`Nenhum contrato novo para gerar (${res?.ja_existiam || 0} já existiam).`)
      }
    } catch (e) {
      alert('Erro ao sincronizar: ' + e.message)
    } finally { setSincronizando(false) }
  }

  function moeda(cents) {
    return (cents / 100).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
  }

  const papelLabel = (r) => ({ autor: 'Autor principal', coautor: 'Coautor', interprete: 'Intérprete', 'intérprete': 'Intérprete' }[r] || r)
  const statusBadge = (st) => {
    const map = {
      pendente:    { bg: '#FFF4E5', fg: '#7A4D00', label: 'Aguardando assinaturas' },
      assinado:    { bg: '#E8F4FD', fg: '#0C5494', label: 'Parcialmente assinado' },
      'concluído': { bg: '#E8F8EC', fg: '#0E6B2B', label: 'Concluído' },
      concluido:   { bg: '#E8F8EC', fg: '#0E6B2B', label: 'Concluído' },
      cancelado:   { bg: '#FBEAEA', fg: '#8B1C1C', label: 'Cancelado' },
    }[st] || { bg: '#EEE', fg: '#555', label: st }
    return (
      <span style={{ padding: '3px 8px', background: map.bg, color: map.fg, fontSize: 11, fontWeight: 600, borderRadius: 4 }}>
        {map.label}
      </span>
    )
  }

  if (loading) return <p style={{ color: 'var(--text-muted)' }}>Carregando…</p>
  if (erro)    return <p style={{ color: '#c0392b' }}>⚠ {erro}</p>

  const botaoSincronizar = (
    <button
      data-testid="btn-sincronizar-contratos"
      className="btn btn-ghost"
      disabled={sincronizando}
      onClick={sincronizar}
      style={{ fontSize: 12, padding: '6px 12px' }}
      title="Verifica suas vendas/compras já pagas e gera contratos que estejam faltando."
    >{sincronizando ? 'Sincronizando…' : '↻ Sincronizar contratos'}</button>
  )

  if (!items.length) {
    return (
      <div style={{ display: 'grid', gap: 14 }}>
        <div data-testid="licenciamento-empty" style={{
          padding: 40, border: '1px dashed var(--border)', borderRadius: 12,
          textAlign: 'center', color: 'var(--text-muted)', fontSize: 13,
        }}>
          Nenhum contrato de licenciamento ainda. Eles são criados automaticamente após
          cada venda/licenciamento de obra.
          <div style={{ marginTop: 16 }}>{botaoSincronizar}</div>
          <p style={{ marginTop: 10, fontSize: 11, color: 'var(--text-muted)' }}>
            Se você já vendeu ou comprou uma obra e o contrato não apareceu
            (comum em ambiente local), clique em Sincronizar para gerá-lo.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div data-testid="licenciamento-lista" style={{ display: 'grid', gap: 12 }}>
      <div style={{ display: 'flex', justifyContent: 'flex-end' }}>{botaoSincronizar}</div>
      {items.map((c, i) => {
        const concluido = c.status === 'concluído' || c.status === 'concluido'
        const ehParteParaAssinar = ['autor', 'coautor', 'interprete', 'intérprete'].includes(c.meu_papel)
        const precisaAssinar = ehParteParaAssinar && !c.minha_assinatura && !concluido && c.status !== 'cancelado'

        return (
          <div key={c.id} data-testid={`licenciamento-${i}`} style={{
            padding: 16, background: '#fff', border: '1px solid var(--border)',
            borderRadius: 12,
            // Destaque visual quando precisa de assinatura
            boxShadow: precisaAssinar ? '0 0 0 2px #f59e0b inset' : 'none',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
              <div style={{ flex: 1, minWidth: 200 }}>
                <div style={{ fontWeight: 700, fontSize: 15 }}>{c?.obras?.nome || 'Obra'}</div>
                <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>
                  {papelLabel(c.meu_papel)} · {moeda(c.valor_cents)} · {new Date(c.created_at).toLocaleDateString('pt-BR')}
                </div>
              </div>
              {statusBadge(c.status)}
              {c.minha_assinatura
                ? <span style={{ fontSize: 11, color: '#0E6B2B', fontWeight: 600 }}>✓ você assinou</span>
                : !concluido && (
                  <span style={{ fontSize: 11, color: '#7A4D00', fontWeight: 600 }}>
                    ⏱ aguardando sua assinatura
                  </span>
                )}

              {precisaAssinar ? (
                <button
                  data-testid={`licenciamento-assinar-${i}`}
                  className="btn btn-primary"
                  style={{
                    fontSize: 13, padding: '8px 16px', fontWeight: 700,
                    background: '#f59e0b', borderColor: '#f59e0b', color: '#fff',
                  }}
                  onClick={() => navigate(`/contratos/licenciamento/${c.id}?assinar=1`)}
                  title="Abrir o contrato para ler e assinar"
                >✍ Assinar contrato</button>
              ) : (
                <button
                  data-testid={`licenciamento-ver-${i}`}
                  className="btn btn-ghost"
                  style={{ fontSize: 12, padding: '6px 12px' }}
                  onClick={() => navigate(`/contratos/licenciamento/${c.id}`)}
                >Abrir</button>
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}
