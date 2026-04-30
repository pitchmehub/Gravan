import React, { useEffect, useState, useCallback } from 'react'
import { api } from '../lib/api'

function StatusBadge({ status }) {
  const map = {
    ok:              { bg: 'rgba(34,197,94,.15)',  cor: '#16a34a', label: '✓ OK' },
    degradado:       { bg: 'rgba(245,158,11,.15)', cor: '#d97706', label: '⚠ Degradado' },
    erro:            { bg: 'rgba(239,68,68,.15)',  cor: '#dc2626', label: '✕ Erro' },
    nao_configurado: { bg: 'rgba(107,114,128,.15)', cor: '#6b7280', label: '○ Não configurado' },
    memoria:         { bg: 'rgba(107,114,128,.15)', cor: '#6b7280', label: '○ Em memória' },
  }
  const s = map[status] || { bg: 'var(--surface-2)', cor: 'var(--text-muted)', label: status }
  return (
    <span style={{
      fontSize: 11, fontWeight: 700, padding: '3px 10px',
      background: s.bg, color: s.cor, borderRadius: 99, whiteSpace: 'nowrap',
    }}>{s.label}</span>
  )
}

function Card({ titulo, status, children, acessorio }) {
  return (
    <div style={{
      background: 'var(--surface)',
      border: '1px solid var(--border)',
      borderRadius: 14, padding: '16px 18px',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10, gap: 8, flexWrap: 'wrap' }}>
        <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 1 }}>
          {titulo}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {acessorio}
          {status && <StatusBadge status={status} />}
        </div>
      </div>
      {children}
    </div>
  )
}

function Linha({ label, valor, mono = false }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10, padding: '4px 0', fontSize: 13, borderBottom: '1px dashed var(--border)' }}>
      <span style={{ color: 'var(--text-muted)' }}>{label}</span>
      <span style={{
        color: 'var(--text)',
        fontWeight: 600,
        fontFamily: mono ? 'ui-monospace, SFMono-Regular, Menlo, monospace' : 'inherit',
        textAlign: 'right', wordBreak: 'break-all',
      }}>{valor ?? '—'}</span>
    </div>
  )
}

