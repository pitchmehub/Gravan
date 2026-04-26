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
  const isPro = isPerfilPro(perfil)

  if (!isPro) {
    return <AnalyticsPaywall />
  }
  return <AnalyticsDashboard />
}

/* ============================================================
   PAYWALL — usuários grátis
   ============================================================ */

function AnalyticsPaywall() {
  const navigate = useNavigate()

  const beneficios = [
    {
      icone: '%',
      titulo: 'COMISSÃO',
      itens: [
        'Fee reduzido de 20% para 15%',
        'Mais lucro em cada venda',
      ],
    },
    {
      icone: 'R$',
      titulo: 'PRECIFICAÇÃO',
      itens: [
        'Precifique de R$ 500 a R$ 10.000',
        'Acesso a compradores premium',
      ],
    },
    {
      icone: '✦',
      titulo: 'OFERTAS',
      itens: [
        'Receba ofertas diretas de compradores',
        'Negocie sem sair do app',
        'Aceite, recuse ou contra-proponha',
        'Licenciamento com exclusividade',
      ],
    },
    {
      icone: '◎',
      titulo: 'VISIBILIDADE',
      itens: [
        'Prioridade na aba Descoberta',
        'Selo PRO no perfil e nas obras',
        'Mais chances de ser escolhido',
      ],
    },
    {
      icone: '◔',
      titulo: 'ANALYTICS',
      itens: [
        'Dashboard financeiro completo',
        'Veja quanto você economizou sendo PRO',
        'Descubra o que está vendendo mais',
        'Tome decisões com base em dados',
      ],
      destaque: true,
    },
  ]

  return (
    <div data-testid="analytics-paywall" style={{
      minHeight: '100%',
      background: 'linear-gradient(180deg, #F7F5EE 0%, #FFFFFF 60%)',
      padding: '40px 20px 80px',
    }}>
      <div style={{ maxWidth: 980, margin: '0 auto' }}>

        {/* HERO */}
        <div style={{
          textAlign: 'center',
          marginBottom: 40,
        }}>
          <div style={{
            display: 'inline-flex', alignItems: 'center', gap: 8,
            padding: '6px 14px',
            background: 'linear-gradient(135deg, #0C447C, #378ADD)',
            color: '#fff',
            fontSize: 11, fontWeight: 800, letterSpacing: 1.5,
            borderRadius: 999,
            marginBottom: 18,
            boxShadow: '0 4px 14px rgba(12,68,124,0.25)',
          }}>
            <span style={{ fontSize: 14 }}>★</span> EXCLUSIVO PARA ASSINANTES PRO
          </div>

          <h1 style={{
            fontSize: 'clamp(28px, 4vw, 40px)',
            fontWeight: 800, letterSpacing: -0.8,
            lineHeight: 1.15, marginBottom: 14,
            color: '#0C447C',
          }}>
            Desbloqueie o seu<br />painel completo de Analytics
          </h1>

          <p style={{
            fontSize: 15, color: 'var(--text-muted)',
            maxWidth: 560, margin: '0 auto', lineHeight: 1.55,
          }}>
            Veja o quanto está vendendo, o quanto está economizando sendo PRO
            e descubra exatamente o que está performando melhor.
            Tudo em um só lugar.
          </p>
        </div>

        {/* PREVIEW MOCKUP DO DASHBOARD (blurred) */}
        <DashboardPreview />

        {/* GRID DE BENEFÍCIOS */}
        <div style={{
          display: 'grid', gap: 16,
          gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
          marginBottom: 40,
        }}>
          {beneficios.map((b) => (
            <BeneficioCard key={b.titulo} {...b} />
          ))}
        </div>

        {/* CTA FINAL */}
        <div style={{
          padding: '36px 24px',
          borderRadius: 18,
          background: 'linear-gradient(135deg, #0C447C 0%, #083257 100%)',
          textAlign: 'center',
          color: '#fff',
          boxShadow: '0 20px 60px rgba(12,68,124,0.30)',
        }}>
          <div style={{
            display: 'inline-block',
            padding: '4px 12px',
            background: 'rgba(255,255,255,0.15)',
            borderRadius: 999,
            fontSize: 11, fontWeight: 700, letterSpacing: 1.5,
            marginBottom: 16,
          }}>
            APENAS R$ 49,90/MÊS
          </div>
          <h2 style={{
            fontSize: 'clamp(20px, 3vw, 26px)',
            fontWeight: 800, marginBottom: 10, letterSpacing: -0.3,
          }}>
            Pare de deixar dinheiro na mesa
          </h2>
          <p style={{
            fontSize: 14, opacity: 0.92, marginBottom: 24,
            maxWidth: 480, margin: '0 auto 24px',
            lineHeight: 1.55,
          }}>
            Com 1 venda de R$ 600 por mês, o PRO já se paga
            só na economia de comissão. Comece hoje.
          </p>

          <button
            data-testid="btn-assine-pro"
            onClick={() => navigate('/planos')}
            style={{
              padding: '16px 38px',
              borderRadius: 10,
              border: 'none',
              background: '#fff',
              color: '#0C447C',
              fontSize: 15,
              fontWeight: 800,
              letterSpacing: 1.5,
              cursor: 'pointer',
              boxShadow: '0 8px 24px rgba(0,0,0,0.18)',
              transition: 'transform .15s ease, box-shadow .15s ease',
            }}
            onMouseDown={(e) => e.currentTarget.style.transform = 'scale(0.97)'}
            onMouseUp={(e) => e.currentTarget.style.transform = 'scale(1)'}
            onMouseLeave={(e) => e.currentTarget.style.transform = 'scale(1)'}
          >
            ASSINE PRO →
          </button>

          <p style={{
            fontSize: 11, opacity: 0.7, marginTop: 18,
          }}>
            Cancele quando quiser. Sem fidelidade.
          </p>
        </div>

      </div>
    </div>
  )
}

