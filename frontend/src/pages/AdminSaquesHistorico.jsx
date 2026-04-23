import React, { useState, useCallback } from 'react'
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

  const STATUS_INFO = {
    pendente_otp:         { bg: '#FEF3C7', cor: '#92400E', label: '✉ Aguardando OTP' },
    aguardando_liberacao: { bg: '#DBEAFE', cor: '#1E40AF', label: '⏳ Janela de 24h' },
    processando:          { bg: '#EDE9FE', cor: '#5B21B6', label: '↻ Processando' },
    pago:                 { bg: '#D1FAE5', cor: '#065F46', label: '✓ Pago' },
    rejeitado:            { bg: '#FEE2E2', cor: '#991B1B', label: '✕ Rejeitado' },
    cancelado:            { bg: '#F3F4F6', cor: '#6B7280', label: '🚫 Cancelado' },
    expirado:             { bg: '#F3F4F6', cor: '#9CA3AF', label: '⌛ Expirado' },
    solicitado:           { bg: '#FEF9C3', cor: '#854D0E', label: '⏱ Solicitado' },
  }

  function downloadCSV(rows) {
    const headers = ['ID','Usuário','E-mail','Valor (R$)','Status','Solicitado em','Confirmado em','Liberado em','Cancelado em','Motivo cancelamento']
    const lines = [headers.join(';')]
    rows.forEach(s => {
      const vals = [
        s.id || '',
        s.perfis?.nome_artistico || s.perfis?.nome || '',
        s.perfis?.email || '',
        ((s.valor_cents ?? 0) / 100).toFixed(2).replace('.', ','),
        s.status || '',
        fmtDt(s.created_at),
        fmtDt(s.confirmado_em),
        fmtDt(s.liberar_em),
        fmtDt(s.cancelado_em),
        (s.cancelado_motivo || '').replace(/;/g, ','),
      ]
      lines.push(vals.map(v => `"${String(v).replace(/"/g, '""')}"`).join(';'))
    })
    const blob = new Blob([lines.join('\n')], { type: 'text/csv;charset=utf-8;' })
    const url  = URL.createObjectURL(blob)
    const a    = document.createElement('a'); a.href = url
    a.download = `saques_${new Date().toISOString().slice(0,10)}.csv`
    a.click(); URL.revokeObjectURL(url)
  }

  const hoje = new Date().toISOString().slice(0, 10)
  const ha30 = new Date(Date.now() - 30 * 86400000).toISOString().slice(0, 10)

  export default function AdminSaquesHistorico() {
    const navigate = useNavigate()

    const [busca,      setBusca]      = useState('')
    const [status,     setStatus]     = useState('')
    const [dataInicio, setDataInicio] = useState(ha30)
    const [dataFim,    setDataFim]    = useState(hoje)
    const [limite,     setLimite]     = useState('200')

    const [saques,  setSaques]  = useState([])
    const [loading, setLoading] = useState(false)
    const [buscado, setBuscado] = useState(false)
    const [erro,    setErro]    = useState('')

    const buscar = useCallback(async () => {
      setLoading(true); setErro(''); setBuscado(false)
      try {
        const params = new URLSearchParams()
        if (busca.trim())  params.set('q',          busca.trim())
        if (status)        params.set('status',      status)
        if (dataInicio)    params.set('data_inicio', dataInicio)
        if (dataFim)       params.set('data_fim',    dataFim + 'T23:59:59')
        params.set('limit', limite || '200')
        const result = await api.get(`/admin/saques/historico?${params}`)
        setSaques(Array.isArray(result) ? result : [])
        setBuscado(true)
      } catch (e) {
        setErro(e.message || 'Erro ao buscar saques.')
      } finally {
        setLoading(false)
      }
    }, [busca, status, dataInicio, dataFim, limite])

    const totalBrl = saques.filter(s => s.status === 'pago').reduce((a, s) => a + (s.valor_cents || 0), 0)

    const label = { style: { fontSize: 12, fontWeight: 600, color: 'var(--text-muted)', marginBottom: 4, display: 'block' } }
    const inp   = { style: { padding: '8px 10px', borderRadius: 8, border: '1px solid var(--border)', fontSize: 13, background: 'var(--surface)', color: 'var(--text)', width: '100%', boxSizing: 'border-box' } }

    return (
      <div style={{ padding: 32, maxWidth: 1200 }}>

        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 24 }}>
          <button onClick={() => navigate('/admin/saques')}
            style={{ background: 'none', border: 'none', color: 'var(--brand)', cursor: 'pointer', fontSize: 20, padding: 0 }}>←</button>
          <div>
            <h1 style={{ fontSize: 24, fontWeight: 800, margin: 0 }}>Histórico de Saques</h1>
            <p style={{ fontSize: 13, color: 'var(--text-muted)', margin: 0 }}>Pesquise e exporte saques com filtros avançados</p>
          </div>
        </div>

        {/* Filters */}
        <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 14, padding: 20, marginBottom: 20 }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 14 }}>
            <div>
              <label {...label}>🔍 Buscar por nome ou e-mail</label>
              <input {...inp} value={busca} onChange={e => setBusca(e.target.value)}
                placeholder="maria@email.com" onKeyDown={e => e.key === 'Enter' && buscar()} />
            </div>
            <div>
              <label {...label}>Status</label>
              <select {...inp} value={status} onChange={e => setStatus(e.target.value)}>
                <option value="">Todos os status</option>
                <option value="pendente_otp">✉ Aguardando OTP</option>
                <option value="aguardando_liberacao">⏳ Janela de 24h</option>
                <option value="processando">↻ Processando</option>
                <option value="pago">✓ Pago</option>
                <option value="cancelado">🚫 Cancelado</option>
                <option value="rejeitado">✕ Rejeitado</option>
                <option value="expirado">⌛ Expirado</option>
                <option value="solicitado">⏱ Solicitado (legado)</option>
              </select>
            </div>
            <div>
              <label {...label}>📅 Data início</label>
              <input {...inp} type="date" value={dataInicio} onChange={e => setDataInicio(e.target.value)} />
            </div>
            <div>
              <label {...label}>📅 Data fim</label>
              <input {...inp} type="date" value={dataFim} onChange={e => setDataFim(e.target.value)} />
            </div>
            <div>
              <label {...label}>Limite de resultados</label>
              <select {...inp} value={limite} onChange={e => setLimite(e.target.value)}>
                <option value="50">50 registros</option>
                <option value="200">200 registros</option>
                <option value="500">500 registros</option>
                <option value="1000">1.000 registros</option>
              </select>
            </div>
          </div>
          <div style={{ marginTop: 14, display: 'flex', gap: 10 }}>
            <button onClick={buscar} disabled={loading} style={{
              padding: '10px 24px', borderRadius: 10, fontWeight: 700, fontSize: 14,
              background: 'var(--brand)', color: '#fff', border: 'none', cursor: 'pointer', opacity: loading ? 0.7 : 1,
            }}>{loading ? 'Buscando…' : '🔍 Buscar'}</button>
            {saques.length > 0 && (
              <button onClick={() => downloadCSV(saques)} style={{
                padding: '10px 20px', borderRadius: 10, fontWeight: 700, fontSize: 14,
                background: '#D1FAE5', color: '#065F46', border: '1px solid #A7F3D0', cursor: 'pointer',
              }}>⬇ Exportar CSV ({saques.length})</button>
            )}
          </div>
          {erro && <p style={{ marginTop: 10, color: 'var(--error)', fontSize: 13 }}>{erro}</p>}
        </div>

        {/* Resumo */}
        {buscado && (
          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 16 }}>
            {[
              { label: 'Total encontrado', value: saques.length + ' saques' },
              { label: 'Total pago (filtro)', value: fmt(totalBrl), color: '#065F46' },
            ].map(c => (
              <div key={c.label} style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 12, padding: '12px 18px' }}>
                <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>{c.label}</div>
                <div style={{ fontSize: 20, fontWeight: 800, color: c.color || 'var(--text)', marginTop: 4 }}>{c.value}</div>
              </div>
            ))}
          </div>
        )}

        {/* Results */}
        {!buscado && !loading && (
          <div style={{ textAlign: 'center', padding: '48px 24px', color: 'var(--text-muted)', background: 'var(--surface)', borderRadius: 14, border: '1px solid var(--border)' }}>
            <div style={{ fontSize: 40, marginBottom: 12 }}>🔍</div>
            <p style={{ fontWeight: 600, margin: 0 }}>Defina os filtros e clique em Buscar</p>
            <p style={{ fontSize: 13, marginTop: 6 }}>Por padrão os últimos 30 dias já estão selecionados</p>
          </div>
        )}

        {buscado && saques.length === 0 && (
          <div style={{ textAlign: 'center', padding: '48px 24px', color: 'var(--text-muted)', background: 'var(--surface)', borderRadius: 14, border: '1px solid var(--border)' }}>
            <div style={{ fontSize: 40, marginBottom: 12 }}>📭</div>
            <p style={{ fontWeight: 600, margin: 0 }}>Nenhum saque encontrado para esses filtros</p>
          </div>
        )}

        {saques.length > 0 && (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ background: 'var(--surface-2)', borderBottom: '2px solid var(--border)' }}>
                  {['Usuário', 'E-mail', 'Valor', 'Status', 'Solicitado', 'Confirmar até / Liberar em'].map(h => (
                    <th key={h} style={{ textAlign: 'left', padding: '10px 12px', fontWeight: 700, whiteSpace: 'nowrap', color: 'var(--text-muted)' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {saques.map((s, i) => {
                  const st = STATUS_INFO[s.status] || STATUS_INFO.solicitado
                  return (
                    <tr key={s.id} style={{ borderBottom: '1px solid var(--border)', background: i % 2 === 0 ? 'var(--surface)' : 'transparent' }}>
                      <td style={{ padding: '10px 12px', fontWeight: 600 }}>{s.perfis?.nome_artistico || s.perfis?.nome || '—'}</td>
                      <td style={{ padding: '10px 12px', color: 'var(--text-muted)' }}>{s.perfis?.email || '—'}</td>
                      <td style={{ padding: '10px 12px', fontWeight: 700 }}>{fmt(s.valor_cents)}</td>
                      <td style={{ padding: '10px 12px' }}>
                        <span style={{ fontSize: 11, fontWeight: 600, padding: '3px 10px', borderRadius: 99, background: st.bg, color: st.cor, whiteSpace: 'nowrap' }}>
                          {st.label}
                        </span>
                      </td>
                      <td style={{ padding: '10px 12px', whiteSpace: 'nowrap', color: 'var(--text-muted)' }}>{fmtDt(s.created_at)}</td>
                      <td style={{ padding: '10px 12px', whiteSpace: 'nowrap', color: 'var(--text-muted)' }}>
                        {s.otp_expires_at ? fmtDt(s.otp_expires_at) : ''}
                        {s.liberar_em ? fmtDt(s.liberar_em) : ''}
                        {s.cancelado_em ? <span style={{ color: '#991B1B' }}>{fmtDt(s.cancelado_em)}</span> : null}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}

      </div>
    )
  }
  