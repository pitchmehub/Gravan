import React, { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { api } from '../lib/api'

export default function AssinaturaSucesso() {
  const [search] = useSearchParams()
  const { refreshPerfil } = useAuth()
  const navigate = useNavigate()
  const [status, setStatus] = useState('processing')
  const sessionId = search.get('session_id')

  useEffect(() => {
    let attempts = 0
    const maxAttempts = 8
    const interval = 1500

    async function poll() {
      attempts += 1
      try {
        // Primeiro: força confirmação verificando a sessão direto no Stripe
        // (fallback para ambientes sem webhook configurado, ex.: localhost)
        if (sessionId && attempts === 1) {
          try { await api.post(`/assinatura/confirmar/${sessionId}`, {}) } catch (_) {}
        }
        const s = await api.get('/assinatura/status')
        if (s?.plano === 'PRO' && s?.status_assinatura !== 'inativa') {
          setStatus('ok')
          await refreshPerfil()
          setTimeout(() => navigate('/dashboard'), 2500)
          return
        }
      } catch (_) { /* noop */ }
      if (attempts >= maxAttempts) { setStatus('pending'); return }
      setTimeout(poll, interval)
    }
    poll()
  }, [])

  return (
    <div data-testid="assinatura-sucesso" style={{
      padding: 80, maxWidth: 560, margin: '0 auto', textAlign: 'center',
    }}>
      {status === 'processing' && (
        <>
          <div style={{ fontSize: 48, marginBottom: 16 }}>⏳</div>
          <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 8 }}>Confirmando seu pagamento…</h1>
          <p style={{ color: 'var(--text-muted)', fontSize: 13 }}>
            Sessão {sessionId ? sessionId.slice(0, 14) + '…' : '—'}
          </p>
        </>
      )}
      {status === 'ok' && (
        <>
          <div style={{ fontSize: 52, marginBottom: 16 }}>🎉</div>
          <h1 style={{ fontSize: 24, fontWeight: 800, marginBottom: 10 }}>Bem-vindo ao PRO!</h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: 14 }}>
            Sua assinatura foi ativada. Taxa de transação agora é <b>15%</b> e você já tem acesso
            ao painel de analytics.
          </p>
          <p style={{ color: 'var(--text-muted)', fontSize: 12, marginTop: 16 }}>
            Redirecionando para o Dashboard…
          </p>
        </>
      )}
      {status === 'pending' && (
        <>
          <div style={{ fontSize: 42, marginBottom: 16 }}>⏱</div>
          <h1 style={{ fontSize: 20, fontWeight: 700, marginBottom: 8 }}>Pagamento em processamento</h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: 13 }}>
            O Stripe ainda está confirmando. Sua assinatura deve ser ativada em alguns minutos.
          </p>
          <button
            data-testid="btn-voltar-planos"
            className="btn btn-ghost"
            onClick={() => navigate('/planos')}
            style={{ marginTop: 20 }}
          >Voltar</button>
        </>
      )}
    </div>
  )
}
