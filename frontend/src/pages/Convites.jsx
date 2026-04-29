import React, { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { api } from '../lib/api'
import { useAuth } from '../contexts/AuthContext'

function fmtData(iso) {
 if (!iso) return '—'
 try { return new Date(iso).toLocaleString('pt-BR') } catch { return iso }
}

export default function Convites() {
 const [params] = useSearchParams()
 const idDestaque = params.get('id')
 const { perfil } = useAuth()

 const [lista, setLista]     = useState([])
 const [loading, setLoading] = useState(true)
 const [erro, setErro]       = useState('')
 const [msg, setMsg]         = useState('')
 const [aberto, setAberto]   = useState(null)   // {id, termo_html, ...}
 const [acao, setAcao]       = useState(null)   // 'aceitar' | 'recusar' | null
 const [assinatura, setAssinatura] = useState('')
 const [salvando, setSalvando] = useState(false)

 async function carregar() {
   setLoading(true); setErro('')
   try {
     const d = await api.get('/agregados/convites/recebidos')
     setLista(d || [])
     if (idDestaque && d?.length) {
       const c = d.find(x => x.id === idDestaque)
       if (c && c.status === 'pendente') abrir(c.id)
     }
   } catch (e) { setErro(e.message) }
   finally { setLoading(false) }
 }
 useEffect(() => { carregar() }, [])

 async function abrir(cid) {
   setMsg(''); setErro(''); setAcao(null); setAssinatura('')
   try {
     const t = await api.get(`/agregados/convites/${cid}/termo`)
     setAberto(t)
   } catch (e) { setErro(e.message) }
 }

 async function confirmar() {
   if (acao === 'aceitar' && !assinatura.trim()) {
     setErro('Digite seu nome completo como assinatura digital.')
     return
   }
   setSalvando(true); setErro('')
   try {
     if (acao === 'aceitar') {
       await api.post(`/agregados/convites/${aberto.id}/aceitar`, { assinatura_nome: assinatura.trim() })
       setMsg('Você aceitou o convite. A vinculação está ativa.')
     } else {
       await api.post(`/agregados/convites/${aberto.id}/recusar`)
       setMsg('Você recusou o convite.')
     }
     setAberto(null); setAcao(null); setAssinatura('')
     await carregar()
   } catch (e) { setErro(e.message) }
   finally { setSalvando(false) }
 }

 const pendentes  = lista.filter(c => c.status === 'pendente')
 const historico  = lista.filter(c => c.status !== 'pendente')

 return (
 <div style={{ padding: '32px 20px', maxWidth: 900, margin: '0 auto' }}>
   <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 4 }}>Convites de editora</h1>
   <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 18 }}>
     Convites recebidos para você se agregar a uma editora. Leia o termo com atenção antes de aceitar.
   </p>

   {msg  && <div style={alertOk}>{msg}</div>}
   {erro && <div style={alertErr}>{erro}</div>}

   {loading ? <p style={{ color: 'var(--text-muted)' }}>Carregando…</p> : (
   <>
     <h3 style={{ fontSize: 13, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 8 }}>
       Pendentes
     </h3>
     {pendentes.length === 0 ? (
       <div style={empty}>Nenhum convite pendente.</div>
     ) : (
       <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 24 }}>
         {pendentes.map(c => (
           <div key={c.id} style={card}>
             <div style={{ flex: 1 }}>
               <div style={{ fontWeight: 700, fontSize: 14 }}>{c.editora_nome || 'Editora'}</div>
               <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                 Recebido em {fmtData(c.created_at)} · Modo: {c.modo === 'cadastrar' ? 'cadastro inicial' : 'convite a artista existente'}
               </div>
             </div>
             <button className="btn btn-primary" onClick={() => abrir(c.id)}>Ler e responder</button>
           </div>
         ))}
       </div>
     )}

     {historico.length > 0 && (
       <>
         <h3 style={{ fontSize: 13, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 8 }}>
           Histórico
         </h3>
         <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
           {historico.map(c => (
             <div key={c.id} style={{ ...card, opacity: 0.75 }}>
               <div style={{ flex: 1 }}>
                 <div style={{ fontWeight: 700, fontSize: 14 }}>{c.editora_nome || 'Editora'}</div>
                 <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                   {fmtData(c.created_at)} · Status: <strong>{c.status}</strong>
                 </div>
               </div>
               <button className="btn btn-ghost" onClick={() => abrir(c.id)}>Ver termo</button>
             </div>
           ))}
         </div>
       </>
     )}
   </>
   )}

   {/* ── Modal: termo + aceitar/recusar ── */}
   {aberto && (
     <div style={modalBg} onClick={() => { if (!salvando) { setAberto(null); setAcao(null) } }}>
       <div style={modalBox} onClick={e => e.stopPropagation()}>
         <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
           <h3 style={{ margin: 0, fontSize: 16, fontWeight: 700 }}>Termo de Agregação</h3>
           <button onClick={() => { if (!salvando) { setAberto(null); setAcao(null) } }}
                   style={{ background: 'none', border: 'none', fontSize: 22, cursor: 'pointer', color: 'var(--text-muted)' }}>×</button>
         </div>

         <pre style={termoBox}>{aberto.termo_text || aberto.termo_html}</pre>

         {aberto.status === 'pendente' ? (
           !acao ? (
             <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 14 }}>
               <button className="btn btn-ghost"   onClick={() => setAcao('recusar')}>Recusar</button>
               <button className="btn btn-primary" onClick={() => { setAcao('aceitar'); setAssinatura(perfil?.nome_completo || perfil?.nome || '') }}>Aceitar e assinar</button>
             </div>
           ) : acao === 'aceitar' ? (
             <div style={{ marginTop: 14, padding: 12, background: 'var(--surface-2, #fafafa)', border: '1px solid var(--border)', borderRadius: 8 }}>
               <label style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>
                 Digite seu nome completo como assinatura digital *
               </label>
               <input value={assinatura} onChange={e => setAssinatura(e.target.value)}
                      style={{ width: '100%', padding: '8px 10px', border: '1px solid var(--border)', borderRadius: 6, fontSize: 13 }}
                      placeholder="Seu nome completo" />
               <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 12 }}>
                 <button className="btn btn-ghost"   disabled={salvando} onClick={() => setAcao(null)}>Voltar</button>
                 <button className="btn btn-primary" disabled={salvando} onClick={confirmar}>
                   {salvando ? 'Confirmando…' : 'Confirmar aceite'}
                 </button>
               </div>
             </div>
           ) : (
             <div style={{ marginTop: 14, padding: 12, background: 'rgba(239,68,68,.05)', border: '1px solid #ef4444', borderRadius: 8 }}>
               <p style={{ margin: 0, fontSize: 13 }}>
                 Tem certeza que deseja <strong>recusar</strong> este convite? A editora será notificada e o convite será arquivado.
               </p>
               <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 10 }}>
                 <button className="btn btn-ghost"  disabled={salvando} onClick={() => setAcao(null)}>Voltar</button>
                 <button className="btn btn-danger" disabled={salvando} onClick={confirmar}>
                   {salvando ? 'Enviando…' : 'Sim, recusar'}
                 </button>
               </div>
             </div>
           )
         ) : (
           <div style={{ marginTop: 12, fontSize: 12, color: 'var(--text-muted)' }}>
             Status atual: <strong>{aberto.status}</strong>
             {aberto.termo_aceito_pelo_artista_em && <> · Você assinou em {fmtData(aberto.termo_aceito_pelo_artista_em)} como “{aberto.assinatura_artista_nome}”.</>}
           </div>
         )}
       </div>
     </div>
   )}
 </div>
 )
}

