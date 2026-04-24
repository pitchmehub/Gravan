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
  // Aleatório ligado por padrão (a fila já é montada embaralhada na Descoberta).
  const [shuffle,     setShuffle]    = useState(true)
  // 'off' | 'all' (repete a fila) | 'one' (repete a obra atual)
  const [repeat,      setRepeat]     = useState('off')

  const audioRef = useRef(new Audio())
  // Refs p/ que listeners do <audio> sempre leiam o valor mais recente
  // sem precisar reanexar a cada toggle.
  const shuffleRef = useRef(shuffle)
  const repeatRef  = useRef(repeat)
  useEffect(() => { shuffleRef.current = shuffle }, [shuffle])
  useEffect(() => { repeatRef.current  = repeat  }, [repeat])

  const obra = queue[index] ?? null

  useEffect(() => {
    const el = audioRef.current
    const onTime     = () => setCurrentTime(el.currentTime)
    const onDuration = () => setDuration(el.duration || 0)
    const onEnded    = () => {
      // Repeat-one: reinicia a mesma faixa
      if (repeatRef.current === 'one') {
        el.currentTime = 0
        el.play().catch(() => {})
        return
      }
      setIndex(i => {
        if (queue.length <= 1) {
          if (repeatRef.current === 'all') {
            el.currentTime = 0
            el.play().catch(() => {})
          }
          return i
        }
        if (shuffleRef.current) {
          let next = i
          while (next === i) next = Math.floor(Math.random() * queue.length)
          return next
        }
        if (i + 1 < queue.length) return i + 1
        return repeatRef.current === 'all' ? 0 : i
      })
    }
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
    const url = await getAudioUrl(obra.id)
    if (!url) { setLoading(false); return }
    el.src = url
    el.load()
    if (autoplay) { try { await el.play() } catch (_) {} }
    setLoading(false)
  }

  const playObra = useCallback(async (obraOuLista, idx = 0, opts = {}) => {
    const lista = Array.isArray(obraOuLista) ? obraOuLista : [obraOuLista]
    let fila = lista
    let inicio = idx
    if (opts.shuffle && lista.length > 1) {
      const start = lista[idx]
      const restantes = lista.filter((_, i) => i !== idx)
      for (let i = restantes.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1))
        ;[restantes[i], restantes[j]] = [restantes[j], restantes[i]]
      }
      fila = [start, ...restantes]
      inicio = 0
    }
    setQueue(fila)
    setIndex(inicio)
    setVisible(true)
    // No mobile, abrir já no modo minimizado (acima da bottom nav).
    // No desktop continua na barra inferior padrão.
    const isMobile = typeof window !== 'undefined' && window.innerWidth < 768
    setMinimized(isMobile)
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
    setIndex(i => {
      if (queue.length <= 1) return i
      if (shuffle) {
        let next = i
        while (next === i) next = Math.floor(Math.random() * queue.length)
        return next
      }
      return i + 1 < queue.length ? i + 1 : 0
    })
  }, [queue.length, shuffle])

  const toggleShuffle = useCallback(() => {
    setShuffle(s => !s)
  }, [])

  const cycleRepeat = useCallback(() => {
    setRepeat(r => (r === 'off' ? 'all' : r === 'all' ? 'one' : 'off'))
  }, [])

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
      shuffle, repeat,
      playObra, expandPlayer, togglePlay, seek,
      goToIndex, nextTrack, prevTrack, reorderQueue, removeFromQueue,
      toggleShuffle, cycleRepeat,
      close, setMinimized, setExpanded, setVolume,
    }}>
      {children}
    </PlayerContext.Provider>
  )
}

export const usePlayer = () => useContext(PlayerContext)
