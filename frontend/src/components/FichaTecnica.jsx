import React, { useEffect, useState } from 'react'
import { createPortal } from 'react-dom'
import { useNavigate } from 'react-router-dom'
import { supabase } from '../lib/supabase'
import { useAuth } from '../contexts/AuthContext'
import OfertaModal from './OfertaModal'
import UpgradeProModal from './UpgradeProModal'
import SeloPro, { isPerfilPro } from './SeloPro'
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
 * Mostra capa grande, nome, gênero, compositores e botão de licenciar.
 *
 * Props:
 *  - obra: objeto da obra (com id, nome, genero, cover_url)
 *  - onClose: () => void
 *  - onPlay?: (obra) => void  (mantido por compatibilidade — não é usado visualmente)
 *  - isPlaying?: boolean
 *  - isActive?: boolean
 */
export default function FichaTecnica({ obra, onClose }) {
  const navigate = useNavigate()
  const { perfil } = useAuth()
  const isInterprete = perfil?.role === 'interprete'
  const isMeuPro = isPerfilPro(perfil)
  const [coautores, setCoautores] = useState([])
  const [titularPro, setTitularPro] = useState(false)
  const [showOferta, setShowOferta] = useState(false)
  const [showUpgrade, setShowUpgrade] = useState(false)
  const isExclusiva = !!obra?.is_exclusive

  useEffect(() => {
    function onKey(e) { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  useEffect(() => {
    async function load() {
      const { data } = await supabase
        .from('coautorias')
        .select('share_pct, perfis(id, nome, nome_artistico, avatar_url, nivel, plano, status_assinatura)')
        .eq('obra_id', obra.id)
      setCoautores(data ?? [])
    }
    load()
  }, [obra.id])

  useEffect(() => {
    async function checkPro() {
      if (!obra?.titular_id) return
      const { data } = await supabase
        .from('perfis')
        .select('plano, status_assinatura')
        .eq('id', obra.titular_id)
        .maybeSingle()
      const pro = data?.plano === 'PRO'
        && ['ativa', 'cancelada', 'past_due'].includes(data?.status_assinatura)
      setTitularPro(!!pro)
    }
    checkPro()
  }, [obra?.titular_id])

  return createPortal(
    <div className="dc-modal-overlay" onClick={e => { if (e.target === e.currentTarget) onClose() }}>
      <div className="dc-modal">
        <button className="dc-modal-close" onClick={onClose}>×</button>

        {/* Capa grande no topo (mesmo formato do card da Descoberta) */}
        <div className="ft-hero" style={{ background: grad(obra.id) }}>
          {obra.cover_url ? (
            <img
              src={obra.cover_url}
              alt={obra.nome}
              className="ft-hero-img"
              onError={e => { e.currentTarget.style.display = 'none' }}
            />
          ) : (
            <span className="ft-hero-iniciais">{(obra.nome || '?').charAt(0).toUpperCase()}</span>
          )}
        </div>

        <div className="ft-titulo">
          <div className="dc-modal-genre">
            {obra.genero || 'Composição'}
            {isExclusiva && (
              <span style={{
                marginLeft: 8, padding: '2px 8px', borderRadius: 99,
                background: '#7c3aed', color: '#fff', fontSize: 11, fontWeight: 700,
                letterSpacing: 0.4, textTransform: 'uppercase',
              }}>
                Exclusiva
              </span>
            )}
          </div>
          <div className="dc-modal-nome">{obra.nome}</div>
        </div>

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
                         style={{
                           ...(perfilId ? { color: '#0C447C', textDecoration: 'underline' } : {}),
                           display: 'inline-flex', alignItems: 'center',
                         }}>
                      {c.perfis?.nome_artistico || c.perfis?.nome}
                      <SeloPro ativo={isPerfilPro(c.perfis)} size="sm" />
                    </div>
                    <div className="dc-modal-comp-nivel">{c.perfis?.nivel}</div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        <div className="dc-modal-buy-bar" style={{ justifyContent: 'center', flexDirection: 'column', gap: 8 }}>
          {isExclusiva ? (
            <div style={{
              padding: '12px 16px', borderRadius: 8, background: '#f5f3ff',
              color: '#5b21b6', fontSize: 13, textAlign: 'center', fontWeight: 600,
            }}>
              Esta obra está sob exclusividade até{' '}
              {obra.exclusive_until
                ? new Date(obra.exclusive_until).toLocaleDateString('pt-BR')
                : '—'}.
            </div>
          ) : (
            <>
              <button
                className="dc-modal-buy-btn"
                style={{ width: '100%' }}
                onClick={() => { onClose(); navigate(`/comprar/${obra.id}`) }}
              >
                Licenciar Composição
              </button>
              <button
                data-testid="btn-fazer-oferta"
                onClick={() => {
                  if (isMeuPro) setShowOferta(true)
                  else setShowUpgrade(true)
                }}
                style={{
                  width: '100%', padding: '11px 16px', borderRadius: 8,
                  background: '#fff', border: '2px solid #0C447C', color: '#0C447C',
                  fontWeight: 700, fontSize: 14, cursor: 'pointer',
                  display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: 8,
                }}
                title={isMeuPro ? '' : 'Disponível para assinantes PRO'}
              >
                Fazer oferta
                {!isMeuPro && (
                  <span style={{
                    padding: '2px 6px', borderRadius: 4,
                    background: 'linear-gradient(135deg, #0C447C, #378ADD)',
                    color: '#fff', fontSize: 9, fontWeight: 800, letterSpacing: 0.8,
                  }}>
                    PRO
                  </span>
                )}
              </button>
            </>
          )}
        </div>
      </div>
      {showOferta && (
        <OfertaModal
          obra={{ ...obra, titular_pro: titularPro }}
          onClose={() => setShowOferta(false)}
          onCriada={() => { setShowOferta(false); navigate('/ofertas') }}
        />
      )}
      <UpgradeProModal
        open={showUpgrade}
        onClose={() => setShowUpgrade(false)}
        titulo="Fazer ofertas é exclusivo do plano PRO"
        mensagem="Negocie diretamente com compositores, envie contrapropostas e desbloqueie licenciamento com exclusividade. Tudo a partir de R$ 29,90/mês."
        ctaLabel="Assinar PRO e fazer ofertas"
      />
    </div>,
    document.body
  )
}
