import React, { useEffect, useState } from 'react'
import { api } from '../lib/api'
import { usePlayer } from '../contexts/PlayerContext'

function fmt(cents) {
  return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format((cents ?? 0) / 100)
}

const ABAS = [
  { id: 'analiticos',  label: 'Analíticos',          icon: '▦' },
  { id: 'receita',     label: 'Receita',             icon: '◎' },
  { id: 'obras',       label: 'Obras',               icon: '♫' },
  { id: 'generos',     label: 'Gêneros mais procurados', icon: '♬' },
  { id: 'saques',      label: 'Autorizar saques',   icon: '💸' },
  { id: 'auditoria',   label: 'Auditoria de splits', icon: '⊟' },
  { id: 'seguranca',   label: 'Segurança',           icon: '🔒' },
]

function StatCard({ label, value, sublabel, color = 'var(--brand)', big = false }) {
  return (
    <div style={{
      background: 'var(--surface)',
      border: '1px solid var(--border)',
      borderRadius: 14, padding: '16px 18px',
    }}>
      <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 1 }}>
        {label}
      </div>
      <div style={{ fontSize: big ? 28 : 22, fontWeight: 800, color, marginTop: 6 }}>
        {value}
      </div>
      {sublabel && <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>{sublabel}</div>}
    </div>
  )
}

