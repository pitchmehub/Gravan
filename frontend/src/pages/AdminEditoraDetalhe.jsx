import React, { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api } from '../lib/api'

function fmt(c) { return ((c ?? 0) / 100).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' }) }
function grad(seed = '') {
  let h = 0; for (let i = 0; i < seed.length; i++) h = (h * 31 + seed.charCodeAt(i)) | 0
  const a = Math.abs(h) % 360, b = (a + 60) % 360
  return `linear-gradient(135deg, hsl(${a},70%,50%), hsl(${b},70%,40%))`
}

export default function AdminEditoraDetalhe() {
  const { publisherId } = useParams()
  const navigate = useNavigate()
  const [data, setData] = useState(null)
  const [erro, setErro] = useState('')
  const [loading, setLoading] = useState(true)
  const [atualizadoEm, setAtualizadoEm] = useState(null)

  async function carregar({ silencioso = false } = {}) {
    if (!silencioso) setLoading(true)
    setErro('')
    try {
      const d = await api.get(`/admin/publishers/${publisherId}/dashboard?_=${Date.now()}`)
      setData(d)
      setAtualizadoEm(new Date())
    } catch (e) { setErro(e.message) }
    finally { setLoading(false) }
  }

  useEffect(() => { carregar() }, [publisherId])

  if (loading) return <div style={{ padding: 32, color: '#71717A' }}>Carregando…</div>
  if (erro)    return <div style={{ padding: 32, color: '#c0392b' }}>⚠ {erro}</div>
  if (!data)   return null

  const p = data.perfil
  const t = data.totais || {}
  const nome = p.razao_social || p.nome_artistico || p.nome || '(sem nome)'

  return (
    <div style={{ padding: '32px 20px', maxWidth: 1100, margin: '0 auto' }}>
      <button onClick={() => navigate('/admin/editoras')}
              style={{ background: 'none', border: 'none', color: '#0C447C', cursor: 'pointer', fontSize: 13, marginBottom: 16 }}>
        ← Voltar para a lista
      </button>

      <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 8, flexWrap: 'wrap' }}>
        <div style={{
          width: 72, height: 72, borderRadius: '50%', background: grad(p.id), color: '#fff',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 26, fontWeight: 700, overflow: 'hidden',
        }}>
          {p.avatar_url ? <img src={p.avatar_url} alt={nome} style={{ width: '100%', height: '100%', objectFit: 'cover' }} /> : (nome[0] || '?').toUpperCase()}
        </div>
        <div style={{ flex: 1, minWidth: 220 }}>
          <h1 style={{ fontSize: 22, fontWeight: 800, margin: 0 }}>{nome}</h1>
          <div style={{ fontSize: 13, color: '#71717A', marginTop: 4 }}>
            Editora · {p.email || '—'}
          </div>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 6 }}>
          <button onClick={() => navigate(`/perfil/${p.id}`)}
                  style={{ padding: '8px 14px', fontSize: 12, fontWeight: 700, background: '#09090B', color: '#fff',
                           border: 'none', borderRadius: 8, cursor: 'pointer' }}>
            Abrir perfil público / excluir
          </button>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 11, color: '#71717A' }}>
            {atualizadoEm && <span>Atualizado às {atualizadoEm.toLocaleTimeString('pt-BR')}</span>}
            <button onClick={() => carregar({ silencioso: true })}
                    style={{ background: 'transparent', border: '1px solid #E5E7EB', borderRadius: 6,
                             padding: '4px 8px', fontSize: 11, cursor: 'pointer', color: '#71717A' }}>
              ↻ Atualizar
            </button>
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: 10, margin: '20px 0' }}>
        <Stat label="Obras"               value={t.obras} />
        <Stat label="Obras publicadas"    value={t.obras_publicadas} />
        <Stat label="Agregados"           value={t.agregados} />
        <Stat label="Contratos"           value={t.contratos} />
        <Stat label="Contratos assinados" value={t.contratos_assinados} />
        <Stat label="Contratos pendentes" value={t.contratos_pendentes} />
        <Stat label="Faturamento"         value={fmt(t.faturamento_cents)} highlight />
        <Stat label="Fee plataforma (5%)" value={fmt(t.fee_devido_cents)} />
      </div>

      <Section title={`Agregados (${data.agregados?.length || 0})`}>
        {(data.agregados || []).length === 0
          ? <Empty texto="Nenhum compositor agregado." />
          : (data.agregados || []).map(a => (
              <Row key={a.id} onClick={() => navigate(`/perfil/${a.id}`)}>
                <strong>{a.nome_artistico || a.nome}</strong>
                <span style={{ color: '#71717A' }}>{a.email || '—'}</span>
                <span style={{ color: '#71717A', fontSize: 11 }}>{a.nivel || ''}</span>
              </Row>
            ))}
      </Section>

      <Section title={`Obras cadastradas (${data.obras?.length || 0})`}>
        {(data.obras || []).length === 0
          ? <Empty texto="Nenhuma obra cadastrada." />
          : (data.obras || []).map(o => (
              <Row key={o.id} onClick={() => navigate(`/comprar/${o.id}`)}>
                <strong>{o.titulo}</strong>
                <span style={{ color: '#71717A' }}>{o.genero || '—'}</span>
                <span style={{ color: '#71717A', fontSize: 11 }}>{o.publicada ? 'Publicada' : (o.status || 'rascunho')}</span>
                <span style={{ color: '#0C447C', fontWeight: 700 }}>{fmt(o.preco_cents)}</span>
              </Row>
            ))}
      </Section>

      <Section title={`Contratos (${data.contratos?.length || 0})`}>
        {(data.contratos || []).length === 0
          ? <Empty texto="Nenhum contrato registrado." />
          : (data.contratos || []).map(c => (
              <Row key={c.id}>
                <code style={{ fontSize: 11 }}>{c.id?.slice(0, 8)}</code>
                <span>{c.status}</span>
                <span style={{ color: '#71717A', fontSize: 11 }}>{c.created_at?.slice(0, 10)}</span>
              </Row>
            ))}
      </Section>

      <Section title={`Transações recentes (${data.transacoes?.length || 0})`}>
        {(data.transacoes || []).length === 0
          ? <Empty texto="Sem transações." />
          : (data.transacoes || []).map(tx => (
              <Row key={tx.id}>
                <code style={{ fontSize: 11 }}>{tx.id?.slice(0, 8)}</code>
                <span>{tx.status}</span>
                <span style={{ color: '#71717A', fontSize: 11 }}>{tx.created_at?.slice(0, 10)}</span>
                <span style={{ fontWeight: 700 }}>{fmt(tx.valor_cents)}</span>
              </Row>
            ))}
      </Section>
    </div>
  )
}

