import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { usePlayer } from '../contexts/PlayerContext'
import { api } from '../lib/api'
import { IconPlay } from '../components/Icons'

function fmt(cents) {
 return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format((cents ?? 0) / 100)
}

/* ── Status das obras ────────────────────────────────────── */
const STATUS_STYLE = {
 publicada: { bg: 'rgba(34,197,94,.12)', cor: '#22c55e', label: '✓ Publicada' },
 rascunho: { bg: 'rgba(245,158,11,.12)', cor: '#f59e0b', label: 'Rascunho' },
 arquivada: { bg: 'rgba(255,255,255,.06)', cor: 'rgba(255,255,255,.4)', label: 'Arquivada' },
}

/* ── Componente StatCard ─────────────────────────────────── */
function StatCard({ label, value, sub, accent = false }) {
 return (
 <div style={{
 padding: '18px 20px',
 background: accent ? 'rgba(12,68,124,.18)' : 'var(--surface)',
 border: `1px solid ${accent ? 'rgba(12,68,124,.4)' : 'var(--border)'}`,
 borderRadius: 14,
 }}>
 <div style={{
 fontSize: 11, fontWeight: 700, color: 'var(--text-muted)',
 textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 8,
 }}>
 {label}
 </div>
 <div style={{
 fontSize: 28, fontWeight: 900, color: accent ? 'var(--brand)' : 'var(--text-primary)',
 lineHeight: 1, marginBottom: 6, letterSpacing: '-1px',
 }}>
 {value}
 </div>
 {sub && (
 <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{sub}</div>
 )}
 </div>
 )
}

