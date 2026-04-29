import React, { useEffect, useRef, useState } from 'react'
import { useParams, useNavigate, useSearchParams } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { api } from '../lib/api'

const GRAVAN_EDITORA_UUID = '00000000-0000-0000-0000-000000000001'

const ROLE_LABEL = {
  autor:              'Autor principal',
  coautor:            'Coautor',
  interprete:         'Intérprete',
  'intérprete':       'Intérprete',
  editora_detentora:  'Editora Detentora dos Direitos',
  editora_agregadora: 'Editora Agregadora',
  editora_terceira:   'Editora',
}

export default function ContratoLicenciamentoDetalhe() {
 const { id } = useParams()
 const { user } = useAuth()
 const navigate = useNavigate()
 const [searchParams] = useSearchParams()
 const focoAssinar = searchParams.get('assinar') === '1'

 const [c, setC] = useState(null)
 const [loading, setLoading] = useState(true)
 const [erro, setErro] = useState('')
 const [concordo, setConcordo] = useState(false)
 const [assinando, setAssinando] = useState(false)
 const [baixando, setBaixando] = useState(false)
 const acoesRef = useRef(null)

 async function reload() {
 try {
 setLoading(true)
 const d = await api.get(`/contratos/licenciamento/${id}`)
 setC(d)
 } catch (e) { setErro(e.message) }
 finally { setLoading(false) }
 }
 useEffect(() => { reload() /* eslint-disable-next-line */ }, [id])

 // Quando entra com ?assinar=1, rola até a área de assinatura
 useEffect(() => {
 if (!loading && focoAssinar && acoesRef.current) {
 setTimeout(() => {
 acoesRef.current.scrollIntoView({ behavior: 'smooth', block: 'center' })
 }, 250)
 }
 }, [loading, focoAssinar])

 const meuSigner = c?.signers?.find(s => s.user_id === user?.id)
 const jaAssinei = !!meuSigner?.signed
 const concluido = c?.status === 'concluído' || c?.status === 'concluido'
 const assinadosCount = c?.signers?.filter(s => s.signed).length || 0
 const totalSigners = c?.signers?.length || 0
 const progresso = totalSigners ? Math.round((assinadosCount / totalSigners) * 100) : 0

 async function aceitar() {
 if (!concordo) { alert('Marque "Li e concordo com os termos" para aceitar.'); return }
 setAssinando(true)
 try {
 await api.post(`/contratos/licenciamento/${id}/aceitar`, { concordo: true })
 await reload()
 } catch (e) { alert('Erro: ' + e.message) }
 finally { setAssinando(false) }
 }

 async function baixarPdf() {
 setBaixando(true)
 try {
 const nome = (c?.obra_nome || 'obra').toLowerCase().replace(/[^a-z0-9]+/g, '-').slice(0, 40)
 await api.download(`/contratos/licenciamento/${id}/pdf`, `contrato-licenciamento-${nome}.pdf`)
 } catch (e) { alert('Erro ao baixar PDF: ' + e.message) }
 finally { setBaixando(false) }
 }

 const papel = ({ autor: 'Autor principal', coautor: 'Coautor', interprete: 'Intérprete', 'intérprete': 'Intérprete' }[meuSigner?.role] || meuSigner?.role)

 function moeda(cents) {
 return (cents / 100).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
 }

 if (loading) return <div style={{ padding: 40 }}>Carregando…</div>
 if (erro) return <div style={{ padding: 40, color: '#c0392b' }}> {erro}</div>
 if (!c) return null

 return (
 <div data-testid="contrato-detalhe" style={{ maxWidth: 880, margin: '0 auto', padding: '32px 20px' }}>
 <button
 onClick={() => navigate(-1)}
 className="btn btn-ghost"
 style={{ fontSize: 12, marginBottom: 16 }}
 >← Voltar</button>

 {/* Cabeçalho */}
 <div style={{
 padding: 20, background: '#fff', border: '1px solid var(--border)',
 borderRadius: 12, marginBottom: 16,
 }}>
 <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 16, flexWrap: 'wrap' }}>
 <div>
 <h1 style={{ fontSize: 20, fontWeight: 700, marginBottom: 4 }}>
 Contrato de Licenciamento
 </h1>
 <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>
 Obra: <b>{c.obra_nome}</b> · Valor: <b style={{ color: 'var(--brand)' }}>{moeda(c.valor_cents)}</b>
 {papel && <> · Seu papel: <b>{papel}</b></>}
 </p>
 </div>
 <div style={{ textAlign: 'right' }}>
 <span data-testid="contrato-status" style={{
 padding: '4px 10px', borderRadius: 4, fontSize: 11, fontWeight: 700,
 background: concluido ? '#E8F8EC' : '#FFF4E5',
 color: concluido ? '#0E6B2B' : '#7A4D00',
 }}>{concluido ? 'CONCLUÍDO' : 'AGUARDANDO ASSINATURAS'}</span>
 <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 6 }}>
 {assinadosCount} de {totalSigners} assinou(ram) · {progresso}%
 </div>
 </div>
 </div>

 {/* Barra de progresso */}
 <div style={{ height: 4, background: 'var(--surface-2,#f0f0f0)', borderRadius: 2, marginTop: 12, overflow: 'hidden' }}>
 <div data-testid="contrato-progresso" style={{
 width: `${progresso}%`, height: '100%',
 background: concluido ? '#0E6B2B' : 'var(--brand)',
 transition: 'width .3s',
 }} />
 </div>
 </div>

 {/* Lista de signers */}
 <div style={{
 padding: 16, background: '#fff', border: '1px solid var(--border)',
 borderRadius: 12, marginBottom: 16,
 }}>
 <h3 style={{ fontSize: 13, fontWeight: 700, marginBottom: 10, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: 1 }}>
 Participantes
 </h3>
 {c.signers?.map((s, i) => {
 const isGravan = s.user_id === GRAVAN_EDITORA_UUID
 const nome = isGravan
  ? 'GRAVAN Editora Musical Ltda.'
  : (s?.perfis?.nome_completo || s?.perfis?.nome || 'Sem nome')
 return (
 <div key={s.user_id} data-testid={`signer-${i}`} style={{
 display: 'flex', justifyContent: 'space-between', alignItems: 'center',
 padding: '8px 0', borderBottom: i < c.signers.length - 1 ? '1px solid var(--border)' : 'none',
 }}>
 <div>
 <div style={{ fontSize: 13, fontWeight: 600 }}>
 {nome}
 {s.user_id === user?.id && <span style={{ color: 'var(--brand)', fontSize: 11, marginLeft: 6 }}>(você)</span>}
 </div>
 <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
 {ROLE_LABEL[s.role] || s.role}
 {s.share_pct != null && ` · ${Number(s.share_pct).toFixed(2)}%`}
 </div>
 </div>
 <div style={{ fontSize: 11, fontWeight: 600 }}>
 {s.signed
 ? <span style={{ color: '#0E6B2B' }}>
   ✓ {isGravan ? 'Assinatura automática' : 'Assinou'}{s.signed_at ? ` · ${new Date(s.signed_at).toLocaleDateString('pt-BR')}` : ''}
  </span>
 : <span style={{ color: 'var(--text-muted)' }}>⏱ Pendente</span>}
 </div>
 </div>
 )
 })}
 </div>

 {/* Conteúdo do contrato */}
 <div style={{
 padding: '32px 36px', background: '#fff', border: '1px solid var(--border)',
 borderRadius: 12, marginBottom: 16, fontSize: 13.5, lineHeight: 1.85,
 color: 'var(--text-secondary)',
 }}>
 <div data-testid="contrato-conteudo" dangerouslySetInnerHTML={{ __html: c.contract_html }} />
 </div>

 {/* Ações */}
 <div ref={acoesRef} style={{
 padding: 16, background: '#fff',
 border: focoAssinar && !jaAssinei && meuSigner && !concluido
 ? '2px solid #f59e0b'
 : '1px solid var(--border)',
 borderRadius: 12,
 boxShadow: focoAssinar && !jaAssinei && meuSigner && !concluido
 ? '0 0 0 4px rgba(245,158,11,0.15)'
 : 'none',
 }}>
 {!jaAssinei && meuSigner && !concluido && (
 <>
 <label style={{ display: 'flex', gap: 8, alignItems: 'flex-start', marginBottom: 14, fontSize: 13, cursor: 'pointer' }}>
 <input
 data-testid="checkbox-concordo"
 type="checkbox" checked={concordo}
 onChange={e => setConcordo(e.target.checked)}
 style={{ marginTop: 3 }}
 />
 <span>Li e concordo com os termos deste <b>Contrato de Autorização para Gravação e Exploração de Obra Musical</b>. Entendo que a assinatura eletrônica é válida nos termos da MP 2.200-2/2001 e da Lei 14.063/2020.</span>
 </label>
 <div style={{ display: 'flex', gap: 10 }}>
 <button
 data-testid="btn-aceitar"
 className="btn btn-primary"
 disabled={!concordo || assinando}
 onClick={aceitar}
 >{assinando ? 'Assinando…' : 'Aceitar contrato'}</button>
 <button
 data-testid="btn-pdf"
 className="btn btn-ghost"
 disabled={baixando}
 onClick={baixarPdf}
 >{baixando ? 'Gerando…' : 'Baixar PDF'}</button>
 </div>
 </>
 )}

 {jaAssinei && !concluido && (
 <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
 <p style={{ fontSize: 13, color: '#0E6B2B', fontWeight: 600 }}>
 ✓ Você já assinou. Aguardando demais participantes.
 </p>
 <button className="btn btn-ghost" onClick={baixarPdf} disabled={baixando}>
 {baixando ? 'Gerando…' : 'Baixar PDF'}
 </button>
 </div>
 )}

 {concluido && (
 <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
 <p style={{ fontSize: 13, color: '#0E6B2B', fontWeight: 600 }}>
 ✓ Contrato concluído — todos assinaram. A licença está liberada.
 </p>
 <button className="btn btn-primary" onClick={baixarPdf} disabled={baixando}>
 {baixando ? 'Gerando…' : 'Baixar PDF'}
 </button>
 </div>
 )}

 {!meuSigner && (
 <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>
 Você tem acesso a este contrato mas não precisa assinar.
 </p>
 )}
 </div>
 </div>
 )
}