function BeneficioCard({ icone, titulo, itens, destaque }) {
  return (
    <article style={{
      background: '#fff',
      border: destaque ? '2px solid #0C447C' : '1px solid var(--border)',
      borderRadius: 14,
      padding: 22,
      position: 'relative',
      boxShadow: destaque
        ? '0 12px 32px rgba(12,68,124,0.12)'
        : '0 2px 8px rgba(0,0,0,0.04)',
    }}>
      {destaque && (
        <div style={{
          position: 'absolute', top: -10, right: 16,
          padding: '3px 10px',
          background: 'linear-gradient(135deg, #0C447C, #378ADD)',
          color: '#fff',
          fontSize: 9, fontWeight: 800, letterSpacing: 1.2,
          borderRadius: 999,
        }}>
          VOCÊ ESTÁ AQUI
        </div>
      )}

      <div style={{
        display: 'flex', alignItems: 'center', gap: 12,
        marginBottom: 14,
      }}>
        <div style={{
          width: 42, height: 42, borderRadius: 10,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          background: 'linear-gradient(135deg, #0C447C, #378ADD)',
          color: '#fff', fontSize: 18, fontWeight: 800,
          flexShrink: 0,
        }}>
          {icone}
        </div>
        <h3 style={{
          fontSize: 13, fontWeight: 800, letterSpacing: 1.5,
          color: '#0C447C', margin: 0,
        }}>
          {titulo}
        </h3>
      </div>

      <ul style={{
        listStyle: 'none', padding: 0, margin: 0,
        display: 'flex', flexDirection: 'column', gap: 8,
      }}>
        {itens.map((item, i) => (
          <li key={i} style={{
            display: 'flex', alignItems: 'flex-start', gap: 8,
            fontSize: 13.5, color: '#3a3a3a', lineHeight: 1.5,
          }}>
            <span style={{
              color: '#0C447C', fontWeight: 800, fontSize: 13,
              flexShrink: 0, marginTop: 1,
            }}>✓</span>
            {item}
          </li>
        ))}
      </ul>
    </article>
  )
}

function DashboardPreview() {
  return (
    <div style={{
      position: 'relative',
      marginBottom: 40,
      borderRadius: 16,
      overflow: 'hidden',
      border: '1px solid var(--border)',
      background: '#fff',
      boxShadow: '0 16px 48px rgba(0,0,0,0.08)',
    }}>
      {/* fake dashboard */}
      <div style={{
        padding: 24,
        filter: 'blur(4px)',
        userSelect: 'none', pointerEvents: 'none',
      }}>
        <div style={{ display: 'flex', gap: 12, marginBottom: 16 }}>
          <FakeKPI label="Economia este mês" value="R$ 1.840,50" accent="#0C447C" />
          <FakeKPI label="Receita líquida" value="R$ 12.350,00" accent="#10b981" />
          <FakeKPI label="ROI da assinatura" value="+264%" accent="#0C447C" />
        </div>
        <div style={{
          height: 140, borderRadius: 10,
          background: 'linear-gradient(180deg, #E6F1FB 0%, #fff 100%)',
          position: 'relative', overflow: 'hidden',
        }}>
          <svg viewBox="0 0 400 140" style={{ width: '100%', height: '100%' }}>
            <polyline
              fill="none" stroke="#0C447C" strokeWidth="3"
              points="0,110 40,95 80,100 120,80 160,70 200,55 240,60 280,40 320,30 360,18 400,10"
            />
            <polyline
              fill="rgba(12,68,124,0.10)" stroke="none"
              points="0,110 40,95 80,100 120,80 160,70 200,55 240,60 280,40 320,30 360,18 400,10 400,140 0,140"
            />
          </svg>
        </div>
      </div>

      {/* lock overlay */}
      <div style={{
        position: 'absolute', inset: 0,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        background: 'rgba(255,255,255,0.55)',
        backdropFilter: 'blur(2px)',
      }}>
        <div style={{
          width: 64, height: 64, borderRadius: '50%',
          background: 'linear-gradient(135deg, #0C447C, #378ADD)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 28, color: '#fff',
          boxShadow: '0 8px 24px rgba(12,68,124,0.35)',
        }}>
          🔒
        </div>
      </div>
    </div>
  )
}