export default function Dashboard() {
 const { perfil } = useAuth()
 const navigate = useNavigate()
 const { playObra } = usePlayer()
 const [data, setData] = useState(null)
 const [loading, setLoading] = useState(true)
 const [error, setError] = useState(null)
 const [lastUpdate, setLastUpdate] = useState(Date.now())

 async function load(silent = false) {
 if (!silent) { setLoading(true); setError(null) }
 try {
 const d = await api.get('/perfis/me/dashboard')
 setData(d)
 setLastUpdate(Date.now())
 setError(null)
 } catch (e) {
 console.error('Erro dashboard:', e)
 setError(e?.message || 'Erro ao carregar dashboard')
 } finally { setLoading(false) }
 }

 useEffect(() => {
 load()
 const interval = setInterval(() => load(true), 10_000)
 return () => clearInterval(interval)
 }, [])

 if (error && !data) {
 return (
 <div style={{ padding: 40, maxWidth: 560 }}>
 <div style={{
 padding: 24, border: '1px solid var(--border)', background: 'var(--surface)',
 }}>
 <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--error)', letterSpacing: '0.12em', marginBottom: 8, textTransform: 'uppercase' }}>
 Erro ao carregar
 </div>
 <h2 style={{ fontSize: 20, marginBottom: 8, fontFamily: "'Space Grotesk', sans-serif" }}>
 Não conseguimos carregar sua dashboard
 </h2>
 <p style={{ fontSize: 14, color: 'var(--text-muted)', marginBottom: 16 }}>
 {error}
 </p>
 <div style={{ display: 'flex', gap: 8 }}>
 <button onClick={() => load()} className="btn btn-primary" data-testid="dashboard-retry">
 Tentar novamente
 </button>
 <button onClick={() => navigate('/perfil/completar')} className="btn btn-ghost">
 Completar cadastro
 </button>
 </div>
 </div>
 </div>
 )
 }

 if (loading || !data) {
 return (
 <div style={{ padding: 40 }}>
 <div style={{
 display: 'flex', gap: 12, flexDirection: 'column',
 }}>
 {[1,2,3].map(i => (
 <div key={i} style={{
 height: 60, borderRadius: 0,
 background: 'var(--surface-2)',
 border: '1px solid var(--border)',
 animation: 'pulse 1.4s ease-in-out infinite',
 opacity: .8,
 }} />
 ))}
 </div>
 </div>
 )
 }

 const segundosDesde = Math.floor((Date.now() - lastUpdate) / 1000)

 return (
 <div style={{ padding: 32, maxWidth: 1100, minHeight: '100vh' }}>

 {/* ── Header ───────────────────────────── */}
 <div style={{
 display: 'flex', justifyContent: 'space-between',
 alignItems: 'flex-start', marginBottom: 24,
 flexWrap: 'wrap', gap: 12,
 }}>
 <div>
 <h1 style={{
 fontSize: 28, fontWeight: 900, color: 'var(--text-primary)',
 letterSpacing: '-1px', marginBottom: 4,
 }}>
 Dashboard
 </h1>
 <p style={{ color: 'var(--text-muted)', fontSize: 13 }}>
 Olá, <strong style={{ color: 'var(--text-secondary)' }}>
 {perfil?.nome_artistico || perfil?.nome}
 </strong>
 {' · '}atualizado {segundosDesde < 5 ? 'agora mesmo' : `há ${segundosDesde}s`}
 <button
 onClick={() => load()}
 style={{
 background: 'none', border: 'none',
 color: 'var(--brand)', cursor: 'pointer',
 marginLeft: 8, fontSize: 12, fontFamily: 'inherit',
 }}>
 ↻ atualizar
 </button>
 </p>
 </div>
 <button className="btn btn-primary" onClick={() => navigate('/obras/nova')}>
 + Nova obra
 </button>
 </div>

 {/* ── Stats grid ─────────────────────── */}
 <div style={{
 display: 'grid',
 gridTemplateColumns: 'repeat(auto-fit, minmax(190px, 1fr))',
 gap: 14, marginBottom: 28,
 }}>
 <StatCard
 label="Obras publicadas"
 value={data.obras_publicadas}
 sub={`de ${data.total_obras} cadastradas`}
 />
 <StatCard
 label="Vendas confirmadas"
 value={data.total_vendas}
 />
 <StatCard
 label="Saldo disponível"
 value={fmt(data.saldo_atual_cents)}
 sub="Pronto para saque"
 accent
 />
 <StatCard
 label="Receita total"
 value={fmt(data.receita_total_cents)}
 sub={`Já sacado: ${fmt(data.total_sacado_cents)}`}
 />
 </div>

 {/* ── Listagem de obras ───────────────── */}
 <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
 {/* Header da listagem */}
 <div style={{
 display: 'flex', justifyContent: 'space-between', alignItems: 'center',
 padding: '18px 22px',
 borderBottom: '1px solid var(--border)',
 }}>
 <h2 style={{ fontSize: 16, fontWeight: 800, color: 'var(--text-primary)' }}>
 Minhas obras ({data.obras.length})
 </h2>
 <button
 onClick={() => navigate('/obras')}
 style={{
 background: 'none', border: 'none',
 color: 'var(--brand)', fontSize: 13,
 cursor: 'pointer', fontWeight: 600, fontFamily: 'inherit',
 }}>
 Ver todas →
 </button>
 </div>

 {/* Lista */}
 {data.obras.length === 0 ? (
 <div style={{ padding: '56px 32px', textAlign: 'center' }}>
 <div style={{ fontSize: 48, opacity: .15, marginBottom: 12 }}></div>
 <p style={{ color: 'var(--text-muted)', marginBottom: 18, fontSize: 15 }}>
 Você ainda não cadastrou nenhuma obra.
 </p>
 <button className="btn btn-primary" onClick={() => navigate('/obras/nova')}>
 Cadastrar primeira obra
 </button>
 </div>
 ) : (
 <div style={{ padding: '10px 14px', display: 'flex', flexDirection: 'column', gap: 4 }}>
 {data.obras.slice(0, 8).map(obra => {
 const st = STATUS_STYLE[obra.status] ?? STATUS_STYLE.rascunho
 return (
 <div key={obra.id} style={{
 display: 'flex', alignItems: 'center', gap: 14,
 padding: '12px 10px',
 background: 'var(--surface-2)',
 borderRadius: 10,
 border: '1px solid transparent',
 transition: 'border-color .15s',
 cursor: 'default',
 }}
 onMouseEnter={e => e.currentTarget.style.borderColor = 'var(--border-2)'}
 onMouseLeave={e => e.currentTarget.style.borderColor = 'transparent'}
 >
 {/* Botão play */}
 {obra.audio_path && (
 <button
 onClick={() => playObra({
 id: obra.id,
 nome: obra.nome,
 audio_path: obra.audio_path,
 titular_nome: perfil?.nome_artistico || perfil?.nome,
 })}
 style={{
 width: 38, height: 38, borderRadius: 9,
 background: 'linear-gradient(135deg, #083257, #09090B)',
 color: '#fff', border: 'none', cursor: 'pointer',
 fontSize: 12, flexShrink: 0, fontFamily: 'inherit',
 boxShadow: '0 2px 12px rgba(12,68,124,.35)',
 transition: 'transform .1s',
 }}
 onMouseEnter={e => e.currentTarget.style.transform = 'scale(1.08)'}
 onMouseLeave={e => e.currentTarget.style.transform = 'scale(1)'}
 ><IconPlay size={14} /></button>
 )}

 {/* Info */}
 <div style={{ flex: 1, minWidth: 0 }}>
 <div style={{ fontWeight: 700, fontSize: 14, color: 'var(--text-primary)' }}>
 {obra.nome}
 {!obra.sou_titular && (
 <span style={{ fontSize: 11, color: 'var(--text-muted)', marginLeft: 8, fontWeight: 400 }}>
 (coautor)
 </span>
 )}
 </div>
 <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>
 {obra.genero || 'Sem gênero'} · {fmt(obra.preco_cents)}
 {' · '}cadastrada em {new Date(obra.created_at).toLocaleDateString('pt-BR')}
 </div>
 </div>

 {/* Status badge */}
 <span style={{
 fontSize: 11, fontWeight: 700,
 padding: '4px 10px', borderRadius: 99,
 background: st.bg, color: st.cor,
 whiteSpace: 'nowrap', flexShrink: 0,
 }}>
 {st.label}
 </span>
 </div>
 )
 })}

 {data.obras.length > 8 && (
 <button
 onClick={() => navigate('/obras')}
 style={{
 margin: '4px 0 8px', padding: 12,
 background: 'transparent',
 border: '1px dashed var(--border-2)',
 borderRadius: 10,
 color: 'var(--brand)', fontSize: 13,
 cursor: 'pointer', fontFamily: 'inherit',
 transition: 'border-color .15s, background .15s',
 }}>
 Ver todas as {data.obras.length} obras
 </button>
 )}
 </div>
 )}
 </div>
 </div>
 )
}
