import React, { createContext, useContext, useRef, useState, useEffect, useCallback } from 'react'
import { getAudioUrl } from '../lib/audioUrl'

const PlayerContext = createContext(null)

export function PlayerProvider({ children }) {
  // Fila de obras
  const [queue,      setQueue]      = useState([])   // [{id, nome, titular_nome, audio_path}]
  const [index,      setIndex]      = useState(0)
  const [playing,    setPlaying]    = useState(false)
  const [minimized,  setMinimized]  = useState(false)
  const [visible,    setVisible]    = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [duration,   setDuration]   = useState(0)
  const [loading,    setLoading]    = useState(false)
  const [volume,     setVolume]     = useState(1)

  const audioRef = useRef(new Audio())

  const obra = queue[index] ?? null

  // Sincroniza eventos do elemento Audio
  useEffect(() => {
    const el = audioRef.current

    const onTime     = () => setCurrentTime(el.currentTime)
    const onDuration = () => setDuration(el.duration || 0)
    const onEnded    = () => nextTrack()
    const onWaiting  = () => setLoading(true)
    const onCanPlay  = () => setLoading(false)
    const onPlay     = () => setPlaying(true)
    const onPause    = () => setPlaying(false)

    el.addEventListener('timeupdate',      onTime)
    el.addEventListener('loadedmetadata',  onDuration)
    el.addEventListener('ended',           onEnded)
    el.addEventListener('waiting',         onWaiting)
    el.addEventListener('canplay',         onCanPlay)
    el.addEventListener('play',            onPlay)
    el.addEventListener('pause',           onPause)

    return () => {
      el.removeEventListener('timeupdate',     onTime)
      el.removeEventListener('loadedmetadata', onDuration)
      el.removeEventListener('ended',          onEnded)
      el.removeEventListener('waiting',        onWaiting)
      el.removeEventListener('canplay',        onCanPlay)
      el.removeEventListener('play',           onPlay)
      el.removeEventListener('pause',          onPause)
    }
  }, [])

  // Carrega nova faixa quando o índice muda
  useEffect(() => {
    if (!obra) return
    loadTrack(obra)
  }, [index, obra?.id])

  // Volume
  useEffect(() => {
    audioRef.current.volume = volume
  }, [volume])

  async function loadTrack(obra, autoplay = true) {
    const el = audioRef.current
    el.pause()
    setCurrentTime(0)
    setDuration(0)
    setLoading(true)

    const url = await getAudioUrl(obra.audio_path)
    if (!url) { setLoading(false); return }

    el.src = url
    el.load()
    if (autoplay) {
      try { await el.play() } catch (_) {}
    }
    setLoading(false)
  }

  // API pública
  const playObra = useCallback(async (obraOuLista, idx = 0) => {
    const lista = Array.isArray(obraOuLista) ? obraOuLista : [obraOuLista]
    setQueue(lista)
    setIndex(idx)
    setVisible(true)
    setMinimized(false)
  }, [])

  const togglePlay = useCallback(() => {
    const el = audioRef.current
    if (el.paused) el.play().catch(() => {})
    else           el.pause()
  }, [])

  const seek = useCallback((time) => {
    audioRef.current.currentTime = time
    setCurrentTime(time)
  }, [])

  const nextTrack = useCallback(() => {
    setIndex(i => {
      const next = i + 1 < queue.length ? i + 1 : 0
      return next
    })
  }, [queue.length])

  const prevTrack = useCallback(() => {
    const el = audioRef.current
    // Se passou mais de 3s, volta ao início da faixa atual
    if (el.currentTime > 3) { seek(0); return }
    setIndex(i => (i - 1 + queue.length) % queue.length)
  }, [queue.length, seek])

  const close = useCallback(() => {
    audioRef.current.pause()
    audioRef.current.src = ''
    setVisible(false)
    setPlaying(false)
    setQueue([])
    setIndex(0)
  }, [])

  return (
    <PlayerContext.Provider value={{
      obra, queue, index, playing, minimized, visible,
      currentTime, duration, loading, volume,
      playObra, togglePlay, seek, nextTrack, prevTrack,
      close, setMinimized, setVolume,
    }}>
      {children}
    </PlayerContext.Provider>
  )
}

export const usePlayer = () => useContext(PlayerContext)
