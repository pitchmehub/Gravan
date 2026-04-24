import React, { useRef, useState, useEffect, useCallback } from 'react'
import { usePlayer } from '../contexts/PlayerContext'
import { supabase } from '../lib/supabase'
import './GlobalPlayer.css'

function fmt(s) {
  if (!isFinite(s) || isNaN(s)) return '0:00'
  const m = Math.floor(s / 60)
  const sec = Math.floor(s % 60).toString().padStart(2, '0')
  return `${m}:${sec}`
}

const GRADIENTS = [
  'linear-gradient(160deg,#083257 0%,#09090B 100%)',
  'linear-gradient(160deg,#0F6E56 0%,#09090B 100%)',
  'linear-gradient(160deg,#854F0B 0%,#09090B 100%)',
  'linear-gradient(160deg,#185FA5 0%,#09090B 100%)',
  'linear-gradient(160deg,#993556 0%,#09090B 100%)',
  'linear-gradient(160deg,#3F3F46 0%,#09090B 100%)',
]
function obraGrad(obra) {
  if (!obra) return GRADIENTS[0]
  return GRADIENTS[(obra.id?.charCodeAt(0) ?? 0) % GRADIENTS.length]
}
function miniColor(obra) {
  if (!obra) return '#3F3F46'
  return ['#083257','#0F6E56','#854F0B','#185FA5','#993556','#3F3F46'][(obra.id?.charCodeAt(0) ?? 0) % 6]
}

