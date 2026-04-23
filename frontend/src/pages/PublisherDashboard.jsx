import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../lib/api'

function fmt(cents) {
  return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format((cents ?? 0) / 100)
}

function StatCard({ label, value, sub, accent }) {
  return (
    <div style={{
      padding: '18px 20px',
      background: accent ? 'rgba(225,29,72,.18)' : 'var(--surface)',
      border: `1px solid ${accent ? 'rgba(225,29,72,.4)' : 'var(--border)'}`,
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

function fmtRestante(h) {
  if (h == null) return '—'
  if (h <= 0)    return 'Expirado'
  if (h < 1)     return `${Math.round(h * 60)} min úteis`
  return `${h.toFixed(1)} h úteis`
}

function OfertasPendentes() {
  const [ofertas, setOfertas] = useState(null)
  const [erro, setErro]       = useState('')
  useEffect(() => {
    api.get('/ofertas-licenciamento/editora')
      .then(setOfertas).catch(e => setErro(e.message))
  }, [])

  if (erro) return null
  if (!ofertas) return null
  const aguardando = ofertas.filter(o => o.status === 'aguardando_editora' || o.status === 'aguardando_assinaturas')
  if (aguardando.length === 0) return null

  return (
    <div style={{ marginBottom: 28 }}>
      <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 12 }}>
        Ofertas pendentes ({aguardando.length})
      </h2>
      <div style={{ display: 'grid', gap: 12 }}>
        {aguardando.map(o => (
          <div key={o.id} style={{
            padding: 16, background: 'var(--surface)',
            border: '1px solid var(--border)', borderRadius: 12,
            display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap',
          }}>
            <div style={{ flex: '1 1 280px', minWidth: 0 }}>
              <div style={{ fontWeight: 700, fontSize: 15 }}>{o.obra?.nome ?? '(obra)'}</div>
              <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>
                Comprador: {o.comprador?.nome ?? '—'} · Status: {o.status.replace(/_/g, ' ')}
              </div>
              {o.mensagem && (
                <div style={{ fontSize: 12, fontStyle: 'italic', marginTop: 6, color: 'var(--text-secondary)' }}>
                  "{o.mensagem}"
                </div>
              )}
            </div>
            <div style={{ textAlign: 'right' }}>
              <div style={{ fontSize: 18, fontWeight: 800, color: 'var(--brand)' }}>{fmt(o.valor_cents)}</div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                Prazo: {fmtRestante(o.horas_uteis_restantes)}
              </div>
              {o.contract_id && (
                <Link to={`/contratos/licenciamento/${o.contract_id}`}
                      className="btn btn-primary btn-sm" style={{ marginTop: 8 }}>
                  Revisar e assinar
                </Link>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default function PublisherDashboard() {
  const [data, setData] = useState(null)
  const [erro, setErro] = useState('')

  useEffect(() => {
    api.get('/publishers/dashboard').then(setData).catch(e => setErro(e.message))
  }, [])

  if (erro) return <div style={{ padding: 32, color: '#c0392b' }}>⚠ {erro}</div>
  if (!data) return <div style={{ padding: 32, color: 'var(--text-muted)' }}>Carregando…</div>

  return (
    <div style={{ padding: '32px 20px', maxWidth: 1100, margin: '0 auto' }}>
      <header style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 24, fontWeight: 700 }}>Dashboard da Editora</h1>
        <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>Visão geral de obras, contratos e faturamento.</p>
      </header>

      <OfertasPendentes />

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 14, marginBottom: 28 }}>
        <StatCard label="Obras" value={data.total_obras} sub={`${data.obras_publicadas} publicadas`} />
        <StatCard label="Agregados" value={data.total_agregados} />
        <StatCard label="Contratos assinados" value={data.contratos_assinados} sub={`${data.contratos_pendentes} pendentes`} />
        <StatCard label="Faturamento bruto" value={fmt(data.faturamento_cents)} accent />
        <StatCard label="Fee devido (5%)" value={fmt(data.fee_devido_cents)} sub="Plataforma PITCH.ME" />
      </div>

      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
        <Link to="/agregados" className="btn btn-primary">Gerir agregados</Link>
        <Link to="/obras/nova" className="btn btn-ghost">Cadastrar nova obra</Link>
        <Link to="/contratos" className="btn btn-ghost">Ver contratos</Link>
      </div>
    </div>
  )
}
