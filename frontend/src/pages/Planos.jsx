import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { api } from '../lib/api'

export default function Planos() {
 const { perfil, user } = useAuth()
 const navigate = useNavigate()
 const [status, setStatus] = useState(null)
 const [loading, setLoading] = useState(true)
 const [subLoading, setSubLoading] = useState(false)
 const [erro, setErro] = useState('')

 useEffect(() => {
 if (!user) { setLoading(false); return }
 api.get('/assinatura/status')
 .then(setStatus)
 .catch(e => setErro(e.message))
 .finally(() => setLoading(false))
 }, [user])

 async function assinarPro() {
 if (!user) { navigate('/login'); return }
 setSubLoading(true); setErro('')
 try {
 const { checkout_url } = await api.post('/assinatura/checkout', {
 origin_url: window.location.origin,
 })
 window.location.href = checkout_url
 } catch (e) {
 setErro(e.message)
 setSubLoading(false)
 }
 }

 async function cancelar() {
 if (!confirm('Cancelar assinatura PRO? Você mantém os benefícios até o fim do ciclo atual.')) return
 setSubLoading(true); setErro('')
 try {
 await api.post('/assinatura/cancelar', {})
 const s = await api.get('/assinatura/status')
 setStatus(s)
 } catch (e) { setErro(e.message) }
 finally { setSubLoading(false) }
 }

 async function sincronizarAssinatura() {
 setSubLoading(true); setErro('')
 try {
 const res = await api.post('/assinatura/sincronizar', {})
 if (res?.encontrado && res?.plano === 'PRO') {
 const s = await api.get('/assinatura/status')
 setStatus(s)
 alert('✓ Assinatura sincronizada! Você agora é PRO.')
 } else {
 alert(res?.motivo || 'Nenhuma assinatura paga encontrada no Stripe para seu email.')
 }
 } catch (e) { setErro(e.message) }
 finally { setSubLoading(false) }
 }

 const isPro = status?.plano === 'PRO' && status?.status_assinatura !== 'inativa'
 const isCanceled = status?.status_assinatura === 'cancelada'
 const feeSavingPct = 5

 return (
 <div data-testid="planos-page" style={{ padding: '48px 20px 80px', maxWidth: 1080, margin: '0 auto' }}>
 <header style={{ textAlign: 'center', marginBottom: 48 }}>
 <h1 style={{ fontSize: 32, fontWeight: 800, letterSpacing: -0.5, marginBottom: 10 }}>
 Escolha seu plano
 </h1>
 <p style={{ color: 'var(--text-muted)', fontSize: 14 }}>
 Taxa de plataforma única de <b>25%</b> para todos os planos.
 </p>
 </header>

 {loading && <p style={{ textAlign: 'center', color: 'var(--text-muted)' }}>Carregando…</p>}
 {erro && <p data-testid="planos-erro" style={{ textAlign: 'center', color: '#c0392b' }}> {erro}</p>}

 {!loading && status?.migration_applied === false && (
 <div data-testid="migration-warning" style={{
 padding: '14px 18px', marginBottom: 24, borderRadius: 10,
 background: '#FFF4E5', border: '1px solid #F5A623', color: '#7A4D00',
 fontSize: 13, lineHeight: 1.5,
 }}>
 <b> Banco de dados desatualizado.</b> O sistema de assinatura precisa da migração
 <code style={{ background: '#fff', padding: '1px 6px', borderRadius: 4, margin: '0 4px' }}>
 backend/db/migration_assinatura.sql
 </code>
 para funcionar. Rode o arquivo no SQL Editor do Supabase e recarregue esta página.
 </div>
 )}

 {!loading && (
 <div style={{
 display: 'grid', gap: 20,
 gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
 }}>
 {/* STARTER */}
 <article data-testid="plano-starter" style={cardStyle(false)}>
 <div style={{ marginBottom: 12 }}>
 <span style={tagStyle('#e4e4e7', '#27272a')}>Gratuito</span>
 </div>
 <h2 style={planName}>STARTER</h2>
 <p style={priceStyle}>R$ 0<span style={priceSuffix}>/mês</span></p>
 <ul style={listStyle}>
 <li>Acesso completo ao catálogo</li>
 <li>Upload ilimitado de obras</li>
 <li>Curtir &amp; salvar na biblioteca</li>
 <li>Licenciamento de obras (compra direta)</li>
 <li>Taxa de 25% por transação</li>
 <li style={{ color: 'var(--text-muted)' }}>✗ Sem propostas/negociação</li>
 <li style={{ color: 'var(--text-muted)' }}>✗ Preço máximo: R$ 1.000</li>
 <li style={{ color: 'var(--text-muted)' }}>✗ Sem analytics</li>
 </ul>
 <button
 data-testid="btn-starter"
 className="btn btn-ghost"
 onClick={() => navigate(user ? '/descoberta' : '/login')}
 style={{ width: '100%', marginTop: 20 }}
 >
 {user ? 'Continuar' : 'Começar grátis'}
 </button>
 </article>

 {/* PRO */}
 <article data-testid="plano-pro" style={cardStyle(true)}>
 <div style={{ marginBottom: 12 }}>
 <span style={tagStyle('var(--brand)', '#fff')}>RECOMENDADO</span>
 </div>
 <h2 style={planName}>PRO</h2>
 <p style={priceStyle}>R$ 49,90<span style={priceSuffix}>/mês</span></p>
 <ul style={listStyle}>
 <li>Tudo do Starter</li>
 <li><b style={{ color: 'var(--brand)' }}>Enviar e receber propostas</b> de licenciamento</li>
 <li><b style={{ color: 'var(--brand)' }}>Precificar até R$ 10.000</b> por obra</li>
 <li><b style={{ color: 'var(--brand)' }}>Painel de analytics</b> (plays, curtidas, vendas)</li>
 <li>Destaque na plataforma</li>
 <li>Selo PRO no seu perfil</li>
 <li>Acesso antecipado a novos recursos</li>
 </ul>
 {isPro ? (
 <>
 <div data-testid="pro-ativo" style={{
 padding: 12, borderRadius: 10, background: 'var(--surface-2,#fafafa)',
 fontSize: 13, color: 'var(--text-secondary)', marginTop: 18,
 }}>
 <div><b>✓ Assinatura {isCanceled ? 'cancelada (ativa até)' : 'ativa'}</b></div>
 <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>
 Válida até {status?.assinatura_fim ? new Date(status.assinatura_fim).toLocaleDateString('pt-BR') : '—'}
 </div>
 </div>
 {!isCanceled && (
 <button
 data-testid="btn-cancelar"
 className="btn btn-ghost"
 disabled={subLoading}
 onClick={cancelar}
 style={{ width: '100%', marginTop: 10 }}
 >
 {subLoading ? '…' : 'Cancelar assinatura'}
 </button>
 )}
 </>
 ) : (
 <>
 <button
 data-testid="btn-assinar-pro"
 className="btn btn-primary"
 onClick={assinarPro}
 disabled={subLoading || status?.migration_applied === false}
 title={status?.migration_applied === false ? 'Execute a migração do banco antes de ativar assinaturas.' : undefined}
 style={{ width: '100%', marginTop: 20 }}
 >
 {subLoading ? 'Redirecionando…' : status?.migration_applied === false ? 'Indisponível (migração pendente)' : 'Assinar PRO'}
 </button>
 <button
 data-testid="btn-sincronizar"
 className="btn btn-ghost"
 onClick={sincronizarAssinatura}
 disabled={subLoading}
 style={{ width: '100%', marginTop: 8, fontSize: 12 }}
 title="Já pagou mas o plano não atualizou? Clique aqui para forçar a sincronização com o Stripe."
 >
 Já paguei — sincronizar com Stripe
 </button>
 </>
 )}
 </article>
 </div>
 )}

 <p style={{ textAlign: 'center', fontSize: 11, color: 'var(--text-muted)', marginTop: 32 }}>
 Cobrança mensal recorrente em BRL via Stripe. Cancele a qualquer momento — você mantém
 o acesso PRO até o fim do ciclo pago.
 </p>
 </div>
 )
}

const cardStyle = (highlight) => ({
 background: '#fff',
 border: highlight ? '2px solid var(--brand)' : '1px solid var(--border)',
 borderRadius: 14,
 padding: 28,
 boxShadow: highlight ? '0 12px 40px rgba(12,68,124,0.10)' : 'none',
 position: 'relative',
})
const tagStyle = (bg, color) => ({
 display: 'inline-block', padding: '3px 10px', borderRadius: 999,
 background: bg, color, fontSize: 10, fontWeight: 700, letterSpacing: 1.2,
})
const planName = { fontSize: 24, fontWeight: 800, marginBottom: 4 }
const priceStyle = { fontSize: 32, fontWeight: 800, marginBottom: 18 }
const priceSuffix = { fontSize: 14, color: 'var(--text-muted)', fontWeight: 500 }
const listStyle = {
 listStyle: 'none', padding: 0, margin: 0,
 display: 'flex', flexDirection: 'column', gap: 10,
 fontSize: 13.5, color: 'var(--text-secondary)',
}
