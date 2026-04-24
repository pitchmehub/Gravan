import React, { useEffect, useState } from 'react'
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
 * Mostra capa, compositores, botão de tocar (opcional), ler letra e
 * licenciar composição.
 *
 * Props:
 *  - obra: objeto da obra (com id, nome, genero, titular_nome, audio_path)
 *  - onClose: () => void
 *  - onPlay?: (obra) => void  (opcional — esconde o botão se não passado)
 *  - isPlaying?: boolean
 *  - isActive?: boolean
 */
export default function FichaTecnica({ obra, onClose, onPlay, isPlaying, isActive }) {
  const navigate = useNavigate()
  const [coautores, setCoautores] = useState([])
  const [letraOpen, setLetraOpen] = useState(false)
  const [letra, setLetra] = useState(null)
  const [loadingLetra, setLoadingLetra] = useState(false)

  useEffect(() => {
    function onKey(e) {
      if (e.key === 'Escape') {
        if (letraOpen) setLetraOpen(false)
        else onClose()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose, letraOpen])

  useEffect(() => {
    async function load() {
      const { data } = await supabase
        .from('coautorias')
        .select('share_pct, is_titular, perfis(id, nome, nome_artistico, avatar_url, nivel)')
        .eq('obra_id', obra.id)
      setCoautores(data ?? [])
    }
    load()
  }, [obra.id])

  async function abrirLetra() {
    setLetraOpen(true)
    if (letra !== null) return
    setLoadingLetra(true)
    try {
      const { data } = await supabase
        .from('obras')
        .select('letra')
        .eq('id', obra.id)
        .maybeSingle()
      setLetra(data?.letra || '')
    } catch (_) {
      setLetra('')
    } finally {
      setLoadingLetra(false)
    }
  }

  return (
    <div className="dc-modal-overlay" onClick={e => { if (e.target === e.currentTarget) onClose() }}>
      <div className="dc-modal">
        <button className="dc-modal-close" onClick={onClose}>×</button>

        <div className="dc-modal-header" style={{ background: grad(obra.id) }}>
          <div className="dc-modal-cover">♪</div>
          <div>
            <div className="dc-modal-genre">{obra.genero || 'Composição'}</div>
            <div className="dc-modal-nome">{obra.nome}</div>
            <div className="dc-modal-autor">{obra.titular_nome}</div>
          </div>
        </div>

        {obra.audio_path && onPlay && (
          <div className="dc-modal-actions">
            <button className="dc-modal-play-btn" onClick={() => onPlay(obra)}>
              {isPlaying ? '⏸' : '▶'}
            </button>
            <span className="dc-modal-action-label">
              {isActive && isPlaying ? 'Reproduzindo…' : 'Ouvir preview'}
            </span>
          </div>
        )}

        <div className="dc-modal-actions" style={{ borderTop: 0, paddingTop: 0 }}>
          <button
            type="button"
            onClick={abrirLetra}
            style={{
              width: '100%', padding: '12px 16px',
              background: '#09090B', color: '#fff',
              border: 'none', borderRadius: 8,
              fontSize: 13, fontWeight: 700, letterSpacing: 0.4,
              cursor: 'pointer', display: 'flex',
              alignItems: 'center', justifyContent: 'center', gap: 8,
            }}>
            <span style={{ fontSize: 15 }}>📖</span> Ler letra
          </button>
        </div>

        {letraOpen && (
          <div
            className="dc-modal-overlay"
            onClick={e => { if (e.target === e.currentTarget) setLetraOpen(false) }}
            style={{ zIndex: 9999 }}>
            <div className="dc-modal" style={{ maxWidth: 640, display: 'flex', flexDirection: 'column', maxHeight: '85vh' }}>
              <button className="dc-modal-close" onClick={() => setLetraOpen(false)}>×</button>
              <div className="dc-modal-header" style={{ background: grad(obra.id) }}>
                <div className="dc-modal-cover">📖</div>
                <div>
                  <div className="dc-modal-genre">Letra completa</div>
                  <div className="dc-modal-nome">{obra.nome}</div>
                  <div className="dc-modal-autor">{obra.titular_nome || obra.compositor_nome || ''}</div>
                </div>
              </div>
              <div
                style={{
                  padding: '20px 24px',
                  overflowY: 'auto',
                  flex: 1,
                  whiteSpace: 'pre-wrap',
                  fontSize: 15,
                  lineHeight: 1.7,
                  color: '#1F2937',
                  fontFamily: 'Georgia, "Times New Roman", serif',
                }}>
                {loadingLetra
                  ? <div style={{ color: '#6B7280', textAlign: 'center', padding: 24 }}>Carregando letra…</div>
                  : (letra && letra.trim())
                    ? letra
                    : <div style={{ color: '#6B7280', textAlign: 'center', padding: 24 }}>
                        Esta obra ainda não tem letra cadastrada.
                      </div>
                }
              </div>
            </div>
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
                      {c.is_titular && <span className="dc-titular-badge">Titular</span>}
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
    </div>
  )
}
