import React, { useState, useEffect, useRef } from 'react'
import { api } from '../lib/api'

function fmt(cents) {
  return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' })
    .format((cents ?? 0) / 100)
}

/**
 * Modal de confirmação de saque por OTP.
 * Props:
 *   meta: { saque_id, expira_em_segundos, email_destino_mascarado, valor_cents }
 *   onClose()
 *   onConfirmado(saque)
 */
export default function SaqueOTPModal({ meta, onClose, onConfirmado }) {
  const [codigo, setCodigo]     = useState('')
  const [erro, setErro]         = useState('')
  const [enviando, setEnviando] = useState(false)
  const [reenviando, setReenv]  = useState(false)
  const [restante, setRestante] = useState(meta.expira_em_segundos || 600)
  const [saqueId, setSaqueId]   = useState(meta.saque_id)
  const [emailMask, setEmail]   = useState(meta.email_destino_mascarado)
  const inputRef = useRef(null)

  // Foco automático
  useEffect(() => { inputRef.current?.focus() }, [])

  // Countdown
  useEffect(() => {
    if (restante <= 0) return
    const t = setInterval(() => setRestante(r => Math.max(0, r - 1)), 1000)
    return () => clearInterval(t)
  }, [restante])

  function fmtTempo(s) {
    const m = Math.floor(s / 60), ss = s % 60
    return `${m}:${ss.toString().padStart(2, '0')}`
  }

  async function confirmar(e) {
    e?.preventDefault()
    setErro(''); setEnviando(true)
    try {
      if (!/^\d{6}$/.test(codigo)) throw new Error('Digite os 6 dígitos do código.')
      const r = await api.post(`/saques/${saqueId}/confirmar`, { codigo })
      onConfirmado(r)
    } catch (e) {
      setErro(e.message ?? 'Código inválido.')
    } finally { setEnviando(false) }
  }

  async function reenviar() {
    setErro(''); setReenv(true)
    try {
      const r = await api.post(`/saques/${saqueId}/reenviar-otp`, {})
      setSaqueId(r.saque_id)
      setEmail(r.email_destino_mascarado)
      setRestante(r.expira_em_segundos)
      setCodigo('')
      inputRef.current?.focus()
    } catch (e) {
      setErro(e.message ?? 'Não foi possível reenviar.')
    } finally { setReenv(false) }
  }

  async function cancelar() {
    if (!confirm('Cancelar esta solicitação? Você poderá iniciar outra a qualquer momento.')) return
    try {
      await api.post(`/saques/${saqueId}/cancelar`, { motivo: 'Cancelado no modal de OTP' })
    } catch { /* ignore */ }
    onClose()
  }

  return (
    <div
      role="dialog" aria-modal="true" aria-labelledby="otp-titulo"
      style={{
        position: 'fixed', inset: 0, background: 'rgba(0,0,0,.55)',
        display: 'grid', placeItems: 'center', padding: 16, zIndex: 9999,
      }}
      onClick={onClose}
    >
      <div
        onClick={e => e.stopPropagation()}
        style={{
          background: '#fff', borderRadius: 16, padding: 28,
          maxWidth: 440, width: '100%', boxShadow: '0 20px 50px rgba(0,0,0,.3)',
        }}
      >
        <h2 id="otp-titulo" style={{ fontSize: 20, fontWeight: 800, marginBottom: 6 }}>
          Confirme seu saque
        </h2>
        <p style={{ fontSize: 13, color: '#555', marginBottom: 16 }}>
          Enviamos um código de 6 dígitos para <strong>{emailMask}</strong>.
          Valor da solicitação: <strong>{fmt(meta.valor_cents)}</strong>.
        </p>

        <form onSubmit={confirmar}>
          <input
            ref={inputRef}
            type="text" inputMode="numeric" autoComplete="one-time-code"
            maxLength={6} pattern="\d{6}"
            value={codigo}
            onChange={e => setCodigo(e.target.value.replace(/\D/g, '').slice(0, 6))}
            placeholder="000000"
            data-testid="saque-otp-input"
            style={{
              width: '100%', padding: '16px 12px', fontSize: 28, textAlign: 'center',
              letterSpacing: 12, fontFamily: 'monospace', fontWeight: 700,
              border: '2px solid #BE123C', borderRadius: 12, marginBottom: 12,
              color: '#BE123C',
            }}
          />

          <div style={{ fontSize: 12, color: restante > 60 ? '#666' : '#B91C1C',
            textAlign: 'center', marginBottom: 14 }}>
            {restante > 0 ? <>Código expira em <strong>{fmtTempo(restante)}</strong></>
                           : 'Código expirado — peça reenvio.'}
          </div>

          {erro && (
            <div style={{
              padding: 10, background: 'var(--error-bg, #FEE2E2)',
              color: 'var(--error, #B91C1C)', borderRadius: 8,
              fontSize: 13, marginBottom: 12, textAlign: 'center',
            }}>⚠ {erro}</div>
          )}

          <button
            type="submit" className="btn btn-primary"
            disabled={enviando || codigo.length !== 6 || restante === 0}
            data-testid="saque-otp-confirmar"
            style={{ width: '100%' }}
          >
            {enviando ? 'Confirmando…' : '✓ Confirmar saque'}
          </button>
        </form>

        <div style={{ display: 'flex', gap: 8, marginTop: 12, justifyContent: 'space-between' }}>
          <button
            className="btn btn-ghost"
            disabled={reenviando}
            onClick={reenviar}
            style={{ fontSize: 12 }}
          >
            {reenviando ? 'Reenviando…' : 'Não recebi — reenviar'}
          </button>
          <button
            className="btn btn-ghost"
            onClick={cancelar}
            style={{ fontSize: 12, color: '#B91C1C' }}
          >
            Cancelar solicitação
          </button>
        </div>

        <p style={{ fontSize: 11, color: '#888', marginTop: 16, lineHeight: 1.5 }}>
          🔐 Seu saque só é efetivado <strong>24 h após a confirmação</strong>. Durante
          esse tempo, você receberá um e-mail com link para cancelar caso não tenha
          sido você quem solicitou.
        </p>
      </div>
    </div>
  )
}
