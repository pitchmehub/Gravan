import React, { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { api } from '../lib/api'

export default function ConnectOnboarding() {
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const veioDoStripe = params.get('sucesso') === '1' || window.location.pathname.includes('sucesso')

  const [status, setStatus] = useState(null)
  const [loading, setLoading] = useState(true)
  const [criando, setCriando] = useState(false)
  const [erro, setErro] = useState('')

  async function carregar() {
    try {
      setLoading(true)
      const s = await api.get('/connect/status')
      setStatus(s)
    } catch (e) { setErro(e.message) }
    finally { setLoading(false) }
  }
  useEffect(() => { carregar() }, [])

  async function iniciarOnboarding() {
    setCriando(true); setErro('')
    try {
      const r = await api.post('/connect/onboarding', {})
      window.location.href = r.url
    } catch (e) { setErro(e.message); setCriando(false) }
  }

  async function abrirDashboard() {
    try {
      const r = await api.post('/connect/dashboard-link', {})
      window.open(r.url, '_blank', 'noopener,noreferrer')
    } catch (e) { alert('Erro: ' + e.message) }
  }

  if (loading) return <div style={{ padding: 40 }}>Carregando…</div>

  const conectado = status?.conectado
  const completo  = status?.onboarding_completo
  const podeCobrar = status?.charges_enabled
  const podePayout = status?.payouts_enabled

  return (
    <div style={{ maxWidth: 720, margin: '0 auto', padding: '32px 20px' }}>
      <button onClick={() => navigate(-1)} className="btn btn-ghost"
        style={{ fontSize: 12, marginBottom: 16 }}>← Voltar</button>

      <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 6 }}>
        Receber pagamentos via Stripe
      </h1>
      <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 24 }}>
        Para receber sua parte das vendas, conecte sua conta Stripe.
        O cadastro é hospedado pela própria Stripe e leva ~3 minutos
        (CPF, dados bancários e selfie de verificação).
      </p>

      {erro && (
        <div style={{ padding: 12, background: '#fee', color: '#c0392b',
          borderRadius: 8, marginBottom: 16, fontSize: 13 }}>⚠ {erro}</div>
      )}

      {veioDoStripe && (
        <div style={{ padding: 12, background: '#E8F8EC', color: '#0E6B2B',
          borderRadius: 8, marginBottom: 16, fontSize: 13 }}>
          ✓ Onboarding finalizado! Verificando seu status…
        </div>
      )}

      {/* Cartão de status */}
      <div style={{ padding: 20, background: '#fff', border: '1px solid var(--border)',
        borderRadius: 12, marginBottom: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between',
          alignItems: 'center', marginBottom: 16 }}>
          <h3 style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-secondary)' }}>
            STATUS DA SUA CONTA
          </h3>
          {completo
            ? <span style={{ padding: '4px 10px', background: '#E8F8EC',
                color: '#0E6B2B', borderRadius: 4, fontSize: 11, fontWeight: 700 }}>ATIVA</span>
            : conectado
              ? <span style={{ padding: '4px 10px', background: '#FFF4E5',
                  color: '#7A4D00', borderRadius: 4, fontSize: 11, fontWeight: 700 }}>PENDENTE</span>
              : <span style={{ padding: '4px 10px', background: '#f3f4f6',
                  color: '#71717A', borderRadius: 4, fontSize: 11, fontWeight: 700 }}>NÃO CONECTADA</span>}
        </div>

        <ul style={{ listStyle: 'none', padding: 0, margin: 0, fontSize: 13 }}>
          <Item ok={conectado} label="Conta criada na Stripe" />
          <Item ok={status?.details_submitted} label="Cadastro enviado" />
          <Item ok={podeCobrar} label="Apta a receber transferências" />
          <Item ok={podePayout} label="Apta a receber payouts (banco verificado)" />
        </ul>

        {status?.requirements_pendentes?.length > 0 && (
          <div style={{ marginTop: 16, padding: 12, background: '#FFF4E5',
            borderRadius: 8, fontSize: 12 }}>
            <b>Pendências da Stripe:</b>
            <ul style={{ margin: '8px 0 0 16px' }}>
              {status.requirements_pendentes.map(r =>
                <li key={r}>{r.replace(/[._]/g, ' ')}</li>)}
            </ul>
          </div>
        )}
      </div>

      <div style={{ display: 'flex', gap: 10 }}>
        {!completo && (
          <button onClick={iniciarOnboarding} disabled={criando}
            className="btn btn-primary" style={{ flex: 1 }}>
            {criando ? 'Gerando link…' :
              conectado ? 'Continuar cadastro' : 'Conectar minha conta Stripe'}
          </button>
        )}
        {conectado && (
          <button onClick={abrirDashboard} className="btn btn-ghost">
            Abrir dashboard Stripe
          </button>
        )}
      </div>

      <p style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 24,
        lineHeight: 1.6 }}>
        🔒 Seus dados bancários ficam apenas com a Stripe (PCI-DSS Nível 1).
        A Pitch.me não armazena nenhuma informação sensível.
        Os pagamentos serão repassados mensalmente para sua conta cadastrada.
      </p>
    </div>
  )
}

function Item({ ok, label }) {
  return (
    <li style={{ display: 'flex', gap: 10, alignItems: 'center', padding: '6px 0' }}>
      <span style={{ width: 18, color: ok ? '#0E6B2B' : '#9ca3af' }}>
        {ok ? '✓' : '○'}
      </span>
      <span style={{ color: ok ? 'var(--text)' : 'var(--text-muted)' }}>{label}</span>
    </li>
  )
}
