import React, { useEffect, useState } from 'react'
import { api } from '../lib/api'

function fmtCPF(v) {
  const d = v.replace(/\D/g, '').slice(0, 11)
  if (d.length <= 3) return d
  if (d.length <= 6) return `${d.slice(0,3)}.${d.slice(3)}`
  if (d.length <= 9) return `${d.slice(0,3)}.${d.slice(3,6)}.${d.slice(6)}`
  return `${d.slice(0,3)}.${d.slice(3,6)}.${d.slice(6,9)}-${d.slice(9)}`
}
function fmtCEP(v) {
  const d = v.replace(/\D/g, '').slice(0, 8)
  if (d.length <= 5) return d
  return `${d.slice(0,5)}-${d.slice(5)}`
}

const EMPTY_FORM = {
  nome_completo: '', nome_artistico: '', rg: '', cpf: '', email: '',
  endereco_rua: '', endereco_numero: '', endereco_compl: '',
  endereco_bairro: '', endereco_cidade: '', endereco_uf: '', endereco_cep: '',
}

export default function Agregados() {
  const [lista, setLista] = useState([])
  const [loading, setLoading] = useState(true)
  const [erro, setErro] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState(EMPTY_FORM)
  const [salvando, setSalvando] = useState(false)
  const [msg, setMsg] = useState('')

  async function carregar() {
    setLoading(true); setErro('')
    try {
      const d = await api.get('/agregados')
      setLista(d || [])
    } catch (e) { setErro(e.message) }
    finally { setLoading(false) }
  }

  useEffect(() => { carregar() }, [])

  async function adicionar(e) {
    e.preventDefault()
    setSalvando(true); setMsg(''); setErro('')
    try {
      const r = await api.post('/agregados', form)
      setMsg(r.modo === 'ghost_criado'
        ? '✓ Novo artista criado e vinculado à sua editora.'
        : '✓ Artista existente vinculado à sua editora.')
      setForm(EMPTY_FORM)
      setShowForm(false)
      await carregar()
    } catch (e) { setErro(e.message) }
    finally { setSalvando(false) }
  }

  async function desvincular(id) {
    if (!confirm('Desvincular este agregado da sua editora?')) return
    try { await api.delete(`/agregados/${id}`); await carregar() }
    catch (e) { alert(e.message) }
  }

  function set(k, v) { setForm(f => ({ ...f, [k]: v })) }

  const inputStyle = { width: '100%', padding: '8px 10px', border: '1px solid var(--border)', borderRadius: 6, fontSize: 13 }
  const lbl = { fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', marginBottom: 3, display: 'block' }

  return (
    <div style={{ padding: '32px 20px', maxWidth: 1100, margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700 }}>Agregados</h1>
          <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>Artistas vinculados à sua editora.</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowForm(s => !s)}>
          {showForm ? 'Cancelar' : '+ Novo agregado'}
        </button>
      </div>

      {msg && <div style={{ padding: 12, background: 'rgba(34,197,94,.1)', border: '1px solid #22c55e', borderRadius: 8, marginBottom: 16, fontSize: 13, color: '#16a34a' }}>{msg}</div>}
      {erro && <div style={{ padding: 12, background: 'rgba(239,68,68,.1)', border: '1px solid #ef4444', borderRadius: 8, marginBottom: 16, fontSize: 13, color: '#c0392b' }}>⚠ {erro}</div>}

      {showForm && (
        <form onSubmit={adicionar} style={{ border: '1px solid var(--border)', borderRadius: 12, padding: 16, marginBottom: 24, background: 'var(--surface)' }}>
          <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 12 }}>Cadastrar / vincular artista</h3>
          <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 14 }}>
            Se o e-mail já existir no sistema, o artista será vinculado à sua editora. Caso contrário, criamos um novo perfil.
          </p>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
            <div><label style={lbl}>Nome completo *</label><input style={inputStyle} value={form.nome_completo} onChange={e => set('nome_completo', e.target.value)} required /></div>
            <div><label style={lbl}>Nome artístico *</label><input style={inputStyle} value={form.nome_artistico} onChange={e => set('nome_artistico', e.target.value)} required /></div>
            <div><label style={lbl}>RG *</label><input style={inputStyle} value={form.rg} onChange={e => set('rg', e.target.value)} required /></div>
            <div><label style={lbl}>CPF *</label><input style={inputStyle} value={form.cpf} onChange={e => set('cpf', fmtCPF(e.target.value))} required /></div>
            <div style={{ gridColumn: '1 / -1' }}><label style={lbl}>E-mail *</label><input style={inputStyle} type="email" value={form.email} onChange={e => set('email', e.target.value)} required /></div>
          </div>

          <h4 style={{ fontSize: 12, fontWeight: 700, marginTop: 14, marginBottom: 8, color: 'var(--text-muted)' }}>Endereço</h4>
          <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr', gap: 10 }}>
            <div><label style={lbl}>Rua</label><input style={inputStyle} value={form.endereco_rua} onChange={e => set('endereco_rua', e.target.value)} /></div>
            <div><label style={lbl}>Número</label><input style={inputStyle} value={form.endereco_numero} onChange={e => set('endereco_numero', e.target.value)} /></div>
            <div><label style={lbl}>Compl.</label><input style={inputStyle} value={form.endereco_compl} onChange={e => set('endereco_compl', e.target.value)} /></div>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 80px 110px', gap: 10, marginTop: 10 }}>
            <div><label style={lbl}>Bairro</label><input style={inputStyle} value={form.endereco_bairro} onChange={e => set('endereco_bairro', e.target.value)} /></div>
            <div><label style={lbl}>Cidade</label><input style={inputStyle} value={form.endereco_cidade} onChange={e => set('endereco_cidade', e.target.value)} /></div>
            <div><label style={lbl}>UF</label><input style={inputStyle} maxLength={2} value={form.endereco_uf} onChange={e => set('endereco_uf', e.target.value.toUpperCase())} /></div>
            <div><label style={lbl}>CEP</label><input style={inputStyle} value={form.endereco_cep} onChange={e => set('endereco_cep', fmtCEP(e.target.value))} /></div>
          </div>

          <button type="submit" disabled={salvando} className="btn btn-primary" style={{ marginTop: 14 }}>
            {salvando ? 'Salvando…' : 'Cadastrar agregado'}
          </button>
        </form>
      )}

      {loading ? (
        <p style={{ color: 'var(--text-muted)' }}>Carregando…</p>
      ) : lista.length === 0 ? (
        <div style={{ padding: 40, border: '1px dashed var(--border)', borderRadius: 12, textAlign: 'center', color: 'var(--text-muted)' }}>
          Nenhum artista agregado ainda.
        </div>
      ) : (
        <div style={{ border: '1px solid var(--border)', borderRadius: 12, overflow: 'hidden' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead style={{ background: 'var(--surface-2, #fafafa)' }}>
              <tr>
                <th style={th}>Nome</th>
                <th style={th}>Nome artístico</th>
                <th style={th}>E-mail</th>
                <th style={th}>Status</th>
                <th style={{ ...th, textAlign: 'right' }}>Ações</th>
              </tr>
            </thead>
            <tbody>
              {lista.map(a => (
                <tr key={a.id} style={{ borderTop: '1px solid var(--border)' }}>
                  <td style={td}>{a.nome_completo}</td>
                  <td style={td}>{a.nome_artistico}</td>
                  <td style={td}>{a.email}</td>
                  <td style={td}>
                    {a.is_ghost
                      ? <span style={{ fontSize: 11, padding: '2px 8px', background: 'rgba(245,158,11,.15)', color: '#d97706', borderRadius: 4 }}>Convite pendente</span>
                      : <span style={{ fontSize: 11, padding: '2px 8px', background: 'rgba(34,197,94,.15)', color: '#16a34a', borderRadius: 4 }}>Ativo</span>}
                  </td>
                  <td style={{ ...td, textAlign: 'right' }}>
                    <button className="btn btn-ghost" style={{ fontSize: 12, padding: '4px 10px' }} onClick={() => desvincular(a.id)}>Desvincular</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

const th = { textAlign: 'left', padding: '10px 14px', fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 0.5 }
const td = { padding: '12px 14px', verticalAlign: 'middle' }