export default function GlobalPlayer() {
  const {
    obra, queue, index, playing, minimized, expanded, visible,
    currentTime, duration, loading, volume,
    togglePlay, seek, nextTrack, prevTrack, goToIndex, reorderQueue, removeFromQueue,
    close, setMinimized, setExpanded, expandPlayer, setVolume,
  } = usePlayer()

  const [showQueue,  setShowQueue]  = useState(false)
  const [letraOpen,  setLetraOpen]  = useState(false)
  const [letra,      setLetra]      = useState(null)
  const [letraLoading, setLetraLoading] = useState(false)

  // Drag-to-reorder state
  const [dragIdx,     setDragIdx]     = useState(null)
  const [dragOverIdx, setDragOverIdx] = useState(null)
  const touchDragRef  = useRef({ idx: null, startY: 0 })
  const queueListRef  = useRef(null)
  const barRef        = useRef(null)
  const touchStart    = useRef(null)
  const letraTouchY   = useRef(null)

  // Reset letra on obra change
  useEffect(() => {
    setLetra(null)
    setLetraOpen(false)
  }, [obra?.id])

  // Close queue view when player collapses
  useEffect(() => {
    if (!expanded) setShowQueue(false)
  }, [expanded])

  if (!visible || !obra) return null

  const pct = duration > 0 ? (currentTime / duration) * 100 : 0
  const iniciais = obra.titular_nome?.charAt(0).toUpperCase() ?? '♪'

  // ── Seek ─────────────────────────────────────────────────
  function seekFromEvent(e) {
    if (!barRef.current || !duration) return
    const rect = barRef.current.getBoundingClientRect()
    const clientX = e.touches ? e.touches[0].clientX : e.clientX
    const x = Math.max(0, Math.min(clientX - rect.left, rect.width))
    seek((x / rect.width) * duration)
  }
  function handleBarMouseDown(e) {
    seekFromEvent(e)
    const onMove = ev => seekFromEvent(ev)
    const onUp   = () => { window.removeEventListener('mousemove', onMove); window.removeEventListener('mouseup', onUp) }
    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onUp)
  }

  // ── Swipe geral no expanded ───────────────────────────────
  function handleExpandedTouchStart(e) {
    if (e.target.closest('.gp-letra-sheet') || e.target.closest('.gp-q-grip') || e.target.closest('.gp-queue-list')) return
    touchStart.current = { x: e.touches[0].clientX, y: e.touches[0].clientY }
  }
  function handleExpandedTouchEnd(e) {
    if (!touchStart.current) return
    const dx = e.changedTouches[0].clientX - touchStart.current.x
    const dy = e.changedTouches[0].clientY - touchStart.current.y
    touchStart.current = null
    if (dy > 80 && Math.abs(dy) > Math.abs(dx) * 1.5) { setExpanded(false); return }
    if (!showQueue) {
      if (dx < -60 && Math.abs(dx) > Math.abs(dy) * 1.5) { nextTrack(); return }
      if (dx > 60  && Math.abs(dx) > Math.abs(dy) * 1.5) { prevTrack() }
    }
  }

  // ── Letra ─────────────────────────────────────────────────
  function handleLetraTouchStart(e) { e.stopPropagation(); letraTouchY.current = e.touches[0].clientY }
  function handleLetraTouchEnd(e) {
    e.stopPropagation()
    if (!letraTouchY.current) return
    const dy = e.changedTouches[0].clientY - letraTouchY.current
    letraTouchY.current = null
    if (dy > 60) setLetraOpen(false)
  }
  async function abrirLetra() {
    setLetraOpen(true)
    if (letra !== null) return
    setLetraLoading(true)
    try {
      const { data } = await supabase.from('obras').select('letra').eq('id', obra.id).maybeSingle()
      setLetra(data?.letra || '')
    } catch (_) { setLetra('') }
    finally { setLetraLoading(false) }
  }

  // ── Drag-to-reorder (touch) ───────────────────────────────
  function handleGripTouchStart(e, idx) {
    e.stopPropagation()
    touchDragRef.current = { idx, startY: e.touches[0].clientY }
    setDragIdx(idx)
  }
  function handleQueueTouchMove(e) {
    if (touchDragRef.current.idx === null) return
    const el = queueListRef.current
    if (!el) return
    const items = [...el.querySelectorAll('.gp-q-item')]
    const y = e.touches[0].clientY
    let over = null
    items.forEach((item, i) => {
      const r = item.getBoundingClientRect()
      if (y >= r.top && y <= r.bottom) over = i
    })
    if (over !== null) setDragOverIdx(over)
  }
  function handleQueueTouchEnd() {
    if (dragIdx !== null && dragOverIdx !== null && dragIdx !== dragOverIdx) {
      reorderQueue(dragIdx, dragOverIdx)
    }
    setDragIdx(null)
    setDragOverIdx(null)
    touchDragRef.current = { idx: null, startY: 0 }
  }

  // ── Drag-to-reorder (mouse/desktop) ──────────────────────
  function handleDragStart(e, idx) { e.dataTransfer.effectAllowed = 'move'; setDragIdx(idx) }
  function handleDragOver(e, idx)  { e.preventDefault(); setDragOverIdx(idx) }
  function handleDrop(e, idx)      { e.preventDefault(); if (dragIdx !== null && dragIdx !== idx) reorderQueue(dragIdx, idx); setDragIdx(null); setDragOverIdx(null) }
  function handleDragEnd()         { setDragIdx(null); setDragOverIdx(null) }

  // ════════════════════════════════════════════════════════
  // PLAYER EXPANDIDO
  // ════════════════════════════════════════════════════════
  if (expanded) {
    return (
      <div
        className="gp-expanded"
        style={{ background: obraGrad(obra) }}
        onTouchStart={handleExpandedTouchStart}
        onTouchEnd={handleExpandedTouchEnd}
      >
        {/* Header */}
        <div className="gp-exp-header">
          <button className="gp-exp-btn" onClick={() => setExpanded(false)}><ChevronDownIcon /></button>

          {/* Tabs TOCANDO | FILA */}
          <div className="gp-view-tabs">
            <button
              className={`gp-view-tab ${!showQueue ? 'active' : ''}`}
              onClick={() => setShowQueue(false)}
            >TOCANDO</button>
            <button
              className={`gp-view-tab ${showQueue ? 'active' : ''}`}
              onClick={() => setShowQueue(true)}
            >FILA {queue.length > 1 ? `· ${queue.length}` : ''}</button>
          </div>

          {queue.length > 1 && !showQueue
            ? <span className="gp-exp-queue-badge">{index + 1}/{queue.length}</span>
            : <div style={{ width: 44 }} />
          }
        </div>

        {/* ── VIEW: TOCANDO ── */}
        {!showQueue && (
          <>
            <div className="gp-exp-cover-wrap">
              <div className="gp-exp-cover">
                <span className="gp-exp-cover-iniciais">{iniciais}</span>
              </div>
            </div>
            <div className="gp-exp-info">
              <div className="gp-exp-nome">{obra.nome}</div>
              <div className="gp-exp-autor">{obra.titular_nome}</div>
            </div>
          </>
        )}

        {/* ── VIEW: FILA ── */}
        {showQueue && (
          <div
            className="gp-queue-list"
            ref={queueListRef}
            onTouchMove={handleQueueTouchMove}
            onTouchEnd={handleQueueTouchEnd}
          >
            {queue.map((item, i) => (
              <div
                key={item.id + i}
                className={[
                  'gp-q-item',
                  i === index      ? 'gp-q-item-active'  : '',
                  i === dragIdx    ? 'gp-q-item-dragging' : '',
                  i === dragOverIdx && i !== dragIdx ? 'gp-q-item-over' : '',
                ].join(' ')}
                draggable
                onDragStart={e => handleDragStart(e, i)}
                onDragOver={e => handleDragOver(e, i)}
                onDrop={e => handleDrop(e, i)}
                onDragEnd={handleDragEnd}
                onClick={() => { if (dragIdx === null) goToIndex(i) }}
              >
                {/* Grip handle */}
                <span
                  className="gp-q-grip"
                  onTouchStart={e => handleGripTouchStart(e, i)}
                >⠿</span>

                {/* Mini cover */}
                <div className="gp-q-mini-cover" style={{ background: miniColor(item) }}>
                  {i === index && playing
                    ? <span className="gp-q-playing-dot">▶</span>
                    : <span style={{ fontSize: 11 }}>♪</span>
                  }
                </div>

                {/* Info */}
                <div className="gp-q-info">
                  <div className="gp-q-nome">{item.nome}</div>
                  <div className="gp-q-autor">{item.titular_nome}</div>
                </div>

                {/* Badge agora tocando */}
                {i === index && (
                  <span className="gp-q-now-badge">agora</span>
                )}

                {/* Remove */}
                {queue.length > 1 && (
                  <button
                    className="gp-q-remove"
                    onClick={e => { e.stopPropagation(); removeFromQueue(i) }}
                    title="Remover da fila"
                  >×</button>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Barra de progresso — sempre visível */}
        <div className="gp-exp-progress-wrap">
          <div
            className="gp-exp-progress-bar"
            ref={barRef}
            onMouseDown={handleBarMouseDown}
            onTouchStart={e => { e.stopPropagation(); seekFromEvent(e) }}
            onTouchMove={e => { e.stopPropagation(); seekFromEvent(e) }}
          >
            <div className="gp-exp-progress-fill" style={{ width: `${pct}%` }}>
              <div className="gp-exp-progress-thumb" />
            </div>
          </div>
          <div className="gp-exp-times">
            <span>{fmt(currentTime)}</span>
            <span>-{fmt(Math.max(0, duration - currentTime))}</span>
          </div>
        </div>

        {/* Controles — sempre visíveis */}
        <div className="gp-exp-controls">
          <button className="gp-exp-ctrl-btn" onClick={prevTrack}><PrevIcon size={28} /></button>
          <button className="gp-exp-play-btn" onClick={togglePlay}>
            {loading ? <Spinner size={32} /> : playing ? <PauseIcon size={32} /> : <PlayIcon size={32} />}
          </button>
          <button className="gp-exp-ctrl-btn" onClick={nextTrack}><NextIcon size={28} /></button>
        </div>

        {/* LER LETRA — só na view Tocando */}
        {!showQueue && (
          <button className="gp-ler-letra-btn" onClick={abrirLetra}>📖 LER LETRA</button>
        )}

        {/* Janela de letra */}
        {letraOpen && (
          <div
            className="gp-letra-sheet"
            onTouchStart={handleLetraTouchStart}
            onTouchEnd={handleLetraTouchEnd}
          >
            <div className="gp-letra-handle-bar" onClick={() => setLetraOpen(false)} />
            <div className="gp-letra-header">
              <span className="gp-letra-titulo">{obra.nome}</span>
              <button className="gp-letra-close" onClick={() => setLetraOpen(false)}>×</button>
            </div>
            <div className="gp-letra-body">
              {letraLoading
                ? <div className="gp-letra-empty">Carregando letra…</div>
                : (letra && letra.trim())
                  ? <pre className="gp-letra-text">{letra}</pre>
                  : <div className="gp-letra-empty">Letra não disponível para esta obra.</div>
              }
            </div>
          </div>
        )}
      </div>
    )
  }

  // ════════════════════════════════════════════════════════
  // MINIMIZADO
  // ════════════════════════════════════════════════════════
  if (minimized) {
    return (
      <div className="gp-mini" onClick={expandPlayer}>
        <div className="gp-mini-cover">{iniciais}</div>
        <div className="gp-mini-info">
          <span className="gp-mini-nome">{obra.nome}</span>
          <span className="gp-mini-autor">{obra.titular_nome}</span>
        </div>
        <button className="gp-icon-btn" onClick={e => { e.stopPropagation(); prevTrack() }}><PrevIcon /></button>
        <button className="gp-icon-btn" onClick={e => { e.stopPropagation(); togglePlay() }}>
          {loading ? <Spinner /> : playing ? <PauseIcon /> : <PlayIcon />}
        </button>
        <button className="gp-icon-btn" onClick={e => { e.stopPropagation(); nextTrack() }}><NextIcon /></button>
        <button className="gp-icon-btn gp-close-btn" onClick={e => { e.stopPropagation(); close() }}><CloseIcon /></button>
        <div className="gp-mini-bar"><div className="gp-mini-bar-fill" style={{ width: `${pct}%` }} /></div>
      </div>
    )
  }

  // ════════════════════════════════════════════════════════
  // BARRA (desktop / clique no mobile → expande)
  // ════════════════════════════════════════════════════════
  return (
    <div className="gp-root" onClick={() => { if (window.innerWidth <= 767) expandPlayer() }}>
      <div className="gp-top-bar" ref={barRef} onMouseDown={e => { e.stopPropagation(); handleBarMouseDown(e) }}>
        <div className="gp-top-bar-fill" style={{ width: `${pct}%` }} />
      </div>
      <div className="gp-body">
        <div className="gp-track-info">
          <div className="gp-cover"><span>{iniciais}</span></div>
          <div className="gp-meta">
            <div className="gp-nome">{obra.nome}</div>
            <div className="gp-autor">{obra.titular_nome}</div>
          </div>
        </div>
        <div className="gp-controls" onClick={e => e.stopPropagation()}>
          <button className="gp-icon-btn" onClick={prevTrack}><PrevIcon /></button>
          <button className="gp-play-btn" onClick={togglePlay}>
            {loading ? <Spinner size={22} /> : playing ? <PauseIcon size={22} /> : <PlayIcon size={22} />}
          </button>
          <button className="gp-icon-btn" onClick={nextTrack}><NextIcon /></button>
        </div>
        <div className="gp-right" onClick={e => e.stopPropagation()}>
          <span className="gp-time">{fmt(currentTime)} / {fmt(duration)}</span>
          <div className="gp-volume">
            <VolumeIcon />
            <input type="range" min="0" max="1" step="0.05" value={volume}
              onChange={e => setVolume(Number(e.target.value))} className="gp-vol-slider" />
          </div>
          {queue.length > 1 && <span className="gp-queue-info">{index + 1}/{queue.length}</span>}
          <button className="gp-icon-btn" onClick={() => setMinimized(true)}><MinimizeIcon /></button>
          <button className="gp-icon-btn gp-close-btn" onClick={close}><CloseIcon /></button>
        </div>
      </div>
    </div>
  )
}

// ── Ícones ────────────────────────────────────────────────
function PlayIcon({ size = 16 }) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor"><polygon points="5,3 19,12 5,21" /></svg>
}
function PauseIcon({ size = 16 }) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="4" width="4" height="16" rx="1"/><rect x="14" y="4" width="4" height="16" rx="1"/></svg>
}
function PrevIcon({ size = 16 }) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor"><polygon points="19,20 9,12 19,4"/><rect x="5" y="4" width="3" height="16" rx="1"/></svg>
}
function NextIcon({ size = 16 }) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor"><polygon points="5,4 15,12 5,20"/><rect x="16" y="4" width="3" height="16" rx="1"/></svg>
}
function CloseIcon() {
  return <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
}
function MinimizeIcon() {
  return <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><line x1="5" y1="12" x2="19" y2="12"/></svg>
}
function ChevronDownIcon() {
  return <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="6 9 12 15 18 9"/></svg>
}
function VolumeIcon() {
  return <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M11 5L6 9H2v6h4l5 4V5z"/><path d="M15.54 8.46a5 5 0 0 1 0 7.07" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round"/></svg>
}
function Spinner({ size = 16 }) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><circle cx="12" cy="12" r="10" strokeOpacity=".25"/><path d="M12 2 a10 10 0 0 1 10 10" strokeLinecap="round" style={{ animation: 'gp-spin .8s linear infinite' }}/></svg>
}
