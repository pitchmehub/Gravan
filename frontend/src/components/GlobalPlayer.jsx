import React, { useRef, useState } from 'react'
import { usePlayer } from '../contexts/PlayerContext'
import './GlobalPlayer.css'

function fmt(s) {
  if (!isFinite(s) || isNaN(s)) return '0:00'
  const m = Math.floor(s / 60)
  const sec = Math.floor(s % 60).toString().padStart(2, '0')
  return `${m}:${sec}`
}

export default function GlobalPlayer() {
  const {
    obra, queue, index, playing, minimized, visible,
    currentTime, duration, loading, volume,
    togglePlay, seek, nextTrack, prevTrack,
    close, setMinimized, setVolume,
  } = usePlayer()

  const [dragging, setDragging] = useState(false)
  const barRef = useRef(null)

  if (!visible || !obra) return null

  const pct = duration > 0 ? (currentTime / duration) * 100 : 0

  function seekFromEvent(e) {
    if (!barRef.current || !duration) return
    const rect = barRef.current.getBoundingClientRect()
    const x = Math.max(0, Math.min(e.clientX - rect.left, rect.width))
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

  const iniciais = obra.titular_nome?.charAt(0).toUpperCase() ?? '♪'

  // ── MINIMIZADO ──────────────────────────────────────────────
  if (minimized) {
    return (
      <div className="gp-mini" onClick={() => setMinimized(false)}>
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

  // ── PLAYER COMPLETO ──────────────────────────────────────────
  return (
    <div className="gp-root">
      {/* Linha de progresso no topo */}
      <div className="gp-top-bar" ref={barRef} onMouseDown={handleBarMouseDown}>
        <div className="gp-top-bar-fill" style={{ width: `${pct}%` }} />
      </div>

      <div className="gp-body">
        {/* Capa + info */}
        <div className="gp-track-info">
          <div className="gp-cover">
            <span>{iniciais}</span>
          </div>
          <div className="gp-meta">
            <div className="gp-nome">{obra.nome}</div>
            <div className="gp-autor">{obra.titular_nome}</div>
          </div>
        </div>

        {/* Controles centrais */}
        <div className="gp-controls">
          <button
            className="gp-icon-btn"
            onClick={prevTrack}
            title="Anterior"
            disabled={queue.length <= 1}
          >
            <PrevIcon />
          </button>

          <button className="gp-play-btn" onClick={togglePlay} title={playing ? 'Pausar' : 'Reproduzir'}>
            {loading ? <Spinner size={22} /> : playing ? <PauseIcon size={22} /> : <PlayIcon size={22} />}
          </button>

          <button
            className="gp-icon-btn"
            onClick={nextTrack}
            title="Próxima"
            disabled={queue.length <= 1}
          >
            <NextIcon />
          </button>
        </div>

        {/* Tempo + volume + ações */}
        <div className="gp-right">
          <span className="gp-time">
            {fmt(currentTime)} / {fmt(duration)}
          </span>

          <div className="gp-volume">
            <VolumeIcon />
            <input
              type="range" min="0" max="1" step="0.05"
              value={volume}
              onChange={e => setVolume(Number(e.target.value))}
              className="gp-vol-slider"
              title={`Volume: ${Math.round(volume * 100)}%`}
            />
          </div>

          {queue.length > 1 && (
            <span className="gp-queue-info">
              {index + 1}/{queue.length}
            </span>
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

// ── Ícones SVG inline ─────────────────────────────────────────

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

function PrevIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
      <polygon points="19,20 9,12 19,4"/>
      <rect x="5" y="4" width="3" height="16" rx="1"/>
    </svg>
  )
}

function NextIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
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
