import React, { useEffect, useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { usePlayer } from '../contexts/PlayerContext'
import BotaoCurtir from '../components/BotaoCurtir'
import { supabase } from '../lib/supabase'
import { api } from '../lib/api'
import './Descoberta.css'
import NotificationBell from '../components/NotificationBell'
import ArtistaHero, { ObrasLista } from '../components/ArtistaHero'
import FichaTecnica from '../components/FichaTecnica'

function fmt(cents) {
 return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format((cents ?? 0) / 100)
}

const GENEROS = ['Todos', 'Sertanejo', 'MPB', 'Funk', 'Samba', 'Rock', 'Pop', 'Gospel', 'Forró', 'Pagode', 'RNB']
const GRADIENTS = [
 'linear-gradient(135deg,#083257,#09090B)',
 'linear-gradient(135deg,#0F6E56,#1D9E75)',
 'linear-gradient(135deg,#854F0B,#EF9F27)',
 'linear-gradient(135deg,#185FA5,#378ADD)',
 'linear-gradient(135deg,#993556,#D4537E)',
 'linear-gradient(135deg,#09090B,#3F3F46)',
]
const ObrgGrad = id => GRADIENTS[(id?.charCodeAt(0) ?? 0) % GRADIENTS.length]

function ObraCard({ obra, onPlay, onShowFicha, onExpand, isPlaying, isActive, onAddHistorico }) {
 function handleClick(e) {
 if (e.target.closest('.dc-card-play')) return
 if (e.target.closest('.dc-card-info-btn')) return
 // 1º clique: começa a tocar e abre o player minimizado.
 // 2º clique (mesma obra): abre a ficha técnica em vez de pausar.
 if (isActive) {
 onShowFicha(obra)
 return
 }
 onAddHistorico(obra.id)
 onPlay(obra)
 }

 return (
 <div className={`dc-card ${isActive ? 'dc-card-active' : ''}`} onClick={handleClick}>
 <div className="dc-card-cover" style={{ background: ObrgGrad(obra.id) }}>
 {obra.cover_url ? (
 <img
 src={obra.cover_url}
 alt=""
 loading="lazy"
 className="dc-card-cover-img"
 onError={e => { e.currentTarget.style.display = 'none' }}
 />
 ) : (
 <span className="dc-card-note"></span>
 )}
 {obra.audio_path && (
 <button
 className={`dc-card-play ${isActive ? 'dc-card-play-active' : ''}`}
 onClick={e => { e.stopPropagation(); onAddHistorico(obra.id); onPlay(obra) }}
 >
 {isPlaying ? '⏸' : '▶'}
 </button>
 )}
 </div>
 <div className="dc-card-info">
 <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 8 }}>
 <div style={{ minWidth: 0, flex: 1 }}>
 <div className="dc-card-nome">{obra.nome}</div>
 <div className="dc-card-autor">{obra.titular_nome}{obra.genero ? ` · ${obra.genero}` : ''}</div>
 </div>
 <div onClick={e => e.stopPropagation()}>
 <BotaoCurtir obraId={obra.id} size={16} />
 </div>
 </div>
 </div>
 </div>
 )
}

function CompositorCard({ compositor, onSelect, isAdmin, navigate }) {
 const iniciais = compositor.nome?.split(' ').slice(0, 2).map(n => n[0]).join('').toUpperCase()
 return (
 <div className="dc-comp-card" onClick={() => onSelect(compositor)}>
 <div className="dc-comp-avatar" style={{ background: ObrgGrad(compositor.id) }}>
 {compositor.avatar_url ? <img src={compositor.avatar_url} alt={compositor.nome} /> : iniciais}
 </div>
 <div className="dc-comp-nome">{compositor.nome_artistico || compositor.nome}</div>
 <div className="dc-comp-nivel">{compositor.nivel}</div>
 {isAdmin && (
 <button
 onClick={e => { e.stopPropagation(); navigate(`/perfil/${compositor.id}`) }}
 data-testid="busca-admin-btn"
 style={{
 marginTop: 8, fontSize: 11, fontWeight: 700, padding: '6px 10px',
 background: '#09090B', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer',
 }}>
 Visualizar como administrador
 </button>
 )}
 </div>
 )
}

