import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { usePlayer } from '../contexts/PlayerContext'
import { supabase } from '../lib/supabase'
import { api } from '../lib/api'
import { IconPlay, IconPause, IconSparkles, IconHourglass } from '../components/Icons'

function fmt(cents) {
 return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format((cents ?? 0) / 100)
}

export default function MinhasObras() {
 const { perfil } = useAuth()
 const navigate = useNavigate()
 const { playObra, obra: obraAtual, playing } = usePlayer()

 const [obras, setObras] = useState([])
 const [loading, setLoading] = useState(true)
 const [selected, setSelected] = useState(null)
 const [excluindo, setExcluindo] = useState(false)
 const [confirmarExcluir, setConfirmarExcluir] = useState(false)
 const [regerandoCapa, setRegerandoCapa] = useState(null)

 useEffect(() => { load() }, [])

 async function load() {
 setLoading(true)
 try {
 const { data } = await supabase
 .from('coautorias')
 .select('share_pct, is_titular, obras(id, nome, genero, preco_cents, status, audio_path, titular_id, created_at, cover_url, publisher_id, gravan_editora_id)')
 .eq('perfil_id', perfil.id)
 const lista = (data ?? [])
 .filter(c => c.obras)
 .map(c => ({ ...c.obras, share_pct: c.share_pct, sou_titular: c.is_titular }))
 .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
 const publisherIds = [...new Set(lista.filter(o => o.publisher_id && !o.gravan_editora_id).map(o => o.publisher_id))]
 let publisherMap = {}
 if (publisherIds.length > 0) {
 const { data: pubs } = await supabase.from('perfis').select('id, nome, nome_artistico').in('id', publisherIds)
 publisherMap = Object.fromEntries((pubs || []).map(p => [p.id, p.nome_artistico || p.nome || 'Editora parceira']))
 }
 setObras(lista.map(o => ({
 ...o,
 _publisher_nome: o.publisher_id && !o.gravan_editora_id ? (publisherMap[o.publisher_id] || 'Editora parceira vinculada') : null,
 })))
 } finally { setLoading(false) }
 }

 async function excluir(obra) {
 if (!obra.sou_titular) {
 alert('Apenas o titular pode excluir a obra.')
 return
 }
 setExcluindo(true)
 try {
 await api.get(`/obras/${obra.id}`) // placeholder; vamos usar fetch DELETE
 } catch (_) {}
 try {
 await fetch(`${import.meta.env.VITE_API_URL || import.meta.env.VITE_API_BASE_URL || '/api'}/obras/${obra.id}`, {
 method: 'DELETE',
 headers: {
 'Authorization': `Bearer ${(await supabase.auth.getSession()).data.session?.access_token}`,
 },
 })
 setObras(prev => prev.filter(o => o.id !== obra.id))
 setSelected(null)
 setConfirmarExcluir(false)
 } catch (e) {
 alert('Erro ao excluir: ' + e.message)
 } finally {
 setExcluindo(false)
 }
 }

 async function regerarCapa(obra) {
 setRegerandoCapa(obra.id)
 try {
 const r = await api.post(`/ai/obras/${obra.id}/gerar-capa`)
 if (r?.cover_url) {
 setObras(prev => prev.map(o => o.id === obra.id ? { ...o, cover_url: r.cover_url } : o))
 }
 } catch (e) {
 alert('Erro ao gerar capa: ' + e.message)
 } finally {
 setRegerandoCapa(null)
 }
 }

 if (loading) return <div style={{ padding: 32 }}><p style={{ color: 'var(--text-muted)' }}>Carregando…</p></div>

 return (
 <div className="page-slide-up" style={{ padding: 32, maxWidth: 920 }}>
 <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
 <div>
 <h1 style={{ fontSize: 24, fontWeight: 800 }}>Minhas obras</h1>
 <p style={{ color: 'var(--text-muted)', fontSize: 14 }}>{obras.length} composição{obras.length !== 1 ? 'ões' : ''} cadastrada{obras.length !== 1 ? 's' : ''}</p>
 </div>
 <button className="btn btn-primary" onClick={() => navigate('/obras/nova')}>+ Nova obra</button>
 </div>

 {obras.length === 0 ? (
 <div style={{
 padding: 60, textAlign: 'center',
 background: 'var(--surface-2)', borderRadius: 16,
 }}>
 <div style={{ fontSize: 48, opacity: .3, marginBottom: 12 }}></div>
 <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 8 }}>Você ainda não cadastrou obras</h2>
 <p style={{ color: 'var(--text-muted)', fontSize: 14, marginBottom: 16 }}>Comece a publicar suas composições no Gravan.</p>
 <button className="btn btn-primary" onClick={() => navigate('/obras/nova')}>Cadastrar primeira obra</button>
 </div>
 ) : (
 <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
 {obras.map(obra => {
 const isPlaying = obraAtual?.id === obra.id && playing
 return (
 <div key={obra.id}
 onClick={() => setSelected(selected?.id === obra.id ? null : obra)}
 style={{
 padding: 16, background: 'var(--surface)',
 border: `1.5px solid ${selected?.id === obra.id ? 'var(--brand)' : 'var(--border)'}`,
 borderRadius: 12, cursor: 'pointer',
 transition: 'all .15s',
 }}>
 <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
 <div style={{ position: 'relative', width: 44, height: 44, flexShrink: 0 }}>
 {obra.cover_url ? (
 <img
 src={obra.cover_url}
 alt=""
 loading="lazy"
 style={{
 width: 44, height: 44, borderRadius: 8,
 objectFit: 'cover', display: 'block',
 background: 'var(--surface-2)',
 }}
 onError={e => { e.currentTarget.style.display = 'none' }}
 />
 ) : (
 <div style={{
 width: 44, height: 44, borderRadius: 8,
 background: 'linear-gradient(135deg,#083257,#09090B)',
 }} />
 )}
 <button
 onClick={e => { e.stopPropagation(); playObra(obra) }}
 style={{
 position: 'absolute', inset: 0,
 borderRadius: 8,
 background: 'rgba(0,0,0,0.45)',
 color: '#fff', border: 'none', cursor: 'pointer',
 fontSize: 14, display: 'flex',
 alignItems: 'center', justifyContent: 'center',
 }}>
 {isPlaying ? <IconPause size={18} /> : <IconPlay size={18} />}
 </button>
 </div>
 <div style={{ flex: 1, minWidth: 0 }}>
 <div style={{ fontSize: 15, fontWeight: 700 }}>{obra.nome}</div>
 <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
 {obra.genero || 'Sem gênero'} · {fmt(obra.preco_cents)} · seu share: {obra.share_pct}%
 {obra.sou_titular && ' · titular'}
 </div>
 {obra.gravan_editora_id && (
 <div style={{ fontSize: 11, color: 'var(--brand)', fontWeight: 600, marginTop: 2 }}>
 Editora: Gravan Editora Musical
 </div>
 )}
 {obra._publisher_nome && (
 <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>
 Editora: {obra._publisher_nome}
 </div>
 )}
 </div>
 <span style={{
 fontSize: 11, fontWeight: 600,
 padding: '3px 10px', borderRadius: 99,
 background: obra.status === 'publicada' ? 'var(--success-bg)' : 'var(--warning-bg)',
 color: obra.status === 'publicada' ? 'var(--success)' : 'var(--warning)',
 }}>
 {obra.status}
 </span>
 </div>

 {/* Ações ao selecionar */}
 {selected?.id === obra.id && (
 <div style={{
 marginTop: 14, paddingTop: 14,
 borderTop: '1px solid var(--border)',
 display: 'flex', gap: 10, justifyContent: 'flex-end',
 }}>
 {obra.sou_titular ? (
 !confirmarExcluir ? (
 <>
 <button
 className="btn btn-secondary btn-sm"
 onClick={e => { e.stopPropagation(); regerarCapa(obra) }}
 disabled={regerandoCapa === obra.id}
 title="Gerar nova capa com IA (Pollinations.ai, grátis)"
 style={{ marginRight: 'auto' }}>
 {regerandoCapa === obra.id ? (
  <><IconHourglass size={14} /> Gerando…</>
 ) : (
  <><IconSparkles size={14} /> Regerar capa</>
 )}
 </button>
 <button
 className="btn btn-danger btn-sm"
 onClick={e => { e.stopPropagation(); setConfirmarExcluir(true) }}>
 Excluir composição
 </button>
 </>
 ) : (
 <>
 <span style={{ fontSize: 13, color: 'var(--error)', alignSelf: 'center', marginRight: 'auto' }}>
 Tem certeza? Esta ação não pode ser desfeita.
 </span>
 <button className="btn btn-ghost btn-sm" onClick={e => { e.stopPropagation(); setConfirmarExcluir(false) }}>
 Cancelar
 </button>
 <button className="btn btn-danger btn-sm" onClick={e => { e.stopPropagation(); excluir(obra) }} disabled={excluindo}>
 {excluindo ? 'Excluindo…' : 'Sim, excluir'}
 </button>
 </>
 )
 ) : (
 <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
 Você é coautor desta obra. Apenas o titular pode excluí-la.
 </span>
 )}
 </div>
 )}
 </div>
 )
 })}
 </div>
 )}
 </div>
 )
}
