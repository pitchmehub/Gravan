import React from 'react'
import { Link } from 'react-router-dom'

const Section = ({ n, title, children }) => (
  <section style={{ marginBottom: 32 }}>
    <h2 style={{
      fontSize: 18, fontWeight: 700, marginBottom: 12,
      fontFamily: "'Space Grotesk', sans-serif", letterSpacing: '-0.02em',
    }}>
      <span style={{ color: 'var(--brand)', marginRight: 8 }}>{n}.</span>{title}
    </h2>
    <div style={{ fontSize: 14.5, color: 'var(--text-secondary)', lineHeight: 1.7 }}>
      {children}
    </div>
  </section>
)

const Bullet = ({ children }) => (
  <li style={{ marginBottom: 6, paddingLeft: 4 }}>{children}</li>
)

export function LegalLayout({ eyebrow, title, lastUpdate, children, active }) {
  return (
    <div style={{ background: 'var(--bg)', minHeight: '100vh' }}>
      <nav style={{
        position: 'sticky', top: 0, background: 'var(--bg)',
        borderBottom: '1px solid var(--border)', zIndex: 10,
      }}>
        <div style={{
          maxWidth: 1080, margin: '0 auto', padding: '18px 32px',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        }}>
          <Link to="/" style={{
            fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700,
            fontSize: 18, color: 'var(--text-primary)', textDecoration: 'none',
            letterSpacing: '-0.02em', display: 'flex', alignItems: 'center', gap: 10,
          }}>
            <span style={{ color: 'var(--brand)', fontSize: 10 }}>●</span> Pitch.me
          </Link>
          <Link to="/" className="btn btn-ghost" style={{ fontSize: 12 }}>← Voltar ao site</Link>
        </div>
      </nav>

      <main style={{ maxWidth: 880, margin: '0 auto', padding: '64px 32px 96px' }}>
        <div style={{
          fontSize: 11, fontWeight: 700, letterSpacing: '0.18em',
          color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 10,
        }}>{eyebrow}</div>
        <h1 style={{
          fontFamily: "'Space Grotesk', sans-serif",
          fontSize: 44, fontWeight: 700, letterSpacing: '-0.03em',
          lineHeight: 1.05, marginBottom: 12,
        }}>
          {title}
        </h1>
        {lastUpdate && (
          <p style={{ color: 'var(--text-muted)', fontSize: 13, marginBottom: 48 }}>
            Última atualização: {lastUpdate}
          </p>
        )}

        {/* Tabs entre docs legais */}
        <div style={{
          display: 'flex', gap: 0, borderBottom: '1px solid var(--border)',
          marginBottom: 40, flexWrap: 'wrap',
        }}>
          {[
            { to: '/termos',             label: 'Termos de Uso' },
            { to: '/privacidade',        label: 'Privacidade' },
            { to: '/direitos-autorais',  label: 'Direitos Autorais' },
          ].map(t => (
            <Link key={t.to} to={t.to} style={{
              padding: '12px 18px',
              fontSize: 13, fontWeight: 600, letterSpacing: '0.04em',
              textDecoration: 'none',
              color: active === t.to ? 'var(--text-primary)' : 'var(--text-muted)',
              borderBottom: active === t.to ? '2px solid var(--brand)' : '2px solid transparent',
              marginBottom: -1,
            }}>{t.label}</Link>
          ))}
        </div>

        {children}

        <div style={{
          marginTop: 64, paddingTop: 24, borderTop: '1px solid var(--border)',
          fontSize: 13, color: 'var(--text-muted)',
        }}>
          Dúvidas? Escreva para <a href="mailto:contato@pitch.me" style={{ color: 'var(--brand)' }}>contato@pitch.me</a>.
        </div>
      </main>
    </div>
  )
}

export { Section, Bullet }
