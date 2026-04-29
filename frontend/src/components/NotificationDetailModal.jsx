import React, { useEffect, useState } from 'react'
import { createPortal } from 'react-dom'
import { useNavigate } from 'react-router-dom'
import { api } from '../lib/api'
import { useAuth } from '../contexts/AuthContext'
import {
  IconBell, IconMusic, IconDocument, IconCheckCircle, IconKey,
  IconTag, IconDownload, IconWallet, IconXCircle,
} from './Icons'
import './NotificationDetailModal.css'

const ICONES = {
  obra_cadastrada:  IconMusic,
  contrato_gerado:  IconDocument,
  contrato_assinado: IconCheckCircle,
  licenciamento:    IconKey,
  oferta:           IconTag,
  dossie_download:  IconDownload,
  saque_confirmado: IconWallet,
  saque_cancelado:  IconXCircle,
  convite_editora:  IconDocument,
}

function fmtCompleto(iso) {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleString('pt-BR', {
      day: '2-digit', month: 'long', year: 'numeric',
      hour: '2-digit', minute: '2-digit',
    })
  } catch { return iso }
}

// Corrige links de notificações antigas que apontavam para rotas inexistentes
function sanearLink(link, n) {
  if (!link) return null
  const payload = n?.payload || {}

  // Notificações de contrato de edição — abre direto no contrato via ?contrato=ID
  if (payload.tipo === 'edicao') {
    const cid = payload.contract_id || payload.contrato_id
    return cid ? `/contratos?contrato=${cid}` : '/contratos'
  }

  // /contratos/<uuid> (sem "licenciamento") → /contratos/licenciamento/<uuid>
  const m = link.match(/^\/contratos\/([0-9a-fA-F-]{8,})$/)
  if (m) return `/contratos/licenciamento/${m[1]}`

  // /publisher/dashboard → /editora/dashboard
  if (link === '/publisher/dashboard') return '/editora/dashboard'
  // /dashboard padrão antigo
  if (link === '/dashboard') return '/descoberta'
  return link
}

function detalhePadrao(n, navigate) {
  const ir = (path) => () => {
    const destino = sanearLink(path, n) || sanearLink(n.link, n) || '/descoberta'
    navigate(destino)
  }

  switch (n.tipo) {
    case 'contrato_pendente':
      return {
        lead: 'Há um contrato aguardando sua assinatura. Sem ela, o licenciamento não avança.',
        dicas: [
          'Leia atentamente as cláusulas antes de assinar.',
          'A assinatura é eletrônica e fica registrada com data, hora e IP.',
        ],
        acoes: [{ label: 'Abrir contrato', kind: 'primary', onClick: ir(n.link || '/contratos') }],
      }

    case 'obra_cadastrada': {
      const obraId = n.payload?.obra_id
      const linkDescoberta = obraId ? `/descoberta?obraId=${obraId}` : '/descoberta'
      return {
        lead: 'Sua obra foi cadastrada com sucesso e está disponível na sua biblioteca. A partir de agora ela pode receber ofertas e entrar em contratos.',
        dicas: [
          'Confira se as informações da obra (título, gênero, autores) estão corretas.',
          'Adicione capa e descrição para chamar mais atenção na Descoberta.',
        ],
        acoes: [
          { label: 'Ver obra',            kind: 'primary', onClick: ir(n.link || '/obras') },
          { label: 'Ir para a Descoberta', kind: 'ghost',  onClick: ir(linkDescoberta) },
        ],
      }
    }
    case 'contrato_gerado':
      return {
        lead: 'Um novo contrato foi gerado e está aguardando sua assinatura. Sem sua assinatura, ele não passa para a próxima etapa.',
        dicas: [
          'Leia atentamente as cláusulas antes de assinar.',
          'A assinatura é eletrônica e fica registrada com data, hora e IP.',
        ],
        acoes: [{ label: 'Abrir contrato', kind: 'primary', onClick: ir(n.link) }],
      }
    case 'contrato_assinado':
      return {
        lead: 'Um contrato foi assinado e o licenciamento está ativo. A partir de agora ele aparece nos seus relatórios e pode gerar repasses.',
        acoes: [
          { label: 'Ver contrato',  kind: 'primary', onClick: ir(n.link || '/contratos') },
          { label: 'Ver Analytics', kind: 'ghost',   onClick: ir('/analytics') },
        ],
      }
    case 'licenciamento':
      return {
        lead: 'Uma de suas obras acabou de ser licenciada. O valor entra na sua aba de Saques após a confirmação do pagamento.',
        acoes: [
          { label: 'Ver detalhes',   kind: 'primary', onClick: ir(n.link || '/contratos') },
          { label: 'Ir para Saques', kind: 'ghost',   onClick: ir('/saques') },
        ],
      }
    case 'oferta':
      return {
        lead: 'Você recebeu uma nova oferta de licenciamento. Você pode aceitar, recusar ou contrapropor a partir do painel de Ofertas.',
        dicas: [
          'Compare o valor com o piso sugerido pela plataforma.',
          'Verifique o uso pretendido (mídia, território, prazo).',
        ],
        acoes: [{ label: 'Ver oferta', kind: 'primary', onClick: ir(n.link || '/ofertas') }],
      }
    case 'dossie_download':
      return {
        lead: 'Um dossiê foi baixado da sua obra. Esse evento ficou registrado no histórico para fins de rastreabilidade.',
        acoes: [{ label: 'Ver histórico', kind: 'primary', onClick: ir(n.link || '/analytics') }],
      }
    case 'saque_confirmado':
      return {
        lead: 'Seu saque foi confirmado e o valor está sendo enviado ao seu meio de pagamento. Ele cai conforme o prazo do banco/PSP.',
        acoes: [{ label: 'Ver saques', kind: 'primary', onClick: ir(n.link || '/saques') }],
      }
    case 'saque_cancelado':
      return {
        lead: 'O saque foi cancelado. O valor voltou para o seu saldo disponível e você pode tentar novamente quando quiser.',
        acoes: [{ label: 'Ver saques', kind: 'primary', onClick: ir(n.link || '/saques') }],
      }
    default:
      return {
        lead: n.mensagem || 'Você tem uma nova notificação.',
        acoes: n.link ? [{ label: 'Abrir', kind: 'primary', onClick: ir(n.link) }] : [],
      }
  }
}

