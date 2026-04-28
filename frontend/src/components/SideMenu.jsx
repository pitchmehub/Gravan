import React, { useState, useEffect, useRef } from 'react'
import { NavLink, useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import GravanLogo from './GravanLogo'
import {
  IconCompass, IconGrid, IconMusic, IconPlus, IconChart, IconDocument,
  IconWallet, IconTag, IconStar, IconBag, IconShield, IconEdit,
  IconFolder, IconBuilding, IconLayers, IconUser, IconLogout,
  IconChevronUp, IconChevronDown, IconMore, IconBell,
} from './Icons'
import './SideMenu.css'

const NAV_ITEMS = {
 compositor: [
 { to: '/descoberta', Icon: IconCompass, label: 'Descoberta' },
 { to: '/dashboard', Icon: IconGrid, label: 'Dashboard' },
 { to: '/obras', Icon: IconMusic, label: 'Minhas obras' },
 { to: '/obras/nova', Icon: IconPlus, label: 'Nova obra' },
 { to: '/analytics', Icon: IconChart, label: 'Analytics', pro: true },
 { to: '/contratos', Icon: IconDocument, label: 'Meus contratos' },
 { to: '/vendas', Icon: IconBag, label: 'Vendas' },
 { to: '/saques', Icon: IconWallet, label: 'Saques' },
 { to: '/ofertas', Icon: IconTag, label: 'Ofertas' },
 { to: '/notificacoes', Icon: IconBell, label: 'Notificações' },
 { to: '/planos', Icon: IconStar, label: 'Planos' },
 ],
 interprete: [
 { to: '/descoberta', Icon: IconCompass, label: 'Descoberta' },
 { to: '/compras', Icon: IconBag, label: 'Compras' },
 { to: '/ofertas', Icon: IconTag, label: 'Ofertas' },
 { to: '/notificacoes', Icon: IconBell, label: 'Notificações' },
 { to: '/planos', Icon: IconStar, label: 'Planos' },
 ],
 // ADMINISTRADOR: tudo sobre a plataforma fica concentrado em "Painel admin".
 administrador: [
 { to: '/admin', Icon: IconShield, label: 'Painel admin', highlight: true },
 { to: '/admin/landing', Icon: IconEdit, label: 'Editar Landing' },
 { to: '/descoberta', Icon: IconCompass, label: 'Descoberta' },
 { to: '/obras', Icon: IconMusic, label: 'Obras' },
 { to: '/obras/nova', Icon: IconPlus, label: 'Nova obra' },
 { to: '/contratos', Icon: IconDocument, label: 'Contratos' },
 { to: '/dossies', Icon: IconFolder, label: 'Dossiês' },
 { to: '/saques', Icon: IconWallet, label: 'Saques' },
 { to: '/admin/editoras', Icon: IconBuilding, label: 'Editoras' },
 { to: '/notificacoes', Icon: IconBell, label: 'Notificações' },
 { to: '/planos', Icon: IconStar, label: 'Planos' },
 ],
 publisher: [
 { to: '/editora/dashboard', Icon: IconGrid, label: 'Dashboard' },
 { to: '/agregados', Icon: IconLayers, label: 'Agregados' },
 { to: '/obras/nova', Icon: IconPlus, label: 'Nova obra' },
 { to: '/obras', Icon: IconMusic, label: 'Obras' },
 { to: '/contratos', Icon: IconDocument, label: 'Contratos' },
 { to: '/ofertas', Icon: IconTag, label: 'Ofertas' },
 { to: '/vendas', Icon: IconBag, label: 'Vendas' },
 { to: '/saques', Icon: IconWallet, label: 'Saques' },
 { to: '/notificacoes', Icon: IconBell, label: 'Notificações' },
 { to: '/descoberta', Icon: IconCompass, label: 'Descoberta' },
 ],
 artist: [
 { to: '/dashboard', Icon: IconGrid, label: 'Dashboard' },
 { to: '/contratos', Icon: IconDocument, label: 'Meus contratos' },
 { to: '/notificacoes', Icon: IconBell, label: 'Notificações' },
 { to: '/descoberta', Icon: IconCompass, label: 'Descoberta' },
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
 const [imgErro, setImgErro] = useState(false)
 const ref = useRef(null)
 const navigate = useNavigate()
 const { signOut, user } = useAuth()

 useEffect(() => {
 function handle(e) { if (ref.current && !ref.current.contains(e.target)) setOpen(false) }
 document.addEventListener('mousedown', handle)
 return () => document.removeEventListener('mousedown', handle)
 }, [])

 if (!perfil) return null
 const iniciais = perfil.nome?.split(' ').slice(0,2).map(n=>n[0]).join('').toUpperCase() ?? '?'
 const isPro = perfil.plano === 'PRO' && perfil.status_assinatura && perfil.status_assinatura !== 'inativa'
 // Fontes de foto: perfil cadastrado → metadados OAuth (Google etc.)
 const fotoUrl = perfil.avatar_url
   || user?.user_metadata?.avatar_url
   || user?.user_metadata?.picture
   || null

 return (
 <div ref={ref} style={{ position: 'relative' }}>
 <div className="sidebar-user-btn" onClick={() => setOpen(o => !o)}>
 <div className="sidebar-avatar">
 {fotoUrl && !imgErro
   ? <img src={fotoUrl} alt={perfil.nome} referrerPolicy="no-referrer" onError={() => setImgErro(true)} />
   : iniciais}
 </div>
 {!collapsed && (
 <>
 <div className="sidebar-user-info">
 <span className="sidebar-user-nome" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
 {perfil.nome_artistico || perfil.nome}
 {isPro && (
 <span data-testid="badge-pro" style={{
 background: 'var(--brand)', color: '#fff',
 fontSize: 9, fontWeight: 700, letterSpacing: 0.8,
 padding: '1px 5px', borderRadius: 3,
 }}>PRO</span>
 )}
 </span>
 <span className="sidebar-user-role">{perfil.role}</span>
 </div>
 <span style={{ display: 'inline-flex', color: 'var(--text-muted)', marginLeft: 'auto' }}>
   {open ? <IconChevronUp size={12} /> : <IconChevronDown size={12} />}
 </span>
 </>
 )}
 </div>
 {open && (
 <div className="sidebar-user-dropdown">
 <button className="sidebar-user-item" onClick={() => { setOpen(false); navigate('/perfil/editar') }}>
 <span style={{ display: 'inline-flex' }}><IconUser size={16} /></span> Editar informações
 </button>
 <button className="sidebar-user-item" onClick={() => { setOpen(false); navigate('/planos') }}>
 <span style={{ display: 'inline-flex' }}><IconStar size={16} /></span> {isPro ? 'Gerenciar assinatura' : 'Assinar PRO'}
 </button>
 <div className="sidebar-user-divider" />
 <button className="sidebar-user-item sidebar-user-item-danger" onClick={() => { setOpen(false); signOut() }}>
 <span style={{ display: 'inline-flex' }}><IconLogout size={16} /></span> Sair da conta
 </button>
 </div>
 )}
 </div>
 )
}

function AdminBadge({ collapsed }) {
 const navigate = useNavigate()
 if (collapsed) {
 return (
 <button
 onClick={() => navigate('/admin')}
 title="MODO ADMINISTRADOR"
 data-testid="modo-admin-btn"
 style={{
 width: '100%', padding: '8px 0', margin: '8px 0',
 background: 'linear-gradient(135deg,#7C3AED,#0C447C)',
 color: '#fff', fontSize: 11, fontWeight: 800, letterSpacing: 0.4,
 border: 'none', borderRadius: 6, cursor: 'pointer',
 }}>
 ADM
 </button>
 )
 }
 return (
 <button
 onClick={() => navigate('/admin')}
 data-testid="modo-admin-btn"
 style={{
 width: '100%', padding: '10px 12px', margin: '8px 0 12px',
 background: 'linear-gradient(135deg,#7C3AED,#0C447C)',
 color: '#fff', fontSize: 11.5, fontWeight: 800, letterSpacing: 0.6,
 border: 'none', borderRadius: 8, cursor: 'pointer',
 display: 'flex', alignItems: 'center', gap: 8, justifyContent: 'center',
 boxShadow: '0 4px 14px rgba(124,58,237,.25)',
 }}>
 <span style={{ display: 'inline-flex' }}><IconShield size={14} /></span>
 MODO ADMINISTRADOR
 </button>
 )
}

export default function SideMenu({ onCollapse }) {
 const isMobile = useIsMobile()
 const [collapsed, setCollapsed] = useState(false)
 const [mobileOpen, setMobileOpen] = useState(false)
 const { perfil } = useAuth()
 const navigate = useNavigate()
 const location = useLocation()
 const drawerRef = useRef(null)
 const dragStateRef = useRef(null)
 const [dragOffset, setDragOffset] = useState(0)

 useEffect(() => { onCollapse?.(isMobile ? true : collapsed) }, [collapsed, isMobile])
 useEffect(() => { setMobileOpen(false) }, [location.pathname])
 useEffect(() => { if (!mobileOpen) setDragOffset(0) }, [mobileOpen])

 function handleDrawerTouchStart(e) {
 const t = e.touches[0]
 dragStateRef.current = { startX: t.clientX, startY: t.clientY, dragging: false }
 }
 function handleDrawerTouchMove(e) {
 const s = dragStateRef.current
 if (!s) return
 const t = e.touches[0]
 const dx = t.clientX - s.startX
 const dy = t.clientY - s.startY
 if (!s.dragging) {
 if (Math.abs(dx) > 8 && Math.abs(dx) > Math.abs(dy)) s.dragging = true
 else return
 }
 if (dx < 0) setDragOffset(dx)
 }
 function handleDrawerTouchEnd() {
 const s = dragStateRef.current
 dragStateRef.current = null
 if (!s) return
 const width = drawerRef.current?.offsetWidth || 280
 if (dragOffset < -Math.min(80, width * 0.25)) {
 setMobileOpen(false)
 } else {
 setDragOffset(0)
 }
 }

 const role = perfil?.role ?? 'compositor'
 const allItems = NAV_ITEMS[role] ?? NAV_ITEMS.compositor
 // "Nova obra" foi removida do menu — o atalho fica dentro da tela "Minhas obras".
 const items = allItems.filter(i => i.to !== '/obras/nova')
 const isAdmin = role === 'administrador'

 // ── MOBILE: barra de navegação inferior ──────────────────────
 if (isMobile) {
 // Descoberta sempre fica como botão central destacado.
 const descoberta = items.find(i => i.to === '/descoberta')
 ?? { to: '/descoberta', Icon: IconCompass, label: 'Descoberta' }
 // Drawer "Mais": esconde Descoberta (já é o botão central) e Nova obra
 // (criada pela tela "Minhas obras", não precisa de atalho).
 const drawerItems = items.filter(i =>
 i.to !== '/descoberta' && i.to !== '/obras/nova'
 )
 // Item principal (à esquerda do botão central): prioriza "Minhas obras",
 // depois "Dashboard", senão o primeiro item disponível do drawer.
 const principal =
 drawerItems.find(i => i.to === '/obras') ??
 drawerItems.find(i => i.to === '/dashboard') ??
 drawerItems.find(i => i.to === '/editora/dashboard') ??
 drawerItems[0]
 return (
 <>
 {mobileOpen && (
 <div
 className="mobile-drawer-backdrop"
 onClick={() => setMobileOpen(false)}
 />
 )}

 {mobileOpen && (
 <aside
 ref={drawerRef}
 className="sidebar mobile-drawer mobile-drawer-open"
 style={{
 transform: dragOffset ? `translateX(${dragOffset}px)` : undefined,
 transition: dragStateRef.current?.dragging ? 'none' : undefined,
 }}
 onTouchStart={handleDrawerTouchStart}
 onTouchMove={handleDrawerTouchMove}
 onTouchEnd={handleDrawerTouchEnd}
 onTouchCancel={handleDrawerTouchEnd}
 >
 <div className="sidebar-header sidebar-header-mobile">
 <button className="sidebar-logo-btn" onClick={() => { navigate('/descoberta'); setMobileOpen(false) }}>
 <GravanLogo height={40} />
 </button>
 <button
 className="sidebar-toggle"
 onClick={() => setMobileOpen(false)}
 aria-label="Fechar menu"
 >×</button>
 </div>

 <nav className="sidebar-nav">
 {isAdmin && <AdminBadge collapsed={false} />}
 {drawerItems.map(({ to, Icon, label, pro, highlight }) => (
 <NavLink key={to} to={to}
 className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}
 style={highlight ? { fontWeight: 700 } : undefined}
 onClick={() => setMobileOpen(false)}>
 <span className="sidebar-icon">{Icon ? <Icon size={18} /> : null}</span>
 <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
 {label}
 {pro && <span style={proTag}>PRO</span>}
 </span>
 </NavLink>
 ))}
 </nav>

 <div className="sidebar-footer">
 <UserMenu perfil={perfil} collapsed={false} />
 </div>
 </aside>
 )}

 <nav className="mobile-bottom-nav">
 {/* Esquerda: item principal (Minhas obras / Dashboard / etc.) */}
 {principal && (
 <NavLink key={principal.to} to={principal.to}
 className={({ isActive }) => `mobile-bottom-item ${isActive ? 'active' : ''}`}>
 <span className="mobile-bottom-icon">
 {principal.Icon ? <principal.Icon size={22} /> : null}
 </span>
 <span className="mobile-bottom-label">{principal.label}</span>
 </NavLink>
 )}

 {/* Centro: Descoberta (botão destacado) */}
 <NavLink
 key={descoberta.to}
 to={descoberta.to}
 className={({ isActive }) => `mobile-bottom-center ${isActive ? 'active' : ''}`}
 aria-label="Descoberta">
 <span className="mobile-bottom-center-circle">
 <span className="mobile-bottom-center-icon">
   {descoberta.Icon ? <descoberta.Icon size={24} /> : null}
 </span>
 </span>
 <span className="mobile-bottom-center-label">{descoberta.label}</span>
 </NavLink>

 {/* Direita: Mais (drawer) */}
 <button
 className={`mobile-bottom-item ${mobileOpen ? 'active' : ''}`}
 onClick={() => setMobileOpen(o => !o)}
 aria-label="Mais opções">
 <span className="mobile-bottom-icon"><IconMore size={22} /></span>
 <span className="mobile-bottom-label">Mais</span>
 </button>
 </nav>
 </>
 )
 }

 // ── DESKTOP: sidebar fixa ─────────────────────────
 return (
 <aside className={`sidebar ${collapsed ? 'collapsed' : ''}`}>
 <div className="sidebar-header">
 {!collapsed && (
 <button className="sidebar-logo-btn" onClick={() => navigate('/descoberta')}>
 <GravanLogo height={28} />
 </button>
 )}
 <button className="sidebar-toggle" onClick={() => setCollapsed(c => !c)}>
 {collapsed ? '›' : '‹'}
 </button>
 </div>

 <nav className="sidebar-nav">
 {isAdmin && <AdminBadge collapsed={collapsed} />}

 {items.map(({ to, Icon, label, pro, highlight }) => (
 <NavLink key={to} to={to}
 className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}
 title={collapsed ? label : undefined}
 style={highlight ? { fontWeight: 700 } : undefined}>
 <span className="sidebar-icon">{Icon ? <Icon size={18} /> : null}</span>
 {!collapsed && (
 <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
 {label}
 {pro && <span style={proTag}>PRO</span>}
 </span>
 )}
 </NavLink>
 ))}
 </nav>

 <div className="sidebar-footer">
 <UserMenu perfil={perfil} collapsed={collapsed} />
 </div>
 </aside>
 )
}


const proTag = {
 background: 'var(--brand)', color: '#fff',
 fontSize: 8.5, fontWeight: 700, letterSpacing: 0.8,
 padding: '1px 5px', borderRadius: 3,
}
