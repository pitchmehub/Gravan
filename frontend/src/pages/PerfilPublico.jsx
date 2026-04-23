import React, { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { supabase } from '../lib/supabase'
import { api } from '../lib/api'

function fmt(cents) {
  return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' })
    .format((cents ?? 0) / 100)
}

const GRADIENTS = [
  'linear-gradient(135deg,#BE123C,#09090B)',
  'linear-gradient(135deg,#0F6E56,#1D9E75)',
  'linear-gradient(135deg,#854F0B,#EF9F27)',
  'linear-gradient(135deg,#185FA5,#378ADD)',
  'linear-gradient(135deg,#993556,#D4537E)',
  'linear-gradient(135deg,#09090B,#3F3F46)',
]
const grad = id => GRADIENTS[(id?.charCodeAt(0) ?? 0) % GRADIENTS.length]

export default function PerfilPublico() {
  const { perfilId } = useParams()
  const navigate = useNavigate()
  const { perfil: meuPerfil } = useAuth()
  const isAdmin = meuPerfil?.role === 'administrador'

  const [perfil, setPerfil] = useState(null)
  const [obras, setObras] = useState([])
  const [erro, setErro] = useState('')
  const [loading, setLoading] = useState(true)
  const [atualizadoEm, setAtualizadoEm] = useState(null)

  // Modal "Visualizar como administrador"
  const [adminOpen, setAdminOpen] = useState(false)
  const [adminData, setAdminData] = useState(null)
  const [adminLoad, setAdminLoad] = useState(false)
  const [adminErro, setAdminErro] = useState('')
  const [adminAtualizadoEm, setAdminAtualizadoEm] = useState(null)

  // Estado da exclusão definitiva
  const [excluirOpen, setExcluirOpen] = useState(false)
  const [excluirTexto, setExcluirTexto] = useState('')
  const [excluindo, setExcluindo] = useState(false)
  const [excluirErro, setExcluirErro] = useState('')
  const [excluirResult, setExcluirResult] = useState(null)

  async function carregarPerfil({ silencioso = false } = {}) {
    if (!silencioso) setLoading(true)
    setErro('')
    try {
      const { data: p, error: ePerfil } = await supabase
        .from('perfis')
        .select('id, nome, nome_artistico, avatar_url, nivel, role, bio')
        .eq('id', perfilId)
        .maybeSingle()
      if (ePerfil) throw new Error(ePerfil.message)
      if (!p) throw new Error('Perfil não encontrado')

      const { data: coa } = await supabase
        .from('coautorias')
        .select('obra_id, is_titular, share_pct, obras(id, nome, genero, preco_cents, audio_path, status, titular_id, perfis!titular_id(nome, nivel))')
        .eq('perfil_id', perfilId)
        .limit(60)

      const lista = (coa ?? [])
        .filter(c => c.obras?.status === 'publicada')
        .map(c => ({
          ...c.obras,
          titular_nome: c.obras?.perfis?.nome,
          titular_nivel: c.obras?.perfis?.nivel,
        }))

      setPerfil(p)
      setObras(lista)
      setAtualizadoEm(new Date())
    } catch (e) {
      setErro(e.message)
    } finally {
      if (!silencioso) setLoading(false)
    }
  }

  // Carrega ao entrar na rota e sempre que o ID mudar
  useEffect(() => { carregarPerfil() /* eslint-disable-next-line */ }, [perfilId])

  // Recarrega ao voltar para a aba/janela (garante números atualizados)
  useEffect(() => {
    function onFocus() { carregarPerfil({ silencioso: true }) }
    function onVisible() { if (document.visibilityState === 'visible') carregarPerfil({ silencioso: true }) }
    window.addEventListener('focus', onFocus)
    document.addEventListener('visibilitychange', onVisible)
    return () => {
      window.removeEventListener('focus', onFocus)
      document.removeEventListener('visibilitychange', onVisible)
    }
    // eslint-disable-next-line
  }, [perfilId])

  async function carregarVisaoAdmin() {
    setAdminLoad(true); setAdminErro('')
    try {
      // Query string com timestamp evita cache do navegador/proxy
      const data = await api.get(`/admin/perfis/${perfilId}/visao?_=${Date.now()}`)
      setAdminData(data)
      setAdminAtualizadoEm(new Date())
    } catch (e) {
      setAdminErro(e.message)
    } finally {
      setAdminLoad(false)
    }
  }

  async function abrirVisaoAdmin() {
    setAdminOpen(true)
    setAdminData(null) // sempre recarrega ao abrir
    await carregarVisaoAdmin()
  }

  if (loading) return <div style={{ padding: 32, color: '#71717A' }}>Carregando…</div>
  if (erro)    return <div style={{ padding: 32, color: '#c0392b' }}>⚠ {erro}</div>
  if (!perfil) return null

  const iniciais = (perfil.nome || '?').split(' ').slice(0, 2).map(n => n[0]).join('').toUpperCase()

  return (
    <div style={{ padding: '32px 20px', maxWidth: 1100, margin: '0 auto' }}>
      <button onClick={() => navigate(-1)}
              style={{ background: 'none', border: 'none', color: 'var(--brand, #E11D48)', cursor: 'pointer', fontSize: 13, marginBottom: 16 }}>
        ← Voltar
      </button>

      <div style={{ display: 'flex', alignItems: 'center', gap: 20, marginBottom: 24, flexWrap: 'wrap' }}>
        <div style={{
          width: 96, height: 96, borderRadius: '50%',
          background: grad(perfil.id), color: '#fff',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 32, fontWeight: 700, overflow: 'hidden',
        }}>
          {perfil.avatar_url
            ? <img src={perfil.avatar_url} alt={perfil.nome} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
            : iniciais}
        </div>
        <div style={{ flex: 1, minWidth: 220 }}>
          <h1 style={{ fontSize: 24, fontWeight: 800, margin: 0 }}>
            {perfil.nome_artistico || perfil.nome}
          </h1>
          {perfil.nome_artistico && perfil.nome_artistico !== perfil.nome && (
            <div style={{ fontSize: 13, color: 'var(--text-muted, #71717A)', marginTop: 2 }}>{perfil.nome}</div>
          )}
          <div style={{ fontSize: 12, color: 'var(--text-muted, #71717A)', marginTop: 6 }}>
            {perfil.role === 'publisher' ? 'Editora' : perfil.role === 'compositor' ? 'Artista' : perfil.role}
            {perfil.nivel && ` · ${perfil.nivel}`}
          </div>
          {perfil.bio && <p style={{ fontSize: 13, color: '#3F3F46', marginTop: 10, maxWidth: 560 }}>{perfil.bio}</p>}
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 6, alignItems: 'flex-end' }}>
          {isAdmin && (
            <button onClick={abrirVisaoAdmin}
                    data-testid="btn-visualizar-como-admin"
                    style={{
                      padding: '10px 18px', fontSize: 13, fontWeight: 700,
                      background: '#09090B', color: '#fff',
                      border: '1px solid #09090B', borderRadius: 10, cursor: 'pointer',
                    }}>
              👑 Visualizar como administrador
            </button>
          )}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 11, color: '#71717A' }}>
            {atualizadoEm && <span>Atualizado às {atualizadoEm.toLocaleTimeString('pt-BR')}</span>}
            <button onClick={() => carregarPerfil({ silencioso: true })}
                    title="Atualizar dados"
                    style={{
                      background: 'transparent', border: '1px solid #E5E7EB', borderRadius: 6,
                      padding: '4px 8px', cursor: 'pointer', fontSize: 11, color: '#71717A',
                    }}>
              ↻ Atualizar
            </button>
          </div>
        </div>
      </div>

      <h2 style={{ fontSize: 16, fontWeight: 700, marginBottom: 12 }}>
        Obras publicadas ({obras.length})
      </h2>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12 }}>
        {obras.map(o => (
          <div key={o.id}
               onClick={() => navigate(`/comprar/${o.id}`)}
               style={{
                 border: '1px solid var(--border, #E5E7EB)', borderRadius: 12,
                 overflow: 'hidden', cursor: 'pointer', background: '#fff',
               }}>
            <div style={{ height: 120, background: grad(o.id), color: '#fff',
                          display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 36 }}>♪</div>
            <div style={{ padding: 12 }}>
              <div style={{ fontSize: 14, fontWeight: 700 }}>{o.nome}</div>
              <div style={{ fontSize: 12, color: 'var(--text-muted, #71717A)' }}>{o.genero || '—'}</div>
              <div style={{ fontSize: 13, fontWeight: 700, marginTop: 6, color: '#E11D48' }}>{fmt(o.preco_cents)}</div>
            </div>
          </div>
        ))}
        {obras.length === 0 && (
          <div style={{ gridColumn: '1 / -1', padding: 24, color: 'var(--text-muted, #71717A)', fontSize: 13 }}>
            Nenhuma obra publicada ainda.
          </div>
        )}
      </div>

      {adminOpen && (
        <div onClick={e => { if (e.target === e.currentTarget) setAdminOpen(false) }}
             style={{
               position: 'fixed', inset: 0, background: 'rgba(0,0,0,.5)',
               display: 'flex', alignItems: 'center', justifyContent: 'center',
               zIndex: 1000, padding: 20,
             }}>
          <div style={{
            background: '#fff', borderRadius: 14, maxWidth: 720, width: '100%',
            maxHeight: '85vh', overflowY: 'auto', padding: 24, position: 'relative',
          }}>
            <button onClick={() => setAdminOpen(false)}
                    style={{
                      position: 'absolute', top: 12, right: 14,
                      background: 'none', border: 'none', fontSize: 24, cursor: 'pointer', color: '#71717A',
                    }}>×</button>

            <div style={{
              background: 'rgba(225,29,72,.08)', border: '1px solid rgba(225,29,72,.3)',
              padding: 12, borderRadius: 8, marginBottom: 14, fontSize: 13,
              display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap',
            }}>
              <span>
                👑 <strong>Modo Admin:</strong> visualizando dashboard de{' '}
                <strong>{perfil.nome_artistico || perfil.nome}</strong> ({perfil.role}).
              </span>
              <button onClick={carregarVisaoAdmin} disabled={adminLoad}
                      style={{
                        background: '#fff', border: '1px solid #E5E7EB', borderRadius: 6,
                        padding: '4px 10px', fontSize: 11, color: '#71717A',
                        cursor: adminLoad ? 'wait' : 'pointer',
                      }}>
                {adminLoad ? 'Atualizando…' : '↻ Atualizar'}
              </button>
            </div>
            {adminAtualizadoEm && (
              <div style={{ fontSize: 11, color: '#71717A', marginBottom: 12 }}>
                Dados atualizados às {adminAtualizadoEm.toLocaleTimeString('pt-BR')}
              </div>
            )}

            {adminLoad && <div style={{ color: '#71717A' }}>Carregando dados…</div>}
            {adminErro && <div style={{ color: '#c0392b' }}>⚠ {adminErro}</div>}

            {adminData && (
              <>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 10, marginBottom: 20 }}>
                  <Card label="ID" value={adminData.perfil?.id?.slice(0, 8)} />
                  <Card label="Role" value={adminData.perfil?.role} />
                  <Card label="E-mail" value={adminData.perfil?.email} />
                  <Card label="Cadastro completo" value={adminData.perfil?.cadastro_completo ? 'Sim' : 'Não'} />
                  <Card label="Obras" value={String(adminData.obras?.length ?? 0)} />
                  <Card label="Contratos" value={String(adminData.contratos?.length ?? 0)} />
                  <Card label="Ganhos totais" value={fmt(adminData.ganhos_cents)} />
                </div>

                <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 8 }}>
                  Obras ({adminData.obras?.length || 0})
                </h3>
                <div style={{ marginBottom: 16 }}>
                  {(adminData.obras || []).slice(0, 10).map(o => (
                    <div key={o.id}
                         style={{ padding: 8, border: '1px solid #E5E7EB', borderRadius: 6, marginBottom: 4, fontSize: 12 }}>
                      <strong>{o.titulo}</strong> · {o.publicada ? 'Publicada' : 'Rascunho'}
                    </div>
                  ))}
                </div>

                <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 8 }}>
                  Contratos ({adminData.contratos?.length || 0})
                </h3>
                <div>
                  {(adminData.contratos || []).slice(0, 10).map(c => (
                    <div key={c.id}
                         style={{ padding: 8, border: '1px solid #E5E7EB', borderRadius: 6, marginBottom: 4, fontSize: 12 }}>
                      {c.id?.slice(0, 8)} · {c.status} · {c.created_at?.slice(0, 10)}
                    </div>
                  ))}
                </div>

                <div style={{ marginTop: 20, display: 'flex', gap: 10, justifyContent: 'space-between', flexWrap: 'wrap' }}>
                  <button onClick={() => {
                            setExcluirOpen(true); setExcluirTexto(''); setExcluirErro(''); setExcluirResult(null)
                          }}
                          data-testid="btn-excluir-usuario"
                          disabled={perfil.role === 'administrador'}
                          title={perfil.role === 'administrador' ? 'Não é possível excluir outro administrador' : 'Excluir usuário definitivamente'}
                          style={{
                            padding: '10px 16px', fontSize: 13, fontWeight: 700,
                            background: perfil.role === 'administrador' ? '#F4F4F5' : '#fff',
                            color: perfil.role === 'administrador' ? '#A1A1AA' : '#B91C1C',
                            border: `1px solid ${perfil.role === 'administrador' ? '#E5E7EB' : '#FCA5A5'}`,
                            borderRadius: 8,
                            cursor: perfil.role === 'administrador' ? 'not-allowed' : 'pointer',
                          }}>
                    🗑 Excluir usuário definitivamente
                  </button>

                  <div style={{ display: 'flex', gap: 10 }}>
                    <button onClick={() => navigate(`/admin/perfil/${perfilId}`)}
                            style={{
                              padding: '10px 16px', fontSize: 13, fontWeight: 700,
                              background: '#09090B', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer',
                            }}>
                      Abrir painel completo →
                    </button>
                    <button onClick={() => setAdminOpen(false)}
                            style={{
                              padding: '10px 16px', fontSize: 13, fontWeight: 600,
                              background: '#fff', color: '#71717A',
                              border: '1px solid #E5E7EB', borderRadius: 8, cursor: 'pointer',
                            }}>
                      Fechar
                    </button>
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {excluirOpen && (
        <div onClick={e => { if (e.target === e.currentTarget && !excluindo) setExcluirOpen(false) }}
             style={{
               position: 'fixed', inset: 0, background: 'rgba(0,0,0,.6)',
               display: 'flex', alignItems: 'center', justifyContent: 'center',
               zIndex: 1100, padding: 20,
             }}>
          <div style={{
            background: '#fff', borderRadius: 14, maxWidth: 520, width: '100%',
            padding: 24, position: 'relative',
          }}>
            <h3 style={{ margin: 0, fontSize: 18, fontWeight: 800, color: '#B91C1C' }}>
              ⚠ Excluir usuário definitivamente
            </h3>
            <p style={{ fontSize: 13, color: '#3F3F46', marginTop: 12, lineHeight: 1.5 }}>
              Esta ação <strong>não pode ser desfeita</strong>. Serão apagados de forma permanente:
              o perfil <strong>{perfil.nome_artistico || perfil.nome}</strong> ({perfil.email || '—'}),
              suas obras (quando ele for o único autor), contratos, ofertas, transações,
              repasses, saques, favoritos, histórico, comentários e o login no sistema.
            </p>

            {!excluirResult && (
              <>
                <p style={{ fontSize: 13, color: '#3F3F46', marginTop: 12 }}>
                  Para confirmar, digite <code style={{ background: '#FEE2E2', padding: '2px 6px', borderRadius: 4 }}>EXCLUIR</code> abaixo:
                </p>
                <input
                  type="text"
                  value={excluirTexto}
                  onChange={e => setExcluirTexto(e.target.value)}
                  disabled={excluindo}
                  autoFocus
                  placeholder="EXCLUIR"
                  style={{
                    width: '100%', padding: '10px 12px', fontSize: 14,
                    border: '1px solid #E5E7EB', borderRadius: 8, marginTop: 6,
                    boxSizing: 'border-box',
                  }}
                />
                {excluirErro && (
                  <div style={{ color: '#c0392b', fontSize: 12, marginTop: 8 }}>⚠ {excluirErro}</div>
                )}
                <div style={{ display: 'flex', gap: 10, marginTop: 18, justifyContent: 'flex-end' }}>
                  <button onClick={() => setExcluirOpen(false)}
                          disabled={excluindo}
                          style={{
                            padding: '10px 16px', fontSize: 13, fontWeight: 600,
                            background: '#fff', color: '#71717A',
                            border: '1px solid #E5E7EB', borderRadius: 8,
                            cursor: excluindo ? 'wait' : 'pointer',
                          }}>
                    Cancelar
                  </button>
                  <button
                    onClick={async () => {
                      setExcluindo(true); setExcluirErro('')
                      try {
                        // Usamos POST (e não DELETE) para evitar bloqueio por proxies/CDNs
                        const r = await api.post(`/admin/perfis/${perfilId}/excluir`, { confirmacao: 'EXCLUIR' })
                        setExcluirResult(r)
                      } catch (e) {
                        setExcluirErro(e.message || 'Falha ao excluir.')
                      } finally {
                        setExcluindo(false)
                      }
                    }}
                    disabled={excluirTexto !== 'EXCLUIR' || excluindo}
                    data-testid="btn-confirmar-exclusao"
                    style={{
                      padding: '10px 16px', fontSize: 13, fontWeight: 700,
                      background: excluirTexto === 'EXCLUIR' && !excluindo ? '#B91C1C' : '#FCA5A5',
                      color: '#fff', border: 'none', borderRadius: 8,
                      cursor: excluirTexto === 'EXCLUIR' && !excluindo ? 'pointer' : 'not-allowed',
                    }}>
                    {excluindo ? 'Excluindo…' : 'Excluir definitivamente'}
                  </button>
                </div>
              </>
            )}

            {excluirResult && (
              <>
                <div style={{
                  marginTop: 14, padding: 12, borderRadius: 8,
                  background: '#ECFDF5', border: '1px solid #A7F3D0', color: '#065F46', fontSize: 13,
                }}>
                  ✔ Usuário excluído.
                  {excluirResult.auth_apagado === false && (
                    <div style={{ color: '#92400E', marginTop: 6 }}>
                      Atenção: o registro de login (auth) não pôde ser removido — verifique manualmente.
                    </div>
                  )}
                </div>
                <details style={{ marginTop: 12, fontSize: 12, color: '#3F3F46' }}>
                  <summary style={{ cursor: 'pointer' }}>Ver detalhes da limpeza</summary>
                  <pre style={{
                    background: '#FAFAFA', border: '1px solid #E5E7EB', borderRadius: 6,
                    padding: 10, marginTop: 6, fontSize: 11, overflow: 'auto', maxHeight: 240,
                  }}>{JSON.stringify({ apagados: excluirResult.apagados, erros: excluirResult.erros }, null, 2)}</pre>
                </details>
                <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 14 }}>
                  <button onClick={() => { setExcluirOpen(false); setAdminOpen(false); navigate(-1) }}
                          style={{
                            padding: '10px 16px', fontSize: 13, fontWeight: 700,
                            background: '#09090B', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer',
                          }}>
                    Fechar e voltar
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

function Card({ label, value }) {
  return (
    <div style={{ padding: 12, background: '#FAFAFA', border: '1px solid #E5E7EB', borderRadius: 8 }}>
      <div style={{ fontSize: 10, color: '#71717A', textTransform: 'uppercase', letterSpacing: 0.5 }}>{label}</div>
      <div style={{ fontSize: 13, fontWeight: 600, marginTop: 4 }}>{value || '—'}</div>
    </div>
  )
}