function EditoraCard({ editora, isAdmin, navigate }) {
 const nome = editora.razao_social || editora.nome_artistico || editora.nome || '(sem nome)'
 const iniciais = (nome[0] || '?').toUpperCase()
 return (
 <div className="dc-comp-card" onClick={() => navigate(`/perfil/${editora.id}`)}>
 <div className="dc-comp-avatar" style={{ background: ObrgGrad(editora.id) }}>
 {editora.avatar_url ? <img src={editora.avatar_url} alt={nome} /> : iniciais}
 </div>
 <div className="dc-comp-nome"> {nome}</div>
 <div className="dc-comp-nivel">Editora</div>
 {isAdmin && (
 <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginTop: 8 }}>
 <button
 onClick={e => { e.stopPropagation(); navigate(`/perfil/${editora.id}`) }}
 data-testid="busca-admin-btn"
 style={{
 fontSize: 11, fontWeight: 700, padding: '6px 10px',
 background: '#09090B', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer',
 }}>
 Visualizar como administrador
 </button>
 <button
 onClick={e => { e.stopPropagation(); navigate(`/admin/editoras/${editora.id}`) }}
 style={{
 fontSize: 11, fontWeight: 700, padding: '6px 10px',
 background: '#fff', color: '#09090B', border: '1px solid #E5E7EB', borderRadius: 6, cursor: 'pointer',
 }}>
 Abrir dashboard da editora →
 </button>
 </div>
 )}
 </div>
 )
}

