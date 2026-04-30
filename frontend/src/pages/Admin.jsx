import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../lib/api'
import { usePlayer } from '../contexts/PlayerContext'
import { IconPlay, IconPause, IconCopy, IconHourglass, IconCheck } from '../components/Icons'
import AdminSaude from './AdminSaude'

function fmt(cents) {
 return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format((cents ?? 0) / 100)
}

const ABAS = [
 { id: 'analiticos', label: 'Analíticos', icon: '' },
 { id: 'receita', label: 'Receita', icon: '' },
 { id: 'vendas', label: 'Vendas', icon: '' },
 { id: 'obras', label: 'Obras', icon: '' },
 { id: 'generos', label: 'Gêneros mais procurados', icon: '' },
 { id: 'contratos', label: 'Contratos', icon: '' },
 { id: 'saques', label: 'Autorizar saques', icon: '' },
 { id: 'auditoria', label: 'Auditoria de splits', icon: '' },
 { id: 'seguranca', label: 'Segurança', icon: '' },
 { id: 'saude', label: 'Saúde do sistema', icon: '' },
]

function StatCard({ label, value, sublabel, color = 'var(--brand)', big = false }) {
 return (
 <div style={{
 background: 'var(--surface)',
 border: '1px solid var(--border)',
 borderRadius: 14, padding: '16px 18px',
 }}>
 <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 1 }}>
 {label}
 </div>
 <div style={{ fontSize: big ? 28 : 22, fontWeight: 800, color, marginTop: 6 }}>
 {value}
 </div>
 {sublabel && <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>{sublabel}</div>}
 </div>
 )
}

