import React, { useEffect, useState } from 'react'
import { api } from '../lib/api'
import ContratosLicenciamentoLista from '../components/ContratosLicenciamentoLista'

export default function MeusContratos() {
 const [aba, setAba] = useState('edicao')
 const [contratos, setContratos] = useState([])
 const [edicaoLista, setEdicaoLista] = useState([])
 const [loading, setLoading] = useState(true)
 const [erro, setErro] = useState('')
 const [baixando, setBaixando] = useState(null)
 const [verConteudo, setVerConteudo] = useState(null)
 const [assinando, setAssinando] = useState(null)
 const [verEdicao, setVerEdicao] = useState(null)
 const [carregandoEdicao, setCarregandoEdicao] = useState(false)

 async function carregarTudo() {
 setLoading(true); setErro('')
 try {
 const [legacy, edicao] = await Promise.all([
 api.get('/perfis/me/contratos').catch(() => []),
 api.get('/contratos-edicao').catch(() => []),
 ])
 setContratos(legacy || [])
 setEdicaoLista(edicao || [])
 } catch (e) { setErro(e.message) }
 finally { setLoading(false) }
 }

 useEffect(() => { carregarTudo() }, [])

 async function baixarPdf(c) {
 try {
 setBaixando(c.id)
 const nomeObra = (c?.obras?.nome || 'obra').toLowerCase().replace(/[^a-z0-9]+/g, '-').slice(0, 40)
 await api.download(`/perfis/contratos/${c.id}/pdf`, `contrato-${nomeObra}-${c.id.slice(0, 8)}.pdf`)
 } catch (e) { alert('Erro ao baixar: ' + e.message) }
 finally { setBaixando(null) }
 }

 async function verTexto(c) {
 try {
 const detalhe = await api.get(`/perfis/contratos/${c.id}`)
 setVerConteudo({ ...c, conteudo: detalhe.conteudo })
 } catch (e) { alert('Erro ao abrir: ' + e.message) }
 }

 async function abrirEdicao(c) {
 setVerEdicao({ id: c.id, conteudo: '' })
 setCarregandoEdicao(true)
 try {
 const d = await api.get(`/contratos-edicao/${c.id}`)
 setVerEdicao({ id: c.id, conteudo: d?.contract_text || '(este contrato não possui texto registrado)' })
 } catch (e) {
 setVerEdicao({ id: c.id, conteudo: `Erro ao carregar: ${e.message}` })
 } finally {
 setCarregandoEdicao(false)
 }
 }

 async function assinar(c) {
 if (!confirm('Confirmar assinatura eletrônica deste contrato? Esta ação é registrada com data/hora e IP.')) return
 setAssinando(c.id)
 try {
 await api.post(`/contratos-edicao/${c.id}/assinar`, {})
 await carregarTudo()
 } catch (e) { alert('Erro ao assinar: ' + e.message) }
 finally { setAssinando(null) }
 }

 function statusLabel(s) {
 return ({
 pendente: { txt: 'Pendente', cor: '#d97706', bg: 'rgba(245,158,11,.15)' },
 assinado_parcial: { txt: 'Assinado parcial', cor: '#0891b2', bg: 'rgba(8,145,178,.15)' },
 assinado: { txt: 'Assinado', cor: '#16a34a', bg: 'rgba(34,197,94,.15)' },
 cancelado: { txt: 'Cancelado', cor: '#6b7280', bg: 'rgba(107,114,128,.15)' },
 })[s] || { txt: s, cor: '#6b7280', bg: 'rgba(107,114,128,.15)' }
 }

 return (
 <div data-testid="meus-contratos-page" style={{ padding: '32px 20px', maxWidth: 960, margin: '0 auto' }}>
 <header style={{ marginBottom: 16 }}>
 <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 6 }}>Meus contratos</h1>
 <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>
 Contratos assinados eletronicamente (MP 2.200-2/2001 &amp; Lei 14.063/2020).
 </p>
 </header>

 <div style={{ display: 'flex', gap: 2, borderBottom: '1px solid var(--border)', marginBottom: 24 }}>
 {[
 { id: 'edicao', label: 'Contratos de Edição' },
 { id: 'licenciamento', label: 'Licenciamentos' },
 ].map(t => (
 <button key={t.id} data-testid={`tab-${t.id}`} onClick={() => setAba(t.id)}
 style={{
 padding: '10px 16px', background: 'transparent', border: 'none',
 borderBottom: aba === t.id ? '2px solid var(--brand)' : '2px solid transparent',
 color: aba === t.id ? 'var(--brand)' : 'var(--text-muted)',
 fontSize: 13, fontWeight: aba === t.id ? 700 : 500, cursor: 'pointer', marginBottom: -1,
 }}>{t.label}</button>
 ))}
 </div>

 {aba === 'licenciamento' ? (
 <ContratosLicenciamentoLista />
 ) : (
 <>
 {loading && <p style={{ color: 'var(--text-muted)' }}>Carregando…</p>}
 {erro && <p style={{ color: '#c0392b' }}> {erro}</p>}

 {/* Contratos de Edição (autor ⇄ editora) */}
 {edicaoLista.length > 0 && (
 <section style={{ marginBottom: 30 }}>
 <h2 style={{ fontSize: 14, fontWeight: 700, marginBottom: 10 }}>Edição (autor ⇄ editora)</h2>
 <div style={{ border: '1px solid var(--border)', borderRadius: 12, overflow: 'hidden', overflowX: 'auto' }}>
 <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13, minWidth: 640 }}>
 <thead style={{ background: 'var(--surface-2, #fafafa)' }}>
 <tr>
 <th style={th}>Contrato</th>
 <th style={th}>Split (autor)</th>
 <th style={th}>Status</th>
 <th style={{ ...th, textAlign: 'right' }}>Ações</th>
 </tr>
 </thead>
 <tbody>
 {edicaoLista.map(c => {
 const sl = statusLabel(c.status)
 const podeAssinar = c.status !== 'assinado' && c.status !== 'cancelado'
 return (
 <tr key={c.id} style={{ borderTop: '1px solid var(--border)' }}>
 <td style={td}>
 <div style={{ fontWeight: 600, fontSize: 13, display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
 <span>Obra</span>
 <code title={c.obra_id} style={{
 fontFamily: 'monospace', fontSize: 11.5,
 background: 'var(--surface)', padding: '2px 6px',
 borderRadius: 4, border: '1px solid var(--border)',
 whiteSpace: 'nowrap',
 }}>{c.obra_id ? `${c.obra_id.slice(0, 8)}…` : '—'}</code>
 </div>
 <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
 {c.created_at && new Date(c.created_at).toLocaleDateString('pt-BR')}
 </div>
 </td>
 <td style={td}>{c.share_pct}%</td>
 <td style={td}>
 <span style={{ fontSize: 11, padding: '2px 8px', background: sl.bg, color: sl.cor, borderRadius: 4 }}>{sl.txt}</span>
 </td>
 <td style={{ ...td, textAlign: 'right' }}>
 <div style={{ display: 'inline-flex', gap: 6, justifyContent: 'flex-end' }}>
 <button className="btn"
 style={{ fontSize: 12, padding: '6px 12px', border: '1px solid var(--border)', background: 'transparent' }}
 onClick={() => abrirEdicao(c)}>
 Ver contrato
 </button>
 {podeAssinar && (
 <button className="btn btn-primary" disabled={assinando === c.id}
 style={{ fontSize: 12, padding: '6px 12px' }}
 onClick={() => assinar(c)}>
 {assinando === c.id ? 'Assinando…' : 'Assinar contrato'}
 </button>
 )}
 </div>
 </td>
 </tr>
 )
 })}
 </tbody>
 </table>
 </div>
 </section>
 )}

 {/* Contratos legacy (compositor) */}
 {!loading && !erro && contratos.length === 0 && edicaoLista.length === 0 && (
 <div style={{ padding: 40, border: '1px dashed var(--border)', borderRadius: 12, textAlign: 'center', color: 'var(--text-muted)', fontSize: 13 }}>
 Você ainda não possui contratos.
 </div>
 )}

 {contratos.length > 0 && (
 <section>
 <h2 style={{ fontSize: 14, fontWeight: 700, marginBottom: 10 }}>Contratos da plataforma</h2>
 <div style={{ border: '1px solid var(--border)', borderRadius: 12, overflow: 'hidden', overflowX: 'auto' }}>
 <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13, minWidth: 640 }}>
 <thead style={{ background: 'var(--surface-2, #fafafa)' }}>
 <tr>
 <th style={th}>Obra</th><th style={th}>Versão</th>
 <th style={th}>Assinado em</th><th style={{ ...th, textAlign: 'right' }}>Ações</th>
 </tr>
 </thead>
 <tbody>
 {contratos.map((c, i) => (
 <tr key={c.id} style={{ borderTop: '1px solid var(--border)' }}>
 <td style={td}>
 <div style={{ fontWeight: 600 }}>{c?.obras?.nome || 'Obra'}</div>
 <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>ID {c.id.slice(0, 8)}</div>
 </td>
 <td style={td}>{c.versao || 'v2.0'}</td>
 <td style={td}>{c.assinado_em ? new Date(c.assinado_em).toLocaleString('pt-BR') : '—'}</td>
 <td style={{ ...td, textAlign: 'right' }}>
 <button onClick={() => verTexto(c)} className="btn btn-ghost"
 style={{ marginRight: 8, fontSize: 12, padding: '6px 12px' }}>Ver texto</button>
 <button onClick={() => baixarPdf(c)} className="btn btn-primary" disabled={baixando === c.id}
 style={{ fontSize: 12, padding: '6px 12px' }}>
 {baixando === c.id ? 'Gerando…' : 'Baixar PDF'}
 </button>
 </td>
 </tr>
 ))}
 </tbody>
 </table>
 </div>
 </section>
 )}
 </>
 )}

 {verConteudo && (
 <div onClick={e => { if (e.target === e.currentTarget) setVerConteudo(null) }}
 style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,.6)', backdropFilter: 'blur(4px)',
 display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 700, padding: 24 }}>
 <div style={{ background: '#fff', borderRadius: 14, width: '100%', maxWidth: 780, maxHeight: '88vh', display: 'flex', flexDirection: 'column' }}>
 <div style={{ padding: '18px 22px', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
 <h2 style={{ fontSize: 15, fontWeight: 700 }}>Contrato — {verConteudo?.obras?.nome}</h2>
 <button onClick={() => setVerConteudo(null)} style={{ background: 'none', border: 'none', fontSize: 24, cursor: 'pointer', color: 'var(--text-muted)' }}>×</button>
 </div>
 <div style={{ padding: '18px 22px', overflowY: 'auto', flex: 1, fontSize: 12.5, lineHeight: 1.7, whiteSpace: 'pre-wrap' }}>
 {verConteudo.conteudo || 'Sem conteúdo.'}
 </div>
 </div>
 </div>
 )}

 {verEdicao && (
 <div onClick={e => { if (e.target === e.currentTarget) setVerEdicao(null) }}
 style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,.6)', backdropFilter: 'blur(4px)',
 display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 700, padding: 24 }}>
 <div style={{ background: '#fff', borderRadius: 14, width: '100%', maxWidth: 780, maxHeight: '88vh', display: 'flex', flexDirection: 'column' }}>
 <div style={{ padding: '18px 22px', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
 <h2 style={{ fontSize: 15, fontWeight: 700 }}>Contrato de Edição — Texto integral</h2>
 <button onClick={() => setVerEdicao(null)} style={{ background: 'none', border: 'none', fontSize: 24, cursor: 'pointer', color: 'var(--text-muted)' }}>×</button>
 </div>
 <div style={{ padding: '18px 22px', overflowY: 'auto', flex: 1, fontSize: 12.5, lineHeight: 1.7, whiteSpace: 'pre-wrap' }}>
 {carregandoEdicao ? 'Carregando…' : (verEdicao.conteudo || 'Sem conteúdo.')}
 </div>
 <div style={{ padding: '12px 22px', borderTop: '1px solid var(--border)', display: 'flex', justifyContent: 'flex-end' }}>
 <button className="btn" style={{ padding: '8px 14px' }} onClick={() => setVerEdicao(null)}>Fechar</button>
 </div>
 </div>
 </div>
 )}
 </div>
 )
}

const th = { textAlign: 'left', padding: '10px 14px', fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 0.5 }
const td = { padding: '12px 14px', verticalAlign: 'middle' }