export default function Descoberta() {
 useEffect(() => {
 const prev = document.body.style.background
 document.body.style.background = '#FFFFFF'
 return () => { document.body.style.background = prev }
 }, [])

 const { perfil } = useAuth()
 const navigate = useNavigate()
 const { playObra, expandPlayer, setMinimized, obra: obraAtual, playing, togglePlay, nextTrack, prevTrack } = usePlayer()

 // Swipe esquerda/direita na tela → próxima/anterior
 const swipeStart = useRef(null)
 function handleRootTouchStart(e) {
 swipeStart.current = { x: e.touches[0].clientX, y: e.touches[0].clientY }
 }
 function handleRootTouchEnd(e) {
 if (!swipeStart.current || !obraAtual) return
 const dx = e.changedTouches[0].clientX - swipeStart.current.x
 const dy = e.changedTouches[0].clientY - swipeStart.current.y
 swipeStart.current = null
 if (Math.abs(dx) < 80 || Math.abs(dx) < Math.abs(dy) * 1.5) return
 if (dx < 0) nextTrack()
 else prevTrack()
 }

 const [aba, setAba] = useState('catalogo')
 const [generoFiltro, setGeneroFiltro] = useState('Todos')
 const [catalogo, setCatalogo] = useState([])
 const [biblioteca, setBiblioteca] = useState([])
 const [busca, setBusca] = useState('')
 const [resultados, setResultados] = useState({ obras: [], compositores: [], editoras: [] })
 const isAdmin = perfil?.role === 'administrador'
 const [compositor, setCompositor] = useState(null)
 const [obrasDoCom, setObrasDoCom] = useState([])
 const [loadCat, setLoadCat] = useState(true)
 const [loadBib, setLoadBib] = useState(false)
 const [buscando, setBuscando] = useState(false)
 const [fichaObra, setFichaObra] = useState(null)
 const buscaTimer = useRef(null)

 useEffect(() => {
 async function load() {
 setLoadCat(true)
 try {
 const params = new URLSearchParams({ page: 1, per_page: 40 })
 if (generoFiltro !== 'Todos') params.set('genero', generoFiltro)
 const data = await api.get(`/catalogo/?${params.toString()}`)
 setCatalogo(Array.isArray(data) ? data : [])
 } catch (e) {
 console.error('Erro ao carregar catálogo:', e)
 setCatalogo([])
 } finally { setLoadCat(false) }
 }
 load()
 }, [generoFiltro])

 useEffect(() => {
 if (aba !== 'biblioteca' || !perfil?.id) return
 async function load() {
 setLoadBib(true)
 try {
 const { data } = await supabase
 .from('historico_escuta')
 .select('obra_id, ouvido_em, obras(id, nome, genero, preco_cents, audio_path, status, titular_id, cover_url, perfis!titular_id(nome, nome_artistico, nivel))')
 .eq('perfil_id', perfil.id)
 .order('ouvido_em', { ascending: false })
 .limit(40)
 setBiblioteca((data ?? []).filter(h => h.obras).map(h => ({
 ...h.obras,
 titular_nome: h.obras?.perfis?.nome_artistico || h.obras?.perfis?.nome,
 titular_nivel: h.obras?.perfis?.nivel,
 })))
 } finally { setLoadBib(false) }
 }
 load()
 }, [aba, perfil?.id])

 async function addHistorico(obraId) {
 if (!perfil?.id) return
 try {
 await supabase.from('historico_escuta').upsert({
 perfil_id: perfil.id, obra_id: obraId, ouvido_em: new Date().toISOString(),
 }, { onConflict: 'perfil_id,obra_id' })
 } catch (_) {}
 }

 useEffect(() => {
 if (!busca.trim()) { setResultados({ obras: [], compositores: [], editoras: [] }); return }
 clearTimeout(buscaTimer.current)
 buscaTimer.current = setTimeout(async () => {
 setBuscando(true)
 try {
 const q = busca.trim()
 const [obras, comps, eds] = await Promise.all([
 api.get(`/catalogo/?q=${encodeURIComponent(q)}&per_page=12`).catch(() => []),
 supabase.from('perfis')
 .select('id, nome, nome_artistico, avatar_url, capa_url, nivel, role, bio')
 .eq('role', 'compositor')
 .or(`nome.ilike.%${q}%,nome_artistico.ilike.%${q}%`)
 .limit(8).then(r => r.data ?? []).catch(() => []),
 supabase.from('perfis')
 .select('id, nome, nome_artistico, razao_social, avatar_url, email')
 .eq('role', 'publisher')
 .or(`nome.ilike.%${q}%,nome_artistico.ilike.%${q}%,razao_social.ilike.%${q}%`)
 .limit(8).then(r => r.data ?? []).catch(() => []),
 ])
 setResultados({ obras: Array.isArray(obras) ? obras : [], compositores: comps, editoras: eds })
 } finally { setBuscando(false) }
 }, 300)
 return () => clearTimeout(buscaTimer.current)
 }, [busca])

 async function selecionarCompositor(comp) {
 if (!comp?.id) return
 navigate(`/perfil/${comp.id}`)
 }

 // Monta fila com todas as obras visíveis que têm áudio.
 // O embaralhamento agora é feito centralmente no PlayerContext via opts.shuffle.
 function buildQueue(clickedObra, listaCustom = null) {
 let lista
 if (listaCustom) {
 lista = listaCustom.filter(o => o.audio_path)
 } else if (busca && resultados.obras.length > 0) {
 lista = resultados.obras.filter(o => o.audio_path)
 } else if (aba === 'biblioteca') {
 lista = biblioteca.filter(o => o.audio_path)
 } else {
 lista = catalogo.filter(o => o.audio_path)
 }
 if (lista.length === 0) lista = [clickedObra]
 const idx = lista.findIndex(o => o.id === clickedObra.id)
 return { lista, idx: idx >= 0 ? idx : 0 }
 }

 function handlePlay(obra, listaCustom = null) {
 if (obraAtual?.id === obra.id) { togglePlay(); setMinimized(true); return }
 if (obra.audio_path) {
 api.post(`/analytics/play/${obra.id}`, {}).catch(() => {})
 }
 addHistorico(obra.id)
 const { lista, idx } = buildQueue(obra, listaCustom)
 playObra(lista, idx, { shuffle: true })
 setMinimized(true)
 }

 const cadastroIncompleto = perfil && !perfil.cadastro_completo

 function handleExpand(obra) {
 if (!obra.audio_path) return
 if (obraAtual?.id !== obra.id) {
 addHistorico(obra.id)
 const { lista, idx } = buildQueue(obra)
 playObra(lista, idx, { shuffle: true })
 }
 expandPlayer()
 }

 return (
 <div
 className="dc-root"
 onTouchStart={handleRootTouchStart}
 onTouchEnd={handleRootTouchEnd}
 >
 {cadastroIncompleto && (
 <div style={{
 padding: '14px 28px',
 background: 'linear-gradient(90deg,#083257,#09090B)',
 color: '#fff', display: 'flex', alignItems: 'center', gap: 14,
 flexWrap: 'wrap',
 }}>
 <span style={{ fontSize: 20 }}></span>
 <div style={{ flex: 1 }}>
 <div style={{ fontSize: 13, fontWeight: 700 }}>Complete seu cadastro</div>
 <div style={{ fontSize: 12, opacity: .9 }}>
 Preencha CPF, RG e endereço para liberar a publicação de obras e realizar compras.
 </div>
 </div>
 <button
 onClick={() => navigate('/perfil/completar')}
 style={{
 background: 'rgba(255,255,255,.2)', color: '#fff',
 border: '1px solid rgba(255,255,255,.3)', padding: '8px 16px', borderRadius: 99,
 fontSize: 13, fontWeight: 700, cursor: 'pointer',
 }}
 >
 Completar agora →
 </button>
 </div>
 )}
 <div className="dc-topbar">
 <div className="dc-topbar-row1">
 <div className="dc-tabs">
 <button className={`dc-tab ${aba === 'catalogo' ? 'dc-tab-active' : ''}`}
 onClick={() => { setAba('catalogo'); setCompositor(null); setBusca('') }}>
 <span className="dc-tab-icon"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="3" width="7" height="7" rx="1.2"/><rect x="14" y="3" width="7" height="7" rx="1.2"/><rect x="3" y="14" width="7" height="7" rx="1.2"/><rect x="14" y="14" width="7" height="7" rx="1.2"/></svg></span> Catálogo
 </button>
 <button className={`dc-tab ${aba === 'biblioteca' ? 'dc-tab-active' : ''}`}
 onClick={() => { setAba('biblioteca'); setCompositor(null); setBusca('') }}>
 <span className="dc-tab-icon"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><path d="M9 18V6l11-2v12"/><circle cx="6.5" cy="18" r="2.5"/><circle cx="17.5" cy="16" r="2.5"/></svg></span> Biblioteca
 </button>
 </div>
 <div className="dc-topbar-bell">
 <NotificationBell />
 </div>
 </div>
 <div className="dc-search-wrap">
 <span className="dc-search-icon">⌕</span>
 <input className="dc-search" placeholder="Buscar obras, compositores ou editoras…"
 value={busca} onChange={e => setBusca(e.target.value)} />
 {busca && <button className="dc-search-clear" onClick={() => { setBusca(''); setResultados({ obras: [], compositores: [], editoras: [] }) }}>×</button>}
 </div>
 </div>

 {busca && (
 <div className="dc-search-results">
 {buscando && <p className="dc-muted">Buscando…</p>}
 {!buscando && resultados.compositores.length > 0 && (
 <div className="dc-section">
 <h2 className="dc-section-title">Compositores</h2>
 <div className="dc-comp-grid">
 {resultados.compositores.map(c => (
 <CompositorCard key={c.id} compositor={c} onSelect={selecionarCompositor}
 isAdmin={isAdmin} navigate={navigate} />
 ))}
 </div>
 </div>
 )}
 {!buscando && resultados.editoras?.length > 0 && (
 <div className="dc-section">
 <h2 className="dc-section-title">Editoras</h2>
 <div className="dc-comp-grid">
 {resultados.editoras.map(e => (
 <EditoraCard key={e.id} editora={e} isAdmin={isAdmin} navigate={navigate} />
 ))}
 </div>
 </div>
 )}
 {!buscando && resultados.obras.length > 0 && (
 <div className="dc-section">
 <h2 className="dc-section-title">Obras</h2>
 <div className="dc-grid">
 {resultados.obras.map(o => (
 <ObraCard key={o.id} obra={o}
 isActive={obraAtual?.id === o.id}
 isPlaying={obraAtual?.id === o.id && playing}
 onPlay={handlePlay}
 onShowFicha={setFichaObra}
 onExpand={handleExpand}
 onAddHistorico={addHistorico} />
 ))}
 </div>
 </div>
 )}
 {!buscando && resultados.obras.length === 0 && resultados.compositores.length === 0 && (resultados.editoras?.length || 0) === 0 && (
 <p className="dc-muted">Nenhum resultado para "{busca}"</p>
 )}
 </div>
 )}

 {compositor && !busca && (
 <div style={{ background: '#fff' }}>
 <ArtistaHero
 perfil={{ ...compositor, role: compositor.role || 'compositor' }}
 totalObras={obrasDoCom.length}
 fallbackGrad={ObrgGrad(compositor.id)}
 onBack={() => setCompositor(null)}
 />
 <div style={{ padding: '20px 32px 40px' }}>
 <h2 style={{ fontSize: 22, fontWeight: 800, marginBottom: 16 }}>
 Composições
 </h2>
 <ObrasLista
 obras={obrasDoCom}
 getGrad={ObrgGrad}
 currentObraId={obraAtual?.id}
 isPlaying={playing}
 onPlay={o => handlePlay(o, obrasDoCom)}
 onShowFicha={setFichaObra}
 />
 </div>
 </div>
 )}

 {!busca && !compositor && (
 <>
 {aba === 'catalogo' && (
 <div className="dc-generos">
 {GENEROS.map(g => (
 <button key={g} className={`dc-genero-btn ${generoFiltro === g ? 'dc-genero-active' : ''}`}
 onClick={() => setGeneroFiltro(g)}>{g}</button>
 ))}
 </div>
 )}

 {aba === 'catalogo' && (
 <div className="dc-section">
 <h2 className="dc-section-title">{generoFiltro === 'Todos' ? 'Descobrir composições' : generoFiltro}</h2>
 {loadCat ? <SkeletonGrid /> : (
 <div className="dc-grid">
 {catalogo.map(o => (
 <ObraCard key={o.id} obra={o}
 isActive={obraAtual?.id === o.id}
 isPlaying={obraAtual?.id === o.id && playing}
 onPlay={handlePlay}
 onShowFicha={setFichaObra}
 onExpand={handleExpand}
 onAddHistorico={addHistorico} />
 ))}
 </div>
 )}
 {!loadCat && catalogo.length === 0 && (
 <div className="dc-empty">
 <div className="dc-empty-icon"></div>
 <div className="dc-empty-title">Nenhuma obra publicada</div>
 </div>
 )}
 </div>
 )}

 {aba === 'biblioteca' && (
 <div className="dc-section">
 <h2 className="dc-section-title">Ouvidas recentemente</h2>
 {loadBib ? <SkeletonGrid /> : biblioteca.length > 0 ? (
 <div className="dc-grid">
 {biblioteca.map(o => (
 <ObraCard key={o.id} obra={o}
 isActive={obraAtual?.id === o.id}
 isPlaying={obraAtual?.id === o.id && playing}
 onPlay={handlePlay}
 onShowFicha={setFichaObra}
 onExpand={handleExpand}
 onAddHistorico={addHistorico} />
 ))}
 </div>
 ) : (
 <div className="dc-empty">
 <div className="dc-empty-icon"></div>
 <div className="dc-empty-title">Sua biblioteca está vazia</div>
 <div className="dc-muted">Toque uma composição no catálogo para ela aparecer aqui.</div>
 <button className="dc-empty-btn" onClick={() => setAba('catalogo')}>Explorar catálogo</button>
 </div>
 )}
 </div>
 )}
 </>
 )}

 {fichaObra && (
 <FichaTecnica
 obra={fichaObra}
 onClose={() => setFichaObra(null)}
 onPlay={handlePlay}
 isPlaying={obraAtual?.id === fichaObra.id && playing}
 isActive={obraAtual?.id === fichaObra.id}
 />
 )}
 </div>
 )
}

function SkeletonGrid() {
 return (
 <div className="dc-grid">
 {Array.from({ length: 8 }).map((_, i) => <div key={i} className="dc-skeleton" />)}
 </div>
 )
}
