import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { api } from '../lib/api'
import StepperCadastro from '../components/StepperCadastro'

function fmtCNPJ(v) {
 const d = v.replace(/\D/g, '').slice(0, 14)
 if (d.length <= 2) return d
 if (d.length <= 5) return `${d.slice(0,2)}.${d.slice(2)}`
 if (d.length <= 8) return `${d.slice(0,2)}.${d.slice(2,5)}.${d.slice(5)}`
 if (d.length <= 12) return `${d.slice(0,2)}.${d.slice(2,5)}.${d.slice(5,8)}/${d.slice(8)}`
 return `${d.slice(0,2)}.${d.slice(2,5)}.${d.slice(5,8)}/${d.slice(8,12)}-${d.slice(12)}`
}
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

export default function CadastroEditora() {
 const { refreshPerfil } = useAuth()
 const navigate = useNavigate()
 const [loading, setLoading] = useState(false)
 const [error, setError] = useState('')
 const [form, setForm] = useState({
 razao_social: '', nome_fantasia: '', cnpj: '',
 telefone: '',
 endereco_rua: '', endereco_numero: '', endereco_compl: '',
 endereco_bairro: '', endereco_cidade: '', endereco_uf: '', endereco_cep: '',
 })

 function set(k, v) { setForm(f => ({ ...f, [k]: v })) }

 function preencherDepois() {
 try { localStorage.setItem('gravan_skip_cadastro', '1') } catch {}
 navigate('/descoberta', { replace: true })
 }

 async function handleSubmit(e) {
 e.preventDefault()
 setError('')
 setLoading(true)
 try {
 await api.post('/publishers', form)
 await refreshPerfil?.()
 navigate('/editora/dashboard', { replace: true })
 } catch (err) {
 setError(err.message)
 } finally {
 setLoading(false)
 }
 }

 const inputStyle = {
 width: '100%', padding: '10px 12px', border: '1px solid var(--border)',
 borderRadius: 8, fontSize: 14, background: 'var(--surface)',
 }
 const labelStyle = { fontSize: 12, fontWeight: 600, color: 'var(--text-muted)', marginBottom: 4, display: 'block' }

 return (
 <div style={{ padding: '32px 20px', maxWidth: 720, margin: '0 auto' }}>
 <StepperCadastro etapa={2} />
 <h1 style={{ fontSize: 24, fontWeight: 700, marginBottom: 8 }}>Cadastro de Editora</h1>
 <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 24 }}>
 Preencha os dados da pessoa jurídica para ativar seu perfil de Editora Musical.
 </p>

 <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
 <fieldset style={{ border: '1px solid var(--border)', borderRadius: 12, padding: 16 }}>
 <legend style={{ fontSize: 13, fontWeight: 700, padding: '0 8px' }}>Dados da empresa</legend>
 <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
 <div><label style={labelStyle}>Razão Social *</label>
 <input style={inputStyle} value={form.razao_social} onChange={e => set('razao_social', e.target.value)} required /></div>
 <div><label style={labelStyle}>Nome Fantasia *</label>
 <input style={inputStyle} value={form.nome_fantasia} onChange={e => set('nome_fantasia', e.target.value)} required /></div>
 <div><label style={labelStyle}>CNPJ *</label>
 <input style={inputStyle} value={form.cnpj} onChange={e => set('cnpj', fmtCNPJ(e.target.value))} required /></div>
 <div><label style={labelStyle}>Telefone *</label>
 <input style={inputStyle} value={form.telefone} onChange={e => set('telefone', e.target.value)} required /></div>
 </div>
 </fieldset>

 <fieldset style={{ border: '1px solid var(--border)', borderRadius: 12, padding: 16 }}>
 <legend style={{ fontSize: 13, fontWeight: 700, padding: '0 8px' }}>Endereço da empresa</legend>
 <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 12 }}>
 <div><label style={labelStyle}>Rua *</label>
 <input style={inputStyle} value={form.endereco_rua} onChange={e => set('endereco_rua', e.target.value)} required /></div>
 <div><label style={labelStyle}>Número *</label>
 <input style={inputStyle} value={form.endereco_numero} onChange={e => set('endereco_numero', e.target.value)} required /></div>
 </div>
 <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginTop: 12 }}>
 <div><label style={labelStyle}>Complemento</label>
 <input style={inputStyle} value={form.endereco_compl} onChange={e => set('endereco_compl', e.target.value)} /></div>
 <div><label style={labelStyle}>Bairro *</label>
 <input style={inputStyle} value={form.endereco_bairro} onChange={e => set('endereco_bairro', e.target.value)} required /></div>
 </div>
 <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr', gap: 12, marginTop: 12 }}>
 <div><label style={labelStyle}>Cidade *</label>
 <input style={inputStyle} value={form.endereco_cidade} onChange={e => set('endereco_cidade', e.target.value)} required /></div>
 <div><label style={labelStyle}>UF *</label>
 <input style={inputStyle} maxLength={2} value={form.endereco_uf} onChange={e => set('endereco_uf', e.target.value.toUpperCase())} required /></div>
 <div><label style={labelStyle}>CEP *</label>
 <input style={inputStyle} value={form.endereco_cep} onChange={e => set('endereco_cep', fmtCEP(e.target.value))} required /></div>
 </div>
 </fieldset>

 {error && <div style={{ color: '#c0392b', fontSize: 13 }}> {error}</div>}

 <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
 <button type="submit" disabled={loading} className="btn btn-primary"
 style={{ padding: '12px 24px', fontSize: 14, fontWeight: 600 }}>
 {loading ? 'Salvando…' : 'Concluir cadastro de Editora'}
 </button>
 <button type="button" onClick={preencherDepois} disabled={loading}
 data-testid="btn-preencher-depois"
 style={{
 padding: '12px 24px', fontSize: 14, fontWeight: 600,
 background: 'transparent', color: 'var(--text-muted, #71717A)',
 border: '1px solid var(--border, #E5E7EB)', borderRadius: 10,
 cursor: loading ? 'not-allowed' : 'pointer',
 }}>
 Preencher depois
 </button>
 </div>
 </form>
 </div>
 )
}
