import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { api } from '../lib/api'
import SeloPro, { isPerfilPro } from '../components/SeloPro'

const fmtBRL = (cents) => (Number(cents || 0) / 100).toLocaleString('pt-BR', {
  style: 'currency', currency: 'BRL', minimumFractionDigits: 2,
})

export default function Analytics() {
  const { perfil } = useAuth()
  const navigate = useNavigate()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [erro, setErro] = useState('')

  const isPro = isPerfilPro(perfil)

  useEffect(() => {
    api.get('/analytics/resumo')
      .then(setData)
      .catch(e => setErro(e.message))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div data-testid="analytics-page" style={{ padding: '32px 20px', maxWidth: 1100, margin: '0 auto' }}>
      <header style={{ marginBottom: 8, display: 'flex', alignItems: 'baseline', gap: 10, flexWrap: 'wrap' }}>
        <h1 style={{ fontSize: 22, fontWeight: 700 }}>Analytics</h1>
        <SeloPro ativo={isPro} size="md" />
        {!isPro && (
          <span style={{
            padding: '3px 8px', background: '#f3f4f6', color: '#6b7280',
            fontSize: 10, fontWeight: 700, letterSpacing: 1, borderRadius: 4,
          }}>
            VOCÊ ESTÁ NO PLANO GRÁTIS
          </span>
        )}
      </header>
      <p style={{ color: 'var(--text-muted)', fontSize: 13, marginBottom: 24 }}>
        Acompanhe engajamento, receita e quanto você está economizando (ou poderia economizar) com o plano PRO.
      </p>

      {loading && <p style={{ color: 'var(--text-muted)' }}>Carregando métricas…</p>}
      {erro && <p style={{ color: '#c0392b' }}>{erro}</p>}

      {data && (
        <>
          {/* Banner de upgrade para STARTER com economia significativa */}
          {!isPro && data.economia_mes_cents > 0 && (
            <UpgradeBanner
              economiaMes={data.economia_mes_cents}
              economiaTotal={data.economia_total_cents}
              assinaturaCents={data.assinatura_pro_cents}
              onUpgrade={() => navigate('/planos')}
            />
          )}

          {/* ── 1. ENGAJAMENTO ─────────────────────────── */}
          <Section title="Engajamento">
            <div style={kpiGrid}>
              <KPI label="Total de plays" value={data.total_plays?.toLocaleString('pt-BR')} testid="kpi-plays" />
              <KPI label="Total de curtidas" value={data.total_favoritos?.toLocaleString('pt-BR')} testid="kpi-favoritos" />
              <KPI label="Obras ativas" value={(data.obras?.length ?? 0).toLocaleString('pt-BR')} testid="kpi-obras" />
            </div>
          </Section>

          {/* ── 2. ECONOMIA PRO ────────────────────────── */}
          <Section
            title={isPro ? 'Sua economia PRO' : 'Quanto você economizaria sendo PRO'}
            subtitle={
              isPro
                ? 'A diferença entre 20% (Grátis) e 15% (PRO) sobre cada venda volta para o seu bolso.'
                : 'Mostramos o quanto você teria economizado em comissão se já fosse PRO. Vire PRO agora e comece a economizar.'
            }
          >
            <div style={kpiGrid}>
              <KPI
                label={isPro ? 'Economia este mês' : 'Você economizaria este mês'}
                value={fmtBRL(data.economia_mes_cents)}
                accent={!isPro ? '#2563eb' : '#10b981'}
                testid="kpi-economia-mes"
              />
              <KPI
                label={isPro ? 'Economia acumulada' : 'Economia potencial acumulada'}
                value={fmtBRL(data.economia_total_cents)}
                accent={!isPro ? '#2563eb' : '#10b981'}
                testid="kpi-economia-total"
              />
              <KPI
                label="ROI da assinatura (mês)"
                value={data.roi_mes_pct == null ? '—' : `${data.roi_mes_pct > 0 ? '+' : ''}${data.roi_mes_pct}%`}
                accent={data.roi_mes_pct > 0 ? '#10b981' : '#6b7280'}
                testid="kpi-roi"
              />
            </div>
            <div style={contextBox}>
              {isPro ? (
                <>
                  Sua assinatura PRO custa <b>{fmtBRL(data.assinatura_pro_cents)}/mês</b>.
                  Você já economizou <b>{fmtBRL(data.economia_mes_cents)}</b> este mês.
                  {data.roi_mes_pct != null && (
                    <> ROI: <b style={{ color: data.roi_mes_pct > 0 ? '#10b981' : '#c0392b' }}>
                      {data.roi_mes_pct > 0 ? '+' : ''}{data.roi_mes_pct}%
                    </b></>
                  )}
                </>
              ) : (
                <>
                  Pelo plano Grátis, a Gravan retém 20% de cada venda. PRO retém 15%.
                  Sobre suas vendas deste mês, isso seria uma economia de <b>{fmtBRL(data.economia_mes_cents)}</b>
                  {' '}contra a mensalidade de <b>{fmtBRL(data.assinatura_pro_cents)}</b>.
                  {' '}<button onClick={() => navigate('/planos')}
                    style={linkBtn} data-testid="btn-upgrade-economia">
                    Conhecer o plano PRO →
                  </button>
                </>
              )}
            </div>
          </Section>

          {/* ── 3. FINANCEIRO ──────────────────────────── */}
          <Section
            title="Financeiro"
            subtitle="Total licenciado e receita líquida (após comissão da plataforma)."
          >
            <div style={kpiGrid}>
              <KPI label="Licenciado este mês" value={fmtBRL(data.receita_mes_cents)} testid="kpi-receita-mes" />
              <KPI label="Licenciado total" value={fmtBRL(data.receita_total_cents)} testid="kpi-receita-total" />
              <KPI
                label="Receita líquida (mês)"
                value={fmtBRL(data.receita_liquida_mes_cents)}
                accent="#10b981"
                testid="kpi-liquido-mes"
              />
              <KPI
                label="Receita líquida (total)"
                value={fmtBRL(data.receita_liquida_total_cents)}
                accent="#10b981"
                testid="kpi-liquido-total"
              />
            </div>

            <h3 style={subTitle}>Ranking de obras por receita</h3>
            <RankingTable
              rows={data.ranking_receita || []}
              colunas={[
                { label: 'Obra', render: (o) => o.nome },
                { label: 'Plays', render: (o) => o.plays.toLocaleString('pt-BR'), align: 'right' },
                { label: 'Receita', render: (o) => fmtBRL(o.receita_cents), align: 'right', bold: true },
              ]}
              emptyMsg="Nenhuma venda registrada ainda."
            />
          </Section>

          {/* ── 4. RANKING DE ENGAJAMENTO ──────────────── */}
          <Section title="Ranking de engajamento" subtitle="Suas obras ordenadas por plays + 3× curtidas.">
            <RankingTable
              rows={data.obras || []}
              colunas={[
                { label: 'Obra', render: (o) => o.nome },
                { label: 'Plays', render: (o) => o.plays.toLocaleString('pt-BR'), align: 'right', bold: true },
                { label: 'Curtidas', render: (o) => o.favoritos.toLocaleString('pt-BR'), align: 'right', bold: true },
                {
                  label: 'Último play',
                  render: (o) => o.last_played_at
                    ? new Date(o.last_played_at).toLocaleDateString('pt-BR')
                    : '—',
                  align: 'right',
                  muted: true,
                },
              ]}
              emptyMsg="Sem obras ainda."
            />
          </Section>

          {/* CTA final pra STARTER */}
          {!isPro && (
            <div style={{
              marginTop: 32, padding: 24, borderRadius: 12,
              background: 'linear-gradient(135deg, #1e3a8a, #2563eb)', color: '#fff',
              textAlign: 'center',
            }}>
              <h3 style={{ fontSize: 18, fontWeight: 700, marginBottom: 8 }}>
                Pronto para faturar mais por obra?
              </h3>
              <p style={{ fontSize: 13, opacity: 0.92, marginBottom: 16 }}>
                Vire PRO por {fmtBRL(data.assinatura_pro_cents)}/mês e desbloqueie obras até R$ 10.000, comissão de 15% e ofertas de exclusividade.
              </p>
              <button
                data-testid="btn-upgrade-final"
                onClick={() => navigate('/planos')}
                style={{
                  padding: '12px 22px', borderRadius: 8, border: 'none',
                  background: '#fff', color: '#1e3a8a', fontWeight: 700,
                  fontSize: 14, cursor: 'pointer',
                }}
              >
                Assinar plano PRO
              </button>
            </div>
          )}
        </>
      )}
    </div>
  )
}

/* ───────────────────────── helpers ───────────────────────── */

function Section({ title, subtitle, children }) {
  return (
    <section style={{ marginBottom: 32 }}>
      <h2 style={{ fontSize: 15, fontWeight: 700, marginBottom: 4, color: '#111' }}>
        {title}
      </h2>
      {subtitle && (
        <p style={{ fontSize: 12, color: 'var(--text-muted, #71717A)', marginBottom: 12 }}>
          {subtitle}
        </p>
      )}
      {children}
    </section>
  )
}

function KPI({ label, value, testid, accent }) {
  return (
    <div data-testid={testid} style={{
      padding: 18, background: '#fff', border: '1px solid var(--border, #e5e7eb)',
      borderRadius: 12,
    }}>
      <div style={{
        fontSize: 11, color: 'var(--text-muted, #71717A)',
        textTransform: 'uppercase', letterSpacing: 1, marginBottom: 6,
      }}>
        {label}
      </div>
      <div style={{ fontSize: 24, fontWeight: 800, color: accent || '#111' }}>
        {value ?? '—'}
      </div>
    </div>
  )
}

function RankingTable({ rows, colunas, emptyMsg }) {
  return (
    <div style={{ border: '1px solid var(--border, #e5e7eb)', borderRadius: 12, overflow: 'hidden', overflowX: 'auto' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
        <thead style={{ background: 'var(--surface-2, #fafafa)' }}>
          <tr>
            <th style={th}>#</th>
            {colunas.map((c, i) => (
              <th key={i} style={{ ...th, textAlign: c.align || 'left' }}>{c.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 && (
            <tr><td colSpan={colunas.length + 1} style={{
              ...td, textAlign: 'center', color: 'var(--text-muted, #71717A)',
            }}>{emptyMsg}</td></tr>
          )}
          {rows.map((o, i) => (
            <tr key={o.obra_id} data-testid={`ranking-row-${i}`} style={{ borderTop: '1px solid var(--border, #e5e7eb)' }}>
              <td style={td}>{i + 1}</td>
              {colunas.map((c, j) => (
                <td key={j} style={{
                  ...td,
                  textAlign: c.align || 'left',
                  fontWeight: c.bold ? 600 : 400,
                  color: c.muted ? 'var(--text-muted, #71717A)' : 'inherit',
                  fontSize: c.muted ? 11 : 13,
                }}>
                  {c.render(o)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function UpgradeBanner({ economiaMes, economiaTotal, assinaturaCents, onUpgrade }) {
  return (
    <div data-testid="upgrade-banner" style={{
      marginBottom: 24, padding: 18, borderRadius: 12,
      background: 'linear-gradient(135deg, #1e3a8a, #2563eb)', color: '#fff',
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      gap: 16, flexWrap: 'wrap',
    }}>
      <div>
        <div style={{ fontSize: 12, fontWeight: 700, letterSpacing: 1, opacity: 0.85, marginBottom: 4 }}>
          VOCÊ ESTÁ DEIXANDO DINHEIRO NA MESA
        </div>
        <div style={{ fontSize: 16, fontWeight: 700 }}>
          {fmtBRL(economiaMes)} este mês · {fmtBRL(economiaTotal)} no total
        </div>
        <div style={{ fontSize: 12, opacity: 0.9, marginTop: 2 }}>
          Quanto você teria economizado em comissão sendo PRO ({fmtBRL(assinaturaCents)}/mês).
        </div>
      </div>
      <button
        onClick={onUpgrade}
        style={{
          padding: '10px 18px', borderRadius: 8, border: 'none',
          background: '#fff', color: '#1e3a8a', fontWeight: 700,
          fontSize: 13, cursor: 'pointer', whiteSpace: 'nowrap',
        }}
      >
        Virar PRO
      </button>
    </div>
  )
}

const kpiGrid = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
  gap: 12, marginBottom: 8,
}
const subTitle = { fontSize: 13, fontWeight: 600, marginTop: 16, marginBottom: 10, color: 'var(--text-secondary, #4b5563)' }
const contextBox = {
  marginTop: 12, padding: 12, borderRadius: 10,
  background: 'var(--surface-2, #fafafa)', border: '1px solid var(--border, #e5e7eb)',
  fontSize: 13, color: '#333', lineHeight: 1.5,
}
const linkBtn = {
  background: 'none', border: 'none', color: '#2563eb',
  fontWeight: 600, cursor: 'pointer', padding: 0, fontSize: 13,
}
const th = { textAlign: 'left', padding: '10px 14px', fontSize: 11, fontWeight: 600, color: 'var(--text-muted, #71717A)', textTransform: 'uppercase', letterSpacing: 0.5 }
const td = { padding: '12px 14px', verticalAlign: 'middle' }
