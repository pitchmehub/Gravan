import React, { useEffect, useState } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { api } from '../lib/api'
import NotificationDetailModal from '../components/NotificationDetailModal'
import {
  IconBell, IconMusic, IconDocument, IconCheckCircle, IconKey,
  IconTag, IconDownload, IconWallet, IconXCircle,
} from '../components/Icons'
import useRealtimeNotifications from '../hooks/useRealtimeNotifications'
import {
  isPushSupported, getPushStatus, subscribePush, unsubscribePush, sendTestPush,
} from '../lib/push'

const ICONES = {
  obra_cadastrada: IconMusic,
  contrato_gerado: IconDocument,
  contrato_assinado: IconCheckCircle,
  licenciamento: IconKey,
  oferta: IconTag,
  dossie_download: IconDownload,
  saque_confirmado: IconWallet,
  saque_cancelado: IconXCircle,
  convite_editora: IconDocument,
}

const TIPOS_LABEL = {
  obra_cadastrada:    'Obras',
  contrato_gerado:    'Contratos',
  contrato_assinado:  'Contratos',
  licenciamento:      'Licenciamentos',
  oferta:             'Ofertas',
  dossie_download:    'Dossiês',
  saque_confirmado:   'Saques',
  saque_cancelado:    'Saques',
  convite_editora:    'Convites',
}

function fmtData(iso) {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleString('pt-BR', {
      day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit',
    })
  } catch { return iso }
}

const PAGE_SIZE = 20

export default function Notificacoes() {
  const { perfil } = useAuth()
  const [items, setItems]     = useState([])
  const [total, setTotal]     = useState(0)
  const [hasMore, setHasMore] = useState(false)
  const [offset, setOffset]   = useState(0)
  const [loading, setLoading] = useState(false)
  const [erro, setErro]       = useState('')
  const [filtroTipo, setFiltroTipo] = useState('todos')   // 'todos' | tipo
  const [naoLidasOnly, setNaoLidasOnly] = useState(false)
  const [selecionada, setSelecionada]   = useState(null)

  const [pushStatus, setPushStatus]   = useState({ supported: false, permission: 'default', subscribed: false })
  const [pushBusy, setPushBusy]       = useState(false)

  async function carregar(reset = false) {
    setLoading(true); setErro('')
    try {
      const off = reset ? 0 : offset
      const params = new URLSearchParams({
        offset: String(off),
        limit:  String(PAGE_SIZE),
      })
      if (naoLidasOnly) params.set('nao_lidas', '1')
      const r = await api.get(`/notificacoes/?${params}`)
      const novos = r.items || []
      setItems(reset ? novos : [...items, ...novos])
      setTotal(r.total || 0)
      setHasMore(!!r.has_more)
      setOffset(off + novos.length)
    } catch (e) { setErro(e.message) }
    finally { setLoading(false) }
  }

  // Carrega na primeira vez e quando muda o filtro de não-lidas
  useEffect(() => { carregar(true) /* eslint-disable-next-line */ }, [naoLidasOnly])

  // Atualiza push status
  useEffect(() => {
    if (!isPushSupported()) return
    getPushStatus().then(setPushStatus)
  }, [])

  // Realtime — quando algo mudar, recarrega o topo
  useRealtimeNotifications(perfil?.id, () => carregar(true))

  async function togglePush() {
    setPushBusy(true)
    try {
      if (pushStatus.subscribed) {
        await unsubscribePush()
      } else {
        await subscribePush()
      }
      setPushStatus(await getPushStatus())
    } catch (e) { alert(e.message) }
    finally { setPushBusy(false) }
  }

  async function testarPush() {
    setPushBusy(true)
    try { await sendTestPush() }
    catch (e) { alert(e.message) }
    finally { setPushBusy(false) }
  }

  async function marcarTodasLidas() {
    try { await api.patch('/notificacoes/marcar-todas-lidas'); carregar(true) }
    catch (e) { alert(e.message) }
  }

  async function abrir(n) {
    if (!n.lida) {
      try { await api.patch(`/notificacoes/${n.id}/marcar-lida`) } catch (_) {}
    }
    setSelecionada({ ...n, lida: true })
    carregar(true)
  }

  // Filtro client-side por tipo
  const visiveis = filtroTipo === 'todos'
    ? items
    : items.filter(n => n.tipo === filtroTipo)

  // Tipos disponíveis para filtro (com base nos itens carregados)
  const tiposPresentes = Array.from(new Set(items.map(n => n.tipo)))

  const naoLidasCount = items.filter(n => !n.lida).length

  return (
    <div style={{ padding: '32px 20px', maxWidth: 920, margin: '0 auto' }}>
      <header style={{ marginBottom: 18 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, margin: 0 }}>Notificações</h1>
        <p style={{ fontSize: 13, color: 'var(--text-muted)', margin: '4px 0 0' }}>
          Histórico completo das suas notificações. {total > 0 && <>· Total: <strong>{total}</strong></>}
        </p>
      </header>

      {/* Cartão de push notifications */}
      {pushStatus.supported && (
        <div style={pushCard}>
          <div style={{ flex: 1 }}>
            <strong style={{ fontSize: 14 }}>Notificações no aparelho (push)</strong>
            <p style={{ fontSize: 12, color: 'var(--text-muted)', margin: '2px 0 0' }}>
              {pushStatus.permission === 'denied'
                ? 'Você bloqueou notificações nas configurações do navegador. Reabra para ativar.'
                : pushStatus.subscribed
                  ? 'Ativadas neste navegador/aparelho. Você receberá avisos mesmo com o app fechado.'
                  : 'Receba avisos no celular ou no desktop sem precisar manter a aba aberta.'}
            </p>
          </div>
          {pushStatus.permission !== 'denied' && (
            <>
              <button className="btn btn-ghost" disabled={pushBusy || !pushStatus.subscribed}
                      onClick={testarPush} style={{ fontSize: 12 }}>
                Testar
              </button>
              <button className={`btn ${pushStatus.subscribed ? 'btn-ghost' : 'btn-primary'}`}
                      disabled={pushBusy} onClick={togglePush}>
                {pushStatus.subscribed ? 'Desativar' : 'Ativar'}
              </button>
            </>
          )}
        </div>
      )}

      {/* Filtros */}
      <div style={filtrosBar}>
        <label style={{ display: 'flex', gap: 6, alignItems: 'center', fontSize: 13, cursor: 'pointer' }}>
          <input type="checkbox" checked={naoLidasOnly} onChange={e => setNaoLidasOnly(e.target.checked)} />
          Só não-lidas
        </label>

        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
          <Chip ativo={filtroTipo === 'todos'} onClick={() => setFiltroTipo('todos')}>Todos</Chip>
          {tiposPresentes.map(t => (
            <Chip key={t} ativo={filtroTipo === t} onClick={() => setFiltroTipo(t)}>
              {TIPOS_LABEL[t] || t}
            </Chip>
          ))}
        </div>

        <div style={{ flex: 1 }} />
        {naoLidasCount > 0 && (
          <button className="btn btn-ghost" style={{ fontSize: 12 }} onClick={marcarTodasLidas}>
            Marcar todas como lidas
          </button>
        )}
      </div>

      {erro && <div style={alertErr}>{erro}</div>}

      {/* Lista */}
      {visiveis.length === 0 && !loading ? (
        <div style={empty}>
          {naoLidasOnly ? 'Nenhuma notificação não-lida.' : 'Nenhuma notificação ainda.'}
        </div>
      ) : (
        <div style={lista}>
          {visiveis.map(n => {
            const Ic = ICONES[n.tipo] || IconBell
            return (
              <button key={n.id} onClick={() => abrir(n)}
                      style={{ ...itemBtn, background: n.lida ? 'var(--surface)' : 'rgba(190,18,60,.04)' }}>
                <span style={{ ...iconBox, background: n.lida ? 'var(--surface-2,#fafafa)' : 'rgba(190,18,60,.1)' }}>
                  <Ic size={18} />
                </span>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: 'flex', gap: 8, alignItems: 'baseline', flexWrap: 'wrap' }}>
                    <strong style={{ fontSize: 14 }}>{n.titulo}</strong>
                    {!n.lida && <span style={dot} />}
                  </div>
                  {n.mensagem && (
                    <p style={{ margin: '2px 0', fontSize: 13, color: 'var(--text-muted)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {n.mensagem}
                    </p>
                  )}
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>
                    {fmtData(n.criada_em)} · {TIPOS_LABEL[n.tipo] || n.tipo}
                  </div>
                </div>
              </button>
            )
          })}
        </div>
      )}

      {/* Carregar mais */}
      {hasMore && (
        <div style={{ textAlign: 'center', marginTop: 16 }}>
          <button className="btn btn-ghost" disabled={loading} onClick={() => carregar(false)}>
            {loading ? 'Carregando…' : 'Carregar mais'}
          </button>
        </div>
      )}

      {selecionada && (
        <NotificationDetailModal
          notif={selecionada}
          onClose={() => setSelecionada(null)}
          onChange={() => carregar(true)}
        />
      )}
    </div>
  )
}

