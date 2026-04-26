import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../lib/api'

function fmt(cents) {
 return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format((cents ?? 0) / 100)
}

function fmtData(iso) {
 if (!iso) return '—'
 try {
   return new Date(iso).toLocaleString('pt-BR', {
     day: '2-digit', month: '2-digit', year: 'numeric',
     hour: '2-digit', minute: '2-digit',
   })
 } catch { return iso }
}

function HistoricoLicenciamentos() {
 const [data, setData] = useState(null)
 const [erro, setErro] = useState('')

 useEffect(() => {
   api.get('/publishers/historico-licenciamentos')
     .then(setData)
     .catch(e => setErro(e.message))
 }, [])

 if (erro) return null
 if (!data) {
   return (
     <div style={{ marginBottom: 28 }}>
       <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 12 }}>Histórico de licenciamentos</h2>
       <div style={{ padding: 16, color: 'var(--text-muted)', fontSize: 13 }}>Carregando…</div>
     </div>
   )
 }

 const itens = data.itens || []

 return (
   <div style={{ marginBottom: 28 }}>
     <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', flexWrap: 'wrap', gap: 8, marginBottom: 12 }}>
       <h2 style={{ fontSize: 18, fontWeight: 700 }}>
         Histórico de licenciamentos
       </h2>
       <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
         {itens.length === 0
           ? 'Nenhum licenciamento ainda'
           : <>Total recebido: <strong style={{ color: 'var(--brand)' }}>{fmt(data.total_cents)}</strong> · {data.total_transacoes} transação(ões)</>}
       </div>
     </div>

     {itens.length === 0 ? (
       <div style={{
         padding: 18, background: 'var(--surface)', border: '1px solid var(--border)',
         borderRadius: 12, fontSize: 13, color: 'var(--text-muted)',
       }}>
         Quando uma obra de um agregado seu for licenciada, a sua participação
         de 10% aparecerá aqui automaticamente.
       </div>
     ) : (
       <div style={{
         background: 'var(--surface)', border: '1px solid var(--border)',
         borderRadius: 12, overflow: 'hidden',
       }}>
         <div style={{ overflowX: 'auto' }}>
           <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
             <thead>
               <tr style={{ background: 'rgba(0,0,0,.04)', textAlign: 'left' }}>
                 <th style={{ padding: '10px 14px', fontWeight: 700, fontSize: 11, textTransform: 'uppercase', letterSpacing: '.06em', color: 'var(--text-muted)' }}>Data</th>
                 <th style={{ padding: '10px 14px', fontWeight: 700, fontSize: 11, textTransform: 'uppercase', letterSpacing: '.06em', color: 'var(--text-muted)' }}>Obra</th>
                 <th style={{ padding: '10px 14px', fontWeight: 700, fontSize: 11, textTransform: 'uppercase', letterSpacing: '.06em', color: 'var(--text-muted)' }}>Titular (agregado)</th>
                 <th style={{ padding: '10px 14px', fontWeight: 700, fontSize: 11, textTransform: 'uppercase', letterSpacing: '.06em', color: 'var(--text-muted)' }}>Comprador</th>
                 <th style={{ padding: '10px 14px', fontWeight: 700, fontSize: 11, textTransform: 'uppercase', letterSpacing: '.06em', color: 'var(--text-muted)', textAlign: 'right' }}>Valor da venda</th>
                 <th style={{ padding: '10px 14px', fontWeight: 700, fontSize: 11, textTransform: 'uppercase', letterSpacing: '.06em', color: 'var(--text-muted)', textAlign: 'right' }}>Sua comissão</th>
               </tr>
             </thead>
             <tbody>
               {itens.map(it => (
                 <tr key={it.id} style={{ borderTop: '1px solid var(--border)' }}>
                   <td style={{ padding: '10px 14px', whiteSpace: 'nowrap', color: 'var(--text-secondary)' }}>{fmtData(it.data)}</td>
                   <td style={{ padding: '10px 14px', fontWeight: 600 }}>{it.obra?.nome || '—'}</td>
                   <td style={{ padding: '10px 14px' }}>{it.titular?.nome || '—'}</td>
                   <td style={{ padding: '10px 14px' }}>{it.comprador?.nome || '—'}</td>
                   <td style={{ padding: '10px 14px', textAlign: 'right', whiteSpace: 'nowrap' }}>
                     {it.valor_total_cents != null ? fmt(it.valor_total_cents) : '—'}
                   </td>
                   <td style={{ padding: '10px 14px', textAlign: 'right', whiteSpace: 'nowrap', fontWeight: 800, color: 'var(--brand)' }}>
                     {fmt(it.comissao_cents)}
                     {it.share_pct != null && (
                       <div style={{ fontSize: 10, fontWeight: 500, color: 'var(--text-muted)' }}>
                         {Number(it.share_pct).toFixed(0)}%
                       </div>
                     )}
                   </td>
                 </tr>
               ))}
             </tbody>
           </table>
         </div>
       </div>
     )}
   </div>
 )
}

