import React, { useState, useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { api } from '../lib/api'
import SaqueOTPModal from '../components/SaqueOTPModal'

function fmt(cents) {
  return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' })
    .format((cents ?? 0) / 100)
}

const STATUS_BADGE = {
  pendente_otp:         { bg: '#FEF3C7', cor: '#92400E', label: '✉ Aguardando código' },
  aguardando_liberacao: { bg: '#DBEAFE', cor: '#1E40AF', label: '⏳ Em janela de 24h' },
  processando:          { bg: 'var(--brand-light)', cor: 'var(--brand)', label: '↻ Processando' },
  pago:                 { bg: 'var(--success-bg)', cor: 'var(--success)', label: '✓ Pago' },
  rejeitado:            { bg: 'var(--error-bg)',   cor: 'var(--error)',   label: '✕ Rejeitado' },
  cancelado:            { bg: '#F3F4F6', cor: '#6B7280', label: '🚫 Cancelado' },
  expirado:             { bg: '#F3F4F6', cor: '#6B7280', label: '⌛ Expirado' },
  // legados
  solicitado:  { bg: 'var(--warning-bg)', cor: 'var(--warning)', label: '⏱ Solicitado' },
}

export default function Saques() {
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const [wallet,   setWallet]   = useState(null)
  const [connect,  setConnect]  = useState(null)
  const [loading,  setLoading]  = useState(true)
  const [valor,    setValor]    = useState('')
  const [enviando, setEnviando] = useState(false)
  const [erro,     setErro]     = useState('')
  const [sucesso,  setSucesso]  = useState('')

  // OTP modal state
  const [otpOpen,  setOtpOpen]  = useState(false)
  const [otpMeta,  setOtpMeta]  = useState(null)   // { saque_id, expira_em_segundos, email_destino_mascarado, valor_cents }

  async function load() {
    setLoading(true); setErro('')
    try {
      const [w, c] = await Promise.all([
        api.get('/perfis/me/wallet'),
        api.get('/connect/status'),
      ])
      setWallet(w); setConnect(c)
    } catch (e) { setErro(e.message) }
    finally { setLoading(false) }
  }
  useEffect(() => { load() }, [])

  // Auto-mostra mensagem se voltou de cancelamento via link
  useEffect(() => {
    if (params.get('cancelado') === '1') {
      setSucesso('✓ Saque cancelado. Valor integralmente devolvido à sua wallet.')
    }
  }, [params])

  async function iniciarSaque(e) {
    e.preventDefault()
    setErro(''); setSucesso(''); setEnviando(true)
    try {
      const valorNum = parseFloat((valor || '').replace(',', '.'))
      if (isNaN(valorNum) || valorNum < 10) throw new Error('Valor mínimo: R$ 10,00')
      const valor_cents = Math.round(valorNum * 100)
      const r = await api.post('/saques/iniciar', { valor_cents })
      setOtpMeta({ ...r, valor_cents })
      setOtpOpen(true)
    } catch (e) {
      setErro(e.message ?? 'Erro ao iniciar saque.')
    } finally { setEnviando(false) }
  }

  async function onOtpConfirmado(saque) {
    setOtpOpen(false)
    setOtpMeta(null)
    setValor('')
    const dt = new Date(saque.liberar_em).toLocaleString('pt-BR')
    setSucesso(
      `✓ Saque confirmado! Será liberado automaticamente em ${dt}. ` +
      `Você recebeu um e-mail com link para cancelar caso não tenha sido você.`
    )
    load()
  }

  async function cancelar(saqueId) {
    if (!confirm('Cancelar este saque? O valor volta integralmente para sua wallet.')) return
    try {
      await api.post(`/saques/${saqueId}/cancelar`, {
        motivo: 'Cancelado pelo usuário no histórico',
      })
      setSucesso('✓ Saque cancelado.')
      load()
    } catch (e) { setErro(e.message) }
  }

  if (loading) return (
    <div style={{ padding: 32 }}>
      <p style={{ color: 'var(--text-muted)' }}>Carregando…</p>
    </div>
  )

  const saldo  = wallet?.saldo_cents ?? 0
  const saques = wallet?.saques ?? []

  // "Reservado" = em saques ainda não-finais
  const reservado = saques
    .filter(x => ['pendente_otp','aguardando_liberacao','processando','solicitado'].includes(x.status))
    .reduce((s, x) => s + x.valor_cents, 0)
  const totalSacado = saques.filter(x => x.status === 'pago').reduce((s, x) => s + x.valor_cents, 0)
  const disponivel  = Math.max(0, saldo - reservado)

  const connectAtivo = connect?.charges_enabled
  const podeSacar    = connectAtivo && disponivel >= 1000

  return (
    <div style={{ padding: 32, maxWidth: 880 }}>
      <h1 style={{ fontSize: 24, fontWeight: 800 }}>Meus ganhos</h1>
      <p style={{ color: 'var(--text-muted)', fontSize: 14, marginBottom: 24 }}>
        Sua receita das vendas acumula aqui. Cada saque exige confirmação por
        e-mail e tem janela de segurança de 24 h antes de ser enviado.
      </p>

      <div style={{
        padding: 24, marginBottom: 16,
        background: 'linear-gradient(135deg,#BE123C,#09090B)',
        borderRadius: 16, color: '#fff',
      }}>
        <div style={{ fontSize: 12, fontWeight: 600,
          color: 'rgba(255,255,255,.7)', letterSpacing: 1, textTransform: 'uppercase' }}>
          Saldo disponível para saque
        </div>
        <div style={{ fontSize: 38, fontWeight: 800, marginTop: 6 }}>{fmt(disponivel)}</div>
        <div style={{ display: 'flex', gap: 24, marginTop: 16, fontSize: 12, flexWrap: 'wrap' }}>
          <div>
            <div style={{ color: 'rgba(255,255,255,.6)' }}>SALDO TOTAL</div>
            <div style={{ fontSize: 16, fontWeight: 700, marginTop: 2 }}>{fmt(saldo)}</div>
          </div>
          <div>
            <div style={{ color: 'rgba(255,255,255,.6)' }}>RESERVADO</div>
            <div style={{ fontSize: 16, fontWeight: 700, marginTop: 2 }}>{fmt(reservado)}</div>
          </div>
          <div>
            <div style={{ color: 'rgba(255,255,255,.6)' }}>JÁ SACADO</div>
            <div style={{ fontSize: 16, fontWeight: 700, marginTop: 2 }}>{fmt(totalSacado)}</div>
          </div>
        </div>
      </div>

      {!connectAtivo && (
        <div style={{
          padding: 20, marginBottom: 24, background: '#FFF4E5',
          border: '1px solid #f59e0b', borderRadius: 12,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
            <span style={{ fontSize: 24 }}>⚠</span>
            <h3 style={{ fontSize: 15, fontWeight: 700, color: '#7A4D00' }}>
              Conecte sua conta Stripe para sacar
            </h3>
          </div>
          <button className="btn btn-primary"
            style={{ background: '#f59e0b', borderColor: '#f59e0b' }}
            onClick={() => navigate('/connect')}>
            {connect?.conectado ? 'Concluir cadastro Stripe' : 'Conectar conta Stripe'}
          </button>
        </div>
      )}

      <div className="card" style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 16, fontWeight: 700, marginBottom: 8 }}>Solicitar saque</h2>
        <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 16 }}>
          🔐 Após confirmar o valor, enviaremos um <strong>código de 6 dígitos</strong> para
          o seu e-mail. O saque só será efetivado <strong>24 h depois</strong> da confirmação,
          e durante esse tempo você pode cancelar a qualquer momento.
        </p>

        <form onSubmit={iniciarSaque}>
          <div className="form-group">
            <label className="form-label">Valor em reais (R$) *</label>
            <input className="input" type="text" required
              placeholder="Ex: 50,00"
              value={valor} onChange={e => setValor(e.target.value)}
              disabled={!podeSacar}
              data-testid="saque-valor" />
            <small style={{ color: 'var(--text-muted)', fontSize: 12 }}>
              Mínimo: R$ 10,00 · Disponível: <strong>{fmt(disponivel)}</strong> ·
              Limite diário: R$ 5.000,00
            </small>
          </div>

          <div className="form-group" style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            {[10, 50, 100, disponivel/100].filter(v => v >= 10 && v <= disponivel/100).slice(0,4).map(v => (
              <button key={v} type="button"
                className="btn btn-ghost" style={{ fontSize: 12, padding: '4px 10px' }}
                onClick={() => setValor(v.toFixed(2).replace('.', ','))}>
                R$ {v.toFixed(2).replace('.', ',')}
              </button>
            ))}
          </div>

          {erro    && <div style={{ padding: 12, background: 'var(--error-bg)',   color: 'var(--error)',
            borderRadius: 8, fontSize: 13, marginBottom: 12 }}>⚠ {erro}</div>}
          {sucesso && <div style={{ padding: 12, background: 'var(--success-bg)', color: 'var(--success)',
            borderRadius: 8, fontSize: 13, marginBottom: 12 }}>{sucesso}</div>}

          <button type="submit" className="btn btn-primary"
            disabled={enviando || !podeSacar}
            data-testid="saque-submit">
            {enviando ? 'Enviando código…'
              : !connectAtivo  ? '🔒 Conecte sua conta Stripe primeiro'
              : disponivel < 1000 ? '💸 Saldo disponível insuficiente (mín. R$ 10)'
              : '✉ Enviar código de confirmação'}
          </button>
        </form>
      </div>

      {/* Histórico */}
      <div className="card">
        <h2 style={{ fontSize: 16, fontWeight: 700, marginBottom: 14 }}>Histórico de saques</h2>
        {saques.length === 0 ? (
          <p style={{ color: 'var(--text-muted)', fontSize: 13 }}>Nenhum saque ainda.</p>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {saques.map(s => {
              const badge = STATUS_BADGE[s.status] ?? STATUS_BADGE.solicitado
              const podeCancelar = ['pendente_otp','aguardando_liberacao'].includes(s.status)
              return (
                <div key={s.id} style={{
                  padding: 14, background: 'var(--surface-2)', borderRadius: 10,
                  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                  flexWrap: 'wrap', gap: 12,
                }}>
                  <div>
                    <div style={{ fontWeight: 700, fontSize: 16 }}>{fmt(s.valor_cents)}</div>
                    <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                      {new Date(s.created_at).toLocaleString('pt-BR')}
                      {s.liberar_em && s.status === 'aguardando_liberacao' && (
                        <> · liberação: {new Date(s.liberar_em).toLocaleString('pt-BR')}</>
                      )}
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                    <span style={{
                      padding: '4px 10px', borderRadius: 12, fontSize: 11, fontWeight: 700,
                      background: badge.bg, color: badge.cor,
                    }}>{badge.label}</span>
                    {podeCancelar && (
                      <button className="btn btn-ghost"
                        style={{ fontSize: 11, padding: '4px 10px', color: '#B91C1C' }}
                        onClick={() => cancelar(s.id)}>
                        Cancelar
                      </button>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>

      {otpOpen && otpMeta && (
        <SaqueOTPModal
          meta={otpMeta}
          onClose={() => { setOtpOpen(false); setOtpMeta(null) }}
          onConfirmado={onOtpConfirmado}
        />
      )}
    </div>
  )
}
