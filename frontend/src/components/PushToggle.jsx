import React, { useState, useEffect } from 'react'
import { isPushSupported, getPushStatus, subscribePush, unsubscribePush, sendTestPush } from '../lib/push'

export default function PushToggle() {
  const [status, setStatus]   = useState(null)
  const [loading, setLoading] = useState(false)
  const [msg, setMsg]         = useState(null)

  async function refresh() {
    const s = await getPushStatus()
    setStatus(s)
  }

  useEffect(() => { refresh() }, [])

  function showMsg(text, type = 'ok') {
    setMsg({ text, type })
    setTimeout(() => setMsg(null), 4000)
  }

  async function handleToggle() {
    if (!status) return
    setLoading(true)
    try {
      if (status.subscribed) {
        await unsubscribePush()
        showMsg('Notificações desativadas neste dispositivo.')
      } else {
        await subscribePush()
        showMsg('Notificações ativadas! Você receberá alertas de novas ofertas e mensagens.', 'ok')
      }
      await refresh()
    } catch (e) {
      showMsg(e.message || 'Não foi possível configurar as notificações.', 'err')
    } finally {
      setLoading(false)
    }
  }

  async function handleTest() {
    setLoading(true)
    try {
      const r = await sendTestPush()
      const n = Number(r?.enviados ?? 0)
      if (n > 0) {
        showMsg(`Notificação de teste enviada para ${n} dispositivo${n > 1 ? 's' : ''}. Se não chegar em alguns segundos, verifique se o "Não perturbe" está desligado e se as notificações do navegador estão liberadas no sistema.`)
      } else {
        showMsg('O servidor não encontrou nenhum dispositivo cadastrado para esta conta. Desative o botão acima e ative novamente — provavelmente a assinatura precisou ser renovada.', 'err')
      }
    } catch (e) {
      showMsg(e?.message || 'Falha ao enviar teste.', 'err')
    } finally {
      setLoading(false)
    }
  }

  if (!isPushSupported()) {
    return (
      <div style={styles.row}>
        <div style={styles.info}>
          <span style={styles.title}>Notificações push</span>
          <span style={styles.sub}>Seu navegador não suporta notificações push.</span>
        </div>
        <span style={{ fontSize: 12, color: 'var(--text-muted)', fontStyle: 'italic' }}>Indisponível</span>
      </div>
    )
  }

  const isBlocked = status?.permission === 'denied'
  const isSubscribed = status?.subscribed

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      <div style={styles.row}>
        <div style={styles.info}>
          <span style={styles.title}>Notificações push</span>
          <span style={styles.sub}>
            {isBlocked
              ? 'Permissão bloqueada — libere nas configurações do navegador.'
              : isSubscribed
                ? 'Ativas neste dispositivo. Você recebe alertas de ofertas, compras e mensagens.'
                : 'Ative para receber alertas de novas ofertas, compras e mensagens em tempo real.'}
          </span>
        </div>

        <button
          onClick={handleToggle}
          disabled={loading || isBlocked || !status}
          style={{
            ...styles.toggle,
            background: isSubscribed ? 'var(--brand)' : 'var(--surface-2)',
            cursor: loading || isBlocked ? 'not-allowed' : 'pointer',
            opacity: isBlocked ? 0.5 : 1,
          }}
          title={isBlocked ? 'Permissão bloqueada no navegador' : isSubscribed ? 'Desativar' : 'Ativar'}
        >
          <span style={{
            ...styles.thumb,
            transform: isSubscribed ? 'translateX(20px)' : 'translateX(2px)',
            background: '#fff',
          }} />
        </button>
      </div>

      {isSubscribed && (
        <button
          onClick={handleTest}
          disabled={loading}
          style={styles.testBtn}
        >
          {loading ? 'Enviando…' : 'Enviar notificação de teste'}
        </button>
      )}

      {msg && (
        <div style={{
          padding: '10px 14px', borderRadius: 8, fontSize: 13,
          background: msg.type === 'err' ? 'var(--error-bg, #fff0f0)' : 'var(--success-bg, #f0fdf4)',
          color: msg.type === 'err' ? 'var(--error, #DC2626)' : 'var(--success, #16A34A)',
          border: `1px solid ${msg.type === 'err' ? 'var(--error, #DC2626)' : 'var(--success, #16A34A)'}`,
        }}>
          {msg.text}
        </div>
      )}
    </div>
  )
}

const styles = {
  row: {
    display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 16,
  },
  info: {
    display: 'flex', flexDirection: 'column', gap: 3, flex: 1, minWidth: 0,
  },
  title: {
    fontSize: 14, fontWeight: 600, color: 'var(--text-primary)',
  },
  sub: {
    fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.5,
  },
  toggle: {
    width: 44, height: 24, borderRadius: 99, border: 'none',
    position: 'relative', flexShrink: 0,
    transition: 'background .2s',
  },
  thumb: {
    position: 'absolute', top: 2, width: 20, height: 20,
    borderRadius: '50%', boxShadow: '0 1px 4px rgba(0,0,0,.25)',
    transition: 'transform .2s',
    display: 'block',
  },
  testBtn: {
    background: 'none', border: '1px solid var(--border)',
    color: 'var(--text-muted)', fontSize: 12, fontWeight: 600,
    padding: '7px 14px', borderRadius: 8, cursor: 'pointer',
    alignSelf: 'flex-start',
    transition: 'border-color .15s, color .15s',
  },
}
