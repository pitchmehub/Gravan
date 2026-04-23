import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { api } from '../lib/api'

export default function Analytics() {
  const { perfil } = useAuth()
  const navigate = useNavigate()
  const [data, setData]       = useState(null)
  const [loading, setLoading] = useState(true)
  const [erro, setErro]       = useState('')

  const isPro = perfil?.plano === 'PRO' && perfil?.status_assinatura !== 'inativa'

  useEffect(() => {
    if (!isPro) { setLoading(false); return }
    api.get('/analytics/resumo')
      .then(setData)
      .catch(e => setErro(e.message))
      .finally(() => setLoading(false))
  }, [isPro])

  if (!isPro) {
    return (
      <div data-testid="analytics-locked" style={{
        padding: 48, maxWidth: 600, margin: '60px auto 0', textAlign: 'center',
        border: '1px dashed var(--border)', borderRadius: 14, background: 'var(--surface-2,#fafafa)',
      }}>
        <div style={{
          display: 'inline-block', padding: '4px 10px', background: 'var(--brand)',
          color: '#fff', fontSize: 10, fontWeight: 700, letterSpacing: 1.2, borderRadius: 4,
          marginBottom: 14,
        }}>RECURSO PRO</div>
        <h1 style={{ fontSize: 20, fontWeight: 700, marginBottom: 8 }}>
          Disponível apenas para usuários PRO
        </h1>
        <p style={{ color: 'var(--text-muted)', fontSize: 13, marginBottom: 20 }}>
          Veja plays, curtidas e engajamento de cada uma das suas obras.
          Economize <b>5% em todas as transações</b> e desbloqueie analytics por R$ 29,90/mês.
        </p>
        <button data-testid="btn-upgrade-pro" className="btn btn-primary" onClick={() => navigate('/planos')}>
          Conhecer o plano PRO
        </button>
      </div>
    )
  }

  return (
    <div data-testid="analytics-page" style={{ padding: '32px 20px', maxWidth: 1000, margin: '0 auto' }}>
      <header style={{ marginBottom: 24, display: 'flex', alignItems: 'baseline', gap: 10 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700 }}>Analytics</h1>
        <span style={{ padding: '3px 8px', background: 'var(--brand)', color: '#fff', fontSize: 10, fontWeight: 700, letterSpacing: 1, borderRadius: 4 }}>PRO</span>
      </header>

      {loading && <p style={{ color: 'var(--text-muted)' }}>Carregando métricas…</p>}
      {erro && <p style={{ color: '#c0392b' }}>⚠ {erro}</p>}

      {data && (
        <>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 12, marginBottom: 24 }}>
            <KPI label="Total de plays"    value={data.total_plays}     testid="kpi-plays" />
            <KPI label="Total de curtidas" value={data.total_favoritos} testid="kpi-favoritos" />
            <KPI label="Obras ativas"      value={data.obras?.length ?? 0} testid="kpi-obras" />
          </div>

          <h2 style={{ fontSize: 14, fontWeight: 600, marginBottom: 10, color: 'var(--text-secondary)' }}>
            Ranking de engajamento
          </h2>
          <div style={{ border: '1px solid var(--border)', borderRadius: 12, overflow: 'hidden' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead style={{ background: 'var(--surface-2,#fafafa)' }}>
                <tr>
                  <th style={th}>#</th>
                  <th style={th}>Obra</th>
                  <th style={{ ...th, textAlign: 'right' }}>Plays</th>
                  <th style={{ ...th, textAlign: 'right' }}>Curtidas</th>
                  <th style={{ ...th, textAlign: 'right' }}>Último play</th>
                </tr>
              </thead>
              <tbody>
                {(data.obras || []).map((o, i) => (
                  <tr key={o.obra_id} data-testid={`ranking-row-${i}`} style={{ borderTop: '1px solid var(--border)' }}>
                    <td style={td}>{i + 1}</td>
                    <td style={td}>{o.nome}</td>
                    <td style={{ ...td, textAlign: 'right', fontWeight: 600 }}>{o.plays}</td>
                    <td style={{ ...td, textAlign: 'right', fontWeight: 600 }}>{o.favoritos}</td>
                    <td style={{ ...td, textAlign: 'right', color: 'var(--text-muted)', fontSize: 11 }}>
                      {o.last_played_at ? new Date(o.last_played_at).toLocaleDateString('pt-BR') : '—'}
                    </td>
                  </tr>
                ))}
                {(data.obras || []).length === 0 && (
                  <tr><td style={{ ...td, textAlign: 'center', color: 'var(--text-muted)' }} colSpan={5}>
                    Sem obras ainda.
                  </td></tr>
                )}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  )
}

function KPI({ label, value, testid }) {
  return (
    <div data-testid={testid} style={{
      padding: 18, background: '#fff', border: '1px solid var(--border)', borderRadius: 12,
    }}>
      <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 6 }}>{label}</div>
      <div style={{ fontSize: 26, fontWeight: 800 }}>{(value ?? 0).toLocaleString('pt-BR')}</div>
    </div>
  )
}

const th = { textAlign: 'left', padding: '10px 14px', fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 0.5 }
const td = { padding: '12px 14px', verticalAlign: 'middle' }
