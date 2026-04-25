import React from 'react'

/**
 * Header estilo Spotify reutilizável:
 *  - Capa de fundo (com fade para branco nas bordas/baixo)
 *  - Avatar circular sobreposto à capa (não embaixo dela)
 *  - Nome grande, badge de tipo, contagem de obras, bio
 */
export default function ArtistaHero({
  perfil,
  totalObras,
  fallbackGrad = 'linear-gradient(135deg, #083257, #09090B)',
  rightSlot = null,
  onBack = null,
}) {
  if (!perfil) return null
  const nomeExibicao = perfil.nome_artistico || perfil.nome
  const iniciais = (perfil.nome || '?').split(' ').slice(0, 2).map(n => n[0]).join('').toUpperCase()
  const tipo = perfil.role === 'publisher' ? 'Editora'
             : perfil.role === 'compositor' ? 'Artista'
             : (perfil.role || '')

  return (
    <div style={{ position: 'relative' }}>
      {/* Camada da capa */}
      <div style={{
        position: 'relative',
        height: 220,
        background: perfil.capa_url
          ? `url(${perfil.capa_url}) center/cover no-repeat`
          : fallbackGrad,
      }}>
        {/* Escurecimento sutil para legibilidade */}
        <div style={{
          position: 'absolute', inset: 0,
          background: 'linear-gradient(180deg, rgba(0,0,0,.10) 0%, rgba(0,0,0,.35) 100%)',
        }} />

        {/* Fade para branco nas laterais (suave) */}
        <div style={{
          position: 'absolute', top: 0, bottom: 0, left: 0, width: 50,
          background: 'linear-gradient(90deg, rgba(255,255,255,.55) 0%, rgba(255,255,255,0) 100%)',
          pointerEvents: 'none',
        }} />
        <div style={{
          position: 'absolute', top: 0, bottom: 0, right: 0, width: 50,
          background: 'linear-gradient(270deg, rgba(255,255,255,.55) 0%, rgba(255,255,255,0) 100%)',
          pointerEvents: 'none',
        }} />
        {/* Fade para branco na base (suave) */}
        <div style={{
          position: 'absolute', left: 0, right: 0, bottom: 0, height: 60,
          background: 'linear-gradient(180deg, rgba(255,255,255,0) 0%, rgba(255,255,255,.85) 100%)',
          pointerEvents: 'none',
        }} />

        {onBack && (
          <button
            onClick={onBack}
            style={{
              position: 'absolute', top: 16, left: 16, zIndex: 3,
              background: 'rgba(0,0,0,.55)', color: '#fff',
              border: 'none', borderRadius: 99, padding: '6px 14px',
              fontSize: 12, fontWeight: 600, cursor: 'pointer',
              backdropFilter: 'blur(4px)',
            }}>
            ← Voltar
          </button>
        )}

        {rightSlot && (
          <div style={{
            position: 'absolute', top: 16, right: 16, zIndex: 3,
            display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 6,
          }}>
            {rightSlot}
          </div>
        )}
      </div>

      {/* Bloco de identidade — avatar SOBRE a capa */}
      <div style={{
        position: 'relative',
        margin: '-56px 24px 0',
        display: 'flex', alignItems: 'flex-end', gap: 16,
        flexWrap: 'wrap',
        zIndex: 2,
      }}>
        <div style={{
          width: 96, height: 96, borderRadius: '50%',
          background: perfil.avatar_url ? '#fff' : fallbackGrad,
          color: '#fff',
          overflow: 'hidden', flexShrink: 0,
          border: '4px solid #fff',
          boxShadow: '0 8px 22px rgba(0,0,0,.22)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 32, fontWeight: 800,
        }}>
          {perfil.avatar_url
            ? <img src={perfil.avatar_url} alt={nomeExibicao}
                   style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
            : iniciais}
        </div>

        <div style={{ flex: 1, minWidth: 200, paddingBottom: 4 }}>
          <div style={{
            fontSize: 10, fontWeight: 700, color: '#71717A',
            textTransform: 'uppercase', letterSpacing: 1.2,
          }}>
            {tipo}
          </div>
          <h1 style={{
            fontSize: 'clamp(22px, 4vw, 34px)',
            fontWeight: 900, margin: '2px 0 0',
            lineHeight: 1.1, letterSpacing: -.8,
            color: '#09090B',
          }}>
            {nomeExibicao}
          </h1>
          <div style={{
            fontSize: 12, color: '#3F3F46', marginTop: 6,
            display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap',
          }}>
            {perfil.nivel && <><span style={{ fontWeight: 600 }}>{perfil.nivel}</span><span>·</span></>}
            <span>{totalObras} obra{totalObras !== 1 ? 's' : ''}</span>
          </div>
          {perfil.bio && (
            <p style={{
              fontSize: 12.5, color: '#3F3F46', marginTop: 8,
              maxWidth: 640, lineHeight: 1.5,
            }}>
              {perfil.bio}
            </p>
          )}
        </div>
      </div>
    </div>
  )
}

/**
 * Lista vertical de obras estilo Spotify.
 *
 * Modos de uso:
 *   1) Modo player (preferido): passar onPlay + onShowFicha.
 *      - 1º clique numa linha: começa a tocar (modo minimizado).
 *      - 2º clique na mesma obra: abre a ficha técnica.
 *      - O botão da direita vira play/pause na obra ativa.
 *   2) Modo legado: passar onSelect + ctaLabel.
 *      - Clique na linha ou no botão chama onSelect(obra).
 */
