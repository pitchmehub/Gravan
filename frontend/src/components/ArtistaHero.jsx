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
        height: 340,
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
          position: 'absolute', left: 0, right: 0, bottom: 0, height: 80,
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
        margin: '-90px 32px 0',
        display: 'flex', alignItems: 'flex-end', gap: 22,
        flexWrap: 'wrap',
        zIndex: 2,
      }}>
        <div style={{
          width: 160, height: 160, borderRadius: '50%',
          background: perfil.avatar_url ? '#fff' : fallbackGrad,
          color: '#fff',
          overflow: 'hidden', flexShrink: 0,
          border: '6px solid #fff',
          boxShadow: '0 12px 30px rgba(0,0,0,.25)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 52, fontWeight: 800,
        }}>
          {perfil.avatar_url
            ? <img src={perfil.avatar_url} alt={nomeExibicao}
                   style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
            : iniciais}
        </div>

        <div style={{ flex: 1, minWidth: 240, paddingBottom: 8 }}>
          <div style={{
            fontSize: 11, fontWeight: 700, color: '#71717A',
            textTransform: 'uppercase', letterSpacing: 1.5,
          }}>
            {tipo}
          </div>
          <h1 style={{
            fontSize: 'clamp(34px, 6vw, 64px)',
            fontWeight: 900, margin: '4px 0 0',
            lineHeight: 1.05, letterSpacing: -1.5,
            color: '#09090B',
          }}>
            {nomeExibicao}
          </h1>
          {perfil.nome_artistico && perfil.nome_artistico !== perfil.nome && (
            <div style={{ fontSize: 13, color: '#71717A', marginTop: 6 }}>
              {perfil.nome}
            </div>
          )}
          <div style={{
            fontSize: 13, color: '#3F3F46', marginTop: 10,
            display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap',
          }}>
            {perfil.nivel && <><span style={{ fontWeight: 600 }}>{perfil.nivel}</span><span>·</span></>}
            <span>{totalObras} obra{totalObras !== 1 ? 's' : ''}</span>
          </div>
          {perfil.bio && (
            <p style={{
              fontSize: 13.5, color: '#3F3F46', marginTop: 14,
              maxWidth: 640, lineHeight: 1.55,
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
 * Lista vertical de obras estilo Spotify, com numeração + thumbnail + botão.
 */
export function ObrasLista({ obras, onSelect, getGrad, ctaLabel = 'Licenciar' }) {
  if (!obras || obras.length === 0) {
    return (
      <div style={{
        padding: 32, color: '#71717A', fontSize: 14, textAlign: 'center',
      }}>
        Nenhuma obra publicada ainda.
      </div>
    )
  }
  return (
    <div style={{ display: 'flex', flexDirection: 'column' }}>
      {obras.map((o, i) => (
        <div
          key={o.id}
          onClick={() => onSelect?.(o)}
          onMouseEnter={e => e.currentTarget.style.background = '#FAFAFA'}
          onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
          style={{
            display: 'grid',
            gridTemplateColumns: '32px 56px 1fr auto',
            alignItems: 'center', gap: 16,
            padding: '10px 12px',
            borderRadius: 8,
            cursor: 'pointer',
            transition: 'background 0.15s',
          }}>
          <div style={{ color: '#71717A', fontSize: 14, fontWeight: 600, textAlign: 'center' }}>
            {i + 1}
          </div>
          <div style={{
            width: 56, height: 56, borderRadius: 6,
            background: getGrad ? getGrad(o.id) : '#09090B',
            color: '#fff',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 22, flexShrink: 0,
          }}>
            ♪
          </div>
          <div style={{ minWidth: 0 }}>
            <div style={{
              fontSize: 15, fontWeight: 600, color: '#09090B',
              whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
            }}>
              {o.nome}
            </div>
            <div style={{ fontSize: 12, color: '#71717A', marginTop: 2 }}>
              {o.genero || '—'}
            </div>
          </div>
          <button
            onClick={e => { e.stopPropagation(); onSelect?.(o) }}
            style={{
              background: '#09090B', color: '#fff',
              border: 'none', borderRadius: 99,
              padding: '8px 16px', fontSize: 12, fontWeight: 700,
              cursor: 'pointer', whiteSpace: 'nowrap',
            }}>
            {ctaLabel}
          </button>
        </div>
      ))}
    </div>
  )
}