export default function Admin() {
  const [aba, setAba] = useState('analiticos')
  const [resumo,  setResumo]  = useState(null)
  const [saques,  setSaques]  = useState([])
  const [saqueLoading, setSaqueLoading] = useState(false)
  const [generos, setGeneros] = useState([])
  const [audit,   setAudit]   = useState([])
  const [volume,  setVolume]  = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      api.get('/admin/bi/resumo').catch(() => null),
      api.get('/admin/bi/generos').catch(() => []),
      api.get('/admin/bi/auditoria?per_page=30').catch(() => []),
      api.get('/admin/bi/volume?dias=30').catch(() => []),
    ]).then(([r, g, a, v]) => {
      setResumo(r); setGeneros(g); setAudit(a); setVolume(v)
    }).finally(() => setLoading(false))
  }, [])

  async function loadSaques() {
    setSaqueLoading(true)
    try {
      const data = await api.get('/admin/saques')
      setSaques(data)
    } catch (e) { console.error(e) }
    finally { setSaqueLoading(false) }
  }

  useEffect(() => {
    if (aba !== 'saques') return
    loadSaques()
    const intv = setInterval(() => loadSaques(), 5000)
    return () => clearInterval(intv)
  }, [aba])

  async function handleSaque(id, acao, motivo) {
    if (acao === 'rejeitado' && !motivo) {
      const m = prompt('Motivo da rejeição (obrigatório):')
      if (!m) return
      motivo = m
    }
    if (!confirm(`Confirmar ${acao === 'pago' ? 'marcar como PAGO' : acao === 'processando' ? 'marcar como PROCESSANDO' : 'REJEITAR e devolver valor'}?`)) return
    try {
      await api.post(`/admin/saques/${id}/aprovar`, { acao, motivo })
      await loadSaques()
    } catch (e) {
      alert('Erro: ' + e.message)
    }
  }

  if (loading) return <div style={{ padding: 32 }}><p style={{ color: 'var(--text-muted)' }}>Carregando painel…</p></div>

  return (
    <div style={{ padding: 32, maxWidth: 1100 }}>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 26, fontWeight: 800 }}>Painel administrador</h1>
        <p style={{ color: 'var(--text-muted)', fontSize: 14 }}>Visão consolidada da plataforma Pitch.me</p>
      </div>

      <div style={{
        display: 'flex', gap: 4, marginBottom: 24,
        borderBottom: '1px solid var(--border)',
        flexWrap: 'wrap',
      }}>
        {ABAS.map(a => (
          <button key={a.id} onClick={() => setAba(a.id)}
            style={{
              padding: '10px 18px', border: 'none', background: 'none',
              cursor: 'pointer', fontSize: 14,
              fontWeight: aba === a.id ? 700 : 500,
              color: aba === a.id ? 'var(--brand)' : 'var(--text-secondary)',
              borderBottom: aba === a.id ? '3px solid var(--brand)' : '3px solid transparent',
              marginBottom: -1, display: 'flex', alignItems: 'center', gap: 6,
            }}>
            <span>{a.icon}</span> {a.label}
          </button>
        ))}
      </div>

      {/* ── ANALÍTICOS ── */}
      {aba === 'analiticos' && resumo && (
        <div>
          <div style={{
            display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
            gap: 14, marginBottom: 24,
          }}>
            <StatCard label="Composições cadastradas" value={resumo.total_obras} sublabel={`${resumo.obras_publicadas} publicadas`} big color="var(--brand)" />
            <StatCard label="Vendas confirmadas"      value={resumo.total_vendas} big color="var(--success)" />
            <StatCard label="Compositores"            value={resumo.total_compositores} sublabel={`de ${resumo.total_usuarios} usuários`} />
            <StatCard label="Intérpretes"             value={resumo.total_interpretes} />
            <StatCard label="Ofertas pendentes"       value={resumo.ofertas_pendentes} color="var(--warning)" />
          </div>

          <div className="card" style={{ background: 'linear-gradient(135deg, #BE123C, #09090B)', border: 'none', color: '#fff', marginBottom: 16, boxShadow: '0 8px 32px rgba(225,29,72,.25)' }}>
            <h2 style={{ fontSize: 14, fontWeight: 600, color: 'rgba(255,255,255,.7)', marginBottom: 12, textTransform: 'uppercase', letterSpacing: 1 }}>
              Receita total da plataforma
            </h2>
            <div style={{ fontSize: 42, fontWeight: 800, color: '#fff', marginBottom: 6 }}>
              {fmt(resumo.receita_bruta_cents)}
            </div>
            <div style={{ display: 'flex', gap: 24, marginTop: 16 }}>
              <div>
                <div style={{ fontSize: 11, color: 'rgba(255,255,255,.5)' }}>RETIDO PELA PLATAFORMA</div>
                <div style={{ fontSize: 22, fontWeight: 700, color: '#34D399', marginTop: 4 }}>
                  {fmt(resumo.receita_plataforma_cents)}
                </div>
              </div>
              <div>
                <div style={{ fontSize: 11, color: 'rgba(255,255,255,.5)' }}>PAGO AOS COMPOSITORES</div>
                <div style={{ fontSize: 22, fontWeight: 700, color: 'var(--text-primary)', marginTop: 4 }}>
                  {fmt(resumo.receita_compositores_cents)}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── RECEITA ── */}
      {aba === 'receita' && resumo && (
        <div>
          <div style={{
            display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
            gap: 14, marginBottom: 24,
          }}>
            <StatCard label="Receita bruta total"     value={fmt(resumo.receita_bruta_cents)} sublabel="Soma de todas as vendas confirmadas" big color="var(--brand)" />
            <StatCard label="Receita líquida da plataforma" value={fmt(resumo.receita_plataforma_cents)} sublabel="Retido direto na fonte" big color="var(--success)" />
            <StatCard label="Pago aos compositores"   value={fmt(resumo.receita_compositores_cents)} sublabel="Distribuído via wallets dos compositores" big color="var(--brand)" />
          </div>

          <div className="card">
            <h2 style={{ fontSize: 15, fontWeight: 700, marginBottom: 14 }}>Histórico de vendas (últimas)</h2>
            {volume.length === 0 ? (
              <p style={{ color: 'var(--text-muted)', fontSize: 13 }}>Nenhuma venda registrada ainda.</p>
            ) : (
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid var(--border)' }}>
                      {['Data', 'Método', 'Status', 'Vendas', 'Bruta', 'Plataforma', 'Compositores'].map(h => (
                        <th key={h} style={{ padding: '10px 12px', textAlign: 'left', color: 'var(--text-muted)', fontWeight: 600, fontSize: 11, textTransform: 'uppercase', letterSpacing: 1 }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {volume.map((v, i) => (
                      <tr key={i} style={{ borderBottom: '1px solid var(--border)' }}>
                        <td style={{ padding: '10px 12px', whiteSpace: 'nowrap' }}>{new Date(v.dia).toLocaleDateString('pt-BR')}</td>
                        <td style={{ padding: '10px 12px', textTransform: 'uppercase', fontWeight: 600 }}>{v.metodo}</td>
                        <td style={{ padding: '10px 12px' }}>{v.status}</td>
                        <td style={{ padding: '10px 12px' }}>{v.total_transacoes}</td>
                        <td style={{ padding: '10px 12px' }}>{fmt(v.receita_bruta_cents)}</td>
                        <td style={{ padding: '10px 12px', color: 'var(--success)' }}>{fmt(v.receita_plataforma_cents)}</td>
                        <td style={{ padding: '10px 12px', color: 'var(--brand)' }}>{fmt(v.pago_compositores_cents)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── OBRAS ── (lista todas as obras + GERAR / BAIXAR DOSSIÊ) */}
      {aba === 'obras' && <ObrasPanel />}

      {/* ── GÊNEROS ── */}
      {aba === 'generos' && (
        <div className="card">
          <h2 style={{ fontSize: 15, fontWeight: 700, marginBottom: 14 }}>Gêneros mais procurados</h2>
          {generos.length === 0 ? (
            <p style={{ color: 'var(--text-muted)', fontSize: 13 }}>Sem dados ainda.</p>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border)' }}>
                  {['Gênero', 'Obras publicadas', 'Vendas', 'Receita gerada'].map(h => (
                    <th key={h} style={{ padding: '10px 12px', textAlign: 'left', color: 'var(--text-muted)', fontWeight: 600, fontSize: 11, textTransform: 'uppercase', letterSpacing: 1 }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {generos.map((g, i) => (
                  <tr key={i} style={{ borderBottom: '1px solid var(--border)' }}>
                    <td style={{ padding: '12px', fontWeight: 700 }}>{g.genero}</td>
                    <td style={{ padding: '12px' }}>{g.total_obras}</td>
                    <td style={{ padding: '12px', color: 'var(--success)' }}>{g.total_vendas}</td>
                    <td style={{ padding: '12px', color: 'var(--brand)', fontWeight: 700 }}>{fmt(g.receita_cents)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* ── SAQUES ── */}
      {aba === 'saques' && (
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14, flexWrap: 'wrap', gap: 8 }}>
            <div>
              <h2 style={{ fontSize: 15, fontWeight: 700 }}>Saques solicitados</h2>
                <div style={{ marginTop: 8, marginBottom: 4, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                  <a href="/admin/saques" style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '6px 14px', borderRadius: 8, fontSize: 12, fontWeight: 700, background: 'var(--brand)', color: '#fff', textDecoration: 'none' }}>💸 Painel de saques ↗</a>
                  <a href="/admin/saques/historico" style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '6px 14px', borderRadius: 8, fontSize: 12, fontWeight: 700, background: 'var(--surface-2)', color: 'var(--brand)', border: '1px solid var(--border)', textDecoration: 'none' }}>📋 Histórico & Exportar ↗</a>
                </div>
                <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>
                <span style={{
                  display: 'inline-block', width: 8, height: 8, borderRadius: '50%',
                  background: 'var(--success)', marginRight: 6,
                  animation: 'pulse 2s infinite',
                }}></span>
                Atualização automática a cada 5 segundos
                {saques.filter(s => s.status === 'solicitado').length > 0 && (
                  <span style={{
                    marginLeft: 10, padding: '2px 8px',
                    background: 'var(--warning-bg)', color: 'var(--warning)',
                    borderRadius: 99, fontSize: 11, fontWeight: 700,
                  }}>
                    {saques.filter(s => s.status === 'solicitado').length} aguardando
                  </span>
                )}
              </p>
            </div>
            <button onClick={loadSaques} style={{ background: 'none', border: '1px solid var(--border)', padding: '6px 12px', borderRadius: 8, color: 'var(--brand)', fontSize: 13, cursor: 'pointer' }}>
              ↻ atualizar agora
            </button>
          </div>
          <style>{`
            @keyframes pulse {
              0%, 100% { opacity: 1; }
              50% { opacity: 0.4; }
            }
          `}</style>

          {saqueLoading ? (
            <p style={{ color: 'var(--text-muted)' }}>Carregando…</p>
          ) : saques.length === 0 ? (
            <p style={{ color: 'var(--text-muted)', fontSize: 13 }}>Nenhum saque solicitado no momento.</p>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {saques.map(s => {
                const statusMap = {
                  solicitado:  { bg: 'var(--warning-bg)', cor: 'var(--warning)', label: '⏱ Solicitado' },
                  processando: { bg: 'var(--brand-light)', cor: 'var(--brand)',  label: '↻ Processando' },
                  pago:        { bg: 'var(--success-bg)', cor: 'var(--success)', label: '✓ Pago' },
                  rejeitado:   { bg: 'var(--error-bg)',   cor: 'var(--error)',   label: '✕ Rejeitado' },
                }
                const st = statusMap[s.status] || statusMap.solicitado
                return (
                  <div key={s.id} style={{
                    padding: 16, background: 'var(--surface-2)', borderRadius: 10,
                    border: '1px solid var(--border)',
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10, flexWrap: 'wrap', gap: 8 }}>
                      <div>
                        <div style={{ fontWeight: 700, fontSize: 18 }}>{fmt(s.valor_cents)}</div>
                        <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                          {s.perfis?.nome_artistico || s.perfis?.nome} · {s.perfis?.email}
                        </div>
                        <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                          Solicitado em {new Date(s.created_at).toLocaleString('pt-BR')}
                          {s.processed_at && ' · processado em ' + new Date(s.processed_at).toLocaleString('pt-BR')}
                        </div>
                      </div>
                      <span style={{ fontSize: 12, fontWeight: 600, padding: '4px 12px', borderRadius: 99, background: st.bg, color: st.cor }}>
                        {st.label}
                      </span>
                    </div>

                    <div style={{ padding: 10, background: 'var(--surface)', borderRadius: 8, marginBottom: 10, fontSize: 13 }}>
                      <strong>PayPal:</strong> <code>{s.paypal_email}</code>
                    </div>

                    {s.motivo_rejeicao && (
                      <div style={{ padding: 10, background: 'var(--error-bg)', borderRadius: 8, marginBottom: 10, fontSize: 12, color: 'var(--error)' }}>
                        <strong>Motivo da rejeição:</strong> {s.motivo_rejeicao}
                      </div>
                    )}

                    {s.status === 'solicitado' && (
                      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                        <button className="btn btn-secondary btn-sm" onClick={() => handleSaque(s.id, 'processando')}>↻ Em processamento</button>
                        <button className="btn btn-primary btn-sm"   onClick={() => handleSaque(s.id, 'pago')}>✓ Marcar como pago</button>
                        <button className="btn btn-danger btn-sm"    onClick={() => handleSaque(s.id, 'rejeitado')}>✕ Rejeitar</button>
                      </div>
                    )}
                    {s.status === 'processando' && (
                      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                        <button className="btn btn-primary btn-sm" onClick={() => handleSaque(s.id, 'pago')}>✓ Confirmar pagamento</button>
                        <button className="btn btn-danger btn-sm"  onClick={() => handleSaque(s.id, 'rejeitado')}>✕ Rejeitar</button>
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          )}
        </div>
      )}

      {/* ── AUDITORIA ── */}
      {aba === 'auditoria' && (
        <div className="card">
          <h2 style={{ fontSize: 15, fontWeight: 700, marginBottom: 14 }}>Auditoria de splits financeiros</h2>
          {audit.length === 0 ? (
            <p style={{ color: 'var(--text-muted)', fontSize: 13 }}>Nenhum split registrado ainda.</p>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--border)' }}>
                    {['Data', 'Obra', 'Compositor', 'Venda', 'Recebido', 'Status'].map(h => (
                      <th key={h} style={{ padding: '10px', textAlign: 'left', color: 'var(--text-muted)', fontWeight: 600, fontSize: 11, textTransform: 'uppercase', letterSpacing: 1, whiteSpace: 'nowrap' }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {audit.map((a, i) => (
                    <tr key={i} style={{ borderBottom: '1px solid var(--border)' }}>
                      <td style={{ padding: '10px', whiteSpace: 'nowrap' }}>{new Date(a.created_at).toLocaleDateString('pt-BR')}</td>
                      <td style={{ padding: '10px', fontWeight: 600 }}>{a.obra_nome}</td>
                      <td style={{ padding: '10px' }}>{a.compositor_nome}</td>
                      <td style={{ padding: '10px' }}>{fmt(a.valor_cents)}</td>
                      <td style={{ padding: '10px', color: 'var(--success)', fontWeight: 700 }}>{fmt(a.pago_cents)}</td>
                      <td style={{ padding: '10px' }}>
                        <span style={{
                          fontSize: 11, fontWeight: 600, padding: '2px 8px',
                          background: a.status === 'confirmada' ? 'var(--success-bg)' : 'var(--surface-2)',
                          color: a.status === 'confirmada' ? 'var(--success)' : 'var(--text-muted)',
                        }}>{a.status}</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* ── SEGURANÇA ── */}
      {aba === 'seguranca' && <SecurityPanel />}
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════
// PAINEL DE OBRAS (admin)
// Lista todas as obras com ID único e botões de GERAR/BAIXAR DOSSIÊ.
// ═══════════════════════════════════════════════════════════════════
function ObrasPanel() {
  const { playObra, obra: obraAtual, playing } = usePlayer()
  const [obras,   setObras]   = useState([])
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState('')
  const [query,   setQuery]   = useState('')
  const [busy,    setBusy]    = useState({})    // { obraId: 'gerar' | 'baixar' }
  const [copiedId, setCopiedId] = useState(null)
  const [feedback, setFeedback] = useState(null) // { obraId, type, message }

  async function load() {
    setLoading(true); setError('')
    try {
      const data = await api.get('/dossies/admin/obras')
      setObras(Array.isArray(data) ? data : [])
    } catch (e) {
      setError(e.message)
    } finally { setLoading(false) }
  }

  useEffect(() => { load() }, [])

  const filtered = !query.trim() ? obras : obras.filter(o => {
    const q = query.trim().toLowerCase()
    return (
      (o.id || '').toLowerCase().includes(q) ||
      (o.nome || '').toLowerCase().includes(q) ||
      (o.titular?.nome || '').toLowerCase().includes(q) ||
      (o.titular?.email || '').toLowerCase().includes(q)
    )
  })

  function showFeedback(obraId, type, message) {
    setFeedback({ obraId, type, message })
    setTimeout(() => setFeedback(prev => prev?.obraId === obraId ? null : prev), 4000)
  }

  async function handleGerar(obra) {
    if (obra.dossie && !confirm(
      `Esta obra já possui dossiê gerado em ${new Date(obra.dossie.created_at).toLocaleString('pt-BR')}.\n\n` +
      `Deseja regenerar (substituirá o anterior)?`
    )) return

    setBusy(prev => ({ ...prev, [obra.id]: 'gerar' }))
    try {
      const r = await api.post(`/dossies/obras/${obra.id}`, {})
      // Atualiza apenas a linha alterada — mais leve do que recarregar tudo
      setObras(prev => prev.map(o => o.id === obra.id
        ? { ...o, dossie: { id: r.id, hash_sha256: r.hash_sha256, created_at: r.created_at } }
        : o
      ))
      showFeedback(obra.id, 'success', '✓ Dossiê gerado com sucesso')
    } catch (e) {
      showFeedback(obra.id, 'error', '⚠ ' + (e.message || 'Erro ao gerar dossiê'))
    } finally {
      setBusy(prev => { const n = { ...prev }; delete n[obra.id]; return n })
    }
  }

  async function handleBaixar(obra) {
    if (!obra.dossie) return
    setBusy(prev => ({ ...prev, [obra.id]: 'baixar' }))
    try {
      const safeName = (obra.nome || obra.id).replace(/[^a-zA-Z0-9-_]/g, '_').slice(0, 60)
      await api.download(`/dossies/${obra.dossie.id}/download`, `dossie-${safeName}.zip`)
    } catch (e) {
      showFeedback(obra.id, 'error', '⚠ Erro ao baixar: ' + e.message)
    } finally {
      setBusy(prev => { const n = { ...prev }; delete n[obra.id]; return n })
    }
  }

  async function copyId(id) {
    try {
      await navigator.clipboard.writeText(id)
      setCopiedId(id)
      setTimeout(() => setCopiedId(prev => prev === id ? null : prev), 1400)
    } catch { /* ignora */ }
  }

  return (
    <div className="card">
      {/* MARCADOR DE VERSÃO — se você vê esta tarja amarela, o Admin.jsx novo
          foi carregado com sucesso. Pode remover depois de validado. */}
      <div style={{
        marginBottom: 14, padding: '8px 12px', borderRadius: 6,
        background: '#FEF3C7', color: '#92400E',
        fontSize: 12, fontWeight: 700, border: '1px solid #FCD34D',
      }}>
        ✓ Painel Obras carregado — versão atualizada (abril/2026)
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14, flexWrap: 'wrap', gap: 12 }}>
        <div>
          <h2 style={{ fontSize: 15, fontWeight: 700 }}>Todas as obras cadastradas</h2>
          <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>
            Cada obra tem um <strong>ID único</strong>. Use os botões para gerar
            ou baixar o dossiê (.zip) oficial.
          </p>
        </div>
        <button
          onClick={load}
          style={{ background: 'none', border: '1px solid var(--border)', padding: '6px 12px', borderRadius: 8, color: 'var(--brand)', fontSize: 13, cursor: 'pointer' }}>
          ↻ atualizar
        </button>
      </div>

      <div style={{ position: 'relative', marginBottom: 14 }}>
        <input
          type="search"
          value={query}
          onChange={e => setQuery(e.target.value)}
          placeholder="Buscar por nome, ID, titular ou email…"
          className="input"
          style={{ paddingLeft: 36 }}
        />
        <span style={{
          position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)',
          color: 'var(--text-muted)', pointerEvents: 'none',
        }}>⌕</span>
      </div>

      {loading && <p style={{ color: 'var(--text-muted)', fontSize: 13 }}>Carregando obras…</p>}
      {error && <p style={{ color: 'var(--error)', fontSize: 13 }}>{error}</p>}

      {!loading && !error && filtered.length === 0 && (
        <div style={{
          padding: 36, textAlign: 'center', color: 'var(--text-muted)',
          border: '1px dashed var(--border)', borderRadius: 10,
        }}>
          {obras.length === 0 ? 'Nenhuma obra cadastrada na plataforma ainda.' : 'Nenhuma obra encontrada para sua busca.'}
        </div>
      )}

      {!loading && filtered.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {filtered.map(o => {
            const isPlaying = obraAtual?.id === o.id && playing
            return (
            <div key={o.id} style={{
              padding: 14, background: 'var(--surface-2)', borderRadius: 10,
              border: '1px solid var(--border)',
              display: 'flex', alignItems: 'center', gap: 14, flexWrap: 'wrap',
            }}>
              {/* Botão de reproduzir / pausar — usa o GlobalPlayer */}
              <button
                onClick={() => playObra(o)}
                disabled={!o.audio_path}
                title={o.audio_path ? (isPlaying ? 'Pausar' : 'Tocar prévia') : 'Áudio indisponível'}
                style={{
                  width: 44, height: 44, borderRadius: 8,
                  background: o.audio_path
                    ? 'linear-gradient(135deg,#BE123C,#09090B)'
                    : 'var(--surface)',
                  color: o.audio_path ? '#fff' : 'var(--text-muted)',
                  border: o.audio_path ? 'none' : '1px solid var(--border)',
                  cursor: o.audio_path ? 'pointer' : 'not-allowed',
                  fontSize: 14, flexShrink: 0,
                }}>
                {isPlaying ? '⏸' : '▶'}
              </button>

              <div style={{ flex: 1, minWidth: 260 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                  <span style={{ fontWeight: 700, fontSize: 15 }}>
                    {o.nome || '(sem nome)'}
                  </span>
                  {o.genero && (
                    <span style={{
                      fontSize: 10, fontWeight: 700, padding: '2px 8px',
                      background: 'var(--brand-light)', color: 'var(--brand)',
                      borderRadius: 99, textTransform: 'uppercase', letterSpacing: 1,
                    }}>{o.genero}</span>
                  )}
                  {o.dossie && (
                    <span style={{
                      fontSize: 10, fontWeight: 700, padding: '2px 8px',
                      background: 'var(--success-bg)', color: 'var(--success)',
                      borderRadius: 99, letterSpacing: 1, textTransform: 'uppercase',
                    }}>✓ dossiê pronto</span>
                  )}
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 6, fontSize: 12 }}>
                  <span style={{ color: 'var(--text-muted)' }}>ID:</span>
                  <code style={{
                    fontFamily: 'monospace', fontSize: 11.5,
                    background: 'var(--surface)', padding: '2px 6px',
                    borderRadius: 4, border: '1px solid var(--border)',
                  }}>{o.id}</code>
                  <button
                    onClick={() => copyId(o.id)}
                    title="Copiar ID"
                    style={{
                      background: 'none', border: 'none', cursor: 'pointer',
                      color: copiedId === o.id ? 'var(--success)' : 'var(--text-muted)',
                      fontSize: 12, padding: '2px 4px',
                    }}>
                    {copiedId === o.id ? '✓ copiado' : '⎘'}
                  </button>
                </div>

                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
                  Titular: {o.titular?.nome || '—'}
                  {o.titular?.email && ` · ${o.titular.email}`}
                  {o.created_at && ` · cadastrada em ${new Date(o.created_at).toLocaleDateString('pt-BR')}`}
                  {typeof o.preco_cents === 'number' && ` · ${fmt(o.preco_cents)}`}
                </div>

                {feedback?.obraId === o.id && (
                  <div style={{
                    marginTop: 8, padding: '6px 10px', borderRadius: 6, fontSize: 12,
                    background: feedback.type === 'success' ? 'var(--success-bg)' : 'var(--error-bg)',
                    color: feedback.type === 'success' ? 'var(--success)' : 'var(--error)',
                  }}>
                    {feedback.message}
                  </div>
                )}
              </div>

              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                <button
                  onClick={() => handleGerar(o)}
                  disabled={!!busy[o.id]}
                  style={{
                    background: o.dossie ? 'transparent' : 'var(--brand)',
                    color: o.dossie ? 'var(--brand)' : '#fff',
                    border: '1px solid var(--brand)',
                    borderRadius: 6, padding: '8px 14px',
                    cursor: busy[o.id] ? 'not-allowed' : 'pointer',
                    fontSize: 12, fontWeight: 700, whiteSpace: 'nowrap',
                    opacity: busy[o.id] === 'gerar' ? 0.6 : 1,
                  }}>
                  {busy[o.id] === 'gerar'
                    ? '⏳ Gerando…'
                    : (o.dossie ? '↻ REGENERAR DOSSIÊ' : '📂 GERAR DOSSIÊ')}
                </button>

                <button
                  onClick={() => handleBaixar(o)}
                  disabled={!o.dossie || !!busy[o.id]}
                  title={!o.dossie ? 'Gere o dossiê primeiro' : 'Baixar ZIP do dossiê'}
                  style={{
                    background: !o.dossie ? 'var(--surface)' : 'var(--success)',
                    color: !o.dossie ? 'var(--text-muted)' : '#fff',
                    border: `1px solid ${!o.dossie ? 'var(--border)' : 'var(--success)'}`,
                    borderRadius: 6, padding: '8px 14px',
                    cursor: !o.dossie ? 'not-allowed' : (busy[o.id] ? 'wait' : 'pointer'),
                    fontSize: 12, fontWeight: 700, whiteSpace: 'nowrap',
                    opacity: busy[o.id] === 'baixar' ? 0.6 : 1,
                  }}>
                  {busy[o.id] === 'baixar' ? '⏳ Baixando…' : '⬇ BAIXAR DOSSIÊ'}
                </button>
              </div>
            </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

function SecurityPanel() {
  const [data, setData]     = useState(null)
  const [loading, setLoad]  = useState(true)
  const [err,   setErr]     = useState(null)

  async function check() {
    setLoad(true); setErr(null)
    try { setData(await api.get('/admin/security-check')) }
    catch (e) { setErr(e.message || 'Erro') }
    finally { setLoad(false) }
  }

  useEffect(() => { check() }, [])

  const statusColor = (s) => ({
    'ok-blocked': 'var(--success)', 'ok-empty': 'var(--success)',
    'leak': 'var(--error)', 'n/a': 'var(--text-muted)',
    'error': 'var(--warning)', 'unknown': 'var(--text-muted)',
  }[s] || 'var(--text-muted)')

  const statusLabel = (s) => ({
    'ok-blocked': '✓ Bloqueado', 'ok-empty': '✓ Protegido',
    'leak': '⚠ VAZAMENTO', 'n/a': '—', 'error': '⚠ Erro', 'unknown': '—',
  }[s] || s)

  const leaks = (data?.tables || []).filter(t => t.status === 'leak')

  return (
    <div className="card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 20 }}>
        <div>
          <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 4 }}>🔒 Painel de Segurança</h2>
          <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>
            Diagnóstico em tempo real das camadas de proteção: RLS, CORS, origens permitidas.
          </p>
        </div>
        <button className="btn btn-ghost" onClick={check} disabled={loading}>
          {loading ? 'Checando…' : 'Reverificar'}
        </button>
      </div>

      {err && <div style={{ padding: 12, background: 'var(--error-bg)', color: 'var(--error)', fontSize: 13, marginBottom: 16 }}>{err}</div>}

      {leaks.length > 0 && (
        <div style={{
          padding: 16, background: 'var(--error-bg)', border: '2px solid var(--error)',
          color: 'var(--error)', fontSize: 13, marginBottom: 20,
        }}>
          <strong style={{ fontSize: 14 }}>⚠ ATENÇÃO — {leaks.length} tabela(s) vazando dados para anônimos!</strong>
        </div>
      )}

      {data && (
        <>
          <div style={{ marginBottom: 24 }}>
            <h3 style={{ fontSize: 12, fontWeight: 700, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 10 }}>
              CORS — origens permitidas
            </h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {(data.allowed_origins || []).map(o => (
                <div key={o} style={{ padding: '8px 12px', border: '1px solid var(--border)', fontFamily: 'monospace', fontSize: 12 }}>
                  <span style={{ color: 'var(--success)' }}>✓</span> {o}
                </div>
              ))}
            </div>
          </div>

          <div>
            <h3 style={{ fontSize: 12, fontWeight: 700, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 10 }}>
              RLS — Row Level Security das tabelas
            </h3>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border)' }}>
                  <th style={{ padding: '10px', textAlign: 'left', color: 'var(--text-muted)', fontWeight: 600, fontSize: 11, textTransform: 'uppercase' }}>Tabela</th>
                  <th style={{ padding: '10px', textAlign: 'left', color: 'var(--text-muted)', fontWeight: 600, fontSize: 11, textTransform: 'uppercase' }}>Status</th>
                  <th style={{ padding: '10px', textAlign: 'left', color: 'var(--text-muted)', fontWeight: 600, fontSize: 11, textTransform: 'uppercase' }}>Detalhes</th>
                </tr>
              </thead>
              <tbody>
                {data.tables.map(t => (
                  <tr key={t.table} style={{ borderBottom: '1px solid var(--border)' }}>
                    <td style={{ padding: '10px', fontFamily: 'monospace', fontWeight: 600 }}>{t.table}</td>
                    <td style={{ padding: '10px', color: statusColor(t.status), fontWeight: 700 }}>{statusLabel(t.status)}</td>
                    <td style={{ padding: '10px', fontSize: 12, color: 'var(--text-muted)' }}>{t.message}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  )
}
