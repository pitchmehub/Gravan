import React, { useEffect, useState, useRef } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { usePlayer } from '../contexts/PlayerContext'
import BotaoCurtir from '../components/BotaoCurtir'
import { supabase } from '../lib/supabase'
import { api } from '../lib/api'
import { prefetchAudioUrl } from '../lib/audioUrl'
import './Descoberta.css'
import ArtistaHero, { ObrasLista } from '../components/ArtistaHero'
import FichaTecnica from '../components/FichaTecnica'
import { IconPlay, IconPause } from '../components/Icons'

function fmt(cents) {
 return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format((cents ?? 0) / 100)
}

// Fisher-Yates: embaralha a lista para que a Descoberta nunca mostre as
// mesmas músicas na mesma ordem. Não muta o array original.
function shuffle(arr) {
 const a = [...arr]
 for (let i = a.length - 1; i > 0; i--) {
  const j = Math.floor(Math.random() * (i + 1))
  ;[a[i], a[j]] = [a[j], a[i]]
 }
 return a
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

 function handlePrefetch() {
 if (obra.id && obra.audio_path) prefetchAudioUrl(obra.id)
 }

 return (
 <div
 className={`dc-card ${isActive ? 'dc-card-active' : ''}`}
 onClick={handleClick}
 onMouseEnter={handlePrefetch}
 onTouchStart={handlePrefetch}
 >
 <div className="dc-card-cover" style={{ background: ObrgGrad(obra.id) }}>
 {obra.cover_url ? (
 <img
 src={obra.cover_url}
 alt=""
 loading="lazy"
 decoding="async"
 className="dc-card-cover-img"
 onError={e => { e.currentTarget.style.display = 'none' }}
 />
 ) : (
 <span className="dc-card-note"></span>
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

function EditoraCard({ editora, isAdmin, navigate, onSelect }) {
 const nome = editora.razao_social || editora.nome_artistico || editora.nome || '(sem nome)'
 const iniciais = (nome[0] || '?').toUpperCase()
 return (
 <div className="dc-comp-card" onClick={() => { onSelect?.(editora, nome); navigate(`/perfil/${editora.id}`) }}>
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
 const location = useLocation()
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
 const [busca, setBusca] = useState(() => {
 try { return localStorage.getItem('gravan_ultima_busca') || '' } catch (_) { return '' }
 })
 const [resultados, setResultados] = useState({ obras: [], compositores: [], editoras: [] })
 const isAdmin = perfil?.role === 'administrador'
 const [compositor, setCompositor] = useState(null)
 const [obrasDoCom, setObrasDoCom] = useState([])
 const [loadCat, setLoadCat] = useState(true)
 const [loadBib, setLoadBib] = useState(false)
 const [buscando, setBuscando] = useState(false)
 const [fichaObra, setFichaObra] = useState(null)
 const buscaTimer = useRef(null)
 const buscaLogTimer = useRef(null)
 const [buscaFocada, setBuscaFocada] = useState(false)
 const [buscasRecentes, setBuscasRecentes] = useState([])
 const [mostraFiltro, setMostraFiltro] = useState(false)
 const [ordem, setOrdem] = useState('recente')
 const [apenasPro, setApenasPro] = useState(false)

 useEffect(() => {
 async function load() {
 setLoadCat(true)
 try {
 const params = new URLSearchParams({ page: 1, per_page: 40 })
 if (generoFiltro !== 'Todos') params.set('genero', generoFiltro)
 if (apenasPro) params.set('pro', 'true')
 if (ordem) params.set('sort', ordem)
 const data = await api.get(`/catalogo/?${params.toString()}`)
 const lista = Array.isArray(data) ? data : []
 // Mantém a vibe de "descoberta" embaralhando quando a ordem for "recente";
 // demais ordenações preservam a ordem do servidor.
 setCatalogo(ordem === 'recente' ? shuffle(lista) : lista)
 } catch (e) {
 console.error('Erro ao carregar catálogo:', e)
 setCatalogo([])
 } finally { setLoadCat(false) }
 }
 load()
 }, [generoFiltro, ordem, apenasPro])

 // Quando vier `?obraId=<id>` (ex.: clique numa notificação),
 // busca a obra e abre a Ficha Técnica automaticamente.
 useEffect(() => {
   const params = new URLSearchParams(location.search)
   const obraId = params.get('obraId')
   if (!obraId) return
   let cancelado = false
   ;(async () => {
     try {
       const obra = await api.get(`/catalogo/${obraId}`)
       if (cancelado || !obra) return
       const titularNome =
         obra.titular_nome ||
         obra.perfis?.nome_artistico ||
         obra.perfis?.nome ||
         ''
       setFichaObra({ ...obra, titular_nome: titularNome })
     } catch (e) {
       console.warn('Não foi possível abrir a obra da notificação:', e)
     } finally {
       // limpa o param para não reabrir ao navegar
       navigate('/descoberta', { replace: true })
     }
   })()
   return () => { cancelado = true }
   // eslint-disable-next-line
 }, [location.search])

 useEffect(() => {
 if (aba !== 'biblioteca' || !perfil?.id) return
 async function load() {
 setLoadBib(true)
 try {
 const { data } = await supabase
 .from('historico_escuta')
 .select('obra_id, ouvido_em, obras(id, nome, genero, preco_cents, audio_path, status, titular_id, cover_url, perfis!titular_id(nome, nome_artistico))')
 .eq('perfil_id', perfil.id)
 .order('ouvido_em', { ascending: false })
 .limit(40)
 setBiblioteca((data ?? []).filter(h => h.obras).map(h => ({
 ...h.obras,
 titular_nome: h.obras?.perfis?.nome_artistico || h.obras?.perfis?.nome,
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
 .select('id, nome, nome_artistico, avatar_url, capa_url, role, bio')
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

 // Registra a busca no histórico global após o usuário "parar de digitar"
 // por ~1s, evitando inserir um registro a cada tecla.
 useEffect(() => {
 const q = busca.trim()
 clearTimeout(buscaLogTimer.current)
 if (q.length < 2) return
 buscaLogTimer.current = setTimeout(async () => {
 try {
 await supabase.from('historico_buscas').insert({
 perfil_id: perfil?.id ?? null,
 query: q.slice(0, 120),
 })
 } catch (_) { /* silencioso — log de busca não pode quebrar a UI */ }
 }, 1200)
 return () => clearTimeout(buscaLogTimer.current)
 }, [busca, perfil?.id])

 // Carrega as últimas buscas (de todos os perfis) quando o input recebe foco
 // pela primeira vez. As buscas ficam em cache na sessão do componente.
 async function carregarBuscasRecentes() {
 if (buscasRecentes.length > 0) return
 try {
 const { data } = await supabase
 .from('historico_buscas')
 .select('query, criada_em')
 .order('criada_em', { ascending: false })
 .limit(40)
 const vistos = new Set()
 const distintas = []
 for (const r of (data ?? [])) {
 const k = r.query.trim().toLowerCase()
 if (!k || vistos.has(k)) continue
 vistos.add(k)
 distintas.push(r.query.trim())
 if (distintas.length >= 8) break
 }
 setBuscasRecentes(distintas)
 } catch (_) { /* silencioso */ }
 }

 async function selecionarCompositor(comp) {
 if (!comp?.id) return
 // Limpa busca salva para que ao voltar a Descoberta a tela apareça limpa
 try { localStorage.removeItem('gravan_ultima_busca') } catch (_) {}
 navigate(`/perfil/${comp.id}`)
 }

 function selecionarEditora(_ed, nome) {
 if (!nome) return
 setBusca(nome)
 try { localStorage.setItem('gravan_ultima_busca', nome) } catch (_) {}
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
 className="dc-root page-slide-up"
 onTouchStart={handleRootTouchStart}
 onTouchEnd={handleRootTouchEnd}
 >
 <div className={`dc-topbar ${buscaFocada ? 'dc-topbar-search-active' : ''}`}>
 <div className="dc-topbar-row1">
 <div className="dc-tabs">
 <button className={`dc-tab ${aba === 'biblioteca' ? 'dc-tab-active' : ''}`}
 onClick={() => {
 setAba(aba === 'biblioteca' ? 'catalogo' : 'biblioteca')
 setCompositor(null)
 setBusca('')
 }}>
 <span className="dc-tab-icon"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><path d="M9 18V6l11-2v12"/><circle cx="6.5" cy="18" r="2.5"/><circle cx="17.5" cy="16" r="2.5"/></svg></span> Biblioteca
 </button>
 </div>
 </div>
 <div className="dc-search-row">
 {buscaFocada && (
 <button
 type="button"
 className="dc-search-cancel"
 onMouseDown={(e) => { e.preventDefault(); setBuscaFocada(false); document.activeElement?.blur() }}
 aria-label="Cancelar busca"
 >
 <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><line x1="19" y1="12" x2="5" y2="12"/><polyline points="12 19 5 12 12 5"/></svg>
 </button>
 )}
 <div className="dc-search-wrap" style={{ position: 'relative' }}>
 <input className="dc-search" placeholder="Buscar"
 value={busca}
 onChange={e => setBusca(e.target.value)}
 onFocus={() => { setBuscaFocada(true); carregarBuscasRecentes() }}
 onBlur={() => { setTimeout(() => setBuscaFocada(false), 150) }} />
 {busca && <button className="dc-search-clear" onClick={() => { setBusca(''); setResultados({ obras: [], compositores: [], editoras: [] }); try { localStorage.removeItem('gravan_ultima_busca') } catch (_) {} }}>×</button>}

 {buscaFocada && !busca && buscasRecentes.length > 0 && (
 <div style={{
 position: 'absolute', top: 'calc(100% + 6px)', left: 0, right: 0,
 background: '#FFFFFF', border: '1px solid #E4E4E7', borderRadius: 12,
 boxShadow: '0 8px 24px rgba(0,0,0,0.06)', padding: '8px 0',
 zIndex: 50, maxHeight: 320, overflowY: 'auto',
 }}>
 <div style={{
 padding: '6px 14px 8px', fontSize: 11, fontWeight: 700,
 letterSpacing: 0.5, color: '#71717A', textTransform: 'uppercase',
 }}>
 Últimas buscas
 </div>
 {buscasRecentes.map((q, i) => (
 <button key={i}
 onMouseDown={(e) => { e.preventDefault(); setBusca(q) }}
 style={{
 display: 'flex', alignItems: 'center', gap: 10, width: '100%',
 padding: '8px 14px', background: 'transparent', border: 'none',
 textAlign: 'left', cursor: 'pointer', fontSize: 14, color: '#09090B',
 }}
 onMouseEnter={(e) => e.currentTarget.style.background = '#FAFAFA'}
 onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}>
 <span style={{ color: '#A1A1AA', fontSize: 14 }}>⌕</span>
 <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{q}</span>
 </button>
 ))}
 </div>
 )}
 </div>
 {aba === 'catalogo' && !compositor && (() => {
 const filtrosAtivos = (generoFiltro !== 'Todos' ? 1 : 0) + (apenasPro ? 1 : 0) + (ordem !== 'recente' ? 1 : 0)
 const ORDENS = [
 { key: 'recente',    label: 'Mais recentes' },
 { key: 'antiga',     label: 'Mais antigas' },
 { key: 'preco_asc',  label: 'Menor preço' },
 { key: 'preco_desc', label: 'Maior preço' },
 { key: 'nome',       label: 'Nome (A–Z)' },
 ]
 return (
 <div className="dc-filtro-wrap">
 <button
 className={`dc-filtro-btn ${filtrosAtivos > 0 ? 'dc-filtro-btn-active' : ''}`}
 onClick={() => setMostraFiltro(v => !v)}
 aria-label="Filtros e ordenação"
 >
 <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
 <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/>
 </svg>
 {filtrosAtivos > 0 && <span className="dc-filtro-badge">{filtrosAtivos}</span>}
 </button>
 {mostraFiltro && (
 <>
 <div className="dc-filtro-overlay" onClick={() => setMostraFiltro(false)} />
 <div className="dc-filtro-menu">
 <button
 className={`dc-filtro-pro ${apenasPro ? 'dc-filtro-pro-active' : ''}`}
 onClick={() => setApenasPro(v => !v)}
 >
 <span className="dc-filtro-pro-label">
 <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2l2.4 7.4H22l-6.2 4.5 2.4 7.4L12 16.8 5.8 21.3l2.4-7.4L2 9.4h7.6z"/></svg>
 Apenas usuários PRO
 </span>
 <span className="dc-filtro-pro-toggle">
 {apenasPro ? 'Ativo' : 'Off'}
 </span>
 </button>

 <div className="dc-filtro-menu-title">Ordenar por</div>
 {ORDENS.map(o => (
 <button
 key={o.key}
 className={`dc-filtro-opt ${ordem === o.key ? 'dc-filtro-opt-active' : ''}`}
 onClick={() => { setOrdem(o.key); setMostraFiltro(false) }}
 >
 {o.label}
 {ordem === o.key && (
 <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
 <polyline points="20 6 9 17 4 12"/>
 </svg>
 )}
 </button>
 ))}

 <div className="dc-filtro-menu-title">Gênero</div>
 {GENEROS.map(g => (
 <button
 key={g}
 className={`dc-filtro-opt ${generoFiltro === g ? 'dc-filtro-opt-active' : ''}`}
 onClick={() => { setGeneroFiltro(g); setMostraFiltro(false) }}
 >
 {g}
 {generoFiltro === g && (
 <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
 <polyline points="20 6 9 17 4 12"/>
 </svg>
 )}
 </button>
 ))}
 </div>
 </>
 )}
 </div>
 )
 })()}
 </div>
 </div>

 {busca && (
 <div className={`dc-search-results ${buscaFocada ? 'dc-search-results-fullscreen' : ''}`}>
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
 <EditoraCard key={e.id} editora={e} isAdmin={isAdmin} navigate={navigate} onSelect={selecionarEditora} />
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
 <div className="dc-section">
 {generoFiltro !== 'Todos' && (
 <h2 className="dc-section-title">{generoFiltro}</h2>
 )}
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