export default function Admin() {
 const [aba, setAba] = useState('analiticos')
 const [resumo, setResumo] = useState(null)
 const [extras, setExtras] = useState(null)
 const [saques, setSaques] = useState([])
 const [saqueLoading, setSaqueLoading] = useState(false)
 const [generos, setGeneros] = useState([])
 const [audit, setAudit] = useState([])
 const [volume, setVolume] = useState([])
 const [loading, setLoading] = useState(true)
 const [reloadingExtras, setReloadingExtras] = useState(false)

 async function carregarBase() {
   const [r, e, g, a, v] = await Promise.all([
     api.get('/admin/bi/resumo').catch(() => null),
     api.get('/admin/bi/extras').catch(() => null),
     api.get('/admin/bi/generos').catch(() => []),
     api.get('/admin/bi/auditoria?per_page=30').catch(() => []),
     api.get('/admin/bi/volume?dias=30').catch(() => []),
   ])
   setResumo(r); setExtras(e); setGeneros(g); setAudit(a); setVolume(v)
 }

 async function reloadExtras() {
   setReloadingExtras(true)
   try {
     const [r, e] = await Promise.all([
       api.get('/admin/bi/resumo').catch(() => null),
       api.get('/admin/bi/extras').catch(() => null),
     ])
     if (r) setResumo(r)
     if (e) setExtras(e)
   } finally { setReloadingExtras(false) }
 }

 useEffect(() => {
   carregarBase().finally(() => setLoading(false))
 }, [])

 // Auto-refresh dos analíticos a cada 15s enquanto a aba estiver aberta
 useEffect(() => {
   if (aba !== 'analiticos') return
   const intv = setInterval(() => { reloadExtras() }, 15000)
   return () => clearInterval(intv)
 }, [aba])

 async function loadSaques() {
 setSaqueLoading(true)
 try {
 const data = await api.get('/admin/saques')
 setSaques(data)
 } catch (e) { console.error(e) }
 finally { setSaqueLoading(false) }
 }

 useEffect(() => {
 if (aba !== 'saques') return
 loadSaques()
 const intv = setInterval(() => loadSaques(), 5000)
 return () => clearInterval(intv)
 }, [aba])

 async function handleSaque(id, acao, motivo) {
 if (acao === 'rejeitado' && !motivo) {
 const m = prompt('Motivo da rejeição (obrigatório):')
 if (!m) return
 motivo = m
 }
 if (!confirm(`Confirmar ${acao === 'pago' ? 'marcar como PAGO' : acao === 'processando' ? 'marcar como PROCESSANDO' : 'REJEITAR e devolver valor'}?`)) return
 try {
 await api.post(`/admin/saques/${id}/aprovar`, { acao, motivo })
 await loadSaques()
 } catch (e) {
 alert('Erro: ' + e.message)
 }
 }

 if (loading) return <div style={{ padding: 32 }}><p style={{ color: 'var(--text-muted)' }}>Carregando painel…</p></div>

 return (
 <div style={{ padding: 32, maxWidth: 1100 }}>
 <div style={{ marginBottom: 24, display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 12 }}>
 <div>
 <h1 style={{ fontSize: 26, fontWeight: 800 }}>Painel administrador</h1>
 <p style={{ color: 'var(--text-muted)', fontSize: 14 }}>Visão consolidada da plataforma Gravan</p>
 </div>
 <a
 href="/admin/landing"
 style={{
 display: 'inline-flex', alignItems: 'center', gap: 8,
 padding: '10px 18px', borderRadius: 10, fontSize: 13, fontWeight: 700,
 background: 'var(--brand)', color: '#fff', textDecoration: 'none',
 boxShadow: '0 2px 8px rgba(0,0,0,.15)',
 whiteSpace: 'nowrap',
 }}
 >
 ✏️ Editar Landing Page
 </a>
 </div>

 <div style={{
 display: 'flex', gap: 4, marginBottom: 24,
 borderBottom: '1px solid var(--border)',
 flexWrap: 'wrap',
 }}>
 {ABAS.map(a => (
 <button key={a.id} onClick={() => setAba(a.id)}
 style={{
 padding: '10px 18px', border: 'none', background: 'none',
 cursor: 'pointer', fontSize: 14,
 fontWeight: aba === a.id ? 700 : 500,
 color: aba === a.id ? 'var(--brand)' : 'var(--text-secondary)',
 borderBottom: aba === a.id ? '3px solid var(--brand)' : '3px solid transparent',
 marginBottom: -1, display: 'flex', alignItems: 'center', gap: 6,
 }}>
 <span>{a.icon}</span> {a.label}
 </button>
 ))}
 </div>

 {/* ── ANALÍTICOS ── */}
 {aba === 'analiticos' && resumo && (
 <AnaliticosPanel resumo={resumo} extras={extras} reloadingExtras={reloadingExtras} reloadExtras={reloadExtras} />
 )}

 {/* ── RECEITA ── */}
 {aba === 'receita' && resumo && (
 <div>
 <div style={{
 display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
 gap: 14, marginBottom: 24,
 }}>
 <StatCard label="Receita bruta total" value={fmt(resumo.receita_bruta_cents)} sublabel="Soma de todas as vendas confirmadas" big color="var(--brand)" />
 <StatCard label="Receita líquida da plataforma" value={fmt(resumo.receita_plataforma_cents)} sublabel="Retido direto na fonte" big color="var(--success)" />
 <StatCard label="Pago aos compositores" value={fmt(resumo.receita_compositores_cents)} sublabel="Distribuído via wallets dos compositores" big color="var(--brand)" />
 </div>

 <div className="card">
 <h2 style={{ fontSize: 15, fontWeight: 700, marginBottom: 14 }}>Histórico de vendas (últimas)</h2>
 {volume.length === 0 ? (
 <p style={{ color: 'var(--text-muted)', fontSize: 13 }}>Nenhuma venda registrada ainda.</p>
 ) : (
 <div style={{ overflowX: 'auto' }}>
 <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
 <thead>
 <tr style={{ borderBottom: '1px solid var(--border)' }}>
 {['Data', 'Método', 'Status', 'Vendas', 'Bruta', 'Plataforma', 'Compositores'].map(h => (
 <th key={h} style={{ padding: '10px 12px', textAlign: 'left', color: 'var(--text-muted)', fontWeight: 600, fontSize: 11, textTransform: 'uppercase', letterSpacing: 1 }}>{h}</th>
 ))}
 </tr>
 </thead>
 <tbody>
 {volume.map((v, i) => (
 <tr key={i} style={{ borderBottom: '1px solid var(--border)' }}>
 <td style={{ padding: '10px 12px', whiteSpace: 'nowrap' }}>{new Date(v.dia).toLocaleDateString('pt-BR')}</td>
 <td style={{ padding: '10px 12px', textTransform: 'uppercase', fontWeight: 600 }}>{v.metodo}</td>
 <td style={{ padding: '10px 12px' }}>{v.status}</td>
 <td style={{ padding: '10px 12px' }}>{v.total_transacoes}</td>
 <td style={{ padding: '10px 12px' }}>{fmt(v.receita_bruta_cents)}</td>
 <td style={{ padding: '10px 12px', color: 'var(--success)' }}>{fmt(v.receita_plataforma_cents)}</td>
 <td style={{ padding: '10px 12px', color: 'var(--brand)' }}>{fmt(v.pago_compositores_cents)}</td>
 </tr>
 ))}
 </tbody>
 </table>
 </div>
 )}
 </div>
 </div>
 )}

 {/* ── VENDAS ── (histórico completo de transações) */}
 {aba === 'vendas' && <VendasPanel />}

 {/* ── OBRAS ── (lista todas as obras + GERAR / BAIXAR DOSSIÊ) */}
 {aba === 'obras' && <ObrasPanel />}

 {/* ── CONTRATOS ── (todos os contratos da plataforma em vigor) */}
 {aba === 'contratos' && <ContratosPanel />}

 {/* ── GÊNEROS ── */}
 {aba === 'generos' && (
 <div className="card">
 <h2 style={{ fontSize: 15, fontWeight: 700, marginBottom: 14 }}>Gêneros mais procurados</h2>
 {generos.length === 0 ? (
 <p style={{ color: 'var(--text-muted)', fontSize: 13 }}>Sem dados ainda.</p>
 ) : (
 <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
 <thead>
 <tr style={{ borderBottom: '1px solid var(--border)' }}>
 {['Gênero', 'Obras publicadas', 'Vendas', 'Receita gerada'].map(h => (
 <th key={h} style={{ padding: '10px 12px', textAlign: 'left', color: 'var(--text-muted)', fontWeight: 600, fontSize: 11, textTransform: 'uppercase', letterSpacing: 1 }}>{h}</th>
 ))}
 </tr>
 </thead>
 <tbody>
 {generos.map((g, i) => (
 <tr key={i} style={{ borderBottom: '1px solid var(--border)' }}>
 <td style={{ padding: '12px', fontWeight: 700 }}>{g.genero}</td>
 <td style={{ padding: '12px' }}>{g.total_obras}</td>
 <td style={{ padding: '12px', color: 'var(--success)' }}>{g.total_vendas}</td>
 <td style={{ padding: '12px', color: 'var(--brand)', fontWeight: 700 }}>{fmt(g.receita_cents)}</td>
 </tr>
 ))}
 </tbody>
 </table>
 )}
 </div>
 )}

 {/* ── SAQUES ── */}
 {aba === 'saques' && (
 <div className="card">
 <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14, flexWrap: 'wrap', gap: 8 }}>
 <div>
 <h2 style={{ fontSize: 15, fontWeight: 700 }}>Saques solicitados</h2>
 <div style={{ marginTop: 8, marginBottom: 4, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
 <a href="/admin/saques" style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '6px 14px', borderRadius: 8, fontSize: 12, fontWeight: 700, background: 'var(--brand)', color: '#fff', textDecoration: 'none' }}> Painel de saques ↗</a>
 <a href="/admin/saques/historico" style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '6px 14px', borderRadius: 8, fontSize: 12, fontWeight: 700, background: 'var(--surface-2)', color: 'var(--brand)', border: '1px solid var(--border)', textDecoration: 'none' }}> Histórico & Exportar ↗</a>
 </div>
 <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>
 <span style={{
 display: 'inline-block', width: 8, height: 8, borderRadius: '50%',
 background: 'var(--success)', marginRight: 6,
 animation: 'pulse 2s infinite',
 }}></span>
 Atualização automática a cada 5 segundos
 {saques.filter(s => s.status === 'solicitado').length > 0 && (
 <span style={{
 marginLeft: 10, padding: '2px 8px',
 background: 'var(--warning-bg)', color: 'var(--warning)',
 borderRadius: 99, fontSize: 11, fontWeight: 700,
 }}>
 {saques.filter(s => s.status === 'solicitado').length} aguardando
 </span>
 )}
 </p>
 </div>
 <button onClick={loadSaques} style={{ background: 'none', border: '1px solid var(--border)', padding: '6px 12px', borderRadius: 8, color: 'var(--brand)', fontSize: 13, cursor: 'pointer' }}>
 ↻ atualizar agora
 </button>
 </div>
 <style>{`
 @keyframes pulse {
 0%, 100% { opacity: 1; }
 50% { opacity: 0.4; }
 }
 `}</style>

 {saqueLoading ? (
 <p style={{ color: 'var(--text-muted)' }}>Carregando…</p>
 ) : saques.length === 0 ? (
 <p style={{ color: 'var(--text-muted)', fontSize: 13 }}>Nenhum saque solicitado no momento.</p>
 ) : (
 <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
 {saques.map(s => {
 const statusMap = {
 solicitado: { bg: 'var(--warning-bg)', cor: 'var(--warning)', label: '⏱ Solicitado' },
 processando: { bg: 'var(--brand-light)', cor: 'var(--brand)', label: '↻ Processando' },
 pago: { bg: 'var(--success-bg)', cor: 'var(--success)', label: '✓ Pago' },
 rejeitado: { bg: 'var(--error-bg)', cor: 'var(--error)', label: '✕ Rejeitado' },
 }
 const st = statusMap[s.status] || statusMap.solicitado
 return (
 <div key={s.id} style={{
 padding: 16, background: 'var(--surface-2)', borderRadius: 10,
 border: '1px solid var(--border)',
 }}>
 <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10, flexWrap: 'wrap', gap: 8 }}>
 <div>
 <div style={{ fontWeight: 700, fontSize: 18 }}>{fmt(s.valor_cents)}</div>
 <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
 {s.perfis?.nome_artistico || s.perfis?.nome} · {s.perfis?.email}
 </div>
 <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
 Solicitado em {new Date(s.created_at).toLocaleString('pt-BR')}
 {s.processed_at && ' · processado em ' + new Date(s.processed_at).toLocaleString('pt-BR')}
 </div>
 </div>
 <span style={{ fontSize: 12, fontWeight: 600, padding: '4px 12px', borderRadius: 99, background: st.bg, color: st.cor }}>
 {st.label}
 </span>
 </div>

 {s.motivo_rejeicao && (
 <div style={{ padding: 10, background: 'var(--error-bg)', borderRadius: 8, marginBottom: 10, fontSize: 12, color: 'var(--error)' }}>
 <strong>Motivo da rejeição:</strong> {s.motivo_rejeicao}
 </div>
 )}

 {s.status === 'solicitado' && (
 <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
 <button className="btn btn-secondary btn-sm" onClick={() => handleSaque(s.id, 'processando')}>↻ Em processamento</button>
 <button className="btn btn-primary btn-sm" onClick={() => handleSaque(s.id, 'pago')}>✓ Marcar como pago</button>
 <button className="btn btn-danger btn-sm" onClick={() => handleSaque(s.id, 'rejeitado')}>✕ Rejeitar</button>
 </div>
 )}
 {s.status === 'processando' && (
 <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
 <button className="btn btn-primary btn-sm" onClick={() => handleSaque(s.id, 'pago')}>✓ Confirmar pagamento</button>
 <button className="btn btn-danger btn-sm" onClick={() => handleSaque(s.id, 'rejeitado')}>✕ Rejeitar</button>
 </div>
 )}
 </div>
 )
 })}
 </div>
 )}
 </div>
 )}

 {/* ── AUDITORIA ── */}
 {aba === 'auditoria' && (
 <div className="card">
 <h2 style={{ fontSize: 15, fontWeight: 700, marginBottom: 14 }}>Auditoria de splits financeiros</h2>
 {audit.length === 0 ? (
 <p style={{ color: 'var(--text-muted)', fontSize: 13 }}>Nenhum split registrado ainda.</p>
 ) : (
 <div style={{ overflowX: 'auto' }}>
 <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
 <thead>
 <tr style={{ borderBottom: '1px solid var(--border)' }}>
 {['Data', 'Obra', 'Compositor', 'Venda', 'Recebido', 'Status'].map(h => (
 <th key={h} style={{ padding: '10px', textAlign: 'left', color: 'var(--text-muted)', fontWeight: 600, fontSize: 11, textTransform: 'uppercase', letterSpacing: 1, whiteSpace: 'nowrap' }}>{h}</th>
 ))}
 </tr>
 </thead>
 <tbody>
 {audit.map((a, i) => (
 <tr key={i} style={{ borderBottom: '1px solid var(--border)' }}>
 <td style={{ padding: '10px', whiteSpace: 'nowrap' }}>{new Date(a.created_at).toLocaleDateString('pt-BR')}</td>
 <td style={{ padding: '10px', fontWeight: 600 }}>{a.obra_nome}</td>
 <td style={{ padding: '10px' }}>{a.compositor_nome}</td>
 <td style={{ padding: '10px' }}>{fmt(a.valor_cents)}</td>
 <td style={{ padding: '10px', color: 'var(--success)', fontWeight: 700 }}>{fmt(a.pago_cents)}</td>
 <td style={{ padding: '10px' }}>
 <span style={{
 fontSize: 11, fontWeight: 600, padding: '2px 8px',
 background: a.status === 'confirmada' ? 'var(--success-bg)' : 'var(--surface-2)',
 color: a.status === 'confirmada' ? 'var(--success)' : 'var(--text-muted)',
 }}>{a.status}</span>
 </td>
 </tr>
 ))}
 </tbody>
 </table>
 </div>
 )}
 </div>
 )}

 {/* ── SEGURANÇA ── */}
 {aba === 'seguranca' && <SecurityPanel />}

 {/* ── SAÚDE DO SISTEMA ── */}
 {aba === 'saude' && <AdminSaude />}
 </div>
 )
}

