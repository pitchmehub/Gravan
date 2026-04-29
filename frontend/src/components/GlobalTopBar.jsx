import React, { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { useTheme } from '../contexts/ThemeContext'
import NotificationBell from './NotificationBell'
import GravanLogo from './GravanLogo'
import {
  IconUser, IconWallet, IconLogout, IconChevronDown,
} from './Icons'
import './GlobalTopBar.css'

export default function GlobalTopBar({ leftOffset = 0, isMobile = false }) {
  const { perfil, signOut } = useAuth()
  const { theme } = useTheme()
  const [open, setOpen] = useState(false)
  const ref = useRef(null)
  const navigate = useNavigate()

  useEffect(() => {
    function onClick(e) {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false)
    }
    document.addEventListener('mousedown', onClick)
    return () => document.removeEventListener('mousedown', onClick)
  }, [])

  if (!perfil) return null

  const iniciais = (perfil.nome || '?')
    .split(' ').slice(0, 2).map(n => n[0] || '').join('').toUpperCase() || '?'

  const logoColor = theme === 'dark' ? '#5BA3E8' : '#0E2A55'
  const logoText  = theme === 'dark' ? '#F2EDE2' : '#111111'

  return (
    <header className="gtb" style={{ left: leftOffset }}>
      <div className="gtb-left">
        {isMobile && (
          <button
            className="gtb-logo-btn"
            onClick={() => navigate('/descoberta')}
            aria-label="Início"
          >
            <GravanLogo height={44} color={logoColor} textColor={logoText} />
          </button>
        )}
      </div>

      <div className="gtb-right">
        <div className="gtb-bell-wrap">
          <NotificationBell />
        </div>

        <div className="gtb-profile" ref={ref}>
          <button
            className="gtb-profile-trigger"
            onClick={() => setOpen(o => !o)}
            aria-label="Menu da conta"
          >
            {perfil.avatar_url
              ? <img src={perfil.avatar_url} alt="" className="gtb-avatar" />
              : <div className="gtb-avatar gtb-avatar-initials">{iniciais}</div>
            }
            <IconChevronDown size={12} />
          </button>

          {open && (
            <div className="gtb-dropdown" role="menu">
              <div className="gtb-dd-header">
                {perfil.avatar_url
                  ? <img src={perfil.avatar_url} alt="" className="gtb-dd-avatar" />
                  : <div className="gtb-dd-avatar gtb-dd-avatar-initials">{iniciais}</div>
                }
                <div className="gtb-dd-info">
                  <div className="gtb-dd-nome">{perfil.nome_artistico || perfil.nome}</div>
                  <div className="gtb-dd-email">{perfil.email}</div>
                </div>
              </div>
              <div className="gtb-dd-sep" />
              <button className="gtb-dd-item" onClick={() => { setOpen(false); navigate('/perfil/editar') }}>
                <IconUser size={15} /> <span>Editar perfil</span>
              </button>
              {(perfil.role === 'compositor' || perfil.role === 'publisher' || perfil.role === 'administrador') && (
                <button className="gtb-dd-item" onClick={() => { setOpen(false); navigate('/saques') }}>
                  <IconWallet size={15} /> <span>Meus saques</span>
                </button>
              )}
              <div className="gtb-dd-sep" />
              <button
                className="gtb-dd-item gtb-dd-danger"
                onClick={() => { setOpen(false); signOut() }}
              >
                <IconLogout size={15} /> <span>Sair</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}