export default function NotificationDetailModal({ notif, onClose, onChange }) {
  const navigate = useNavigate()
  const { perfil } = useAuth()

  const [detalheExtra, setDetalheExtra] = useState(null)
  const [loadingExtra, setLoadingExtra] = useState(false)
  const [erro, setErro]                 = useState('')
  const [acao, setAcao]                 = useState(null)
  const [assinatura, setAssinatura]     = useState('')
  const [salvando, setSalvando]         = useState(false)
  const [feedback, setFeedback]         = useState('')

  useEffect(() => {
    if (!notif) return
    setDetalheExtra(null); setErro(''); setAcao(null); setFeedback('')
    // Auto-marca como lida assim que o modal abre (silenciosamente)
    if (!notif.lida) {
      api.patch(`/notificacoes/${notif.id}/marcar-lida`)
        .then(() => onChange?.())
        .catch(() => {/* falha silenciosa: UI continua */})
    }
    if (notif.tipo === 'convite_editora' && notif.payload?.convite_id) {
      setLoadingExtra(true)
      api.get(`/agregados/convites/${notif.payload.convite_id}/termo`)
        .then(t => setDetalheExtra(t))
        .catch(e => setErro(e.message))
        .finally(() => setLoadingExtra(false))
    }
  }, [notif?.id])

  if (!notif) return null

  const padrao = detalhePadrao(notif, navigate)
  const IcTipo = ICONES[notif.tipo] || IconBell

  async function confirmarConvite() {
    if (acao === 'aceitar' && !assinatura.trim()) {
      setErro('Digite seu nome completo como assinatura digital.')
      return
    }
    setSalvando(true); setErro('')
    try {
      const cid = notif.payload.convite_id
      if (acao === 'aceitar') {
        await api.post(`/agregados/convites/${cid}/aceitar`, { assinatura_nome: assinatura.trim() })
        setFeedback('Convite aceito. A vinculação está ativa.')
      } else {
        await api.post(`/agregados/convites/${cid}/recusar`)
        setFeedback('Convite recusado.')
      }
      const t = await api.get(`/agregados/convites/${cid}/termo`).catch(() => null)
      if (t) setDetalheExtra(t)
      setAcao(null); setAssinatura('')
      onChange?.()
    } catch (e) { setErro(e.message) }
    finally { setSalvando(false) }
  }

  async function excluir() {
    if (!confirm('Excluir esta notificação?')) return
    try {
      await api.delete(`/notificacoes/${notif.id}`)
      onChange?.()
      onClose()
    } catch (e) { setErro(e.message) }
  }

  const isConvitePendente =
    notif.tipo === 'convite_editora'
    && detalheExtra?.status === 'pendente'
    && detalheExtra?.editora_id !== perfil?.id

  return createPortal(
    <div className="ndm-bg" onClick={() => { if (!salvando) onClose() }}>
      <div className="ndm-box" onClick={e => e.stopPropagation()}>

        {/* ── CABEÇALHO ── */}
        <header className="ndm-head">
          <div className="ndm-head-left">
            <div className="ndm-icon-block">
              <IcTipo size={22} />
            </div>
            <div className="ndm-head-text">
              <h3>{notif.titulo}</h3>
              <p className="ndm-time">{fmtCompleto(notif.criada_em)}</p>
            </div>
          </div>
          <button className="ndm-close" onClick={onClose} aria-label="Fechar">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
                 stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
              <path d="M18 6 6 18M6 6l12 12"/>
            </svg>
          </button>
        </header>

        {/* ── ALERTAS ── */}
        {feedback && <div className="ndm-alert ok">{feedback}</div>}
        {erro     && <div className="ndm-alert err">{erro}</div>}

        {/* ── CORPO ── */}
        <div className="ndm-body">
          <p className="ndm-lead">{padrao.lead}</p>

          {notif.mensagem && notif.mensagem !== padrao.lead && (
            <p className="ndm-msg">"{notif.mensagem}"</p>
          )}

          {padrao.dicas && padrao.dicas.length > 0 && (
            <ul className="ndm-dicas">
              {padrao.dicas.map((d, i) => <li key={i}>{d}</li>)}
            </ul>
          )}

          {/* DETALHE EXTRA: convite editora */}
          {notif.tipo === 'convite_editora' && (
            <div className="ndm-extra">
              {loadingExtra && <p className="ndm-muted">Carregando termo…</p>}
              {detalheExtra && (
                <>
                  <div className="ndm-status-row">
                    <span>Status do convite:</span>
                    <strong className={`ndm-pill st-${detalheExtra.status}`}>
                      {detalheExtra.status}
                    </strong>
                  </div>
                  <details className="ndm-details">
                    <summary>Ler texto integral do termo jurídico</summary>
                    <pre className="ndm-termo" style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word', margin: 0, fontFamily: 'Georgia, "Times New Roman", serif' }}>
                      {detalheExtra.termo_text || detalheExtra.termo_html}
                    </pre>
                  </details>
                  {detalheExtra.termo_aceito_pelo_artista_em && (
                    <p className="ndm-muted small">
                      Assinado em {fmtCompleto(detalheExtra.termo_aceito_pelo_artista_em)} como
                      "{detalheExtra.assinatura_artista_nome}".
                    </p>
                  )}
                </>
              )}
            </div>
          )}
        </div>

        {/* ── AÇÕES inline convite pendente ── */}
        {isConvitePendente && !acao && (
          <footer className="ndm-actions">
            <button className="btn btn-ghost ndm-btn-ghost" onClick={() => setAcao('recusar')} disabled={salvando}>Recusar</button>
            <button className="btn btn-primary ndm-btn-primary"
                    onClick={() => { setAcao('aceitar'); setAssinatura(perfil?.nome_completo || perfil?.nome_artistico || '') }}
                    disabled={salvando}>
              Aceitar e assinar
            </button>
          </footer>
        )}

        {isConvitePendente && acao === 'aceitar' && (
          <div className="ndm-confirm">
            <label>Digite seu nome completo como assinatura digital *</label>
            <input value={assinatura} onChange={e => setAssinatura(e.target.value)}
                   placeholder="Seu nome completo" />
            <div className="ndm-actions">
              <button className="btn btn-ghost ndm-btn-ghost" onClick={() => setAcao(null)} disabled={salvando}>Voltar</button>
              <button className="btn btn-primary ndm-btn-primary" onClick={confirmarConvite} disabled={salvando}>
                {salvando ? 'Confirmando…' : 'Confirmar aceite'}
              </button>
            </div>
          </div>
        )}

        {isConvitePendente && acao === 'recusar' && (
          <div className="ndm-confirm danger">
            <p>Tem certeza que deseja <strong>recusar</strong> este convite? A editora será avisada.</p>
            <div className="ndm-actions">
              <button className="btn btn-ghost ndm-btn-ghost" onClick={() => setAcao(null)} disabled={salvando}>Voltar</button>
              <button className="btn btn-danger ndm-btn-danger" onClick={confirmarConvite} disabled={salvando}>
                {salvando ? 'Enviando…' : 'Sim, recusar'}
              </button>
            </div>
          </div>
        )}

        {/* ── AÇÕES padrão ── */}
        {!isConvitePendente && !acao && !loadingExtra && (
          <footer className="ndm-actions">
            <button className="btn btn-ghost ndm-btn-ghost ndm-danger" onClick={excluir}>Excluir</button>
            <div style={{ flex: 1 }} />
            {padrao.acoes.map((a, i) => (
              <button key={i}
                      className={`btn ${a.kind === 'primary' ? 'ndm-btn-primary' : 'ndm-btn-ghost'}`}
                      onClick={() => { a.onClick(); if (a.kind === 'primary') onClose() }}>
                {a.label}
              </button>
            ))}
          </footer>
        )}
      </div>
    </div>,
    document.body
  )
}
