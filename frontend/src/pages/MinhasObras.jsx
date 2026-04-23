import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { usePlayer } from '../contexts/PlayerContext'
import { supabase } from '../lib/supabase'
import { api } from '../lib/api'

function fmt(cents) {
  return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format((cents ?? 0) / 100)
}

export default function MinhasObras() {
  const { perfil } = useAuth()
  const navigate = useNavigate()
  const { playObra, obra: obraAtual, playing } = usePlayer()

  const [obras, setObras] = useState([])
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState(null)
  const [excluindo, setExcluindo] = useState(false)
  const [confirmarExcluir, setConfirmarExcluir] = useState(false)

  useEffect(() => { load() }, [])

  async function load() {
    setLoading(true)
    try {
      const { data } = await supabase
        .from('coautorias')
        .select('share_pct, is_titular, obras(id, nome, genero, preco_cents, status, audio_path, titular_id, created_at)')
        .eq('perfil_id', perfil.id)
      setObras((data ?? [])
        .filter(c => c.obras)
        .map(c => ({ ...c.obras, share_pct: c.share_pct, sou_titular: c.is_titular }))
        .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
      )
    } finally { setLoading(false) }
  }

  async function excluir(obra) {
    if (!obra.sou_titular) {
      alert('Apenas o titular pode excluir a obra.')
      return
    }
    setExcluindo(true)
    try {
      await api.get(`/obras/${obra.id}`) // placeholder; vamos usar fetch DELETE
    } catch (_) {}
    try {
      await fetch(`${import.meta.env.VITE_API_BASE_URL}/obras/${obra.id}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${(await supabase.auth.getSession()).data.session?.access_token}`,
        },
      })
      setObras(prev => prev.filter(o => o.id !== obra.id))
      setSelected(null)
      setConfirmarExcluir(false)
    } catch (e) {
      alert('Erro ao excluir: ' + e.message)
    } finally {
      setExcluindo(false)
    }
  }

  if (loading) return <div style={{ padding: 32 }}><p style={{ color: 'var(--text-muted)' }}>Carregando…</p></div>

  return (
    <div style={{ padding: 32, maxWidth: 920 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: 24, fontWeight: 800 }}>Minhas obras</h1>
          <p style={{ color: 'var(--text-muted)', fontSize: 14 }}>{obras.length} composição{obras.length !== 1 ? 'ões' : ''} cadastrada{obras.length !== 1 ? 's' : ''}</p>
        </div>
        <button className="btn btn-primary" onClick={() => navigate('/obras/nova')}>+ Nova obra</button>
      </div>

      {obras.length === 0 ? (
        <div style={{
          padding: 60, textAlign: 'center',
          background: 'var(--surface-2)', borderRadius: 16,
        }}>
          <div style={{ fontSize: 48, opacity: .3, marginBottom: 12 }}>♪</div>
          <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 8 }}>Você ainda não cadastrou obras</h2>
          <p style={{ color: 'var(--text-muted)', fontSize: 14, marginBottom: 16 }}>Comece a publicar suas composições no Pitch.me.</p>
          <button className="btn btn-primary" onClick={() => navigate('/obras/nova')}>Cadastrar primeira obra</button>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {obras.map(obra => {
            const isPlaying = obraAtual?.id === obra.id && playing
            return (
              <div key={obra.id}
                onClick={() => setSelected(selected?.id === obra.id ? null : obra)}
                style={{
                  padding: 16, background: 'var(--surface)',
                  border: `1.5px solid ${selected?.id === obra.id ? 'var(--brand)' : 'var(--border)'}`,
                  borderRadius: 12, cursor: 'pointer',
                  transition: 'all .15s',
                }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
                  <button
                    onClick={e => { e.stopPropagation(); playObra(obra) }}
                    style={{
                      width: 44, height: 44, borderRadius: 8,
                      background: 'linear-gradient(135deg,#BE123C,#09090B)',
                      color: '#fff', border: 'none', cursor: 'pointer',
                      fontSize: 14, flexShrink: 0,
                    }}>
                    {isPlaying ? '⏸' : '▶'}
                  </button>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 15, fontWeight: 700 }}>{obra.nome}</div>
                    <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                      {obra.genero || 'Sem gênero'} · {fmt(obra.preco_cents)} · seu share: {obra.share_pct}%
                      {obra.sou_titular && ' · titular'}
                    </div>
                  </div>
                  <span style={{
                    fontSize: 11, fontWeight: 600,
                    padding: '3px 10px', borderRadius: 99,
                    background: obra.status === 'publicada' ? 'var(--success-bg)' : 'var(--warning-bg)',
                    color: obra.status === 'publicada' ? 'var(--success)' : 'var(--warning)',
                  }}>
                    {obra.status}
                  </span>
                </div>

                {/* Ações ao selecionar */}
                {selected?.id === obra.id && (
                  <div style={{
                    marginTop: 14, paddingTop: 14,
                    borderTop: '1px solid var(--border)',
                    display: 'flex', gap: 10, justifyContent: 'flex-end',
                  }}>
                    {obra.sou_titular ? (
                      !confirmarExcluir ? (
                        <button
                          className="btn btn-danger btn-sm"
                          onClick={e => { e.stopPropagation(); setConfirmarExcluir(true) }}>
                          🗑 Excluir composição
                        </button>
                      ) : (
                        <>
                          <span style={{ fontSize: 13, color: 'var(--error)', alignSelf: 'center', marginRight: 'auto' }}>
                            Tem certeza? Esta ação não pode ser desfeita.
                          </span>
                          <button className="btn btn-ghost btn-sm" onClick={e => { e.stopPropagation(); setConfirmarExcluir(false) }}>
                            Cancelar
                          </button>
                          <button className="btn btn-danger btn-sm" onClick={e => { e.stopPropagation(); excluir(obra) }} disabled={excluindo}>
                            {excluindo ? 'Excluindo…' : 'Sim, excluir'}
                          </button>
                        </>
                      )
                    ) : (
                      <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                        Você é coautor desta obra. Apenas o titular pode excluí-la.
                      </span>
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
