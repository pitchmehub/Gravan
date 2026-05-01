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

  const [emailDest, setEmailDest] = useState('')
  const [emailEnviando, setEmailEnviando] = useState(false)
  const [emailResult, setEmailResult] = useState(null)

  async function testarEmail() {
    if (!emailDest.trim()) return
    setEmailEnviando(true)
    setEmailResult(null)
    try {
      const r = await api.post('/admin/test-email', { to: emailDest.trim() })
      setEmailResult({ ok: true, data: r })
    } catch (e) {
      let data = null
      try { data = JSON.parse(e.message) } catch {}
      setEmailResult({ ok: false, msg: e.message, data })
    } finally { setEmailEnviando(false) }
  }

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

      {/* Teste de e-mail */}
      <Card titulo="Teste de e-mail (SMTP)">
        <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 12 }}>
          Dispara um e-mail de teste para validar a configuração SMTP do servidor de produção.
          Se o campo SMTP_HOST não estiver configurado, o envio será <strong>simulado</strong> (aparece no log do servidor, não chega à caixa de entrada).
        </p>
        <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
          <input
            className="input"
            type="email"
            placeholder="Destinatário (ex: voce@email.com)"
            value={emailDest}
            onChange={e => { setEmailDest(e.target.value); setEmailResult(null) }}
            onKeyDown={e => { if (e.key === 'Enter') testarEmail() }}
            style={{ flex: 1, fontSize: 13 }}
          />
          <button
            className="btn btn-secondary btn-sm"
            onClick={testarEmail}
            disabled={emailEnviando || !emailDest.trim()}
          >
            {emailEnviando ? 'Enviando…' : 'Enviar teste'}
          </button>
        </div>

        {emailResult && (() => {
          const cfg = emailResult.data?.configuracao || {}
          const simulado = emailResult.data?.simulado
          return (
            <div style={{
              padding: 14, borderRadius: 10, fontSize: 12,
              background: emailResult.ok
                ? (simulado ? 'rgba(245,158,11,.08)' : 'rgba(34,197,94,.08)')
                : 'rgba(239,68,68,.08)',
              border: `1px solid ${emailResult.ok
                ? (simulado ? 'rgba(245,158,11,.4)' : 'rgba(34,197,94,.4)')
                : 'rgba(239,68,68,.4)'}`,
            }}>
              <div style={{
                fontWeight: 700, fontSize: 13, marginBottom: 10,
                color: emailResult.ok
                  ? (simulado ? '#d97706' : '#16a34a')
                  : '#dc2626',
              }}>
                {emailResult.ok
                  ? (simulado
                      ? 'Simulado — SMTP não configurado. Verifique o log do servidor.'
                      : `E-mail enviado com sucesso para ${emailResult.data?.enviado_para}`)
                  : 'Falha no envio'}
              </div>

              {Object.keys(cfg).length > 0 && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 4, marginBottom: emailResult.data?.erro ? 10 : 0 }}>
                  <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 4 }}>
                    Configuração SMTP detectada
                  </div>
                  {Object.entries(cfg).filter(([k]) => k !== 'configurado').map(([k, v]) => (
                    <div key={k} style={{ display: 'flex', justifyContent: 'space-between', padding: '3px 8px', background: 'var(--surface-2)', borderRadius: 6 }}>
                      <span style={{ fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace', fontSize: 11, color: 'var(--text-muted)' }}>{k}</span>
                      <span style={{ fontWeight: 600, fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace', fontSize: 11 }}>{String(v)}</span>
                    </div>
                  ))}
                </div>
              )}

              {emailResult.data?.erro && (
                <pre style={{
                  marginTop: 10, padding: 10, borderRadius: 8,
                  background: 'rgba(239,68,68,.08)', border: '1px solid rgba(239,68,68,.2)',
                  fontSize: 11, color: '#dc2626', whiteSpace: 'pre-wrap', wordBreak: 'break-all',
                  maxHeight: 200, overflowY: 'auto',
                }}>{emailResult.data.erro}</pre>
              )}

              {!emailResult.ok && !emailResult.data && (
                <p style={{ color: 'var(--error)', marginTop: 6 }}>{emailResult.msg}</p>
              )}
            </div>
          )
        })()}
      </Card>

      {/* Mapa de e-mails automáticos */}
      <Card titulo="E-mails automáticos — mapa completo">
        {(() => {
          const grupos = [
            {
              grupo: 'Saques',
              cor: '#1d4ed8',
              emails: [
                { fn: 'render_otp_email', gatilho: 'Usuário solicita saque', destinatario: 'Titular da carteira', descricao: 'Código OTP de confirmação (expira em 10 min).' },
                { fn: 'render_saque_agendado_email', gatilho: 'OTP confirmado — saque entra na janela de 24h', destinatario: 'Titular da carteira', descricao: 'Confirmação de agendamento + link de cancelamento de emergência.' },
                { fn: 'render_saque_pago_email', gatilho: 'Saque processado pelo Stripe', destinatario: 'Titular da carteira', descricao: 'Comprovante de transferência com ID Stripe.' },
                { fn: 'render_saque_cancelado_email', gatilho: 'Saque cancelado (pelo app ou pelo link do e-mail)', destinatario: 'Titular da carteira', descricao: 'Aviso de cancelamento e orientações de segurança.' },
              ],
            },
            {
              grupo: 'Ofertas de licenciamento (obra com editora terceira)',
              cor: '#d97706',
              emails: [
                { fn: 'render_oferta_editora_email', gatilho: 'Pagamento da oferta confirmado no Stripe', destinatario: 'Editora terceira', descricao: 'Nova oferta de licença — prazo para aceitar e assinar o contrato trilateral.' },
                { fn: 'render_oferta_notificacao_compositor_email', gatilho: 'Pagamento da oferta confirmado no Stripe', destinatario: 'Compositor(es) da obra', descricao: 'Aviso de que há uma oferta em andamento na obra.' },
                { fn: 'render_oferta_reminder_email', gatilho: 'Job de lembrete (watchdog) quando prazo está próximo', destinatario: 'Editora terceira', descricao: 'Lembrete de oferta prestes a expirar com horas úteis restantes.' },
                { fn: 'render_oferta_lembrete_compositor_email', gatilho: 'Job de lembrete (watchdog)', destinatario: 'Compositor(es)', descricao: 'Lembrete de oferta prestes a expirar.' },
                { fn: 'render_oferta_expirada_comprador_email', gatilho: 'Oferta expira sem resposta da editora', destinatario: 'Comprador (intérprete)', descricao: 'Aviso de estorno integral do valor pago.' },
                { fn: 'render_oferta_expirada_editora_email', gatilho: 'Oferta expira sem resposta', destinatario: 'Editora terceira', descricao: 'Aviso de expiração e orientação de cadastro.' },
                { fn: 'render_oferta_expirada_compositor_email', gatilho: 'Oferta expira sem resposta da editora', destinatario: 'Compositor(es)', descricao: 'Aviso de que a oferta expirou.' },
                { fn: 'render_oferta_concluida_email', gatilho: 'Todas as partes assinaram o contrato', destinatario: 'Comprador (intérprete)', descricao: 'Confirmação de licença ativa + link para baixar o áudio.' },
                { fn: 'render_oferta_concluida_compositor_email', gatilho: 'Todas as partes assinaram o contrato', destinatario: 'Compositor(es)', descricao: 'Confirmação de licença concluída.' },
                { fn: 'render_oferta_concluida_editora_terceira_email', gatilho: 'Todas as partes assinaram o contrato', destinatario: 'Editora terceira', descricao: 'Confirmação de licença concluída.' },
              ],
            },
            {
              grupo: 'Contrato de licenciamento (obra sem editora terceira)',
              cor: '#16a34a',
              emails: [
                { fn: 'render_licenciamento_concluido_email', gatilho: 'Contrato de licenciamento assinado por todas as partes', destinatario: 'Compositor, intérprete e editora (se houver)', descricao: 'Contrato ativo — enviado a cada papel com os detalhes do contrato.' },
              ],
            },
            {
              grupo: 'Exclusividade e rescisão',
              cor: '#BE123C',
              emails: [
                { fn: 'render_rescisao_exclusividade_email', gatilho: 'Compositor rescinde contrato de exclusividade', destinatario: 'Intérprete, editora-mãe e editora terceira', descricao: 'Aviso formal de rescisão com os dados da obra.' },
              ],
            },
            {
              grupo: 'Convites (sistema de agregação de editoras)',
              cor: '#6b7280',
              emails: [
                { fn: 'render_convite_novo_usuario_email', gatilho: 'Editora convida artista que ainda não tem cadastro', destinatario: 'E-mail do convidado (novo usuário)', descricao: 'Link para definir senha e responder ao convite de agregação.' },
                { fn: 'render_convite_usuario_existente_email', gatilho: 'Editora convida artista já cadastrado', destinatario: 'Usuário existente', descricao: 'Notificação de convite de agregação com link para responder.' },
              ],
            },
          ]

          return (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
              {grupos.map(g => (
                <div key={g.grupo}>
                  <div style={{
                    fontSize: 11, fontWeight: 700, textTransform: 'uppercase',
                    letterSpacing: 1, color: g.cor, marginBottom: 8,
                    borderBottom: `2px solid ${g.cor}22`, paddingBottom: 4,
                  }}>
                    {g.grupo}
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                    {g.emails.map(e => (
                      <div key={e.fn} style={{
                        display: 'grid',
                        gridTemplateColumns: 'minmax(220px,1fr) minmax(160px,.7fr) minmax(0,1.2fr)',
                        gap: 10, alignItems: 'start',
                        padding: '8px 10px',
                        background: 'var(--surface-2)', borderRadius: 8, fontSize: 12,
                      }}>
                        <div>
                          <div style={{
                            fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
                            fontSize: 10, color: g.cor, fontWeight: 700, marginBottom: 3,
                          }}>{e.fn}</div>
                          <div style={{ color: 'var(--text)', fontWeight: 600, fontSize: 12 }}>
                            {e.descricao}
                          </div>
                        </div>
                        <div>
                          <div style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 2 }}>Gatilho</div>
                          <div style={{ color: 'var(--text-secondary)', fontSize: 12 }}>{e.gatilho}</div>
                        </div>
                        <div>
                          <div style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 2 }}>Destinatário</div>
                          <div style={{ color: 'var(--text-secondary)', fontSize: 12 }}>{e.destinatario}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
              <p style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
                Todos os envios passam por <code>send_email()</code> em <code>services/email_service.py</code>.
                Se SMTP_HOST não estiver configurado no servidor, os e-mails são <strong>simulados</strong> (aparecem no log do Render mas não chegam ao destinatário).
              </p>
            </div>
          )
        })()}
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