// ═══════════════════════════════════════════════════════════════════
// PAINEL DE VENDAS (admin)
// Histórico completo de transações da plataforma com filtros e detalhes.
// ═══════════════════════════════════════════════════════════════════
function fmtData(iso) {
 if (!iso) return '—'
 try {
   return new Date(iso).toLocaleString('pt-BR', {
     day: '2-digit', month: '2-digit', year: 'numeric',
     hour: '2-digit', minute: '2-digit',
   })
 } catch { return iso }
}

const STATUS_VENDA = {
 confirmada: { bg: 'rgba(34,197,94,.15)',  cor: '#16a34a', label: '✓ Confirmada' },
 pendente:   { bg: 'rgba(245,158,11,.15)', cor: '#d97706', label: '⏱ Pendente' },
 cancelada:  { bg: 'rgba(239,68,68,.15)',  cor: '#dc2626', label: '✕ Cancelada' },
 estornada:  { bg: 'rgba(107,114,128,.15)', cor: '#6b7280', label: '↩ Estornada' },
}

function VendasPanel() {
 const [data, setData] = useState(null)
 const [erro, setErro] = useState('')
 const [loading, setLoading] = useState(true)
 const [filtros, setFiltros] = useState({ status: 'confirmada', dias: 90, limit: 200 })
 const [expandida, setExpandida] = useState(null)

 async function carregar(f = filtros) {
   setLoading(true); setErro('')
   try {
     const qs = new URLSearchParams(f).toString()
     const r = await api.get(`/admin/historico-vendas?${qs}`)
     setData(r)
   } catch (e) { setErro(e.message); setData(null) }
   finally { setLoading(false) }
 }

 useEffect(() => { carregar() }, [])

 function aplicar(novo) {
   const f = { ...filtros, ...novo }
   setFiltros(f); carregar(f)
 }

 const itens = data?.itens || []

 return (
   <div className="card">
     <div style={{ display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12, alignItems: 'flex-end', marginBottom: 16 }}>
       <div>
         <h2 style={{ fontSize: 15, fontWeight: 700 }}>Histórico de vendas — todos os usuários</h2>
         {data && (
           <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>
             {data.total_transacoes} venda(s) confirmada(s) · Bruta: <strong style={{ color: 'var(--brand)' }}>{fmt(data.total_cents)}</strong> · Plataforma: <strong style={{ color: 'var(--success)' }}>{fmt(data.plataforma_cents)}</strong>
           </div>
         )}
       </div>
       <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'flex-end' }}>
         <label style={{ fontSize: 11, color: 'var(--text-muted)', display: 'flex', flexDirection: 'column', gap: 4 }}>
           STATUS
           <select value={filtros.status} onChange={e => aplicar({ status: e.target.value })}
             style={{ padding: '6px 10px', borderRadius: 8, border: '1px solid var(--border)', background: 'var(--surface)', fontSize: 13 }}>
             <option value="confirmada">Confirmada</option>
             <option value="pendente">Pendente</option>
             <option value="cancelada">Cancelada</option>
             <option value="todas">Todas</option>
           </select>
         </label>
         <label style={{ fontSize: 11, color: 'var(--text-muted)', display: 'flex', flexDirection: 'column', gap: 4 }}>
           PERÍODO
           <select value={filtros.dias} onChange={e => aplicar({ dias: Number(e.target.value) })}
             style={{ padding: '6px 10px', borderRadius: 8, border: '1px solid var(--border)', background: 'var(--surface)', fontSize: 13 }}>
             <option value={7}>7 dias</option>
             <option value={30}>30 dias</option>
             <option value={90}>90 dias</option>
             <option value={365}>1 ano</option>
             <option value={730}>2 anos</option>
           </select>
         </label>
         <button onClick={() => carregar()} disabled={loading}
           style={{ background: 'none', border: '1px solid var(--border)', padding: '6px 12px', borderRadius: 8, color: 'var(--brand)', fontSize: 13, cursor: loading ? 'wait' : 'pointer' }}>
           ↻ {loading ? 'atualizando…' : 'atualizar'}
         </button>
       </div>
     </div>

     {erro && <div style={{ color: '#c0392b', fontSize: 13, marginBottom: 12 }}>{erro}</div>}
     {loading && !data && <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>Carregando…</div>}

     {data && itens.length === 0 && (
       <div style={{ padding: 22, fontSize: 13, color: 'var(--text-muted)', textAlign: 'center', border: '1px dashed var(--border)', borderRadius: 10 }}>
         Nenhuma venda no período / filtro selecionado.
       </div>
     )}

     {itens.length > 0 && (
       <div style={{ overflowX: 'auto' }}>
         <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
           <thead>
             <tr style={{ borderBottom: '1px solid var(--border)' }}>
               {['Data', 'Obra', 'Titular', 'Comprador', 'Status', 'Bruto', 'Plataforma', 'Líquido', ''].map(h => (
                 <th key={h} style={{ padding: '10px 12px', textAlign: 'left', color: 'var(--text-muted)', fontWeight: 700, fontSize: 11, textTransform: 'uppercase', letterSpacing: 1 }}>{h}</th>
               ))}
             </tr>
           </thead>
           <tbody>
             {itens.map(it => {
               const s = STATUS_VENDA[it.status] || { bg: 'var(--surface-2)', cor: 'var(--text-muted)', label: it.status }
               const aberto = expandida === it.id
               return (
                 <React.Fragment key={it.id}>
                   <tr style={{ borderBottom: '1px solid var(--border)', background: aberto ? 'rgba(0,0,0,.02)' : 'transparent' }}>
                     <td style={{ padding: '10px 12px', whiteSpace: 'nowrap', color: 'var(--text-secondary)' }}>{fmtData(it.data)}</td>
                     <td style={{ padding: '10px 12px', fontWeight: 600 }}>{it.obra?.nome || '—'}</td>
                     <td style={{ padding: '10px 12px' }}>{it.titular?.nome || '—'}</td>
                     <td style={{ padding: '10px 12px' }}>{it.comprador?.nome || '—'}</td>
                     <td style={{ padding: '10px 12px' }}>
                       <span style={{ fontSize: 11, padding: '3px 9px', background: s.bg, color: s.cor, borderRadius: 99, fontWeight: 700, whiteSpace: 'nowrap' }}>
                         {s.label}
                       </span>
                     </td>
                     <td style={{ padding: '10px 12px', whiteSpace: 'nowrap' }}>{fmt(it.valor_total_cents)}</td>
                     <td style={{ padding: '10px 12px', whiteSpace: 'nowrap', color: 'var(--success)' }}>{fmt(it.plataforma_cents)}</td>
                     <td style={{ padding: '10px 12px', whiteSpace: 'nowrap', color: 'var(--brand)', fontWeight: 700 }}>{fmt(it.liquido_cents)}</td>
                     <td style={{ padding: '10px 12px', textAlign: 'right' }}>
                       {it.beneficiarios && it.beneficiarios.length > 0 && (
                         <button onClick={() => setExpandida(aberto ? null : it.id)}
                           style={{ background: 'none', border: '1px solid var(--border)', padding: '4px 10px', borderRadius: 8, color: 'var(--brand)', fontSize: 11, cursor: 'pointer' }}>
                           {aberto ? '▴ ocultar' : `▾ ${it.beneficiarios.length} repasse(s)`}
                         </button>
                       )}
                     </td>
                   </tr>
                   {aberto && (
                     <tr style={{ background: 'rgba(0,0,0,.02)' }}>
                       <td colSpan={9} style={{ padding: '14px 18px' }}>
                         <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 8 }}>
                           Beneficiários
                         </div>
                         <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                           <thead>
                             <tr style={{ color: 'var(--text-muted)' }}>
                               <th style={{ padding: '6px 10px', textAlign: 'left', fontWeight: 600 }}>Perfil</th>
                               <th style={{ padding: '6px 10px', textAlign: 'left', fontWeight: 600 }}>Papel</th>
                               <th style={{ padding: '6px 10px', textAlign: 'right', fontWeight: 600 }}>Share</th>
                               <th style={{ padding: '6px 10px', textAlign: 'right', fontWeight: 600 }}>Valor recebido</th>
                             </tr>
                           </thead>
                           <tbody>
                             {it.beneficiarios.map((b, i) => (
                               <tr key={i} style={{ borderTop: '1px solid var(--border)' }}>
                                 <td style={{ padding: '6px 10px', fontWeight: 600 }}>{b.nome || '—'}</td>
                                 <td style={{ padding: '6px 10px', color: 'var(--text-muted)', textTransform: 'capitalize' }}>{b.role || '—'}</td>
                                 <td style={{ padding: '6px 10px', textAlign: 'right' }}>{b.share_pct != null ? `${Number(b.share_pct).toFixed(0)}%` : '—'}</td>
                                 <td style={{ padding: '6px 10px', textAlign: 'right', fontWeight: 700, color: 'var(--brand)' }}>{fmt(b.valor_cents)}</td>
                               </tr>
                             ))}
                           </tbody>
                         </table>
                       </td>
                     </tr>
                   )}
                 </React.Fragment>
               )
             })}
           </tbody>
         </table>
       </div>
     )}
   </div>
 )
}