function Chip({ ativo, onClick, children }) {
  return (
    <button onClick={onClick}
      style={{
        padding: '4px 10px', borderRadius: 999, border: '1px solid var(--border)',
        background: ativo ? 'var(--brand)' : 'var(--surface)',
        color: ativo ? '#fff' : 'var(--text-primary)',
        fontSize: 12, fontWeight: 600, cursor: 'pointer', fontFamily: 'inherit',
      }}>{children}</button>
  )
}

const pushCard  = { display: 'flex', alignItems: 'center', gap: 10, padding: 14, border: '1px solid var(--border)', borderRadius: 12, marginBottom: 16, background: 'var(--surface)', flexWrap: 'wrap' }
const filtrosBar= { display: 'flex', gap: 10, alignItems: 'center', marginBottom: 14, flexWrap: 'wrap' }
const empty     = { padding: 40, border: '1px dashed var(--border)', borderRadius: 12, textAlign: 'center', color: 'var(--text-muted)' }
const lista     = { display: 'flex', flexDirection: 'column', gap: 6 }
const itemBtn   = {
  display: 'flex', alignItems: 'center', gap: 12, width: '100%', textAlign: 'left',
  padding: 12, border: '1px solid var(--border)', borderRadius: 10, cursor: 'pointer',
  fontFamily: 'inherit', color: 'inherit',
}
const iconBox   = { width: 38, height: 38, borderRadius: 999, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }
const dot       = { width: 8, height: 8, borderRadius: 999, background: 'var(--brand,#BE123C)', display: 'inline-block', flexShrink: 0 }
const alertErr  = { padding: 12, background: 'rgba(239,68,68,.1)', border: '1px solid #ef4444', borderRadius: 8, marginBottom: 16, fontSize: 13, color: '#c0392b' }