function FakeKPI({ label, value, accent }) {
  return (
    <div style={{
      flex: 1, padding: 14,
      border: '1px solid var(--border)', borderRadius: 10,
      background: '#fff',
    }}>
      <div style={{
        fontSize: 10, color: 'var(--text-muted)',
        textTransform: 'uppercase', letterSpacing: 1, marginBottom: 4,
      }}>{label}</div>
      <div style={{ fontSize: 20, fontWeight: 800, color: accent }}>{value}</div>
    </div>
  )
}

/* ============================================================
   DASHBOARD — usuários PRO
   ============================================================ */

function AnalyticsDashboard() {
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
      </header>
      <p style={{ color: 'var(--text-muted)', fontSize: 13, marginBottom: 24 }}>
        Acompanhe engajamento, receita e quanto você está economizando com o plano PRO.
      </p>

      {loading && <p style={{ color: 'var(--text-muted)' }}>Carregando métricas…</p>}
      {erro && <p style={{ color: '#c0392b' }}>{erro}</p>}

      {data && (
        <>
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
            title="Sua economia PRO"
            subtitle="A diferença entre 20% (Grátis) e 15% (PRO) sobre cada venda volta para o seu bolso."
          >
            <div style={kpiGrid}>
              <KPI
                label="Economia este mês"
                value={fmtBRL(data.economia_mes_cents)}
                accent="#10b981"
                testid="kpi-economia-mes"
              />
              <KPI
                label="Economia acumulada"
                value={fmtBRL(data.economia_total_cents)}
                accent="#10b981"
                testid="kpi-economia-total"
              />
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

          {/* ── 5. OFERTAS E EXCLUSIVIDADE ─────────────── */}
          {data.ofertas && (
            <Section
              title="Ofertas e exclusividade"
              subtitle="Propostas recebidas de intérpretes nas suas obras."
            >
              <div style={kpiGrid}>
                <KPI
                  label="Pendentes"
                  value={data.ofertas.pendentes ?? 0}
                  testid="kpi-ofertas-pendentes"
                  accent="#d97706"
                />
                <KPI
                  label="Aceitas"
                  value={data.ofertas.aceitas ?? 0}
                  testid="kpi-ofertas-aceitas"
                  accent="#10b981"
                />
                <KPI
                  label="Pagas"
                  value={data.ofertas.pagas ?? 0}
                  testid="kpi-ofertas-pagas"
                  accent="#1e3a8a"
                />
                <KPI
                  label="Taxa de conversão"
                  value={
                    data.ofertas.taxa_conversao_pct != null
                      ? `${data.ofertas.taxa_conversao_pct}%`
                      : '—'
                  }
                  testid="kpi-ofertas-conversao"
                />
              </div>

              <div style={kpiGrid}>
                <KPI
                  label="Valor pendente"
                  value={fmtBRL(data.ofertas.valor_pendentes_cents)}
                  testid="kpi-ofertas-valor-pendente"
                />
                <KPI
                  label="Valor pago em ofertas"
                  value={fmtBRL(data.ofertas.valor_pagas_cents)}
                  testid="kpi-ofertas-valor-pago"
                  accent="#10b981"
                />
                <KPI
                  label="Contrapropostas"
                  value={data.ofertas.contra_proposta ?? 0}
                  testid="kpi-ofertas-contra"
                />
                <KPI
                  label="Obras exclusivas"
                  value={data.obras_exclusivas ?? 0}
                  testid="kpi-obras-exclusivas"
                  accent="#7c3aed"
                />
              </div>

              <div style={contextBox}>
                {(data.ofertas.pendentes ?? 0) > 0 ? (
                  <>
                    Você tem <b>{data.ofertas.pendentes}</b> oferta(s) aguardando resposta
                    {' '}({fmtBRL(data.ofertas.valor_pendentes_cents)} em jogo).{' '}
                    <button onClick={() => navigate('/ofertas')} style={linkBtn}>
                      Responder agora →
                    </button>
                  </>
                ) : (
                  <>
                    Quanto mais rápido você responde a uma oferta, maior a chance dela virar venda.
                  </>
                )}
              </div>
            </Section>
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
