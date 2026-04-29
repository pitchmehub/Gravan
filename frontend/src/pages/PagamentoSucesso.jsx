import React, { useEffect, useState } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { api } from '../lib/api'

function fmt(cents) {
 return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format((cents ?? 0) / 100)
}

export default function PagamentoSucesso() {
 const [params] = useSearchParams()
 const navigate = useNavigate()
 const sessionId = params.get('session_id')

 const [status, setStatus] = useState('verificando') // verificando | sucesso | erro
 const [dados, setDados] = useState(null)
 const [erro, setErro] = useState('')
 const [contratoId, setContratoId] = useState(null)
 const [baixandoDossie, setBaixandoDossie] = useState(false)

 useEffect(() => {
 if (!sessionId) { setStatus('erro'); setErro('Sessão inválida.'); return }

 async function verify() {
 try {
 const resp = await api.get(`/stripe/sucesso/${sessionId}`)
 setDados(resp)
 const confirmado = resp.stripe_status === 'paid' || resp.transacao?.status === 'confirmada'
 if (confirmado) {
 setStatus('sucesso')
 const tid = resp?.transacao?.id
 if (tid) {
 try {
 const c = await api.get(`/contratos/licenciamento/by-transacao/${tid}`)
 if (c?.contract_id && c?.sou_comprador) setContratoId(c.contract_id)
 } catch (_) { /* silencioso — botão fica oculto */ }
 }
 } else {
 setStatus('aguardando')
 }
 } catch (e) {
 setStatus('erro')
 setErro(e.message ?? 'Erro ao verificar pagamento.')
 }
 }
 verify()
 }, [sessionId])

 async function baixarDossie() {
 if (!contratoId) return
 setBaixandoDossie(true)
 try {
 const slug = (dados?.obra_nome || 'obra').toLowerCase().replace(/[^a-z0-9]+/g, '-').slice(0, 40)
 await api.download(
 `/contratos/licenciamento/${contratoId}/dossie-licenca`,
 `dossie-de-licenca-${slug}.zip`,
 )
 } catch (e) {
 alert('Erro ao baixar Dossiê de Licença: ' + (e?.message || ''))
 } finally {
 setBaixandoDossie(false)
 }
 }

 return (
 <div style={{ padding: 32, maxWidth: 520, margin: '40px auto', textAlign: 'center' }}>
 {status === 'verificando' && (
 <>
 <div style={{
 width: 80, height: 80, borderRadius: '50%',
 background: 'var(--brand-light)', color: 'var(--brand)',
 fontSize: 36, display: 'flex', alignItems: 'center', justifyContent: 'center',
 margin: '0 auto 20px',
 animation: 'spin 1.5s linear infinite',
 }}>⟳</div>
 <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 8 }}>Verificando pagamento…</h1>
 <p style={{ color: 'var(--text-muted)' }}>Aguarde um instante.</p>
 <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
 </>
 )}

 {status === 'sucesso' && (
 <>
 <div style={{
 width: 80, height: 80, borderRadius: '50%',
 background: 'var(--success-bg)', color: 'var(--success)',
 fontSize: 40, fontWeight: 'bold',
 display: 'flex', alignItems: 'center', justifyContent: 'center',
 margin: '0 auto 20px',
 }}>✓</div>
 <h1 style={{ fontSize: 24, fontWeight: 800, marginBottom: 8 }}>Pagamento confirmado!</h1>
 <p style={{ color: 'var(--text-muted)', marginBottom: 24, lineHeight: 1.6 }}>
 Sua licença de <strong>{dados?.obra_nome}</strong> foi aprovada.<br />
 O valor está retido em escrow até que todas as partes assinem o contrato de licenciamento.
 </p>

 {dados?.transacao && (
 <div className="card" style={{ marginBottom: 20, textAlign: 'left' }}>
 <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 12 }}>
 Detalhes da compra
 </div>
 <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
 <span style={{ color: 'var(--text-secondary)' }}>Composição</span>
 <span style={{ fontWeight: 600 }}>{dados.obra_nome}</span>
 </div>
 <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
 <span style={{ color: 'var(--text-secondary)' }}>Valor pago</span>
 <span style={{ fontWeight: 700, color: 'var(--brand)' }}>{fmt(dados.transacao.valor_cents)}</span>
 </div>
 <div style={{ display: 'flex', justifyContent: 'space-between' }}>
 <span style={{ color: 'var(--text-secondary)' }}>Status</span>
 <span style={{
 fontWeight: 600, color: 'var(--success)',
 background: 'var(--success-bg)', padding: '2px 10px', borderRadius: 99, fontSize: 12,
 }}>
 ✓ Confirmado
 </span>
 </div>
 </div>
 )}

 {contratoId && (
 <div style={{
 marginBottom: 16, padding: 16, textAlign: 'left',
 background: 'linear-gradient(135deg, #083257 0%, #0b1220 100%)',
 borderRadius: 14, color: '#fff',
 boxShadow: '0 6px 24px rgba(8, 50, 87, 0.25)',
 }}>
 <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: 1.2, opacity: .8, textTransform: 'uppercase', marginBottom: 6 }}>
 Cortesia exclusiva
 </div>
 <div style={{ fontSize: 16, fontWeight: 800, marginBottom: 4 }}>Dossiê de Licença</div>
 <div style={{ fontSize: 12, opacity: .85, lineHeight: 1.5, marginBottom: 12 }}>
 Pacote ZIP com a letra em PDF premium, o áudio MP3 da composição e a cópia do contrato assinado.
 </div>
 <button
 data-testid="btn-baixar-dossie-licenca"
 onClick={baixarDossie}
 disabled={baixandoDossie}
 style={{
 background: '#fff', color: '#083257', border: 'none',
 padding: '10px 18px', borderRadius: 8, fontSize: 13, fontWeight: 700,
 cursor: baixandoDossie ? 'wait' : 'pointer', opacity: baixandoDossie ? .7 : 1,
 }}
 >{baixandoDossie ? 'Preparando ZIP…' : '↓ Baixar Dossiê de Licença'}</button>
 </div>
 )}

 <div style={{ display: 'flex', gap: 12, justifyContent: 'center' }}>
 <button className="btn btn-primary" onClick={() => navigate('/compras')}>Minhas compras</button>
 <button className="btn btn-ghost" onClick={() => navigate('/descoberta')}>Voltar ao catálogo</button>
 </div>
 </>
 )}

 {status === 'aguardando' && (
 <>
 <div style={{
 width: 80, height: 80, borderRadius: '50%',
 background: 'var(--warning-bg)', color: 'var(--warning)',
 fontSize: 40, display: 'flex', alignItems: 'center', justifyContent: 'center',
 margin: '0 auto 20px',
 }}>⏱</div>
 <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 8 }}>Aguardando confirmação</h1>
 <p style={{ color: 'var(--text-muted)', marginBottom: 24 }}>
 Para PIX a confirmação pode levar alguns segundos. Pode atualizar a página em instantes.
 </p>
 <button className="btn btn-primary" onClick={() => window.location.reload()}>Atualizar agora</button>
 </>
 )}

 {status === 'erro' && (
 <>
 <div style={{
 width: 80, height: 80, borderRadius: '50%',
 background: 'var(--error-bg)', color: 'var(--error)',
 fontSize: 40, display: 'flex', alignItems: 'center', justifyContent: 'center',
 margin: '0 auto 20px',
 }}>!</div>
 <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 8 }}>Erro ao verificar pagamento</h1>
 <p style={{ color: 'var(--text-muted)', marginBottom: 24 }}>{erro}</p>
 <button className="btn btn-primary" onClick={() => navigate('/descoberta')}>Voltar ao catálogo</button>
 </>
 )}
 </div>
 )
}
