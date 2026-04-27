import React, { useEffect, useState } from 'react'
import { api } from '../lib/api'

function fmtCPF(v) {
 const d = v.replace(/\D/g, '').slice(0, 11)
 if (d.length <= 3) return d
 if (d.length <= 6) return `${d.slice(0,3)}.${d.slice(3)}`
 if (d.length <= 9) return `${d.slice(0,3)}.${d.slice(3,6)}.${d.slice(6)}`
 return `${d.slice(0,3)}.${d.slice(3,6)}.${d.slice(6,9)}-${d.slice(9)}`
}
function fmtCEP(v) {
 const d = v.replace(/\D/g, '').slice(0, 8)
 if (d.length <= 5) return d
 return `${d.slice(0,5)}-${d.slice(5)}`
}
function fmtData(iso) {
 if (!iso) return '—'
 try { return new Date(iso).toLocaleDateString('pt-BR', { day: '2-digit', month: 'short', year: 'numeric' }) }
 catch { return iso }
}

const EMPTY_CADASTRAR = {
 nome_completo: '', nome_artistico: '', rg: '', cpf: '', email: '',
 endereco_rua: '', endereco_numero: '', endereco_compl: '',
 endereco_bairro: '', endereco_cidade: '', endereco_uf: '', endereco_cep: '',
 responsavel_aceite: '', responsavel_cpf: '', aceitou_termo: false,
}
const EMPTY_ADICIONAR = { email: '', responsavel_aceite: '', responsavel_cpf: '', aceitou_termo: false }