function Stat({ label, value, highlight }) {
  return (
    <div style={{
      padding: 14, borderRadius: 10, background: highlight ? '#FEF2F2' : '#FAFAFA',
      border: `1px solid ${highlight ? '#FECACA' : '#E5E7EB'}`,
    }}>
      <div style={{ fontSize: 10, color: '#71717A', textTransform: 'uppercase', letterSpacing: 0.5 }}>{label}</div>
      <div style={{ fontSize: 18, fontWeight: 800, marginTop: 4, color: highlight ? '#B91C1C' : '#09090B' }}>
        {value ?? '—'}
      </div>
    </div>
  )
}
function Section({ title, children }) {
  return (
    <div style={{ marginTop: 22 }}>
      <h2 style={{ fontSize: 15, fontWeight: 700, marginBottom: 8 }}>{title}</h2>
      <div style={{ display: 'grid', gap: 6 }}>{children}</div>
    </div>
  )
}
function Row({ children, onClick }) {
  return (
    <div onClick={onClick}
         style={{
           display: 'flex', gap: 14, alignItems: 'center', padding: '10px 12px',
           background: '#fff', border: '1px solid #E5E7EB', borderRadius: 8,
           fontSize: 13, cursor: onClick ? 'pointer' : 'default', flexWrap: 'wrap',
         }}>
      {children}
    </div>
  )
}
function Empty({ texto }) {
  return <div style={{ padding: 14, color: '#71717A', fontSize: 13, fontStyle: 'italic' }}>{texto}</div>
}
