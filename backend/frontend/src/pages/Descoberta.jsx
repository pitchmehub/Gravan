import React, { useEffect, useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { usePlayer } from '../contexts/PlayerContext'
import BotaoCurtir from '../components/BotaoCurtir'
import { supabase } from '../lib/supabase'
import { api } from '../lib/api'
import './Descoberta.css'

function fmt(cents) {
  return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format((cents ?? 0) / 100)
}

const GENEROS = ['Todos', 'Sertanejo', 'MPB', 'Funk', 'Samba', 'Rock', 'Pop', 'Gospel', 'Forró', 'Pagode', 'RNB']
const GRADIENTS = [
  'linear-gradient(135deg,#BE123C,#09090B)',
  'linear-gradient(135deg,#0F6E56,#1D9E75)',
  'linear-gradient(135deg,#854F0B,#EF9F27)',
  'linear-gradient(135deg,#185FA5,#378ADD)',
  'linear-gradient(135deg,#993556,#D4537E)',
  'linear-gradient(135deg,#09090B,#3F3F46)',
]
const ObrgGrad = id => GRADIENTS[(id?.charCodeAt(0) ?? 0) % GRADIENTS.length]

function ObraCard({ obra, onPlay, onShowFicha, isPlaying, isActive, onAddHistorico }) {
  const lastClick = useRef(0)

  function handleClick(e) {
    if (e.target.closest('.dc-card-play')) return
    const now = Date.now()
    if (now - lastClick.current < 400) {
      lastClick.current = 0
      onShowFicha(obra)
    } else {
      lastClick.current = now
      if (obra.audio_path) {
        onAddHistorico(obra.id)
        onPlay(obra)
      } else {
        // Sem áudio? Já abre a ficha técnica
        onShowFicha(obra)
      }
    }
  }

  return (
    <div className={`dc-card ${isActive ? 'dc-card-active' : ''}`} onClick={handleClick}>
      <div className="dc-card-cover" style={{ background: ObrgGrad(obra.id) }}>
        <span className="dc-card-note">♪</span>
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
        <div className="dc-card-preco">{fmt(obra.preco_cents)}</div>
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
          👑 Visualizar como administrador
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
      <div className="dc-comp-nome">🏢 {nome}</div>
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
            👑 Visualizar como administrador
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

function FichaTecnica({ obra, onClose, onPlay, isPlaying, isActive }) {
  const navigate = useNavigate()
  const [coautores, setCoautores] = useState([])

  useEffect(() => {
    async function load() {
      const { data } = await supabase
        .from('coautorias')
        .select('share_pct, is_titular, perfis(id, nome, nome_artistico, avatar_url, nivel)')
        .eq('obra_id', obra.id)
      setCoautores(data ?? [])
    }
    load()
  }, [obra.id])

  return (
    <div className="dc-modal-overlay" onClick={e => { if (e.target === e.currentTarget) onClose() }}>
      <div className="dc-modal">
        <button className="dc-modal-close" onClick={onClose}>×</button>

        <div className="dc-modal-header" style={{ background: ObrgGrad(obra.id) }}>
          <div className="dc-modal-cover">♪</div>
          <div>
            <div className="dc-modal-genre">{obra.genero || 'Composição'}</div>
            <div className="dc-modal-nome">{obra.nome}</div>
            <div className="dc-modal-autor">{obra.titular_nome}</div>
          </div>
        </div>

        {obra.audio_path && (
          <div className="dc-modal-actions">
            <button className="dc-modal-play-btn" onClick={() => onPlay(obra)}>
              {isPlaying ? '⏸' : '▶'}
            </button>
            <span className="dc-modal-action-label">
              {isActive && isPlaying ? 'Reproduzindo…' : 'Ouvir preview'}
            </span>
          </div>
        )}

        <div className="dc-modal-section">
          <h3 className="dc-modal-section-title">Compositores</h3>
          <div className="dc-modal-comp-list">
            {coautores.map((c, i) => {
              const perfilId = c.perfis?.id
              const irParaPerfil = () => {
                if (!perfilId) return
                onClose()
                navigate(`/perfil/${perfilId}`)
              }
              return (
                <div key={i} className="dc-modal-comp-row"
                     onClick={irParaPerfil}
                     style={{ cursor: perfilId ? 'pointer' : 'default' }}
                     title={perfilId ? 'Ver perfil' : ''}>
                  <div className="dc-modal-comp-avatar">
                    {c.perfis?.avatar_url
                      ? <img src={c.perfis.avatar_url} alt={c.perfis.nome} />
                      : c.perfis?.nome?.charAt(0).toUpperCase()
                    }
                  </div>
                  <div className="dc-modal-comp-info">
                    <div className="dc-modal-comp-nome"
                         style={perfilId ? { color: '#E11D48', textDecoration: 'underline' } : undefined}>
                      {c.perfis?.nome_artistico || c.perfis?.nome}
                      {c.is_titular && <span className="dc-titular-badge">Titular</span>}
                    </div>
                    <div className="dc-modal-comp-nivel">{c.perfis?.nivel}</div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        <div className="dc-modal-buy-bar">
          <div>
            <div className="dc-modal-buy-label">Valor da licença</div>
            <div className="dc-modal-buy-valor">{fmt(obra.preco_cents)}</div>
          </div>
          <button
            className="dc-modal-buy-btn"
            onClick={() => { onClose(); navigate(`/comprar/${obra.id}`) }}
          >
            Comprar composição
          </button>
        </div>
      </div>
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
  const { playObra, obra: obraAtual, playing, togglePlay } = usePlayer()

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
          .select('obra_id, ouvido_em, obras(id, nome, genero, preco_cents, audio_path, status, titular_id, perfis!titular_id(nome, nivel))')
          .eq('perfil_id', perfil.id)
          .order('ouvido_em', { ascending: false })
          .limit(40)
        setBiblioteca((data ?? []).filter(h => h.obras).map(h => ({
          ...h.obras,
          titular_nome: h.obras?.perfis?.nome,
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
            .select('id, nome, nome_artistico, avatar_url, nivel')
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
    setCompositor(comp)
    setBusca('')
    setResultados({ obras: [], compositores: [] })
    const { data } = await supabase
      .from('coautorias')
      .select('obra_id, is_titular, share_pct, obras(id, nome, genero, preco_cents, audio_path, status, titular_id, perfis!titular_id(nome, nivel))')
      .eq('perfil_id', comp.id)
      .limit(60)
    const obras = (data ?? [])
      .filter(c => c.obras?.status === 'publicada')
      .map(c => ({
        ...c.obras,
        titular_nome:  c.obras?.perfis?.nome,
        titular_nivel: c.obras?.perfis?.nivel,
      }))
    setObrasDoCom(obras)
  }

  function handlePlay(obra) {
    if (!obra.audio_path) {
      // Sem áudio: abre a ficha técnica
      setFichaObra(obra)
      return
    }
    if (obraAtual?.id === obra.id) { togglePlay(); return }
    // Registra play para analytics (fire-and-forget — não bloqueia o UX)
    api.post(`/analytics/play/${obra.id}`, {}).catch(() => {})
    playObra(obra)
  }

  const cadastroIncompleto = perfil && !perfil.cadastro_completo

  return (
    <div className="dc-root">
      {cadastroIncompleto && (
        <div style={{
          padding: '14px 28px',
          background: 'linear-gradient(90deg,#BE123C,#09090B)',
          color: '#fff', display: 'flex', alignItems: 'center', gap: 14,
          flexWrap: 'wrap',
        }}>
          <span style={{ fontSize: 20 }}>⚠</span>
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
        <div className="dc-tabs">
          <button className={`dc-tab ${aba === 'catalogo' ? 'dc-tab-active' : ''}`}
            onClick={() => { setAba('catalogo'); setCompositor(null); setBusca('') }}>
            <span className="dc-tab-icon">⊞</span> Catálogo
          </button>
          <button className={`dc-tab ${aba === 'biblioteca' ? 'dc-tab-active' : ''}`}
            onClick={() => { setAba('biblioteca'); setCompositor(null); setBusca('') }}>
            <span className="dc-tab-icon">♫</span> Biblioteca
          </button>
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
        <div className="dc-section">
          <div className="dc-compositor-header">
            <div className="dc-compositor-avatar" style={{ background: ObrgGrad(compositor.id) }}>
              {compositor.avatar_url ? <img src={compositor.avatar_url} alt={compositor.nome} /> : compositor.nome?.charAt(0).toUpperCase()}
            </div>
            <div>
              <div className="dc-compositor-nome">{compositor.nome_artistico || compositor.nome}</div>
              <div className="dc-muted">{obrasDoCom.length} obra{obrasDoCom.length !== 1 ? 's' : ''} (titular ou coautor)</div>
            </div>
            <button className="dc-back-btn" onClick={() => setCompositor(null)}>← Voltar</button>
          </div>
          <div className="dc-grid">
            {obrasDoCom.map(o => (
              <ObraCard key={o.id} obra={o}
                isActive={obraAtual?.id === o.id}
                isPlaying={obraAtual?.id === o.id && playing}
                onPlay={handlePlay}
                onShowFicha={setFichaObra}
                onAddHistorico={addHistorico} />
            ))}
            {obrasDoCom.length === 0 && <p className="dc-muted">Nenhuma obra publicada.</p>}
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
                      onAddHistorico={addHistorico} />
                  ))}
                </div>
              )}
              {!loadCat && catalogo.length === 0 && (
                <div className="dc-empty">
                  <div className="dc-empty-icon">♪</div>
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
                      onAddHistorico={addHistorico} />
                  ))}
                </div>
              ) : (
                <div className="dc-empty">
                  <div className="dc-empty-icon">♫</div>
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
