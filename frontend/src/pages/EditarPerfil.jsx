import React, { useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { useTheme } from '../contexts/ThemeContext'
import { supabase } from '../lib/supabase'
import ImageCropper from '../components/ImageCropper'
import PushToggle from '../components/PushToggle'
import { IconSun, IconMoon } from '../components/Icons'

const MAX_AVATAR = 2 * 1024 * 1024 // 2 MB
const MAX_CAPA = 5 * 1024 * 1024 // 5 MB

export default function EditarPerfil() {
 const { perfil, refreshPerfil } = useAuth()
 const { theme, toggle: toggleTheme } = useTheme()
 const navigate = useNavigate()
 const avatarFileRef = useRef(null)
 const capaFileRef = useRef(null)

 const [form, setForm] = useState({
 nome: perfil?.nome ?? '',
 nome_artistico: perfil?.nome_artistico ?? '',
 telefone: perfil?.telefone ?? '',
 bio: perfil?.bio ?? '',
 })

 const [avatarPreview, setAvatarPreview] = useState(perfil?.avatar_url ?? null)
 const [avatarBlob, setAvatarBlob] = useState(null)
 const [avatarErro, setAvatarErro] = useState('')

 const [capaPreview, setCapaPreview] = useState(perfil?.capa_url ?? null)
 const [capaBlob, setCapaBlob] = useState(null)
 const [capaErro, setCapaErro] = useState('')

 // Cropper state
 const [cropSrc, setCropSrc] = useState(null)
 const [cropMode, setCropMode] = useState(null) // 'avatar' | 'capa'

 const [salvando, setSalvando] = useState(false)
 const [erro, setErro] = useState('')
 const [sucesso, setSucesso] = useState('')

 // Trocar senha
 const [senhaEnviando, setSenhaEnviando] = useState(false)
 const [senhaMsg, setSenhaMsg] = useState('')
 const [senhaErro, setSenhaErro] = useState('')

 async function enviarLinkTrocaSenha() {
  if (!perfil?.email) {
   setSenhaErro('Não foi possível identificar o e-mail da sua conta.')
   return
  }
  if (!confirm(`Enviaremos um link para ${perfil.email} com instruções para alterar sua senha. Continuar?`)) return
  setSenhaEnviando(true); setSenhaErro(''); setSenhaMsg('')
  try {
   const { error } = await supabase.auth.resetPasswordForEmail(perfil.email, {
    redirectTo: `${window.location.origin}/redefinir-senha`,
   })
   if (error) throw error
   setSenhaMsg(`Link enviado para ${perfil.email}. Verifique sua caixa de entrada (e a pasta de spam).`)
  } catch (e) {
   setSenhaErro(e.message || 'Não foi possível enviar o link agora. Tente novamente.')
  } finally { setSenhaEnviando(false) }
 }

 function handleChange(e) {
 setForm(p => ({ ...p, [e.target.name]: e.target.value }))
 }

 function abrirArquivo(e, tipo) {
 const setErr = tipo === 'avatar' ? setAvatarErro : setCapaErro
 setErr('')
 const file = e.target.files?.[0]
 e.target.value = ''
 if (!file) return
 if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) {
 setErr('Apenas JPG, PNG ou WebP são aceitos.')
 return
 }
 const max = tipo === 'avatar' ? MAX_AVATAR : MAX_CAPA
 if (file.size > max) {
 setErr(`Imagem excede ${max / (1024 * 1024)} MB.`)
 return
 }
 setCropSrc(URL.createObjectURL(file))
 setCropMode(tipo)
 }

 function aplicarCrop(blob) {
 const url = URL.createObjectURL(blob)
 if (cropMode === 'avatar') {
 setAvatarBlob(blob)
 setAvatarPreview(url)
 } else if (cropMode === 'capa') {
 setCapaBlob(blob)
 setCapaPreview(url)
 }
 setCropSrc(null)
 setCropMode(null)
 }

 async function uploadImagem(bucket, blob) {
 const path = `${perfil.id}/${bucket}.jpg`
 const { error: upErr } = await supabase.storage
 .from(bucket)
 .upload(path, blob, { upsert: true, contentType: 'image/jpeg' })
 if (upErr) throw upErr
 const { data } = supabase.storage.from(bucket).getPublicUrl(path)
 return data.publicUrl + '?t=' + Date.now()
 }

 async function salvar(e) {
 e.preventDefault()
 setErro(''); setSucesso('')

 // Validações obrigatórias
 if (!avatarPreview) {
 setErro('Adicione uma foto de perfil para continuar.')
 return
 }
 if (!capaPreview) {
 setErro('Adicione uma foto de capa para continuar.')
 return
 }

 setSalvando(true)
 try {
 let avatar_url = perfil?.avatar_url ?? null
 let capa_url = perfil?.capa_url ?? null

 if (avatarBlob) avatar_url = await uploadImagem('avatares', avatarBlob)
 if (capaBlob) capa_url = await uploadImagem('capas', capaBlob)

 const { error: dbErr } = await supabase
 .from('perfis')
 .update({
 nome: form.nome.trim(),
 nome_artistico: form.nome_artistico.trim() || null,
 telefone: form.telefone.trim() || null,
 bio: form.bio.trim() || null,
 avatar_url,
 capa_url,
 })
 .eq('id', perfil.id)
 if (dbErr) throw dbErr

 await refreshPerfil()
 setSucesso('Perfil atualizado com sucesso!')
 setAvatarBlob(null)
 setCapaBlob(null)
 } catch (err) {
 setErro(err.message ?? 'Erro ao salvar perfil.')
 } finally {
 setSalvando(false)
 }
 }

 const iniciais = form.nome?.split(' ').slice(0, 2).map(n => n[0]).join('').toUpperCase() || '?'

 return (
 <div style={{ maxWidth: 720, padding: '24px 20px', margin: '0 auto' }}>
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
 {/* Capa + Avatar (estilo Spotify) */}
 <div className="card" style={{ marginBottom: 20, padding: 0, overflow: 'hidden' }}>
 <div
 onClick={() => capaFileRef.current?.click()}
 style={{
 position: 'relative',
 height: 180,
 background: capaPreview
 ? `url(${capaPreview}) center/cover no-repeat`
 : 'linear-gradient(135deg, #083257, #09090B)',
 cursor: 'pointer',
 display: 'flex', alignItems: 'center', justifyContent: 'center',
 }}
 >
 {!capaPreview && (
 <div style={{ color: '#fff', textAlign: 'center', padding: 20 }}>
 <div style={{ fontSize: 28 }}></div>
 <div style={{ fontSize: 13, fontWeight: 700, marginTop: 4 }}>Adicionar foto de capa *</div>
 <div style={{ fontSize: 11, opacity: 0.8 }}>Recomendado: 1500×500 px · JPG, PNG ou WebP · Máx. 5 MB</div>
 </div>
 )}
 {capaPreview && (
 <button
 type="button"
 onClick={e => { e.stopPropagation(); capaFileRef.current?.click() }}
 style={{
 position: 'absolute', bottom: 12, right: 12,
 background: 'rgba(0,0,0,.6)', color: '#fff',
 border: 'none', borderRadius: 99, padding: '6px 14px',
 fontSize: 12, fontWeight: 600, cursor: 'pointer',
 }}
 >
 Trocar capa
 </button>
 )}
 <input
 ref={capaFileRef}
 type="file"
 accept="image/jpeg,image/png,image/webp"
 style={{ display: 'none' }}
 onChange={e => abrirArquivo(e, 'capa')}
 />
 </div>

 <div style={{ padding: 20, display: 'flex', alignItems: 'flex-end', gap: 16 }}>
 <div
 onClick={() => avatarFileRef.current?.click()}
 style={{
 width: 100, height: 100, borderRadius: '50%',
 background: avatarPreview ? '#fff' : 'var(--brand-light, #FCE7E7)',
 overflow: 'hidden', flexShrink: 0, cursor: 'pointer',
 border: '4px solid #fff',
 boxShadow: '0 4px 12px rgba(0,0,0,.2)',
 display: 'flex', alignItems: 'center', justifyContent: 'center',
 marginTop: -50,
 }}
 >
 {avatarPreview
 ? <img src={avatarPreview} alt="Avatar" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
 : <div style={{ fontSize: 30, fontWeight: 700, color: 'var(--brand, #0C447C)' }}>{iniciais}</div>
 }
 </div>
 <div style={{ flex: 1, minWidth: 0 }}>
 <input
 ref={avatarFileRef}
 type="file"
 accept="image/jpeg,image/png,image/webp"
 style={{ display: 'none' }}
 onChange={e => abrirArquivo(e, 'avatar')}
 />
 <button
 type="button"
 className="btn btn-secondary btn-sm"
 onClick={() => avatarFileRef.current?.click()}
 >
 {avatarPreview ? 'Trocar foto' : 'Adicionar foto de perfil *'}
 </button>
 <p style={{ fontSize: 12, color: 'var(--text-muted, #71717A)', marginTop: 6 }}>
 JPG, PNG ou WebP · Máx. 2 MB · Você poderá ajustar o enquadramento
 </p>
 </div>
 </div>

 {(avatarErro || capaErro) && (
 <div style={{ padding: '0 20px 14px' }}>
 {avatarErro && <p style={{ fontSize: 12, color: 'var(--error, #c0392b)', margin: 0 }}>Foto de perfil: {avatarErro}</p>}
 {capaErro && <p style={{ fontSize: 12, color: 'var(--error, #c0392b)', margin: '4px 0 0' }}>Capa: {capaErro}</p>}
 </div>
 )}
 </div>

 {/* Dados */}
 <div className="card" style={{ marginBottom: 20 }}>
 <h2 style={{ fontSize: 15, fontWeight: 600, marginBottom: 16 }}>Informações pessoais</h2>

 <div className="form-group">
 <label className="form-label">Nome completo *</label>
 <input className="input" name="nome" value={form.nome} onChange={handleChange} required maxLength={120} />
 </div>

 <div className="form-group">
 <label className="form-label">Nome artístico {perfil?.nome_artistico && <span style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 400 }}> permanente</span>}</label>
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
 O nome artístico é permanente. Para alterar, entre em contato com o suporte em <strong>contatogravan@gmail.com</strong>.
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

 {/* Notificações push */}
 <div className="card" style={{ marginBottom: 20 }}>
 <h2 style={{ fontSize: 15, fontWeight: 600, marginBottom: 16 }}>Notificações</h2>
 <PushToggle />

 <div style={{ height: 1, background: 'var(--border)', margin: '16px 0' }} />

 <h2 style={{ fontSize: 15, fontWeight: 600, marginBottom: 4 }}>Aparência</h2>
 <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 14 }}>
   Escolha entre tema claro e escuro para o app.
 </p>
 <button
   type="button"
   onClick={toggleTheme}
   aria-label={theme === 'dark' ? 'Mudar para tema claro' : 'Mudar para tema escuro'}
   style={{
     display: 'flex', alignItems: 'center', gap: 12,
     width: '100%', padding: '12px 14px',
     background: 'var(--surface-2)',
     border: '1px solid var(--border)',
     borderRadius: 12,
     cursor: 'pointer',
     color: 'var(--text-primary)',
     fontFamily: 'inherit',
     textAlign: 'left',
     transition: 'background .15s, border-color .15s',
   }}
 >
   <span style={{
     width: 36, height: 36, borderRadius: '50%',
     display: 'flex', alignItems: 'center', justifyContent: 'center',
     background: 'var(--surface)', border: '1px solid var(--border)',
     color: 'var(--brand)',
   }}>
     {theme === 'dark' ? <IconSun size={18} /> : <IconMoon size={18} />}
   </span>
   <span style={{ flex: 1 }}>
     <div style={{ fontSize: 14, fontWeight: 600 }}>
       Modo {theme === 'dark' ? 'escuro' : 'claro'}
     </div>
     <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>
       Toque para mudar para o modo {theme === 'dark' ? 'claro' : 'escuro'}.
     </div>
   </span>
   <span style={{
     padding: '4px 10px', borderRadius: 999,
     background: 'var(--brand-light)', color: 'var(--brand)',
     fontSize: 11, fontWeight: 700, letterSpacing: .5,
     textTransform: 'uppercase',
   }}>
     {theme === 'dark' ? 'Escuro' : 'Claro'}
   </span>
 </button>
 </div>

 {/* Segurança – trocar senha */}
 <div className="card" style={{ marginBottom: 20 }}>
 <h2 style={{ fontSize: 15, fontWeight: 600, marginBottom: 8 }}>Segurança</h2>
 <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 14 }}>
 Para alterar sua senha, enviaremos um link seguro para o e-mail cadastrado. No link você confirmará seu e-mail e definirá a nova senha.
 </p>
 {senhaMsg && (
 <div style={{ background: 'var(--success-bg)', border: '1px solid var(--success)', color: 'var(--success)', padding: '10px 12px', borderRadius: 8, fontSize: 13, marginBottom: 12 }}>
 ✓ {senhaMsg}
 </div>
 )}
 {senhaErro && (
 <div style={{ background: 'var(--error-bg)', border: '1px solid var(--error)', color: 'var(--error)', padding: '10px 12px', borderRadius: 8, fontSize: 13, marginBottom: 12 }}>
 {senhaErro}
 </div>
 )}
 <button
 type="button"
 className="btn btn-secondary"
 onClick={enviarLinkTrocaSenha}
 disabled={senhaEnviando}
 >
 {senhaEnviando ? 'Enviando link…' : '🔑 Trocar senha por e-mail'}
 </button>
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
 <div style={{ color: 'var(--text-muted)', marginBottom: 2 }}>Plano</div>
 <div style={{ fontWeight: 500 }}>{(perfil?.plano || 'STARTER') === 'PRO' ? 'PRO' : 'Free'}</div>
 </div>
 <div>
 <div style={{ color: 'var(--text-muted)', marginBottom: 2 }}>Membro desde</div>
 <div style={{ fontWeight: 500 }}>{new Date(perfil?.created_at).toLocaleDateString('pt-BR')}</div>
 </div>
 </div>
 </div>

 {erro && <div className="card" style={{ background: 'var(--error-bg)', border: '1px solid var(--error)', marginBottom: 16 }}><p style={{ color: 'var(--error)', fontSize: 14 }}>{erro}</p></div>}
 {sucesso && <div className="card" style={{ background: 'var(--success-bg)', border: '1px solid var(--success)', marginBottom: 16 }}><p style={{ color: 'var(--success)', fontSize: 14 }}>✓ {sucesso}</p></div>}

 <div style={{ display: 'flex', gap: 12 }}>
 <button type="submit" className="btn btn-primary" disabled={salvando}>
 {salvando ? 'Salvando…' : '✓ Salvar alterações'}
 </button>
 <button type="button" className="btn btn-ghost" onClick={() => navigate(-1)}>Cancelar</button>
 </div>
 </form>

 {cropSrc && (
 <ImageCropper
 src={cropSrc}
 aspect={cropMode === 'avatar' ? 1 : 3}
 shape={cropMode === 'avatar' ? 'circle' : 'rect'}
 outputWidth={cropMode === 'avatar' ? 600 : 1500}
 title={cropMode === 'avatar' ? 'Ajustar foto de perfil' : 'Ajustar foto de capa'}
 onCancel={() => { setCropSrc(null); setCropMode(null) }}
 onConfirm={aplicarCrop}
 />
 )}
 </div>
 )
}
