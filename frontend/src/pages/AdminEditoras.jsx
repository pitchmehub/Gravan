import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../lib/api'

function fmt(c) { return ((c ?? 0) / 100).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' }) }
function grad(seed = '') {
  let h = 0; for (let i = 0; i < seed.length; i++) h = (h * 31 + seed.charCodeAt(i)) | 0
  const a = Math.abs(h) % 360, b = (a + 60) % 360
  return `linear-gradient(135deg, hsl(${a},70%,50%), hsl(${b},70%,40%))`
}

export default function AdminEditoras() {
  const navigate = useNavigate()
  const [lista, setLista] = useState([])
  const [erro, setErro] = useState('')
  const [loading, setLoading] = useState(true)
  const [filtro, setFiltro] = useState('')
  const [atualizadoEm, setAtualizadoEm] = useState(null)

  async function carregar({ silencioso = false } = {}) {
    if (!silencioso) setLoading(true)
    setErro('')
    try {
      const data = await api.get(`/admin/publishers?_=${Date.now()}`)
      setLista(Array.isArray(data) ? data : [])
      setAtualizadoEm(new Date())
    } catch (e) { setErro(e.message) }
    finally { setLoading(false) }
  }

  useEffect(() => { carregar() }, [])

  const filtradas = lista.filter(p => {
    const q = filtro.trim().toLowerCase()
    if (!q) return true
    return [p.nome, p.nome_artistico, p.razao_social, p.email]
      .filter(Boolean).some(s => s.toLowerCase().includes(q))
  })

  return (
    <div style={{ padding: '32px 20px', maxWidth: 1100, margin: '0 auto' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12, marginBottom: 18 }}>
        <h1 style={{ fontSize: 24, fontWeight: 800, margin: 0 }}>🏢 Editoras</h1>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, fontSize: 11, color: '#71717A' }}>
          {atualizadoEm && <span>Atualizado às {atualizadoEm.toLocaleTimeString('pt-BR')}</span>}
          <button onClick={() => carregar({ silencioso: true })}
                  style={{ background: '#fff', border: '1px solid #E5E7EB', borderRadius: 6, padding: '4px 10px', fontSize: 11, cursor: 'pointer', color: '#71717A' }}>
            ↻ Atualizar
          </button>
        </div>
      </div>

      <input
        placeholder="Filtrar por nome, razão social ou e-mail…"
        value={filtro} onChange={e => setFiltro(e.target.value)}
        style={{ width: '100%', padding: '10px 12px', fontSize: 14,
                 border: '1px solid #E5E7EB', borderRadius: 8, marginBottom: 16, boxSizing: 'border-box' }}
      />

      {loading && <div style={{ color: '#71717A' }}>Carregando…</div>}
      {erro && <div style={{ color: '#c0392b' }}>⚠ {erro}</div>}

      {!loading && filtradas.length === 0 && !erro && (
        <div style={{ padding: 24, color: '#71717A', textAlign: 'center', border: '1px dashed #E5E7EB', borderRadius: 12 }}>
          Nenhuma editora encontrada.
        </div>
      )}

      <div style={{ display: 'grid', gap: 10 }}>
        {filtradas.map(p => {
          const nome = p.razao_social || p.nome_artistico || p.nome || '(sem nome)'
          const ini = (nome[0] || '?').toUpperCase()
          return (
            <div key={p.id}
                 onClick={() => navigate(`/admin/editoras/${p.id}`)}
                 data-testid="editora-card"
                 style={{
                   display: 'flex', alignItems: 'center', gap: 14, padding: 14,
                   border: '1px solid #E5E7EB', borderRadius: 12, background: '#fff',
                   cursor: 'pointer',
                 }}>
              <div style={{
                width: 48, height: 48, borderRadius: '50%', background: grad(p.id), color: '#fff',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontWeight: 700, fontSize: 18, overflow: 'hidden', flex: '0 0 auto',
              }}>
                {p.avatar_url ? <img src={p.avatar_url} alt={nome} style={{ width: '100%', height: '100%', objectFit: 'cover' }} /> : ini}
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontWeight: 700, fontSize: 15 }}>{nome}</div>
                <div style={{ fontSize: 12, color: '#71717A' }}>{p.email || '—'}</div>
              </div>
              <div style={{ display: 'flex', gap: 16, fontSize: 12, color: '#3F3F46', flexWrap: 'wrap' }}>
                <span><strong>{p.total_obras ?? 0}</strong> obras</span>
                <span><strong>{p.total_agregados ?? 0}</strong> agregados</span>
                <span><strong>{p.total_contratos ?? 0}</strong> contratos</span>
              </div>
              <span style={{ color: '#71717A', fontSize: 18 }}>›</span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