export default function Agregados() {
 const [aba, setAba]           = useState('lista')   // 'lista' | 'cadastrar' | 'adicionar' | 'convites'
 const [lista, setLista]       = useState([])
 const [convites, setConvites] = useState([])
 const [loading, setLoading]   = useState(true)
 const [erro, setErro]         = useState('')
 const [msg, setMsg]           = useState('')
 const [formC, setFormC]       = useState(EMPTY_CADASTRAR)
 const [formA, setFormA]       = useState(EMPTY_ADICIONAR)
 const [salvando, setSalvando] = useState(false)
 const [showTermo, setShowTermo] = useState(false)

 async function carregar() {
 setLoading(true); setErro('')
 try {
 const [d1, d2] = await Promise.all([
 api.get('/agregados'),
 api.get('/agregados/convites'),
 ])
 setLista(d1 || [])
 setConvites(d2 || [])
 } catch (e) { setErro(e.message) }
 finally { setLoading(false) }
 }
 useEffect(() => { carregar() }, [])

 async function submitCadastrar(e) {
 e.preventDefault()
 if (!formC.aceitou_termo) {
   setErro('Você precisa confirmar a leitura e aceite do termo jurídico.')
   return
 }
 setSalvando(true); setMsg(''); setErro('')
 try {
 await api.post('/agregados/cadastrar', formC)
 setMsg('Convite enviado. O artista receberá um e-mail para definir senha e responder ao termo.')
 setFormC(EMPTY_CADASTRAR)
 setAba('convites')
 await carregar()
 } catch (e) { setErro(e.message) }
 finally { setSalvando(false) }
 }

 async function submitAdicionar(e) {
 e.preventDefault()
 if (!formA.aceitou_termo) {
   setErro('Você precisa confirmar a leitura e aceite do termo jurídico.')
   return
 }
 setSalvando(true); setMsg(''); setErro('')
 try {
 await api.post('/agregados/adicionar', formA)
 setMsg('Convite enviado. O artista receberá uma notificação para aceitar ou recusar.')
 setFormA(EMPTY_ADICIONAR)
 setAba('convites')
 await carregar()
 } catch (e) { setErro(e.message) }
 finally { setSalvando(false) }
 }

 async function desvincular(id) {
 if (!confirm('Desvincular este agregado da sua editora? As obras já cadastradas continuam, mas você não poderá mais administrá-las.')) return
 try { await api.delete(`/agregados/${id}`); await carregar() }
 catch (e) { alert(e.message) }
 }

 async function cancelarConvite(cid) {
 if (!confirm('Cancelar este convite?')) return
 try { await api.delete(`/agregados/convites/${cid}`); await carregar() }
 catch (e) { alert(e.message) }
 }

 function setC(k, v) { setFormC(f => ({ ...f, [k]: v })) }
 function setA(k, v) { setFormA(f => ({ ...f, [k]: v })) }

 const inputStyle = { width: '100%', padding: '8px 10px', border: '1px solid var(--border)', borderRadius: 6, fontSize: 13 }
 const lbl = { fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', marginBottom: 3, display: 'block' }

 return (
 <div style={{ padding: '32px 20px', maxWidth: 1100, margin: '0 auto' }}>
 <div style={{ marginBottom: 18 }}>
 <h1 style={{ fontSize: 22, fontWeight: 700 }}>Agregados</h1>
 <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>Artistas vinculados à sua editora.</p>
 </div>

 {/* Abas */}
 <div style={{ display: 'flex', gap: 4, borderBottom: '1px solid var(--border)', marginBottom: 18, flexWrap: 'wrap' }}>
 <Tab ativa={aba === 'lista'}      onClick={() => setAba('lista')}>Vinculados ({lista.length})</Tab>
 <Tab ativa={aba === 'convites'}   onClick={() => setAba('convites')}>Convites enviados ({convites.filter(c => c.status === 'pendente').length})</Tab>
 <div style={{ flex: 1 }} />
 <Tab ativa={aba === 'cadastrar'}  onClick={() => { setAba('cadastrar'); setMsg(''); setErro('') }} primary>+ Cadastrar agregado</Tab>
 <Tab ativa={aba === 'adicionar'}  onClick={() => { setAba('adicionar'); setMsg(''); setErro('') }} primary>+ Adicionar agregado</Tab>
 </div>

 {msg  && <div style={alertOk}>{msg}</div>}
 {erro && <div style={alertErr}>{erro}</div>}

 {/* ─── ABA: VINCULADOS ─── */}
 {aba === 'lista' && (
 loading ? <p style={{ color: 'var(--text-muted)' }}>Carregando…</p>
 : lista.length === 0 ? (
   <div style={empty}>Nenhum artista agregado ainda. Use "Cadastrar" ou "Adicionar" acima.</div>
 ) : (
 <div style={{ ...card, padding: 0, overflowX: 'auto' }}>
 <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13, minWidth: 640 }}>
 <thead style={{ background: 'var(--surface-2, #fafafa)' }}>
 <tr>
 <th style={th}>Nome</th>
 <th style={th}>Nome artístico</th>
 <th style={th}>E-mail</th>
 <th style={th}>Status</th>
 <th style={{ ...th, textAlign: 'right' }}>Ações</th>
 </tr>
 </thead>
 <tbody>
 {lista.map(a => (
 <tr key={a.id} style={{ borderTop: '1px solid var(--border)' }}>
 <td style={td}>{a.nome_completo}</td>
 <td style={td}>{a.nome_artistico}</td>
 <td style={td}>{a.email}</td>
 <td style={td}>
   {a.is_ghost
     ? <span style={badgeWarn}>Ativação pendente</span>
     : <span style={badgeOk}>Ativo</span>}
 </td>
 <td style={{ ...td, textAlign: 'right' }}>
   <button className="btn btn-ghost" style={{ fontSize: 12, padding: '4px 10px' }}
           onClick={() => desvincular(a.id)}>Desvincular</button>
 </td>
 </tr>
 ))}
 </tbody>
 </table>
 </div>
 )
 )}

 {/* ─── ABA: CONVITES ENVIADOS ─── */}
 {aba === 'convites' && (
   convites.length === 0 ? (
     <div style={empty}>Nenhum convite enviado.</div>
   ) : (
     <div style={{ ...card, padding: 0, overflowX: 'auto' }}>
       <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13, minWidth: 720 }}>
         <thead style={{ background: 'var(--surface-2, #fafafa)' }}>
           <tr>
             <th style={th}>E-mail</th>
             <th style={th}>Modo</th>
             <th style={th}>Enviado em</th>
             <th style={th}>Decidido em</th>
             <th style={th}>Status</th>
             <th style={{ ...th, textAlign: 'right' }}>Ações</th>
           </tr>
         </thead>
         <tbody>
           {convites.map(c => (
             <tr key={c.id} style={{ borderTop: '1px solid var(--border)' }}>
               <td style={td}>{c.email_artista}</td>
               <td style={td}>{c.modo === 'cadastrar' ? 'Cadastro novo' : 'Adicionar existente'}</td>
               <td style={td}>{fmtData(c.created_at)}</td>
               <td style={td}>{fmtData(c.decided_at)}</td>
               <td style={td}>
                 {c.status === 'pendente' && <span style={badgeWarn}>Pendente</span>}
                 {c.status === 'aceito'   && <span style={badgeOk}>Aceito</span>}
                 {c.status === 'recusado' && <span style={badgeErr}>Recusado</span>}
                 {c.status === 'cancelado'&& <span style={badgeMuted}>Cancelado</span>}
                 {c.status === 'expirado' && <span style={badgeMuted}>Expirado</span>}
               </td>
               <td style={{ ...td, textAlign: 'right' }}>
                 {c.status === 'pendente' && (
                   <button className="btn btn-ghost" style={{ fontSize: 12, padding: '4px 10px' }}
                           onClick={() => cancelarConvite(c.id)}>Cancelar</button>
                 )}
               </td>
             </tr>
           ))}
         </tbody>
       </table>
     </div>
   )
 )}

 {/* ─── ABA: CADASTRAR ─── */}
 {aba === 'cadastrar' && (
 <form onSubmit={submitCadastrar} style={card}>
 <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 6 }}>Cadastrar artista que ainda não está na Gravan</h3>
 <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 14 }}>
   Informe os dados completos do artista. Ele receberá um e-mail para definir uma senha e,
   no primeiro acesso, deverá <strong>aceitar ou recusar</strong> o termo jurídico de agregação.
   Sem o aceite do artista, nenhuma obra é administrada em seu nome.
 </p>

 <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
 <div><label style={lbl}>Nome completo *</label><input style={inputStyle} value={formC.nome_completo} onChange={e => setC('nome_completo', e.target.value)} required /></div>
 <div><label style={lbl}>Nome artístico *</label><input style={inputStyle} value={formC.nome_artistico} onChange={e => setC('nome_artistico', e.target.value)} required /></div>
 <div><label style={lbl}>RG *</label><input style={inputStyle} value={formC.rg} onChange={e => setC('rg', e.target.value)} required /></div>
 <div><label style={lbl}>CPF *</label><input style={inputStyle} value={formC.cpf} onChange={e => setC('cpf', fmtCPF(e.target.value))} required /></div>
 <div style={{ gridColumn: '1 / -1' }}><label style={lbl}>E-mail *</label><input style={inputStyle} type="email" value={formC.email} onChange={e => setC('email', e.target.value)} required /></div>
 </div>

 <h4 style={{ fontSize: 12, fontWeight: 700, marginTop: 14, marginBottom: 8, color: 'var(--text-muted)' }}>Endereço</h4>
 <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr', gap: 10 }}>
 <div><label style={lbl}>Rua</label><input style={inputStyle} value={formC.endereco_rua} onChange={e => setC('endereco_rua', e.target.value)} /></div>
 <div><label style={lbl}>Número</label><input style={inputStyle} value={formC.endereco_numero} onChange={e => setC('endereco_numero', e.target.value)} /></div>
 <div><label style={lbl}>Compl.</label><input style={inputStyle} value={formC.endereco_compl} onChange={e => setC('endereco_compl', e.target.value)} /></div>
 </div>
 <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 80px 110px', gap: 10, marginTop: 10 }}>
 <div><label style={lbl}>Bairro</label><input style={inputStyle} value={formC.endereco_bairro} onChange={e => setC('endereco_bairro', e.target.value)} /></div>
 <div><label style={lbl}>Cidade</label><input style={inputStyle} value={formC.endereco_cidade} onChange={e => setC('endereco_cidade', e.target.value)} /></div>
 <div><label style={lbl}>UF</label><input style={inputStyle} maxLength={2} value={formC.endereco_uf} onChange={e => setC('endereco_uf', e.target.value.toUpperCase())} /></div>
 <div><label style={lbl}>CEP</label><input style={inputStyle} value={formC.endereco_cep} onChange={e => setC('endereco_cep', fmtCEP(e.target.value))} /></div>
 </div>

 <BlocoTermoEditora
   responsavel={formC.responsavel_aceite}
   onResponsavel={v => setC('responsavel_aceite', v)}
   responsavelCpf={formC.responsavel_cpf}
   onResponsavelCpf={v => setC('responsavel_cpf', fmtCPF(v))}
   aceitou={formC.aceitou_termo}
   onAceitou={v => setC('aceitou_termo', v)}
   showTermo={showTermo}
   setShowTermo={setShowTermo}
   modo="cadastrar"
 />

 <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', marginTop: 14 }}>
   <button type="button" className="btn btn-ghost" onClick={() => setAba('lista')}>Cancelar</button>
   <button type="submit" disabled={salvando} className="btn btn-primary">
     {salvando ? 'Enviando…' : 'Cadastrar e enviar convite'}
   </button>
 </div>
 </form>
 )}

 {/* ─── ABA: ADICIONAR ─── */}
 {aba === 'adicionar' && (
 <form onSubmit={submitAdicionar} style={card}>
 <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 6 }}>Adicionar artista que já tem perfil na Gravan</h3>
 <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 14 }}>
   Informe o e-mail cadastrado pelo artista. Ele receberá uma notificação na plataforma e
   por e-mail para <strong>aceitar ou recusar</strong> o termo de agregação. O vínculo só se
   efetiva após o aceite.
 </p>

 <div><label style={lbl}>E-mail do artista *</label>
  <input style={inputStyle} type="email" value={formA.email}
         onChange={e => setA('email', e.target.value)} required placeholder="artista@exemplo.com" /></div>

 <BlocoTermoEditora
   responsavel={formA.responsavel_aceite}
   onResponsavel={v => setA('responsavel_aceite', v)}
   responsavelCpf={formA.responsavel_cpf}
   onResponsavelCpf={v => setA('responsavel_cpf', fmtCPF(v))}
   aceitou={formA.aceitou_termo}
   onAceitou={v => setA('aceitou_termo', v)}
   showTermo={showTermo}
   setShowTermo={setShowTermo}
   modo="adicionar"
 />

 <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', marginTop: 14 }}>
   <button type="button" className="btn btn-ghost" onClick={() => setAba('lista')}>Cancelar</button>
   <button type="submit" disabled={salvando} className="btn btn-primary">
     {salvando ? 'Enviando…' : 'Enviar convite'}
   </button>
 </div>
 </form>
 )}
 </div>
 )
}

