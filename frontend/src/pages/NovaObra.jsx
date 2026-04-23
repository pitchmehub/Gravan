import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { api } from '../lib/api'
import { supabase } from '../lib/supabase'
import TermosModal from '../components/TermosModal'
import ContratoEdicaoModal from '../components/ContratoEdicaoModal'

const MAX_BYTES   = 10 * 1024 * 1024
const MAX_AUTORES = 10

export default function NovaObra() {
  const { perfil } = useAuth()
  const navigate   = useNavigate()

  const [nome,      setNome]      = useState('')
  const [letra,     setLetra]     = useState('')
  const [genero,    setGenero]    = useState('')
  const [preco,     setPreco]     = useState('')
  const [audioFile, setAudioFile] = useState(null)
  const [audioError, setAudioError] = useState('')

  const [coautores, setCoautores] = useState([])
  const [buscaCo,   setBuscaCo]   = useState('')
  const [resultCo,  setResultCo]  = useState([])

  const [loading,        setLoading]        = useState(false)
  const [error,          setError]          = useState('')
  const [termosAceitos,  setTermosAceitos]  = useState(false)
  const [contratoAceito, setContratoAceito] = useState(false)
  const [obraEditada,    setObraEditada]    = useState(null)
  const [editoraTNome,     setEditoraTNome]     = useState('')
  const [editoraTEmail,    setEditoraTEmail]    = useState('')
  const [editoraTTelefone, setEditoraTTelefone] = useState('')
  // Status do lookup: 'idle' | 'checking' | 'found' | 'not_found' | 'error'
  const [editoraLookup, setEditoraLookup] = useState({ status: 'idle' })

  async function checarEditoraPorEmail() {
    const email = editoraTEmail.trim().toLowerCase()
    if (!email || !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) {
      setEditoraLookup({ status: 'idle' })
      return
    }
    setEditoraLookup({ status: 'checking' })
    try {
      const { data } = await api.get('/publishers/lookup-by-email', { params: { email } })
      if (data?.found) {
        setEditoraLookup({ status: 'found', data })
        const oficial = data.razao_social || data.nome_fantasia
        if (oficial && (!editoraTNome.trim() || editoraTNome.trim() !== oficial)) {
          setEditoraTNome(oficial)
        }
      } else {
        setEditoraLookup({ status: 'not_found' })
      }
    } catch (err) {
      setEditoraLookup({ status: 'error' })
    }
  }
  const [showTermos,     setShowTermos]     = useState(false)
  const [showContrato,   setShowContrato]   = useState(false)

  useEffect(() => {
    if (perfil && !perfil.cadastro_completo) {
      navigate('/perfil/completar', { replace: true })
    }
  }, [perfil])

  const [buscaErro, setBuscaErro] = useState('')
  const [buscando,  setBuscando]  = useState(false)

  async function buscarCoautorPorEmail() {
    setBuscaErro('')
    const email = buscaCo.trim().toLowerCase()
    if (!email) return
    if (!/^[^@]+@[^@]+\.[^@]+$/.test(email)) { setBuscaErro('Email inválido'); return }
    if (email === perfil?.email?.toLowerCase()) { setBuscaErro('Você já é o titular da obra'); return }
    if (coautores.some(c => c.email?.toLowerCase() === email)) { setBuscaErro('Este coautor já foi adicionado'); return }
    setBuscando(true)
    try {
      const p = await api.get(`/perfis/buscar-por-email?email=${encodeURIComponent(email)}`)
      setCoautores(prev => [...prev, {
        perfil_id: p.id,
        nome: p.nome_artistico || p.nome,
        email: p.email,
        avatar_url: p.avatar_url,
      }])
      setBuscaCo('')
    } catch (e) {
      setBuscaErro(e.message)
    } finally { setBuscando(false) }
  }

  const handleAudio = (e) => {
    const file = e.target.files?.[0]
    setAudioError(''); setAudioFile(null)
    if (!file) return
    if (!file.name.toLowerCase().endsWith('.mp3')) { setAudioError('Apenas arquivos .mp3.'); return }
    if (file.size > MAX_BYTES) { setAudioError('Arquivo excede 10 MB.'); return }
    setAudioFile(file)
  }

  function addCoautor(c) {
    if (coautores.length >= MAX_AUTORES - 1) return
    setCoautores(prev => [...prev, { perfil_id: c.id, nome: c.nome_artistico || c.nome }])
    setBuscaCo(''); setResultCo([])
  }
  function removeCoautor(id) {
    setCoautores(prev => prev.filter(c => c.perfil_id !== id))
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')

    if (!audioFile)    { setError('Selecione um arquivo de áudio.'); return }
    if (!nome.trim())  { setError('Nome da obra é obrigatório.'); return }
    if (!letra.trim()) { setError('Letra da obra é obrigatória.'); return }
    const precoNum = Number(preco)
    const precoMax = perfil?.nivel === 'diamante' ? 10000 : 3000
    if (!preco || precoNum < 500) { setError('Preço mínimo: R$ 500,00.'); return }
    if (precoNum > precoMax) { setError(`Preço máximo para seu nível: R$ ${precoMax.toLocaleString('pt-BR')}`); return }
    if (obraEditada === null) { setError('Responda se a obra já foi editada.'); return }
    if (obraEditada === true) {
      if (!editoraTNome.trim())  { setError('Informe o nome da editora terceira.'); return }
      if (!editoraTEmail.trim()) { setError('Informe o e-mail da editora terceira.'); return }
      if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(editoraTEmail.trim())) { setError('E-mail da editora terceira inválido.'); return }
    }
    if (!termosAceitos)  { setError('Você precisa aceitar os Termos de Uso.'); return }
    if (obraEditada === false && !contratoAceito) { setError('Você precisa assinar o Contrato de Edição.'); return }

    const totalPessoas  = 1 + coautores.length
    const base          = Math.floor(10000 / totalPessoas) / 100
    const splitTitular  = 100 - base * coautores.length
    const coautorias    = [
      { perfil_id: perfil.id, share_pct: Number(splitTitular.toFixed(2)), is_titular: true },
      ...coautores.map(c => ({ perfil_id: c.perfil_id, share_pct: base })),
    ]

    setLoading(true)
    try {
      const form = new FormData()
      form.append('audio',       audioFile)
      form.append('nome',        nome.trim())
      form.append('letra',       letra.trim())
      form.append('genero',      genero.trim())
      form.append('preco_cents', String(Math.round(Number(preco) * 100)))
      form.append('termos_aceitos',  'true')
      form.append('contrato_aceito', obraEditada ? 'false' : 'true')
      form.append('obra_editada',    obraEditada ? 'true' : 'false')
      if (obraEditada) {
        form.append('editora_terceira_nome',     editoraTNome.trim())
        form.append('editora_terceira_email',    editoraTEmail.trim().toLowerCase())
        form.append('editora_terceira_telefone', editoraTTelefone.trim())
      }
      form.append('coautorias',      JSON.stringify(coautorias))

      await api.upload('/obras/', form)

      // Obra cadastrada — vai direto pra lista do usuário.
      // A geração do dossiê agora é feita pelo administrador na aba "Obras".
      navigate('/obras')
    } catch (err) {
      setError(err.message)
    } finally { setLoading(false) }
  }

  return (
    <div style={{ padding: 32, maxWidth: 680 }}>
      <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 4 }}>Nova Obra</h1>
      <p style={{ color: 'var(--text-muted)', fontSize: 14, marginBottom: 28 }}>
        Cadastre sua composição musical na plataforma.
      </p>

      <form onSubmit={handleSubmit}>
        {/* Áudio */}
        <div className="card" style={{ marginBottom: 20 }}>
          <h2 style={{ fontSize: 15, fontWeight: 600, marginBottom: 14 }}>♪ Arquivo de áudio</h2>
          <div className="form-group">
            <label className="form-label">Arquivo MP3 *</label>
            <input type="file" accept=".mp3,audio/mpeg" onChange={handleAudio}
              className="input" style={{ padding: '7px 14px', cursor: 'pointer' }} />
            {audioError && <span style={{ color: 'var(--error)', fontSize: 12 }}>{audioError}</span>}
            {audioFile && <span style={{ color: 'var(--success)', fontSize: 13 }}>
              ✓ {audioFile.name} ({(audioFile.size / 1024 / 1024).toFixed(2)} MB)
            </span>}
            <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>Apenas .mp3 · máximo 10 MB</span>
          </div>
        </div>

        {/* Dados */}
        <div className="card" style={{ marginBottom: 20 }}>
          <h2 style={{ fontSize: 15, fontWeight: 600, marginBottom: 14 }}>♫ Dados da composição</h2>

          <div className="form-group">
            <label className="form-label">Nome da obra *</label>
            <input className="input" placeholder="Ex: Noite de Inverno"
              value={nome} onChange={e => setNome(e.target.value)} maxLength={200} />
          </div>

          <div className="form-group">
            <label className="form-label">Letra completa *</label>
            <textarea className="input" placeholder="Cole aqui a letra completa da composição…"
              value={letra} onChange={e => setLetra(e.target.value)} style={{ minHeight: 180 }} />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
            <div className="form-group">
              <label className="form-label">Gênero</label>
              <input className="input" placeholder="Ex: Sertanejo, MPB…"
                value={genero} onChange={e => setGenero(e.target.value)} maxLength={80} />
            </div>
            <div className="form-group">
              <label className="form-label">Valor da licença (R$) *</label>
              <input className="input" type="number"
                min="500" max={perfil?.nivel === 'diamante' ? 10000 : 3000}
                step="1" placeholder="Ex: 1500"
                value={preco} onChange={e => setPreco(e.target.value)} />
              <small style={{ color: 'var(--text-muted)', fontSize: 11 }}>
                {perfil?.nivel === 'diamante'
                  ? '💎 Nível Diamante: R$ 500 a R$ 10.000'
                  : '🥇 Nível Ouro: R$ 500 a R$ 3.000 (venda 6 obras para desbloquear Diamante)'
                }
              </small>
            </div>
          </div>
        </div>

        {/* Coautores */}
        <div className="card" style={{ marginBottom: 20 }}>
          <h2 style={{ fontSize: 15, fontWeight: 600, marginBottom: 8 }}>◈ Coautores</h2>
          <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 12 }}>
            Adicione os demais compositores que participaram da criação. Os ganhos serão divididos igualmente entre todos.
          </p>

          <div style={{ marginBottom: 12 }}>
            <div style={{
              padding: '8px 12px', background: 'var(--brand-light)', color: 'var(--brand)',
              borderRadius: 8, fontSize: 13, fontWeight: 600, display: 'inline-block',
            }}>
              ✓ {perfil?.nome_artistico || perfil?.nome} (você — titular)
            </div>
          </div>

          {coautores.map(c => (
            <div key={c.perfil_id} style={{
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
              padding: '10px 12px', background: 'var(--surface-2)', borderRadius: 8,
              marginBottom: 8, fontSize: 13,
            }}>
              <div>
                <div><strong>{c.nome}</strong> <span style={{ color: 'var(--text-muted)' }}>— coautor</span></div>
                {c.email && <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{c.email}</div>}
              </div>
              <button type="button" onClick={() => removeCoautor(c.perfil_id)}
                style={{ background: 'none', border: 'none', color: 'var(--error)', cursor: 'pointer', fontSize: 18 }}>×</button>
            </div>
          ))}

          {coautores.length < MAX_AUTORES - 1 && (
            <div style={{ marginTop: 8 }}>
              <div style={{ display: 'flex', gap: 8 }}>
                <input
                  className="input"
                  placeholder="Email do coautor (ex: coautor@email.com)"
                  value={buscaCo}
                  onChange={e => { setBuscaCo(e.target.value); setBuscaErro('') }}
                  onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); buscarCoautorPorEmail() } }}
                  type="email"
                />
                <button type="button" className="btn btn-secondary btn-sm"
                  onClick={buscarCoautorPorEmail} disabled={buscando || !buscaCo.trim()}>
                  {buscando ? '...' : '+ Adicionar'}
                </button>
              </div>
              {buscaErro && <small style={{ color: 'var(--error)', fontSize: 12 }}>{buscaErro}</small>}
              <small style={{ color: 'var(--text-muted)', fontSize: 11, display: 'block', marginTop: 4 }}>
                O coautor precisa ter cadastro na plataforma como compositor.
              </small>
            </div>
          )}
        </div>

        {/* Obra já editada? */}
        <div className="card" style={{ marginBottom: 20 }}>
          <h2 style={{ fontSize: 15, fontWeight: 600, marginBottom: 10 }}>
            ℹ A obra já foi editada por outra editora? *
          </h2>
          <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 14 }}>
            Declare se a composição possui contrato de edição vigente com terceiros.
          </p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <label style={{
              display: 'flex', alignItems: 'center', gap: 10,
              padding: '12px 14px', borderRadius: 8, cursor: 'pointer',
              border: `2px solid ${obraEditada === false ? 'var(--success)' : 'var(--border)'}`,
              background: obraEditada === false ? 'var(--success-bg)' : 'var(--surface)',
            }}>
              <input type="radio" checked={obraEditada === false}
                onChange={() => setObraEditada(false)}
                style={{ accentColor: 'var(--success)' }} />
              <div>
                <div style={{ fontWeight: 600, fontSize: 13 }}>Obra não editada</div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                  A composição está livre e posso assinar o contrato de edição com a Pitche.me
                </div>
              </div>
            </label>

            <label style={{
              display: 'flex', alignItems: 'center', gap: 10,
              padding: '12px 14px', borderRadius: 8, cursor: 'pointer',
              border: `2px solid ${obraEditada === true ? 'var(--error)' : 'var(--border)'}`,
              background: obraEditada === true ? 'var(--error-bg)' : 'var(--surface)',
            }}>
              <input type="radio" checked={obraEditada === true}
                onChange={() => setObraEditada(true)}
                style={{ accentColor: 'var(--error)' }} />
              <div>
                <div style={{ fontWeight: 600, fontSize: 13 }}>Obra já editada por outra editora</div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                  A obra possui contrato de edição ativo com terceiros
                </div>
              </div>
            </label>
          </div>

          {obraEditada === true && (
            <div style={{
              marginTop: 12, padding: 14,
              background: 'var(--surface-2)', border: '1px solid var(--border)',
              borderRadius: 8,
            }}>
              <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 10, lineHeight: 1.5 }}>
                A obra será publicada no catálogo. Quando alguém fizer uma oferta, a editora terceira informada abaixo
                será convidada por e-mail a aceitar a licença em até 72h úteis. Sem o aceite dela, a oferta é cancelada
                automaticamente e o valor estornado ao comprador.
              </div>
              <div style={{ display: 'grid', gap: 10 }}>
                <input className="input" placeholder="Nome / razão social da editora terceira *"
                  value={editoraTNome} onChange={e => setEditoraTNome(e.target.value)} />
                <input
                  className="input"
                  type="email"
                  placeholder="E-mail da editora terceira *"
                  value={editoraTEmail}
                  onChange={e => {
                    setEditoraTEmail(e.target.value)
                    if (editoraLookup.status !== 'idle') setEditoraLookup({ status: 'idle' })
                  }}
                  onBlur={checarEditoraPorEmail}
                />
                {editoraLookup.status === 'checking' && (
                  <div style={{ fontSize: 13, color: '#666' }}>
                    🔎 Verificando se essa editora já tem cadastro…
                  </div>
                )}
                {editoraLookup.status === 'found' && (
                  <div style={{
                    fontSize: 13, padding: '8px 12px', borderRadius: 6,
                    background: '#e8f5e9', color: '#1b5e20',
                    border: '1px solid #a5d6a7'
                  }}>
                    ✓ Editora identificada na plataforma:{' '}
                    <strong>{editoraLookup.data.razao_social || editoraLookup.data.nome_fantasia}</strong>.
                    Quando alguém licenciar esta obra, ela receberá uma notificação
                    interna (e o e-mail como backup) para aceitar o contrato.
                  </div>
                )}
                {editoraLookup.status === 'not_found' && (
                  <div style={{
                    fontSize: 13, padding: '8px 12px', borderRadius: 6,
                    background: '#fff8e1', color: '#5d4037',
                    border: '1px solid #ffe082'
                  }}>
                    ℹ️ Esta editora ainda não tem cadastro na Pitch.me. Quando alguém
                    licenciar, ela receberá um e-mail com link único para se cadastrar
                    e assinar o contrato (prazo de 72 horas úteis).
                  </div>
                )}
                {editoraLookup.status === 'error' && (
                  <div style={{ fontSize: 13, color: '#c62828' }}>
                    Não consegui verificar agora — você pode prosseguir mesmo assim.
                  </div>
                )}
                <input className="input" placeholder="Telefone (opcional)"
                  value={editoraTTelefone} onChange={e => setEditoraTTelefone(e.target.value)} />
              </div>
            </div>
          )}
        </div>

        {/* Aceite de Contrato de Edição */}
        {obraEditada === false && (
          <div className="card" style={{ marginBottom: 16, background: 'var(--surface-2)' }}>
            <label style={{ display: 'flex', alignItems: 'flex-start', gap: 10, cursor: 'pointer' }}>
              <input type="checkbox" checked={contratoAceito}
                onChange={e => setContratoAceito(e.target.checked)}
                style={{ marginTop: 3, width: 18, height: 18, accentColor: 'var(--brand)', cursor: 'pointer', flexShrink: 0 }} />
              <span style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.6 }}>
                Li e assino eletronicamente o{' '}
                <button type="button" onClick={e => { e.preventDefault(); setShowContrato(true) }}
                  style={{ background: 'none', border: 'none', color: 'var(--brand)', textDecoration: 'underline', cursor: 'pointer', padding: 0, fontSize: 13, fontWeight: 600 }}>
                  Contrato de Edição Musical
                </button>
                {' '}com meus dados cadastrais e a data de hoje.
              </span>
            </label>
          </div>
        )}

        {/* Aceite de Termos */}
        <div className="card" style={{ marginBottom: 20, background: 'var(--surface-2)' }}>
          <label style={{ display: 'flex', alignItems: 'flex-start', gap: 10, cursor: 'pointer' }}>
            <input type="checkbox" checked={termosAceitos}
              onChange={e => setTermosAceitos(e.target.checked)}
              style={{ marginTop: 3, width: 18, height: 18, accentColor: 'var(--brand)', cursor: 'pointer', flexShrink: 0 }} />
            <span style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.6 }}>
              Li e aceito os{' '}
              <button type="button" onClick={e => { e.preventDefault(); setShowTermos(true) }}
                style={{ background: 'none', border: 'none', color: 'var(--brand)', textDecoration: 'underline', cursor: 'pointer', padding: 0, fontSize: 13, fontWeight: 600 }}>
                Termos de Uso e Cessão de Direitos
              </button>
              {' '}da plataforma.
            </span>
          </label>
        </div>

        {error && (
          <div className="card" style={{ background: 'var(--error-bg)', border: '1px solid var(--error)', marginBottom: 16 }}>
            <p style={{ color: 'var(--error)', fontSize: 14 }}>{error}</p>
          </div>
        )}

        <div style={{ display: 'flex', gap: 12 }}>
          <button type="submit" className="btn btn-primary"
            disabled={loading || !termosAceitos || obraEditada === null || (obraEditada === false && !contratoAceito) || (obraEditada === true && (!editoraTNome.trim() || !editoraTEmail.trim()))}>
            {loading ? 'Salvando…' : '✓ Cadastrar obra'}
          </button>
          <button type="button" className="btn btn-ghost" onClick={() => navigate('/obras')}>
            Cancelar
          </button>
        </div>
      </form>

      {showTermos   && <TermosModal onClose={() => setShowTermos(false)} />}
      {showContrato && <ContratoEdicaoModal onClose={() => setShowContrato(false)} />}
    </div>
  )
}
