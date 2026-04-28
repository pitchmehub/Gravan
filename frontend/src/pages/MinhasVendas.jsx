import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../lib/api'

function fmt(cents) {
  return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' })
    .format((cents ?? 0) / 100)
}

function fmtData(iso) {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleString('pt-BR', {
      day: '2-digit', month: '2-digit', year: 'numeric',
      hour: '2-digit', minute: '2-digit',
    })
  } catch { return iso }
}

export default function MinhasVendas() {
  const [data, setData] = useState(null)
  const [erro, setErro] = useState('')

  useEffect(() => {
    api.get('/transacoes/minhas-vendas')
      .then(setData)
      .catch(e => setErro(e.message))
  }, [])

  if (erro) return (
    <div style={{ padding: 32, color: '#c0392b' }}>
      Não foi possível carregar suas vendas: {erro}
    </div>
  )
  if (!data) return (
    <div style={{ padding: 32, color: 'var(--text-muted)' }}>Carregando…</div>
  )

  const itens = data.itens || []
  const titulo = (
    <>
      <h1 style={{ fontSize: 26, fontWeight: 800 }}>Histórico de vendas</h1>
      <p style={{ color: 'var(--text-muted)', fontSize: 14 }}>
        Cada licenciamento das suas obras em que você recebeu participação.
      </p>
    </>
  )

  if (itens.length === 0) {
    return (
      <div style={{ padding: 32, maxWidth: 1080, margin: '0 auto' }}>
        <header style={{ marginBottom: 24 }}>{titulo}</header>
        <div style={{
          padding: 28, background: 'var(--surface)', border: '1px dashed var(--border)',
          borderRadius: 14, textAlign: 'center', color: 'var(--text-muted)',
        }}>
          <div style={{ fontSize: 15, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 6 }}>
            Você ainda não tem vendas registradas.
          </div>
          <div style={{ fontSize: 13 }}>
            Quando uma das suas obras for licenciada, ela aparece aqui com o valor recebido.
          </div>
          <div style={{ marginTop: 18 }}>
            <Link to="/obras" className="btn btn-primary">Ver minhas obras</Link>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div style={{ padding: 32, maxWidth: 1080, margin: '0 auto' }}>
      <header style={{ marginBottom: 24 }}>{titulo}</header>

      <div style={{
        display: 'grid', gap: 14, marginBottom: 22,
        gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
      }}>
        <Card label="Total recebido" value={fmt(data.total_cents)} accent />
        <Card label="Vendas" value={data.total_transacoes} sub="licenciamentos" />
        <Card label="Itens registrados" value={itens.length} sub="participações" />
      </div>

      <div style={{
        background: 'var(--surface)', border: '1px solid var(--border)',
        borderRadius: 12, overflow: 'hidden',
      }}>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ background: 'rgba(0,0,0,.04)', textAlign: 'left' }}>
                <Th>Data</Th>
                <Th>Obra</Th>
                <Th>Comprador</Th>
                <Th>Papel</Th>
                <Th align="right">Valor da venda</Th>
                <Th align="right">Você recebeu</Th>
              </tr>
            </thead>
            <tbody>
              {itens.map(it => (
                <tr key={it.id} style={{ borderTop: '1px solid var(--border)' }}>
                  <td style={{ padding: '10px 14px', whiteSpace: 'nowrap', color: 'var(--text-secondary)' }}>
                    {fmtData(it.data)}
                  </td>
                  <td style={{ padding: '10px 14px', fontWeight: 600 }}>{it.obra?.nome || '—'}</td>
                  <td style={{ padding: '10px 14px' }}>{it.comprador?.nome || '—'}</td>
                  <td style={{ padding: '10px 14px' }}>
                    <span style={{
                      fontSize: 11, padding: '3px 9px', borderRadius: 99, fontWeight: 700,
                      background: it.sou_titular ? 'rgba(12,68,124,.15)' : 'rgba(107,114,128,.15)',
                      color: it.sou_titular ? 'var(--brand)' : 'var(--text-muted)',
                    }}>
                      {it.sou_titular ? 'Titular' : 'Coautor'}
                    </span>
                  </td>
                  <td style={{ padding: '10px 14px', textAlign: 'right', whiteSpace: 'nowrap', color: 'var(--text-secondary)' }}>
                    {it.valor_total_cents != null ? fmt(it.valor_total_cents) : '—'}
                  </td>
                  <td style={{ padding: '10px 14px', textAlign: 'right', whiteSpace: 'nowrap', fontWeight: 800, color: 'var(--brand)' }}>
                    {fmt(it.valor_recebido_cents)}
                    {it.share_pct != null && (
                      <div style={{ fontSize: 10, fontWeight: 500, color: 'var(--text-muted)' }}>
                        {Number(it.share_pct).toFixed(0)}%
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

function Card({ label, value, sub, accent }) {
  return (
    <div style={{
      padding: '18px 20px',
      background: accent ? 'rgba(12,68,124,.18)' : 'var(--surface)',
      border: `1px solid ${accent ? 'rgba(12,68,124,.4)' : 'var(--border)'}`,
      borderRadius: 14,
    }}>
      <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 8 }}>
        {label}
      </div>
      <div style={{ fontSize: 28, fontWeight: 900, color: accent ? 'var(--brand)' : 'var(--text-primary)', lineHeight: 1, marginBottom: 6 }}>
        {value}
      </div>
      {sub && <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{sub}</div>}
    </div>
  )
}

function Th({ children, align = 'left' }) {
  return (
    <th style={{
      padding: '10px 14px', fontWeight: 700, fontSize: 11, textTransform: 'uppercase',
      letterSpacing: '.06em', color: 'var(--text-muted)', textAlign: align,
    }}>
      {children}
    </th>
  )
}