// ── Bloco do termo jurídico ──────────────────────────────
function BlocoTermoEditora({ responsavel, onResponsavel, responsavelCpf, onResponsavelCpf, aceitou, onAceitou, showTermo, setShowTermo, modo }) {
 const inputStyle = { width: '100%', padding: '8px 10px', border: '1px solid var(--border)', borderRadius: 6, fontSize: 13 }
 const lbl = { fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', marginBottom: 3, display: 'block' }
 return (
   <div style={{ marginTop: 18, padding: 14, background: 'var(--surface-2, #fafafa)', border: '1px solid var(--border)', borderRadius: 8 }}>
     <h4 style={{ fontSize: 13, fontWeight: 700, margin: '0 0 4px' }}>Termo de Agregação e Representação Editorial</h4>
     <p style={{ fontSize: 12, color: 'var(--text-muted)', margin: '0 0 10px' }}>
       Ao enviar este convite, sua editora declara, sob as penas da lei, possuir os direitos
       de administração editorial das obras do artista — ou que os obterá mediante o aceite
       digital deste termo. Você indeniza e mantém indene a Gravan de qualquer reclamação
       de terceiros (Cláusula 3.3 do termo).
     </p>

     <button type="button" onClick={() => setShowTermo(s => !s)}
             style={{ background: 'none', border: 'none', color: 'var(--brand)', cursor: 'pointer',
                      fontSize: 12, fontWeight: 600, padding: 0, marginBottom: 10 }}>
       {showTermo ? '▲ Ocultar texto integral do termo' : '▼ Ler texto integral do termo'}
     </button>

     {showTermo && (
       <div style={{ background: '#fff', border: '1px solid var(--border)', borderRadius: 6, padding: 12, maxHeight: 280, overflowY: 'auto', fontSize: 12, color: '#333', marginBottom: 10 }}>
         <PreviaTermo modo={modo} />
       </div>
     )}

     <p style={{ fontSize: 11, color: 'var(--text-muted)', margin: '4px 0 8px' }}>
       Identifique a pessoa física que está fazendo esta solicitação em nome da editora:
     </p>
     <div style={{ display: 'grid', gridTemplateColumns: '1fr 180px', gap: 10 }}>
       <div><label style={lbl}>Nome de quem está solicitando *</label>
         <input style={inputStyle} value={responsavel} onChange={e => onResponsavel(e.target.value)}
                placeholder="Ex: Maria da Silva" required minLength={5} />
       </div>
       <div><label style={lbl}>CPF de quem está solicitando *</label>
         <input style={inputStyle} value={responsavelCpf} onChange={e => onResponsavelCpf(e.target.value)}
                placeholder="000.000.000-00" required maxLength={14} />
       </div>
     </div>

     <label style={{ display: 'flex', gap: 8, marginTop: 10, cursor: 'pointer', fontSize: 13 }}>
       <input type="checkbox" checked={aceitou} onChange={e => onAceitou(e.target.checked)} required />
       <span>Li e <strong>aceito o termo</strong> em nome da editora, declarando ter os direitos de administração editorial das obras deste artista.</span>
     </label>
   </div>
 )
}

function PreviaTermo({ modo }) {
 return (
   <div>
     <p><strong>OBJETO.</strong> O artista nomeia a editora como sua representante editorial perante a plataforma Gravan, conferindo-lhe poderes para administrar as obras musicais que vierem a ser cadastradas e vinculadas ao seu catálogo.</p>
     <p><strong>PODERES.</strong> Cadastrar e publicar obras; receber e responder ofertas de licenciamento; negociar e assinar contratos; receber valores e fazer repasses na forma da Cláusula 5ª.</p>
     <p><strong>DECLARAÇÕES DA EDITORA.</strong> Possui plena capacidade jurídica; detém os direitos de administração editorial; <strong>indeniza e mantém indene a Gravan</strong> de qualquer reclamação por excesso ou falta dos poderes; respeita LGPD.</p>
     <p><strong>ACEITE DIGITAL.</strong> {modo === 'cadastrar'
       ? 'Cadastro inicial: artista define senha e, no primeiro acesso, aceita ou recusa o termo (Cláusula 4.1).'
       : 'Convite a artista existente: vinculação só se efetiva após aceite eletrônico expresso, registrado com data, hora e IP (Cláusula 4.2).'}</p>
     <p><strong>REVOGAÇÃO.</strong> O artista pode desfazer o vínculo a qualquer tempo em seu painel; contratos já assinados permanecem válidos até seu termo.</p>
     <p><strong>RESPONSABILIDADE.</strong> A Gravan atua como plataforma intermediária e não responde por divergências entre editora e artista quanto à titularidade dos direitos.</p>
     <p style={{ fontSize: 11, color: '#666' }}>Texto integral salvo de forma imutável no convite após o envio.</p>
   </div>
 )
}

// ── pequenos componentes/estilos ─────────────────────────
function Tab({ ativa, onClick, children, primary }) {
 return (
   <button type="button" onClick={onClick}
     style={{
       padding: '10px 14px', border: 'none', cursor: 'pointer',
       background: 'transparent',
       borderBottom: ativa ? '2px solid var(--brand)' : '2px solid transparent',
       color: ativa ? 'var(--brand)' : (primary ? 'var(--text-primary)' : 'var(--text-muted)'),
       fontSize: 13, fontWeight: 600, fontFamily: 'inherit',
     }}>{children}</button>
 )
}

const card    = { border: '1px solid var(--border)', borderRadius: 12, padding: 16, marginBottom: 24, background: 'var(--surface)' }
const empty   = { padding: 40, border: '1px dashed var(--border)', borderRadius: 12, textAlign: 'center', color: 'var(--text-muted)' }
const alertOk = { padding: 12, background: 'rgba(34,197,94,.1)',  border: '1px solid #22c55e', borderRadius: 8, marginBottom: 16, fontSize: 13, color: '#16a34a' }
const alertErr= { padding: 12, background: 'rgba(239,68,68,.1)',  border: '1px solid #ef4444', borderRadius: 8, marginBottom: 16, fontSize: 13, color: '#c0392b' }
const th      = { textAlign: 'left', padding: '10px 14px', fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 0.5 }
const td      = { padding: '12px 14px', verticalAlign: 'middle' }
const badgeOk    = { fontSize: 11, padding: '2px 8px', background: 'rgba(34,197,94,.15)',  color: '#16a34a', borderRadius: 4 }
const badgeWarn  = { fontSize: 11, padding: '2px 8px', background: 'rgba(245,158,11,.15)', color: '#d97706', borderRadius: 4 }
const badgeErr   = { fontSize: 11, padding: '2px 8px', background: 'rgba(239,68,68,.15)',  color: '#c0392b', borderRadius: 4 }
const badgeMuted = { fontSize: 11, padding: '2px 8px', background: 'rgba(0,0,0,.06)',      color: '#666',    borderRadius: 4 }