export function ObrasLista({
  obras,
  getGrad,
  onSelect,
  ctaLabel = 'Licenciar',
  onPlay,
  onShowFicha,
  currentObraId = null,
  isPlaying = false,
  compact = false,
}) {
  const SZ = compact ? {
    cols: '22px 36px 1fr auto',
    gap: 8,
    rowPad: '5px 8px',
    rowRadius: 6,
    idxFs: 11,
    cover: 36,
    coverRadius: 5,
    coverFs: 14,
    titleFs: 13,
    subFs: 11,
    btn: 26,
    iconSz: 11,
    ctaPad: '5px 10px',
    ctaFs: 11,
  } : {
    cols: '32px 56px 1fr auto',
    gap: 16,
    rowPad: '10px 12px',
    rowRadius: 8,
    idxFs: 13,
    cover: 48,
    coverRadius: 6,
    coverFs: 18,
    titleFs: 15,
    subFs: 12,
    btn: 32,
    iconSz: 13,
    ctaPad: '8px 16px',
    ctaFs: 12,
  }
  if (!obras || obras.length === 0) {
    return (
      <div style={{
        padding: 32, color: '#71717A', fontSize: 14, textAlign: 'center',
      }}>
        Nenhuma obra publicada ainda.
      </div>
    )
  }

  const modoPlayer = typeof onPlay === 'function'

  function handleRowClick(o) {
    if (modoPlayer) {
      const isActive = currentObraId === o.id
      if (isActive) onShowFicha?.(o)
      else onPlay(o)
      return
    }
    onSelect?.(o)
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column' }}>
      {obras.map((o, i) => {
        const isActive = modoPlayer && currentObraId === o.id
        return (
          <div
            key={o.id}
            onClick={() => handleRowClick(o)}
            onMouseEnter={e => e.currentTarget.style.background = isActive ? '#F4F4F5' : '#FAFAFA'}
            onMouseLeave={e => e.currentTarget.style.background = isActive ? '#FAFAFA' : 'transparent'}
            style={{
              display: 'grid',
              gridTemplateColumns: SZ.cols,
              alignItems: 'center', gap: SZ.gap,
              padding: SZ.rowPad,
              borderRadius: SZ.rowRadius,
              cursor: 'pointer',
              transition: 'background 0.15s',
              background: isActive ? '#FAFAFA' : 'transparent',
            }}>
            <div style={{
              color: isActive ? '#E11D48' : '#71717A',
              fontSize: SZ.idxFs, fontWeight: 600, textAlign: 'center',
            }}>
              {isActive && isPlaying
                ? <svg width={SZ.iconSz - 1} height={SZ.iconSz - 1} viewBox="0 0 24 24" fill="currentColor" style={{ display: 'inline-block' }}><polygon points="5,3 19,12 5,21" /></svg>
                : i + 1}
            </div>
            <div style={{
              width: SZ.cover, height: SZ.cover, borderRadius: SZ.coverRadius,
              background: getGrad ? getGrad(o.id) : '#09090B',
              color: '#fff',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: SZ.coverFs, fontWeight: 700, flexShrink: 0,
              backgroundImage: o.cover_url ? `url(${o.cover_url})` : undefined,
              backgroundSize: 'cover',
              backgroundPosition: 'center',
              overflow: 'hidden',
            }}>
              {!o.cover_url && (o.nome || '?').charAt(0).toUpperCase()}
            </div>
            <div style={{ minWidth: 0 }}>
              <div style={{
                fontSize: SZ.titleFs, fontWeight: 600,
                color: isActive ? '#E11D48' : '#09090B',
                whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
              }}>
                {o.nome}
              </div>
              <div style={{ fontSize: SZ.subFs, color: '#71717A', marginTop: compact ? 1 : 2 }}>
                {o.genero || '—'}
              </div>
            </div>
            {modoPlayer ? (
              <button
                onClick={e => { e.stopPropagation(); onPlay(o) }}
                aria-label={isActive && isPlaying ? 'Pausar' : 'Tocar'}
                style={{
                  background: isActive ? '#E11D48' : '#09090B', color: '#fff',
                  border: 'none', borderRadius: '50%',
                  width: SZ.btn, height: SZ.btn,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  cursor: 'pointer', whiteSpace: 'nowrap', flexShrink: 0,
                }}>
                {isActive && isPlaying
                  ? <svg width={SZ.iconSz} height={SZ.iconSz} viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="4" width="4" height="16" rx="1"/><rect x="14" y="4" width="4" height="16" rx="1"/></svg>
                  : <svg width={SZ.iconSz} height={SZ.iconSz} viewBox="0 0 24 24" fill="currentColor"><polygon points="5,3 19,12 5,21" /></svg>
                }
              </button>
            ) : (
              <button
                onClick={e => { e.stopPropagation(); onSelect?.(o) }}
                style={{
                  background: '#09090B', color: '#fff',
                  border: 'none', borderRadius: 99,
                  padding: SZ.ctaPad, fontSize: SZ.ctaFs, fontWeight: 700,
                  cursor: 'pointer', whiteSpace: 'nowrap',
                }}>
                {ctaLabel}
              </button>
            )}
          </div>
        )
      })}
    </div>
  )
}
