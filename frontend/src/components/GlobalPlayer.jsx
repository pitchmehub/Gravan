import React, { useRef, useState, useEffect } from 'react'
import { usePlayer } from '../contexts/PlayerContext'
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

export default function GlobalPlayer() {
  const {
    obra, queue, index, playing, minimized, expanded, visible,
    currentTime, duration, loading, volume,
    togglePlay, seek, nextTrack, prevTrack,
    close, setMinimized, setExpanded, expandPlayer, setVolume,
  } = usePlayer()

  const [dragging, setDragging] = useState(false)
  const barRef = useRef(null)

  // Touch swipe state for expanded player
  const touchStart = useRef(null)
  const expandedRef = useRef(null)

  if (!visible || !obra) return null

  const pct = duration > 0 ? (currentTime / duration) * 100 : 0
  const iniciais = obra.titular_nome?.charAt(0).toUpperCase() ?? '♪'

  function seekFromEvent(e) {
    if (!barRef.current || !duration) return
    const rect = barRef.current.getBoundingClientRect()
    const clientX = e.touches ? e.touches[0].clientX : e.clientX
    const x = Math.max(0, Math.min(clientX - rect.left, rect.width))
    seek((x / rect.width) * duration)
  }

  function handleBarMouseDown(e) {
    seekFromEvent(e)
    setDragging(true)
    const onMove = (ev) => seekFromEvent(ev)
    const onUp = () => {
      setDragging(false)
      window.removeEventListener('mousemove', onMove)
      window.removeEventListener('mouseup', onUp)
    }
    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onUp)
  }

  function handleBarTouchStart(e) {
    seekFromEvent(e)
  }
  function handleBarTouchMove(e) {
    seekFromEvent(e)
  }

  // Swipe handlers for expanded player
  function handleExpandedTouchStart(e) {
    touchStart.current = {
      x: e.touches[0].clientX,
      y: e.touches[0].clientY,
    }
  }

  function handleExpandedTouchEnd(e) {
    if (!touchStart.current) return
    const dx = e.changedTouches[0].clientX - touchStart.current.x
    const dy = e.changedTouches[0].clientY - touchStart.current.y
    touchStart.current = null

    // Swipe down → minimize
    if (dy > 80 && Math.abs(dy) > Math.abs(dx) * 1.5) {
      setExpanded(false)
      return
    }
    // Swipe left → next track
    if (dx < -60 && Math.abs(dx) > Math.abs(dy) * 1.5) {
      nextTrack()
      return
    }
    // Swipe right → prev track
    if (dx > 60 && Math.abs(dx) > Math.abs(dy) * 1.5) {
      prevTrack()
    }
  }

  // ── PLAYER EXPANDIDO (tela cheia) ──────────────────────────
  if (expanded) {
    return (
      <div
        className="gp-expanded"
        style={{ background: obraGrad(obra) }}
        ref={expandedRef}
        onTouchStart={handleExpandedTouchStart}
        onTouchEnd={handleExpandedTouchEnd}
      >
        {/* Topo */}
        <div className="gp-exp-header">
          <button className="gp-exp-btn" onClick={() => setExpanded(false)} title="Minimizar">
            <ChevronDownIcon />
          </button>
          <span className="gp-exp-title">{obra.genero || 'Reproduzindo'}</span>
          <div style={{ width: 40 }} />
        </div>

        {/* Capa grande */}
        <div className="gp-exp-cover-wrap">
          <div className="gp-exp-cover">
            <span className="gp-exp-cover-iniciais">{iniciais}</span>
          </div>
        </div>

        {/* Info da faixa */}
        <div className="gp-exp-info">
          <div className="gp-exp-nome">{obra.nome}</div>
          <div className="gp-exp-autor">{obra.titular_nome}</div>
        </div>

        {/* Barra de progresso */}
        <div className="gp-exp-progress-wrap">
          <div
            className="gp-exp-progress-bar"
            ref={barRef}
            onMouseDown={handleBarMouseDown}
            onTouchStart={handleBarTouchStart}
            onTouchMove={handleBarTouchMove}
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

        {/* Controles principais */}
        <div className="gp-exp-controls">
          <button className="gp-exp-ctrl-btn" onClick={prevTrack} disabled={queue.length <= 1}>
            <PrevIcon size={28} />
          </button>
          <button className="gp-exp-play-btn" onClick={togglePlay}>
            {loading ? <Spinner size={32} /> : playing ? <PauseIcon size={32} /> : <PlayIcon size={32} />}
          </button>
          <button className="gp-exp-ctrl-btn" onClick={nextTrack} disabled={queue.length <= 1}>
            <NextIcon size={28} />
          </button>
        </div>

        {/* Fila */}
        {queue.length > 1 && (
          <div className="gp-exp-queue-info">
            {index + 1} / {queue.length}
          </div>
        )}

        {/* Dica de gesto */}
        <div className="gp-exp-swipe-hint">Arraste para baixo para minimizar</div>
      </div>
    )
  }

  // ── MINIMIZADO ──────────────────────────────────────────────
  if (minimized) {
    return (
      <div className="gp-mini" onClick={expandPlayer}>
        <div className="gp-mini-cover">{iniciais}</div>
        <div className="gp-mini-info">
          <span className="gp-mini-nome">{obra.nome}</span>
          <span className="gp-mini-autor">{obra.titular_nome}</span>
        </div>
        <button className="gp-icon-btn" onClick={e => { e.stopPropagation(); togglePlay() }}>
          {loading ? <Spinner /> : playing ? <PauseIcon /> : <PlayIcon />}
        </button>
        <button className="gp-icon-btn gp-close-btn" onClick={e => { e.stopPropagation(); close() }}>
          <CloseIcon />
        </button>
        <div className="gp-mini-bar">
          <div className="gp-mini-bar-fill" style={{ width: `${pct}%` }} />
        </div>
      </div>
    )
  }

  // ── PLAYER BARRA (desktop / tablet) ──────────────────────────
  return (
    <div className="gp-root" onClick={e => {
      // No mobile, clicar na barra expande
      if (window.innerWidth <= 767) expandPlayer()
    }}>
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
          <button className="gp-icon-btn" onClick={prevTrack} title="Anterior" disabled={queue.length <= 1}>
            <PrevIcon />
          </button>
          <button className="gp-play-btn" onClick={togglePlay} title={playing ? 'Pausar' : 'Reproduzir'}>
            {loading ? <Spinner size={22} /> : playing ? <PauseIcon size={22} /> : <PlayIcon size={22} />}
          </button>
          <button className="gp-icon-btn" onClick={nextTrack} title="Próxima" disabled={queue.length <= 1}>
            <NextIcon />
          </button>
        </div>

        <div className="gp-right" onClick={e => e.stopPropagation()}>
          <span className="gp-time">{fmt(currentTime)} / {fmt(duration)}</span>
          <div className="gp-volume">
            <VolumeIcon />
            <input
              type="range" min="0" max="1" step="0.05"
              value={volume}
              onChange={e => setVolume(Number(e.target.value))}
              className="gp-vol-slider"
            />
          </div>
          {queue.length > 1 && (
            <span className="gp-queue-info">{index + 1}/{queue.length}</span>
          )}
          <button className="gp-icon-btn" onClick={() => setMinimized(true)} title="Minimizar">
            <MinimizeIcon />
          </button>
          <button className="gp-icon-btn gp-close-btn" onClick={close} title="Fechar">
            <CloseIcon />
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Ícones SVG ────────────────────────────────────────────────

function PlayIcon({ size = 16 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor">
      <polygon points="5,3 19,12 5,21" />
    </svg>
  )
}
function PauseIcon({ size = 16 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor">
      <rect x="6" y="4" width="4" height="16" rx="1"/>
      <rect x="14" y="4" width="4" height="16" rx="1"/>
    </svg>
  )
}
function PrevIcon({ size = 16 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor">
      <polygon points="19,20 9,12 19,4"/>
      <rect x="5" y="4" width="3" height="16" rx="1"/>
    </svg>
  )
}
function NextIcon({ size = 16 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor">
      <polygon points="5,4 15,12 5,20"/>
      <rect x="16" y="4" width="3" height="16" rx="1"/>
    </svg>
  )
}
function CloseIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
      <line x1="18" y1="6" x2="6" y2="18"/>
      <line x1="6" y1="6" x2="18" y2="18"/>
    </svg>
  )
}
function MinimizeIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
      <line x1="5" y1="12" x2="19" y2="12"/>
    </svg>
  )
}
function ChevronDownIcon() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="6 9 12 15 18 9"/>
    </svg>
  )
}
function VolumeIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
      <path d="M11 5L6 9H2v6h4l5 4V5z"/>
      <path d="M15.54 8.46a5 5 0 0 1 0 7.07" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round"/>
    </svg>
  )
}
function Spinner({ size = 16 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
      <circle cx="12" cy="12" r="10" strokeOpacity=".25"/>
      <path d="M12 2 a10 10 0 0 1 10 10" strokeLinecap="round" style={{ animation: 'gp-spin .8s linear infinite' }}/>
    </svg>
  )
}
