import React, { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api } from '../lib/api'
import { useAuth } from '../contexts/AuthContext'

function fmt(cents) {
  return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format((cents ?? 0) / 100)
}

const METODOS = [
  { id: 'pix',     icone: '◎', label: 'PIX',              desc: 'Aprovação imediata · sem taxas extras' },
  { id: 'credito', icone: '▪', label: 'Cartão de Crédito', desc: 'Visa, Mastercard, Elo, Amex' },
  { id: 'debito',  icone: '▫', label: 'Cartão de Débito',  desc: 'Débito à vista' },
]

export default function Comprar() {
  const { obraId } = useParams()
  const navigate   = useNavigate()
  const { perfil } = useAuth()

  // Bloqueia compra se o cadastro inicial ainda não foi preenchido (fluxo pós-login).
  useEffect(() => {
    if (perfil === undefined || perfil === null) return
    if (!perfil.role) {
      navigate('/escolher-tipo-perfil', { replace: true })
      return
    }
    if (!perfil.cadastro_completo) {
      try { localStorage.removeItem('pitchme_skip_cadastro') } catch {}
      const destino = perfil.role === 'publisher' ? '/cadastro-editora' : '/perfil/completar'
      navigate(destino, { replace: true, state: { motivo: 'compra' } })
    }
  }, [perfil, navigate])

  const [obra,    setObra]    = useState(null)
  const [metodo,  setMetodo]  = useState('credito')
  const [loading, setLoading] = useState(true)
  const [pagando, setPagando] = useState(false)
  const [erro,    setErro]    = useState('')
  const [concordo,     setConcordo]     = useState(false)
  const [verContrato,  setVerContrato]  = useState(false)
  const [contratoTpl,  setContratoTpl]  = useState('')

  useEffect(() => {
    api.get(`/catalogo/${obraId}`)
      .then(setObra)
      .catch(() => navigate('/descoberta'))
      .finally(() => setLoading(false))
  }, [obraId])

  async function confirmar() {
    if (!concordo) {
      setErro('Marque a caixa de concordância com o contrato antes de prosseguir.')
      return
    }
    setPagando(true); setErro('')
    try {
      const { checkout_url } = await api.post('/stripe/checkout', {
        obra_id: obraId, metodo, concordo_contrato: true,
      })
      window.location.href = checkout_url
    } catch (e) {
      setErro(e.message)
      setPagando(false)
    }
  }

  async function abrirContrato() {
    setVerContrato(true)
    if (contratoTpl) return
    try {
      const d = await api.get('/landing/content')
      const tpl = d?.contrato_licenciamento_template || d?.contrato_licenciamento_preview || ''
      if (tpl) { setContratoTpl(tpl); return }
    } catch (_) { /* fallback abaixo */ }
    // Fallback: texto resumido estático (cláusulas-chave)
    setContratoTpl(CONTRATO_RESUMO)
  }

  if (loading) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: 400 }}>
      <p style={{ color: 'var(--text-muted)' }}>Carregando…</p>
    </div>
  )
  if (!obra) return null

  return (
    <div style={{ padding: 32, maxWidth: 560 }}>
      <button
        onClick={() => navigate('/descoberta')}
        style={{ background: 'none', border: 'none', color: 'var(--brand)', cursor: 'pointer', fontSize: 14, padding: 0, marginBottom: 20 }}
      >
        ← Voltar ao catálogo
      </button>

      <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 4 }}>Finalizar licença</h1>
      <p style={{ color: 'var(--text-muted)', fontSize: 14, marginBottom: 24 }}>Licenciamento de composição musical</p>

      <div className="card" style={{ marginBottom: 20 }}>
        <div style={{ display: 'flex', gap: 16, alignItems: 'center', marginBottom: 16 }}>
          <div style={{
            width: 56, height: 56, borderRadius: 12,
            background: 'linear-gradient(135deg, #BE123C, #09090B)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 24, flexShrink: 0,
          }}>♪</div>
          <div>
            <div style={{ fontWeight: 700, fontSize: 17 }}>{obra.nome}</div>
            <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>
              {obra.titular_nome}
              {obra.genero && ` · ${obra.genero}`}
            </div>
          </div>
        </div>

        {obra.coautores?.length > 0 && (
          <div style={{ marginBottom: 14 }}>
            <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 6 }}>Compositores</div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
              {obra.coautores.map(c => (
                <span key={c.perfil_id} style={{
                  background: 'var(--brand-light)', color: 'var(--brand)',
                  padding: '3px 10px', borderRadius: 99, fontSize: 12,
                }}>
                  {c.nome}
                </span>
              ))}
            </div>
          </div>
        )}

        <div style={{
          display: 'flex', justifyContent: 'space-between',
          fontWeight: 700, fontSize: 22,
          borderTop: '1px solid var(--border)', paddingTop: 16, marginTop: 8,
        }}>
          <span>Total</span>
          <span style={{ color: 'var(--brand)' }}>{fmt(obra.preco_cents)}</span>
        </div>
      </div>

      <div className="card" style={{ marginBottom: 20 }}>
        <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-muted)', letterSpacing: 1, marginBottom: 14 }}>
          MÉTODO DE PAGAMENTO
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {METODOS.map(m => (
            <label key={m.id} style={{
              display: 'flex', alignItems: 'center', gap: 14,
              padding: '13px 16px', borderRadius: 'var(--radius-md)',
              border: `2px solid ${metodo === m.id ? 'var(--brand)' : 'var(--border)'}`,
              background: metodo === m.id ? 'var(--brand-light)' : 'var(--surface)',
              cursor: 'pointer', transition: 'all .15s',
            }}>
              <input
                type="radio" name="metodo" value={m.id}
                checked={metodo === m.id}
                onChange={() => setMetodo(m.id)}
                style={{ accentColor: 'var(--brand)', width: 16, height: 16 }}
              />
              <span style={{ fontSize: 22, color: metodo === m.id ? 'var(--brand)' : 'var(--text-muted)' }}>
                {m.icone}
              </span>
              <div>
                <div style={{ fontWeight: 600, fontSize: 14 }}>{m.label}</div>
                <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{m.desc}</div>
              </div>
            </label>
          ))}
        </div>
      </div>

      {erro && (
        <div className="card" style={{ background: 'var(--error-bg)', border: '1px solid var(--error)', marginBottom: 16 }}>
          <p style={{ color: 'var(--error)', fontSize: 14 }}>{erro}</p>
        </div>
      )}

      {/* Checkbox obrigatório: concordância com o contrato */}
      <div className="card" data-testid="card-concordancia" style={{
        marginBottom: 16,
        background: concordo ? 'var(--surface-2)' : '#FFF8E7',
        border: concordo ? '1px solid var(--border)' : '1px solid #F5C518',
      }}>
        <label htmlFor="chk-contrato-lic" style={{
          display: 'flex', gap: 10, alignItems: 'flex-start', cursor: 'pointer',
          fontSize: 13.5, lineHeight: 1.6,
        }}>
          <input
            id="chk-contrato-lic"
            data-testid="checkbox-contrato-licenciamento"
            type="checkbox"
            checked={concordo}
            onChange={e => { setConcordo(e.target.checked); if (e.target.checked) setErro('') }}
            style={{ marginTop: 3, accentColor: 'var(--brand)', width: 16, height: 16, flexShrink: 0 }}
          />
          <span>
            Declaro que li e concordo com os termos do <b>Contrato de Autorização para
            Gravação e Exploração de Obra Musical</b>, autorizando o licenciamento da
            obra <b>{obra.nome}</b> nas condições apresentadas (splits, royalties ECAD
            80/10/10, fonograma 2%, foro Rio de Janeiro). Ao clicar em "Pagar", minha
            assinatura eletrônica será registrada (MP 2.200-2/2001 e Lei 14.063/2020).
          </span>
        </label>
        <div style={{ marginTop: 10, paddingLeft: 26 }}>
          <button
            data-testid="link-ver-contrato"
            type="button"
            onClick={(e) => {
              e.preventDefault()
              e.stopPropagation()
              abrirContrato()
            }}
            style={{
              background: 'none', border: 'none', padding: 0, cursor: 'pointer',
              color: 'var(--brand)', fontWeight: 600, textDecoration: 'underline',
              font: 'inherit', fontSize: 12.5,
            }}
          >📄 Ver texto completo do contrato</button>
        </div>
      </div>

      <button
        className="btn btn-primary"
        style={{ width: '100%', justifyContent: 'center', fontSize: 16, padding: '14px 20px', opacity: concordo ? 1 : 0.5 }}
        onClick={confirmar}
        disabled={pagando || !concordo}
        data-testid="btn-pagar"
        title={!concordo ? 'Marque a concordância com o contrato para prosseguir.' : undefined}
      >
        {pagando ? 'Redirecionando…' : `🔒 Pagar com Stripe · ${fmt(obra.preco_cents)}`}
      </button>

      <div style={{
        marginTop: 14, padding: 12,
        background: 'var(--surface-2)', borderRadius: 8,
        display: 'flex', alignItems: 'center', gap: 10,
      }}>
        <span style={{ fontSize: 16 }}>🔐</span>
        <p style={{ fontSize: 12, color: 'var(--text-muted)', margin: 0 }}>
          Você será redirecionado para a página segura do Stripe para concluir o pagamento.
        </p>
      </div>

      {verContrato && (
        <div
          data-testid="modal-contrato"
          onClick={e => { if (e.target === e.currentTarget) setVerContrato(false) }}
          style={{
            position: 'fixed', inset: 0, background: 'rgba(0,0,0,.6)', backdropFilter: 'blur(4px)',
            display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 900, padding: 16,
          }}
        >
          <div style={{
            background: '#fff', borderRadius: 14, width: '100%', maxWidth: 760,
            maxHeight: '88vh', display: 'flex', flexDirection: 'column',
          }}>
            <div style={{
              padding: '18px 22px', borderBottom: '1px solid var(--border)',
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            }}>
              <h2 style={{ fontSize: 15, fontWeight: 700 }}>
                Contrato de Autorização — Pré-visualização
              </h2>
              <button onClick={() => setVerContrato(false)} style={{
                background: 'none', border: 'none', fontSize: 24, cursor: 'pointer', color: 'var(--text-muted)',
              }}>×</button>
            </div>
            <div style={{
              padding: '18px 22px', overflowY: 'auto', flex: 1, fontSize: 12.5,
              lineHeight: 1.7, color: 'var(--text-secondary)', whiteSpace: 'pre-wrap',
            }}>
              {contratoTpl || 'Carregando…'}
            </div>
            <div style={{
              padding: '12px 22px', borderTop: '1px solid var(--border)',
              display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8,
            }}>
              <p style={{ fontSize: 11, color: 'var(--text-muted)', margin: 0 }}>
                O contrato final, com todos os seus dados preenchidos, será gerado após a compra
                e ficará disponível em <b>Meus contratos → Licenciamentos</b>.
              </p>
              <button className="btn btn-primary" onClick={() => { setConcordo(true); setVerContrato(false) }}>
                Li e concordo
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// Resumo apresentado quando o template completo não está disponível no banco.
// Os campos com {{placeholders}} são preenchidos automaticamente na geração
// real do contrato (depois da confirmação do pagamento).
const CONTRATO_RESUMO = `CONTRATO DE AUTORIZAÇÃO PARA GRAVAÇÃO E EXPLORAÇÃO DE OBRA MUSICAL

Cláusulas-chave deste contrato (versão resumida para visualização antes da compra):

CLÁUSULA 1 — OBJETO
Autorização para fixação da obra musical em fonograma e sua exploração comercial pelo LICENCIADO.

CLÁUSULA 2 — CESSÃO DE DIREITOS
O(s) AUTOR(ES) autoriza(m), de forma irrevogável e irretratável, o LICENCIADO a:
 I. Reproduzir a obra em qualquer formato ou suporte;
 II. Distribuir e comercializar em meios físicos e digitais;
 III. Disponibilizar em plataformas de streaming (Spotify, Apple Music, etc.);
 IV. Utilizar em redes sociais e plataformas digitais;
 V. Sincronizar com conteúdos audiovisuais.

CLÁUSULA 3 — TERRITÓRIO E PRAZO
Autorização mundial, pelo prazo integral de proteção legal (Lei 9.610/98).

CLÁUSULA 5 — REMUNERAÇÃO
 5.1 Buyout: valor pago através do Stripe (apresentado acima).
 5.2 Royalties ECAD: 80% autores / 10% intérprete / 10% PITCH.ME.
 5.3 Royalties de fonograma: 2% para autores, via distribuidora digital.

CLÁUSULA 10 — SPLIT ENTRE COAUTORES
Divisão conforme percentuais cadastrados na obra na plataforma PITCH.ME.

CLÁUSULA 11 — FORO
Comarca do Rio de Janeiro/RJ.

ASSINATURAS ELETRÔNICAS
Este instrumento é firmado eletronicamente (MP 2.200-2/2001; Lei 14.063/2020).
O contrato completo, preenchido com todos os dados reais, estará disponível
em "Meus contratos → Licenciamentos" após a confirmação do pagamento.`