const card    = { display: 'flex', alignItems: 'center', gap: 12, padding: 14, border: '1px solid var(--border)', borderRadius: 10, background: 'var(--surface)' }
const empty   = { padding: 32, border: '1px dashed var(--border)', borderRadius: 12, textAlign: 'center', color: 'var(--text-muted)', marginBottom: 24 }
const alertOk = { padding: 12, background: 'rgba(34,197,94,.1)', border: '1px solid #22c55e', borderRadius: 8, marginBottom: 16, fontSize: 13, color: '#16a34a' }
const alertErr= { padding: 12, background: 'rgba(239,68,68,.1)', border: '1px solid #ef4444', borderRadius: 8, marginBottom: 16, fontSize: 13, color: '#c0392b' }
const modalBg = { position: 'fixed', inset: 0, background: 'rgba(0,0,0,.45)', zIndex: 600, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16 }
const modalBox= { background: '#fff', borderRadius: 14, maxWidth: 760, width: '100%', maxHeight: '90vh', overflowY: 'auto', padding: 20, boxShadow: '0 20px 60px rgba(0,0,0,.3)' }
const termoBox= { background: '#FAFAFA', border: '1px solid var(--border)', borderRadius: 8, padding: 20, whiteSpace: 'pre-wrap', wordBreak: 'break-word', fontFamily: 'Georgia, "Times New Roman", serif', fontSize: 13, lineHeight: 1.85, margin: 0 }
