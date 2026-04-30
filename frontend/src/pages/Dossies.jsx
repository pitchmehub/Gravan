import React, { useEffect, useMemo, useState } from 'react'
import { api } from '../lib/api'
import { IconCopy, IconCheck } from '../components/Icons'

export default function Dossies() {
  const [obras, setObras]       = useState([])
  const [loading, setLoading]   = useState(true)
  const [error, setError]       = useState('')
  const [query, setQuery]       = useState('')
  const [busy, setBusy]         = useState({})
  const [copiedId, setCopiedId] = useState(null)
  const [feedback, setFeedback] = useState(null)

  async function carregar() {
    setLoading(true)
    setError('')
    try {
      const data = await api.get('/dossies/admin/obras')
      setObras(Array.isArray(data) ? data : [])
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { carregar() }, [])

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) return obras
    return obras.filter(o =>
      (o.id || '').toLowerCase().includes(q) ||
      (o.nome || '').toLowerCase().includes(q) ||
      (o.titular?.nome || '').toLowerCase().includes(q) ||
      (o.titular?.email || '').toLowerCase().includes(q)
    )
  }, [query, obras])

  function showFeedback(obraId, type, message) {
    setFeedback({ obraId, type, message })
    setTimeout(() => setFeedback(prev => prev?.obraId === obraId ? null : prev), 4000)
  }

  async function handleGerar(obra) {
    if (obra.dossie && !confirm(
      `Esta obra já possui dossiê gerado em ${new Date(obra.dossie.created_at).toLocaleString('pt-BR')}.\n\nDeseja regenerar (substituirá o anterior)?`
    )) return

    setBusy(prev => ({ ...prev, [obra.id]: 'gerar' }))
    try {
      const r = await api.post(`/dossies/obras/${obra.id}`, {})
      setObras(prev => prev.map(o =>
        o.id === obra.id
          ? { ...o, dossie: { id: r.id, hash_sha256: r.hash_sha256, created_at: r.created_at } }
          : o
      ))
      showFeedback(obra.id, 'success', '✓ Dossiê gerado com sucesso')
    } catch (e) {
      showFeedback(obra.id, 'error', '✗ Erro: ' + e.message)
    } finally {
      setBusy(prev => ({ ...prev, [obra.id]: null }))
    }
  }

  async function handleBaixar(obra) {
    if (!obra.dossie) return
    setBusy(prev => ({ ...prev, [obra.id]: 'baixar' }))
    try {
      const safeName = (obra.nome || obra.id).replace(/[^a-zA-Z0-9-_]/g, '_').slice(0, 60)
      await api.download(`/dossies/${obra.dossie.id}/download`, `dossie-${safeName}.zip`)
    } catch (e) {
      showFeedback(obra.id, 'error', '✗ Erro ao baixar: ' + e.message)
    } finally {
      setBusy(prev => ({ ...prev, [obra.id]: null }))
    }
  }

  async function handleCopyId(id) {
    try {
      await navigator.clipboard.writeText(id)
      setCopiedId(id)
      setTimeout(() => setCopiedId(prev => prev === id ? null : prev), 1400)
    } catch { }
  }

  const total    = obras.length
  const comDossie = obras.filter(o => o.dossie).length

  return (
    <div style={{ padding: '2rem', maxWidth: 1080, margin: '0 auto' }}>
      <div style={{ marginBottom: '1.4rem' }}>
        <h2 style={{ fontFamily: 'monospace', letterSpacing: 2, marginBottom: '0.3rem' }}>
          DOSSIÊS DAS OBRAS
        </h2>
        <p style={{ color: 'var(--text-muted)', fontSize: 13, margin: 0 }}>
          Todas as obras da plataforma. Gere e baixe o ZIP oficial de cada uma.
        </p>
      </div>

      {/* Barra de pesquisa */}
      <div style={{ position: 'relative', marginBottom: '1rem' }}>
        <span style={{
          position: 'absolute', left: 14, top: '50%', transform: 'translateY(-50%)',
          color: 'var(--text-muted)', fontSize: 14, pointerEvents: 'none',
        }}>⌕</span>
        <input
          type="search"
          value={query}
          onChange={e => setQuery(e.target.value)}
          placeholder="Buscar por nome, ID único ou e-mail do titular…"
          style={{
            width: '100%', padding: '0.75rem 2.4rem', fontSize: '0.92rem',
            background: 'var(--surface)', color: 'var(--text)',
            border: '1px solid var(--border)', borderRadius: 8,
            outline: 'none', fontFamily: 'inherit', boxSizing: 'border-box',
          }}
        />
        {query && (
          <button onClick={() => setQuery('')} style={{
            position: 'absolute', right: 8, top: '50%', transform: 'translateY(-50%)',
            background: 'none', border: 'none', cursor: 'pointer',
            color: 'var(--text-muted)', fontSize: 16, padding: '4px 10px',
          }}>✕</button>
        )}
      </div>

      {/* Contadores */}
      <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: '1.2rem', display: 'flex', gap: 16 }}>
        {loading ? 'Carregando…' : (
          <>
            <span><strong>{filtered.length}</strong> obra(s) exibida(s) de <strong>{total}</strong></span>
            <span>·</span>
            <span style={{ color: 'var(--success)' }}><strong>{comDossie}</strong> com dossiê gerado</span>
            <span>·</span>
            <span style={{ color: 'var(--text-muted)' }}><strong>{total - comDossie}</strong> sem dossiê</span>
          </>
        )}
      </div>

      {error && <p style={{ color: '#e55', marginBottom: 12 }}>⚠ {error}</p>}

      {!loading && filtered.length === 0 && !error && (
        <div style={{
          padding: '3rem', textAlign: 'center', background: 'var(--surface)',
          border: '1px dashed var(--border)', borderRadius: 10,
        }}>
          <div style={{ fontSize: 32, marginBottom: 12 }}></div>
          <div style={{ fontWeight: 600, marginBottom: 4 }}>
            {query ? 'Nenhuma obra encontrada' : 'Nenhuma obra cadastrada'}
          </div>
          <div style={{ opacity: 0.5, fontSize: 13 }}>
            {query ? `Nenhum resultado para "${query}".` : 'As obras aparecerão aqui quando forem cadastradas.'}
          </div>
        </div>
      )}

      {/* Lista */}
      <div style={{ display: 'grid', gap: 10 }}>
        {filtered.map(o => {
          const fb = feedback?.obraId === o.id ? feedback : null
          return (
            <div key={o.id} style={{
              border: '1px solid var(--border)',
              borderRadius: 12,
              padding: '14px 16px',
              background: 'var(--surface)',
              display: 'flex',
              alignItems: 'center',
              gap: 14,
              flexWrap: 'wrap',
            }}>
              {/* Capa */}
              {o.cover_url && (
                <img src={o.cover_url} alt={o.nome}
                  style={{ width: 48, height: 48, borderRadius: 6, objectFit: 'cover', flexShrink: 0 }} />
              )}

              {/* Info */}
              <div style={{ flex: 1, minWidth: 200 }}>
                <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 2 }}>{o.nome || '(sem nome)'}</div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                  {o.titular?.nome || o.titular?.nome_artistico || '—'}
                  {o.genero && <span style={{ marginLeft: 8, background: 'var(--surface-2, rgba(0,0,0,.06))', borderRadius: 4, padding: '1px 6px' }}>{o.genero}</span>}
                </div>

                {/* ID da obra */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 4 }}>
                  <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>ID:</span>
                  <code style={{ fontSize: 10, fontFamily: 'monospace', background: 'var(--surface-2, rgba(0,0,0,.04))', padding: '1px 5px', borderRadius: 4 }}>
                    {o.id}
                  </code>
                  <button onClick={() => handleCopyId(o.id)} title="Copiar ID" style={{
                    background: 'none', border: 'none', cursor: 'pointer',
                    color: copiedId === o.id ? 'var(--brand)' : 'var(--text-muted)', fontSize: 10, padding: '1px 3px',
                  }}>
                    {copiedId === o.id ? <><IconCheck size={10} /> copiado</> : <IconCopy size={11} />}
                  </button>
                </div>

                {/* Dossiê info */}
                {o.dossie && (
                  <div style={{ fontSize: 10, color: 'var(--success)', marginTop: 3 }}>
                    ✓ Gerado em {new Date(o.dossie.created_at).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' })}
                    &nbsp;·&nbsp;hash: <code style={{ fontSize: 10 }}>{(o.dossie.hash_sha256 || '').slice(0, 12)}…</code>
                  </div>
                )}

                {fb && (
                  <div style={{ fontSize: 11, marginTop: 4, color: fb.type === 'success' ? 'var(--success)' : '#e55' }}>
                    {fb.message}
                  </div>
                )}
              </div>

              {/* Badges */}
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 6 }}>
                {o.dossie && (
                  <span style={{
                    fontSize: 10, fontWeight: 700, padding: '2px 8px',
                    background: 'var(--success-bg, #d1fae5)', color: 'var(--success, #059669)',
                    borderRadius: 99, textTransform: 'uppercase', letterSpacing: 1,
                  }}>Dossiê gerado</span>
                )}
              </div>

              {/* Ações */}
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                <button
                  onClick={() => handleGerar(o)}
                  disabled={!!busy[o.id]}
                  style={{
                    background: o.dossie ? 'transparent' : 'var(--brand)',
                    color: o.dossie ? 'var(--brand)' : '#fff',
                    border: '1px solid var(--brand)',
                    borderRadius: 6, padding: '7px 12px',
                    cursor: busy[o.id] ? 'not-allowed' : 'pointer',
                    fontSize: 12, fontWeight: 700, whiteSpace: 'nowrap',
                    opacity: busy[o.id] ? 0.6 : 1,
                  }}
                >
                  {busy[o.id] === 'gerar' ? '⏳ Gerando…' : (o.dossie ? '↻ Regenerar' : 'Gerar dossiê')}
                </button>

                <button
                  onClick={() => handleBaixar(o)}
                  disabled={!o.dossie || !!busy[o.id]}
                  title={!o.dossie ? 'Gere o dossiê primeiro' : 'Baixar ZIP do dossiê'}
                  style={{
                    background: !o.dossie ? 'var(--surface)' : 'var(--success)',
                    color: !o.dossie ? 'var(--text-muted)' : '#fff',
                    border: `1px solid ${!o.dossie ? 'var(--border)' : 'var(--success)'}`,
                    borderRadius: 6, padding: '7px 12px',
                    cursor: !o.dossie ? 'not-allowed' : (busy[o.id] ? 'wait' : 'pointer'),
                    fontSize: 12, fontWeight: 700, whiteSpace: 'nowrap',
                    opacity: busy[o.id] === 'baixar' ? 0.6 : 1,
                  }}
                >
                  {busy[o.id] === 'baixar' ? '⏳ Baixando…' : '⬇ Baixar ZIP'}
                </button>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
