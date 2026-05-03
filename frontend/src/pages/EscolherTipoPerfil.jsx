import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { api } from '../lib/api'
import StepperCadastro from '../components/StepperCadastro'

// Apenas 2 categorias (ARTISTA / EDITORA), apresentadas em cards grandes.
// ARTISTA → role 'compositor'
// EDITORA → role 'publisher'
const TIPOS = [
 {
 id: 'compositor',
 titulo: 'ARTISTA',
 desc: 'Compositor / intérprete. Cadastre obras e receba royalties.',
 icone: '',
 },
 {
 id: 'publisher',
 titulo: 'EDITORA',
 desc: 'Pessoa Jurídica que representa artistas e cuida do catálogo.',
 icone: '',
 },
]

export default function EscolherTipoPerfil() {
 const { refreshPerfil } = useAuth()
 const navigate = useNavigate()
 const [escolhido, setEscolhido] = useState(null)
 const [loading, setLoading] = useState(false)
 const [erro, setErro] = useState('')

 async function confirmar() {
 if (!escolhido) return
 setLoading(true); setErro('')
 try {
 await api.post('/perfis/me/tipo', { role: escolhido })
 // Garante que o cadastro detalhado será exigido em seguida
 try { localStorage.removeItem('gravan_skip_cadastro') } catch {}
 await refreshPerfil?.()
 if (escolhido === 'publisher') navigate('/editora/cadastro', { replace: true })
 else navigate('/perfil/completar', { replace: true })
 } catch (e) {
 setErro(e.message)
 } finally { setLoading(false) }
 }

 return (
 <div style={{
 minHeight: '70vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
 padding: '40px 20px',
 }}>
 <div style={{ maxWidth: 640, width: '100%' }}>
 <StepperCadastro etapa={1} />
 <div style={{
 background: 'var(--surface, #fff)', border: '1px solid var(--border, #E5E7EB)',
 borderRadius: 16, padding: 32, boxShadow: '0 6px 24px rgba(0,0,0,.04)',
 }}>
 <h1 style={{ fontSize: 22, fontWeight: 800, marginBottom: 6, letterSpacing: 0.2 }}>
 Bem-vindo ao GRAVAN
 </h1>
 <p style={{ fontSize: 13, color: 'var(--text-muted, #71717A)', marginBottom: 24 }}>
 Como você vai usar a plataforma? Escolha um perfil para continuar.
 </p>

 <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
 {TIPOS.map(t => (
 <button key={t.id}
 onClick={() => setEscolhido(t.id)}
 data-testid={`tipo-perfil-${t.id}`}
 style={{
 textAlign: 'left', padding: '22px 20px',
 border: `2px solid ${escolhido === t.id ? '#0C447C' : 'var(--border, #E5E7EB)'}`,
 borderRadius: 14,
 background: escolhido === t.id ? 'rgba(12,68,124,.06)' : '#fff',
 cursor: 'pointer', transition: 'all .15s',
 display: 'flex', flexDirection: 'column', gap: 8,
 }}>
 <span style={{ fontSize: 30 }}>{t.icone}</span>
 <span style={{ fontSize: 17, fontWeight: 800, letterSpacing: 0.3 }}>{t.titulo}</span>
 <span style={{ fontSize: 12.5, color: 'var(--text-muted, #71717A)', lineHeight: 1.4 }}>
 {t.desc}
 </span>
 </button>
 ))}
 </div>

 {erro && <div style={{ color: '#c0392b', fontSize: 13, marginTop: 16 }}> {erro}</div>}

 <div style={{ display: 'flex', gap: 10, marginTop: 24, flexWrap: 'wrap' }}>
 <button onClick={confirmar} disabled={!escolhido || loading}
 style={{
 padding: '12px 22px', fontSize: 14, fontWeight: 700,
 background: escolhido ? '#0C447C' : '#E5E7EB',
 color: escolhido ? '#fff' : '#9CA3AF',
 border: 'none', borderRadius: 10,
 cursor: escolhido && !loading ? 'pointer' : 'not-allowed',
 }}>
 {loading ? 'Salvando…' : 'Continuar'}
 </button>
 </div>

 <p style={{ fontSize: 11, color: 'var(--text-muted, #71717A)', marginTop: 16, lineHeight: 1.4 }}>
 Esta escolha é necessária para acessar a plataforma. Você poderá mudá-la
 depois em Editar perfil.
 </p>
 </div>
 </div>
 </div>
 )
}