// ═══════════════════════════════════════════════════════════════════
// PAINEL DE OBRAS (admin)
// Lista todas as obras com ID único e botões de GERAR/BAIXAR DOSSIÊ.
// ═══════════════════════════════════════════════════════════════════
function ObrasPanel() {
 const { playObra, obra: obraAtual, playing } = usePlayer()
 const [obras, setObras] = useState([])
 const [loading, setLoading] = useState(true)
 const [error, setError] = useState('')
 const [query, setQuery] = useState('')
 const [busy, setBusy] = useState({}) // { obraId: 'gerar' | 'baixar' }
 const [copiedId, setCopiedId] = useState(null)
 const [feedback, setFeedback] = useState(null) // { obraId, type, message }

 async function load() {
 setLoading(true); setError('')
 try {
 const data = await api.get('/dossies/admin/obras')
 setObras(Array.isArray(data) ? data : [])
 } catch (e) {
 setError(e.message)
 } finally { setLoading(false) }
 }

 useEffect(() => { load() }, [])

 const filtered = !query.trim() ? obras : obras.filter(o => {
 const q = query.trim().toLowerCase()
 return (
 (o.id || '').toLowerCase().includes(q) ||
 (o.nome || '').toLowerCase().includes(q) ||
 (o.titular?.nome || '').toLowerCase().includes(q) ||
 (o.titular?.email || '').toLowerCase().includes(q)
 )
 })

 function showFeedback(obraId, type, message) {
 setFeedback({ obraId, type, message })
 setTimeout(() => setFeedback(prev => prev?.obraId === obraId ? null : prev), 4000)
 }

 async function handleGerar(obra) {
 if (obra.dossie && !confirm(
 `Esta obra já possui dossiê gerado em ${new Date(obra.dossie.created_at).toLocaleString('pt-BR')}.\n\n` +
 `Deseja regenerar (substituirá o anterior)?`
 )) return

 setBusy(prev => ({ ...prev, [obra.id]: 'gerar' }))
 try {
 const r = await api.post(`/dossies/obras/${obra.id}`, {})
 // Atualiza apenas a linha alterada — mais leve do que recarregar tudo
 setObras(prev => prev.map(o => o.id === obra.id
 ? { ...o, dossie: { id: r.id, hash_sha256: r.hash_sha256, created_at: r.created_at } }
 : o
 ))
 showFeedback(obra.id, 'success', '✓ Dossiê gerado com sucesso')
 } catch (e) {
 showFeedback(obra.id, 'error', ' ' + (e.message || 'Erro ao gerar dossiê'))
 } finally {
 setBusy(prev => { const n = { ...prev }; delete n[obra.id]; return n })
 }
 }

 async function handleBaixar(obra) {
 if (!obra.dossie) return
 setBusy(prev => ({ ...prev, [obra.id]: 'baixar' }))
 try {
 const safeName = (obra.nome || obra.id).replace(/[^a-zA-Z0-9-_]/g, '_').slice(0, 60)
 await api.download(`/dossies/${obra.dossie.id}/download`, `dossie-${safeName}.zip`)
 } catch (e) {
 showFeedback(obra.id, 'error', ' Erro ao baixar: ' + e.message)
 } finally {
 setBusy(prev => { const n = { ...prev }; delete n[obra.id]; return n })
 }
 }

 async function copyId(id) {
 try {
 await navigator.clipboard.writeText(id)
 setCopiedId(id)
 setTimeout(() => setCopiedId(prev => prev === id ? null : prev), 1400)
 } catch { /* ignora */ }
 }

 return (
 <div className="card">
 {/* MARCADOR DE VERSÃO — se você vê esta tarja amarela, o Admin.jsx novo
 foi carregado com sucesso. Pode remover depois de validado. */}
 <div style={{
 marginBottom: 14, padding: '8px 12px', borderRadius: 6,
 background: '#FEF3C7', color: '#92400E',
 fontSize: 12, fontWeight: 700, border: '1px solid #FCD34D',
 }}>
 ✓ Painel Obras carregado — versão atualizada (abril/2026)
 </div>

 <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14, flexWrap: 'wrap', gap: 12 }}>
 <div>
 <h2 style={{ fontSize: 15, fontWeight: 700 }}>Todas as obras cadastradas</h2>
 <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>
 Cada obra tem um <strong>ID único</strong>. Use os botões para gerar
 ou baixar o dossiê (.zip) oficial.
 </p>
 </div>
 <button
 onClick={load}
 style={{ background: 'none', border: '1px solid var(--border)', padding: '6px 12px', borderRadius: 8, color: 'var(--brand)', fontSize: 13, cursor: 'pointer' }}>
 ↻ atualizar
 </button>
 </div>

 <div style={{ position: 'relative', marginBottom: 14 }}>
 <input
 type="search"
 value={query}
 onChange={e => setQuery(e.target.value)}
 placeholder="Buscar por nome, ID, titular ou email…"
 className="input"
 style={{ paddingLeft: 36 }}
 />
 <span style={{
 position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)',
 color: 'var(--text-muted)', pointerEvents: 'none',
 }}>⌕</span>
 </div>

 {loading && <p style={{ color: 'var(--text-muted)', fontSize: 13 }}>Carregando obras…</p>}
 {error && <p style={{ color: 'var(--error)', fontSize: 13 }}>{error}</p>}

 {!loading && !error && filtered.length === 0 && (
 <div style={{
 padding: 36, textAlign: 'center', color: 'var(--text-muted)',
 border: '1px dashed var(--border)', borderRadius: 10,
 }}>
 {obras.length === 0 ? 'Nenhuma obra cadastrada na plataforma ainda.' : 'Nenhuma obra encontrada para sua busca.'}
 </div>
 )}

 {!loading && filtered.length > 0 && (
 <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
 {filtered.map(o => {
 const isPlaying = obraAtual?.id === o.id && playing
 return (
 <div key={o.id} style={{
 padding: 14, background: 'var(--surface-2)', borderRadius: 10,
 border: '1px solid var(--border)',
 display: 'flex', alignItems: 'center', gap: 14, flexWrap: 'wrap',
 }}>
 {/* Botão de reproduzir / pausar — usa o GlobalPlayer */}
 <button
 onClick={() => playObra(o)}
 disabled={!o.audio_path}
 title={o.audio_path ? (isPlaying ? 'Pausar' : 'Tocar prévia') : 'Áudio indisponível'}
 style={{
 width: 44, height: 44, borderRadius: 8,
 background: o.audio_path
 ? 'linear-gradient(135deg,#083257,#09090B)'
 : 'var(--surface)',
 color: o.audio_path ? '#fff' : 'var(--text-muted)',
 border: o.audio_path ? 'none' : '1px solid var(--border)',
 cursor: o.audio_path ? 'pointer' : 'not-allowed',
 fontSize: 14, flexShrink: 0,
 }}>
 {isPlaying ? <IconPause size={16} /> : <IconPlay size={16} />}
 </button>

 <div style={{ flex: 1, minWidth: 260 }}>
 <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
 <span style={{ fontWeight: 700, fontSize: 15 }}>
 {o.nome || '(sem nome)'}
 </span>
 {o.genero && (
 <span style={{
 fontSize: 10, fontWeight: 700, padding: '2px 8px',
 background: 'var(--brand-light)', color: 'var(--brand)',
 borderRadius: 99, textTransform: 'uppercase', letterSpacing: 1,
 }}>{o.genero}</span>
 )}
 {o.dossie && (
 <span style={{
 fontSize: 10, fontWeight: 700, padding: '2px 8px',
 background: 'var(--success-bg)', color: 'var(--success)',
 borderRadius: 99, letterSpacing: 1, textTransform: 'uppercase',
 }}>✓ dossiê pronto</span>
 )}
 </div>

 <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 6, fontSize: 12 }}>
 <span style={{ color: 'var(--text-muted)' }}>ID:</span>
 <code style={{
 fontFamily: 'monospace', fontSize: 11.5,
 background: 'var(--surface)', padding: '2px 6px',
 borderRadius: 4, border: '1px solid var(--border)',
 }}>{o.id}</code>
 <button
 onClick={() => copyId(o.id)}
 title="Copiar ID"
 style={{
 background: 'none', border: 'none', cursor: 'pointer',
 color: copiedId === o.id ? 'var(--success)' : 'var(--text-muted)',
 fontSize: 12, padding: '2px 4px',
 }}>
 {copiedId === o.id ? (<><IconCheck size={12} /> copiado</>) : <IconCopy size={14} />}
 </button>
 </div>

 <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
 Titular: {o.titular?.nome || '—'}
 {o.titular?.email && ` · ${o.titular.email}`}
 {o.created_at && ` · cadastrada em ${new Date(o.created_at).toLocaleDateString('pt-BR')}`}
 {typeof o.preco_cents === 'number' && ` · ${fmt(o.preco_cents)}`}
 </div>

 {feedback?.obraId === o.id && (
 <div style={{
 marginTop: 8, padding: '6px 10px', borderRadius: 6, fontSize: 12,
 background: feedback.type === 'success' ? 'var(--success-bg)' : 'var(--error-bg)',
 color: feedback.type === 'success' ? 'var(--success)' : 'var(--error)',
 }}>
 {feedback.message}
 </div>
 )}
 </div>

 <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
 <button
 onClick={() => handleGerar(o)}
 disabled={!!busy[o.id]}
 style={{
 background: o.dossie ? 'transparent' : 'var(--brand)',
 color: o.dossie ? 'var(--brand)' : '#fff',
 border: '1px solid var(--brand)',
 borderRadius: 6, padding: '8px 14px',
 cursor: busy[o.id] ? 'not-allowed' : 'pointer',
 fontSize: 12, fontWeight: 700, whiteSpace: 'nowrap',
 opacity: busy[o.id] === 'gerar' ? 0.6 : 1,
 }}>
 {busy[o.id] === 'gerar'
 ? (<><IconHourglass size={12} /> Gerando…</>)
 : (o.dossie ? '↻ REGENERAR DOSSIÊ' : 'GERAR DOSSIÊ')}
 </button>

 <button
 onClick={() => handleBaixar(o)}
 disabled={!o.dossie || !!busy[o.id]}
 title={!o.dossie ? 'Gere o dossiê primeiro' : 'Baixar ZIP do dossiê'}
 style={{
 background: !o.dossie ? 'var(--surface)' : 'var(--success)',
 color: !o.dossie ? 'var(--text-muted)' : '#fff',
 border: `1px solid ${!o.dossie ? 'var(--border)' : 'var(--success)'}`,
 borderRadius: 6, padding: '8px 14px',
 cursor: !o.dossie ? 'not-allowed' : (busy[o.id] ? 'wait' : 'pointer'),
 fontSize: 12, fontWeight: 700, whiteSpace: 'nowrap',
 opacity: busy[o.id] === 'baixar' ? 0.6 : 1,
 }}>
 {busy[o.id] === 'baixar' ? (<><IconHourglass size={12} /> Baixando…</>) : 'BAIXAR DOSSIÊ'}
 </button>
 </div>
 </div>
 )
 })}
 </div>
 )}
 </div>
 )
}

