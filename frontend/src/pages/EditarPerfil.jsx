import React, { useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { supabase } from '../lib/supabase'

const MAX_AVATAR = 2 * 1024 * 1024 // 2 MB

export default function EditarPerfil() {
  const { perfil, refreshPerfil } = useAuth()
  const navigate = useNavigate()
  const fileRef  = useRef(null)

  const [form, setForm] = useState({
    nome:           perfil?.nome           ?? '',
    nome_artistico: perfil?.nome_artistico ?? '',
    telefone:       perfil?.telefone       ?? '',
    bio:            perfil?.bio            ?? '',
  })
  const [avatarPreview, setAvatarPreview] = useState(perfil?.avatar_url ?? null)
  const [avatarFile,    setAvatarFile]    = useState(null)
  const [avatarErro,    setAvatarErro]    = useState('')
  const [salvando,      setSalvando]      = useState(false)
  const [erro,          setErro]          = useState('')
  const [sucesso,       setSucesso]       = useState('')

  function handleChange(e) {
    setForm(p => ({ ...p, [e.target.name]: e.target.value }))
  }

  function handleAvatar(e) {
    setAvatarErro('')
    const file = e.target.files?.[0]
    if (!file) return
    if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) {
      setAvatarErro('Apenas JPG, PNG ou WebP são aceitos.')
      return
    }
    if (file.size > MAX_AVATAR) {
      setAvatarErro('Imagem excede 2 MB.')
      return
    }
    setAvatarFile(file)
    setAvatarPreview(URL.createObjectURL(file))
  }

  async function salvar(e) {
    e.preventDefault()
    setErro(''); setSucesso(''); setSalvando(true)

    try {
      let avatar_url = perfil?.avatar_url ?? null

      // 1. Upload do avatar se houver novo arquivo
      if (avatarFile) {
        const ext  = avatarFile.name.split('.').pop()
        const path = `${perfil.id}/avatar.${ext}`
        const { error: upErr } = await supabase.storage
          .from('avatares')
          .upload(path, avatarFile, { upsert: true, contentType: avatarFile.type })
        if (upErr) throw upErr

        const { data } = supabase.storage.from('avatares').getPublicUrl(path)
        avatar_url = data.publicUrl + '?t=' + Date.now() // cache-bust
      }

      // 2. Atualizar perfil no banco
      const { error: dbErr } = await supabase
        .from('perfis')
        .update({
          nome:           form.nome.trim(),
          nome_artistico: form.nome_artistico.trim() || null,
          telefone:       form.telefone.trim() || null,
          bio:            form.bio.trim() || null,
          avatar_url,
        })
        .eq('id', perfil.id)
      if (dbErr) throw dbErr

      // 3. Atualizar contexto
      await refreshPerfil()
      setSucesso('Perfil atualizado com sucesso!')
      setAvatarFile(null)
    } catch (err) {
      setErro(err.message ?? 'Erro ao salvar perfil.')
    } finally {
      setSalvando(false)
    }
  }

  const iniciais = form.nome?.split(' ').slice(0, 2).map(n => n[0]).join('').toUpperCase() || '?'

  return (
    <div style={{ maxWidth: 560 }}>
      <div style={{ marginBottom: 28 }}>
        <button
          onClick={() => navigate(-1)}
          style={{ background: 'none', border: 'none', color: 'var(--brand)', cursor: 'pointer', fontSize: 14, padding: 0, marginBottom: 12 }}
        >
          ← Voltar
        </button>
        <h1 style={{ fontSize: 22, fontWeight: 700 }}>Editar perfil</h1>
        <p style={{ color: 'var(--text-muted)', fontSize: 14 }}>Atualize suas informações pessoais</p>
      </div>

      <form onSubmit={salvar}>
        {/* Avatar */}
        <div className="card" style={{ marginBottom: 20, display: 'flex', alignItems: 'center', gap: 20 }}>
          <div
            style={{
              width: 80, height: 80, borderRadius: '50%',
              background: avatarPreview ? 'transparent' : 'var(--brand-light)',
              overflow: 'hidden', flexShrink: 0, cursor: 'pointer',
              border: '3px solid var(--brand-light)',
            }}
            onClick={() => fileRef.current?.click()}
          >
            {avatarPreview
              ? <img src={avatarPreview} alt="Avatar" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
              : <div style={{ width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 26, fontWeight: 700, color: 'var(--brand)' }}>{iniciais}</div>
            }
          </div>
          <div>
            <input ref={fileRef} type="file" accept="image/jpeg,image/png,image/webp" style={{ display: 'none' }} onChange={handleAvatar} />
            <button type="button" className="btn btn-secondary btn-sm" onClick={() => fileRef.current?.click()}>
              📷 Trocar foto
            </button>
            <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 6 }}>JPG, PNG ou WebP · Máx. 2 MB</p>
            {avatarErro && <p style={{ fontSize: 12, color: 'var(--error)', marginTop: 4 }}>{avatarErro}</p>}
          </div>
        </div>

        {/* Dados */}
        <div className="card" style={{ marginBottom: 20 }}>
          <h2 style={{ fontSize: 15, fontWeight: 600, marginBottom: 16 }}>Informações pessoais</h2>

          <div className="form-group">
            <label className="form-label">Nome completo *</label>
            <input className="input" name="nome" value={form.nome} onChange={handleChange} required maxLength={120} />
          </div>

          <div className="form-group">
            <label className="form-label">Nome artístico {perfil?.nome_artistico && <span style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 400 }}>🔒 permanente</span>}</label>
            <input
              className="input"
              name="nome_artistico"
              placeholder="Como você é conhecido no meio musical"
              value={form.nome_artistico}
              onChange={handleChange}
              maxLength={120}
              readOnly={!!perfil?.nome_artistico}
              style={perfil?.nome_artistico ? { background: 'var(--surface-2)', color: 'var(--text-muted)', cursor: 'not-allowed' } : {}}
            />
            {perfil?.nome_artistico && (
              <small style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4, display: 'block' }}>
                O nome artístico é permanente. Para alterar, entre em contato com o suporte em <strong>contatopitch.me@gmail.com</strong>.
              </small>
            )}
          </div>

          <div className="form-group">
            <label className="form-label">Telefone <span style={{ color: 'var(--text-muted)', fontWeight: 400 }}>(opcional)</span></label>
            <input className="input" name="telefone" type="tel" placeholder="(11) 99999-9999" value={form.telefone} onChange={handleChange} maxLength={20} />
          </div>

          <div className="form-group" style={{ marginBottom: 0 }}>
            <label className="form-label">Bio <span style={{ color: 'var(--text-muted)', fontWeight: 400 }}>(opcional)</span></label>
            <textarea className="input" name="bio" placeholder="Fale um pouco sobre você e sua música…" value={form.bio} onChange={handleChange} maxLength={500} style={{ minHeight: 90 }} />
            <span style={{ fontSize: 12, color: 'var(--text-muted)', alignSelf: 'flex-end' }}>
              {form.bio.length}/500
            </span>
          </div>
        </div>

        {/* Info de conta (somente leitura) */}
        <div className="card" style={{ marginBottom: 20, background: 'var(--surface-2)' }}>
          <h2 style={{ fontSize: 15, fontWeight: 600, marginBottom: 12 }}>Informações da conta</h2>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, fontSize: 13 }}>
            <div>
              <div style={{ color: 'var(--text-muted)', marginBottom: 2 }}>Email</div>
              <div style={{ fontWeight: 500 }}>{perfil?.email}</div>
            </div>
            <div>
              <div style={{ color: 'var(--text-muted)', marginBottom: 2 }}>Tipo de conta</div>
              <div style={{ fontWeight: 500, textTransform: 'capitalize' }}>{perfil?.role}</div>
            </div>
            <div>
              <div style={{ color: 'var(--text-muted)', marginBottom: 2 }}>Nível</div>
              <div style={{ fontWeight: 500, textTransform: 'capitalize' }}>{perfil?.nivel}</div>
            </div>
            <div>
              <div style={{ color: 'var(--text-muted)', marginBottom: 2 }}>Membro desde</div>
              <div style={{ fontWeight: 500 }}>{new Date(perfil?.created_at).toLocaleDateString('pt-BR')}</div>
            </div>
          </div>
        </div>

        {erro    && <div className="card" style={{ background: 'var(--error-bg)', border: '1px solid var(--error)', marginBottom: 16 }}><p style={{ color: 'var(--error)', fontSize: 14 }}>{erro}</p></div>}
        {sucesso && <div className="card" style={{ background: 'var(--success-bg)', border: '1px solid var(--success)', marginBottom: 16 }}><p style={{ color: 'var(--success)', fontSize: 14 }}>✓ {sucesso}</p></div>}

        <div style={{ display: 'flex', gap: 12 }}>
          <button type="submit" className="btn btn-primary" disabled={salvando}>
            {salvando ? 'Salvando…' : '✓ Salvar alterações'}
          </button>
          <button type="button" className="btn btn-ghost" onClick={() => navigate(-1)}>Cancelar</button>
        </div>
      </form>
    </div>
  )
}
