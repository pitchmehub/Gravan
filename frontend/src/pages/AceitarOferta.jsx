import React, { useEffect, useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { api } from '../lib/api'
import { useAuth } from '../contexts/AuthContext'

function fmt(cents) {
  return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format((cents ?? 0) / 100)
}

function fmtCNPJ(v) {
  const d = v.replace(/\D/g, '').slice(0, 14)
  if (d.length <= 2) return d
  if (d.length <= 5) return `${d.slice(0,2)}.${d.slice(2)}`
  if (d.length <= 8) return `${d.slice(0,2)}.${d.slice(2,5)}.${d.slice(5)}`
  if (d.length <= 12) return `${d.slice(0,2)}.${d.slice(2,5)}.${d.slice(5,8)}/${d.slice(8)}`
  return `${d.slice(0,2)}.${d.slice(2,5)}.${d.slice(5,8)}/${d.slice(8,12)}-${d.slice(12)}`
}
function fmtCPF(v) {
  const d = v.replace(/\D/g, '').slice(0, 11)
  if (d.length <= 3) return d
  if (d.length <= 6) return `${d.slice(0,3)}.${d.slice(3)}`
  if (d.length <= 9) return `${d.slice(0,3)}.${d.slice(3,6)}.${d.slice(6)}`
  return `${d.slice(0,3)}.${d.slice(3,6)}.${d.slice(6,9)}-${d.slice(9)}`
}

export default function AceitarOferta() {
  const { token } = useParams()
  const navigate = useNavigate()
  const { user, perfil, refreshPerfil, loading: authLoading } = useAuth()

  const [oferta, setOferta]   = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [successMsg, setSuccessMsg] = useState('')

  const [form, setForm] = useState({
    razao_social: '', nome_fantasia: '', cnpj: '',
    telefone: '', responsavel_nome: '', responsavel_cpf: '',
    endereco_rua: '', endereco_numero: '', endereco_compl: '',
    endereco_bairro: '', endereco_cidade: '', endereco_uf: '', endereco_cep: '',
  })
  function set(k, v) { setForm(f => ({ ...f, [k]: v })) }

  useEffect(() => {
    api.get(`/ofertas-licenciamento/por-token/${token}`)
      .then(d => { setOferta(d); if (d?.editora_terceira_nome) set('razao_social', d.editora_terceira_nome) })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [token])

  async function aceitarTudo(e) {
    e?.preventDefault?.()
    setError(''); setSubmitting(true)
    try {
      // 1. Garante perfil PJ — se não existe ainda, cria via cadastro de editora
      if (!perfil?.razao_social) {
        await api.post('/publishers', form)
        await refreshPerfil?.()
      }
      // 2. Vincula a oferta usando o token (gera contrato trilateral)
      await api.post('/publishers/aceitar-oferta', { token })
      setSuccessMsg('Oferta vinculada! Acesse seus contratos para revisar e assinar.')
      setTimeout(() => navigate('/contratos', { replace: true }), 1800)
    } catch (e) {
      setError(e.message); setSubmitting(false)
    }
  }

  if (loading || authLoading) {
    return <div style={{ padding: 40, textAlign: 'center', color: '#71717A' }}>Carregando oferta…</div>
  }

  if (error && !oferta) {
    return (
      <div style={{ maxWidth: 520, margin: '60px auto', padding: 24, background: '#FEF2F2', border: '1px solid #FCA5A5', borderRadius: 12 }}>
        <h2 style={{ color: '#B91C1C', marginBottom: 8 }}>Não foi possível abrir a oferta</h2>
        <p style={{ color: '#7F1D1D', fontSize: 14 }}>{error}</p>
        <p style={{ color: '#7F1D1D', fontSize: 13, marginTop: 12 }}>
          O link pode ter expirado, sido cancelado ou já utilizado.
        </p>
      </div>
    )
  }

  const oTituloObra   = oferta?.obra?.nome      ?? '(obra)'
  const oCompositor   = oferta?.compositor?.nome ?? oferta?.obra?.titular?.nome ?? '—'
  const oComprador    = oferta?.comprador?.nome ?? '—'
  const oValorCents   = oferta?.valor_cents     ?? 0
  const oDeadline     = oferta?.deadline_at ? new Date(oferta.deadline_at) : null

  const inputStyle = { width: '100%', padding: '10px 12px', border: '1px solid var(--border)', borderRadius: 8, fontSize: 14, background: 'var(--surface)' }
  const labelStyle = { fontSize: 12, fontWeight: 600, color: 'var(--text-muted)', marginBottom: 4, display: 'block' }

  return (
    <div style={{ maxWidth: 720, margin: '32px auto', padding: '0 20px' }}>
      <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 12, padding: 24, marginBottom: 24 }}>
        <div style={{ fontSize: 12, color: 'var(--text-muted)', letterSpacing: 1.2, fontWeight: 600 }}>NOVA OFERTA DE LICENCIAMENTO</div>
        <h1 style={{ fontSize: 24, fontWeight: 700, marginTop: 6 }}>{oTituloObra}</h1>
        <div style={{ marginTop: 16, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14, fontSize: 14 }}>
          <div><div style={labelStyle}>COMPOSITOR</div><div>{oCompositor}</div></div>
          <div><div style={labelStyle}>COMPRADOR (INTÉRPRETE)</div><div>{oComprador}</div></div>
          <div><div style={labelStyle}>VALOR DA OFERTA</div><div style={{ fontWeight: 700, color: 'var(--brand)', fontSize: 18 }}>{fmt(oValorCents)}</div></div>
          <div><div style={labelStyle}>PRAZO PARA ACEITE</div>
            <div>{oDeadline ? oDeadline.toLocaleString('pt-BR') : '—'}</div>
          </div>
        </div>
        {oferta?.mensagem && (
          <div style={{ marginTop: 16, padding: 12, background: 'var(--surface-2)', borderRadius: 8 }}>
            <div style={labelStyle}>MENSAGEM DO COMPRADOR</div>
            <div style={{ fontSize: 13, fontStyle: 'italic' }}>"{oferta.mensagem}"</div>
          </div>
        )}
        <div style={{ marginTop: 16, padding: 12, background: '#FEF3C7', border: '1px solid #FCD34D', borderRadius: 8, fontSize: 12, color: '#78350F' }}>
          ⚠ O valor já está autorizado no cartão do comprador (sem cobrança). Ao aceitar e assinar o contrato trilateral,
          o pagamento é capturado e repassado conforme o contrato. Se você não aceitar até o prazo acima, o valor é
          estornado integralmente.
        </div>
      </div>

      {!user ? (
        <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 12, padding: 24, textAlign: 'center' }}>
          <p style={{ marginBottom: 16, fontSize: 14 }}>
            Para aceitar a oferta, faça login ou crie uma conta de Editora.
          </p>
          <Link to={`/login?redirect=/editora/aceitar-oferta/${token}`}
                className="btn btn-primary" style={{ padding: '12px 24px' }}>
            Entrar / criar conta
          </Link>
        </div>
      ) : successMsg ? (
        <div style={{ background: '#ECFDF5', border: '1px solid #6EE7B7', borderRadius: 12, padding: 24, textAlign: 'center', color: '#065F46' }}>
          ✓ {successMsg}
        </div>
      ) : (
        <form onSubmit={aceitarTudo} style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 12, padding: 24 }}>
          {!perfil?.razao_social && (
            <>
              <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 4 }}>Cadastre sua editora</h2>
              <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 16 }}>
                Esses dados constarão no contrato trilateral com a Gravan e o intérprete.
              </p>
              <fieldset style={{ border: '1px solid var(--border)', borderRadius: 12, padding: 16, marginBottom: 12 }}>
                <legend style={{ fontSize: 13, fontWeight: 700, padding: '0 8px' }}>Empresa</legend>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                  <div><label style={labelStyle}>Razão Social *</label>
                    <input style={inputStyle} value={form.razao_social} onChange={e => set('razao_social', e.target.value)} required /></div>
                  <div><label style={labelStyle}>Nome Fantasia *</label>
                    <input style={inputStyle} value={form.nome_fantasia} onChange={e => set('nome_fantasia', e.target.value)} required /></div>
                  <div><label style={labelStyle}>CNPJ *</label>
                    <input style={inputStyle} value={form.cnpj} onChange={e => set('cnpj', fmtCNPJ(e.target.value))} required /></div>
                  <div><label style={labelStyle}>Telefone *</label>
                    <input style={inputStyle} value={form.telefone} onChange={e => set('telefone', e.target.value)} required /></div>
                </div>
              </fieldset>
              <fieldset style={{ border: '1px solid var(--border)', borderRadius: 12, padding: 16, marginBottom: 12 }}>
                <legend style={{ fontSize: 13, fontWeight: 700, padding: '0 8px' }}>Responsável legal</legend>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                  <div><label style={labelStyle}>Nome *</label>
                    <input style={inputStyle} value={form.responsavel_nome} onChange={e => set('responsavel_nome', e.target.value)} required /></div>
                  <div><label style={labelStyle}>CPF *</label>
                    <input style={inputStyle} value={form.responsavel_cpf} onChange={e => set('responsavel_cpf', fmtCPF(e.target.value))} required /></div>
                </div>
              </fieldset>
              <fieldset style={{ border: '1px solid var(--border)', borderRadius: 12, padding: 16, marginBottom: 12 }}>
                <legend style={{ fontSize: 13, fontWeight: 700, padding: '0 8px' }}>Endereço</legend>
                <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 12 }}>
                  <div><label style={labelStyle}>Rua *</label>
                    <input style={inputStyle} value={form.endereco_rua} onChange={e => set('endereco_rua', e.target.value)} required /></div>
                  <div><label style={labelStyle}>Número *</label>
                    <input style={inputStyle} value={form.endereco_numero} onChange={e => set('endereco_numero', e.target.value)} required /></div>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginTop: 12 }}>
                  <div><label style={labelStyle}>Bairro *</label>
                    <input style={inputStyle} value={form.endereco_bairro} onChange={e => set('endereco_bairro', e.target.value)} required /></div>
                  <div><label style={labelStyle}>Complemento</label>
                    <input style={inputStyle} value={form.endereco_compl} onChange={e => set('endereco_compl', e.target.value)} /></div>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr', gap: 12, marginTop: 12 }}>
                  <div><label style={labelStyle}>Cidade *</label>
                    <input style={inputStyle} value={form.endereco_cidade} onChange={e => set('endereco_cidade', e.target.value)} required /></div>
                  <div><label style={labelStyle}>UF *</label>
                    <input style={inputStyle} maxLength={2} value={form.endereco_uf} onChange={e => set('endereco_uf', e.target.value.toUpperCase())} required /></div>
                  <div><label style={labelStyle}>CEP *</label>
                    <input style={inputStyle} value={form.endereco_cep} onChange={e => set('endereco_cep', (v=>{const d=v.replace(/\D/g,'').slice(0,8); return d.length<=5?d:`${d.slice(0,5)}-${d.slice(5)}`})(e.target.value))} required /></div>
                </div>
              </fieldset>
            </>
          )}

          {error && <div style={{ color: '#c0392b', fontSize: 13, marginBottom: 12 }}>⚠ {error}</div>}

          <button type="submit" disabled={submitting}
                  className="btn btn-primary" style={{ padding: '12px 24px', fontSize: 14, fontWeight: 600, width: '100%' }}>
            {submitting ? 'Processando…' : '✓ Aceitar oferta e gerar contrato'}
          </button>
          <p style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 10, textAlign: 'center' }}>
            O contrato trilateral será disponibilizado para você, o compositor e o intérprete assinarem eletronicamente.
          </p>
        </form>
      )}
    </div>
  )
}
