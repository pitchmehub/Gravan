import React, { useState, useEffect, useRef, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import DEFAULT_CONTENT from '../config/landing.default.json'
import GravanLogo from '../components/GravanLogo'

const API_URL = import.meta.env.VITE_API_URL

export default function Landing() {
  const [showContato, setShowContato] = useState(false)
  const [stats, setStats] = useState(null)
  const [content, setContent] = useState(DEFAULT_CONTENT)
  const [navScrolled, setNavScrolled] = useState(false)
  const { user, loading } = useAuth()
  const navigate = useNavigate()

  // Se já está logado, restaura a última rota visitada (ou /descoberta).
  // Evita ver a Landing por um instante quando o usuário recarrega o site.
  useEffect(() => {
    if (loading || !user) return
    let destino = '/descoberta'
    try {
      const ultima = localStorage.getItem('gravan_last_route')
      if (ultima && ultima !== '/' && ultima !== '/login') destino = ultima
    } catch { /* noop */ }
    navigate(destino, { replace: true })
  }, [user, loading, navigate])

  // Carrega conteúdo editável da Landing (fallback para defaults)
  useEffect(() => {
    let mounted = true
    fetch(`${API_URL}/landing/content`)
      .then(r => r.ok ? r.json() : null)
      .then(data => {
        if (mounted && data && Object.keys(data).length) {
          // merge raso para nunca perder seção caso admin não tenha preenchido uma parte
          setContent(c => ({ ...c, ...data,
            brand: { ...c.brand, ...(data.brand || {}) },
            nav:   { ...c.nav,   ...(data.nav || {}) },
            hero:  { ...c.hero,  ...(data.hero || {}) },
            stats: { ...c.stats, ...(data.stats || {}) },
            comoFunciona: { ...c.comoFunciona, ...(data.comoFunciona || {}) },
            recursos:  { ...c.recursos,  ...(data.recursos || {}) },
            manifesto: { ...c.manifesto, ...(data.manifesto || {}) },
            precos:    { ...c.precos,    ...(data.precos || {}) },
            footer:    { ...c.footer,    ...(data.footer || {}) },
          }))
        }
      })
      .catch(() => {})
    return () => { mounted = false }
  }, [])

  useEffect(() => {
    let mounted = true
    async function loadStats() {
      try {
        const res = await fetch(`${API_URL}/catalogo/stats/public`)
        if (!res.ok) throw new Error('fail')
        const data = await res.json()
        if (!mounted) return
        setStats({
          obras: data.obras || 0,
          compositores: data.compositores || 0,
          totalPago: data.total_pago || 0,
        })
      } catch {
        if (mounted) setStats({ obras: 0, compositores: 0, totalPago: 0 })
      }
    }
    loadStats()
    return () => { mounted = false }
  }, [])

  // Nav shadow on scroll
  useEffect(() => {
    const onScroll = () => setNavScrolled(window.scrollY > 24)
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  // Scroll reveal via IntersectionObserver
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            entry.target.classList.add('is-visible')
            observer.unobserve(entry.target)
          }
        })
      },
      { threshold: 0.1, rootMargin: '0px 0px -48px 0px' }
    )
    const targets = document.querySelectorAll('[data-reveal]')
    targets.forEach(el => observer.observe(el))
    return () => observer.disconnect()
  }, [content])

  const handleCTA = () => {
    if (user) {
      navigate('/descoberta')
    } else {
      navigate('/login')
    }
  }

  function formatNumber(n) {
    if (n < 1000) return String(n)
    if (n < 10000) return (n / 1000).toFixed(1).replace(/\.0$/, '') + 'k'
    return Math.round(n / 1000) + 'k'
  }

  function formatBRL(n) {
    if (!n || n < 1) return 'R$ 0'
    if (n < 1000) return `R$ ${Math.round(n)}`
    if (n < 1_000_000) return `R$ ${(n / 1000).toFixed(1).replace(/\.0$/, '')}k`
    return `R$ ${(n / 1_000_000).toFixed(1).replace(/\.0$/, '')}M`
  }

  // Decide se mostra números reais ou fallbacks editáveis
  const showReal = content.stats?.showRealNumbers !== false
  const statCompositores = showReal && stats ? formatNumber(stats.compositores) : (content.stats?.fallbackCompositores || '—')
  const statObras        = showReal && stats ? formatNumber(stats.obras)        : (content.stats?.fallbackObras || '—')
  const statPago         = showReal && stats ? formatBRL(stats.totalPago)       : (content.stats?.fallbackPago || '—')

  return (
    <div className="landing-v1">
      {/* Navigation */}
      <nav className={`nav-minimal${navScrolled ? ' is-scrolled' : ''}`} data-testid="landing-nav">
        <div className="nav-container">
          <a href="#" className="logo" data-testid="logo" aria-label={content.brand.logoText}>
            <GravanLogo height={52} />
          </a>
          <div className="nav-center">
            <a href="#como-funciona" data-testid="nav-como-funciona">{content.nav.link1}</a>
            <a href="#recursos" data-testid="nav-recursos">{content.nav.link2}</a>
            <a href="#precos" data-testid="nav-precos">{content.nav.link3}</a>
          </div>
          <div className="nav-actions">
            {user ? (
              <button
                className="btn-accent"
                onClick={() => navigate('/descoberta')}
                data-testid="nav-btn-dashboard"
              >
                {content.nav.ctaLogado}
              </button>
            ) : (
              <button
                className="btn-accent"
                onClick={() => navigate('/login')}
                data-testid="nav-btn-entrar"
              >
                {content.nav.ctaDeslogado}
              </button>
            )}
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="hero" data-testid="hero-section">
        <div className="hero-grid">
          <div className="hero-text">
            <div className="eyebrow">
              <span className="dot-rec" /> {content.brand.eyebrow}
            </div>
            <h1 className="hero-title">
              {content.hero.titleLine1} <br />
              <span className="italic-light">{content.hero.titleLine2}</span> <br />
              {content.hero.titleLine3}
            </h1>
            <p className="hero-subtitle">
              {content.hero.subtitle}
            </p>
            <div className="hero-cta-row">
              <button
                className="btn-primary"
                onClick={handleCTA}
                data-testid="hero-cta-comecar"
              >
                {content.hero.ctaPrimary}
              </button>
              <a href="#como-funciona" className="btn-ghost" data-testid="hero-cta-saiba-mais">
                {content.hero.ctaSecondary}
              </a>
            </div>
          </div>
          <div className="hero-media">
            <img
              src={content.hero.imageUrl}
              alt="Hero"
              loading="eager"
            />
            <div className="hero-media-label">
              <span className="dot-rec" /> {content.hero.imageLabel}
            </div>
          </div>
        </div>
      </section>

      {/* Como Funciona */}
      <section className="section-block" id="como-funciona" data-testid="section-como-funciona">
        <div className="block-header" data-reveal>
          <span className="section-index">01</span>
          <h2 className="section-title">{content.comoFunciona.sectionTitle}</h2>
          <p className="section-lead">
            {content.comoFunciona.sectionLead}
          </p>
        </div>
        <div className="grid-two" data-reveal data-delay="1">
          <div className="grid-col" data-testid="card-compositores">
            <div className="col-head">
              <span className="col-label">{content.comoFunciona.compositoresLabel}</span>
              <h3>{content.comoFunciona.compositoresTitle}</h3>
            </div>
            <ol className="step-list">
              {(content.comoFunciona.compositoresSteps || []).map((step, i) => (
                <li key={i}>
                  <span className="step-num">{i + 1}</span>
                  <div>
                    <strong>{step.title}</strong>
                    <p>{step.text}</p>
                  </div>
                </li>
              ))}
            </ol>
          </div>
          <div className="grid-col grid-col-dark" data-testid="card-compradores">
            <div className="col-head">
              <span className="col-label">{content.comoFunciona.compradoresLabel}</span>
              <h3>{content.comoFunciona.compradoresTitle}</h3>
            </div>
            <ol className="step-list">
              {(content.comoFunciona.compradoresSteps || []).map((step, i) => (
                <li key={i}>
                  <span className="step-num">{i + 1}</span>
                  <div>
                    <strong>{step.title}</strong>
                    <p>{step.text}</p>
                  </div>
                </li>
              ))}
            </ol>
          </div>
        </div>
      </section>

      {/* Recursos */}
      <section className="section-block section-features" id="recursos" data-testid="section-recursos">
        <div className="block-header" data-reveal>
          <span className="section-index">02</span>
          <h2 className="section-title">{content.recursos.title}</h2>
        </div>
        <div className="features-grid">
          {(content.recursos.items || []).map((item, i) => (
            <div key={i} className="feature-cell" data-reveal data-delay={String(i)} data-testid={`feature-${i}`}>
              <div className="feature-label">{item.label}</div>
              <h4>{item.title}</h4>
              <p>{item.text}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Manifesto */}
      <section className="testimonial" data-testid="section-manifesto">
        <div className="testimonial-inner" data-reveal>
          <span className="quote-mark">"</span>
          <blockquote className="testimonial-quote">
            {content.manifesto.line1}<br />
            <span className="italic-light">{content.manifesto.line2}</span>
          </blockquote>
          <div className="testimonial-author">
            <div>
              <strong>{content.manifesto.authorName}</strong>
              <span>{content.manifesto.authorCaption}</span>
            </div>
          </div>
        </div>
      </section>

      {/* Preços */}
      <section className="section-block" id="precos" data-testid="section-precos">
        <div className="block-header" data-reveal>
          <span className="section-index">03</span>
          <h2 className="section-title">{content.precos.title}</h2>
          <p className="section-lead">
            {content.precos.lead}
          </p>
        </div>
        <div className="pricing-grid" data-reveal data-delay="1">
          <div className="price-cell" data-testid="plan-basico">
            <div className="price-label">{content.precos.basico.label}</div>
            <div className="price-value">{content.precos.basico.price}</div>
            <ul className="price-list">
              {(content.precos.basico.features || []).map((f, i) => <li key={i}>{f}</li>)}
            </ul>
            <button className="btn-ghost full" onClick={handleCTA}>
              {content.precos.basico.cta}
            </button>
          </div>
          <div className="price-cell price-cell-feature" data-testid="plan-pro">
            {content.precos.pro.ribbon && <div className="price-ribbon">{content.precos.pro.ribbon}</div>}
            <div className="price-label">{content.precos.pro.label}</div>
            <div className="price-value">{content.precos.pro.price}{content.precos.pro.priceUnit && <small>{content.precos.pro.priceUnit}</small>}</div>
            <ul className="price-list">
              {(content.precos.pro.features || []).map((f, i) => <li key={i}>{f}</li>)}
            </ul>
            <button className="btn-primary full" onClick={handleCTA} data-testid="plan-pro-cta">
              {content.precos.pro.cta}
            </button>
          </div>
        </div>
      </section>

      {/* Footer massivo */}
      <footer className="footer-massive" data-testid="footer">
        <div className="footer-top">
          <div className="footer-links-row">
            <div>
              <h4>{content.footer.colPlatformTitle}</h4>
              <a href="#como-funciona">{content.comoFunciona.sectionTitle}</a>
              <a href="#recursos">{content.nav.link2}</a>
              <a href="#precos">{content.nav.link3}</a>
              <a href="/login">Login</a>
            </div>
            <div>
              <h4>{content.footer.colLegalTitle}</h4>
              <a href="/termos">Termos de Uso</a>
              <a href="/privacidade">Política de Privacidade</a>
              <a href="/direitos-autorais">Direitos Autorais</a>
            </div>
            <div>
              <h4>{content.footer.colContactTitle}</h4>
              <a href={`mailto:${content.footer.email}`}>{content.footer.email}</a>
              <a
                href="#"
                onClick={(e) => {
                  e.preventDefault()
                  setShowContato(true)
                }}
                data-testid="footer-fale-conosco"
              >
                Fale Conosco
              </a>
            </div>
          </div>
          <div className="footer-cta" data-reveal>
            <h2>{content.footer.ctaTitle}</h2>
            <button
              className="btn-primary footer-btn"
              onClick={handleCTA}
              data-testid="footer-cta-comecar"
            >
              {content.footer.ctaButton}
            </button>
          </div>
        </div>
        <div className="footer-wordmark">{content.footer.wordmark}</div>
        <div className="footer-bottom">
          <span>{content.footer.copyright}</span>
          <span>{content.footer.tagline}</span>
        </div>
      </footer>

      {showContato && (
        <div className="modal-backdrop" onClick={() => setShowContato(false)} data-testid="contato-modal">
          <div className="modal-card" onClick={(e) => e.stopPropagation()}>
            <h3>Fale Conosco</h3>
            <p>Envie um e-mail para <strong>contato@gravan.com</strong> ou responda este modal em breve.</p>
            <button className="btn-primary" onClick={() => setShowContato(false)} data-testid="contato-fechar">
              Fechar
            </button>
          </div>
        </div>
      )}

      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&family=IBM+Plex+Sans:wght@300;400;500;600&display=swap');

        :root {
          --bg: #F1EFE8;
          --surface: #FFFFFF;
          --text: #2C2C2A;
          --muted: #888780;
          --accent: #0C447C;
          --accent-2: #378ADD;
          --border: #E0DDD3;
          --ink: #2C2C2A;
        }

        .landing-v1 {
          background: var(--bg);
          color: var(--text);
          min-height: 100vh;
          font-family: 'IBM Plex Sans', system-ui, -apple-system, sans-serif;
          line-height: 1.5;
        }

        .landing-v1 * { box-sizing: border-box; }

        .landing-v1 h1, .landing-v1 h2, .landing-v1 h3, .landing-v1 h4 {
          font-family: 'Space Grotesk', 'Inter', sans-serif;
          letter-spacing: -0.02em;
          font-weight: 700;
          margin: 0;
        }

        .italic-light {
          font-style: italic;
          font-weight: 300;
        }

        /* ===================== NAV ===================== */
        .nav-minimal {
          position: sticky;
          top: 0;
          background: #FFFFFF;
          border-bottom: 1px solid var(--border);
          z-index: 100;
        }
        .nav-container {
          max-width: 1280px;
          margin: 0 auto;
          padding: 18px 32px;
          display: grid;
          grid-template-columns: 1fr auto 1fr;
          align-items: center;
          gap: 24px;
        }
        .logo {
          font-family: 'Space Grotesk', sans-serif;
          font-weight: 700;
          font-size: 20px;
          color: var(--text);
          text-decoration: none;
          letter-spacing: -0.02em;
          display: inline-flex;
          align-items: center;
          gap: 10px;
        }
        .logo-mark {
          color: var(--accent);
          font-size: 14px;
        }
        .logo-img {
          height: 36px;
          width: auto;
          display: block;
          object-fit: contain;
        }
        .nav-center {
          display: flex;
          gap: 28px;
          justify-self: center;
        }
        .nav-center a {
          color: var(--text);
          text-decoration: none;
          font-size: 14px;
          font-weight: 500;
          transition: color .2s ease;
        }
        .nav-center a:hover { color: var(--accent); }
        .nav-actions { justify-self: end; }

        .btn-accent {
          background: var(--text);
          color: #FFFFFF;
          border: none;
          padding: 12px 22px;
          border-radius: 0;
          font-weight: 600;
          font-size: 14px;
          cursor: pointer;
          transition: background .2s ease, transform .2s ease;
          font-family: inherit;
        }
        .btn-accent:hover { background: var(--accent); }

        /* ===================== HERO ===================== */
        .hero {
          border-bottom: 1px solid var(--border);
        }
        .hero-grid {
          max-width: 1280px;
          margin: 0 auto;
          padding: 90px 32px 110px;
          display: grid;
          grid-template-columns: 1.1fr 0.9fr;
          gap: 72px;
          align-items: center;
        }
        .eyebrow {
          display: inline-flex;
          align-items: center;
          gap: 10px;
          font-size: 12px;
          font-weight: 600;
          letter-spacing: 0.14em;
          color: var(--muted);
          border: 1px solid var(--border);
          padding: 10px 16px;
          border-radius: 0;
          margin-bottom: 32px;
        }
        .dot-rec {
          width: 9px;
          height: 9px;
          background: var(--accent);
          border-radius: 999px;
          display: inline-block;
          box-shadow: 0 0 0 4px rgba(12,68,124,0.15);
          animation: pulse 1.6s ease-in-out infinite;
        }
        @keyframes pulse {
          0%,100% { box-shadow: 0 0 0 4px rgba(12,68,124,0.18); }
          50% { box-shadow: 0 0 0 8px rgba(12,68,124,0.05); }
        }

        /* ─── ANIMATION KEYFRAMES ─────────────────────────── */
        @keyframes gvFadeSlideUp {
          from { opacity: 0; transform: translateY(32px); }
          to   { opacity: 1; transform: translateY(0); }
        }
        @keyframes gvFadeIn {
          from { opacity: 0; }
          to   { opacity: 1; }
        }
        @keyframes gvScaleReveal {
          from { opacity: 0; transform: scale(0.97) translateY(12px); }
          to   { opacity: 1; transform: scale(1) translateY(0); }
        }

        /* ─── HERO ENTRANCE (page load, no scroll) ────────── */
        .hero-text .eyebrow {
          animation: gvFadeSlideUp .55s cubic-bezier(.22,.68,0,1.2) .08s both;
        }
        .hero-text .hero-title {
          animation: gvFadeSlideUp .65s cubic-bezier(.22,.68,0,1.15) .2s both;
        }
        .hero-text .hero-subtitle {
          animation: gvFadeSlideUp .55s ease .38s both;
        }
        .hero-text .hero-cta-row {
          animation: gvFadeSlideUp .5s ease .52s both;
        }
        .hero-text .hero-meta {
          animation: gvFadeSlideUp .5s ease .64s both;
        }
        .hero-media {
          animation: gvScaleReveal .8s cubic-bezier(.22,.68,0,1.05) .18s both;
        }

        /* ─── SCROLL REVEAL ────────────────────────────────── */
        [data-reveal] {
          opacity: 0;
          transform: translateY(30px);
          transition:
            opacity  .65s cubic-bezier(.22,.68,0,1.1),
            transform .65s cubic-bezier(.22,.68,0,1.1);
        }
        [data-reveal].is-visible {
          opacity: 1;
          transform: none;
        }
        [data-reveal][data-delay="1"] { transition-delay: .12s; }
        [data-reveal][data-delay="2"] { transition-delay: .24s; }
        [data-reveal][data-delay="3"] { transition-delay: .36s; }
        [data-reveal][data-delay="4"] { transition-delay: .48s; }
        [data-reveal][data-delay="5"] { transition-delay: .56s; }

        /* ─── NAV SCROLL SHADOW ────────────────────────────── */
        .nav-minimal {
          transition: box-shadow .3s ease;
        }
        .nav-minimal.is-scrolled {
          box-shadow: 0 2px 24px rgba(44,44,42,0.10);
        }
        .hero-title {
          font-size: clamp(44px, 6.4vw, 92px);
          line-height: 0.96;
          letter-spacing: -0.035em;
          font-weight: 700;
          margin-bottom: 28px;
        }
        .hero-subtitle {
          font-size: 18px;
          color: var(--muted);
          max-width: 520px;
          margin: 0 0 36px;
        }
        .hero-cta-row {
          display: flex;
          gap: 16px;
          align-items: center;
          margin-bottom: 48px;
          flex-wrap: wrap;
        }
        .btn-primary {
          background: var(--accent);
          color: #FFFFFF;
          border: 1px solid var(--accent);
          padding: 18px 32px;
          border-radius: 0;
          font-family: inherit;
          font-weight: 700;
          font-size: 15px;
          letter-spacing: 0.02em;
          cursor: pointer;
          transition: all .2s ease;
          text-transform: uppercase;
        }
        .btn-primary:hover {
          background: var(--text);
          border-color: var(--text);
          transform: translateY(-2px);
        }
        .btn-primary.full { width: 100%; }
        .btn-ghost {
          background: transparent;
          color: var(--text);
          border: 1px solid var(--text);
          padding: 18px 28px;
          border-radius: 0;
          font-family: inherit;
          font-weight: 600;
          font-size: 15px;
          cursor: pointer;
          text-decoration: none;
          display: inline-block;
          transition: all .2s ease;
        }
        .btn-ghost:hover {
          background: var(--text);
          color: #FFFFFF;
        }
        .btn-ghost.full {
          width: 100%;
          text-align: center;
          padding: 16px 24px;
        }

        .hero-meta {
          display: flex;
          gap: 48px;
          padding-top: 28px;
          border-top: 1px solid var(--border);
        }
        .hero-meta div { display: flex; flex-direction: column; gap: 4px; }
        .hero-meta strong {
          font-family: 'Space Grotesk', sans-serif;
          font-size: 28px;
          font-weight: 700;
          color: var(--text);
        }
        .hero-meta span { font-size: 13px; color: var(--muted); }

        .hero-media {
          position: relative;
          aspect-ratio: 1 / 1.05;
          border: 1px solid var(--border);
          overflow: hidden;
        }
        .hero-media img {
          width: 100%;
          height: 100%;
          object-fit: cover;
          display: block;
          filter: grayscale(0%) contrast(1.05);
        }
        .hero-media-label {
          position: absolute;
          bottom: 18px;
          left: 18px;
          background: #FFFFFF;
          border: 1px solid var(--text);
          padding: 8px 14px;
          font-size: 11px;
          font-weight: 600;
          letter-spacing: 0.14em;
          display: flex;
          align-items: center;
          gap: 8px;
        }

        /* ===================== SECTION BLOCKS ===================== */
        .section-block {
          max-width: 1280px;
          margin: 0 auto;
          padding: 120px 32px;
          border-bottom: 1px solid var(--border);
        }
        .block-header { max-width: 820px; margin-bottom: 64px; }
        .section-index {
          display: inline-block;
          font-family: 'Space Grotesk', sans-serif;
          font-size: 13px;
          color: var(--muted);
          letter-spacing: 0.2em;
          margin-bottom: 20px;
        }
        .section-title {
          font-size: clamp(36px, 4.6vw, 64px);
          line-height: 1.02;
          letter-spacing: -0.03em;
          margin-bottom: 18px;
        }
        .section-lead {
          font-size: 18px;
          color: var(--muted);
          max-width: 600px;
          margin: 0;
        }

        /* Two columns Como Funciona */
        .grid-two {
          display: grid;
          grid-template-columns: 1fr 1fr;
          border: 1px solid var(--border);
        }
        .grid-col {
          padding: 56px 48px;
          border-right: 1px solid var(--border);
        }
        .grid-col:last-child { border-right: none; }
        .grid-col-dark {
          background: var(--text);
          color: #FFFFFF;
        }
        .grid-col-dark .col-label { color: rgba(255,255,255,0.55); }
        .grid-col-dark .step-list li p { color: rgba(255,255,255,0.65); }
        .grid-col-dark .step-num { background: #FFFFFF; color: var(--text); }

        .col-head { margin-bottom: 40px; }
        .col-label {
          display: block;
          font-size: 12px;
          letter-spacing: 0.18em;
          color: var(--muted);
          margin-bottom: 16px;
          font-weight: 600;
        }
        .col-head h3 {
          font-size: 32px;
          line-height: 1.1;
          letter-spacing: -0.02em;
        }
        .step-list {
          list-style: none;
          padding: 0;
          margin: 0;
          display: flex;
          flex-direction: column;
          gap: 28px;
        }
        .step-list li {
          display: grid;
          grid-template-columns: 44px 1fr;
          gap: 20px;
          align-items: start;
        }
        .step-num {
          background: var(--text);
          color: #FFFFFF;
          width: 36px;
          height: 36px;
          display: inline-flex;
          align-items: center;
          justify-content: center;
          font-family: 'Space Grotesk', sans-serif;
          font-weight: 700;
          font-size: 14px;
        }
        .step-list li strong {
          display: block;
          font-size: 17px;
          margin-bottom: 6px;
          font-weight: 600;
        }
        .step-list li p {
          margin: 0;
          color: var(--muted);
          font-size: 15px;
        }

        /* Features grid */
        .section-features { background: var(--bg); }
        .features-grid {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          border: 1px solid var(--border);
          border-right: none;
          border-bottom: none;
        }
        .feature-cell {
          border-right: 1px solid var(--border);
          border-bottom: 1px solid var(--border);
          padding: 40px 36px;
          transition: background .25s ease, transform .25s ease, box-shadow .25s ease;
        }
        .feature-cell:hover {
          background: var(--surface);
          transform: translateY(-3px);
          box-shadow: 0 8px 24px rgba(44,44,42,0.07);
          position: relative;
          z-index: 1;
        }
        .feature-label {
          font-family: 'Space Grotesk', sans-serif;
          font-size: 12px;
          color: var(--muted);
          letter-spacing: 0.18em;
          margin-bottom: 20px;
        }
        .feature-cell h4 {
          font-size: 22px;
          margin-bottom: 10px;
          letter-spacing: -0.02em;
        }
        .feature-cell p {
          color: var(--muted);
          margin: 0;
          font-size: 15px;
        }

        /* Testimonial editorial */
        .testimonial {
          border-bottom: 1px solid var(--border);
        }
        .testimonial-inner {
          max-width: 1080px;
          margin: 0 auto;
          padding: 120px 32px;
          position: relative;
        }
        .quote-mark {
          font-family: 'Space Grotesk', sans-serif;
          font-size: 180px;
          line-height: 0.6;
          color: var(--accent);
          position: absolute;
          top: 100px;
          left: 16px;
          opacity: 0.18;
          font-weight: 700;
        }
        .testimonial-quote {
          font-family: 'Space Grotesk', sans-serif;
          font-size: clamp(32px, 4.2vw, 56px);
          line-height: 1.1;
          letter-spacing: -0.025em;
          font-weight: 600;
          margin: 0 0 40px;
          max-width: 900px;
        }
        .testimonial-author {
          display: flex;
          align-items: center;
          gap: 16px;
        }
        .testimonial-author img {
          width: 56px;
          height: 56px;
          object-fit: cover;
          border: 1px solid var(--border);
        }
        .testimonial-author strong {
          display: block;
          font-size: 16px;
        }
        .testimonial-author span { color: var(--muted); font-size: 14px; }

        /* Pricing */
        .pricing-grid {
          display: grid;
          grid-template-columns: 1fr 1fr;
          border: 1px solid var(--border);
        }
        .price-cell {
          padding: 48px 40px;
          border-right: 1px solid var(--border);
          position: relative;
          transition: transform .3s cubic-bezier(.22,.68,0,1.2), box-shadow .3s ease;
        }
        .price-cell:last-child { border-right: none; }
        .price-cell:hover {
          transform: translateY(-5px);
          box-shadow: 0 16px 40px rgba(44,44,42,0.12);
          z-index: 1;
        }
        .price-cell-feature {
          background: var(--text);
          color: #FFFFFF;
        }
        .price-cell-feature .price-label,
        .price-cell-feature .price-list li { color: rgba(255,255,255,0.7); }
        .price-ribbon {
          position: absolute;
          top: 20px;
          right: 20px;
          background: var(--accent);
          color: #FFFFFF;
          font-size: 11px;
          font-weight: 700;
          letter-spacing: 0.16em;
          padding: 6px 12px;
        }
        .price-label {
          font-size: 12px;
          letter-spacing: 0.18em;
          color: var(--muted);
          margin-bottom: 16px;
          font-weight: 600;
        }
        .price-value {
          font-family: 'Space Grotesk', sans-serif;
          font-size: 64px;
          font-weight: 700;
          letter-spacing: -0.03em;
          margin-bottom: 24px;
          line-height: 1;
        }
        .price-value small {
          font-size: 16px;
          color: var(--muted);
          font-weight: 400;
          margin-left: 4px;
        }
        .price-cell-feature .price-value small { color: rgba(255,255,255,0.6); }
        .price-list {
          list-style: none;
          padding: 0;
          margin: 0 0 36px;
          display: flex;
          flex-direction: column;
          gap: 10px;
        }
        .price-list li {
          font-size: 15px;
          display: flex;
          align-items: center;
          gap: 12px;
        }
        .price-list li::before {
          content: '';
          width: 14px;
          height: 1px;
          background: currentColor;
          display: inline-block;
          opacity: 0.5;
        }

        /* FOOTER */
        .footer-massive {
          background: #09090B;
          color: #FFFFFF;
          padding: 100px 32px 40px;
        }
        .footer-top {
          max-width: 1280px;
          margin: 0 auto;
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 72px;
          padding-bottom: 80px;
          border-bottom: 1px solid rgba(255,255,255,0.1);
        }
        .footer-links-row {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 32px;
        }
        .footer-links-row h4 {
          font-size: 13px;
          letter-spacing: 0.18em;
          color: rgba(255,255,255,0.5);
          margin-bottom: 20px;
          font-family: 'Space Grotesk', sans-serif;
          font-weight: 600;
        }
        .footer-links-row a {
          display: block;
          color: #FFFFFF;
          text-decoration: none;
          font-size: 14px;
          margin-bottom: 10px;
          transition: color .2s;
        }
        .footer-links-row a:hover { color: var(--accent); }
        .footer-cta h2 {
          font-size: clamp(36px, 4.6vw, 64px);
          margin-bottom: 24px;
          letter-spacing: -0.03em;
        }
        .footer-btn { background: var(--accent); border-color: var(--accent); }
        .footer-btn:hover { background: #FFFFFF; color: var(--text); border-color: #FFFFFF; }

        .footer-wordmark {
          font-family: 'Space Grotesk', sans-serif;
          font-size: clamp(80px, 20vw, 280px);
          font-weight: 700;
          letter-spacing: -0.06em;
          line-height: 0.85;
          text-align: center;
          margin: 60px 0 40px;
          background: linear-gradient(180deg, rgba(255,255,255,1) 0%, rgba(255,255,255,0.15) 100%);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          background-clip: text;
        }
        .footer-bottom {
          max-width: 1280px;
          margin: 0 auto;
          display: flex;
          justify-content: space-between;
          font-size: 13px;
          color: rgba(255,255,255,0.5);
          padding-top: 24px;
          border-top: 1px solid rgba(255,255,255,0.08);
          flex-wrap: wrap;
          gap: 12px;
        }

        /* Modal */
        .modal-backdrop {
          position: fixed; inset: 0; background: rgba(9,9,11,0.6);
          display: flex; align-items: center; justify-content: center;
          z-index: 9999; padding: 24px;
        }
        .modal-card {
          background: #FFFFFF; color: var(--text); padding: 40px;
          max-width: 440px; width: 100%; border: 1px solid var(--border);
        }
        .modal-card h3 { margin-bottom: 12px; font-size: 24px; }
        .modal-card p { color: var(--muted); margin-bottom: 24px; }

        /* Responsive */
        @media (max-width: 960px) {
          .nav-container { grid-template-columns: 1fr auto; }
          .nav-center { display: none; }
          .hero-grid { grid-template-columns: 1fr; padding: 60px 24px 72px; gap: 48px; }
          .hero-meta { gap: 28px; }
          .grid-two, .pricing-grid { grid-template-columns: 1fr; }
          .grid-col, .price-cell { border-right: none; border-bottom: 1px solid var(--border); }
          .grid-col-dark { border-bottom: none; }
          .features-grid { grid-template-columns: 1fr 1fr; }
          .footer-top { grid-template-columns: 1fr; gap: 48px; }
          .section-block { padding: 72px 24px; }
          .testimonial-inner { padding: 72px 24px; }
        }
        @media (max-width: 560px) {
          .features-grid { grid-template-columns: 1fr; }
          .hero-meta { flex-wrap: wrap; }
          .footer-links-row { grid-template-columns: 1fr 1fr; }
        }
      `}</style>
    </div>
  )
}
