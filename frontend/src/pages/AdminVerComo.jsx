import React, { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { api } from '../lib/api'

function fmt(cents) {
  return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format((cents ?? 0) / 100)
}

export default function AdminVerComo() {
  const { perfilId } = useParams()
  const [data, setData] = useState(null)
  const [erro, setErro] = useState('')

  useEffect(() => {
    api.get(`/admin/perfis/${perfilId}/visao`)
      .then(setData)
      .catch(e => setErro(e.message))
  }, [perfilId])

  if (erro) return <div style={{ padding: 32, color: '#c0392b' }}>⚠ {erro}</div>
  if (!data) return <div style={{ padding: 32, color: 'var(--text-muted)' }}>Carregando…</div>

  const p = data.perfil

  return (
    <div style={{ padding: '32px 20px', maxWidth: 1100, margin: '0 auto' }}>
      <div style={{ background: 'rgba(225,29,72,.08)', border: '1px solid rgba(225,29,72,.3)', padding: 12, borderRadius: 8, marginBottom: 20, fontSize: 13 }}>
        👑 <strong>Modo Admin:</strong> visualizando perfil de <strong>{p.nome_completo || p.nome || p.email}</strong> ({p.role}).
        <Link to="/admin" style={{ marginLeft: 12, color: 'var(--brand)' }}>← voltar ao painel</Link>
      </div>

      <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 16 }}>{p.nome_artistico || p.nome_completo || p.email}</h1>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 12, marginBottom: 24 }}>
        <Card label="ID" value={p.id?.slice(0, 8)} />
        <Card label="Role" value={p.role} />
        <Card label="E-mail" value={p.email} />
        <Card label="Cadastro completo" value={p.cadastro_completo ? 'Sim' : 'Não'} />
        {p.publisher_id && <Card label="Vinculado à editora" value={p.publisher_id.slice(0, 8)} />}
      </div>

      <h2 style={{ fontSize: 16, fontWeight: 700, marginTop: 20, marginBottom: 10 }}>Obras ({data.obras?.length || 0})</h2>
      {(data.obras || []).map(o => (
        <div key={o.id} style={{ padding: 10, border: '1px solid var(--border)', borderRadius: 8, marginBottom: 6, fontSize: 13 }}>
          <strong>{o.titulo}</strong> · {o.publicada ? 'Publicada' : 'Rascunho'}
        </div>
      ))}

      <h2 style={{ fontSize: 16, fontWeight: 700, marginTop: 20, marginBottom: 10 }}>Contratos ({data.contratos?.length || 0})</h2>
      {(data.contratos || []).map(c => (
        <div key={c.id} style={{ padding: 10, border: '1px solid var(--border)', borderRadius: 8, marginBottom: 6, fontSize: 13 }}>
          {c.id.slice(0, 8)} · {c.status} · {c.created_at?.slice(0, 10)}
        </div>
      ))}

      <h2 style={{ fontSize: 16, fontWeight: 700, marginTop: 20, marginBottom: 10 }}>Ganhos: {fmt(data.ganhos_cents)}</h2>
    </div>
  )
}

function Card({ label, value }) {
  return (
    <div style={{ padding: 14, background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 10 }}>
      <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 0.5 }}>{label}</div>
      <div style={{ fontSize: 14, fontWeight: 600, marginTop: 4 }}>{value || '—'}</div>
    </div>
  )
}
