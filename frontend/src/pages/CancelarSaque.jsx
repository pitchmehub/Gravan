import React, { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'

const BASE = import.meta.env.VITE_API_URL || import.meta.env.VITE_API_BASE_URL

/**
 * Página pública de cancelamento de saque via link "Não fui eu" do e-mail.
 * Rota sugerida: /saques/cancelar?token=xxxxxxxx
 *
 * Adicione no App.jsx (ou roteador):
 *   <Route path="/saques/cancelar" element={<CancelarSaque />} />
 */
export default function CancelarSaque() {
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const token = params.get('token') || ''
  const [estado, setEstado] = useState('confirmando') // confirmando | sucesso | erro
  const [mensagem, setMensagem] = useState('')
  const [enviando, setEnviando] = useState(false)

  async function executar() {
    setEnviando(true)
    try {
      const res = await fetch(`${BASE}/api/saques/cancelar-por-token`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'omit',
        body: JSON.stringify({ token, motivo: 'Cancelado via link no e-mail' }),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(data.error || 'Falha ao cancelar.')
      setEstado('sucesso')
      setMensagem('Saque cancelado com sucesso. O valor voltou para a sua wallet.')
    } catch (e) {
      setEstado('erro')
      setMensagem(e.message)
    } finally { setEnviando(false) }
  }

  useEffect(() => {
    if (!token) {
      setEstado('erro')
      setMensagem('Link inválido — token ausente.')
    }
  }, [token])

  return (
    <div style={{ minHeight: '100vh', display: 'grid', placeItems: 'center',
                  padding: 24, background: '#f6f6f7' }}>
      <div style={{ maxWidth: 500, width: '100%', background: '#fff',
                    padding: 32, borderRadius: 16,
                    boxShadow: '0 10px 30px rgba(0,0,0,.08)' }}>
        <div style={{ fontWeight: 800, color: '#BE123C', marginBottom: 18 }}>Pitch.me</div>

        {estado === 'confirmando' && (
          <>
            <h1 style={{ fontSize: 22, fontWeight: 800, marginBottom: 10 }}>
              Cancelar este saque?
            </h1>
            <p style={{ fontSize: 14, color: '#444', marginBottom: 20 }}>
              Você está prestes a cancelar um saque pendente. O valor voltará
              integralmente para sua wallet, e você poderá solicitar novamente quando quiser.
            </p>
            <p style={{ fontSize: 13, color: '#B91C1C', marginBottom: 20 }}>
              ⚠ Se você não solicitou este saque, recomendamos também trocar
              sua senha imediatamente.
            </p>
            <div style={{ display: 'flex', gap: 8 }}>
              <button className="btn btn-primary"
                disabled={enviando || !token}
                onClick={executar}
                style={{ flex: 1, background: '#B91C1C', borderColor: '#B91C1C' }}>
                {enviando ? 'Cancelando…' : 'Sim, cancelar saque'}
              </button>
              <button className="btn btn-ghost"
                onClick={() => navigate('/')}>
                Voltar
              </button>
            </div>
          </>
        )}

        {estado === 'sucesso' && (
          <>
            <h1 style={{ fontSize: 22, fontWeight: 800, marginBottom: 10, color: '#059669' }}>
              ✓ Saque cancelado
            </h1>
            <p style={{ fontSize: 14, color: '#444', marginBottom: 20 }}>{mensagem}</p>
            <button className="btn btn-primary" onClick={() => navigate('/saques?cancelado=1')}>
              Ir para meus ganhos
            </button>
          </>
        )}

        {estado === 'erro' && (
          <>
            <h1 style={{ fontSize: 22, fontWeight: 800, marginBottom: 10, color: '#B91C1C' }}>
              Não foi possível cancelar
            </h1>
            <p style={{ fontSize: 14, color: '#444', marginBottom: 20 }}>{mensagem}</p>
            <button className="btn btn-primary" onClick={() => navigate('/')}>Voltar</button>
          </>
        )}
      </div>
    </div>
  )
}
