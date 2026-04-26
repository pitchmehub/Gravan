import React, { useEffect, useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../lib/api'
import {
  IconBell, IconMusic, IconDocument, IconCheckCircle, IconKey,
  IconTag, IconDownload, IconWallet, IconXCircle,
} from './Icons'
import './NotificationBell.css'

const ICONES = {
 obra_cadastrada: IconMusic,
 contrato_gerado: IconDocument,
 contrato_assinado: IconCheckCircle,
 licenciamento: IconKey,
 oferta: IconTag,
 dossie_download: IconDownload,
 saque_confirmado: IconWallet,
 saque_cancelado: IconXCircle,
 convite_editora: IconDocument,
}

function tempoRelativo(iso) {
 const s = Math.floor((Date.now() - new Date(iso).getTime()) / 1000)
 if (s < 60) return 'agora'
 if (s < 3600) return `${Math.floor(s / 60)}min`
 if (s < 86400) return `${Math.floor(s / 3600)}h`
 return `${Math.floor(s / 86400)}d`
}

export default function NotificationBell() {
 const [open, setOpen] = useState(false)
 const [list, setList] = useState([])
 const [naoLidas, setNaoLidas] = useState(0)
 const ref = useRef(null)
 const navigate = useNavigate()

 async function carregar() {
 try {
 const [items, count] = await Promise.all([
 api.get('/notificacoes/'),
 api.get('/notificacoes/nao-lidas'),
 ])
 setList(items || [])
 setNaoLidas(count?.total || 0)
 } catch (_) { /* silencioso */ }
 }

 useEffect(() => {
 carregar()
 const t = setInterval(carregar, 30000) // polling 30s
 return () => clearInterval(t)
 }, [])

 useEffect(() => {
 function onClick(e) {
 if (ref.current && !ref.current.contains(e.target)) setOpen(false)
 }
 document.addEventListener('mousedown', onClick)
 return () => document.removeEventListener('mousedown', onClick)
 }, [])

 async function abrir(n) {
 try { await api.patch(`/notificacoes/${n.id}/marcar-lida`) } catch (_) {}
 setOpen(false)
 if (n.link) navigate(n.link)
 carregar()
 }

 async function marcarTodas() {
 try { await api.patch('/notificacoes/marcar-todas-lidas') } catch (_) {}
 carregar()
 }

 return (
 <div className="notif-wrap" ref={ref}>
 <button
 className="notif-btn"
 onClick={() => setOpen(o => !o)}
 aria-label="Notificações"
 >
 <IconBell size={20} />
 {naoLidas > 0 && (
 <span className="notif-badge">{naoLidas > 9 ? '9+' : naoLidas}</span>
 )}
 </button>

 {open && (
 <div className="notif-panel">
 <div className="notif-header">
 <strong>Notificações</strong>
 {naoLidas > 0 && (
 <button className="notif-markall" onClick={marcarTodas}>
 Marcar todas como lidas
 </button>
 )}
 </div>
 <div className="notif-list">
 {list.length === 0 && (
 <div className="notif-empty">Nenhuma notificação ainda.</div>
 )}
 {list.map(n => (
 <div
 key={n.id}
 className={`notif-item ${n.lida ? '' : 'notif-item-unread'}`}
 onClick={() => abrir(n)}
 >
 <div className="notif-icon">
   {(() => { const Ic = ICONES[n.tipo] || IconBell; return <Ic size={18} /> })()}
 </div>
 <div className="notif-content">
 <div className="notif-title">{n.titulo}</div>
 {n.mensagem && <div className="notif-msg">{n.mensagem}</div>}
 <div className="notif-time">{tempoRelativo(n.criada_em)}</div>
 </div>
 {!n.lida && <span className="notif-dot" />}
 </div>
 ))}
 </div>
 </div>
 )}
 </div>
 )
}
