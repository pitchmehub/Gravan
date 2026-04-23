import React, { useState, useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom'
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
import MeusContratos from './pages/MeusContratos'
import ContratoLicenciamentoDetalhe from './pages/ContratoLicenciamentoDetalhe'
import Biblioteca    from './pages/Biblioteca'
import Analytics     from './pages/Analytics'
import Planos        from './pages/Planos'
import AssinaturaSucesso from './pages/AssinaturaSucesso'
import Comprar       from './pages/Comprar'
import Compras       from './pages/Compras'
import Saques        from './pages/Saques'
import ConnectOnboarding from './pages/ConnectOnboarding'
import Ofertas       from './pages/Ofertas'
import Admin         from './pages/Admin'
import AdminLanding  from './pages/AdminLanding'
import AdminVerComo  from './pages/AdminVerComo'
import CadastroEditora    from './pages/CadastroEditora'
import PublisherDashboard from './pages/PublisherDashboard'
import Agregados          from './pages/Agregados'
import EscolherTipoPerfil  from './pages/EscolherTipoPerfil'
import PerfilPublico       from './pages/PerfilPublico'
import AdminEditoras       from './pages/AdminEditoras'
import AdminEditoraDetalhe    from './pages/AdminEditoraDetalhe'
import AdminSaques            from './pages/AdminSaques'
import AdminSaquesHistorico   from './pages/AdminSaquesHistorico'
import Termos           from './pages/legal/Termos'
import Privacidade      from './pages/legal/Privacidade'
import DireitosAutorais from './pages/legal/DireitosAutorais'
import EditarPerfil  from './pages/EditarPerfil'
import CompletarCadastro from './pages/CompletarCadastro'
import Dossies                from './pages/Dossies'
import CancelarSaque          from './pages/CancelarSaque'
import PagamentoSucesso   from './pages/PagamentoSucesso'
import PagamentoCancelado from './pages/PagamentoCancelado'
import AceitarOferta      from './pages/AceitarOferta'
import './styles/global.css'
import './components/GlobalPlayer.css'


function GlobalRedirect() {
  const { user, perfil, loading } = useAuth()
  const location = useLocation()

  if (!loading && user && perfil && !perfil.role && location.pathname !== '/perfil/tipo') {
    return <Navigate to="/perfil/tipo" replace />
  }
  return null
}

function PrivateRoute({ children, roles }) {
  const { user, perfil, loading } = useAuth()
  const path = typeof window !== 'undefined' ? window.location.pathname : ''
  const skipCadastro = (() => {
    try { return typeof window !== 'undefined' && localStorage.getItem('pitchme_skip_cadastro') === '1' }
    catch { return false }
  })()

  if (loading) return <div style={{ padding: 40, color: '#71717A', fontFamily: 'IBM Plex Sans, system-ui, sans-serif' }}>Carregando…</div>
  if (!user)   return <Navigate to="/login" replace />

  if (perfil && !perfil.role && path !== '/perfil/tipo') {
    return <Navigate to="/perfil/tipo" replace />
  }
  if (perfil && perfil.role === 'compositor' && !perfil.cadastro_completo && !skipCadastro
      && path !== '/perfil/completar' && path !== '/perfil/tipo') {
    return <Navigate to="/perfil/completar" replace />
  }
  if (perfil && perfil.role === 'publisher' && !perfil.razao_social && !skipCadastro
      && path !== '/editora/cadastro' && path !== '/perfil/tipo') {
    return <Navigate to="/editora/cadastro" replace />
  }

  if (roles && perfil && perfil.role !== 'administrador' && !roles.includes(perfil.role)) {
    return <Navigate to="/descoberta" replace />
  }
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
      <Route path="/contratos"     element={<PrivateRoute roles={['compositor','administrador']}><AppShell><MeusContratos /></AppShell></PrivateRoute>} />
      <Route path="/contratos/licenciamento/:id" element={<PrivateRoute><AppShell><ContratoLicenciamentoDetalhe /></AppShell></PrivateRoute>} />
      <Route path="/biblioteca"    element={<PrivateRoute><AppShell><Biblioteca /></AppShell></PrivateRoute>} />
      <Route path="/analytics"     element={<PrivateRoute roles={['compositor','administrador']}><AppShell><Analytics /></AppShell></PrivateRoute>} />
      <Route path="/planos"        element={<PrivateRoute><AppShell><Planos /></AppShell></PrivateRoute>} />
      <Route path="/assinatura/sucesso" element={<PrivateRoute><AppShell><AssinaturaSucesso /></AppShell></PrivateRoute>} />
      <Route path="/saques/cancelar" element={<CancelarSaque />} />
              <Route path="/saques"        element={<PrivateRoute roles={['compositor','administrador']}><AppShell><Saques /></AppShell></PrivateRoute>} />
      <Route path="/connect"           element={<PrivateRoute><AppShell><ConnectOnboarding /></AppShell></PrivateRoute>} />
      <Route path="/connect/sucesso"   element={<PrivateRoute><AppShell><ConnectOnboarding /></AppShell></PrivateRoute>} />
      <Route path="/connect/refresh"   element={<PrivateRoute><AppShell><ConnectOnboarding /></AppShell></PrivateRoute>} />
      <Route path="/compras"       element={<PrivateRoute><AppShell><Compras /></AppShell></PrivateRoute>} />
      <Route path="/comprar/:obraId"      element={<PrivateRoute><AppShell><Comprar /></AppShell></PrivateRoute>} />
      <Route path="/pagamento/sucesso"    element={<PrivateRoute><AppShell><PagamentoSucesso /></AppShell></PrivateRoute>} />
      <Route path="/pagamento/cancelado"  element={<PrivateRoute><AppShell><PagamentoCancelado /></AppShell></PrivateRoute>} />
      <Route path="/ofertas"       element={<PrivateRoute><AppShell><Ofertas /></AppShell></PrivateRoute>} />
      <Route path="/perfil/editar" element={<PrivateRoute><AppShell><EditarPerfil /></AppShell></PrivateRoute>} />
      <Route path="/perfil/completar" element={<PrivateRoute><AppShell><CompletarCadastro /></AppShell></PrivateRoute>} />
      <Route path="/perfil/tipo"      element={<PrivateRoute><AppShell><EscolherTipoPerfil /></AppShell></PrivateRoute>} />
      <Route path="/perfil/:perfilId" element={<PrivateRoute><AppShell><PerfilPublico /></AppShell></PrivateRoute>} />
      <Route path="/admin"         element={<PrivateRoute roles={['administrador']}><AppShell><Admin /></AppShell></PrivateRoute>} />
      <Route path="/admin/landing" element={<PrivateRoute roles={['administrador']}><AppShell><AdminLanding /></AppShell></PrivateRoute>} />
      <Route path="/admin/perfil/:perfilId" element={<PrivateRoute roles={['administrador']}><AppShell><AdminVerComo /></AppShell></PrivateRoute>} />
      <Route path="/admin/editoras"               element={<PrivateRoute roles={['administrador']}><AppShell><AdminEditoras /></AppShell></PrivateRoute>} />
      <Route path="/admin/editoras/:publisherId"  element={<PrivateRoute roles={['administrador']}><AppShell><AdminEditoraDetalhe /></AppShell></PrivateRoute>} />
        <Route path="/admin/saques"              element={<PrivateRoute roles={['administrador']}><AppShell><AdminSaques /></AppShell></PrivateRoute>} />
        <Route path="/admin/saques/historico"    element={<PrivateRoute roles={['administrador']}><AppShell><AdminSaquesHistorico /></AppShell></PrivateRoute>} />

      {/* Dossiês — somente administrador */}
      <Route path="/dossies" element={<PrivateRoute roles={['administrador']}><AppShell><Dossies /></AppShell></PrivateRoute>} />

      {/* Editora */}
      <Route path="/editora/cadastro"  element={<PrivateRoute><AppShell><CadastroEditora /></AppShell></PrivateRoute>} />
      <Route path="/editora/dashboard" element={<PrivateRoute roles={['publisher','administrador']}><AppShell><PublisherDashboard /></AppShell></PrivateRoute>} />
      <Route path="/editora/aceitar-oferta/:token" element={<AceitarOferta />} />
      <Route path="/agregados"         element={<PrivateRoute roles={['publisher','administrador']}><AppShell><Agregados /></AppShell></PrivateRoute>} />

      {/* Páginas legais (públicas) */}
      <Route path="/termos"            element={<Termos />} />
      <Route path="/privacidade"       element={<Privacidade />} />
      <Route path="/direitos-autorais" element={<DireitosAutorais />} />

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