function StatCard({ label, value, sub, accent }) {
 return (
 <div style={{
 padding: '18px 20px',
 background: accent ? 'rgba(12,68,124,.18)' : 'var(--surface)',
 border: `1px solid ${accent ? 'rgba(12,68,124,.4)' : 'var(--border)'}`,
 borderRadius: 14,
 }}>
 <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 8 }}>
 {label}
 </div>
 <div style={{ fontSize: 28, fontWeight: 900, color: accent ? 'var(--brand)' : 'var(--text-primary)', lineHeight: 1, marginBottom: 6 }}>
 {value}
 </div>
 {sub && <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{sub}</div>}
 </div>
 )
}

function fmtRestante(h) {
 if (h == null) return '—'
 if (h <= 0) return 'Expirado'
 if (h < 1) return `${Math.round(h * 60)} min úteis`
 return `${h.toFixed(1)} h úteis`
}

function OfertasPendentes() {
 const [ofertas, setOfertas] = useState(null)
 const [erro, setErro] = useState('')
 useEffect(() => {
 api.get('/ofertas-licenciamento/editora')
 .then(setOfertas).catch(e => setErro(e.message))
 }, [])

 if (erro) return null
 if (!ofertas) return null
 const aguardando = ofertas.filter(o => o.status === 'aguardando_editora' || o.status === 'aguardando_assinaturas')
 if (aguardando.length === 0) return null

 return (
 <div style={{ marginBottom: 28 }}>
 <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 12 }}>
 Ofertas pendentes ({aguardando.length})
 </h2>
 <div style={{ display: 'grid', gap: 12 }}>
 {aguardando.map(o => (
 <div key={o.id} style={{
 padding: 16, background: 'var(--surface)',
 border: '1px solid var(--border)', borderRadius: 12,
 display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap',
 }}>
 <div style={{ flex: '1 1 280px', minWidth: 0 }}>
 <div style={{ fontWeight: 700, fontSize: 15 }}>{o.obra?.nome ?? '(obra)'}</div>
 <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>
 Comprador: {o.comprador?.nome ?? '—'} · Status: {o.status.replace(/_/g, ' ')}
 </div>
 {o.mensagem && (
 <div style={{ fontSize: 12, fontStyle: 'italic', marginTop: 6, color: 'var(--text-secondary)' }}>
 "{o.mensagem}"
 </div>
 )}
 </div>
 <div style={{ textAlign: 'right' }}>
 <div style={{ fontSize: 18, fontWeight: 800, color: 'var(--brand)' }}>{fmt(o.valor_cents)}</div>
 <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
 Prazo: {fmtRestante(o.horas_uteis_restantes)}
 </div>
 {o.contract_id && (
 <Link to={`/contratos/licenciamento/${o.contract_id}`}
 className="btn btn-primary btn-sm" style={{ marginTop: 8 }}>
 Revisar e assinar
 </Link>
 )}
 </div>
 </div>
 ))}
 </div>
 </div>
 )
}