function SecurityPanel() {
 const [data, setData] = useState(null)
 const [loading, setLoad] = useState(true)
 const [err, setErr] = useState(null)

 async function check() {
 setLoad(true); setErr(null)
 try { setData(await api.get('/admin/security-check')) }
 catch (e) { setErr(e.message || 'Erro') }
 finally { setLoad(false) }
 }

 useEffect(() => { check() }, [])

 const statusColor = (s) => ({
 'ok-blocked': 'var(--success)', 'ok-empty': 'var(--success)',
 'leak': 'var(--error)', 'n/a': 'var(--text-muted)',
 'error': 'var(--warning)', 'unknown': 'var(--text-muted)',
 }[s] || 'var(--text-muted)')

 const statusLabel = (s) => ({
 'ok-blocked': '✓ Bloqueado', 'ok-empty': '✓ Protegido',
 'leak': ' VAZAMENTO', 'n/a': '—', 'error': ' Erro', 'unknown': '—',
 }[s] || s)

 const leaks = (data?.tables || []).filter(t => t.status === 'leak')

 return (
 <div className="card">
 <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 20 }}>
 <div>
 <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 4 }}> Painel de Segurança</h2>
 <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>
 Diagnóstico em tempo real das camadas de proteção: RLS, CORS, origens permitidas.
 </p>
 </div>
 <button className="btn btn-ghost" onClick={check} disabled={loading}>
 {loading ? 'Checando…' : 'Reverificar'}
 </button>
 </div>

 {err && <div style={{ padding: 12, background: 'var(--error-bg)', color: 'var(--error)', fontSize: 13, marginBottom: 16 }}>{err}</div>}

 {leaks.length > 0 && (
 <div style={{
 padding: 16, background: 'var(--error-bg)', border: '2px solid var(--error)',
 color: 'var(--error)', fontSize: 13, marginBottom: 20,
 }}>
 <strong style={{ fontSize: 14 }}> ATENÇÃO — {leaks.length} tabela(s) vazando dados para anônimos!</strong>
 </div>
 )}

 {data && (
 <>
 <div style={{ marginBottom: 24 }}>
 <h3 style={{ fontSize: 12, fontWeight: 700, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 10 }}>
 CORS — origens permitidas
 </h3>
 <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
 {(data.allowed_origins || []).map(o => (
 <div key={o} style={{ padding: '8px 12px', border: '1px solid var(--border)', fontFamily: 'monospace', fontSize: 12 }}>
 <span style={{ color: 'var(--success)' }}>✓</span> {o}
 </div>
 ))}
 </div>
 </div>

 <div>
 <h3 style={{ fontSize: 12, fontWeight: 700, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 10 }}>
 RLS — Row Level Security das tabelas
 </h3>
 <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
 <thead>
 <tr style={{ borderBottom: '1px solid var(--border)' }}>
 <th style={{ padding: '10px', textAlign: 'left', color: 'var(--text-muted)', fontWeight: 600, fontSize: 11, textTransform: 'uppercase' }}>Tabela</th>
 <th style={{ padding: '10px', textAlign: 'left', color: 'var(--text-muted)', fontWeight: 600, fontSize: 11, textTransform: 'uppercase' }}>Status</th>
 <th style={{ padding: '10px', textAlign: 'left', color: 'var(--text-muted)', fontWeight: 600, fontSize: 11, textTransform: 'uppercase' }}>Detalhes</th>
 </tr>
 </thead>
 <tbody>
 {data.tables.map(t => (
 <tr key={t.table} style={{ borderBottom: '1px solid var(--border)' }}>
 <td style={{ padding: '10px', fontFamily: 'monospace', fontWeight: 600 }}>{t.table}</td>
 <td style={{ padding: '10px', color: statusColor(t.status), fontWeight: 700 }}>{statusLabel(t.status)}</td>
 <td style={{ padding: '10px', fontSize: 12, color: 'var(--text-muted)' }}>{t.message}</td>
 </tr>
 ))}
 </tbody>
 </table>
 </div>
 </>
 )}
 </div>
 )
}

