import React, { useEffect, useMemo, useState } from 'react'
import { api } from '../lib/api'

/**
 * Página de administração de Dossiês.
 *
 * Spec:
 *  - Listar todos os dossiês (já gerados) com NOME + ID ÚNICO.
 *  - Barra de pesquisa para buscar pelo ID ÚNICO do dossiê.
 *  - Botão para baixar o ZIP de cada dossiê.
 *  - Botão para visualizar o metadata (preview do que está dentro).
 *
 * A geração de dossiê em si acontece a partir da página de
 * detalhe da obra (POST /api/dossies/obras/:obra_id) e cai aqui
 * automaticamente assim que persistido.
 */
export default function Dossies() {
  const [dossies,     setDossies]     = useState([])
  const [loading,     setLoading]     = useState(true)
  const [error,       setError]       = useState('')
  const [query,       setQuery]       = useState('')
  const [selected,    setSelected]    = useState(null)
  const [meta,        setMeta]        = useState(null)
  const [metaLoading, setMetaLoading] = useState(false)
  const [dlLoadingId, setDlLoadingId] = useState(null)
  const [copiedId,    setCopiedId]    = useState(null)

  // ────────────────────────────────────────────────────────────
  // Carrega a lista
  // ────────────────────────────────────────────────────────────
  useEffect(() => {
    let alive = true
    setLoading(true)
    api.get('/dossies')
      .then(data => { if (alive) setDossies(Array.isArray(data) ? data : []) })
      .catch(e   => { if (alive) setError(e.message) })
      .finally(() => { if (alive) setLoading(false) })
    return () => { alive = false }
  }, [])

  // ────────────────────────────────────────────────────────────
  // Busca local (instantânea por ID único OU nome da obra)
  // ────────────────────────────────────────────────────────────
  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) return dossies
    return dossies.filter(d => {
      const id     = (d.id          || '').toLowerCase()
      const obraId = (d.obra_id     || '').toLowerCase()
      const titulo = (d.titulo_obra || '').toLowerCase()
      const hash   = (d.hash_sha256 || '').toLowerCase()
      return id.includes(q) || obraId.includes(q) || titulo.includes(q) || hash.includes(q)
    })
  }, [query, dossies])

  // ────────────────────────────────────────────────────────────
  // Ações
  // ────────────────────────────────────────────────────────────
  async function handleVisualizar(d) {
    if (selected?.id === d.id) {
      setSelected(null); setMeta(null); return
    }
    setSelected(d); setMeta(null); setMetaLoading(true)
    try {
      const data = await api.get(`/dossies/${d.id}/visualizar`)
      setMeta(data)
    } catch (e) {
      setMeta({ erro: e.message })
    } finally {
      setMetaLoading(false)
    }
  }

  async function handleDownload(d) {
    setDlLoadingId(d.id)
    try {
      await api.download(`/dossies/${d.id}/download`, `obra-${d.obra_id}.zip`)
    } catch (e) {
      alert('Erro ao baixar: ' + e.message)
    } finally {
      setDlLoadingId(null)
    }
  }

  async function handleCopyId(id) {
    try {
      await navigator.clipboard.writeText(id)
      setCopiedId(id)
      setTimeout(() => setCopiedId(prev => prev === id ? null : prev), 1400)
    } catch {
      // ignora — alguns navegadores bloqueiam fora de HTTPS
    }
  }

  function fmt(ts) {
    if (!ts) return '—'
    return new Date(ts).toLocaleString('pt-BR', {
      dateStyle: 'short',
      timeStyle: 'short',
    })
  }

  // ────────────────────────────────────────────────────────────
  // Render
  // ────────────────────────────────────────────────────────────
  return (
    <div style={{ padding: '2rem', maxWidth: 1080, margin: '0 auto' }}>
      <h2 style={{
        fontFamily: 'monospace',
        letterSpacing: 2,
        marginBottom: '0.4rem',
      }}>
        DOSSIÊS DAS OBRAS
      </h2>
      <p style={{
        color: 'var(--text-muted)',
        fontSize: 13,
        marginBottom: '1.4rem',
      }}>
        Arquivos ZIP oficiais gerados a partir dos contratos assinados na
        plataforma. Cada dossiê tem um <b>ID único</b> que serve como
        identificador permanente.
      </p>

      {/* ── Barra de pesquisa ─────────────────────────────────── */}
      <div style={{
        position: 'relative',
        marginBottom: '1.4rem',
      }}>
        <span style={{
          position: 'absolute', left: 14, top: '50%',
          transform: 'translateY(-50%)',
          color: 'var(--text-muted)', fontSize: 14,
          pointerEvents: 'none',
        }}>⌕</span>
        <input
          type="search"
          value={query}
          onChange={e => setQuery(e.target.value)}
          placeholder="Buscar pelo ID único do dossiê, ID da obra ou nome…"
          aria-label="Buscar dossiê"
          style={{
            width: '100%',
            padding: '0.75rem 1rem 0.75rem 2.4rem',
            fontSize: '0.92rem',
            background: 'var(--surface)',
            color: 'var(--text)',
            border: '1px solid var(--border)',
            borderRadius: 8,
            outline: 'none',
            fontFamily: 'inherit',
          }}
        />
        {query && (
          <button
            onClick={() => setQuery('')}
            aria-label="Limpar busca"
            style={{
              position: 'absolute', right: 8, top: '50%',
              transform: 'translateY(-50%)',
              background: 'none', border: 'none', cursor: 'pointer',
              color: 'var(--text-muted)', fontSize: 16, padding: '4px 10px',
            }}
          >✕</button>
        )}
      </div>

      <div style={{
        fontSize: 12,
        color: 'var(--text-muted)',
        marginBottom: '1rem',
      }}>
        {loading
          ? 'Carregando…'
          : `${filtered.length} de ${dossies.length} dossiê(s)`}
      </div>

      {error && (
        <p style={{ color: '#e55' }}>
          {error}
        </p>
      )}

      {/* ── Empty states ──────────────────────────────────────── */}
      {!loading && !error && dossies.length === 0 && (
        <EmptyCard
          icon="📂"
          title="Nenhum dossiê gerado ainda"
          subtitle="Gere o primeiro dossiê na página de detalhe de uma obra."
        />
      )}

      {!loading && !error && dossies.length > 0 && filtered.length === 0 && (
        <EmptyCard
          icon="∅"
          title="Nenhum dossiê encontrado"
          subtitle={`Nenhum resultado para "${query}".`}
        />
      )}

      {/* ── Lista ─────────────────────────────────────────────── */}
      {filtered.map(d => (
        <div key={d.id} style={{
          border: selected?.id === d.id
            ? '1px solid var(--brand)'
            : '1px solid var(--border)',
          borderRadius: 10,
          marginBottom: 10,
          padding: '1rem 1.2rem',
          background: 'var(--surface)',
          display: 'flex',
          alignItems: 'center',
          gap: '1rem',
          flexWrap: 'wrap',
          transition: 'border-color .15s',
        }}>
          <div style={{ flex: 1, minWidth: 240 }}>
            <div style={{
              fontWeight: 700,
              fontSize: '0.98rem',
              marginBottom: 4,
            }}>
              {d.titulo_obra || '(sem título)'}
            </div>

            {/* ID único + copiar */}
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              fontSize: '0.72rem',
              opacity: 0.8,
            }}>
              <span style={{ color: 'var(--text-muted)' }}>ID:</span>
              <code style={{
                fontFamily: 'monospace',
                fontSize: '0.72rem',
                background: 'var(--surface-2, rgba(0,0,0,.04))',
                padding: '2px 6px',
                borderRadius: 4,
              }}>{d.id}</code>
              <button
                onClick={() => handleCopyId(d.id)}
                title="Copiar ID"
                style={{
                  background: 'none', border: 'none', cursor: 'pointer',
                  color: copiedId === d.id ? 'var(--brand)' : 'var(--text-muted)',
                  fontSize: '0.72rem', padding: '2px 4px',
                }}
              >{copiedId === d.id ? '✓ copiado' : '⎘'}</button>
            </div>

            <div style={{
              fontSize: '0.7rem',
              opacity: 0.5,
              marginTop: 4,
            }}>
              Gerado em {fmt(d.created_at)}
              &nbsp;·&nbsp;
              hash: <code style={{ fontSize: '0.68rem' }}>
                {(d.hash_sha256 || '').slice(0, 16)}…
              </code>
            </div>
          </div>

          <button
            onClick={() => handleVisualizar(d)}
            style={btnStyle('transparent', selected?.id === d.id ? 'var(--brand)' : 'var(--text-muted)')}
          >
            {selected?.id === d.id ? '▲ Fechar' : '◎ Visualizar'}
          </button>

          <button
            onClick={() => handleDownload(d)}
            disabled={dlLoadingId === d.id}
            style={btnStyle('var(--brand)', '#fff')}
          >
            {dlLoadingId === d.id ? 'Baixando…' : '⬇ Baixar ZIP'}
          </button>
        </div>
      ))}

      {/* ── Painel de visualização do metadata ────────────────── */}
      {selected && (
        <div style={{
          marginTop: '1.5rem',
          padding: '1.5rem',
          background: 'var(--surface)',
          border: '1px solid var(--border)',
          borderRadius: 10,
        }}>
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: '1rem',
          }}>
            <h3 style={{ margin: 0, fontFamily: 'monospace', fontSize: 14 }}>
              📄 {selected.titulo_obra || selected.obra_id}
            </h3>
            <button
              onClick={() => { setSelected(null); setMeta(null) }}
              style={{
                background: 'none',
                border: 'none',
                color: 'var(--text-muted)',
                cursor: 'pointer',
                fontSize: '1.2rem',
              }}
            >✕</button>
          </div>

          {metaLoading && <p style={{ opacity: 0.5 }}>Carregando metadata…</p>}

          {meta && !metaLoading && (
            <pre style={{
              background: 'var(--surface-2, rgba(0,0,0,.04))',
              padding: '1rem',
              borderRadius: 8,
              fontSize: '0.78rem',
              overflowX: 'auto',
              color: 'var(--text-secondary)',
              lineHeight: 1.7,
              margin: 0,
              maxHeight: 480,
            }}>
              {JSON.stringify(meta.metadata || meta, null, 2)}
            </pre>
          )}
        </div>
      )}
    </div>
  )
}

function EmptyCard({ icon, title, subtitle }) {
  return (
    <div style={{
      padding: '3rem',
      textAlign: 'center',
      background: 'var(--surface)',
      border: '1px dashed var(--border)',
      borderRadius: 10,
    }}>
      <div style={{ fontSize: 32, marginBottom: 12 }}>{icon}</div>
      <div style={{ fontWeight: 600, marginBottom: 4 }}>{title}</div>
      <div style={{ opacity: 0.5, fontSize: 13 }}>{subtitle}</div>
    </div>
  )
}

function btnStyle(bg, color) {
  return {
    background:    bg,
    color,
    border:        `1px solid ${color === '#fff' ? 'var(--brand)' : 'var(--border)'}`,
    borderRadius:  6,
    padding:       '0.45rem 1rem',
    cursor:        'pointer',
    fontSize:      '0.82rem',
    fontWeight:    600,
    whiteSpace:    'nowrap',
  }
}
