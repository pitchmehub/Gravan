import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { usePlayer } from '../contexts/PlayerContext'
import { api } from '../lib/api'

const GENEROS = ['Sertanejo', 'MPB', 'Funk', 'Samba', 'Rock', 'Pop', 'Gospel', 'Forró', 'Pagode', 'Eletrônica']

function fmt(cents) {
 return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format((cents ?? 0) / 100)
}


export default function Catalogo() {
 const { perfil } = useAuth()
 const navigate = useNavigate()
 const { playObra, obra: obraAtual, playing, togglePlay } = usePlayer()

 const [obras, setObras] = useState([])
 const [loading, setLoading] = useState(true)
 const [busca, setBusca] = useState('')
 const [genero, setGenero] = useState('')
 const [page, setPage] = useState(1)
 const [hasMore, setHasMore] = useState(true)
 const [selected, setSelected] = useState(null)

 const perPage = 12

 useEffect(() => { fetchObras(1, true) }, [busca, genero])

 async function fetchObras(p = 1, reset = false) {
 setLoading(true)
 try {
 const params = new URLSearchParams({ page: p, per_page: perPage })
 if (busca) params.set('q', busca)
 if (genero) params.set('genero', genero)
 const data = await api.get(`/catalogo/?${params}`)
 setObras(prev => reset ? data : [...prev, ...data])
 setHasMore(data.length === perPage)
 setPage(p)
 } finally {
 setLoading(false)
 }
 }

 function loadMore() { fetchObras(page + 1) }

 function handlePlayCard(e, obra) {
 e.stopPropagation()
 if (!obra.audio_path) return
 // Se já é essa obra, toggle play/pause
 if (obraAtual?.id === obra.id) { togglePlay(); return }
 // Toca toda a lista a partir dessa obra
 const idx = obras.findIndex(o => o.id === obra.id)
 playObra(obras.filter(o => o.audio_path), Math.max(0, obras.filter(o => o.audio_path).findIndex(o => o.id === obra.id)))
 }

 return (
 <div style={{ padding: '32px 20px', maxWidth: 1100, margin: '0 auto' }}>
 <div style={{ marginBottom: 24 }}>
 <h1 style={{ fontSize: 22, fontWeight: 700 }}>Catálogo de Obras</h1>
 <p style={{ color: 'var(--text-muted)', fontSize: 14 }}>Explore composições disponíveis para licenciamento</p>
 </div>

 {/* Busca + Filtros */}
 <div style={{ display: 'flex', gap: 12, marginBottom: 24, flexWrap: 'wrap' }}>
 <input
 className="input" style={{ flex: 1, minWidth: 200 }}
 placeholder="Buscar por nome…" value={busca}
 onChange={e => { setBusca(e.target.value) }}
 />
 <select className="input" style={{ width: 180 }} value={genero} onChange={e => setGenero(e.target.value)}>
 <option value="">Todos os gêneros</option>
 {GENEROS.map(g => <option key={g} value={g}>{g}</option>)}
 </select>
 </div>

 {/* Grid */}
 <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 16, marginBottom: 24 }}>
 {obras.map(obra => {
 const isPlaying = obraAtual?.id === obra.id && playing
 const isActive = obraAtual?.id === obra.id

 return (
 <div
 key={obra.id}
 className="card"
 style={{
 cursor: 'pointer',
 border: isActive ? '2px solid var(--brand)' : '1px solid var(--border)',
 transition: 'box-shadow .15s',
 }}
 onClick={() => setSelected(obra)}
 onMouseEnter={e => e.currentTarget.style.boxShadow = 'var(--shadow-md)'}
 onMouseLeave={e => e.currentTarget.style.boxShadow = 'none'}
 >
 {/* Capa com botão de play */}
 <div style={{
 height: 80,
 background: isActive
 ? 'linear-gradient(135deg, #083257, #09090B)'
 : 'var(--brand-light)',
 borderRadius: 'var(--radius-md)',
 marginBottom: 12,
 display: 'flex', alignItems: 'center', justifyContent: 'center',
 position: 'relative',
 }}>
 <span style={{ fontSize: 28, fontWeight: 800, color: isActive ? '#fff' : 'var(--brand)', opacity: isActive ? .5 : .9 }}>
 {(obra.nome || '?').charAt(0).toUpperCase()}
 </span>
 {obra.audio_path && (
 <button
 onClick={e => handlePlayCard(e, obra)}
 style={{
 position: 'absolute',
 width: 40, height: 40,
 borderRadius: '50%',
 background: isActive ? '#fff' : 'var(--brand)',
 color: isActive ? 'var(--brand)' : '#fff',
 border: 'none', cursor: 'pointer',
 display: 'flex', alignItems: 'center', justifyContent: 'center',
 boxShadow: '0 4px 12px rgba(0,0,0,.2)',
 transition: 'transform .1s',
 }}
 title={isPlaying ? 'Pausar' : 'Tocar preview'}
 >
 {isPlaying
 ? <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="4" width="4" height="16" rx="1"/><rect x="14" y="4" width="4" height="16" rx="1"/></svg>
 : <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><polygon points="5,3 19,12 5,21"/></svg>}
 </button>
 )}
 </div>

 <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 2 }}>{obra.nome}</div>
 <div style={{ color: 'var(--text-muted)', fontSize: 12, marginBottom: 8 }}>
 {obra.titular_nome}
 {obra.genero && ` · ${obra.genero}`}
 </div>

 {obra.coautores?.length > 1 && (
 <div style={{ color: 'var(--text-muted)', fontSize: 11, marginBottom: 8 }}>
 feat. {obra.coautores.filter(c => !c.is_titular).map(c => c.nome).join(', ')}
 </div>
 )}

 <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
 <span style={{ fontWeight: 700, color: 'var(--brand)', fontSize: 15 }}>
 {fmt(obra.preco_cents)}
 </span>
 <span style={{ color: 'var(--text-muted)', fontSize: 11 }}>
 {obra.total_comentarios}
 </span>
 </div>
 </div>
 )
 })}
 </div>

 {loading && <p style={{ color: 'var(--text-muted)' }}>Carregando…</p>}
 {!loading && obras.length === 0 && <p style={{ color: 'var(--text-muted)' }}>Nenhuma obra encontrada.</p>}
 {hasMore && !loading && (
 <button className="btn btn-secondary" onClick={loadMore}>Carregar mais</button>
 )}

 {/* Modal de detalhe */}
 {selected && (
 <div
 style={{
 position: 'fixed', inset: 0, background: 'rgba(0,0,0,.55)',
 display: 'flex', alignItems: 'center', justifyContent: 'center',
 zIndex: 200, padding: 24,
 }}
 onClick={e => { if (e.target === e.currentTarget) setSelected(null) }}
 >
 <div className="card" style={{ width: '100%', maxWidth: 520, maxHeight: '80vh', overflowY: 'auto' }}>
 <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
 <h2 style={{ fontSize: 18, fontWeight: 700 }}>{selected.nome}</h2>
 <button className="btn btn-ghost btn-sm" onClick={() => setSelected(null)}>×</button>
 </div>

 <div style={{ color: 'var(--text-muted)', fontSize: 13, marginBottom: 12 }}>
 {selected.titular_nome}
 {selected.genero && ` · ${selected.genero}`}
 </div>

 {/* Coautores */}
 {selected.coautores?.length > 0 && (
 <div style={{ marginBottom: 16 }}>
 <div style={{ color: 'var(--text-muted)', fontSize: 12, marginBottom: 6 }}>Compositores</div>
 <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
 {selected.coautores.map(c => (
 <span key={c.perfil_id} style={{
 background: 'var(--brand-light)', color: 'var(--brand)',
 padding: '3px 10px', borderRadius: 99, fontSize: 12,
 }}>
 {c.nome} {c.is_titular ? '(titular)' : ''} · {c.share_pct}%
 </span>
 ))}
 </div>
 </div>
 )}

 {/* Botão de player */}
 {selected.audio_path && (
 <div style={{
 background: 'var(--surface-2)', borderRadius: 'var(--radius-md)',
 padding: '14px 16px', marginBottom: 16,
 display: 'flex', alignItems: 'center', gap: 14,
 }}>
 <button
 onClick={() => {
 if (obraAtual?.id === selected.id) { togglePlay() }
 else { playObra(selected) }
 }}
 className="btn btn-primary"
 style={{ borderRadius: '50%', width: 48, height: 48, padding: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 18, flexShrink: 0 }}
 >
 {obraAtual?.id === selected.id && playing
 ? <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="4" width="4" height="16" rx="1"/><rect x="14" y="4" width="4" height="16" rx="1"/></svg>
 : <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><polygon points="5,3 19,12 5,21"/></svg>}
 </button>
 <div>
 <div style={{ fontWeight: 600, fontSize: 14 }}>
 {obraAtual?.id === selected.id && playing ? 'Reproduzindo…' : 'Ouvir preview'}
 </div>
 <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
 Player aparece na parte inferior da tela
 </div>
 </div>
 </div>
 )}

 {/* Preço e ações */}
 <div style={{
 display: 'flex', justifyContent: 'space-between', alignItems: 'center',
 padding: '14px 0', borderTop: '1px solid var(--border)',
 }}>
 <span style={{ fontSize: 22, fontWeight: 700, color: 'var(--brand)' }}>
 {fmt(selected.preco_cents)}
 </span>
 <div style={{ display: 'flex', gap: 8 }}>
 <button
 className="btn btn-primary btn-sm"
 onClick={() => { setSelected(null); navigate(`/comprar/${selected.id}`) }}
 >
 Licenciar Composição
 </button>
 </div>
 </div>

 <ComentariosSection obraId={selected.id} perfilAtual={perfil} />
 </div>
 </div>
 )}

 </div>
 )
}