// ═══════════════════════════════════════════════════════════════════
// PAINEL DE ANALÍTICOS (admin)
// Visão consolidada da plataforma: usuários, receita, ofertas e a
// economia gerada pela assinatura PRO. Auto-refresh a cada 15s.
// ═══════════════════════════════════════════════════════════════════
function AnaliticosPanel({ resumo, extras, reloadingExtras, reloadExtras }) {
  const u  = extras?.usuarios || {}
  const r  = extras?.receita  || {}
  const a  = extras?.assinatura || {}
  const o  = extras?.ofertas  || {}
  const lt = extras?.licenciamento_terceiros || {}
  const ob = extras?.obras?.por_status || {}
  const papel = u.por_papel || {}

  const atualizadoEm = extras?.atualizado_em
    ? new Date(extras.atualizado_em).toLocaleTimeString('pt-BR', {
        hour: '2-digit', minute: '2-digit', second: '2-digit',
      })
    : '—'

  return (
    <div style={{ padding: '32px 20px', maxWidth: 1200, margin: '0 auto' }}>
      {/* Topo: hora da última atualização + botão manual */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        marginBottom: 16, flexWrap: 'wrap', gap: 8,
      }}>
        <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
          Atualização automática a cada 15s · última leitura: <strong style={{ color: 'var(--text-primary)' }}>{atualizadoEm}</strong>
          {reloadingExtras && <span style={{ marginLeft: 8, color: 'var(--brand)' }}>atualizando…</span>}
        </div>
        <button className="btn-secondary" onClick={reloadExtras} disabled={reloadingExtras}
          style={{ fontSize: 12, padding: '6px 14px' }}>
          {reloadingExtras ? 'Atualizando…' : '↻ Atualizar agora'}
        </button>
      </div>

      {/* Linha 1 — Receita destaque */}
      <div className="card" style={{
        background: 'linear-gradient(135deg, #083257, #09090B)', border: 'none',
        color: '#fff', marginBottom: 16, boxShadow: '0 8px 32px rgba(12,68,124,.25)',
      }}>
        <h2 style={{ fontSize: 14, fontWeight: 600, color: 'rgba(255,255,255,.7)',
          marginBottom: 12, textTransform: 'uppercase', letterSpacing: 1 }}>
          Receita total da plataforma
        </h2>
        <div style={{ fontSize: 42, fontWeight: 800, color: '#fff', marginBottom: 6 }}>
          {fmt(resumo.receita_bruta_cents)}
        </div>
        <div style={{ display: 'flex', gap: 24, marginTop: 16, flexWrap: 'wrap' }}>
          <div>
            <div style={{ fontSize: 11, color: 'rgba(255,255,255,.5)' }}>RETIDO PELA PLATAFORMA</div>
            <div style={{ fontSize: 22, fontWeight: 700, color: '#34D399', marginTop: 4 }}>
              {fmt(resumo.receita_plataforma_cents)}
            </div>
          </div>
          <div>
            <div style={{ fontSize: 11, color: 'rgba(255,255,255,.5)' }}>PAGO AOS COMPOSITORES</div>
            <div style={{ fontSize: 22, fontWeight: 700, color: '#fff', marginTop: 4 }}>
              {fmt(resumo.receita_compositores_cents)}
            </div>
          </div>
          <div>
            <div style={{ fontSize: 11, color: 'rgba(255,255,255,.5)' }}>ÚLTIMOS 30 DIAS</div>
            <div style={{ fontSize: 22, fontWeight: 700, color: '#fff', marginTop: 4 }}>
              {fmt(r.ultimos_30d_cents || 0)}
            </div>
          </div>
          <div>
            <div style={{ fontSize: 11, color: 'rgba(255,255,255,.5)' }}>ÚLTIMOS 7 DIAS</div>
            <div style={{ fontSize: 22, fontWeight: 700, color: '#fff', marginTop: 4 }}>
              {fmt(r.ultimos_7d_cents || 0)}
            </div>
          </div>
          <div>
            <div style={{ fontSize: 11, color: 'rgba(255,255,255,.5)' }}>TICKET MÉDIO</div>
            <div style={{ fontSize: 22, fontWeight: 700, color: '#fff', marginTop: 4 }}>
              {fmt(r.ticket_medio_cents || 0)}
            </div>
          </div>
        </div>
      </div>

      {/* Linha 2 — Economia gerada pela assinatura PRO */}
      <div className="card" style={{
        background: 'linear-gradient(135deg, #16653f, #022c22)',
        border: 'none', color: '#fff', marginBottom: 16,
        boxShadow: '0 8px 32px rgba(16,185,129,.25)',
      }}>
        <h2 style={{ fontSize: 14, fontWeight: 600, color: 'rgba(255,255,255,.75)',
          marginBottom: 12, textTransform: 'uppercase', letterSpacing: 1 }}>
          Economia acumulada dos assinantes PRO
        </h2>
        <div style={{ fontSize: 38, fontWeight: 800, color: '#fff', marginBottom: 4 }}>
          {fmt(a.economia_total_cents || 0)}
        </div>
        <div style={{ fontSize: 12, color: 'rgba(255,255,255,.7)', marginBottom: 14 }}>
          Volume de vendas gerado por usuários PRO na plataforma.
        </div>
        <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap' }}>
          <div>
            <div style={{ fontSize: 11, color: 'rgba(255,255,255,.55)' }}>NOS ÚLTIMOS 30 DIAS</div>
            <div style={{ fontSize: 20, fontWeight: 700, color: '#A7F3D0', marginTop: 4 }}>
              {fmt(a.economia_30d_cents || 0)}
            </div>
          </div>
          <div>
            <div style={{ fontSize: 11, color: 'rgba(255,255,255,.55)' }}>ASSINANTES PRO ATIVOS</div>
            <div style={{ fontSize: 20, fontWeight: 700, color: '#fff', marginTop: 4 }}>
              {a.pro_ativos || 0}
              {a.pro_past_due ? <span style={{ fontSize: 12, color: '#FCA5A5', marginLeft: 8 }}>+{a.pro_past_due} em atraso</span> : null}
            </div>
          </div>
          <div>
            <div style={{ fontSize: 11, color: 'rgba(255,255,255,.55)' }}>RECEITA MENSAL DE ASSINATURA (estim.)</div>
            <div style={{ fontSize: 20, fontWeight: 700, color: '#fff', marginTop: 4 }}>
              {fmt(a.receita_mensal_cents || 0)}
            </div>
          </div>
        </div>
      </div>

      {/* Linha 3 — Stat cards principais */}
      <div style={{
        display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
        gap: 14, marginBottom: 16,
      }}>
        <StatCard label="Composições cadastradas" value={resumo.total_obras}
          sublabel={`${resumo.obras_publicadas} publicadas`} big color="var(--brand)" />
        <StatCard label="Vendas confirmadas" value={r.transacoes_total ?? resumo.total_vendas}
          sublabel={`${r.transacoes_30d || 0} em 30 dias`} big color="var(--success)" />
        <StatCard label="Pago aos artistas (saques)" value={fmt(r.pago_artistas_cents || 0)}
          sublabel="Saques liquidados" />
        <StatCard label="Ofertas em aberto" value={o.pendentes ?? resumo.ofertas_pendentes}
          color="var(--warning)" sublabel={`${o.total || 0} no total`} />
      </div>

      {/* Linha 4 — Painel de Usuários */}
      <div className="card" style={{ marginBottom: 16 }}>
        <h3 style={{ fontSize: 13, fontWeight: 700, marginBottom: 12,
          textTransform: 'uppercase', letterSpacing: 1, color: 'var(--text-secondary)' }}>
          Usuários da plataforma
        </h3>
        <div style={{
          display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: 12,
        }}>
          <StatCard label="Total de usuários" value={u.total ?? resumo.total_usuarios}
            sublabel={`+${u.novos_30d || 0} em 30 dias`} big color="var(--brand)" />
          <StatCard label="Compositores" value={papel.compositor || 0} />
          <StatCard label="Intérpretes" value={papel.interprete || 0} />
          <StatCard label="Editoras" value={papel.publisher || 0} />
          <StatCard label="Agregadores" value={papel.agregador || 0} />
          <StatCard label="Administradores" value={papel.administrador || 0} />
          <StatCard label="Assinantes PRO" value={a.pro_ativos || 0}
            sublabel={`${a.pro_past_due || 0} em atraso`} color="var(--success)" />
          <StatCard label="Plano STARTER" value={u.starter || 0} />
          <StatCard label="Novos (7 dias)" value={u.novos_7d || 0} color="var(--brand)" />
        </div>
      </div>

      {/* Linha 5 — Ofertas (catálogo) */}
      <div className="card" style={{ marginBottom: 16 }}>
        <h3 style={{ fontSize: 13, fontWeight: 700, marginBottom: 4,
          textTransform: 'uppercase', letterSpacing: 1, color: 'var(--text-secondary)' }}>
          Ofertas de catálogo (intérpretes → compositores)
        </h3>
        <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginBottom: 12 }}>
          Total negociado (aceitas + pagas): <strong style={{ color: 'var(--success)' }}>{fmt(o.total_negociado_cents || 0)}</strong>
          {' · '}Ticket médio: <strong>{fmt(o.ticket_medio_cents || 0)}</strong>
          {' · '}Taxa de aceite: <strong>{o.taxa_aceite_pct || 0}%</strong>
        </div>
        <div style={{
          display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: 12,
        }}>
          <StatCard label="Total de ofertas" value={o.total || 0} big />
          <StatCard label="Pendentes" value={o.pendentes || 0} color="var(--warning)" />
          <StatCard label="Aceitas (em negoc.)" value={(o.aceitas || 0) - (o.pagas || 0)} color="#0891b2" />
          <StatCard label="Pagas (concluídas)" value={o.pagas || 0} color="var(--success)" />
          <StatCard label="Recusadas" value={o.recusadas || 0} color="var(--danger)" />
          <StatCard label="Canceladas/expiradas" value={o.canceladas || 0} />
          <StatCard label="Exclusividade" value={o.exclusividade || 0} color="var(--brand)" />
        </div>
      </div>

      {/* Linha 6 — Licenciamento de terceiros + obras por status */}
      <div style={{
        display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 14,
      }}>
        <div className="card">
          <h3 style={{ fontSize: 13, fontWeight: 700, marginBottom: 12,
            textTransform: 'uppercase', letterSpacing: 1, color: 'var(--text-secondary)' }}>
            Licenciamento por terceiros (editoras)
          </h3>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10 }}>
            <StatCard label="Total" value={lt.total || 0} />
            <StatCard label="Em andamento" value={lt.em_andamento || 0} color="var(--warning)" />
            <StatCard label="Concluídas" value={lt.concluidas || 0} color="var(--success)" />
          </div>
        </div>
        <div className="card">
          <h3 style={{ fontSize: 13, fontWeight: 700, marginBottom: 12,
            textTransform: 'uppercase', letterSpacing: 1, color: 'var(--text-secondary)' }}>
            Obras por status
          </h3>
          {Object.keys(ob).length === 0 ? (
            <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>Nenhum dado disponível.</div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {Object.entries(ob).sort((a,b) => b[1]-a[1]).map(([st, qtd]) => (
                <div key={st} style={{
                  display: 'flex', justifyContent: 'space-between',
                  padding: '8px 12px', background: 'var(--bg-elevated)',
                  borderRadius: 6, fontSize: 13,
                }}>
                  <span style={{ textTransform: 'capitalize' }}>{st.replace(/_/g, ' ')}</span>
                  <strong>{qtd}</strong>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════
// PAINEL DE CONTRATOS (admin)
// Lista TODOS os contratos da plataforma (licenciamento + edição) com
// botão de atualização manual. "Em vigor" = concluído ou assinado.
// ═══════════════════════════════════════════════════════════════════
function ContratosPanel() {
 const [data, setData] = useState(null)
 const [loading, setLoading] = useState(true)
 const [erro, setErro] = useState('')
 const [filtro, setFiltro] = useState('em_vigor')   // em_vigor | pendente | todos
 const [busca, setBusca] = useState('')
 const [reconciliando, setReconciliando] = useState(false)
 const [resultadoReconc, setResultadoReconc] = useState(null)

 async function load() {
  setLoading(true); setErro('')
  try {
   const r = await api.get('/admin/contratos')
   setData(r)
  } catch (e) { setErro(e.message) }
  finally { setLoading(false) }
 }
 useEffect(() => { load() }, [])

 async function reconciliar() {
  const ok = window.confirm(
   'Isto vai varrer todas as obras vinculadas a uma editora e gerar o ' +
   'contrato de edição para as que ainda não têm. As editoras serão ' +
   'notificadas. Deseja continuar?'
  )
  if (!ok) return
  setReconciliando(true); setResultadoReconc(null); setErro('')
  try {
   const r = await api.post('/admin/contratos-edicao/reconciliar', { notificar: true })
   setResultadoReconc(r)
   await load()
  } catch (e) { setErro(e.message) }
  finally { setReconciliando(false) }
 }

 function statusBadge(tipo, st) {
  // Mapa de cores por status (compartilhado entre licenciamento e edição)
  const map = {
   concluido:        { bg: 'var(--success-bg)', cor: 'var(--success)', label: '✓ Em vigor' },
   'concluído':      { bg: 'var(--success-bg)', cor: 'var(--success)', label: '✓ Em vigor' },
   assinado:         { bg: 'var(--success-bg)', cor: 'var(--success)', label: '✓ Em vigor' },
   assinado_parcial: { bg: '#E8F4FD', cor: '#0C5494',         label: '◐ Parcialmente assinado' },
   pendente:         { bg: 'var(--warning-bg)', cor: 'var(--warning)', label: '⏱ Pendente' },
   cancelado:        { bg: 'var(--error-bg)', cor: 'var(--error)',     label: '✕ Cancelado' },
  }
  const m = map[st] || { bg: 'var(--surface-2)', cor: 'var(--text-muted)', label: st || '—' }
  return (
   <span style={{
    fontSize: 11, fontWeight: 700, padding: '2px 8px',
    background: m.bg, color: m.cor, borderRadius: 99,
   }}>{m.label}</span>
  )
 }

 const itens = (data?.itens || [])
 const filtrados = itens.filter(c => {
  // Filtro de status
  if (filtro === 'em_vigor') {
   const ok = (c.tipo === 'licenciamento' && (c.status === 'concluido' || c.status === 'concluído'))
           || (c.tipo === 'edicao' && c.status === 'assinado')
   if (!ok) return false
  } else if (filtro === 'pendente') {
   if (!['pendente', 'assinado_parcial', 'assinado'].includes(c.status)) return false
   // No licenciamento, "assinado" é parcial; no edicao, "assinado" é final.
   if (c.tipo === 'edicao' && c.status === 'assinado') return false
  }
  // Busca textual
  if (busca.trim()) {
   const q = busca.trim().toLowerCase()
   const blob = [
    c.id, c.obra_nome, c.obra_id,
    c.vendedor?.nome, c.comprador?.nome,
    c.autor?.nome, c.editora?.nome,
   ].filter(Boolean).join(' ').toLowerCase()
   if (!blob.includes(q)) return false
  }
  return true
 })

 return (
  <div className="card">
   <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14, flexWrap: 'wrap', gap: 12 }}>
    <div>
     <h2 style={{ fontSize: 15, fontWeight: 700 }}>Contratos da plataforma</h2>
     <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>
      {data
       ? <>Total: <strong>{data.total}</strong> · em vigor: <strong style={{ color: 'var(--success)' }}>{data.em_vigor}</strong> · pendentes: <strong style={{ color: 'var(--warning)' }}>{data.pendentes}</strong></>
       : 'Carregando…'}
     </p>
    </div>
    <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
     <button onClick={reconciliar} disabled={reconciliando}
      title="Gera contratos de edição faltantes para obras que estão vinculadas a uma editora mas ficaram sem contrato (por exemplo, por falha temporária no cadastro)."
      style={{ background: 'var(--brand)', border: '1px solid var(--brand)', padding: '6px 12px', borderRadius: 8, color: '#fff', fontSize: 13, cursor: reconciliando ? 'wait' : 'pointer', fontWeight: 600 }}>
      {reconciliando ? 'reconciliando…' : 'Reconciliar contratos pendentes'}
     </button>
     <button onClick={load} disabled={loading}
      style={{ background: 'none', border: '1px solid var(--border)', padding: '6px 12px', borderRadius: 8, color: 'var(--brand)', fontSize: 13, cursor: loading ? 'wait' : 'pointer' }}>
      ↻ {loading ? 'atualizando…' : 'atualizar agora'}
     </button>
    </div>
   </div>

   {resultadoReconc && (
    <div style={{
     marginBottom: 12, padding: '10px 14px',
     background: resultadoReconc.contratos_criados > 0 ? 'var(--success-bg)' : 'var(--surface-2)',
     border: '1px solid ' + (resultadoReconc.contratos_criados > 0 ? 'var(--success)' : 'var(--border)'),
     color: 'var(--text-primary)',
     borderRadius: 10, fontSize: 13,
    }}>
     <strong>Reconciliação concluída.</strong>{' '}
     Obras analisadas: <strong>{resultadoReconc.obras_analisadas}</strong> ·
     Já tinham contrato: <strong>{resultadoReconc.ja_tinham_contrato}</strong> ·
     Contratos criados agora: <strong style={{ color: 'var(--success)' }}>{resultadoReconc.contratos_criados}</strong>
     {resultadoReconc.erros?.length > 0 && (
      <> · <span style={{ color: 'var(--error)' }}>Erros: {resultadoReconc.erros.length}</span></>
     )}
    </div>
   )}

   {/* Filtros rápidos */}
   <div style={{ display: 'flex', gap: 6, marginBottom: 12, flexWrap: 'wrap' }}>
    {[
     { id: 'em_vigor', label: 'Em vigor' },
     { id: 'pendente', label: 'Pendentes' },
     { id: 'todos',    label: 'Todos' },
    ].map(b => (
     <button key={b.id} onClick={() => setFiltro(b.id)}
      style={{
       padding: '6px 12px', borderRadius: 99, fontSize: 12, fontWeight: 600,
       cursor: 'pointer',
       background: filtro === b.id ? 'var(--brand)' : 'transparent',
       color:      filtro === b.id ? '#fff' : 'var(--text-secondary)',
       border:     filtro === b.id ? '1px solid var(--brand)' : '1px solid var(--border)',
      }}>{b.label}</button>
    ))}
    <input
     type="search" value={busca} onChange={e => setBusca(e.target.value)}
     placeholder="Buscar por obra, parte, ID…"
     className="input"
     style={{ flex: '1 1 240px', minWidth: 200, fontSize: 13, padding: '6px 12px' }}
    />
   </div>

   {erro && <p style={{ color: 'var(--error)', fontSize: 13 }}>{erro}</p>}
   {loading && !data && <p style={{ color: 'var(--text-muted)', fontSize: 13 }}>Carregando contratos…</p>}

   {!loading && filtrados.length === 0 && (
    <div style={{
     padding: 36, textAlign: 'center', color: 'var(--text-muted)',
     border: '1px dashed var(--border)', borderRadius: 10, fontSize: 13,
    }}>
     {itens.length === 0
      ? 'Nenhum contrato cadastrado na plataforma ainda.'
      : 'Nenhum contrato encontrado com esses filtros.'}
    </div>
   )}

   {filtrados.length > 0 && (
    <div style={{ overflowX: 'auto' }}>
     <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
      <thead>
       <tr style={{ borderBottom: '1px solid var(--border)' }}>
        {['Tipo', 'Obra', 'Partes', 'Valor / Split', 'Status', 'Data', 'Ações'].map(h => (
         <th key={h} style={{ padding: '10px', textAlign: 'left', color: 'var(--text-muted)', fontWeight: 600, fontSize: 11, textTransform: 'uppercase', letterSpacing: 1, whiteSpace: 'nowrap' }}>{h}</th>
        ))}
       </tr>
      </thead>
      <tbody>
       {filtrados.map(c => (
        <tr key={c.id} style={{ borderBottom: '1px solid var(--border)' }}>
         <td style={{ padding: '10px' }}>
          <span style={{
           fontSize: 10, fontWeight: 700, padding: '2px 8px',
           background: c.tipo === 'licenciamento' ? 'var(--brand-light)' : '#FEF3C7',
           color:      c.tipo === 'licenciamento' ? 'var(--brand)'       : '#92400E',
           borderRadius: 4, textTransform: 'uppercase', letterSpacing: 1,
          }}>{c.tipo === 'licenciamento' ? 'Licenc.' : 'Edição'}</span>
          {c.trilateral && (
           <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 2 }}>trilateral</div>
          )}
         </td>
         <td style={{ padding: '10px' }}>
          <div style={{ fontWeight: 600 }}>{c.obra_nome || '(sem nome)'}</div>
          <code style={{ fontSize: 10, color: 'var(--text-muted)', fontFamily: 'monospace' }}>
           {(c.id || '').slice(0, 8)}
          </code>
         </td>
         <td style={{ padding: '10px', fontSize: 12, lineHeight: 1.5 }}>
          {c.tipo === 'licenciamento' ? (
           <>
            <div><strong>Vendedor:</strong> {c.vendedor?.nome || '—'}</div>
            <div><strong>Comprador:</strong> {c.comprador?.nome || '—'}</div>
           </>
          ) : (
           <>
            <div>
             <strong>Autor:</strong> {c.autor?.nome || '—'}
             {c.autor?.assinou && <span style={{ marginLeft: 6, color: 'var(--success)' }}>✓</span>}
            </div>
            <div>
             <strong>Editora:</strong> {c.editora?.nome || '—'}
             {c.editora?.assinou && <span style={{ marginLeft: 6, color: 'var(--success)' }}>✓</span>}
            </div>
           </>
          )}
         </td>
         <td style={{ padding: '10px', whiteSpace: 'nowrap', fontWeight: 700 }}>
          {c.tipo === 'licenciamento'
           ? <span style={{ color: 'var(--brand)' }}>{fmt(c.valor_cents)}</span>
           : <span>{c.share_pct != null ? `${Number(c.share_pct).toFixed(0)}%` : '—'}</span>}
         </td>
         <td style={{ padding: '10px' }}>{statusBadge(c.tipo, c.status)}</td>
         <td style={{ padding: '10px', whiteSpace: 'nowrap', color: 'var(--text-secondary)', fontSize: 12 }}>
          {c.created_at ? new Date(c.created_at).toLocaleDateString('pt-BR') : '—'}
         </td>
         <td style={{ padding: '10px' }}>
          {c.tipo === 'licenciamento' && (
           <Link to={`/contratos/licenciamento/${c.id}`}
              style={{ color: 'var(--brand)', fontSize: 12, fontWeight: 600, textDecoration: 'none' }}>
            ver →
           </Link>
          )}
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