export default function AdminSaude() {
  const [data, setData] = useState(null)
  const [erro, setErro] = useState('')
  const [loading, setLoading] = useState(true)
  const [auto, setAuto] = useState(true)
  const [ultimoCheck, setUltimoCheck] = useState(null)

  const carregar = useCallback(async () => {
    try {
      const r = await api.get('/admin/saude')
      setData(r); setErro(''); setUltimoCheck(new Date())
    } catch (e) {
      setErro(e.message || 'Falha ao consultar saúde do sistema.')
    } finally { setLoading(false) }
  }, [])

  useEffect(() => { carregar() }, [carregar])
  useEffect(() => {
    if (!auto) return
    const intv = setInterval(carregar, 15000)
    return () => clearInterval(intv)
  }, [auto, carregar])

  if (loading) return <div className="card"><p style={{ color: 'var(--text-muted)' }}>Verificando saúde do sistema…</p></div>
  if (erro) return (
    <div className="card">
      <p style={{ color: 'var(--error)', marginBottom: 8 }}>{erro}</p>
      <button onClick={carregar} className="btn btn-secondary btn-sm">↻ Tentar novamente</button>
    </div>
  )
  if (!data) return null

  const b = data.backend || {}
  const db = data.banco_dados || {}
  const stripe = data.stripe || {}
  const redis = data.redis || {}
  const env = data.variaveis_ambiente || {}
  const migr = data.migracoes || {}
  const csp = data.csp_violations || {}

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {/* Cabeçalho */}
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        flexWrap: 'wrap', gap: 12,
        padding: '14px 18px',
        background: data.status_geral === 'ok' ? 'rgba(34,197,94,.08)' : 'rgba(245,158,11,.08)',
        border: `1px solid ${data.status_geral === 'ok' ? 'rgba(34,197,94,.3)' : 'rgba(245,158,11,.3)'}`,
        borderRadius: 14,
      }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <h2 style={{ fontSize: 18, fontWeight: 800 }}>Saúde do sistema</h2>
            <StatusBadge status={data.status_geral} />
          </div>
          <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>
            Última verificação: {ultimoCheck ? ultimoCheck.toLocaleTimeString('pt-BR') : '—'}
            {auto && ' · atualização automática a cada 15s'}
          </p>
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <label style={{ fontSize: 12, color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: 6 }}>
            <input type="checkbox" checked={auto} onChange={e => setAuto(e.target.checked)} />
            auto-refresh
          </label>
          <button onClick={carregar} className="btn btn-secondary btn-sm">↻ atualizar</button>
        </div>
      </div>

      {/* Backend */}
      <Card titulo="Backend (API)" status="ok">
        <Linha label="Ambiente" valor={b.ambiente} />
        <Linha label="Tempo no ar" valor={b.uptime_humano} />
        <Linha label="Python" valor={b.python} />
        <Linha label="Servidor" valor={b.host} />
        <Linha label="Versão (commit)" valor={b.commit_short || '—'} mono />
        {b.commit_msg && <Linha label="Última mensagem" valor={b.commit_msg} />}
      </Card>

      {/* Banco de dados */}
      <Card titulo="Banco de dados (Supabase)" status={db.status}>
        {db.latencia_ms != null && <Linha label="Latência da consulta" valor={`${db.latencia_ms} ms`} />}
        {db.mensagem && <Linha label="Mensagem" valor={db.mensagem} />}
      </Card>

      {/* Stripe */}
      <Card titulo="Stripe (pagamentos)" status={stripe.status}>
        {stripe.modo && <Linha label="Modo" valor={stripe.modo === 'live' ? 'PRODUÇÃO (live)' : 'TESTE (test)'} />}
        {stripe.latencia_ms != null && <Linha label="Latência" valor={`${stripe.latencia_ms} ms`} />}
        {stripe.mensagem && <Linha label="Mensagem" valor={stripe.mensagem} />}
      </Card>

      {/* Redis / Cache */}
      <Card titulo="Cache / Rate limiter (Redis)" status={redis.status}>
        {redis.latencia_ms != null && <Linha label="Latência" valor={`${redis.latencia_ms} ms`} />}
        {redis.mensagem && <Linha label="Mensagem" valor={redis.mensagem} />}
      </Card>

      {/* Variáveis de ambiente */}
      <Card titulo="Variáveis de ambiente">
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 14 }}>
          {Object.entries(env).map(([grupo, items]) => (
            <div key={grupo}>
              <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 6 }}>
                {grupo}
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                {items.map(it => (
                  <div key={it.name} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 12, padding: '4px 8px', background: 'var(--surface-2)', borderRadius: 6 }}>
                    <span style={{ fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace', fontSize: 11 }}>{it.name}</span>
                    <span style={{
                      fontSize: 10, fontWeight: 700, padding: '2px 7px', borderRadius: 99,
                      background: it.set ? 'rgba(34,197,94,.15)' : 'rgba(239,68,68,.15)',
                      color: it.set ? '#16a34a' : '#dc2626',
                    }}>
                      {it.set ? 'OK' : 'AUSENTE'}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* Migrações */}
      {Array.isArray(migr) && migr.length > 0 && (
        <Card
          titulo="Migrações de banco"
          status={migr.some(m => m.status === 'missing') ? 'degradado' : 'ok'}
          acessorio={
            <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
              {migr.filter(m => m.status === 'applied').length}/{migr.length} aplicadas
            </span>
          }
        >
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4, maxHeight: 240, overflowY: 'auto' }}>
            {migr.map((m, i) => (
              <div key={i} style={{
                display: 'flex', justifyContent: 'space-between', gap: 8,
                fontSize: 12, padding: '6px 10px',
                background: 'var(--surface-2)', borderRadius: 6,
              }}>
                <span style={{ fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace' }}>
                  {m.name || m.id || `#${i}`}
                </span>
                <StatusBadge status={
                  m.status === 'applied' ? 'ok' :
                  m.status === 'missing' ? 'erro' : 'degradado'
                } />
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* CSP violations */}
      <Card
        titulo="Violações de política de segurança (CSP)"
        status={csp.total_capturadas > 0 ? 'degradado' : 'ok'}
        acessorio={
          <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
            {csp.total_capturadas || 0} registrada(s) desde o boot
          </span>
        }
      >
        {(!csp.ultimas || csp.ultimas.length === 0) ? (
          <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>Nenhuma violação capturada.</p>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6, maxHeight: 320, overflowY: 'auto' }}>
            {csp.ultimas.map((v, i) => {
              const r = v.payload?.['csp-report'] || v.payload || {}
              return (
                <div key={i} style={{ padding: 10, background: 'var(--surface-2)', borderRadius: 8, fontSize: 12 }}>
                  <div style={{ color: 'var(--text-muted)', fontSize: 11, marginBottom: 4 }}>{v.ts}</div>
                  <div><strong>{r['violated-directive'] || r.violatedDirective || '—'}</strong></div>
                  <div style={{ fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace', fontSize: 11, color: 'var(--text-secondary)', marginTop: 2 }}>
                    bloqueado: {r['blocked-uri'] || r.blockedURL || '—'}
                  </div>
                  {(r['document-uri'] || r.documentURL) && (
                    <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>
                      origem: {r['document-uri'] || r.documentURL}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </Card>
    </div>
  )
}
