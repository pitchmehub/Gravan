import React, { createContext, useContext, useRef, useState, useEffect, useCallback } from 'react'
import { getAudioUrl } from '../lib/audioUrl'

const PlayerContext = createContext(null)

export function PlayerProvider({ children }) {
  const [queue,       setQueue]      = useState([])
  const [index,       setIndex]      = useState(0)
  const [playing,     setPlaying]    = useState(false)
  const [minimized,   setMinimized]  = useState(false)
  const [expanded,    setExpanded]   = useState(false)
  const [visible,     setVisible]    = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [duration,    setDuration]   = useState(0)
  const [loading,     setLoading]    = useState(false)
  const [volume,      setVolume]     = useState(1)

  const audioRef = useRef(new Audio())

  const obra = queue[index] ?? null

  useEffect(() => {
    const el = audioRef.current
    const onTime     = () => setCurrentTime(el.currentTime)
    const onDuration = () => setDuration(el.duration || 0)
    const onEnded    = () => setIndex(i => (i + 1 < queue.length ? i + 1 : 0))
    const onWaiting  = () => setLoading(true)
    const onCanPlay  = () => setLoading(false)
    const onPlay     = () => setPlaying(true)
    const onPause    = () => setPlaying(false)

    el.addEventListener('timeupdate',     onTime)
    el.addEventListener('loadedmetadata', onDuration)
    el.addEventListener('ended',          onEnded)
    el.addEventListener('waiting',        onWaiting)
    el.addEventListener('canplay',        onCanPlay)
    el.addEventListener('play',           onPlay)
    el.addEventListener('pause',          onPause)

    return () => {
      el.removeEventListener('timeupdate',     onTime)
      el.removeEventListener('loadedmetadata', onDuration)
      el.removeEventListener('ended',          onEnded)
      el.removeEventListener('waiting',        onWaiting)
      el.removeEventListener('canplay',        onCanPlay)
      el.removeEventListener('play',           onPlay)
      el.removeEventListener('pause',          onPause)
    }
  }, [queue.length])

  useEffect(() => {
    if (!obra) return
    loadTrack(obra)
  }, [index, obra?.id])

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
    if (autoplay) { try { await el.play() } catch (_) {} }
    setLoading(false)
  }

  const playObra = useCallback(async (obraOuLista, idx = 0) => {
    const lista = Array.isArray(obraOuLista) ? obraOuLista : [obraOuLista]
    setQueue(lista)
    setIndex(idx)
    setVisible(true)
    setMinimized(false)
    setExpanded(false)
  }, [])

  const expandPlayer = useCallback(() => {
    setExpanded(true)
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

  const goToIndex = useCallback((i) => {
    setIndex(i)
  }, [])

  const nextTrack = useCallback(() => {
    setIndex(i => (i + 1 < queue.length ? i + 1 : 0))
  }, [queue.length])

  const prevTrack = useCallback(() => {
    const el = audioRef.current
    if (el.currentTime > 3) { seek(0); return }
    setIndex(i => (i - 1 + queue.length) % queue.length)
  }, [queue.length, seek])

  // Move item in queue, adjusts current index accordingly
  const reorderQueue = useCallback((from, to) => {
    if (from === to) return
    setQueue(q => {
      const arr = [...q]
      const [item] = arr.splice(from, 1)
      arr.splice(to, 0, item)
      return arr
    })
    setIndex(i => {
      if (i === from) return to
      if (from < to && i > from && i <= to) return i - 1
      if (from > to && i >= to && i < from) return i + 1
      return i
    })
  }, [])

  // Remove item from queue, keep playing if possible
  const removeFromQueue = useCallback((idx) => {
    setQueue(q => {
      if (q.length <= 1) return q
      const arr = [...q]
      arr.splice(idx, 1)
      return arr
    })
    setIndex(i => {
      if (idx < i) return i - 1
      if (idx === i) return Math.max(0, i - 1)
      return i
    })
  }, [])

  const close = useCallback(() => {
    audioRef.current.pause()
    audioRef.current.src = ''
    setVisible(false)
    setPlaying(false)
    setQueue([])
    setIndex(0)
    setExpanded(false)
  }, [])

  return (
    <PlayerContext.Provider value={{
      obra, queue, index, playing, minimized, expanded, visible,
      currentTime, duration, loading, volume,
      playObra, expandPlayer, togglePlay, seek,
      goToIndex, nextTrack, prevTrack, reorderQueue, removeFromQueue,
      close, setMinimized, setExpanded, setVolume,
    }}>
      {children}
    </PlayerContext.Provider>
  )
}

export const usePlayer = () => useContext(PlayerContext)
