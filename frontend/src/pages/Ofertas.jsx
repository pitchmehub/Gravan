import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { api } from '../lib/api'
import OfertaModal from '../components/OfertaModal'

function fmt(cents) {
  return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' })
    .format((cents ?? 0) / 100)
}

const STATUS_STYLE = {
  pendente:        { bg: '#FEF3C7', color: '#92400E', label: 'Pendente' },
  aceita:          { bg: '#D1FAE5', color: '#065F46', label: 'Aceita' },
  recusada:        { bg: '#FEE2E2', color: '#991B1B', label: 'Recusada' },
  expirada:        { bg: '#F3F4F6', color: '#6B7280', label: 'Expirada' },
  contra_proposta: { bg: '#EDE9FE', color: '#5B21B6', label: 'Contraproposta enviada' },
  paga:            { bg: '#DBEAFE', color: '#1E3A8A', label: 'Paga' },
  cancelada:       { bg: '#F3F4F6', color: '#6B7280', label: 'Cancelada' },
}

function tempoRestante(expiresAt) {
  if (!expiresAt) return null
  const ms = new Date(expiresAt).getTime() - Date.now()
  if (ms <= 0) return 'Expirada'
  const h = Math.floor(ms / 3600000)
  const m = Math.floor((ms % 3600000) / 60000)
  if (h >= 1) return `${h}h ${m}m restantes`
  return `${m}m restantes`
}

