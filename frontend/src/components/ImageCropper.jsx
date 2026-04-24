import React, { useEffect, useRef, useState } from 'react'

export default function ImageCropper({
  src,
  aspect = 1,
  shape = 'circle',
  outputWidth = 600,
  onCancel,
  onConfirm,
  title = 'Ajustar imagem',
}) {
  const containerRef = useRef(null)
  const imgRef = useRef(null)

  const [imgLoaded, setImgLoaded] = useState(false)
  const [natural, setNatural] = useState({ w: 0, h: 0 })
  const [containerSize, setContainerSize] = useState({ w: 400, h: 400 })

  const [scale, setScale] = useState(1)
  const [minScale, setMinScale] = useState(1)
  const [pos, setPos] = useState({ x: 0, y: 0 })

  const dragRef = useRef({ active: false, startX: 0, startY: 0, startPosX: 0, startPosY: 0 })

  useEffect(() => {
    function onResize() {
      const el = containerRef.current
      if (!el) return
      const w = Math.min(el.clientWidth, 480)
      const h = Math.round(w / aspect)
      setContainerSize({ w, h })
    }
    onResize()
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [aspect])

  useEffect(() => {
    if (!imgLoaded || !natural.w || !natural.h) return
    const fitX = containerSize.w / natural.w
    const fitY = containerSize.h / natural.h
    const fit = Math.max(fitX, fitY)
    setMinScale(fit)
    setScale(fit)
    setPos({ x: 0, y: 0 })
  }, [imgLoaded, natural, containerSize])

  function clampPos(nextPos, nextScale) {
    const imgW = natural.w * nextScale
    const imgH = natural.h * nextScale
    const maxX = Math.max(0, (imgW - containerSize.w) / 2)
    const maxY = Math.max(0, (imgH - containerSize.h) / 2)
    return {
      x: Math.max(-maxX, Math.min(maxX, nextPos.x)),
      y: Math.max(-maxY, Math.min(maxY, nextPos.y)),
    }
  }

  function handlePointerDown(e) {
    e.preventDefault()
    const point = e.touches ? e.touches[0] : e
    dragRef.current = {
      active: true,
      startX: point.clientX,
      startY: point.clientY,
      startPosX: pos.x,
      startPosY: pos.y,
    }
  }

  function handlePointerMove(e) {
    if (!dragRef.current.active) return
    const point = e.touches ? e.touches[0] : e
    const dx = point.clientX - dragRef.current.startX
    const dy = point.clientY - dragRef.current.startY
    setPos(clampPos({ x: dragRef.current.startPosX + dx, y: dragRef.current.startPosY + dy }, scale))
  }

  function handlePointerUp() {
    dragRef.current.active = false
  }

  function handleScaleChange(newScale) {
    const s = Math.max(minScale, Math.min(minScale * 4, newScale))
    setScale(s)
    setPos(p => clampPos(p, s))
  }

  function handleWheel(e) {
    e.preventDefault()
    const delta = e.deltaY < 0 ? 1.05 : 0.95
    handleScaleChange(scale * delta)
  }

  function gerar() {
    const outW = outputWidth
    const outH = Math.round(outW / aspect)
    const canvas = document.createElement('canvas')
    canvas.width = outW
    canvas.height = outH
    const ctx = canvas.getContext('2d')
    ctx.fillStyle = '#000'
    ctx.fillRect(0, 0, outW, outH)

    const imgW = natural.w * scale
    const imgH = natural.h * scale
    const imgLeft = (containerSize.w - imgW) / 2 + pos.x
    const imgTop = (containerSize.h - imgH) / 2 + pos.y

    const sx = (-imgLeft / scale)
    const sy = (-imgTop / scale)
    const sw = containerSize.w / scale
    const sh = containerSize.h / scale

    ctx.drawImage(imgRef.current, sx, sy, sw, sh, 0, 0, outW, outH)

    canvas.toBlob(blob => {
      onConfirm(blob)
    }, 'image/jpeg', 0.9)
  }

  return (
    <div
      onClick={e => { if (e.target === e.currentTarget) onCancel() }}
      style={{
        position: 'fixed', inset: 0, background: 'rgba(0,0,0,.7)',
        zIndex: 2000, display: 'flex', alignItems: 'center', justifyContent: 'center',
        padding: 20,
      }}
    >
      <div style={{
        background: '#fff', borderRadius: 14, padding: 20, maxWidth: 540, width: '100%',
        boxShadow: '0 20px 60px rgba(0,0,0,.4)',
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
          <h3 style={{ margin: 0, fontSize: 16, fontWeight: 700 }}>{title}</h3>
          <button onClick={onCancel} style={{
            background: 'none', border: 'none', fontSize: 22, cursor: 'pointer', color: '#71717A', lineHeight: 1,
          }}>×</button>
        </div>

        <p style={{ fontSize: 12, color: '#71717A', marginBottom: 12 }}>
          Arraste para mover · Use o controle abaixo (ou a roda do mouse) para ajustar o zoom.
        </p>

        <div
          ref={containerRef}
          onMouseDown={handlePointerDown}
          onMouseMove={handlePointerMove}
          onMouseUp={handlePointerUp}
          onMouseLeave={handlePointerUp}
          onTouchStart={handlePointerDown}
          onTouchMove={handlePointerMove}
          onTouchEnd={handlePointerUp}
          onWheel={handleWheel}
          style={{
            width: '100%', height: containerSize.h, overflow: 'hidden',
            background: '#09090B', position: 'relative',
            borderRadius: shape === 'circle' ? '50%' : 8,
            cursor: dragRef.current.active ? 'grabbing' : 'grab',
            margin: '0 auto', maxWidth: containerSize.w,
            userSelect: 'none', touchAction: 'none',
          }}
        >
          {/* eslint-disable-next-line jsx-a11y/alt-text */}
          <img
            ref={imgRef}
            src={src}
            onLoad={e => {
              setNatural({ w: e.target.naturalWidth, h: e.target.naturalHeight })
              setImgLoaded(true)
            }}
            draggable={false}
            style={{
              position: 'absolute',
              left: '50%', top: '50%',
              width: natural.w * scale,
              height: natural.h * scale,
              transform: `translate(calc(-50% + ${pos.x}px), calc(-50% + ${pos.y}px))`,
              pointerEvents: 'none',
              maxWidth: 'none', maxHeight: 'none',
            }}
          />
        </div>

        <div style={{ marginTop: 14, display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 11, color: '#71717A' }}>Zoom</span>
          <input
            type="range"
            min={minScale}
            max={minScale * 4}
            step={(minScale * 3) / 100 || 0.01}
            value={scale}
            onChange={e => handleScaleChange(parseFloat(e.target.value))}
            style={{ flex: 1 }}
          />
        </div>

        <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end', marginTop: 16 }}>
          <button
            type="button"
            onClick={onCancel}
            style={{
              padding: '10px 16px', fontSize: 13, fontWeight: 600,
              background: '#fff', color: '#71717A',
              border: '1px solid #E5E7EB', borderRadius: 8, cursor: 'pointer',
            }}
          >
            Cancelar
          </button>
          <button
            type="button"
            onClick={gerar}
            disabled={!imgLoaded}
            style={{
              padding: '10px 18px', fontSize: 13, fontWeight: 700,
              background: imgLoaded ? '#09090B' : '#A1A1AA', color: '#fff',
              border: 'none', borderRadius: 8,
              cursor: imgLoaded ? 'pointer' : 'wait',
            }}
          >
            ✓ Aplicar
          </button>
        </div>
      </div>
    </div>
  )
}