function ComentariosSection({ obraId, perfilAtual }) {
 const [comentarios, setComentarios] = useState([])
 const [novo, setNovo] = useState('')
 const [enviando, setEnviando] = useState(false)

 useEffect(() => {
 api.get(`/catalogo/${obraId}/comentarios`).then(setComentarios).catch(() => {})
 }, [obraId])

 async function enviar() {
 if (!novo.trim()) return
 setEnviando(true)
 try {
 const c = await api.post(`/catalogo/${obraId}/comentarios`, { conteudo: novo.trim() })
 setComentarios(prev => [c, ...prev])
 setNovo('')
 } catch (e) { alert(e.message) }
 finally { setEnviando(false) }
 }

 return (
 <div style={{ marginTop: 16, borderTop: '1px solid var(--border)', paddingTop: 14 }}>
 <div style={{ color: 'var(--text-muted)', fontSize: 12, marginBottom: 10 }}>
 {comentarios.length} comentário{comentarios.length !== 1 ? 's' : ''}
 </div>
 {perfilAtual && (
 <div style={{ display: 'flex', gap: 8, marginBottom: 14 }}>
 <textarea
 className="input" rows={2}
 placeholder="Escreva um comentário…"
 value={novo} onChange={e => setNovo(e.target.value)}
 style={{ flex: 1, minHeight: 'unset', resize: 'none' }}
 />
 <button className="btn btn-primary btn-sm" onClick={enviar} disabled={enviando || !novo.trim()}>
 {enviando ? '…' : 'Enviar'}
 </button>
 </div>
 )}
 <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
 {comentarios.map(c => (
 <div key={c.id} style={{ fontSize: 13, lineHeight: 1.5 }}>
 <span style={{ fontWeight: 600 }}>{c.perfis?.nome}</span>
 <p style={{ color: 'var(--text-secondary)', margin: '2px 0 0' }}>{c.conteudo}</p>
 </div>
 ))}
 </div>
 </div>
 )
}
