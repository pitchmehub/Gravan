import React, { useEffect, useState } from 'react'
import { useParams, useNavigate, useSearchParams } from 'react-router-dom'
import { api } from '../lib/api'
import { useAuth } from '../contexts/AuthContext'

function fmt(cents) {
 return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format((cents ?? 0) / 100)
}

const METODOS = [
 { id: 'credito', label: 'Cartão de Crédito', desc: 'Visa, Mastercard, Elo, Amex',                                    icon: '💳' },
 { id: 'debito',  label: 'Cartão de Débito',  desc: 'Débito à vista',                                                 icon: '💳' },
 { id: 'pix',     label: 'PIX',              desc: 'Em breve · aguardando ativação na Stripe', icon: '🏦', disabled: true },
]

export default function Comprar() {
 const { obraId } = useParams()
 const navigate = useNavigate()
 const { perfil } = useAuth()
 const [searchParams] = useSearchParams()
 const ofertaId = searchParams.get('oferta_id') || null
 const [oferta, setOferta] = useState(null)

 // Bloqueia compra se o cadastro inicial ainda não foi preenchido (fluxo pós-login).
 useEffect(() => {
 if (perfil === undefined || perfil === null) return
 if (!perfil.role) {
 navigate('/escolher-tipo-perfil', { replace: true })
 return
 }
 if (!perfil.cadastro_completo) {
 try { localStorage.removeItem('gravan_skip_cadastro') } catch {}
 const destino = perfil.role === 'publisher' ? '/cadastro-editora' : '/perfil/completar'
 navigate(destino, { replace: true, state: { motivo: 'compra' } })
 }
 }, [perfil, navigate])

 const [obra, setObra] = useState(null)
 const [metodo, setMetodo] = useState('credito')
 const [loading, setLoading] = useState(true)
 const [pagando, setPagando] = useState(false)
 const [erro, setErro] = useState('')
 const [concordo, setConcordo] = useState(false)
 const [verContrato, setVerContrato] = useState(false)
 const [contratoTpl, setContratoTpl] = useState('')

 useEffect(() => {
 async function load() {
 try {
 const o = await api.get(`/catalogo/${obraId}`)
 setObra(o)
 if (ofertaId) {
 try {
 const of = await api.get(`/catalogo/ofertas/${ofertaId}`)
 setOferta(of)
 } catch (_) { /* segue sem oferta */ }
 }
 } catch (_) {
 navigate('/descoberta')
 } finally {
 setLoading(false)
 }
 }
 load()
 }, [obraId, ofertaId])

 // Valor exibido = valor da oferta aceita (se houver) ou preço cheio
 const valorFinal = (oferta?.status === 'aceita' ? oferta.valor_cents : obra?.preco_cents) || 0
 const eExclusiva = oferta?.tipo === 'exclusividade'

 async function confirmar() {
 if (!concordo) {
 setErro('Marque a caixa de concordância com o contrato antes de prosseguir.')
 return
 }
 setPagando(true); setErro('')
 try {
 const payload = { obra_id: obraId, metodo, concordo_contrato: true }
 if (ofertaId && oferta?.status === 'aceita') payload.oferta_id = ofertaId
 const { checkout_url } = await api.post('/stripe/checkout', payload)
 window.location.href = checkout_url
 } catch (e) {
 setErro(e.message)
 setPagando(false)
 }
 }

 async function abrirContrato() {
 setVerContrato(true)
 if (contratoTpl) return
 try {
 const params = new URLSearchParams({ obra_id: obraId })
 if (valorFinal) params.set('valor_cents', String(valorFinal))
 const d = await api.get(`/contratos/licenciamento/preview?${params.toString()}`)
 setContratoTpl(d?.conteudo || '')
 } catch (e) {
 setContratoTpl(`Não foi possível carregar o texto do contrato neste momento (${e.message}). O contrato completo, com todos os seus dados, será gerado e disponibilizado em "Meus contratos → Licenciamentos" assim que o pagamento for confirmado.`)
 }
 }

 if (loading) return (
 <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: 400 }}>
 <p style={{ color: 'var(--text-muted)' }}>Carregando…</p>
 </div>
 )
 if (!obra) return null

 return (
 <div style={{ padding: 32, maxWidth: 560 }}>
 <button
 onClick={() => navigate('/descoberta')}
 style={{ background: 'none', border: 'none', color: 'var(--brand)', cursor: 'pointer', fontSize: 14, padding: 0, marginBottom: 20 }}
 >
 ← Voltar ao catálogo
 </button>

 <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 4 }}>Finalizar licença</h1>
 <p style={{ color: 'var(--text-muted)', fontSize: 14, marginBottom: 24 }}>Licenciamento de composição musical</p>

 <div className="card" style={{ marginBottom: 20 }}>
 <div style={{ display: 'flex', gap: 16, alignItems: 'center', marginBottom: 16 }}>
 <div style={{
 width: 56, height: 56, borderRadius: 12,
 background: 'linear-gradient(135deg, #083257, #09090B)',
 display: 'flex', alignItems: 'center', justifyContent: 'center',
 fontSize: 24, flexShrink: 0,
 }}></div>
 <div>
 <div style={{ fontWeight: 700, fontSize: 17 }}>{obra.nome}</div>
 <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>
 {obra.titular_nome}
 {obra.genero && ` · ${obra.genero}`}
 </div>
 </div>
 </div>

 {obra.coautores?.length > 0 && (
 <div style={{ marginBottom: 14 }}>
 <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 6 }}>Compositores</div>
 <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
 {obra.coautores.map(c => (
 <span key={c.perfil_id} style={{
 background: 'var(--brand-light)', color: 'var(--brand)',
 padding: '3px 10px', borderRadius: 99, fontSize: 12,
 }}>
 {c.nome}
 </span>
 ))}
 </div>
 </div>
 )}

 {oferta?.status === 'aceita' && (
 <div style={{
 padding: '10px 14px', borderRadius: 8,
 background: eExclusiva ? '#f5f3ff' : '#eff6ff',
 color: eExclusiva ? '#5b21b6' : '#1e40af',
 fontSize: 13, fontWeight: 600, marginBottom: 12,
 }}>
 {eExclusiva
 ? `Pagamento de licença EXCLUSIVA (5 anos) · oferta aceita pelo compositor`
 : `Pagamento da sua oferta aceita · ${oferta.valor_cents !== obra.preco_cents
 ? `valor pactuado de ${fmt(oferta.valor_cents)} (catálogo: ${fmt(obra.preco_cents)})`
 : 'valor cheio'}`}
 </div>
 )}

 <div style={{
 display: 'flex', justifyContent: 'space-between',
 fontWeight: 700, fontSize: 22,
 borderTop: '1px solid var(--border)', paddingTop: 16, marginTop: 8,
 }}>
 <span>Total</span>
 <span style={{ color: 'var(--brand)' }}>{fmt(valorFinal)}</span>
 </div>
 </div>

 <div className="card" style={{ marginBottom: 20 }}>
 <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-muted)', letterSpacing: 1, marginBottom: 14 }}>
 MÉTODO DE PAGAMENTO
 </div>
 <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
 {METODOS.map(m => (
 <label key={m.id} style={{
 display: 'flex', alignItems: 'center', gap: 14,
 padding: '13px 16px', borderRadius: 'var(--radius-md)',
 border: `2px solid ${m.disabled ? 'var(--border)' : metodo === m.id ? 'var(--brand)' : 'var(--border)'}`,
 background: m.disabled ? 'var(--surface-2)' : metodo === m.id ? 'var(--brand-light)' : 'var(--surface)',
 cursor: m.disabled ? 'not-allowed' : 'pointer',
 opacity: m.disabled ? 0.5 : 1,
 transition: 'all .15s',
 }}>
 <input
 type="radio" name="metodo" value={m.id}
 checked={metodo === m.id}
 onChange={() => !m.disabled && setMetodo(m.id)}
 disabled={m.disabled}
 style={{ accentColor: 'var(--brand)', width: 16, height: 16 }}
 />
 <span style={{ fontSize: 20 }}>{m.icon}</span>
 <div>
 <div style={{ fontWeight: 600, fontSize: 14 }}>
 {m.label}
 {m.disabled && <span style={{ marginLeft: 8, fontSize: 11, fontWeight: 500, color: 'var(--text-muted)', background: 'var(--border)', padding: '2px 7px', borderRadius: 99 }}>Em breve</span>}
 </div>
 <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{m.desc}</div>
 </div>
 </label>
 ))}
 </div>
 </div>

 {erro && (
 <div className="card" style={{ background: 'var(--error-bg)', border: '1px solid var(--error)', marginBottom: 16 }}>
 <p style={{ color: 'var(--error)', fontSize: 14 }}>{erro}</p>
 </div>
 )}

 {/* Checkbox obrigatório: concordância com o contrato */}
 <div className="card" data-testid="card-concordancia" style={{
 marginBottom: 16,
 background: concordo ? 'var(--surface-2)' : '#FFF8E7',
 border: concordo ? '1px solid var(--border)' : '1px solid #F5C518',
 }}>
 <label htmlFor="chk-contrato-lic" style={{
 display: 'flex', gap: 10, alignItems: 'flex-start', cursor: 'pointer',
 fontSize: 13.5, lineHeight: 1.6,
 }}>
 <input
 id="chk-contrato-lic"
 data-testid="checkbox-contrato-licenciamento"
 type="checkbox"
 checked={concordo}
 onChange={e => { setConcordo(e.target.checked); if (e.target.checked) setErro('') }}
 style={{ marginTop: 3, accentColor: 'var(--brand)', width: 16, height: 16, flexShrink: 0 }}
 />
 <span>
 Declaro que li e concordo com os termos do <b>Contrato de Autorização para
 Gravação e Exploração de Obra Musical</b>, autorizando o licenciamento da
 obra <b>{obra.nome}</b> nas condições apresentadas
 ({eExclusiva ? 'exclusivo' : 'não exclusivo'}, vigência 5 anos
 {eExclusiva
 ? ' de exclusividade (renovação somente por novo acordo escrito)'
 : ' com renovação automática (rescisão por e-mail com 30 dias de antecedência ao fim do período)'},
 fee de 5% à GRAVAN sobre a exploração comercial da obra,
 território mundial, foro Rio de Janeiro/RJ).
 Ao clicar em "Pagar", minha assinatura eletrônica será registrada
 (MP 2.200-2/2001 e Lei 14.063/2020).
 </span>
 </label>
 <div style={{ marginTop: 10, paddingLeft: 26 }}>
 <button
 data-testid="link-ver-contrato"
 type="button"
 onClick={(e) => {
 e.preventDefault()
 e.stopPropagation()
 abrirContrato()
 }}
 style={{
 background: 'none', border: 'none', padding: 0, cursor: 'pointer',
 color: 'var(--brand)', fontWeight: 600, textDecoration: 'underline',
 font: 'inherit', fontSize: 12.5,
 }}
 > Ver texto completo do contrato</button>
 </div>
 </div>

 <button
 className="btn btn-primary"
 style={{ width: '100%', justifyContent: 'center', fontSize: 16, padding: '14px 20px', opacity: concordo ? 1 : 0.5 }}
 onClick={confirmar}
 disabled={pagando || !concordo}
 data-testid="btn-pagar"
 title={!concordo ? 'Marque a concordância com o contrato para prosseguir.' : undefined}
 >
 {pagando ? 'Redirecionando…' : metodo === 'pix' ? `🏦 Pagar com PIX · ${fmt(valorFinal)}` : `💳 Pagar com Cartão · ${fmt(valorFinal)}`}
 </button>

 <div style={{
 marginTop: 14, padding: 12,
 background: 'var(--surface-2)', borderRadius: 8,
 display: 'flex', alignItems: 'center', gap: 10,
 }}>
 <span style={{ fontSize: 16 }}></span>
 <p style={{ fontSize: 12, color: 'var(--text-muted)', margin: 0 }}>
 Você será redirecionado para a página segura do Stripe para concluir o pagamento.
 </p>
 </div>

 {verContrato && (
 <div
 data-testid="modal-contrato"
 onClick={e => { if (e.target === e.currentTarget) setVerContrato(false) }}
 style={{
 position: 'fixed', inset: 0, background: 'rgba(0,0,0,.6)', backdropFilter: 'blur(4px)',
 display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 900, padding: 16,
 }}
 >
 <div style={{
 background: '#fff', borderRadius: 14, width: '100%', maxWidth: 760,
 maxHeight: '88vh', display: 'flex', flexDirection: 'column',
 }}>
 <div style={{
 padding: '18px 22px', borderBottom: '1px solid var(--border)',
 display: 'flex', justifyContent: 'space-between', alignItems: 'center',
 }}>
 <h2 style={{ fontSize: 15, fontWeight: 700 }}>
 Contrato de Autorização — Texto integral
 </h2>
 <button onClick={() => setVerContrato(false)} style={{
 background: 'none', border: 'none', fontSize: 24, cursor: 'pointer', color: 'var(--text-muted)',
 }}>×</button>
 </div>
 <div style={{
 padding: '18px 22px', overflowY: 'auto', flex: 1, fontSize: 12.5,
 lineHeight: 1.7, color: 'var(--text-secondary)', whiteSpace: 'pre-wrap',
 }}>
 {contratoTpl || 'Carregando…'}
 </div>
 <div style={{
 padding: '12px 22px', borderTop: '1px solid var(--border)',
 display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8,
 }}>
 <p style={{ fontSize: 11, color: 'var(--text-muted)', margin: 0 }}>
 Este é o texto exato do contrato que será assinado eletronicamente após o pagamento.
 Ficará disponível em <b>Meus contratos → Licenciamentos</b> com hash SHA-256 final.
 </p>
 <button className="btn btn-primary" onClick={() => { setConcordo(true); setVerContrato(false) }}>
 Li e concordo
 </button>
 </div>
 </div>
 </div>
 )}
 </div>
 )
}

