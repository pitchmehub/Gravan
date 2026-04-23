# 🎨 Pitch.me — Código Completo (Design 1)

Todos os arquivos relevantes do redesign Design 1 + backend + assets de PWA,
organizados em seções. Gerado automaticamente em 2026-04-21.

**Stack:**
- Frontend: React 18 + Vite + CSS-in-JS (styled-jsx inline na Landing)
- Backend: Python + Flask + Gunicorn (gerenciado via Supervisor)
- DB: Supabase (PostgreSQL) + RLS
- Pagamentos: Stripe + PayPal

**Paleta Design 1:**
- Background: `#FFFFFF` · Superfície: `#FAFAFA` / `#F4F4F5` · Bordas: `#E4E4E7`
- Texto: `#09090B` (primário) / `#3F3F46` (secundário) / `#71717A` (muted)
- Acento REC: `#E11D48` (brand) / `#BE123C` (brand-dark)
- Tipografia: Space Grotesk (headings) + IBM Plex Sans (body)

---

## 📑 Índice

1. [frontend/index.html](#1-frontendindex-html)
2. [frontend/src/styles/global.css](#2-frontendsrcstylesglobalcss)
3. [frontend/src/App.jsx](#3-frontendsrcappjsx)
4. [frontend/src/pages/Landing.jsx](#4-frontendsrcpageslandingjsx) *(Landing completa)*
5. [frontend/src/pages/Login.jsx](#5-frontendsrcpagesloginjsx)
6. [frontend/src/pages/Login.css](#6-frontendsrcpagesloginss)
7. [frontend/src/components/SideMenu.jsx](#7-frontendsrccomponentssidemenujsx)
8. [frontend/src/components/SideMenu.css](#8-frontendsrccomponentssidemenucss)
9. [frontend/src/components/GlobalPlayer.css](#9-frontendsrccomponentsglobalplayercss)
10. [frontend/src/components/ProfileMenu.css](#10-frontendsrccomponentsprofilemenucss)
11. [frontend/src/components/FaleConoscoModal.jsx](#11-frontendsrccomponentsfaleconoscomodaljsx)
12. [frontend/src/components/PWAInstaller.jsx](#12-frontendsrccomponentspwainstallerjsx)
13. [frontend/src/pages/Dashboard.jsx](#13-frontendsrcpagesdashboardjsx)
14. [frontend/src/pages/Descoberta.css](#14-frontendsrcpagesdescobertas)
15. [frontend/src/contexts/AuthContext.jsx](#15-frontendsrccontextsauthcontextjsx)
16. [frontend/src/lib/api.js](#16-frontendsrclibapijs)
17. [frontend/public/sw.js](#17-frontendpublicswjs)
18. [frontend/public/manifest.webmanifest](#18-frontendpublicmanifestwebmanifest)
19. [backend/routes/catalogo.py](#19-backendroutescatalogopy) *(com novo endpoint /stats/public)*
20. [backend/app.py](#20-backendapppy)

---


## 1. `frontend/index.html`

*65 linhas · 4.0K*

```html
<!doctype html>
<html lang="pt-BR">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover, maximum-scale=5.0" />
    <meta name="referrer" content="strict-origin-when-cross-origin" />
    <meta http-equiv="X-Content-Type-Options" content="nosniff" />

    <title>Pitch.me — Composições Musicais</title>
    <meta name="description" content="Marketplace de composições musicais — conectando compositores e intérpretes." />

    <!-- PWA manifest -->
    <link rel="manifest" href="/manifest.webmanifest" />
    <meta name="theme-color" content="#E11D48" />
    <meta name="color-scheme" content="light" />

    <!-- iOS PWA -->
    <meta name="apple-mobile-web-app-capable" content="yes" />
    <meta name="apple-mobile-web-app-status-bar-style" content="default" />
    <meta name="apple-mobile-web-app-title" content="Pitch.me" />
    <link rel="apple-touch-icon" href="/icons/apple-touch-icon.png" />

    <!-- Favicons -->
    <link rel="icon" type="image/png" sizes="32x32" href="/icons/favicon-32.png" />
    <link rel="icon" type="image/png" sizes="192x192" href="/icons/icon-192.png" />

    <!-- Fontes -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=IBM+Plex+Sans:wght@300;400;500;600;700&display=swap" rel="stylesheet">
  </head>
  <body>
    <div id="root"></div>
    <script>
      // Migração forçada: invalida Service Workers e caches anteriores ao Design 1.
      // Executa 1x por cliente (marca no localStorage) para eliminar CSS roxo cacheado.
      (function migratePWA() {
        try {
          var KEY = 'pitchme_design1_migrated_v3'
          if (localStorage.getItem(KEY) === '1') return
          if ('serviceWorker' in navigator) {
            navigator.serviceWorker.getRegistrations().then(function (regs) {
              regs.forEach(function (r) { r.unregister().catch(function(){}) })
            }).catch(function(){})
          }
          if ('caches' in window) {
            caches.keys().then(function (keys) {
              return Promise.all(keys.map(function (k) { return caches.delete(k) }))
            }).then(function () {
              localStorage.setItem(KEY, '1')
              // Recarrega uma vez pra pegar CSS/JS fresco do servidor
              if (!sessionStorage.getItem('pitchme_pwa_reloaded')) {
                sessionStorage.setItem('pitchme_pwa_reloaded', '1')
                window.location.reload()
              }
            }).catch(function(){ localStorage.setItem(KEY, '1') })
          } else {
            localStorage.setItem(KEY, '1')
          }
        } catch (e) { /* noop */ }
      })()
    </script>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>

```

---

## 2. `frontend/src/styles/global.css`

*332 linhas · 12K*

```css
/* ============================================================
   Pitch.me — Design Tokens & Global Styles
   Tema: Minimalista · Branco + Preto + Red REC (Design 1)
   ============================================================ */

@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=IBM+Plex+Sans:wght@300;400;500;600;700&display=swap');

:root {
  /* ── Marca (Red REC) ── */
  --brand:        #E11D48;
  --brand-light:  rgba(225, 29, 72, .10);
  --brand-dark:   #BE123C;
  --brand-glow:   rgba(225, 29, 72, .25);
  --brand-border: rgba(225, 29, 72, .35);

  /* ── Fundos (brancos / acinzentados) ── */
  --bg:           #FFFFFF;
  --surface:      #FAFAFA;
  --surface-2:    #F4F4F5;
  --surface-3:    #E4E4E7;

  /* ── Texto (preto e cinzas) ── */
  --text-primary:   #09090B;
  --text-secondary: #3F3F46;
  --text-muted:     #71717A;

  /* ── Inverso (para elementos escuros pontuais) ── */
  --ink:          #09090B;
  --ink-invert:   #FFFFFF;

  /* ── Bordas (cinza claro, retas) ── */
  --border:       #E4E4E7;
  --border-2:     #D4D4D8;
  --border-focus: #09090B;

  /* ── Semânticas ── */
  --success:      #16A34A;
  --success-bg:   rgba(22, 163, 74, .10);
  --error:        #DC2626;
  --error-bg:     rgba(220, 38, 38, .10);
  --warning:      #D97706;
  --warning-bg:   rgba(217, 119, 6, .10);

  /* ── Radii (tudo reto — Swiss style) ── */
  --radius-sm:    0px;
  --radius-md:    0px;
  --radius-lg:    0px;
  --radius-xl:    0px;

  /* ── Sombras (leves) ── */
  --shadow-sm:    0 1px 2px rgba(9,9,11,.04);
  --shadow-md:    0 2px 8px rgba(9,9,11,.06);
  --shadow-lg:    0 8px 32px rgba(9,9,11,.08);

  /* ── Layout ── */
  --sidebar-w:          240px;
  --sidebar-collapsed:  64px;
  --header-h:           60px;
  --transition:         .2s ease;
}

/* ════════════════════════════════════
   RESET GLOBAL
════════════════════════════════════ */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

html { scroll-behavior: smooth; }

body {
  font-family: 'IBM Plex Sans', system-ui, -apple-system, sans-serif;
  background: var(--bg);
  color: var(--text-primary);
  line-height: 1.55;
  font-size: 14px;
  -webkit-font-smoothing: antialiased;
}

h1, h2, h3, h4, h5, h6 {
  font-family: 'Space Grotesk', sans-serif;
  letter-spacing: -0.02em;
  font-weight: 700;
  color: var(--text-primary);
}

a { color: var(--brand); text-decoration: none; }
a:hover { text-decoration: underline; }

/* ════════════════════════════════════
   BOTÕES
════════════════════════════════════ */
.btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  border-radius: 0;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  border: 1px solid transparent;
  transition: all var(--transition);
  font-family: inherit;
  white-space: nowrap;
  letter-spacing: 0.01em;
}

.btn-primary {
  background: var(--brand);
  color: #fff;
  border-color: var(--brand);
}
.btn-primary:hover {
  background: var(--ink);
  border-color: var(--ink);
  transform: translateY(-1px);
}

.btn-secondary {
  background: transparent;
  color: var(--ink);
  border: 1px solid var(--ink);
}
.btn-secondary:hover {
  background: var(--ink);
  color: #fff;
}

.btn-ghost {
  background: transparent;
  color: var(--text-secondary);
  border: 1px solid var(--border);
}
.btn-ghost:hover {
  background: var(--surface-2);
  color: var(--text-primary);
  border-color: var(--border-2);
}

.btn-danger {
  background: transparent;
  color: var(--error);
  border: 1px solid var(--error);
}
.btn-danger:hover { background: var(--error); color: #fff; }

.btn:disabled { opacity: .4; cursor: not-allowed; transform: none !important; }
.btn-sm  { padding: 7px 14px; font-size: 12px; }
.btn-lg  { padding: 14px 28px; font-size: 15px; }

/* ════════════════════════════════════
   INPUTS
════════════════════════════════════ */
.input {
  width: 100%;
  padding: 11px 14px;
  border: 1px solid var(--border);
  border-radius: 0;
  font-size: 14px;
  color: var(--text-primary);
  background: var(--bg);
  transition: border-color var(--transition);
  outline: none;
  font-family: inherit;
}
.input:focus {
  border-color: var(--border-focus);
  box-shadow: 0 0 0 3px rgba(9,9,11,.08);
}
.input::placeholder { color: var(--text-muted); }
textarea.input { resize: vertical; min-height: 120px; }

select.input {
  appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='8' viewBox='0 0 12 8'%3E%3Cpath d='M1 1l5 5 5-5' stroke='%2309090B' stroke-width='2' fill='none' stroke-linecap='round'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 14px center;
  padding-right: 36px;
}

/* ════════════════════════════════════
   CARDS (bordas finas, sem arredondamento)
════════════════════════════════════ */
.card {
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 0;
  padding: 24px;
}
.card-sm { padding: 16px; }

/* ════════════════════════════════════
   BADGES
════════════════════════════════════ */
.badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 10px;
  border-radius: 0;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text-secondary);
}
.badge-silver  { background: var(--surface-2); color: var(--text-secondary); }
.badge-gold    { background: #FEF3C7; color: #92400E; border-color: #FCD34D; }
.badge-diamond { background: var(--brand-light); color: var(--brand); border-color: var(--brand-border); }
.badge-success { background: var(--success-bg); color: var(--success); border-color: rgba(22,163,74,.3); }
.badge-error   { background: var(--error-bg); color: var(--error); border-color: rgba(220,38,38,.3); }
.badge-warning { background: var(--warning-bg); color: var(--warning); border-color: rgba(217,119,6,.3); }

/* ════════════════════════════════════
   LAYOUT SHELL
════════════════════════════════════ */
.app-shell {
  display: flex;
  min-height: 100vh;
  background: var(--bg);
}
.main-content {
  flex: 1;
  margin-left: var(--sidebar-w);
  padding: 32px;
  transition: margin-left var(--transition);
  background: var(--bg);
  min-height: 100vh;
}
.main-content.collapsed { margin-left: var(--sidebar-collapsed); }

/* ════════════════════════════════════
   FORMULÁRIOS
════════════════════════════════════ */
.form-group  { display: flex; flex-direction: column; gap: 6px; margin-bottom: 18px; }
.form-label  {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--text-secondary);
}
.form-error  { font-size: 12px; color: var(--error); }
.form-hint   { font-size: 12px; color: var(--text-muted); }

/* ════════════════════════════════════
   UTILITÁRIOS
════════════════════════════════════ */
.text-muted   { color: var(--text-muted); font-size: 13px; }
.text-success { color: var(--success); }
.text-error   { color: var(--error); }
.text-warning { color: var(--warning); }
.text-brand   { color: var(--brand); }

.flex         { display: flex; }
.flex-col     { flex-direction: column; }
.items-center { align-items: center; }
.gap-8        { gap: 8px; }
.gap-16       { gap: 16px; }
.mt-8         { margin-top: 8px; }
.mt-16        { margin-top: 16px; }
.mt-24        { margin-top: 24px; }
.w-full       { width: 100%; }

.divider { height: 1px; background: var(--border); margin: 16px 0; border: none; }

/* Scrollbar minimalista */
::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb {
  background: var(--border-2);
  border-radius: 0;
}
::-webkit-scrollbar-thumb:hover { background: var(--text-muted); }

/* ════════════════════════════════════
   RESPONSIVO GLOBAL
════════════════════════════════════ */
@media (max-width: 768px) {
  .sidebar {
    transform: translateX(-100%);
    transition: transform .25s ease;
    width: 260px !important;
    box-shadow: 4px 0 32px rgba(9,9,11,.1);
  }
  .sidebar.mobile-open { transform: translateX(0); }
  .sidebar.collapsed   { transform: translateX(-100%); width: 260px !important; }

  .app-shell main,
  div[style*="marginLeft: 240"],
  div[style*="marginLeft: 64"] { margin-left: 0 !important; }

  .mobile-backdrop {
    display: block;
    position: fixed; inset: 0;
    background: rgba(9,9,11,.3);
    z-index: 99;
    backdrop-filter: blur(2px);
  }

  .mobile-menu-btn {
    position: fixed; top: 12px; left: 12px; z-index: 110;
    width: 42px; height: 42px; border-radius: 0;
    background: var(--bg);
    border: 1px solid var(--border);
    cursor: pointer; font-size: 18px; color: var(--text-primary);
    display: flex; align-items: center; justify-content: center;
    box-shadow: 0 2px 8px rgba(9,9,11,.08);
  }

  .card { padding: 16px !important; }
  h1    { font-size: 22px !important; }
  h2    { font-size: 17px !important; }

  .input, input, textarea, select {
    font-size: 16px !important;
    padding: 11px 14px !important;
  }
  .btn { padding: 10px 16px; }
}

@media (max-width: 380px) {
  .dc-grid { grid-template-columns: 1fr !important; }
}

@supports (padding: env(safe-area-inset-top)) {
  body {
    padding-top:    env(safe-area-inset-top);
    padding-bottom: env(safe-area-inset-bottom);
  }
}

```

---

## 3. `frontend/src/App.jsx`

*90 linhas · 8.0K*

```jsx
import React, { useState, useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import { PlayerProvider } from './contexts/PlayerContext'
import SideMenu      from './components/SideMenu'
import GlobalPlayer  from './components/GlobalPlayer'
import PWAInstaller  from './components/PWAInstaller'
import PWAInstall    from './components/PWAInstall'
import Landing       from './pages/Landing'
import Login         from './pages/Login'
import Dashboard     from './pages/Dashboard'
import Descoberta    from './pages/Descoberta'
import NovaObra      from './pages/NovaObra'
import MinhasObras   from './pages/MinhasObras'
import Comprar       from './pages/Comprar'
import Compras       from './pages/Compras'
import Saques        from './pages/Saques'
import Ofertas       from './pages/Ofertas'
import Admin         from './pages/Admin'
import EditarPerfil  from './pages/EditarPerfil'
import CompletarCadastro from './pages/CompletarCadastro'
import PagamentoSucesso   from './pages/PagamentoSucesso'
import PagamentoCancelado from './pages/PagamentoCancelado'
import './styles/global.css'
import './components/GlobalPlayer.css'

function PrivateRoute({ children, roles }) {
  const { user, perfil, loading } = useAuth()
  if (loading) return <div style={{ padding: 40, color: '#71717A', fontFamily: 'IBM Plex Sans, system-ui, sans-serif' }}>Carregando…</div>
  if (!user)   return <Navigate to="/login" replace />
  if (roles && perfil && !roles.includes(perfil.role)) return <Navigate to="/descoberta" replace />
  return children
}

function AppShell({ children }) {
  const [collapsed, setCollapsed] = useState(false)
  const sideW = collapsed ? 64 : 240
  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: '#FFFFFF' }}>
      <SideMenu onCollapse={setCollapsed} />
      <main style={{
        marginLeft: sideW, flex: 1,
        transition: 'margin-left .2s ease',
        minWidth: 0, background: '#FFFFFF',
      }}>
        {children}
      </main>
      <GlobalPlayer />
      <PWAInstall />
    </div>
  )
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/"              element={<Landing />} />
      <Route path="/login"         element={<Login />} />

      <Route path="/descoberta"    element={<PrivateRoute><AppShell><Descoberta /></AppShell></PrivateRoute>} />
      <Route path="/dashboard"     element={<PrivateRoute><AppShell><Dashboard /></AppShell></PrivateRoute>} />
      <Route path="/obras"         element={<PrivateRoute roles={['compositor','administrador']}><AppShell><MinhasObras /></AppShell></PrivateRoute>} />
      <Route path="/obras/nova"    element={<PrivateRoute roles={['compositor','administrador']}><AppShell><NovaObra /></AppShell></PrivateRoute>} />
      <Route path="/saques"        element={<PrivateRoute roles={['compositor','administrador']}><AppShell><Saques /></AppShell></PrivateRoute>} />
      <Route path="/compras"       element={<PrivateRoute><AppShell><Compras /></AppShell></PrivateRoute>} />
      <Route path="/comprar/:obraId"      element={<PrivateRoute><AppShell><Comprar /></AppShell></PrivateRoute>} />
      <Route path="/pagamento/sucesso"    element={<PrivateRoute><AppShell><PagamentoSucesso /></AppShell></PrivateRoute>} />
      <Route path="/pagamento/cancelado"  element={<PrivateRoute><AppShell><PagamentoCancelado /></AppShell></PrivateRoute>} />
      <Route path="/ofertas"       element={<PrivateRoute><AppShell><Ofertas /></AppShell></PrivateRoute>} />
      <Route path="/perfil/editar" element={<PrivateRoute><AppShell><EditarPerfil /></AppShell></PrivateRoute>} />
      <Route path="/perfil/completar" element={<PrivateRoute><AppShell><CompletarCadastro /></AppShell></PrivateRoute>} />
      <Route path="/admin"         element={<PrivateRoute roles={['administrador']}><AppShell><Admin /></AppShell></PrivateRoute>} />

      <Route path="*"              element={<Navigate to="/descoberta" replace />} />
    </Routes>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <PlayerProvider>
          <AppRoutes />
          <PWAInstaller />
        </PlayerProvider>
      </AuthProvider>
    </BrowserRouter>
  )
}

```

---

## 4. `frontend/src/pages/Landing.jsx`

*980 linhas · 32K*

```jsx
import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

const API_URL = import.meta.env.VITE_API_URL

export default function Landing() {
  const [showContato, setShowContato] = useState(false)
  const [stats, setStats] = useState(null)
  const { user } = useAuth()
  const navigate = useNavigate()

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

  const handleCTA = () => {
    if (user) {
      navigate('/dashboard')
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

  return (
    <div className="landing-v1">
      {/* Navigation */}
      <nav className="nav-minimal" data-testid="landing-nav">
        <div className="nav-container">
          <a href="#" className="logo" data-testid="logo">
            <span className="logo-mark">●</span> Pitch.me
          </a>
          <div className="nav-center">
            <a href="#como-funciona" data-testid="nav-como-funciona">Como Funciona</a>
            <a href="#recursos" data-testid="nav-recursos">Recursos</a>
            <a href="#precos" data-testid="nav-precos">Preços</a>
          </div>
          <div className="nav-actions">
            {user ? (
              <button
                className="btn-accent"
                onClick={() => navigate('/dashboard')}
                data-testid="nav-btn-dashboard"
              >
                Dashboard →
              </button>
            ) : (
              <button
                className="btn-accent"
                onClick={() => navigate('/login')}
                data-testid="nav-btn-entrar"
              >
                Entrar
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
              <span className="dot-rec" /> MARKETPLACE DE OBRAS MUSICAIS
            </div>
            <h1 className="hero-title">
              Venda suas <br />
              <span className="italic-light">obras musicais</span> <br />
              como nunca antes.
            </h1>
            <p className="hero-subtitle">
              O marketplace que conecta compositores e compradores com
              transparência, segurança e pagamento instantâneo.
            </p>
            <div className="hero-cta-row">
              <button
                className="btn-primary"
                onClick={handleCTA}
                data-testid="hero-cta-comecar"
              >
                ▶ Começar Agora
              </button>
              <a href="#como-funciona" className="btn-ghost" data-testid="hero-cta-saiba-mais">
                Saiba mais →
              </a>
            </div>
            <div className="hero-meta">
              <div data-testid="stat-compositores">
                <strong>{stats ? formatNumber(stats.compositores) : '—'}</strong>
                <span>{stats && stats.compositores === 1 ? 'Compositor' : 'Compositores'}</span>
              </div>
              <div data-testid="stat-obras">
                <strong>{stats ? formatNumber(stats.obras) : '—'}</strong>
                <span>{stats && stats.obras === 1 ? 'Obra publicada' : 'Obras publicadas'}</span>
              </div>
              <div data-testid="stat-pagos">
                <strong>{stats ? formatBRL(stats.totalPago) : '—'}</strong>
                <span>Pagos a compositores</span>
              </div>
            </div>
          </div>
          <div className="hero-media">
            <img
              src="https://images.pexels.com/photos/32725048/pexels-photo-32725048.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=900&w=900"
              alt="Equipamento de estúdio musical"
              loading="eager"
            />
            <div className="hero-media-label">
              <span className="dot-rec" /> EM GRAVAÇÃO · 04:37
            </div>
          </div>
        </div>
      </section>

      {/* Como Funciona */}
      <section className="section-block" id="como-funciona" data-testid="section-como-funciona">
        <div className="block-header">
          <span className="section-index">01</span>
          <h2 className="section-title">Como Funciona</h2>
          <p className="section-lead">
            Dois fluxos simples. Uma plataforma construída para todos os lados do palco.
          </p>
        </div>
        <div className="grid-two">
          <div className="grid-col" data-testid="card-compositores">
            <div className="col-head">
              <span className="col-label">PARA COMPOSITORES</span>
              <h3>Transforme sua arte <br />em receita recorrente.</h3>
            </div>
            <ol className="step-list">
              <li>
                <span className="step-num">1</span>
                <div>
                  <strong>Cadastre-se em 2 minutos</strong>
                  <p>Crie sua conta, configure seu perfil e dados bancários.</p>
                </div>
              </li>
              <li>
                <span className="step-num">2</span>
                <div>
                  <strong>Faça upload do seu MP3</strong>
                  <p>Arquivos até 10MB. Metadados, coautoria e licenças claras.</p>
                </div>
              </li>
              <li>
                <span className="step-num">3</span>
                <div>
                  <strong>Receba a cada venda</strong>
                  <p>Split automático, relatórios e pagamentos via Stripe/PayPal.</p>
                </div>
              </li>
            </ol>
          </div>
          <div className="grid-col grid-col-dark" data-testid="card-compradores">
            <div className="col-head">
              <span className="col-label">PARA COMPRADORES</span>
              <h3>Descubra obras exclusivas <br />e licencie sem fricção.</h3>
            </div>
            <ol className="step-list">
              <li>
                <span className="step-num">1</span>
                <div>
                  <strong>Explore o catálogo</strong>
                  <p>Busque por gênero, BPM, humor e tipo de licença.</p>
                </div>
              </li>
              <li>
                <span className="step-num">2</span>
                <div>
                  <strong>Compre com segurança</strong>
                  <p>Checkout criptografado e contrato gerado automaticamente.</p>
                </div>
              </li>
              <li>
                <span className="step-num">3</span>
                <div>
                  <strong>Use onde precisar</strong>
                  <p>Download instantâneo e licença rastreável.</p>
                </div>
              </li>
            </ol>
          </div>
        </div>
      </section>

      {/* Recursos */}
      <section className="section-block section-features" id="recursos" data-testid="section-recursos">
        <div className="block-header">
          <span className="section-index">02</span>
          <h2 className="section-title">Recursos construídos para escalar.</h2>
        </div>
        <div className="features-grid">
          <div className="feature-cell" data-testid="feature-uploads">
            <div className="feature-label">01 / UPLOAD</div>
            <h4>MP3 até 10MB</h4>
            <p>Upload rápido, validação de metadata e preview instantâneo no player.</p>
          </div>
          <div className="feature-cell" data-testid="feature-pagamento">
            <div className="feature-label">02 / PAGAMENTOS</div>
            <h4>Stripe & PayPal</h4>
            <p>Checkout em BRL e USD. Repasse automático e relatórios fiscais.</p>
          </div>
          <div className="feature-cell" data-testid="feature-seguranca">
            <div className="feature-label">03 / SEGURANÇA</div>
            <h4>Criptografia de ponta</h4>
            <p>CPF/RG criptografados, RLS no banco e logs de auditoria em tempo real.</p>
          </div>
          <div className="feature-cell" data-testid="feature-coautoria">
            <div className="feature-label">04 / COAUTORIA</div>
            <h4>Split automático</h4>
            <p>Divida receitas com coautores direto no cadastro da obra.</p>
          </div>
          <div className="feature-cell" data-testid="feature-analytics">
            <div className="feature-label">05 / ANALYTICS</div>
            <h4>Dashboard completo</h4>
            <p>Vendas, plays, origem do tráfego e performance por obra.</p>
          </div>
          <div className="feature-cell" data-testid="feature-suporte">
            <div className="feature-label">06 / SUPORTE</div>
            <h4>Humano, quando precisa</h4>
            <p>Equipe dedicada e base de conhecimento aberta 24/7.</p>
          </div>
        </div>
      </section>

      {/* Manifesto editorial (sem depoimentos fake) */}
      <section className="testimonial" data-testid="section-manifesto">
        <div className="testimonial-inner">
          <span className="quote-mark">"</span>
          <blockquote className="testimonial-quote">
            Feito por quem respeita a obra.<br />
            <span className="italic-light">Pago por quem respeita o autor.</span>
          </blockquote>
          <div className="testimonial-author">
            <div>
              <strong>Pitch.me</strong>
              <span>Marketplace independente de composições musicais</span>
            </div>
          </div>
        </div>
      </section>

      {/* Preços / Stats */}
      <section className="section-block" id="precos" data-testid="section-precos">
        <div className="block-header">
          <span className="section-index">03</span>
          <h2 className="section-title">Preço honesto. Sem pegadinhas.</h2>
          <p className="section-lead">
            Sem mensalidade. Você só paga quando vende.
          </p>
        </div>
        <div className="pricing-grid">
          <div className="price-cell" data-testid="plan-basico">
            <div className="price-label">PLANO BÁSICO</div>
            <div className="price-value">Grátis</div>
            <ul className="price-list">
              <li>Upload ilimitado</li>
              <li>Taxa de 12% por venda</li>
              <li>Pagamento em até 7 dias</li>
              <li>Suporte por e-mail</li>
            </ul>
            <button className="btn-ghost full" onClick={handleCTA}>
              Começar grátis →
            </button>
          </div>
          <div className="price-cell price-cell-feature" data-testid="plan-pro">
            <div className="price-ribbon">MAIS POPULAR</div>
            <div className="price-label">PLANO PRO</div>
            <div className="price-value">R$ 49<small>/mês</small></div>
            <ul className="price-list">
              <li>Tudo do Básico</li>
              <li>Taxa reduzida de 7% por venda</li>
              <li>Pagamento em 24h</li>
              <li>Analytics avançado</li>
              <li>Suporte prioritário</li>
            </ul>
            <button className="btn-primary full" onClick={handleCTA} data-testid="plan-pro-cta">
              Assinar Pro ▶
            </button>
          </div>
        </div>
      </section>

      {/* Footer massivo */}
      <footer className="footer-massive" data-testid="footer">
        <div className="footer-top">
          <div className="footer-links-row">
            <div>
              <h4>Plataforma</h4>
              <a href="#como-funciona">Como Funciona</a>
              <a href="#recursos">Recursos</a>
              <a href="#precos">Preços</a>
              <a href="/login">Login</a>
            </div>
            <div>
              <h4>Legal</h4>
              <a href="#termos">Termos de Uso</a>
              <a href="#privacidade">Privacidade</a>
              <a href="#contrato">Contratos</a>
            </div>
            <div>
              <h4>Contato</h4>
              <a href="mailto:contato@pitchme.com">contato@pitchme.com</a>
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
          <div className="footer-cta">
            <h2>Comece agora.</h2>
            <button
              className="btn-primary footer-btn"
              onClick={handleCTA}
              data-testid="footer-cta-comecar"
            >
              ▶ Criar conta grátis
            </button>
          </div>
        </div>
        <div className="footer-wordmark">PITCH.ME</div>
        <div className="footer-bottom">
          <span>© 2025 Pitch.me — Todos os direitos reservados.</span>
          <span>Feito com precisão para compositores.</span>
        </div>
      </footer>

      {showContato && (
        <div className="modal-backdrop" onClick={() => setShowContato(false)} data-testid="contato-modal">
          <div className="modal-card" onClick={(e) => e.stopPropagation()}>
            <h3>Fale Conosco</h3>
            <p>Envie um e-mail para <strong>contato@pitchme.com</strong> ou responda este modal em breve.</p>
            <button className="btn-primary" onClick={() => setShowContato(false)} data-testid="contato-fechar">
              Fechar
            </button>
          </div>
        </div>
      )}

      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&family=IBM+Plex+Sans:wght@300;400;500;600&display=swap');

        :root {
          --bg: #FFFFFF;
          --surface: #F4F4F5;
          --text: #09090B;
          --muted: #71717A;
          --accent: #E11D48;
          --border: #E4E4E7;
          --ink: #09090B;
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
          box-shadow: 0 0 0 4px rgba(225,29,72,0.15);
          animation: pulse 1.6s ease-in-out infinite;
        }
        @keyframes pulse {
          0%,100% { box-shadow: 0 0 0 4px rgba(225,29,72,0.18); }
          50% { box-shadow: 0 0 0 8px rgba(225,29,72,0.05); }
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
          transition: background .2s ease;
        }
        .feature-cell:hover { background: var(--surface); }
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
        }
        .price-cell:last-child { border-right: none; }
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

```

---

## 5. `frontend/src/pages/Login.jsx`

*151 linhas · 8.0K*

```jsx
import React, { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { supabase } from '../lib/supabase'

import './Login.css'

export default function Login() {
  const { user, signInWithGoogle, loading } = useAuth()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()

  const [aba,      setAba]     = useState(searchParams.get('cadastro') === '1' ? 'cadastrar' : 'entrar')
  const [form,     setForm]    = useState({
    nome: '', nome_artistico: '', telefone: '',
    email: '', senha: '', confirmar_senha: '', role: 'compositor',
  })
  const [erro,     setErro]    = useState('')
  const [sucesso,  setSucesso] = useState('')
  const [enviando, setEnviando]= useState(false)

  useEffect(() => {
    if (!loading && user) navigate('/dashboard')
  }, [user, loading, navigate])

  function handleChange(e) {
    setForm(prev => ({ ...prev, [e.target.name]: e.target.value }))
    setErro('')
  }

  async function handleLogin(e) {
    e.preventDefault(); setErro(''); setEnviando(true)
    const { error } = await supabase.auth.signInWithPassword({ email: form.email, password: form.senha })
    if (error) setErro('Email ou senha incorretos.')
    setEnviando(false)
  }

  async function handleCadastro(e) {
    e.preventDefault(); setErro('')
    if (!form.nome.trim())  { setErro('Nome completo é obrigatório.'); return }
    if (!form.email.trim()) { setErro('Email é obrigatório.'); return }
    if (form.senha.length < 6) { setErro('A senha deve ter no mínimo 6 caracteres.'); return }
    if (form.senha !== form.confirmar_senha) { setErro('As senhas não coincidem.'); return }
    setEnviando(true)
    const { error } = await supabase.auth.signUp({
      email: form.email, password: form.senha,
      options: { data: {
        full_name: form.nome.trim(),
        nome_artistico: form.nome_artistico.trim() || null,
        telefone: form.telefone.trim() || null,
        role: form.role,
      }},
    })
    if (error) {
      setErro(error.message.includes('already registered') ? 'Email já cadastrado. Tente fazer login.' : error.message)
    } else {
      setSucesso('Conta criada! Verifique seu email para confirmar o cadastro.')
      setForm({ nome:'', nome_artistico:'', telefone:'', email:'', senha:'', confirmar_senha:'', role:'compositor' })
    }
    setEnviando(false)
  }

  return (
    <div className="login-root">
      <div className="login-card">
        <div className="login-logo">
          <span className="login-logo-icon">♪</span>
          <span className="login-logo-text">PITCH.ME</span>
        </div>
        <p className="login-tagline">Plataforma de composições musicais</p>

        <div className="login-tabs">
          <button className={`login-tab ${aba==='entrar'?'active':''}`} onClick={()=>{setAba('entrar');setErro('');setSucesso('')}}>Entrar</button>
          <button className={`login-tab ${aba==='cadastrar'?'active':''}`} onClick={()=>{setAba('cadastrar');setErro('');setSucesso('')}}>Criar conta</button>
        </div>

        {aba === 'entrar' && (
          <form onSubmit={handleLogin} className="login-form">
            <div className="login-field">
              <label>Email</label>
              <input name="email" type="email" required placeholder="seu@email.com" value={form.email} onChange={handleChange}/>
            </div>
            <div className="login-field">
              <label>Senha</label>
              <input name="senha" type="password" required placeholder="••••••••" value={form.senha} onChange={handleChange}/>
            </div>
            {erro && <div className="login-erro">{erro}</div>}
            <button type="submit" className="login-btn-primary" disabled={enviando}>{enviando?'Entrando…':'Entrar'}</button>
            <div className="login-divisor"><span>ou</span></div>
            <button type="button" className="login-btn-google" onClick={signInWithGoogle}>
              <GoogleIcon/> Entrar com Google
            </button>
          </form>
        )}

        {aba === 'cadastrar' && (
          <form onSubmit={handleCadastro} className="login-form">
            <div className="login-role-group">
              <button type="button" className={`login-role-btn ${form.role==='compositor'?'active':''}`} onClick={()=>setForm(p=>({...p,role:'compositor'}))}>🎵 Compositor</button>
              <button type="button" className={`login-role-btn ${form.role==='interprete'?'active':''}`} onClick={()=>setForm(p=>({...p,role:'interprete'}))}>🎤 Intérprete</button>
            </div>
            <div className="login-field">
              <label>Nome completo *</label>
              <input name="nome" type="text" required placeholder="Seu nome completo" value={form.nome} onChange={handleChange}/>
            </div>
            <div className="login-field">
              <label>Nome artístico</label>
              <input name="nome_artistico" type="text" placeholder="Como você é conhecido no meio musical" value={form.nome_artistico} onChange={handleChange}/>
            </div>
            <div className="login-field">
              <label>Telefone <span className="login-opcional">(opcional)</span></label>
              <input name="telefone" type="tel" placeholder="(11) 99999-9999" value={form.telefone} onChange={handleChange}/>
            </div>
            <div className="login-field">
              <label>Email *</label>
              <input name="email" type="email" required placeholder="seu@email.com" value={form.email} onChange={handleChange}/>
            </div>
            <div className="login-grid-2">
              <div className="login-field">
                <label>Senha *</label>
                <input name="senha" type="password" required placeholder="Mínimo 6 caracteres" value={form.senha} onChange={handleChange}/>
              </div>
              <div className="login-field">
                <label>Confirmar senha *</label>
                <input name="confirmar_senha" type="password" required placeholder="Repita a senha" value={form.confirmar_senha} onChange={handleChange}/>
              </div>
            </div>
            {erro    && <div className="login-erro">{erro}</div>}
            {sucesso && <div className="login-sucesso">{sucesso}</div>}
            <button type="submit" className="login-btn-primary" disabled={enviando}>{enviando?'Criando conta…':'Criar conta'}</button>
            <div className="login-divisor"><span>ou</span></div>
            <button type="button" className="login-btn-google" onClick={signInWithGoogle}>
              <GoogleIcon/> Cadastrar com Google
            </button>
          </form>
        )}
      </div>
    </div>
  )
}

function GoogleIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
      <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
      <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
      <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z" fill="#FBBC05"/>
      <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
    </svg>
  )
}

```

---

## 6. `frontend/src/pages/Login.css`

*270 linhas · 8.0K*

```css
/* ============================================================
   Login / Cadastro — PITCH.ME (Design 1: branco + preto + red REC)
   ============================================================ */

.login-root {
  min-height: 100vh;
  display: flex;
  align-items: stretch;
  justify-content: center;
  background: var(--bg);
  padding: 0;
  position: relative;
  overflow: hidden;
}

/* Painel lateral esquerdo (imagem editorial) — desktop only */
.login-root::before {
  content: '';
  position: absolute;
  top: 0; left: 0; bottom: 0;
  width: 42%;
  background:
    linear-gradient(180deg, rgba(9,9,11,0.55) 0%, rgba(9,9,11,0.75) 100%),
    url('https://images.pexels.com/photos/32725048/pexels-photo-32725048.jpeg?auto=compress&cs=tinysrgb&w=1200') center / cover;
  border-right: 1px solid var(--border);
  pointer-events: none;
}
.login-root::after {
  content: 'PITCH.ME';
  position: absolute;
  top: 50%; left: 21%;
  transform: translate(-50%, -50%);
  font-family: 'Space Grotesk', sans-serif;
  font-weight: 700;
  font-size: clamp(48px, 6vw, 92px);
  color: #fff;
  letter-spacing: -0.04em;
  line-height: 0.9;
  pointer-events: none;
  white-space: nowrap;
}

@media (max-width: 900px) {
  .login-root::before,
  .login-root::after { display: none; }
}

/* Card */
.login-card {
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 0;
  padding: 48px 40px;
  width: 100%;
  max-width: 480px;
  margin-left: auto;
  margin-right: 8%;
  align-self: center;
  position: relative;
  z-index: 1;
}
@media (max-width: 900px) {
  .login-card { margin: 24px; }
}

/* ── Logo ───────────────────────────────── */
.login-logo {
  display: flex; align-items: center; justify-content: flex-start;
  gap: 10px; margin-bottom: 4px;
}
.login-logo-icon { font-size: 10px; color: var(--brand); }
.login-logo-text {
  font-family: 'Space Grotesk', sans-serif;
  font-size: 20px;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: -0.02em;
}
.login-tagline {
  text-align: left;
  font-size: 13px;
  color: var(--text-muted);
  margin-bottom: 36px;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  font-weight: 500;
}

/* ── Abas ───────────────────────────────── */
.login-tabs {
  display: flex;
  border-bottom: 1px solid var(--border);
  margin-bottom: 28px;
  gap: 0;
}
.login-tab {
  flex: 1;
  padding: 12px 0;
  border: none;
  background: transparent;
  border-bottom: 2px solid transparent;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-muted);
  cursor: pointer;
  transition: all .15s;
  font-family: inherit;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  margin-bottom: -1px;
}
.login-tab.active {
  color: var(--text-primary);
  border-bottom-color: var(--brand);
}
.login-tab:not(.active):hover { color: var(--text-primary); }

/* ── Seletor de role ───────────────────── */
.login-role-group {
  display: grid;
  grid-template-columns: 1fr 1fr;
  border: 1px solid var(--border);
  margin-bottom: 20px;
}
.login-role-btn {
  padding: 14px;
  border: none;
  border-right: 1px solid var(--border);
  background: var(--bg);
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all .15s;
  font-family: inherit;
}
.login-role-btn:last-child { border-right: none; }
.login-role-btn:hover { background: var(--surface-2); color: var(--text-primary); }
.login-role-btn.active {
  background: var(--ink);
  color: #fff;
  font-weight: 600;
}

/* ── Formulário ─────────────────────────── */
.login-form { display: flex; flex-direction: column; gap: 0; }
.login-field { display: flex; flex-direction: column; gap: 6px; margin-bottom: 16px; }
.login-field label {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-secondary);
  letter-spacing: 0.12em;
  text-transform: uppercase;
}
.login-opcional {
  font-weight: 400;
  color: var(--text-muted);
  text-transform: none;
  letter-spacing: 0;
}

.login-field input {
  padding: 12px 14px;
  border: 1px solid var(--border);
  border-radius: 0;
  font-size: 14px;
  color: var(--text-primary);
  background: var(--bg);
  outline: none;
  transition: border-color .15s, box-shadow .15s;
  font-family: inherit;
}
.login-field input::placeholder { color: var(--text-muted); }
.login-field input:focus {
  border-color: var(--ink);
  box-shadow: 0 0 0 3px rgba(9,9,11,.08);
}

.login-grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }

/* ── Alertas ────────────────────────────── */
.login-erro {
  background: var(--error-bg);
  color: var(--error);
  border: 1px solid rgba(220,38,38,.3);
  border-radius: 0;
  padding: 10px 14px;
  font-size: 13px;
  margin-bottom: 14px;
}
.login-sucesso {
  background: var(--success-bg);
  color: var(--success);
  border: 1px solid rgba(22,163,74,.3);
  border-radius: 0;
  padding: 10px 14px;
  font-size: 13px;
  margin-bottom: 14px;
}

/* ── Botões ─────────────────────────────── */
.login-btn-primary {
  width: 100%;
  padding: 14px;
  background: var(--brand);
  color: #fff;
  border: 1px solid var(--brand);
  border-radius: 0;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  transition: all .15s;
  margin-bottom: 14px;
  font-family: inherit;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
.login-btn-primary:hover {
  background: var(--ink);
  border-color: var(--ink);
  transform: translateY(-1px);
}
.login-btn-primary:disabled { opacity: .5; cursor: not-allowed; transform: none; }

.login-divisor {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 14px;
  color: var(--text-muted);
  font-size: 11px;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  font-weight: 600;
}
.login-divisor::before,
.login-divisor::after {
  content: '';
  flex: 1;
  height: 1px;
  background: var(--border);
}

.login-btn-google {
  width: 100%;
  padding: 13px;
  background: var(--bg);
  color: var(--text-primary);
  border: 1px solid var(--border);
  border-radius: 0;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  transition: all .15s;
  font-family: inherit;
}
.login-btn-google:hover {
  border-color: var(--ink);
  background: var(--surface-2);
}

/* ── Responsivo ─────────────────────────── */
@media (max-width: 480px) {
  .login-card   { padding: 32px 24px; }
  .login-grid-2 { grid-template-columns: 1fr; }
}

```

---

## 7. `frontend/src/components/SideMenu.jsx`

*209 linhas · 8.0K*

```jsx
import React, { useState, useEffect, useRef } from 'react'
import { NavLink, useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import './SideMenu.css'

const NAV_ITEMS = {
  compositor: [
    { to: '/descoberta',  icon: '⊞', label: 'Descoberta'      },
    { to: '/dashboard',   icon: '◈', label: 'Dashboard'       },
    { to: '/obras',       icon: '♫', label: 'Minhas obras'    },
    { to: '/obras/nova',  icon: '♪', label: 'Nova obra'       },
    { to: '/saques',      icon: '◎', label: 'Saques (PayPal)' },
    { to: '/ofertas',     icon: '✉', label: 'Ofertas'         },
  ],
  interprete: [
    { to: '/descoberta',  icon: '⊞', label: 'Descoberta'      },
    { to: '/compras',     icon: '◉', label: 'Compras'         },
    { to: '/ofertas',     icon: '✉', label: 'Ofertas'         },
  ],
  administrador: [
    { to: '/descoberta',  icon: '⊞', label: 'Descoberta'      },
    { to: '/admin',       icon: '▦', label: 'Painel admin'    },
  ],
}

function useIsMobile() {
  const [m, setM] = useState(() => typeof window !== 'undefined' && window.innerWidth < 768)
  useEffect(() => {
    function h() { setM(window.innerWidth < 768) }
    window.addEventListener('resize', h)
    return () => window.removeEventListener('resize', h)
  }, [])
  return m
}

function UserMenu({ perfil, collapsed }) {
  const [open, setOpen] = useState(false)
  const ref = useRef(null)
  const navigate = useNavigate()
  const { signOut } = useAuth()

  useEffect(() => {
    function handle(e) { if (ref.current && !ref.current.contains(e.target)) setOpen(false) }
    document.addEventListener('mousedown', handle)
    return () => document.removeEventListener('mousedown', handle)
  }, [])

  if (!perfil) return null
  const iniciais = perfil.nome?.split(' ').slice(0,2).map(n=>n[0]).join('').toUpperCase() ?? '?'

  return (
    <div ref={ref} style={{ position: 'relative' }}>
      <div className="sidebar-user-btn" onClick={() => setOpen(o => !o)}>
        <div className="sidebar-avatar">
          {perfil.avatar_url ? <img src={perfil.avatar_url} alt={perfil.nome} /> : iniciais}
        </div>
        {!collapsed && (
          <>
            <div className="sidebar-user-info">
              <span className="sidebar-user-nome">{perfil.nome_artistico || perfil.nome}</span>
              <span className="sidebar-user-role">{perfil.role}</span>
            </div>
            <span style={{ fontSize: 10, color: 'var(--text-muted)', marginLeft: 'auto' }}>{open ? '▴' : '▾'}</span>
          </>
        )}
      </div>
      {open && (
        <div className="sidebar-user-dropdown">
          <button className="sidebar-user-item" onClick={() => { setOpen(false); navigate('/perfil/editar') }}>
            <span>✎</span> Editar informações
          </button>
          <div className="sidebar-user-divider" />
          <button className="sidebar-user-item sidebar-user-item-danger" onClick={() => { setOpen(false); signOut() }}>
            <span>⏻</span> Sair da conta
          </button>
        </div>
      )}
    </div>
  )
}

export default function SideMenu({ onCollapse }) {
  const isMobile = useIsMobile()
  const [collapsed, setCollapsed] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)
  const { perfil, signOut } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  useEffect(() => { onCollapse?.(isMobile ? true : collapsed) }, [collapsed, isMobile])
  useEffect(() => { setMobileOpen(false) }, [location.pathname])  // fecha drawer ao navegar

  const role = perfil?.role ?? 'compositor'
  const items = NAV_ITEMS[role] ?? NAV_ITEMS.compositor

  // ── MOBILE: hamburger + drawer ──────────────────────
  if (isMobile) {
    return (
      <>
        <button
          className="mobile-hamburger"
          onClick={() => setMobileOpen(true)}
          aria-label="Abrir menu"
        >
          <span /><span /><span />
        </button>

        {mobileOpen && (
          <div
            className="mobile-drawer-backdrop"
            onClick={() => setMobileOpen(false)}
          />
        )}

        <aside className={`sidebar mobile-drawer ${mobileOpen ? 'mobile-drawer-open' : ''}`}>
          <div className="sidebar-header">
            <button className="sidebar-logo-btn" onClick={() => { navigate('/descoberta'); setMobileOpen(false) }}>
              PITCH.ME
            </button>
            <button
              className="sidebar-toggle"
              onClick={() => setMobileOpen(false)}
              aria-label="Fechar menu"
            >×</button>
          </div>

          <nav className="sidebar-nav">
            {items.map(({ to, icon, label }) => (
              <NavLink key={to} to={to}
                className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}>
                <span className="sidebar-icon">{icon}</span>
                <span>{label}</span>
              </NavLink>
            ))}

            <div style={{ height: 1, background: 'var(--border)', margin: '8px 4px' }} />

            <NavLink to="/perfil/editar"
              className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}>
              <span className="sidebar-icon">✎</span>
              <span>Editar informações</span>
            </NavLink>

            <button
              className="sidebar-link"
              onClick={() => signOut()}
              style={{ color: 'var(--error)' }}>
              <span className="sidebar-icon">⏻</span>
              <span>Sair da conta</span>
            </button>
          </nav>

          <div className="sidebar-footer">
            <UserMenu perfil={perfil} collapsed={false} />
          </div>
        </aside>
      </>
    )
  }

  // ── DESKTOP: sidebar fixa ─────────────────────────
  return (
    <aside className={`sidebar ${collapsed ? 'collapsed' : ''}`}>
      <div className="sidebar-header">
        {!collapsed && (
          <button className="sidebar-logo-btn" onClick={() => navigate('/descoberta')}>
            PITCH.ME
          </button>
        )}
        <button className="sidebar-toggle" onClick={() => setCollapsed(c => !c)}>
          {collapsed ? '›' : '‹'}
        </button>
      </div>

      <nav className="sidebar-nav">
        {items.map(({ to, icon, label }) => (
          <NavLink key={to} to={to}
            className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}
            title={collapsed ? label : undefined}>
            <span className="sidebar-icon">{icon}</span>
            {!collapsed && <span>{label}</span>}
          </NavLink>
        ))}

        <div style={{ height: 1, background: 'var(--border)', margin: '8px 4px' }} />

        <NavLink to="/perfil/editar"
          className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}
          title={collapsed ? 'Editar informações' : undefined}>
          <span className="sidebar-icon">✎</span>
          {!collapsed && <span>Editar informações</span>}
        </NavLink>

        <button
          className="sidebar-link"
          onClick={() => signOut()}
          title={collapsed ? 'Sair da conta' : undefined}
          style={{ color: 'var(--error)' }}>
          <span className="sidebar-icon">⏻</span>
          {!collapsed && <span>Sair da conta</span>}
        </button>
      </nav>

      <div className="sidebar-footer">
        <UserMenu perfil={perfil} collapsed={collapsed} />
      </div>
    </aside>
  )
}

```

---

## 8. `frontend/src/components/SideMenu.css`

*264 linhas · 8.0K*

```css
/* ============================================================
   SideMenu — Design 1 (minimalista, branco + preto + red REC)
   ============================================================ */

.sidebar {
  position: fixed;
  top: 0; left: 0;
  height: 100vh;
  width: var(--sidebar-w);
  background: var(--bg);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  transition: width .2s ease;
  z-index: 100;
  overflow: hidden;
}
.sidebar.collapsed { width: var(--sidebar-collapsed); }

/* ── HEADER ──────────────────────────────── */
.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  border-bottom: 1px solid var(--border);
  min-height: 64px;
  flex-shrink: 0;
}

.sidebar-logo-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 15px;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: -0.02em;
  padding: 0;
  white-space: nowrap;
  overflow: hidden;
  transition: opacity .15s;
  display: flex;
  align-items: center;
  gap: 8px;
  font-family: 'Space Grotesk', sans-serif;
}
.sidebar-logo-btn::before {
  content: '●';
  font-size: 10px;
  color: var(--brand);
}
.sidebar-logo-btn:hover { opacity: .7; }

.sidebar-toggle {
  background: transparent;
  border: 1px solid var(--border);
  cursor: pointer;
  font-size: 14px;
  color: var(--text-muted);
  padding: 4px 8px;
  border-radius: 0;
  transition: all .15s;
  line-height: 1;
  flex-shrink: 0;
}
.sidebar-toggle:hover {
  border-color: var(--ink);
  color: var(--ink);
  background: var(--surface-2);
}

/* ── NAVEGAÇÃO ───────────────────────────── */
.sidebar-nav {
  flex: 1;
  padding: 16px 8px;
  display: flex;
  flex-direction: column;
  gap: 2px;
  overflow-y: auto;
  overflow-x: hidden;
}

.sidebar-link {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 0;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all .15s;
  text-decoration: none;
  border: none;
  background: none;
  width: 100%;
  white-space: nowrap;
  overflow: hidden;
  font-family: inherit;
  border-left: 2px solid transparent;
}
.sidebar-link:hover {
  background: var(--surface-2);
  color: var(--text-primary);
}
.sidebar-link.active {
  background: var(--surface-2);
  color: var(--text-primary);
  font-weight: 600;
  border-left-color: var(--brand);
}
.sidebar-link.active .sidebar-icon { color: var(--brand); }

.sidebar-icon {
  font-size: 15px;
  width: 20px;
  text-align: center;
  flex-shrink: 0;
  color: var(--text-muted);
}
.sidebar-link:hover .sidebar-icon { color: var(--text-primary); }

/* ── RODAPÉ / USUÁRIO ────────────────────── */
.sidebar-footer {
  padding: 8px;
  border-top: 1px solid var(--border);
  flex-shrink: 0;
  overflow: hidden;
  position: relative;
}

.sidebar-user-btn {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px;
  border: none;
  background: transparent;
  border-radius: 0;
  cursor: pointer;
  transition: background .15s;
  text-align: left;
  font-family: inherit;
}
.sidebar-user-btn:hover { background: var(--surface-2); }

.sidebar-avatar {
  width: 34px; height: 34px;
  border-radius: 0;
  background: var(--ink);
  border: 1px solid var(--ink);
  color: #fff;
  font-size: 12px; font-weight: 700;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0; overflow: hidden;
  font-family: 'Space Grotesk', sans-serif;
}
.sidebar-avatar img { width: 100%; height: 100%; object-fit: cover; }

.sidebar-user-info {
  flex: 1; min-width: 0;
  display: flex; flex-direction: column;
}
.sidebar-user-nome {
  font-size: 13px; font-weight: 600;
  color: var(--text-primary);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.sidebar-user-role {
  font-size: 10px;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.12em;
  font-weight: 600;
}

/* Dropdown */
.sidebar-user-dropdown {
  position: absolute;
  bottom: calc(100% + 4px);
  left: 8px; right: 8px;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 0;
  box-shadow: var(--shadow-lg);
  overflow: hidden;
  z-index: 300;
  animation: sDropIn .15s ease;
}
@keyframes sDropIn {
  from { opacity: 0; transform: translateY(6px); }
  to   { opacity: 1; transform: translateY(0); }
}

.sidebar-user-item {
  width: 100%;
  display: flex; align-items: center; gap: 10px;
  padding: 12px 14px;
  border: none; background: transparent;
  font-size: 13px; color: var(--text-secondary);
  cursor: pointer; text-align: left;
  transition: background .15s;
  font-family: inherit;
}
.sidebar-user-item:hover { background: var(--surface-2); color: var(--text-primary); }
.sidebar-user-divider { height: 1px; background: var(--border); }
.sidebar-user-item-danger { color: var(--error); }
.sidebar-user-item-danger:hover { background: var(--error-bg); color: var(--error); }

/* ════════════════════════════════════════════
   MOBILE — hamburger + drawer
════════════════════════════════════════════ */
.mobile-hamburger {
  display: none;
  position: fixed;
  top: 14px; left: 14px;
  z-index: 200;
  width: 44px; height: 44px;
  border-radius: 0;
  background: var(--bg);
  border: 1px solid var(--border);
  cursor: pointer;
  padding: 10px;
  flex-direction: column;
  gap: 4px;
  align-items: center;
  justify-content: center;
  transition: border-color .15s, box-shadow .15s;
  box-shadow: 0 2px 8px rgba(9,9,11,.08);
}
.mobile-hamburger:hover { border-color: var(--ink); }
.mobile-hamburger span {
  width: 20px; height: 2px;
  background: var(--text-primary);
  border-radius: 0;
}

.mobile-drawer-backdrop { display: none; }

@media (max-width: 767px) {
  .mobile-hamburger { display: flex; }

  .mobile-drawer-backdrop {
    display: block;
    position: fixed; inset: 0;
    background: rgba(9,9,11,.3);
    z-index: 150;
    backdrop-filter: blur(2px);
    animation: backdropIn .2s ease;
  }
  @keyframes backdropIn { from { opacity: 0; } to { opacity: 1; } }

  .sidebar.mobile-drawer {
    width: 280px !important;
    transform: translateX(-100%);
    transition: transform .25s ease;
    z-index: 160;
    box-shadow: 4px 0 40px rgba(9,9,11,.15);
  }
  .sidebar.mobile-drawer-open { transform: translateX(0); }
}

```

---

## 9. `frontend/src/components/GlobalPlayer.css`

*231 linhas · 8.0K*

```css
/* ============================================================
   GlobalPlayer — Design 1 (branco + preto + red REC accent)
   ============================================================ */

@keyframes gpSlideUp {
  from { transform: translateY(100%); opacity: 0; }
  to   { transform: translateY(0);    opacity: 1; }
}
@keyframes gpFadeIn {
  from { opacity: 0; transform: scale(.9) translateY(8px); }
  to   { opacity: 1; transform: scale(1)  translateY(0); }
}
@keyframes gp-spin { to { transform: rotate(360deg); } }

/* ── PLAYER COMPLETO ─────────────────────── */
.gp-root {
  position: fixed;
  bottom: 0; left: 0; right: 0;
  z-index: 500;
  background: var(--bg);
  border-top: 1px solid var(--border);
  box-shadow: 0 -4px 20px rgba(9,9,11,.06);
  animation: gpSlideUp .22s ease;
}

.gp-top-bar {
  height: 3px;
  background: var(--surface-2);
  cursor: pointer;
  position: relative;
  transition: height .15s;
}
.gp-top-bar:hover { height: 5px; }
.gp-top-bar-fill {
  height: 100%;
  background: var(--brand);
  transition: width .1s linear;
  pointer-events: none;
}

.gp-body {
  display: flex;
  align-items: center;
  padding: 10px 24px;
  gap: 20px;
  height: 68px;
}

/* Info */
.gp-track-info {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 260px;
  flex-shrink: 0;
  min-width: 0;
}
.gp-cover {
  width: 42px; height: 42px;
  border-radius: 0;
  background: var(--ink);
  display: flex; align-items: center; justify-content: center;
  font-size: 16px; font-weight: 700; color: #fff;
  flex-shrink: 0;
  font-family: 'Space Grotesk', sans-serif;
}
.gp-meta { min-width: 0; }
.gp-nome {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.gp-autor {
  font-size: 11px;
  color: var(--text-muted);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}

/* Controles */
.gp-controls {
  display: flex;
  align-items: center;
  gap: 16px;
  flex: 1;
  justify-content: center;
}
.gp-play-btn {
  width: 44px; height: 44px;
  border-radius: 0;
  background: var(--brand);
  color: #fff;
  border: 1px solid var(--brand);
  cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  transition: all .15s;
  flex-shrink: 0;
}
.gp-play-btn:hover  { background: var(--ink); border-color: var(--ink); }
.gp-play-btn:active { transform: scale(.95); }

.gp-icon-btn {
  background: none;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  padding: 6px;
  border-radius: 0;
  transition: color .15s, background .15s;
  flex-shrink: 0;
}
.gp-icon-btn:hover    { color: var(--text-primary); background: var(--surface-2); }
.gp-icon-btn:disabled { opacity: .25; cursor: default; }
.gp-close-btn:hover   { color: var(--error); }

/* Área direita */
.gp-right {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 260px;
  justify-content: flex-end;
  flex-shrink: 0;
}
.gp-time {
  font-size: 11px;
  color: var(--text-muted);
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
  font-family: 'Space Grotesk', sans-serif;
}
.gp-queue-info { font-size: 11px; color: var(--text-muted); white-space: nowrap; }

/* Volume */
.gp-volume { display: flex; align-items: center; gap: 6px; color: var(--text-muted); }
.gp-vol-slider {
  width: 70px; height: 3px;
  appearance: none;
  background: var(--surface-2);
  border-radius: 0;
  outline: none;
  cursor: pointer;
}
.gp-vol-slider::-webkit-slider-thumb {
  appearance: none;
  width: 12px; height: 12px;
  border-radius: 0;
  background: var(--brand);
  cursor: pointer;
}
.gp-vol-slider::-moz-range-thumb {
  width: 12px; height: 12px;
  border-radius: 0;
  background: var(--brand);
  border: none;
  cursor: pointer;
}

/* ── MINIMIZADO ──────────────────────────── */
.gp-mini {
  position: fixed;
  bottom: 16px; right: 16px;
  z-index: 500;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 0;
  padding: 10px 14px;
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  box-shadow: 0 8px 32px rgba(9,9,11,.08);
  min-width: 220px;
  max-width: 300px;
  transition: all .2s;
  animation: gpFadeIn .2s ease;
  overflow: hidden;
}
.gp-mini:hover {
  box-shadow: 0 12px 40px rgba(9,9,11,.12);
  border-color: var(--ink);
}

.gp-mini-cover {
  width: 36px; height: 36px;
  border-radius: 0;
  background: var(--ink);
  display: flex; align-items: center; justify-content: center;
  font-size: 14px; font-weight: 700; color: #fff;
  flex-shrink: 0;
  font-family: 'Space Grotesk', sans-serif;
}
.gp-mini-info { flex: 1; min-width: 0; display: flex; flex-direction: column; }
.gp-mini-nome  {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-primary);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.gp-mini-autor { font-size: 10px; color: var(--text-muted); }

.gp-mini-bar {
  position: absolute;
  bottom: 0; left: 0; right: 0;
  height: 2px;
  background: var(--surface-2);
  overflow: hidden;
}
.gp-mini-bar-fill {
  height: 100%;
  background: var(--brand);
  transition: width .1s linear;
}

.main-content.player-open { padding-bottom: calc(68px + 4px + 40px); }

/* ── RESPONSIVO ──────────────────────────── */
@media (max-width: 767px) {
  .gp-body    { padding: 8px 12px; height: 56px; gap: 10px; }
  .gp-track-info { width: auto; flex: 1; min-width: 0; }
  .gp-cover   { width: 36px; height: 36px; font-size: 14px; }
  .gp-nome    { font-size: 12px; }
  .gp-autor   { font-size: 10px; }
  .gp-controls { gap: 8px; flex: 0 0 auto; }
  .gp-play-btn { width: 38px; height: 38px; }
  .gp-right   { width: auto; gap: 6px; }
  .gp-volume  { display: none; }
  .gp-time    { display: none; }
  .gp-queue-info { display: none; }
}

```

---

## 10. `frontend/src/components/ProfileMenu.css`

*140 linhas · 4.0K*

```css
/* ── ProfileMenu — Design 1 (branco + preto) ── */
.pm-wrap { position: relative; padding: 8px 8px 0; }

.pm-trigger {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px;
  border: none;
  background: transparent;
  border-radius: 0;
  cursor: pointer;
  transition: background var(--transition);
  text-align: left;
}
.pm-trigger:hover { background: var(--surface-2); }

.pm-avatar-img,
.pm-avatar-initials {
  width: 36px; height: 36px;
  border-radius: 0;
  flex-shrink: 0;
  object-fit: cover;
}
.pm-avatar-initials {
  background: var(--ink);
  color: #fff;
  font-size: 12px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: 'Space Grotesk', sans-serif;
}
.pm-trigger-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}
.pm-trigger-nome {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.pm-trigger-role {
  font-size: 10px;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.12em;
  font-weight: 600;
}
.pm-chevron { font-size: 10px; color: var(--text-muted); }

/* Dropdown */
.pm-dropdown {
  position: absolute;
  bottom: calc(100% + 4px);
  left: 8px;
  right: 8px;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 0;
  box-shadow: var(--shadow-lg);
  z-index: 200;
  overflow: hidden;
  animation: pmFadeIn .15s ease;
}
@keyframes pmFadeIn {
  from { opacity: 0; transform: translateY(6px); }
  to   { opacity: 1; transform: translateY(0); }
}

.pm-dropdown-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  background: var(--surface-2);
  border-bottom: 1px solid var(--border);
}
.pm-dd-avatar-img,
.pm-dd-avatar-initials {
  width: 44px; height: 44px;
  border-radius: 0;
  flex-shrink: 0;
  object-fit: cover;
}
.pm-dd-avatar-initials {
  background: var(--ink);
  color: #fff;
  font-size: 15px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: 'Space Grotesk', sans-serif;
}
.pm-dd-nome      { font-size: 14px; font-weight: 600; color: var(--text-primary); }
.pm-dd-artistico { font-size: 12px; color: var(--brand); }
.pm-dd-email     { font-size: 11px; color: var(--text-muted); margin-top: 1px; }
.pm-nivel {
  display: inline-block;
  margin-top: 4px;
  font-size: 10px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 0;
  border: 1px solid var(--border);
  letter-spacing: 0.1em;
  text-transform: uppercase;
}
.pm-nivel-prata   { background: var(--surface-2); color: var(--text-secondary); }
.pm-nivel-ouro    { background: #FEF3C7; color: #92400E; border-color: #FCD34D; }
.pm-nivel-diamante{ background: var(--brand-light); color: var(--brand); border-color: var(--brand-border); }

.pm-divider { height: 1px; background: var(--border); margin: 4px 0; }

.pm-item {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 11px 14px;
  border: none;
  background: transparent;
  font-size: 13px;
  color: var(--text-secondary);
  cursor: pointer;
  transition: background var(--transition);
  text-align: left;
}
.pm-item:hover { background: var(--surface-2); color: var(--text-primary); }
.pm-item-icon  { font-size: 14px; width: 18px; text-align: center; }
.pm-item-danger       { color: var(--error); }
.pm-item-danger:hover { background: var(--error-bg); color: var(--error); }

```

---

## 11. `frontend/src/components/FaleConoscoModal.jsx`

*199 linhas · 8.0K*

```jsx
import React, { useState } from 'react'
import { api } from '../lib/api'

const EMAIL_SUPORTE = 'contatopitch.me@gmail.com'
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
              background: '#E11D48',
              color: '#fff', border: '1px solid #E11D48', borderRadius: 0,
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

```

---

## 12. `frontend/src/components/PWAInstaller.jsx`

*132 linhas · 8.0K*

```jsx
import React, { useEffect, useState } from 'react'

/**
 * Registra o service worker e mostra um prompt discreto pra instalar o app.
 *
 * Uso: <PWAInstaller /> dentro do App root.
 */
export default function PWAInstaller() {
  const [deferredPrompt, setDeferredPrompt] = useState(null)
  const [installed,      setInstalled]      = useState(false)
  const [dismissed,      setDismissed]      = useState(false)

  // 1. Registra o Service Worker + força update quando houver nova versão
  useEffect(() => {
    if (!('serviceWorker' in navigator)) return
    // Em dev não registra (evita cache de HMR)
    if (import.meta.env.DEV) return

    window.addEventListener('load', async () => {
      try {
        const reg = await navigator.serviceWorker.register('/sw.js')

        // Força checar update a cada load (pega novo sw.js rapidamente)
        reg.update().catch(() => {})

        // Se já tem um SW novo esperando, pede pra ele tomar controle
        if (reg.waiting) {
          reg.waiting.postMessage({ type: 'SKIP_WAITING' })
        }

        // Quando um novo SW for instalado, envia skipWaiting
        reg.addEventListener('updatefound', () => {
          const newWorker = reg.installing
          if (!newWorker) return
          newWorker.addEventListener('statechange', () => {
            if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
              // Novo SW pronto — pede pra ativar imediatamente
              newWorker.postMessage({ type: 'SKIP_WAITING' })
            }
          })
        })

        // Quando o controller mudar (novo SW assumiu), recarrega 1x pra pegar novos assets
        let refreshing = false
        navigator.serviceWorker.addEventListener('controllerchange', () => {
          if (refreshing) return
          refreshing = true
          window.location.reload()
        })
      } catch { /* noop */ }
    })
  }, [])

  // 2. Escuta evento de "installable"
  useEffect(() => {
    function onPrompt(e) {
      e.preventDefault()
      // Só mostra o prompt se ainda não foi dispensado nessa sessão
      if (sessionStorage.getItem('pwa_dismissed') === '1') return
      setDeferredPrompt(e)
    }
    function onInstalled() {
      setInstalled(true)
      setDeferredPrompt(null)
    }
    window.addEventListener('beforeinstallprompt', onPrompt)
    window.addEventListener('appinstalled', onInstalled)
    return () => {
      window.removeEventListener('beforeinstallprompt', onPrompt)
      window.removeEventListener('appinstalled', onInstalled)
    }
  }, [])

  async function handleInstall() {
    if (!deferredPrompt) return
    deferredPrompt.prompt()
    await deferredPrompt.userChoice
    setDeferredPrompt(null)
  }

  function dismiss() {
    sessionStorage.setItem('pwa_dismissed', '1')
    setDismissed(true)
  }

  if (installed || dismissed || !deferredPrompt) return null

  return (
    <div style={{
      position: 'fixed',
      bottom: 16, left: 16, right: 16,
      maxWidth: 420, margin: '0 auto',
      padding: 14,
      background: 'linear-gradient(135deg,#BE123C,#09090B)',
      color: '#fff', borderRadius: 14,
      boxShadow: '0 10px 30px rgba(225,29,72,.4)',
      display: 'flex', alignItems: 'center', gap: 12,
      zIndex: 9999,
      animation: 'pwa-slide-up .3s ease-out',
    }}>
      <style>{`
        @keyframes pwa-slide-up {
          from { transform: translateY(40px); opacity: 0 }
          to   { transform: translateY(0);    opacity: 1 }
        }
      `}</style>
      <div style={{
        fontSize: 28, width: 40, height: 40, flexShrink: 0,
        background: 'rgba(255,255,255,.2)', borderRadius: 10,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}>♪</div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 13, fontWeight: 700 }}>Instalar Pitch.me</div>
        <div style={{ fontSize: 11, opacity: .9 }}>Abra direto da tela inicial</div>
      </div>
      <button
        onClick={handleInstall}
        style={{
          background: 'rgba(255,255,255,.12)', color: '#fff',
          border: 'none', padding: '8px 14px', borderRadius: 99,
          fontSize: 13, fontWeight: 700, cursor: 'pointer',
        }}>Instalar</button>
      <button
        onClick={dismiss}
        aria-label="Dispensar"
        style={{
          background: 'transparent', border: 'none', color: '#fff',
          opacity: .6, cursor: 'pointer', fontSize: 20, padding: 4,
        }}>×</button>
    </div>
  )
}

```

---

## 13. `frontend/src/pages/Dashboard.jsx`

*344 linhas · 16K*

```jsx
import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { usePlayer } from '../contexts/PlayerContext'
import { api } from '../lib/api'

function fmt(cents) {
  return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format((cents ?? 0) / 100)
}

/* ── Configuração dos níveis ─────────────────────────────── */
const NIVEL_INFO = {
  ouro: {
    label: '🥇 Ouro',
    bg: 'linear-gradient(135deg, #b8860b 0%, #f5c842 100%)',
    glow: 'rgba(245,200,66,.25)',
    texto: 'Licenciamento de R$ 500 a R$ 3.000',
    proximoNivel: 'Venda 6 obras para desbloquear o nível Diamante (licenciamento até R$ 10.000).',
  },
  diamante: {
    label: '💎 Diamante',
    bg: 'linear-gradient(135deg, #BE123C 0%, #09090B 100%)',
    glow: 'rgba(225,29,72,.25)',
    texto: 'Licenciamento de R$ 500 a R$ 10.000',
    proximoNivel: 'Você está no nível máximo! Continue publicando composições de alta qualidade.',
  },
}

/* ── Status das obras ────────────────────────────────────── */
const STATUS_STYLE = {
  publicada: { bg: 'rgba(34,197,94,.12)',  cor: '#22c55e', label: '✓ Publicada' },
  rascunho:  { bg: 'rgba(245,158,11,.12)', cor: '#f59e0b', label: 'Rascunho'   },
  arquivada: { bg: 'rgba(255,255,255,.06)', cor: 'rgba(255,255,255,.4)', label: 'Arquivada' },
}

/* ── Componente StatCard ─────────────────────────────────── */
function StatCard({ label, value, sub, accent = false }) {
  return (
    <div style={{
      padding: '18px 20px',
      background: accent ? 'rgba(225,29,72,.18)' : 'var(--surface)',
      border: `1px solid ${accent ? 'rgba(225,29,72,.4)' : 'var(--border)'}`,
      borderRadius: 14,
    }}>
      <div style={{
        fontSize: 11, fontWeight: 700, color: 'var(--text-muted)',
        textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 8,
      }}>
        {label}
      </div>
      <div style={{
        fontSize: 28, fontWeight: 900, color: accent ? 'var(--brand)' : 'var(--text-primary)',
        lineHeight: 1, marginBottom: 6, letterSpacing: '-1px',
      }}>
        {value}
      </div>
      {sub && (
        <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{sub}</div>
      )}
    </div>
  )
}

export default function Dashboard() {
  const { perfil } = useAuth()
  const navigate   = useNavigate()
  const { playObra } = usePlayer()
  const [data,       setData]       = useState(null)
  const [loading,    setLoading]    = useState(true)
  const [lastUpdate, setLastUpdate] = useState(Date.now())

  async function load(silent = false) {
    if (!silent) setLoading(true)
    try {
      const d = await api.get('/perfis/me/dashboard')
      setData(d)
      setLastUpdate(Date.now())
    } catch (e) {
      console.error('Erro dashboard:', e)
    } finally { setLoading(false) }
  }

  useEffect(() => {
    load()
    const interval = setInterval(() => load(true), 10_000)
    return () => clearInterval(interval)
  }, [])

  if (loading || !data) {
    return (
      <div style={{ padding: 40 }}>
        <div style={{
          display: 'flex', gap: 12, flexDirection: 'column',
        }}>
          {[1,2,3].map(i => (
            <div key={i} style={{
              height: 60, borderRadius: 0,
              background: 'var(--surface-2)',
              border: '1px solid var(--border)',
              animation: 'pulse 1.4s ease-in-out infinite',
              opacity: .8,
            }} />
          ))}
        </div>
      </div>
    )
  }

  const nivelInfo = NIVEL_INFO[data.nivel] ?? NIVEL_INFO.ouro
  const segundosDesde = Math.floor((Date.now() - lastUpdate) / 1000)

  return (
    <div style={{ padding: 32, maxWidth: 1100, minHeight: '100vh' }}>

      {/* ── Header ───────────────────────────── */}
      <div style={{
        display: 'flex', justifyContent: 'space-between',
        alignItems: 'flex-start', marginBottom: 24,
        flexWrap: 'wrap', gap: 12,
      }}>
        <div>
          <h1 style={{
            fontSize: 28, fontWeight: 900, color: 'var(--text-primary)',
            letterSpacing: '-1px', marginBottom: 4,
          }}>
            Dashboard
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: 13 }}>
            Olá, <strong style={{ color: 'var(--text-secondary)' }}>
              {perfil?.nome_artistico || perfil?.nome}
            </strong>
            {' · '}atualizado {segundosDesde < 5 ? 'agora mesmo' : `há ${segundosDesde}s`}
            <button
              onClick={() => load()}
              style={{
                background: 'none', border: 'none',
                color: 'var(--brand)', cursor: 'pointer',
                marginLeft: 8, fontSize: 12, fontFamily: 'inherit',
              }}>
              ↻ atualizar
            </button>
          </p>
        </div>
        <button className="btn btn-primary" onClick={() => navigate('/obras/nova')}>
          + Nova obra
        </button>
      </div>

      {/* ── Card de nível ──────────────────── */}
      <div style={{
        padding: '22px 24px', marginBottom: 24,
        background: nivelInfo.bg, color: '#fff',
        borderRadius: 16,
        boxShadow: `0 8px 40px ${nivelInfo.glow}`,
        position: 'relative', overflow: 'hidden',
      }}>
        {/* Ruído de fundo */}
        <div style={{
          position: 'absolute', inset: 0, opacity: .04,
          backgroundImage: 'url("data:image/svg+xml,%3Csvg viewBox=\'0 0 256 256\' xmlns=\'http://www.w3.org/2000/svg\'%3E%3Cfilter id=\'n\'%3E%3CfeTurbulence type=\'fractalNoise\' baseFrequency=\'0.9\' numOctaves=\'4\' stitchTiles=\'stitch\'/%3E%3C/filter%3E%3Crect width=\'100%25\' height=\'100%25\' filter=\'url(%23n)\'/%3E%3C/svg%3E")',
          pointerEvents: 'none',
        }} />

        <div style={{ display: 'flex', alignItems: 'center', gap: 16, flexWrap: 'wrap', position: 'relative' }}>
          <div style={{ fontSize: 36 }}>{nivelInfo.label.split(' ')[0]}</div>
          <div style={{ flex: 1, minWidth: 200 }}>
            <div style={{ fontSize: 11, fontWeight: 700, opacity: .7, textTransform: 'uppercase', letterSpacing: '.1em' }}>
              Seu nível de compositor
            </div>
            <div style={{ fontSize: 22, fontWeight: 900, marginTop: 2, letterSpacing: '-.5px' }}>
              {nivelInfo.label.split(' ').slice(1).join(' ')}
            </div>
            <div style={{ fontSize: 13, opacity: .85, marginTop: 4 }}>{nivelInfo.texto}</div>
          </div>
          <div style={{
            padding: '8px 16px',
            background: 'rgba(0,0,0,.25)',
            borderRadius: 99, fontSize: 13, fontWeight: 600,
            backdropFilter: 'blur(8px)',
            border: '1px solid rgba(9,9,11,.1)',
          }}>
            {data.total_vendas} venda{data.total_vendas !== 1 ? 's' : ''} confirmada{data.total_vendas !== 1 ? 's' : ''}
          </div>
        </div>

        <div style={{
          marginTop: 14, fontSize: 13, padding: '10px 14px',
          background: 'rgba(0,0,0,.2)', borderRadius: 10,
          backdropFilter: 'blur(8px)', position: 'relative',
        }}>
          💡 {nivelInfo.proximoNivel}
        </div>
      </div>

      {/* ── Stats grid ─────────────────────── */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(190px, 1fr))',
        gap: 14, marginBottom: 28,
      }}>
        <StatCard
          label="Obras publicadas"
          value={data.obras_publicadas}
          sub={`de ${data.total_obras} cadastradas`}
        />
        <StatCard
          label="Vendas confirmadas"
          value={data.total_vendas}
        />
        <StatCard
          label="Saldo disponível"
          value={fmt(data.saldo_atual_cents)}
          sub="Pronto para saque"
          accent
        />
        <StatCard
          label="Receita total"
          value={fmt(data.receita_total_cents)}
          sub={`Já sacado: ${fmt(data.total_sacado_cents)}`}
        />
      </div>

      {/* ── Listagem de obras ───────────────── */}
      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        {/* Header da listagem */}
        <div style={{
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          padding: '18px 22px',
          borderBottom: '1px solid var(--border)',
        }}>
          <h2 style={{ fontSize: 16, fontWeight: 800, color: 'var(--text-primary)' }}>
            Minhas obras ({data.obras.length})
          </h2>
          <button
            onClick={() => navigate('/obras')}
            style={{
              background: 'none', border: 'none',
              color: 'var(--brand)', fontSize: 13,
              cursor: 'pointer', fontWeight: 600, fontFamily: 'inherit',
            }}>
            Ver todas →
          </button>
        </div>

        {/* Lista */}
        {data.obras.length === 0 ? (
          <div style={{ padding: '56px 32px', textAlign: 'center' }}>
            <div style={{ fontSize: 48, opacity: .15, marginBottom: 12 }}>♪</div>
            <p style={{ color: 'var(--text-muted)', marginBottom: 18, fontSize: 15 }}>
              Você ainda não cadastrou nenhuma obra.
            </p>
            <button className="btn btn-primary" onClick={() => navigate('/obras/nova')}>
              Cadastrar primeira obra
            </button>
          </div>
        ) : (
          <div style={{ padding: '10px 14px', display: 'flex', flexDirection: 'column', gap: 4 }}>
            {data.obras.slice(0, 8).map(obra => {
              const st = STATUS_STYLE[obra.status] ?? STATUS_STYLE.rascunho
              return (
                <div key={obra.id} style={{
                  display: 'flex', alignItems: 'center', gap: 14,
                  padding: '12px 10px',
                  background: 'var(--surface-2)',
                  borderRadius: 10,
                  border: '1px solid transparent',
                  transition: 'border-color .15s',
                  cursor: 'default',
                }}
                  onMouseEnter={e => e.currentTarget.style.borderColor = 'var(--border-2)'}
                  onMouseLeave={e => e.currentTarget.style.borderColor = 'transparent'}
                >
                  {/* Botão play */}
                  {obra.audio_path && (
                    <button
                      onClick={() => playObra({
                        id: obra.id,
                        nome: obra.nome,
                        audio_path: obra.audio_path,
                        titular_nome: perfil?.nome,
                      })}
                      style={{
                        width: 38, height: 38, borderRadius: 9,
                        background: 'linear-gradient(135deg, #BE123C, #09090B)',
                        color: '#fff', border: 'none', cursor: 'pointer',
                        fontSize: 12, flexShrink: 0, fontFamily: 'inherit',
                        boxShadow: '0 2px 12px rgba(225,29,72,.35)',
                        transition: 'transform .1s',
                      }}
                      onMouseEnter={e => e.currentTarget.style.transform = 'scale(1.08)'}
                      onMouseLeave={e => e.currentTarget.style.transform = 'scale(1)'}
                    >▶</button>
                  )}

                  {/* Info */}
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontWeight: 700, fontSize: 14, color: 'var(--text-primary)' }}>
                      {obra.nome}
                      {!obra.sou_titular && (
                        <span style={{ fontSize: 11, color: 'var(--text-muted)', marginLeft: 8, fontWeight: 400 }}>
                          (coautor)
                        </span>
                      )}
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>
                      {obra.genero || 'Sem gênero'} · {fmt(obra.preco_cents)}
                      {' · '}cadastrada em {new Date(obra.created_at).toLocaleDateString('pt-BR')}
                    </div>
                  </div>

                  {/* Status badge */}
                  <span style={{
                    fontSize: 11, fontWeight: 700,
                    padding: '4px 10px', borderRadius: 99,
                    background: st.bg, color: st.cor,
                    whiteSpace: 'nowrap', flexShrink: 0,
                  }}>
                    {st.label}
                  </span>
                </div>
              )
            })}

            {data.obras.length > 8 && (
              <button
                onClick={() => navigate('/obras')}
                style={{
                  margin: '4px 0 8px', padding: 12,
                  background: 'transparent',
                  border: '1px dashed var(--border-2)',
                  borderRadius: 10,
                  color: 'var(--brand)', fontSize: 13,
                  cursor: 'pointer', fontFamily: 'inherit',
                  transition: 'border-color .15s, background .15s',
                }}>
                Ver todas as {data.obras.length} obras
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

```

---

## 14. `frontend/src/pages/Descoberta.css`

*393 linhas · 16K*

```css
/* ============================================================
   Descoberta — light premium (branco · roxo)
   ============================================================ */

.dc-root {
  font-family: 'Inter', system-ui, sans-serif;
  background: var(--bg, #FFFFFF);
  color: var(--text-primary, #09090B);
  padding-bottom: 100px;
  min-height: 100vh;
}

/* ── TOPBAR ──────────────────────────────── */
.dc-topbar {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 16px 28px 14px;
  background: rgba(255,255,255,0.92);
  position: sticky;
  top: 0;
  z-index: 50;
  border-bottom: 1px solid var(--border);
  backdrop-filter: blur(12px);
}

/* Abas */
.dc-tabs { display: flex; gap: 8px; flex-shrink: 0; }
.dc-tab {
  display: flex; align-items: center; gap: 6px;
  padding: 8px 16px;
  border-radius: 99px;
  border: 1px solid var(--border);
  background: transparent;
  color: var(--text-secondary);
  font-size: 14px; font-weight: 500;
  cursor: pointer;
  transition: all .15s;
  font-family: inherit;
}
.dc-tab:hover { background: var(--surface-2); color: var(--brand); border-color: var(--brand-border); }
.dc-tab-active {
  background: var(--brand) !important;
  color: #fff !important;
  border-color: var(--brand) !important;
  font-weight: 700;
}
.dc-tab-icon { font-size: 14px; }

/* Busca */
.dc-search-wrap {
  flex: 1; max-width: 440px;
  position: relative;
  display: flex; align-items: center;
}
.dc-search-icon {
  position: absolute; left: 14px;
  font-size: 16px; color: var(--text-muted);
  pointer-events: none;
}
.dc-search {
  width: 100%;
  background: var(--surface);
  border: 1.5px solid var(--border);
  border-radius: 99px;
  padding: 10px 40px 10px 42px;
  color: var(--text-primary);
  font-size: 14px;
  outline: none;
  transition: border-color .15s, box-shadow .15s;
  font-family: inherit;
}
.dc-search::placeholder { color: var(--text-muted); }
.dc-search:focus {
  border-color: var(--brand);
  box-shadow: 0 0 0 3px rgba(225,29,72,.1);
}
.dc-search-clear {
  position: absolute; right: 12px;
  background: none; border: none;
  color: var(--text-muted);
  font-size: 18px; cursor: pointer; padding: 0; line-height: 1;
}
.dc-search-clear:hover { color: var(--text-primary); }

/* ── FILTRO DE GÊNEROS ───────────────────── */
.dc-generos {
  display: flex; gap: 8px;
  padding: 14px 28px 10px;
  flex-wrap: wrap;
}
.dc-genero-btn {
  padding: 6px 16px;
  border-radius: 99px;
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text-secondary);
  font-size: 13px; font-weight: 500;
  cursor: pointer; transition: all .15s;
  white-space: nowrap; font-family: inherit;
}
.dc-genero-btn:hover { background: var(--surface-2); color: var(--brand); border-color: var(--brand-border); }
.dc-genero-active {
  background: var(--brand) !important;
  border-color: var(--brand) !important;
  color: #fff !important;
  box-shadow: 0 4px 12px rgba(225,29,72,.25);
}

/* ── SEÇÕES ──────────────────────────────── */
.dc-section { padding: 20px 28px; }
.dc-section-title {
  font-size: 19px; font-weight: 800;
  margin-bottom: 18px;
  color: var(--text-primary);
  letter-spacing: -.3px;
}

/* ── GRID DE CARDS ───────────────────────── */
.dc-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(168px, 1fr));
  gap: 16px;
}

.dc-card {
  background: var(--surface);
  border-radius: 0;
  padding: 14px;
  cursor: pointer;
  transition: background .15s, transform .2s, border-color .15s, box-shadow .2s;
  border: 1.5px solid var(--border);
}
.dc-card:hover {
  background: var(--surface);
  transform: translateY(-3px);
  border-color: var(--brand-border);
  box-shadow: none;
}
.dc-card-active {
  border-color: var(--brand) !important;
  box-shadow: 0 8px 24px rgba(225,29,72,.15) !important;
}

.dc-card-cover {
  width: 100%; aspect-ratio: 1;
  border-radius: 0;
  display: flex; align-items: center; justify-content: center;
  margin-bottom: 12px;
  position: relative; overflow: hidden;
}
.dc-card-note { font-size: 32px; color: rgba(255,255,255,.7); }

.dc-card-play {
  position: absolute; bottom: 8px; right: 8px;
  width: 40px; height: 40px; border-radius: 50%;
  background: var(--brand);
  color: #fff; border: none; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  font-size: 14px;
  opacity: 0; transform: translateY(4px);
  transition: opacity .2s, transform .2s;
  box-shadow: none;
}
.dc-card:hover .dc-card-play,
.dc-card-play-active { opacity: 1 !important; transform: translateY(0) !important; }
.dc-card-play-active { background: #fff !important; color: var(--brand) !important; }

.dc-card-nome  { font-size: 14px; font-weight: 600; color: var(--text-primary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin-bottom: 3px; }
.dc-card-autor { font-size: 12px; color: var(--text-muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin-bottom: 6px; }
.dc-card-preco { font-size: 12px; font-weight: 700; color: var(--brand); }

/* ── RESULTADOS DE BUSCA ─────────────────── */
.dc-search-results { padding: 16px 28px; }

/* ── COMPOSITORES ────────────────────────── */
.dc-comp-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: 16px; margin-bottom: 24px;
}
.dc-comp-card {
  display: flex; flex-direction: column; align-items: center;
  gap: 8px; cursor: pointer; padding: 12px 8px;
  border-radius: 0; transition: background .15s; text-align: center;
}
.dc-comp-card:hover { background: var(--surface-2); }
.dc-comp-avatar {
  width: 72px; height: 72px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 24px; font-weight: 700; color: #fff;
  overflow: hidden; flex-shrink: 0;
}
.dc-comp-avatar img { width: 100%; height: 100%; object-fit: cover; }
.dc-comp-nome  { font-size: 13px; font-weight: 600; color: var(--text-primary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 110px; }
.dc-comp-nivel { font-size: 11px; color: var(--text-muted); text-transform: capitalize; }

/* ── PERFIL DO COMPOSITOR ────────────────── */
.dc-compositor-header {
  display: flex; align-items: center; gap: 16px;
  margin-bottom: 24px; padding: 20px;
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: 0;
}
.dc-compositor-avatar {
  width: 80px; height: 80px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 30px; font-weight: 700; color: #fff;
  overflow: hidden; flex-shrink: 0;
}
.dc-compositor-avatar img { width: 100%; height: 100%; object-fit: cover; }
.dc-compositor-nome { font-size: 22px; font-weight: 800; color: var(--text-primary); margin-bottom: 4px; }
.dc-back-btn {
  margin-left: auto;
  background: var(--surface); border: 1px solid var(--border);
  color: var(--text-secondary);
  padding: 8px 16px; border-radius: 0;
  font-size: 13px; cursor: pointer;
  transition: all .15s; font-family: inherit;
}
.dc-back-btn:hover { border-color: var(--brand); color: var(--brand); background: var(--brand-light); }

/* ── ESTADO VAZIO ────────────────────────── */
.dc-empty {
  display: flex; flex-direction: column; align-items: center;
  justify-content: center; padding: 72px 20px; text-align: center; gap: 12px;
}
.dc-empty-icon  { font-size: 48px; opacity: .25; }
.dc-empty-title { font-size: 18px; font-weight: 700; color: var(--text-primary); }
.dc-empty-btn {
  margin-top: 8px;
  background: var(--brand); color: #fff;
  border: none; padding: 10px 24px; border-radius: 0;
  font-size: 14px; font-weight: 700; cursor: pointer;
  transition: background .15s, box-shadow .15s; font-family: inherit;
  box-shadow: none;
}
.dc-empty-btn:hover { background: var(--brand-dark); }

/* ── SKELETON ────────────────────────────── */
.dc-skeleton {
  height: 220px; background: var(--surface-2);
  border-radius: 0;
  animation: dc-pulse 1.4s ease-in-out infinite;
}
@keyframes dc-pulse { 0%,100% { opacity: .5; } 50% { opacity: 1; } }

.dc-muted { color: var(--text-muted); font-size: 13px; }

/* ── MODAL FICHA TÉCNICA ─────────────────── */
.dc-modal-overlay {
  position: fixed; inset: 0;
  background: rgba(9,9,11,0.75);
  backdrop-filter: blur(6px);
  display: flex; align-items: center; justify-content: center;
  z-index: 600; padding: 24px;
  animation: dcFadeIn .15s ease;
}
@keyframes dcFadeIn { from{opacity:0} to{opacity:1} }

.dc-modal {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 0;
  width: 100%; max-width: 520px;
  max-height: 88vh;
  overflow-y: auto;
  position: relative;
  box-shadow: var(--shadow-lg);
  animation: dcSlideUp .2s ease;
}
@keyframes dcSlideUp {
  from { opacity:0; transform: scale(.96) translateY(8px); }
  to   { opacity:1; transform: scale(1) translateY(0); }
}

.dc-modal-close {
  position: absolute; top: 14px; right: 14px;
  width: 32px; height: 32px; border-radius: 50%;
  background: var(--surface-2); border: 1px solid var(--border);
  color: var(--text-secondary);
  font-size: 20px; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  z-index: 2; transition: all .15s;
}
.dc-modal-close:hover { background: var(--brand-light); color: var(--brand); border-color: var(--brand-border); }

.dc-modal-header {
  padding: 28px 24px;
  display: flex; align-items: center; gap: 18px;
  border-bottom: 1px solid var(--border);
}
.dc-modal-cover {
  width: 80px; height: 80px; border-radius: 0;
  background: var(--brand-light);
  display: flex; align-items: center; justify-content: center;
  font-size: 36px; color: var(--brand); flex-shrink: 0;
}
.dc-modal-genre { font-size: 11px; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 4px; }
.dc-modal-nome  { font-size: 26px; font-weight: 900; color: var(--text-primary); line-height: 1.1; margin-bottom: 6px; letter-spacing: -.5px; }
.dc-modal-autor { font-size: 13px; color: var(--text-secondary); }

.dc-modal-actions {
  padding: 16px 24px;
  display: flex; align-items: center; gap: 14px;
  border-bottom: 1px solid var(--border);
}
.dc-modal-play-btn {
  width: 52px; height: 52px; border-radius: 50%;
  background: var(--brand); color: #fff;
  border: none; cursor: pointer; font-size: 18px;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
  transition: background .15s, transform .1s, box-shadow .15s;
  box-shadow: none;
}
.dc-modal-play-btn:hover  { background: var(--brand-dark); }
.dc-modal-play-btn:active { transform: scale(.96); }
.dc-modal-action-label { color: var(--text-muted); font-size: 14px; }

.dc-modal-section { padding: 10px 24px 18px; }
.dc-modal-section-title {
  font-size: 11px; font-weight: 700;
  color: var(--text-muted); text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 12px;
}

.dc-modal-comp-list { display: flex; flex-direction: column; gap: 8px; }
.dc-modal-comp-row {
  display: flex; align-items: center; gap: 12px;
  padding: 10px 12px;
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: 0;
}
.dc-modal-comp-avatar {
  width: 36px; height: 36px; border-radius: 50%;
  background: linear-gradient(135deg, #BE123C, #E11D48);
  color: #fff; font-size: 14px; font-weight: 700;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0; overflow: hidden;
}
.dc-modal-comp-avatar img { width: 100%; height: 100%; object-fit: cover; }
.dc-modal-comp-info { flex: 1; min-width: 0; }
.dc-modal-comp-nome  { font-size: 14px; font-weight: 600; color: var(--text-primary); display: flex; align-items: center; gap: 6px; }
.dc-modal-comp-nivel { font-size: 11px; color: var(--text-muted); text-transform: capitalize; }
.dc-modal-comp-share { font-size: 13px; font-weight: 700; color: var(--brand); flex-shrink: 0; }
.dc-titular-badge {
  font-size: 9px; font-weight: 700;
  background: var(--brand); color: #fff;
  padding: 2px 7px; border-radius: 0;
  letter-spacing: .5px; text-transform: uppercase;
}

.dc-modal-buy-bar {
  margin: 8px 24px 24px; padding: 16px;
  background: var(--brand-light);
  border: 1px solid var(--brand-border);
  border-radius: 0;
  display: flex; align-items: center; justify-content: space-between; gap: 12px;
}
.dc-modal-buy-label { font-size: 11px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 1px; }
.dc-modal-buy-valor { font-size: 24px; font-weight: 900; color: var(--text-primary); margin-top: 2px; }
.dc-modal-buy-btn {
  background: var(--brand); color: #fff;
  border: none; cursor: pointer;
  padding: 12px 24px; border-radius: 0;
  font-size: 14px; font-weight: 700; white-space: nowrap;
  transition: background .15s, box-shadow .15s; font-family: inherit;
  box-shadow: none;
}
.dc-modal-buy-btn:hover { background: var(--brand-dark); }

/* ── RESPONSIVO ──────────────────────────── */
@media (max-width: 767px) {
  .dc-topbar { padding: 14px 16px 12px; padding-left: 70px; flex-direction: column; align-items: stretch; gap: 10px; }
  .dc-tabs   { justify-content: center; }
  .dc-search-wrap { max-width: 100%; }
  .dc-section     { padding: 16px; }
  .dc-generos     { padding: 12px 16px; gap: 6px; }
  .dc-genero-btn  { font-size: 12px; padding: 5px 12px; }
  .dc-grid { grid-template-columns: repeat(2, 1fr); gap: 10px; }
  .dc-card { padding: 10px; }
  .dc-comp-grid { grid-template-columns: repeat(3, 1fr); }
  .dc-comp-avatar { width: 60px; height: 60px; font-size: 20px; }
  .dc-modal-overlay { padding: 12px; }
  .dc-modal-header  { padding: 20px 16px; gap: 12px; }
  .dc-modal-cover   { width: 64px; height: 64px; font-size: 28px; }
  .dc-modal-nome    { font-size: 20px; }
  .dc-modal-section { padding: 8px 16px 12px; }
  .dc-modal-buy-bar { margin: 8px 16px 16px; padding: 14px; flex-direction: column; align-items: stretch; gap: 10px; }
  .dc-modal-buy-btn { width: 100%; text-align: center; }
}

```

---

## 15. `frontend/src/contexts/AuthContext.jsx`

*69 linhas · 4.0K*

```jsx
import React, { createContext, useContext, useEffect, useState } from 'react'
import { supabase } from '../lib/supabase'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user,    setUser]    = useState(undefined)
  const [perfil,  setPerfil]  = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (session?.user) { setUser(session.user); fetchPerfil(session.user.id) }
      else { setUser(null); setLoading(false) }
    })

    const { data: { subscription } } = supabase.auth.onAuthStateChange((event, session) => {
      if (event === 'SIGNED_IN' && session?.user) {
        setUser(session.user); fetchPerfil(session.user.id)
      } else if (event === 'SIGNED_OUT') {
        setUser(null); setPerfil(null); setLoading(false)
      }
    })
    return () => subscription.unsubscribe()
  }, [])

  async function fetchPerfil(userId) {
    try {
      const { data } = await supabase
        .from('perfis')
        .select('*, wallets(saldo_cents)')
        .eq('id', userId)
        .single()
      if (data) setPerfil(data)
    } catch (_) {}
    finally { setLoading(false) }
  }

  async function refreshPerfil() {
    if (user?.id) await fetchPerfil(user.id)
  }

  async function signInWithGoogle() {
    await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: { redirectTo: window.location.origin },
    })
  }

  async function signOut() {
    await supabase.auth.signOut()
    // Redireciona para a landing page
    if (typeof window !== 'undefined') {
      window.location.href = '/'
    }
  }

  if (loading && user === undefined) {
    return <div style={{ padding: 40, textAlign: 'center', color: '#71717A' }}>Carregando…</div>
  }

  return (
    <AuthContext.Provider value={{ user, perfil, loading, signInWithGoogle, signOut, refreshPerfil }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)

```

---

## 16. `frontend/src/lib/api.js`

*67 linhas · 4.0K*

```js
/**
 * Cliente HTTP para a API Flask — com trat. de 401 e hardening.
 */
import { supabase } from './supabase'

const BASE = import.meta.env.VITE_API_URL || import.meta.env.VITE_API_BASE_URL

async function getJwt() {
  const { data } = await supabase.auth.getSession()
  return data?.session?.access_token ?? null
}

async function request(method, path, { body, isFormData = false } = {}) {
  // Valida path: não pode conter quebras de linha nem caracteres bizarros
  if (typeof path !== 'string' || /[\r\n\t]/.test(path)) {
    throw new Error('Requisição inválida.')
  }

  const jwt = await getJwt()
  const headers = {}
  if (jwt) headers['Authorization'] = `Bearer ${jwt}`
  if (!isFormData && body !== undefined) headers['Content-Type'] = 'application/json'

  let res
  try {
    res = await fetch(`${BASE}${path}`, {
      method,
      headers,
      body: isFormData ? body : body !== undefined ? JSON.stringify(body) : undefined,
      credentials: 'omit', // Não enviamos cookies — usamos JWT apenas
    })
  } catch (e) {
    throw new Error('Servidor inacessível. Verifique se o backend está rodando.')
  }

  // Sessão expirada: força logout e redirect
  if (res.status === 401) {
    await supabase.auth.signOut().catch(() => {})
    if (typeof window !== 'undefined' && window.location.pathname !== '/login') {
      window.location.href = '/login?expirado=1'
    }
    throw new Error('Sessão expirada. Faça login novamente.')
  }

  // Rate limit
  if (res.status === 429) {
    throw new Error('Muitas tentativas em curto espaço de tempo. Aguarde e tente novamente.')
  }

  const text = await res.text()
  let json = {}
  try { json = text ? JSON.parse(text) : {} } catch {}

  if (!res.ok) {
    const msg = json.error || json.description || json.message || `Erro ${res.status}`
    throw new Error(msg)
  }
  return json
}

export const api = {
  get:    (path)       => request('GET',    path),
  post:   (path, body) => request('POST',   path, { body }),
  patch:  (path, body) => request('PATCH',  path, { body }),
  delete: (path)       => request('DELETE', path),
  upload: (path, form) => request('POST',   path, { body: form, isFormData: true }),
}

```

---

## 17. `frontend/public/sw.js`

*92 linhas · 4.0K*

```js
/**
 * Service Worker Pitch.me — Design 1 edition
 * CSS/JS/fonts usam networkFirst para sempre refletir updates do server.
 */

const VERSION       = 'pitchme-v3-design1-20260421'
const STATIC_CACHE  = `static-${VERSION}`
const IMG_CACHE     = `img-${VERSION}`
const RUNTIME_CACHE = `runtime-${VERSION}`

const PRECACHE_URLS = ['/', '/manifest.webmanifest']

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then(cache => cache.addAll(PRECACHE_URLS).catch(() => {}))
      .then(() => self.skipWaiting())
  )
})

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => !k.includes(VERSION)).map(k => caches.delete(k)))
    ).then(() => self.clients.claim())
  )
})

self.addEventListener('fetch', event => {
  const { request } = event
  const url = new URL(request.url)

  if (request.method !== 'GET') return
  if (url.pathname.startsWith('/api/')) return
  if (url.hostname.includes('supabase.co') || url.hostname.includes('stripe.com')) return

  // HTML / navigation — sempre network-first
  if (request.mode === 'navigate' || (request.headers.get('accept') || '').includes('text/html')) {
    event.respondWith(networkFirst(request, RUNTIME_CACHE))
    return
  }

  // Images — cache-first é ok (assets estáveis)
  if (request.destination === 'image') {
    event.respondWith(cacheFirst(request, IMG_CACHE))
    return
  }

  // CSS / JS / fontes — networkFirst para pegar updates do tema imediatamente
  if (['style', 'script', 'font'].includes(request.destination)) {
    event.respondWith(networkFirst(request, STATIC_CACHE))
    return
  }

  event.respondWith(networkFirst(request, RUNTIME_CACHE))
})

async function networkFirst(request, cacheName) {
  try {
    const res = await fetch(request)
    if (res && res.status === 200 && res.type === 'basic') {
      const cache = await caches.open(cacheName)
      cache.put(request, res.clone()).catch(() => {})
    }
    return res
  } catch {
    const cached = await caches.match(request)
    return cached || caches.match('/') || new Response('Offline', { status: 503 })
  }
}

async function cacheFirst(request, cacheName) {
  const cached = await caches.match(request)
  if (cached) return cached
  try {
    const res = await fetch(request)
    if (res && res.status === 200 && res.type === 'basic') {
      const cache = await caches.open(cacheName)
      cache.put(request, res.clone()).catch(() => {})
    }
    return res
  } catch {
    return new Response('', { status: 504 })
  }
}

self.addEventListener('message', event => {
  if (event.data?.type === 'SKIP_WAITING') self.skipWaiting()
  if (event.data?.type === 'CLEAR_CACHES') {
    event.waitUntil(caches.keys().then(keys => Promise.all(keys.map(k => caches.delete(k)))))
  }
})

```

---

## 18. `frontend/public/manifest.webmanifest`

*33 linhas · 4.0K*

```json
{
  "name": "Pitch.me — Composições Musicais",
  "short_name": "Pitch.me",
  "description": "Marketplace de composições musicais — conectando compositores e intérpretes.",
  "start_url": "/descoberta",
  "scope": "/",
  "display": "standalone",
  "orientation": "portrait-primary",
  "background_color": "#FFFFFF",
  "theme_color": "#E11D48",
  "lang": "pt-BR",
  "categories": ["music", "entertainment", "business"],
  "icons": [
    {
      "src": "/icons/icon-192.png",
      "sizes": "192x192",
      "type": "image/png",
      "purpose": "any"
    },
    {
      "src": "/icons/icon-512.png",
      "sizes": "512x512",
      "type": "image/png",
      "purpose": "any"
    },
    {
      "src": "/icons/icon-maskable-512.png",
      "sizes": "512x512",
      "type": "image/png",
      "purpose": "maskable"
    }
  ]
}

```

---

## 19. `backend/routes/catalogo.py`

*266 linhas · 12K*

```python
"""
Routes: /api/catalogo  /api/comentarios  /api/ofertas
"""
from flask import Blueprint, request, jsonify, g, abort
from middleware.auth import require_auth, require_role
from db.supabase_client import get_supabase
from utils.sanitizer import sanitize_text

catalogo_bp = Blueprint("catalogo", __name__)

# ──────────────────────────────────────────────
# ESTATÍSTICAS PÚBLICAS (para Landing)
# ──────────────────────────────────────────────

@catalogo_bp.route("/stats/public", methods=["GET"])
def stats_publicas():
    """Retorna estatísticas agregadas da plataforma para exibir na Landing.
    Público — não requer autenticação."""
    import logging
    log = logging.getLogger(__name__)
    sb = get_supabase()

    try:
        obras_resp = sb.table("catalogo_publico").select("id", count="exact").execute()
        total_obras = obras_resp.count if obras_resp.count is not None else len(obras_resp.data or [])
    except Exception as e:
        log.warning("stats_publicas: erro contando obras: %s", e)
        total_obras = 0

    try:
        comp_resp = (
            sb.table("perfis")
            .select("id", count="exact")
            .eq("role", "compositor")
            .execute()
        )
        total_compositores = comp_resp.count if comp_resp.count is not None else len(comp_resp.data or [])
    except Exception as e:
        log.warning("stats_publicas: erro contando compositores: %s", e)
        total_compositores = 0

    try:
        trans_resp = (
            sb.table("transacoes")
            .select("valor_cents")
            .eq("status", "confirmada")
            .execute()
        )
        total_pago_cents = sum(int(t.get("valor_cents") or 0) for t in (trans_resp.data or []))
        total_pago = total_pago_cents / 100.0
    except Exception as e:
        log.warning("stats_publicas: erro somando transações: %s", e)
        total_pago = 0.0

    return jsonify({
        "obras": total_obras,
        "compositores": total_compositores,
        "total_pago": total_pago,
    }), 200


# ──────────────────────────────────────────────
# CATÁLOGO PÚBLICO
# ──────────────────────────────────────────────

@catalogo_bp.route("/", methods=["GET"])
def listar_catalogo():
    genero   = request.args.get("genero")
    busca    = request.args.get("q", "").strip()
    page     = max(1, int(request.args.get("page", 1)))
    per_page = min(50, int(request.args.get("per_page", 20)))
    offset   = (page - 1) * per_page

    sb = get_supabase()
    query = (
        sb.table("catalogo_publico")
        .select("*")
        .order("created_at", desc=True)
        .range(offset, offset + per_page - 1)
    )
    if genero:
        query = query.eq("genero", genero)
    if busca:
        query = query.ilike("nome", f"%{busca}%")

    resp = query.execute()
    return jsonify(resp.data or []), 200


@catalogo_bp.route("/<obra_id>", methods=["GET"])
def detalhe_obra(obra_id):
    sb = get_supabase()
    try:
        resp = (
            sb.table("catalogo_publico")
            .select("*")
            .eq("id", obra_id)
            .maybe_single()
            .execute()
        )
    except Exception:
        abort(404, description="Obra não encontrada.")
    if not resp or not resp.data:
        abort(404, description="Obra não encontrada.")
    return jsonify(resp.data), 200


# ──────────────────────────────────────────────
# COMENTÁRIOS
# ──────────────────────────────────────────────

@catalogo_bp.route("/<obra_id>/comentarios", methods=["GET"])
def listar_comentarios(obra_id):
    sb = get_supabase()
    resp = (
        sb.table("comentarios")
        .select("*, perfis(nome, avatar_url, nivel)")
        .eq("obra_id", obra_id)
        .order("created_at", desc=True)
        .execute()
    )
    return jsonify(resp.data or []), 200


@catalogo_bp.route("/<obra_id>/comentarios", methods=["POST"])
@require_auth
def criar_comentario(obra_id):
    data = request.get_json(force=True, silent=True) or {}
    conteudo_raw = data.get("conteudo", "")

    try:
        conteudo = sanitize_text(conteudo_raw, max_length=1000)
    except ValueError as e:
        abort(422, description=str(e))

    if not conteudo:
        abort(422, description="Comentário não pode estar vazio.")

    sb = get_supabase()
    resp = (
        sb.table("comentarios")
        .insert({"obra_id": obra_id, "perfil_id": g.user.id, "conteudo": conteudo})
        .execute()
    )
    return jsonify(resp.data[0]), 201


@catalogo_bp.route("/comentarios/<comentario_id>", methods=["DELETE"])
@require_auth
def deletar_comentario(comentario_id):
    sb = get_supabase()
    # RLS garante que só o autor pode deletar
    sb.table("comentarios").delete().eq("id", comentario_id).eq("perfil_id", g.user.id).execute()
    return jsonify({"ok": True}), 200


# ──────────────────────────────────────────────
# OFERTAS / CONTRAPROPOSTAS
# ──────────────────────────────────────────────

@catalogo_bp.route("/<obra_id>/ofertas", methods=["POST"])
@require_auth
@require_role("interprete")
def criar_oferta(obra_id):
    data = request.get_json(force=True, silent=True) or {}

    try:
        valor_cents = int(data.get("valor_cents", 0))
        if valor_cents < 100:
            raise ValueError()
    except (ValueError, TypeError):
        abort(422, description="'valor_cents' deve ser inteiro >= 100.")

    mensagem = None
    if data.get("mensagem"):
        try:
            mensagem = sanitize_text(data["mensagem"], max_length=500)
        except ValueError as e:
            abort(422, description=str(e))

    sb = get_supabase()

    # Verifica que a obra existe e está publicada
    obra = sb.table("obras").select("id").eq("id", obra_id).eq("status", "publicada").execute()
    if not obra.data:
        abort(404, description="Obra não encontrada ou não publicada.")

    # Verifica se já existe oferta pendente do mesmo intérprete
    existente = (
        sb.table("ofertas")
        .select("id")
        .eq("obra_id", obra_id)
        .eq("interprete_id", g.user.id)
        .eq("status", "pendente")
        .execute()
    )
    if existente.data:
        abort(409, description="Você já possui uma oferta pendente para esta obra.")

    resp = sb.table("ofertas").insert({
        "obra_id":       obra_id,
        "interprete_id": g.user.id,
        "valor_cents":   valor_cents,
        "mensagem":      mensagem,
        "status":        "pendente",
    }).execute()

    return jsonify(resp.data[0]), 201


@catalogo_bp.route("/ofertas/<oferta_id>/responder", methods=["PATCH"])
@require_auth
@require_role("compositor")
def responder_oferta(oferta_id):
    data = request.get_json(force=True, silent=True) or {}
    novo_status = data.get("status")

    if novo_status not in ("aceita", "recusada"):
        abort(422, description="'status' deve ser 'aceita' ou 'recusada'.")

    sb = get_supabase()
    # RLS garante que só o titular da obra pode atualizar
    resp = (
        sb.table("ofertas")
        .update({"status": novo_status, "responded_at": "now()"})
        .eq("id", oferta_id)
        .eq("status", "pendente")
        .execute()
    )
    if not resp.data:
        abort(404, description="Oferta não encontrada ou já respondida.")
    return jsonify(resp.data[0]), 200


@catalogo_bp.route("/ofertas/recebidas", methods=["GET"])
@require_auth
@require_role("compositor")
def ofertas_recebidas():
    """Ofertas recebidas em obras do compositor autenticado."""
    sb = get_supabase()
    resp = (
        sb.table("ofertas")
        .select("*, obras(nome), perfis!interprete_id(nome, avatar_url)")
        .in_("obra_id",
             [r["id"] for r in
              sb.table("obras").select("id").eq("titular_id", g.user.id).execute().data or []]
             )
        .order("created_at", desc=True)
        .execute()
    )
    return jsonify(resp.data or []), 200


@catalogo_bp.route("/ofertas/enviadas", methods=["GET"])
@require_auth
@require_role("interprete")
def ofertas_enviadas():
    sb = get_supabase()
    resp = (
        sb.table("ofertas")
        .select("*, obras(nome, preco_cents)")
        .eq("interprete_id", g.user.id)
        .order("created_at", desc=True)
        .execute()
    )
    return jsonify(resp.data or []), 200

```

---

## 20. `backend/app.py`

*160 linhas · 12K*

```python
"""
Pitch.me — API Flask com hardening completo de segurança.

CORREÇÕES DE VULNERABILIDADES IMPLEMENTADAS:
- #5 (ALTA): CSRF Protection via Flask-WTF
- #8 (ALTA): Secure session configuration  
- #11 (MÉDIA): Content Security Policy headers
- #13 (MÉDIA): Rate limiting otimizado
- #19 (BAIXA): SameSite cookie configuration
"""
import os
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect
from dotenv import load_dotenv

load_dotenv()

# Rate limiter - tenta Redis primeiro, fallback pra memória
REDIS_URL = os.getenv("REDIS_URL", "memory://")
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["600 per minute", "10000 per hour"],
    storage_uri=REDIS_URL,
)

# CSRF Protection (vulnerabilidade #5)
csrf = CSRFProtect()


def create_app() -> Flask:
    app = Flask(__name__)
    
    # ═══════════════════════════════════════════════════════════
    # SESSION CONFIGURATION (Vulnerabilidade #8 - ALTA)
    # ═══════════════════════════════════════════════════════════
    app.secret_key = os.environ["FLASK_SECRET_KEY"]
    app.config.update(
        SESSION_COOKIE_SECURE=request.is_secure if request else True,  # HTTPS only em prod
        SESSION_COOKIE_HTTPONLY=True,  # Bloqueia acesso via JavaScript
        SESSION_COOKIE_SAMESITE='Lax',  # Proteção CSRF adicional (vuln #19)
        PERMANENT_SESSION_LIFETIME=3600,  # 1 hora
        SESSION_COOKIE_NAME='pitchme_session',
    )

    # ═══════════════════════════════════════════════════════════
    # CORS CONFIGURATION
    # ═══════════════════════════════════════════════════════════
    allowed = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")
    allowed = [o.strip() for o in allowed if o.strip()]
    CORS(
        app,
        resources={r"/api/*": {"origins": allowed}},
        supports_credentials=True,  # Permite cookies
        max_age=3600,
    )

    # ═══════════════════════════════════════════════════════════
    # SECURITY CONFIGURATIONS
    # ═══════════════════════════════════════════════════════════
    app.config["MAX_CONTENT_LENGTH"] = 11 * 1024 * 1024  # 10MB + margem
    
    # CSRF Protection (vulnerabilidade #5 - ALTA)
    # Exempta rotas de webhook que usam validação externa
    csrf.init_app(app)
    app.config['WTF_CSRF_CHECK_DEFAULT'] = False  # Controle manual por rota
    
    # Rate Limiter (vulnerabilidade #13 - MÉDIA otimizada)
    limiter.init_app(app)

    # ═══════════════════════════════════════════════════════════
    # SECURITY HEADERS (Vulnerabilidades #7, #11)
    # ═══════════════════════════════════════════════════════════
    @app.after_request
    def add_security_headers(response):
        # Básicos
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        # HSTS (HTTPS only)
        if request.is_secure:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        
        # ─────────────────────────────────────────────────────────
        # CSP (Content Security Policy) - Vulnerabilidade #11 (MÉDIA)
        # ─────────────────────────────────────────────────────────
        csp_directives = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://js.stripe.com",  # Stripe precisa
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
            "font-src 'self' https://fonts.gstatic.com",
            "img-src 'self' data: https: blob:",
            "media-src 'self' blob: https://*.supabase.co",  # Storage Supabase
            "connect-src 'self' https://*.supabase.co https://api.stripe.com",
            "frame-src 'self' https://js.stripe.com",
            "object-src 'none'",
            "base-uri 'self'",
            "form-action 'self'",
            "frame-ancestors 'none'",
        ]
        response.headers["Content-Security-Policy"] = "; ".join(csp_directives)
        
        return response

    # ═══════════════════════════════════════════════════════════
    # BLUEPRINTS
    # ═══════════════════════════════════════════════════════════
    # Imports absolutos para compatibilidade com gunicorn
    import routes.obras as obras_module
    import routes.transacoes as transacoes_module
    import routes.perfis as perfis_module
    import routes.catalogo as catalogo_module
    import routes.admin as admin_module
    import routes.stripe_routes as stripe_module
    import routes.paypal_routes as paypal_module
    import routes.contato as contato_module
    import routes.download as download_module
    
    obras_bp = obras_module.obras_bp
    transacoes_bp = transacoes_module.transacoes_bp
    perfis_bp = perfis_module.perfis_bp
    catalogo_bp = catalogo_module.catalogo_bp
    admin_bp = admin_module.admin_bp
    stripe_bp = stripe_module.stripe_bp
    paypal_bp = paypal_module.paypal_bp
    contato_bp = contato_module.contato_bp
    download_bp = download_module.download_bp

    app.register_blueprint(obras_bp, url_prefix="/api/obras")
    app.register_blueprint(transacoes_bp, url_prefix="/api/transacoes")
    app.register_blueprint(perfis_bp, url_prefix="/api/perfis")
    app.register_blueprint(catalogo_bp, url_prefix="/api/catalogo")
    app.register_blueprint(admin_bp, url_prefix="/api/admin")
    app.register_blueprint(stripe_bp, url_prefix="/api/stripe")
    app.register_blueprint(paypal_bp, url_prefix="/api/paypal")
    app.register_blueprint(contato_bp, url_prefix="/api/contato")
    app.register_blueprint(download_bp, url_prefix="/api")

    # ═══════════════════════════════════════════════════════════
    # ERROR HANDLERS (Vulnerabilidade #7 - logs seguros)
    # ═══════════════════════════════════════════════════════════
    import utils.errors as errors_module
    errors_module.register_error_handlers(app)

    @app.errorhandler(429)
    def ratelimit_handler(e):
        return jsonify({"error": "Muitas requisições. Aguarde um momento."}), 429

    # ═══════════════════════════════════════════════════════════
    # HEALTH CHECK
    # ═══════════════════════════════════════════════════════════
    @app.route("/api/health", methods=["GET"])
    def health():
        return jsonify({"status": "healthy", "version": "2.0-secure"}), 200

    return app

```

---

_Documento gerado automaticamente a partir do código-fonte em /app_
