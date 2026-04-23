import React from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'

export default function PagamentoCancelado() {
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const sessionId = params.get('session_id')

  return (
    <div style={{ padding: 32, maxWidth: 480, margin: '40px auto', textAlign: 'center' }}>
      <div style={{
        width: 80, height: 80, borderRadius: '50%',
        background: 'var(--surface-2)', color: 'var(--text-muted)',
        fontSize: 40,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        margin: '0 auto 20px',
      }}>×</div>

      <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 8 }}>Pagamento cancelado</h1>
      <p style={{ color: 'var(--text-muted)', marginBottom: 24, lineHeight: 1.6 }}>
        Você cancelou o pagamento antes de concluir.<br />
        Nenhum valor foi cobrado.
      </p>

      <div style={{ display: 'flex', gap: 12, justifyContent: 'center' }}>
        <button className="btn btn-primary" onClick={() => navigate(-1)}>Tentar novamente</button>
        <button className="btn btn-ghost"   onClick={() => navigate('/descoberta')}>Voltar ao catálogo</button>
      </div>

      {sessionId && (
        <p style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 24 }}>
          Sessão: {sessionId.substring(0, 24)}…
        </p>
      )}
    </div>
  )
}
