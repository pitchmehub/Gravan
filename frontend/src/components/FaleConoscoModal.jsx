import React, { useState } from 'react'
import { api } from '../lib/api'

const EMAIL_SUPORTE = 'contatogravan@gmail.com'
const MAX_MSG = 1000

export default function FaleConoscoModal({ onClose }) {
  const [nome,     setNome]     = useState('')
  const [email,    setEmail]    = useState('')
  const [mensagem, setMensagem] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [enviado,  setEnviado]  = useState(false)
  const [erro,     setErro]     = useState('')

  async function enviar(e) {
    e.preventDefault()
    setErro(''); setEnviando(true)
    try {
      await api.post('/contato/', {
        nome:     nome.trim(),
        email:    email.trim().toLowerCase(),
        mensagem: mensagem.trim(),
      })
      setEnviado(true)
      setTimeout(() => onClose(), 2500)
    } catch (e) {
      setErro(e.message)
    } finally { setEnviando(false) }
  }

  return (
    <div
      onClick={e => { if (e.target === e.currentTarget) onClose() }}
      style={{
        position: 'fixed', inset: 0,
        background: 'rgba(9,9,11,.4)', backdropFilter: 'blur(4px)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        zIndex: 900, padding: 20,
      }}
    >
      <div style={{
        background: '#FFFFFF',
        border: '1px solid #E4E4E7',
        borderRadius: 0,
        width: '100%', maxWidth: 520,
        maxHeight: '90vh', overflow: 'auto',
        color: '#09090B',
      }}>
        {/* Header */}
        <div style={{ padding: '24px 28px', borderBottom: '1px solid #E4E4E7' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h2 style={{ fontSize: 20, fontWeight: 700, fontFamily: "'Space Grotesk', sans-serif", letterSpacing: '-0.02em' }}>
              Fale Conosco
            </h2>
            <button onClick={onClose} aria-label="Fechar" style={{
              background: 'none', border: 'none', color: '#71717A',
              fontSize: 24, cursor: 'pointer', lineHeight: 1,
            }}>×</button>
          </div>
          <div style={{
            marginTop: 14,
            padding: '12px 14px',
            background: '#FAFAFA',
            border: '1px solid #E4E4E7',
            borderRadius: 0,
            fontSize: 13,
          }}>
            <div style={{
              color: '#71717A', fontSize: 10, fontWeight: 700,
              letterSpacing: '0.12em', marginBottom: 4, textTransform: 'uppercase',
            }}>
              Email da plataforma
            </div>
            <a href={`mailto:${EMAIL_SUPORTE}`} style={{
              color: '#09090B', textDecoration: 'none', fontWeight: 600,
            }}>
              {EMAIL_SUPORTE}
            </a>
          </div>
        </div>

        {/* Body */}
        {enviado ? (
          <div style={{ padding: 40, textAlign: 'center' }}>
            <div style={{
              fontSize: 36, marginBottom: 12, color: '#16A34A',
              fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700,
            }}>✓</div>
            <h3 style={{ fontSize: 18, fontWeight: 700, marginBottom: 8 }}>Mensagem enviada!</h3>
            <p style={{ color: '#71717A', fontSize: 14 }}>
              Em breve entraremos em contato pelo email informado.
            </p>
          </div>
        ) : (
          <form onSubmit={enviar} style={{ padding: 24 }}>
            <div style={{ marginBottom: 16 }}>
              <label style={{
                display: 'block', fontSize: 11, fontWeight: 600, marginBottom: 6,
                color: '#3F3F46', letterSpacing: '0.12em', textTransform: 'uppercase',
              }}>
                Nome *
              </label>
              <input
                value={nome}
                onChange={e => setNome(e.target.value)}
                required
                maxLength={120}
                placeholder="Seu nome"
                style={{
                  width: '100%', padding: '12px 14px',
                  background: '#FFFFFF',
                  border: '1px solid #E4E4E7',
                  borderRadius: 0, color: '#09090B', fontSize: 14,
                  outline: 'none', boxSizing: 'border-box',
                  fontFamily: 'inherit',
                }}
              />
            </div>

            <div style={{ marginBottom: 16 }}>
              <label style={{
                display: 'block', fontSize: 11, fontWeight: 600, marginBottom: 6,
                color: '#3F3F46', letterSpacing: '0.12em', textTransform: 'uppercase',
              }}>
                Email *
              </label>
              <input
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                required
                maxLength={200}
                placeholder="seu@email.com"
                style={{
                  width: '100%', padding: '12px 14px',
                  background: '#FFFFFF',
                  border: '1px solid #E4E4E7',
                  borderRadius: 0, color: '#09090B', fontSize: 14,
                  outline: 'none', boxSizing: 'border-box',
                  fontFamily: 'inherit',
                }}
              />
            </div>

            <div style={{ marginBottom: 16 }}>
              <label style={{
                display: 'block', fontSize: 11, fontWeight: 600, marginBottom: 6,
                color: '#3F3F46', letterSpacing: '0.12em', textTransform: 'uppercase',
              }}>
                Mensagem *
              </label>
              <textarea
                value={mensagem}
                onChange={e => setMensagem(e.target.value.slice(0, MAX_MSG))}
                required
                minLength={10}
                maxLength={MAX_MSG}
                placeholder="Descreva seu contato…"
                rows={6}
                style={{
                  width: '100%', padding: '12px 14px',
                  background: '#FFFFFF',
                  border: '1px solid #E4E4E7',
                  borderRadius: 0, color: '#09090B', fontSize: 14,
                  outline: 'none', boxSizing: 'border-box',
                  resize: 'vertical', minHeight: 120, fontFamily: 'inherit',
                }}
              />
              <div style={{ textAlign: 'right', fontSize: 11, color: '#71717A', marginTop: 4 }}>
                {mensagem.length} / {MAX_MSG}
              </div>
            </div>

            {erro && (
              <div style={{
                padding: 10, marginBottom: 14,
                background: 'rgba(220,38,38,.10)',
                border: '1px solid rgba(220,38,38,.3)',
                borderRadius: 0, fontSize: 13, color: '#DC2626',
              }}>{erro}</div>
            )}

            <button type="submit" disabled={enviando} style={{
              width: '100%', padding: '14px',
              background: '#0C447C',
              color: '#fff', border: '1px solid #0C447C', borderRadius: 0,
              fontSize: 13, fontWeight: 700, cursor: 'pointer',
              opacity: enviando ? .6 : 1,
              letterSpacing: '0.08em', textTransform: 'uppercase',
              fontFamily: 'inherit',
            }}>
              {enviando ? 'Enviando…' : 'Enviar mensagem'}
            </button>
          </form>
        )}
      </div>
    </div>
  )
}
