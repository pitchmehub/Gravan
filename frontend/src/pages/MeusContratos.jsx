import React, { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { api } from '../lib/api'
import { useAuth } from '../contexts/AuthContext'
import ContratosLicenciamentoLista from '../components/ContratosLicenciamentoLista'

const GRAVAN_EDITORA_UUID = 'e96bd8af-dfb8-4bf1-9ba5-7746207269cd'

function fmtData(iso) {
 if (!iso) return null
 try { return new Date(iso).toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' }) }
 catch { return iso }
}

export default function MeusContratos() {
 const [searchParams] = useSearchParams()
 const contratoIdParam = searchParams.get('contrato')
 const { user } = useAuth()

 const [aba, setAba] = useState('edicao')
 const [contratos, setContratos] = useState([])
 const [edicaoLista, setEdicaoLista] = useState([])
 const [loading, setLoading] = useState(true)
 const [erro, setErro] = useState('')
 const [baixando, setBaixando] = useState(null)
 const [verConteudo, setVerConteudo] = useState(null)
 const [verEdicao, setVerEdicao] = useState(null)
 const [carregandoEdicao, setCarregandoEdicao] = useState(false)
 const [concordoEdicao, setConcordoEdicao] = useState(false)
 const [assinando, setAssinando] = useState(null)

 async function carregarTudo() {
  setLoading(true); setErro('')
  try {
   const [legacy, edicao] = await Promise.all([
    api.get('/perfis/me/contratos').catch(() => []),
    api.get('/contratos-edicao').catch(() => []),
   ])
   const sortByDate = arr => [...(arr || [])].sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
   const sortedLegacy = sortByDate(legacy)
   const sortedEdicao = sortByDate(edicao)
   setContratos(sortedLegacy)
   setEdicaoLista(sortedEdicao)
   return sortedEdicao
  } catch (e) { setErro(e.message); return [] }
  finally { setLoading(false) }
 }

 useEffect(() => {
  carregarTudo().then(lista => {
   if (contratoIdParam && lista.length > 0) {
    const alvo = lista.find(c => c.id === contratoIdParam)
    if (alvo) abrirEdicao(alvo)
   }
  })
 }, []) // eslint-disable-line

 async function baixarPdf(c) {
  try {
   setBaixando(c.id)
   const nomeObra = (c?.obras?.nome || 'obra').toLowerCase().replace(/[^a-z0-9]+/g, '-').slice(0, 40)
   await api.download(`/perfis/contratos/${c.id}/pdf`, `contrato-${nomeObra}-${c.id.slice(0, 8)}.pdf`)
  } catch (e) { alert('Erro ao baixar: ' + e.message) }
  finally { setBaixando(null) }
 }

 async function verTexto(c) {
  try {
   const detalhe = await api.get(`/perfis/contratos/${c.id}`)
   setVerConteudo({ ...c, conteudo: detalhe.conteudo })
  } catch (e) { alert('Erro ao abrir: ' + e.message) }
 }

 async function abrirEdicao(c) {
  setConcordoEdicao(false)
  setVerEdicao({ ...c, conteudo: '' })
  setCarregandoEdicao(true)
  try {
   const d = await api.get(`/contratos-edicao/${c.id}`)
   // Mescla todos os campos do detalhe (inclui signed_by_*, publisher_id, etc.)
   setVerEdicao(prev => ({ ...prev, ...d, conteudo: d?.contract_text || '(este contrato não possui texto registrado)' }))
  } catch (e) {
   setVerEdicao(prev => ({ ...prev, conteudo: `Erro ao carregar: ${e.message}` }))
  } finally {
   setCarregandoEdicao(false)
  }
 }

 async function assinarEdicao() {
  if (!concordoEdicao) return
  const c = verEdicao
  setAssinando(c.id)
  try {
   await api.post(`/contratos-edicao/${c.id}/assinar`, {})
   setVerEdicao(null)
   await carregarTudo()
  } catch (e) { alert('Erro ao assinar: ' + e.message) }
  finally { setAssinando(null) }
 }

 function statusLabel(s) {
  return ({
   pendente:        { txt: 'Pendente',        cor: '#d97706', bg: 'rgba(245,158,11,.15)' },
   assinado_parcial:{ txt: 'Assinado parcial',cor: '#0891b2', bg: 'rgba(8,145,178,.15)' },
   assinado:        { txt: 'Assinado',         cor: '#16a34a', bg: 'rgba(34,197,94,.15)' },
   cancelado:       { txt: 'Cancelado',        cor: '#6b7280', bg: 'rgba(107,114,128,.15)' },
  })[s] || { txt: s, cor: '#6b7280', bg: 'rgba(107,114,128,.15)' }
 }

 const gravanEPublisher = verEdicao?.publisher_id === GRAVAN_EDITORA_UUID
 const euSouAutor     = verEdicao?.autor_id === user?.id
 const euSouPublisher = verEdicao?.publisher_id === user?.id && !gravanEPublisher
 const jaAssinou      = euSouAutor ? !!verEdicao?.signed_by_autor_at
                       : euSouPublisher ? !!verEdicao?.signed_by_publisher_at
                       : false
 const podeAssinarEdicao = verEdicao &&
  verEdicao.status !== 'assinado' &&
  verEdicao.status !== 'cancelado' &&
  !jaAssinou

 return (
  <div data-testid="meus-contratos-page" style={{ padding: '32px 20px', maxWidth: 960, margin: '0 auto' }}>
   <header style={{ marginBottom: 16 }}>
    <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 6 }}>Meus contratos</h1>
    <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>
     Contratos assinados eletronicamente (MP 2.200-2/2001 &amp; Lei 14.063/2020).
    </p>
   </header>

   <div style={{ display: 'flex', gap: 2, borderBottom: '1px solid var(--border)', marginBottom: 24 }}>
    {[
     { id: 'edicao', label: 'Contratos de Edição' },
     { id: 'licenciamento', label: 'Licenciamentos' },
    ].map(t => (
     <button key={t.id} data-testid={`tab-${t.id}`} onClick={() => setAba(t.id)}
      style={{
       padding: '10px 16px', background: 'transparent', border: 'none',
       borderBottom: aba === t.id ? '2px solid var(--brand)' : '2px solid transparent',
       color: aba === t.id ? 'var(--brand)' : 'var(--text-muted)',
       fontSize: 13, fontWeight: aba === t.id ? 700 : 500, cursor: 'pointer', marginBottom: -1,
      }}>{t.label}</button>
    ))}
   </div>

   {aba === 'licenciamento' ? (
    <ContratosLicenciamentoLista />
   ) : (
    <>
     {loading && <p style={{ color: 'var(--text-muted)' }}>Carregando…</p>}
     {erro && <p style={{ color: '#c0392b' }}> {erro}</p>}

     {/* Contratos de Edição (autor ⇄ editora) */}
     {edicaoLista.length > 0 && (
      <section style={{ marginBottom: 30 }}>
       <div style={{ display: 'grid', gap: 12 }}>
        {edicaoLista.map((c, i) => {
         const sl = statusLabel(c.status)
         const assinado = c.status === 'assinado' || c.status === 'cancelado'
         const euSouAutorCard = c.autor_id === user?.id
         const jaAssinou = euSouAutorCard ? !!c.signed_by_autor_at : !!c.signed_by_publisher_at
         const precisaAssinar = !assinado && !jaAssinou
         return (
          <div key={c.id} data-testid={`edicao-${i}`} style={{
           padding: 16, background: '#fff', border: '1px solid var(--border)',
           borderRadius: 12,
           boxShadow: precisaAssinar ? '0 0 0 2px #f59e0b inset' : 'none',
          }}>
           <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
            <div style={{ flex: 1, minWidth: 200 }}>
             <div style={{ fontWeight: 700, fontSize: 15 }}>{c.obra_nome || 'Obra'}</div>
             <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>
              {euSouAutorCard ? 'Autor' : 'Editora'} · Split autor: {c.share_pct}% · {c.created_at && new Date(c.created_at).toLocaleDateString('pt-BR')}
             </div>
            </div>
            <span style={{ fontSize: 11, padding: '3px 8px', background: sl.bg, color: sl.cor, fontWeight: 600, borderRadius: 4 }}>{sl.txt}</span>
            {jaAssinou
             ? <span style={{ fontSize: 11, color: '#0E6B2B', fontWeight: 600 }}>✓ você assinou</span>
             : !assinado && (
              <span style={{ fontSize: 11, color: '#7A4D00', fontWeight: 600 }}>⏱ aguardando sua assinatura</span>
             )}
            {precisaAssinar ? (
             <button className="btn btn-primary"
              style={{ fontSize: 13, padding: '8px 16px', fontWeight: 700, background: '#f59e0b', borderColor: '#f59e0b', color: '#fff' }}
              onClick={() => abrirEdicao(c)}>
              Assinar contrato
             </button>
            ) : (
             <button className="btn btn-ghost"
              style={{ fontSize: 12, padding: '6px 12px' }}
              onClick={() => abrirEdicao(c)}>
              Ver contrato
             </button>
            )}
           </div>
          </div>
         )
        })}
       </div>
      </section>
     )}

     {!loading && !erro && contratos.length === 0 && edicaoLista.length === 0 && (
      <div style={{ padding: 40, border: '1px dashed var(--border)', borderRadius: 12, textAlign: 'center', color: 'var(--text-muted)', fontSize: 13 }}>
       Você ainda não possui contratos.
      </div>
     )}

     {contratos.length > 0 && (
      <section>
       <h2 style={{ fontSize: 14, fontWeight: 700, marginBottom: 10 }}>Contratos da plataforma</h2>
       <div style={{ border: '1px solid var(--border)', borderRadius: 12, overflow: 'hidden', overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13, minWidth: 640 }}>
         <thead style={{ background: 'var(--surface-2, #fafafa)' }}>
          <tr>
           <th style={th}>Obra</th><th style={th}>Versão</th>
           <th style={th}>Assinado em</th><th style={{ ...th, textAlign: 'right' }}>Ações</th>
          </tr>
         </thead>
         <tbody>
          {contratos.map((c) => (
           <tr key={c.id} style={{ borderTop: '1px solid var(--border)' }}>
            <td style={td}>
             <div style={{ fontWeight: 600 }}>{c?.obras?.nome || 'Obra'}</div>
             <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>ID {c.id.slice(0, 8)}</div>
            </td>
            <td style={td}>{c.versao || 'v2.0'}</td>
            <td style={td}>{c.assinado_em ? new Date(c.assinado_em).toLocaleString('pt-BR') : '—'}</td>
            <td style={{ ...td, textAlign: 'right' }}>
             <button onClick={() => verTexto(c)} className="btn btn-ghost"
              style={{ marginRight: 8, fontSize: 12, padding: '6px 12px' }}>Ver texto</button>
             <button onClick={() => baixarPdf(c)} className="btn btn-primary" disabled={baixando === c.id}
              style={{ fontSize: 12, padding: '6px 12px' }}>
              {baixando === c.id ? 'Gerando…' : 'Baixar PDF'}
             </button>
            </td>
           </tr>
          ))}
         </tbody>
        </table>
       </div>
      </section>
     )}
    </>
   )}

   {/* Modal: contrato legado (plataforma) */}
   {verConteudo && (
    <div onClick={e => { if (e.target === e.currentTarget) setVerConteudo(null) }}
     style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,.6)', backdropFilter: 'blur(4px)',
      display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 700, padding: 24 }}>
     <div style={{ background: '#fff', borderRadius: 14, width: '100%', maxWidth: 780, maxHeight: '88vh', display: 'flex', flexDirection: 'column' }}>
      <div style={{ padding: '18px 22px', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
       <h2 style={{ fontSize: 15, fontWeight: 700 }}>Contrato — {verConteudo?.obras?.nome}</h2>
       <button onClick={() => setVerConteudo(null)} style={{ background: 'none', border: 'none', fontSize: 24, cursor: 'pointer', color: 'var(--text-muted)' }}>×</button>
      </div>
      <div style={{ padding: '18px 22px', overflowY: 'auto', flex: 1, fontSize: 12.5, lineHeight: 1.7, whiteSpace: 'pre-wrap', fontFamily: 'Georgia, serif' }}>
       {verConteudo.conteudo || 'Sem conteúdo.'}
      </div>
      <div style={{ padding: '12px 22px', borderTop: '1px solid var(--border)', display: 'flex', justifyContent: 'flex-end' }}>
       <button className="btn" style={{ padding: '8px 14px' }} onClick={() => setVerConteudo(null)}>Fechar</button>
      </div>
     </div>
    </div>
   )}

   {/* Modal: contrato de edição — visualização + assinatura integradas */}
   {verEdicao && (
    <div onClick={e => { if (e.target === e.currentTarget) setVerEdicao(null) }}
     style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,.6)', backdropFilter: 'blur(4px)',
      display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 700, padding: 24 }}>
     <div style={{ background: '#fff', borderRadius: 14, width: '100%', maxWidth: 780, maxHeight: '88vh', display: 'flex', flexDirection: 'column' }}>

      {/* Cabeçalho */}
      <div style={{ padding: '18px 22px', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
       <div>
        <h2 style={{ fontSize: 15, fontWeight: 700 }}>
         Contrato de Edição Musical{verEdicao?.obra_nome ? ` — ${verEdicao.obra_nome}` : ''}
        </h2>
        <p style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>
         Leia o contrato completo antes de assinar
        </p>
       </div>
       <button onClick={() => setVerEdicao(null)} style={{ background: 'none', border: 'none', fontSize: 24, cursor: 'pointer', color: 'var(--text-muted)' }}>×</button>
      </div>

      {/* Corpo — texto integral */}
      <div style={{ padding: '18px 22px', overflowY: 'auto', flex: 1, fontSize: 12.5, lineHeight: 1.75, whiteSpace: 'pre-wrap', fontFamily: 'Georgia, serif' }}>
       {carregandoEdicao ? (
        <p style={{ color: 'var(--text-muted)' }}>Carregando contrato…</p>
       ) : (
        verEdicao.conteudo || 'Sem conteúdo.'
       )}
      </div>

      {/* Rodapé — assinatura */}
      <div style={{ padding: '16px 22px', borderTop: '1px solid var(--border)', background: '#fafafa' }}>

       {/* Painel de assinaturas — sempre visível */}
       <div style={{ marginBottom: 14, display: 'flex', flexDirection: 'column', gap: 6 }}>
        {/* Gravan (publisher automático) */}
        {gravanEPublisher && (
         <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12.5 }}>
          <span style={{ color: '#16a34a', fontWeight: 700, fontSize: 14 }}>✓</span>
          <span>
           <strong>GRAVAN Editora Musical Ltda.</strong>
           {' — '}
           <span style={{ color: '#16a34a' }}>
            Assinatura automática{verEdicao.signed_by_publisher_at ? ` · ${fmtData(verEdicao.signed_by_publisher_at)}` : ''}
           </span>
          </span>
         </div>
        )}

        {/* Autor */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12.5 }}>
         {verEdicao.signed_by_autor_at ? (
          <span style={{ color: '#16a34a', fontWeight: 700, fontSize: 14 }}>✓</span>
         ) : (
          <span style={{ color: '#d97706', fontWeight: 700, fontSize: 14 }}>⏳</span>
         )}
         <span>
          <strong>Compositor</strong>
          {' — '}
          {verEdicao.signed_by_autor_at
           ? <span style={{ color: '#16a34a' }}>Assinado · {fmtData(verEdicao.signed_by_autor_at)}</span>
           : <span style={{ color: '#d97706' }}>Aguardando assinatura</span>
          }
         </span>
        </div>

        {/* Publisher real (quando não é Gravan) */}
        {!gravanEPublisher && (
         <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12.5 }}>
          {verEdicao.signed_by_publisher_at ? (
           <span style={{ color: '#16a34a', fontWeight: 700, fontSize: 14 }}>✓</span>
          ) : (
           <span style={{ color: '#d97706', fontWeight: 700, fontSize: 14 }}>⏳</span>
          )}
          <span>
           <strong>Editora</strong>
           {' — '}
           {verEdicao.signed_by_publisher_at
            ? <span style={{ color: '#16a34a' }}>Assinado · {fmtData(verEdicao.signed_by_publisher_at)}</span>
            : <span style={{ color: '#d97706' }}>Aguardando assinatura</span>
           }
          </span>
         </div>
        )}
       </div>

       {podeAssinarEdicao ? (
        <>
         <label style={{ display: 'flex', alignItems: 'flex-start', gap: 10, cursor: 'pointer', marginBottom: 14, fontSize: 13 }}>
          <input
           type="checkbox"
           checked={concordoEdicao}
           onChange={e => setConcordoEdicao(e.target.checked)}
           style={{ marginTop: 3, width: 16, height: 16, accentColor: 'var(--brand)', flexShrink: 0, cursor: 'pointer' }}
          />
          <span style={{ lineHeight: 1.5 }}>
           Li o texto integral acima e <strong>assino eletronicamente</strong> este Contrato de Edição Musical.
           Entendo que a assinatura eletrônica é juridicamente válida nos termos da MP 2.200-2/2001 e da Lei 14.063/2020.
          </span>
         </label>
         <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
          <button className="btn" style={{ padding: '8px 14px' }} onClick={() => setVerEdicao(null)}>Fechar</button>
          <button
           className="btn btn-primary"
           disabled={!concordoEdicao || assinando === verEdicao?.id || carregandoEdicao}
           style={{ padding: '8px 18px' }}
           onClick={assinarEdicao}
          >
           {assinando === verEdicao?.id ? 'Assinando…' : 'Confirmar assinatura'}
          </button>
         </div>
        </>
       ) : (
        <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
         <button className="btn" style={{ padding: '8px 14px' }} onClick={() => setVerEdicao(null)}>Fechar</button>
        </div>
       )}
      </div>

     </div>
    </div>
   )}
  </div>
 )
}

const th = { textAlign: 'left', padding: '10px 14px', fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 0.5 }
const td = { padding: '12px 14px', verticalAlign: 'middle' }
