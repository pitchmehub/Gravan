import React, { useState, useEffect, useCallback } from 'react'
  import { useNavigate } from 'react-router-dom'
  import { api } from '../lib/api'

  function fmt(cents) {
    return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' })
      .format((cents ?? 0) / 100)
  }
  function fmtDt(iso) {
    if (!iso) return '—'
    return new Date(iso).toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })
  }
  function Countdown({ iso }) {
    const calc = () => {
      if (!iso) return null
      const diff = Math.floor((new Date(iso) - Date.now()) / 1000)
      if (diff <= 0) return 'Pronto para liberar'
      const h = Math.floor(diff / 3600), m = Math.floor((diff % 3600) / 60), s = diff % 60
      if (h > 0) return `${h}h ${m}min`
      return `${m}min ${s}s`
    }
    const [display, setDisplay] = useState(calc)
    useEffect(() => {
      const t = setInterval(() => setDisplay(calc()), 1000)
      return () => clearInterval(t)
    }, [iso])
    if (!iso) return <span style={{ color: 'var(--text-muted)' }}>—</span>
    const isReady = display === 'Pronto para liberar'
    return <span style={{ color: isReady ? 'var(--success)' : 'var(--brand)', fontWeight: 600 }}>{display}</span>
  }

  const STATUS_INFO = {
    pendente_otp:         { bg: '#FEF3C7', cor: '#92400E', label: '✉ Aguardando OTP' },
    aguardando_liberacao: { bg: '#DBEAFE', cor: '#1E40AF', label: '⏳ Na janela de 24h' },
    processando:          { bg: '#EDE9FE', cor: '#5B21B6', label: '↻ Processando' },
    pago:                 { bg: '#D1FAE5', cor: '#065F46', label: '✓ Pago' },
    rejeitado:            { bg: '#FEE2E2', cor: '#991B1B', label: '✕ Rejeitado' },
    cancelado:            { bg: '#F3F4F6', cor: '#6B7280', label: '🚫 Cancelado' },
    expirado:             { bg: '#F3F4F6', cor: '#9CA3AF', label: '⌛ Expirado' },
    solicitado:           { bg: '#FEF9C3', cor: '#854D0E', label: '⏱ Solicitado (legado)' },
  }

  const FILTROS = [
    { id: '',                  label: 'Todos' },
    { id: 'pendente_otp',      label: '✉ Aguardando OTP' },
    { id: 'aguardando_liberacao', label: '⏳ Janela 24h' },
    { id: 'processando',       label: '↻ Processando' },
    { id: 'pago',              label: '✓ Pagos' },
    { id: 'cancelado',         label: '🚫 Cancelados' },
    { id: 'rejeitado',         label: '✕ Rejeitados' },
    { id: 'expirado',          label: '⌛ Expirados' },
  ]

  function StatCard({ label, value, sublabel, color = '#1a1a1a', bg = 'var(--surface)' }) {
    return (
      <div style={{ background: bg, border: '1px solid var(--border)', borderRadius: 14, padding: '16px 18px', minWidth: 140 }}>
        <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 1 }}>{label}</div>
        <div style={{ fontSize: 24, fontWeight: 800, color, marginTop: 6 }}>{value}</div>
        {sublabel && <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>{sublabel}</div>}
      </div>
    )
  }

  export default function AdminSaques() {
    const navigate = useNavigate()
    const [saques, setSaques]       = useState([])
    const [contagens, setContagens] = useState({})
    const [filtro,  setFiltro]      = useState('')
    const [loading, setLoading]     = useState(true)
    const [autoRefresh, setAuto]    = useState(true)
    const [ultimaAt,    setUltimaAt] = useState(null)
    const [acao,   setAcao]         = useState({}) // { [id]: 'loading' | 'ok' | 'erro' }

    const load = useCallback(async (silent = false) => {
      if (!silent) setLoading(true)
      try {
        const params = filtro ? `?status=${filtro}` : ''
        const [lista, painel] = await Promise.all([
          api.get(`/admin/saques${params}`),
          api.get('/admin/saques/painel').catch(() => ({})),
        ])
        setSaques(Array.isArray(lista) ? lista : [])
        setContagens(painel.contagens || {})
        setUltimaAt(new Date())
      } catch (e) {
        console.error('load saques', e)
      } finally {
        setLoading(false)
      }
    }, [filtro])

    useEffect(() => { load() }, [load])
    useEffect(() => {
      if (!autoRefresh) return
      const t = setInterval(() => load(true), 5000)
      return () => clearInterval(t)
    }, [autoRefresh, load])

    async function forcarLiberar(id) {
      if (!confirm('Forçar liberação AGORA, ignorando a janela de 24h?')) return
      setAcao(a => ({ ...a, [id]: 'loading' }))
      try {
        await api.post(`/admin/saques/${id}/forcar-liberar`, {})
        setAcao(a => ({ ...a, [id]: 'ok' }))
        await load(true)
      } catch (e) {
        setAcao(a => ({ ...a, [id]: 'erro' }))
        alert('Erro: ' + (e.message || 'falha ao liberar'))
      }
    }

    async function cancelarAdmin(id) {
      const motivo = prompt('Motivo do cancelamento (obrigatório):')
      if (!motivo) return
      setAcao(a => ({ ...a, [id]: 'loading' }))
      try {
        await api.post(`/admin/saques/${id}/cancelar-admin`, { motivo })
        setAcao(a => ({ ...a, [id]: 'ok' }))
        await load(true)
      } catch (e) {
        setAcao(a => ({ ...a, [id]: 'erro' }))
        alert('Erro: ' + (e.message || 'falha ao cancelar'))
      }
    }

    async function aprovarLegado(id, acao_legada, motivo) {
      if (acao_legada === 'rejeitado') {
        const m = prompt('Motivo da rejeição:')
        if (!m) return
        motivo = m
      }
      if (!confirm(`Confirmar: ${acao_legada}?`)) return
      try {
        await api.post(`/admin/saques/${id}/aprovar`, { acao: acao_legada, motivo })
        await load(true)
      } catch (e) {
        alert('Erro: ' + e.message)
      }
    }

    const pendentesAtivos = (contagens.pendente_otp || 0) + (contagens.aguardando_liberacao || 0) + (contagens.processando || 0)
    const pagosHoje = contagens.pago_hoje || 0
    const totalHoje = contagens.total_hoje_cents || 0

    return (
      <div style={{ padding: 32, maxWidth: 1200 }}>

        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
          <button
            onClick={() => navigate('/admin')}
            style={{ background: 'none', border: 'none', color: 'var(--brand)', cursor: 'pointer', fontSize: 20, padding: 0 }}
            title="Voltar ao painel"
          >←</button>
          <div>
            <h1 style={{ fontSize: 24, fontWeight: 800, margin: 0 }}>Gerenciar Saques</h1>
            <p style={{ fontSize: 13, color: 'var(--text-muted)', margin: 0 }}>
              Controle em tempo real de todos os saques da plataforma
            </p>
          </div>
        </div>

        {/* Historico shortcut */}
        <div style={{ marginBottom: 8 }}>
          <a href="/admin/saques/historico" style={{ fontSize: 13, color: 'var(--brand)', textDecoration: 'none', fontWeight: 600 }}>
            📋 Ver histórico completo & exportar CSV →
          </a>
        </div>

        {/* Stats */}
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 24, marginTop: 20 }}>
          <StatCard label="Pendentes (ativos)" value={pendentesAtivos}
            color={pendentesAtivos > 0 ? '#92400E' : 'var(--text-muted)'} bg={pendentesAtivos > 0 ? '#FEF3C7' : undefined} />
          <StatCard label="✉ Aguardando OTP"   value={contagens.pendente_otp || 0} />
          <StatCard label="⏳ Janela de 24h"    value={contagens.aguardando_liberacao || 0} />
          <StatCard label="↻ Processando"       value={contagens.processando || 0} />
          <StatCard label="✓ Pagos hoje"        value={pagosHoje}
            color={pagosHoje > 0 ? '#065F46' : 'var(--text-muted)'} bg={pagosHoje > 0 ? '#D1FAE5' : undefined}
            sublabel={pagosHoje > 0 ? fmt(totalHoje) : undefined} />
          <StatCard label="🚫 Cancelados hoje"  value={contagens.cancelado_hoje || 0} />
        </div>

        {/* Toolbar */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14, flexWrap: 'wrap', gap: 10 }}>
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            {FILTROS.map(f => (
              <button
                key={f.id}
                onClick={() => setFiltro(f.id)}
                style={{
                  padding: '6px 12px', borderRadius: 20, fontSize: 12, fontWeight: 600, cursor: 'pointer',
                  border: filtro === f.id ? '2px solid var(--brand)' : '1px solid var(--border)',
                  background: filtro === f.id ? 'var(--brand)' : 'var(--surface)',
                  color: filtro === f.id ? '#fff' : 'var(--text)',
                }}
              >{f.label}</button>
            ))}
          </div>
          <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
            <label style={{ fontSize: 12, color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer' }}>
              <input type="checkbox" checked={autoRefresh} onChange={e => setAuto(e.target.checked)} />
              Auto-refresh (5s)
            </label>
            {ultimaAt && (
              <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                Atualizado às {ultimaAt.toLocaleTimeString('pt-BR')}
              </span>
            )}
            <button onClick={() => load()}
              style={{ background: 'none', border: '1px solid var(--border)', padding: '6px 12px', borderRadius: 8, color: 'var(--brand)', fontSize: 12, cursor: 'pointer' }}>
              ↻ Atualizar
            </button>
          </div>
        </div>

        {/* Table */}
        {loading ? (
          <p style={{ color: 'var(--text-muted)', padding: 24 }}>Carregando…</p>
        ) : saques.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '48px 24px', color: 'var(--text-muted)', background: 'var(--surface)', borderRadius: 14, border: '1px solid var(--border)' }}>
            <div style={{ fontSize: 36, marginBottom: 12 }}>💸</div>
            <p style={{ fontWeight: 600, margin: 0 }}>Nenhum saque encontrado</p>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {saques.map(s => {
              const st = STATUS_INFO[s.status] || STATUS_INFO.solicitado
              const isOtpFlow = ['pendente_otp','aguardando_liberacao','processando','cancelado','expirado'].includes(s.status)
              const acaoAtual = acao[s.id]
              return (
                <div key={s.id} style={{
                  padding: '14px 16px', background: 'var(--surface)', borderRadius: 12,
                  border: '1px solid var(--border)',
                  borderLeft: `4px solid ${st.cor}`,
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12, flexWrap: 'wrap' }}>

                    {/* Info principal */}
                    <div style={{ flex: 1, minWidth: 220 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap', marginBottom: 4 }}>
                        <span style={{ fontSize: 18, fontWeight: 800 }}>{fmt(s.valor_cents)}</span>
                        <span style={{ fontSize: 11, fontWeight: 600, padding: '3px 10px', borderRadius: 99, background: st.bg, color: st.cor }}>
                          {st.label}
                        </span>
                      </div>
                      <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text)' }}>
                        {s.perfis?.nome_artistico || s.perfis?.nome || '—'}
                      </div>
                      <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{s.perfis?.email}</div>
                    </div>

                    {/* Datas e timeline */}
                    <div style={{ fontSize: 12, color: 'var(--text-muted)', minWidth: 200 }}>
                      <div>📅 Solicitado: {fmtDt(s.created_at)}</div>
                      {s.confirmado_em && <div>✅ Confirmado: {fmtDt(s.confirmado_em)}</div>}
                      {s.liberar_em && (
                        <div style={{ marginTop: 2 }}>
                          🕐 Liberar em: <Countdown iso={s.liberar_em} />
                          <span style={{ color: 'var(--text-muted)', marginLeft: 4, fontSize: 11 }}>({fmtDt(s.liberar_em)})</span>
                        </div>
                      )}
                      {s.cancelado_em && <div>🚫 Cancelado: {fmtDt(s.cancelado_em)}</div>}
                      {s.cancelado_motivo && <div style={{ color: '#991B1B', fontStyle: 'italic' }}>"{s.cancelado_motivo}"</div>}
                      {s.otp_attempts > 0 && <div>🔑 Tentativas OTP: {s.otp_attempts}</div>}
                      <div style={{ fontSize: 11, marginTop: 2, opacity: 0.7 }}>ID: {s.id?.slice(0,8)}…</div>
                    </div>

                    {/* Ações */}
                    <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center', alignSelf: 'center' }}>
                      {acaoAtual === 'loading' ? (
                        <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>Aguarde…</span>
                      ) : (
                        <>
                          {s.status === 'aguardando_liberacao' && (
                            <button onClick={() => forcarLiberar(s.id)} style={{
                              padding: '7px 14px', borderRadius: 8, fontSize: 12, fontWeight: 700, cursor: 'pointer',
                              background: 'var(--brand)', color: '#fff', border: 'none',
                            }}>⚡ Forçar liberar</button>
                          )}
                          {['pendente_otp','aguardando_liberacao'].includes(s.status) && (
                            <button onClick={() => cancelarAdmin(s.id)} style={{
                              padding: '7px 14px', borderRadius: 8, fontSize: 12, fontWeight: 700, cursor: 'pointer',
                              background: '#FEE2E2', color: '#991B1B', border: '1px solid #FECACA',
                            }}>✕ Cancelar</button>
                          )}
                          {!isOtpFlow && s.status === 'solicitado' && (
                            <>
                              <button onClick={() => aprovarLegado(s.id, 'processando')} style={{
                                padding: '7px 12px', borderRadius: 8, fontSize: 11, fontWeight: 600, cursor: 'pointer',
                                background: 'var(--brand-light)', color: 'var(--brand)', border: '1px solid var(--border)',
                              }}>Processando</button>
                              <button onClick={() => aprovarLegado(s.id, 'pago')} style={{
                                padding: '7px 12px', borderRadius: 8, fontSize: 11, fontWeight: 600, cursor: 'pointer',
                                background: '#D1FAE5', color: '#065F46', border: '1px solid #A7F3D0',
                              }}>✓ Pago</button>
                              <button onClick={() => aprovarLegado(s.id, 'rejeitado')} style={{
                                padding: '7px 12px', borderRadius: 8, fontSize: 11, fontWeight: 600, cursor: 'pointer',
                                background: '#FEE2E2', color: '#991B1B', border: '1px solid #FECACA',
                              }}>✕ Rejeitar</button>
                            </>
                          )}
                          {['pago','rejeitado','cancelado','expirado'].includes(s.status) && (
                            <span style={{ fontSize: 11, color: 'var(--text-muted)', fontStyle: 'italic' }}>Sem ações</span>
                          )}
                        </>
                      )}
                    </div>

                  </div>
                </div>
              )
            })}
          </div>
        )}

      </div>
    )
  }
  