export default function Ofertas() {
  const { perfil } = useAuth()
  const navigate = useNavigate()
  const isCompositor = perfil?.role === 'compositor'
  const isPublisher  = perfil?.role === 'publisher'

  // Aba inicial: compositor → recebidas; editora → editora; demais → enviadas
  const [aba, setAba] = useState(
    isCompositor ? 'recebidas' : isPublisher ? 'editora' : 'enviadas'
  )

  const [recebidas, setRecebidas] = useState([])
  const [enviadas, setEnviadas]   = useState([])
  const [editora, setEditora]     = useState([])
  const [loading, setLoading]     = useState(true)
  const [respondendo, setRespondendo] = useState(null)
  const [contraOferta, setContraOferta] = useState(null)

  async function carregar() {
    setLoading(true)
    try {
      const reqs = []
      if (isCompositor) {
        reqs.push(api.get('/catalogo/ofertas/recebidas').then(d => setRecebidas(d || [])))
      }
      if (isPublisher) {
        reqs.push(api.get('/catalogo/ofertas/editora').then(d => setEditora(d || [])))
      }
      // Enviadas: qualquer usuário pode ter feito ofertas
      reqs.push(api.get('/catalogo/ofertas/enviadas').then(d => setEnviadas(d || [])))
      await Promise.all(reqs)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { carregar() }, [isCompositor, isPublisher])

  async function responder(oferta, status) {
    setRespondendo(oferta.id)
    try {
      const isContra = oferta.aguardando_resposta_de === 'interprete'
      const url = isContra
        ? `/catalogo/ofertas/${oferta.id}/responder-contraproposta`
        : `/catalogo/ofertas/${oferta.id}/responder`
      const updated = await api.patch(url, { status })
      const merge = (arr) => arr.map(o => o.id === oferta.id ? { ...o, ...updated } : o)
      setRecebidas(prev => merge(prev))
      setEnviadas(prev => merge(prev))
      setEditora(prev => merge(prev))

      // Ao aceitar uma contraproposta, leva o intérprete direto ao checkout
      // com o valor negociado. O backend devolve `checkout_redirect`.
      if (isContra && status === 'aceita') {
        const dest = updated?.checkout_redirect
          || `/comprar/${oferta.obra_id}?oferta_id=${oferta.id}`
        navigate(dest)
        return
      }
    } catch (e) {
      alert(e.message)
    } finally {
      setRespondendo(null)
    }
  }

  if (loading) return <p className="text-muted">Carregando ofertas…</p>

  const listas = { recebidas, enviadas, editora }
  const ofertas = listas[aba] || []

  const tabs = []
  if (isCompositor) tabs.push({ key: 'recebidas', label: 'Recebidas', count: recebidas.length })
  if (isPublisher)  tabs.push({ key: 'editora',   label: 'Como editora', count: editora.length })
  tabs.push({ key: 'enviadas', label: 'Enviadas', count: enviadas.length })

  const subtitulo = {
    recebidas: 'Propostas de compradores para suas obras. Você tem 48h para aceitar, recusar ou contra-propor — a editora não decide, apenas acompanha.',
    enviadas:  'Acompanhe suas propostas. Quando o compositor aceitar, você terá 72h para assinar o contrato e pagar.',
    editora:   'Ofertas em obras que você edita. Visualização somente: a decisão é do compositor titular. Você é notificada de cada etapa.',
  }[aba]

  const tituloPagina = isCompositor || isPublisher ? 'Ofertas' : 'Minhas Ofertas'

  return (
    <div style={{ padding: '32px 20px', maxWidth: 720, margin: '0 auto' }}>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 22, fontWeight: 600 }}>{tituloPagina}</h1>
        <p className="text-muted">{subtitulo}</p>
      </div>

      {tabs.length > 1 && (
        <div style={{
          display: 'flex', gap: 4, marginBottom: 20, flexWrap: 'wrap',
          borderBottom: '1px solid var(--border)',
        }}>
          {tabs.map(t => {
            const ativo = aba === t.key
            return (
              <button
                key={t.key}
                onClick={() => setAba(t.key)}
                style={{
                  padding: '10px 16px',
                  background: 'transparent',
                  border: 'none',
                  borderBottom: ativo ? '2px solid var(--brand)' : '2px solid transparent',
                  color: ativo ? 'var(--brand)' : 'var(--text-secondary)',
                  fontWeight: ativo ? 600 : 500,
                  fontSize: 14,
                  cursor: 'pointer',
                  marginBottom: -1,
                }}
              >
                {t.label}
                <span style={{
                  marginLeft: 8, padding: '1px 8px', borderRadius: 99,
                  background: ativo ? 'var(--brand)' : 'var(--surface-2)',
                  color: ativo ? '#fff' : 'var(--text-secondary)',
                  fontSize: 11, fontWeight: 700,
                }}>
                  {t.count}
                </span>
              </button>
            )
          })}
        </div>
      )}

      {ofertas.length === 0 && (
        <div className="card" style={{ textAlign: 'center', padding: 40 }}>
          <p className="text-muted">
            {aba === 'recebidas' && 'Nenhuma oferta recebida ainda.'}
            {aba === 'enviadas'  && 'Você ainda não fez nenhuma oferta.'}
            {aba === 'editora'   && 'Nenhuma oferta nas obras que você edita.'}
          </p>
        </div>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {ofertas.map(oferta => {
          const s = STATUS_STYLE[oferta.status] ?? STATUS_STYLE.expirada
          const eExclusiva = oferta.tipo === 'exclusividade'
          const aguardandoCompositor = oferta.aguardando_resposta_de === 'compositor'
          const aguardandoInterprete = oferta.aguardando_resposta_de === 'interprete'
          const isCounter = !!oferta.contraproposta_de_id

          // Apenas a aba "Recebidas" do compositor tem ações decisórias.
          // A aba "Como editora" é somente leitura — editora não decide.
          const podeResponderRecebida   = aba === 'recebidas' && oferta.status === 'pendente' && aguardandoCompositor
          const podePagarEnviada        = aba === 'enviadas'  && oferta.status === 'aceita'
          const podeResponderContraEnv  = aba === 'enviadas'  && oferta.status === 'pendente' && aguardandoInterprete

          const labelExpiracao = aba === 'enviadas' && oferta.status === 'aceita'
            ? 'Janela de pagamento'
            : 'Janela'

          return (
            <div key={oferta.id} className="card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 10 }}>
                <div>
                  <div style={{ fontWeight: 600, fontSize: 15, display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                    {oferta.obras?.nome ?? '—'}
                    {eExclusiva && (
                      <span style={{
                        background: '#7c3aed', color: '#fff', fontSize: 10,
                        padding: '2px 8px', borderRadius: 99, fontWeight: 700,
                        letterSpacing: 0.4,
                      }}>EXCLUSIVA</span>
                    )}
                    {isCounter && (
                      <span style={{
                        background: '#0C447C', color: '#fff', fontSize: 10,
                        padding: '2px 8px', borderRadius: 99, fontWeight: 700,
                      }}>CONTRAPROPOSTA</span>
                    )}
                    {aba === 'editora' && (
                      <span style={{
                        background: '#6B7280', color: '#fff', fontSize: 10,
                        padding: '2px 8px', borderRadius: 99, fontWeight: 700,
                      }}>SOMENTE LEITURA</span>
                    )}
                  </div>
                  <div className="text-muted" style={{ fontSize: 13 }}>
                    {(aba === 'recebidas' || aba === 'editora')
                      ? `De: ${oferta.perfis?.nome ?? oferta.interprete_id}`
                      : `Preço de catálogo: ${fmt(oferta.obras?.preco_cents)}`}
                    {' · '}
                    {new Date(oferta.created_at).toLocaleDateString('pt-BR')}
                  </div>
                </div>
                <span style={{
                  padding: '3px 12px', borderRadius: 99, fontSize: 12, fontWeight: 600,
                  background: s.bg, color: s.color, whiteSpace: 'nowrap',
                }}>
                  {s.label}
                </span>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: oferta.mensagem ? 10 : 0 }}>
                <div>
                  <div className="text-muted" style={{ fontSize: 12 }}>Valor ofertado</div>
                  <div style={{ fontSize: 18, fontWeight: 700, color: 'var(--brand)' }}>
                    {fmt(oferta.valor_cents)}
                  </div>
                </div>
                {oferta.obras?.preco_cents && (
                  <div>
                    <div className="text-muted" style={{ fontSize: 12 }}>Catálogo</div>
                    <div style={{ fontSize: 14, color: 'var(--text-secondary)' }}>
                      {fmt(oferta.obras.preco_cents)}
                    </div>
                  </div>
                )}
                {(oferta.status === 'pendente' || oferta.status === 'aceita') && oferta.expires_at && (
                  <div style={{ marginLeft: 'auto' }}>
                    <div className="text-muted" style={{ fontSize: 12 }}>{labelExpiracao}</div>
                    <div style={{ fontSize: 13, fontWeight: 600, color: '#dc2626' }}>
                      {tempoRestante(oferta.expires_at)}
                    </div>
                  </div>
                )}
              </div>

              {oferta.mensagem && (
                <div style={{
                  background: 'var(--surface-2)', borderRadius: 'var(--radius-md)',
                  padding: '8px 12px', fontSize: 13, color: 'var(--text-secondary)',
                  marginBottom: 10,
                }}>
                  "{oferta.mensagem}"
                </div>
              )}

              {/* Ações */}
              {podeResponderRecebida && (
                <>
                  <div style={{
                    background: '#FEF3C7', color: '#92400E',
                    padding: '8px 12px', borderRadius: 6, marginBottom: 10,
                    fontSize: 12,
                  }}>
                    Ao aceitar, abre uma janela de 72h para o comprador
                    assinar o contrato e pagar. Após esse prazo, a oferta
                    perde validade automaticamente.
                  </div>
                  <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                    <button
                      className="btn btn-primary btn-sm"
                      disabled={respondendo === oferta.id}
                      onClick={() => responder(oferta, 'aceita')}
                    >
                      Aceitar e gerar contrato
                    </button>
                    <button
                      className="btn btn-sm"
                      style={{ background: '#7c3aed', color: '#fff' }}
                      disabled={respondendo === oferta.id}
                      onClick={() => setContraOferta(oferta)}
                    >
                      Contra-propor
                    </button>
                    <button
                      className="btn btn-danger btn-sm"
                      disabled={respondendo === oferta.id}
                      onClick={() => responder(oferta, 'recusada')}
                    >
                      Recusar
                    </button>
                  </div>
                </>
              )}

              {podeResponderContraEnv && (
                <div style={{ display: 'flex', gap: 8 }}>
                  <button
                    className="btn btn-primary btn-sm"
                    disabled={respondendo === oferta.id}
                    onClick={() => responder(oferta, 'aceita')}
                  >
                    Aceitar contraproposta
                  </button>
                  <button
                    className="btn btn-danger btn-sm"
                    disabled={respondendo === oferta.id}
                    onClick={() => responder(oferta, 'recusada')}
                  >
                    Recusar
                  </button>
                </div>
              )}

              {podePagarEnviada && (
                <button
                  className="btn btn-primary btn-sm"
                  onClick={() => navigate(`/comprar/${oferta.obra_id}?oferta_id=${oferta.id}`)}
                >
                  Assinar contrato e pagar · {fmt(oferta.valor_cents)}
                </button>
              )}

              {oferta.responded_at && (
                <div className="text-muted" style={{ fontSize: 12, marginTop: 8 }}>
                  Respondida em {new Date(oferta.responded_at).toLocaleDateString('pt-BR')}
                </div>
              )}
            </div>
          )
        })}
      </div>

      {contraOferta && (
        <OfertaModal
          obra={{
            id: contraOferta.obra_id,
            nome: contraOferta.obras?.nome,
            preco_cents: contraOferta.obras?.preco_cents,
            titular_pro: true,
          }}
          modo="contraproposta"
          ofertaOriginal={contraOferta}
          onClose={() => setContraOferta(null)}
          onCriada={() => { setContraOferta(null); carregar() }}
        />
      )}
    </div>
  )
}
