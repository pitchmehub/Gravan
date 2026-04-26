import React, { useEffect, useState } from 'react'
import { createPortal } from 'react-dom'
import { useNavigate } from 'react-router-dom'
import { supabase } from '../lib/supabase'
import '../pages/Descoberta.css'

const GRADIENTS = [
  'linear-gradient(135deg,#083257,#09090B)',
  'linear-gradient(135deg,#0F6E56,#1D9E75)',
  'linear-gradient(135deg,#854F0B,#EF9F27)',
  'linear-gradient(135deg,#185FA5,#378ADD)',
  'linear-gradient(135deg,#993556,#D4537E)',
  'linear-gradient(135deg,#09090B,#3F3F46)',
]
const grad = id => GRADIENTS[(id?.charCodeAt(0) ?? 0) % GRADIENTS.length]

/**
 * Modal de Ficha Técnica de uma obra.
 * Mostra capa, compositores, botão de tocar (opcional) e licenciar composição.
 *
 * Props:
 *  - obra: objeto da obra (com id, nome, genero, audio_path)
 *  - onClose: () => void
 *  - onPlay?: (obra) => void  (opcional — esconde o botão se não passado)
 *  - isPlaying?: boolean
 *  - isActive?: boolean
 */
export default function FichaTecnica({ obra, onClose, onPlay, isPlaying, isActive }) {
  const navigate = useNavigate()
  const [coautores, setCoautores] = useState([])

  useEffect(() => {
    function onKey(e) { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  useEffect(() => {
    async function load() {
      const { data } = await supabase
        .from('coautorias')
        .select('share_pct, perfis(id, nome, nome_artistico, avatar_url, nivel)')
        .eq('obra_id', obra.id)
      setCoautores(data ?? [])
    }
    load()
  }, [obra.id])

  return createPortal(
    <div className="dc-modal-overlay" onClick={e => { if (e.target === e.currentTarget) onClose() }}>
      <div className="dc-modal">
        <button className="dc-modal-close" onClick={onClose}>×</button>

        <div className="dc-modal-header" style={{ background: grad(obra.id) }}>
          <div className="dc-modal-cover">{(obra.nome || '?').charAt(0).toUpperCase()}</div>
          <div>
            <div className="dc-modal-genre">{obra.genero || 'Composição'}</div>
            <div className="dc-modal-nome">{obra.nome}</div>
          </div>
        </div>

        {obra.audio_path && onPlay && (
          <div className="dc-modal-actions">
            <button className="dc-modal-play-btn" onClick={() => onPlay(obra)} aria-label={isPlaying ? 'Pausar' : 'Tocar'}>
              {isPlaying
                ? <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="4" width="4" height="16" rx="1"/><rect x="14" y="4" width="4" height="16" rx="1"/></svg>
                : <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><polygon points="5,3 19,12 5,21" /></svg>
              }
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
                         style={perfilId ? { color: '#0C447C', textDecoration: 'underline' } : undefined}>
                      {c.perfis?.nome_artistico || c.perfis?.nome}
                    </div>
                    <div className="dc-modal-comp-nivel">{c.perfis?.nivel}</div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        <div className="dc-modal-buy-bar" style={{ justifyContent: 'center' }}>
          <button
            className="dc-modal-buy-btn"
            style={{ width: '100%' }}
            onClick={() => { onClose(); navigate(`/comprar/${obra.id}`) }}
          >
            Licenciar composição
          </button>
        </div>
      </div>
    </div>,
    document.body
  )
}