function CartaoSaque() {
 const [wallet, setWallet] = useState(null)

 useEffect(() => {
   api.get('/perfis/me/wallet').then(setWallet).catch(() => setWallet({ saldo_cents: 0, saques: [] }))
 }, [])

 const saldo = wallet?.saldo_cents ?? 0
 const saques = wallet?.saques ?? []
 const reservado = saques
   .filter(x => ['pendente_otp', 'aguardando_liberacao', 'processando', 'solicitado'].includes(x.status))
   .reduce((s, x) => s + x.valor_cents, 0)
 const totalSacado = saques.filter(x => x.status === 'pago').reduce((s, x) => s + x.valor_cents, 0)
 const disponivel = Math.max(0, saldo - reservado)

 return (
   <div style={{
     padding: 24, marginBottom: 28,
     background: 'linear-gradient(135deg,#083257,#09090B)',
     borderRadius: 16, color: '#fff',
   }}>
     <div style={{ fontSize: 12, fontWeight: 600, color: 'rgba(255,255,255,.7)', letterSpacing: 1, textTransform: 'uppercase' }}>
       Saldo da editora disponível para saque
     </div>
     <div style={{ fontSize: 38, fontWeight: 800, marginTop: 6 }}>{fmt(disponivel)}</div>
     <div style={{ display: 'flex', gap: 24, marginTop: 16, fontSize: 12, flexWrap: 'wrap' }}>
       <div>
         <div style={{ color: 'rgba(255,255,255,.6)' }}>SALDO TOTAL</div>
         <div style={{ fontSize: 16, fontWeight: 700, marginTop: 2 }}>{fmt(saldo)}</div>
       </div>
       <div>
         <div style={{ color: 'rgba(255,255,255,.6)' }}>RESERVADO</div>
         <div style={{ fontSize: 16, fontWeight: 700, marginTop: 2 }}>{fmt(reservado)}</div>
       </div>
       <div>
         <div style={{ color: 'rgba(255,255,255,.6)' }}>JÁ SACADO</div>
         <div style={{ fontSize: 16, fontWeight: 700, marginTop: 2 }}>{fmt(totalSacado)}</div>
       </div>
     </div>
     <div style={{ marginTop: 18 }}>
       <Link to="/saques" className="btn btn-primary"
             style={{ background: '#fff', color: '#083257', borderColor: '#fff' }}>
         Solicitar saque
       </Link>
     </div>
   </div>
 )
}

export default function PublisherDashboard() {
 const [data, setData] = useState(null)
 const [erro, setErro] = useState('')

 useEffect(() => {
 api.get('/publishers/dashboard').then(setData).catch(e => setErro(e.message))
 }, [])

 if (erro) return <div style={{ padding: 32, color: '#c0392b' }}> {erro}</div>
 if (!data) return <div style={{ padding: 32, color: 'var(--text-muted)' }}>Carregando…</div>

 return (
 <div style={{ padding: '32px 20px', maxWidth: 1100, margin: '0 auto' }}>
 <header style={{ marginBottom: 24 }}>
 <h1 style={{ fontSize: 24, fontWeight: 700 }}>Dashboard da Editora</h1>
 <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>Visão geral de obras, contratos e faturamento.</p>
 </header>

 <CartaoSaque />

 <OfertasPendentes />

 <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 14, marginBottom: 28 }}>
 <StatCard label="Obras" value={data.total_obras} sub={`${data.obras_publicadas} publicadas`} />
 <StatCard label="Agregados" value={data.total_agregados} />
 <StatCard label="Contratos assinados" value={data.contratos_assinados} sub={`${data.contratos_pendentes} pendentes`} />
 <StatCard label="Faturamento bruto" value={fmt(data.faturamento_cents)} accent />
 <StatCard label="Fee devido (5%)" value={fmt(data.fee_devido_cents)} sub="Plataforma GRAVAN" />
 </div>

 <HistoricoLicenciamentos />

 <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
 <Link to="/agregados" className="btn btn-primary">Gerir agregados</Link>
 <Link to="/obras/nova" className="btn btn-ghost">Cadastrar nova obra</Link>
 <Link to="/contratos" className="btn btn-ghost">Ver contratos</Link>
 </div>
 </div>
 )
}
