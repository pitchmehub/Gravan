import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { api } from '../lib/api'
import DEFAULT_CONTENT from '../config/landing.default.json'

/**
 * Admin — Editor da Landing Page
 * Permite editar todos os textos/imagens da landing em tempo real.
 * Só acessível para usuários com role = 'administrador'.
 */
export default function AdminLanding() {
  const { perfil } = useAuth()
  const navigate   = useNavigate()
  const [content,  setContent]  = useState(null)
  const [original, setOriginal] = useState(null)
  const [saving,   setSaving]   = useState(false)
  const [msg,      setMsg]      = useState(null)

  useEffect(() => {
    if (perfil && perfil.role !== 'administrador') {
      navigate('/descoberta')
      return
    }
    api.get('/landing/content').then(data => {
      const merged = { ...DEFAULT_CONTENT, ...(data || {}) }
      setContent(merged)
      setOriginal(JSON.parse(JSON.stringify(merged)))
    }).catch(() => {
      setContent(DEFAULT_CONTENT)
      setOriginal(JSON.parse(JSON.stringify(DEFAULT_CONTENT)))
    })
  }, [perfil])

  function setField(path, value) {
    setContent(prev => {
      const next = JSON.parse(JSON.stringify(prev))
      const keys = path.split('.')
      let obj = next
      for (let i = 0; i < keys.length - 1; i++) {
        if (!obj[keys[i]]) obj[keys[i]] = {}
        obj = obj[keys[i]]
      }
      obj[keys[keys.length - 1]] = value
      return next
    })
  }

  function setArrayField(path, idx, key, value) {
    setContent(prev => {
      const next = JSON.parse(JSON.stringify(prev))
      const keys = path.split('.')
      let obj = next
      for (let i = 0; i < keys.length - 1; i++) obj = obj[keys[i]]
      const arr = obj[keys[keys.length - 1]]
      if (!Array.isArray(arr)) return prev
      arr[idx] = { ...arr[idx], [key]: value }
      return next
    })
  }

  async function save() {
    setSaving(true); setMsg(null)
    try {
      await api.request('PUT', '/landing/content', { body: content })
      setOriginal(JSON.parse(JSON.stringify(content)))
      setMsg({ type: 'success', text: '✓ Salvo! Abra a landing em outra aba e dê F5 para ver as mudanças.' })
    } catch (e) {
      setMsg({ type: 'error', text: e.message || 'Erro ao salvar' })
    } finally {
      setSaving(false)
      setTimeout(() => setMsg(null), 5000)
    }
  }

  function reset() {
    if (!confirm('Descartar todas as alterações não salvas?')) return
    setContent(JSON.parse(JSON.stringify(original)))
  }

  function resetDefaults() {
    if (!confirm('Restaurar conteúdo ORIGINAL (apaga tudo que você editou)?')) return
    setContent(JSON.parse(JSON.stringify(DEFAULT_CONTENT)))
  }

  if (!content) {
    return <div style={{ padding: 40, color: 'var(--text-muted)' }}>Carregando editor…</div>
  }

  const changed = JSON.stringify(content) !== JSON.stringify(original)

  return (
    <div style={{ padding: 32, maxWidth: 1100 }}>
      {/* Header sticky */}
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        marginBottom: 24, paddingBottom: 16, borderBottom: '1px solid var(--border)',
      }}>
        <div>
          <h1 style={{ fontSize: 26, fontFamily: "'Space Grotesk', sans-serif", letterSpacing: '-0.02em' }}>
            Editor da Landing
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: 13, marginTop: 4 }}>
            Edite cada bloco da landing · as mudanças ficam salvas no servidor
          </p>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <a className="btn btn-ghost" href="/" target="_blank" rel="noopener">
            Abrir landing ↗
          </a>
          <button className="btn btn-ghost" onClick={resetDefaults}>Padrão</button>
          <button className="btn btn-ghost" onClick={reset} disabled={!changed}>Desfazer</button>
          <button className="btn btn-primary" onClick={save} disabled={saving || !changed} data-testid="admin-landing-save">
            {saving ? 'Salvando…' : (changed ? 'Salvar alterações' : 'Sem alterações')}
          </button>
        </div>
      </div>

      {msg && (
        <div style={{
          padding: 12, marginBottom: 20, fontSize: 13,
          background: msg.type === 'success' ? 'var(--success-bg)' : 'var(--error-bg)',
          color:      msg.type === 'success' ? 'var(--success)'    : 'var(--error)',
          border: `1px solid ${msg.type === 'success' ? 'rgba(22,163,74,.3)' : 'rgba(220,38,38,.3)'}`,
        }}>{msg.text}</div>
      )}

      {/* BRAND + NAV */}
      <Section title="01 · Marca & Navegação">
        <Row>
          <Field label="Nome da marca (logo)"  value={content.brand.logoText}  onChange={v => setField('brand.logoText', v)} />
          <Field label="Eyebrow (badge hero)"  value={content.brand.eyebrow}   onChange={v => setField('brand.eyebrow', v)} />
        </Row>
        <Row>
          <Field label="Link 1 (nav)"          value={content.nav.link1}       onChange={v => setField('nav.link1', v)} />
          <Field label="Link 2 (nav)"          value={content.nav.link2}       onChange={v => setField('nav.link2', v)} />
          <Field label="Link 3 (nav)"          value={content.nav.link3}       onChange={v => setField('nav.link3', v)} />
        </Row>
        <Row>
          <Field label="CTA quando logado"     value={content.nav.ctaLogado}   onChange={v => setField('nav.ctaLogado', v)} />
          <Field label="CTA quando deslogado"  value={content.nav.ctaDeslogado} onChange={v => setField('nav.ctaDeslogado', v)} />
        </Row>
      </Section>

      {/* HERO */}
      <Section title="02 · Hero (banner principal)">
        <Row>
          <Field label="Título — linha 1"      value={content.hero.titleLine1} onChange={v => setField('hero.titleLine1', v)} />
          <Field label="Título — linha 2 (itálica)" value={content.hero.titleLine2} onChange={v => setField('hero.titleLine2', v)} />
          <Field label="Título — linha 3"      value={content.hero.titleLine3} onChange={v => setField('hero.titleLine3', v)} />
        </Row>
        <Field label="Subtítulo" value={content.hero.subtitle}      onChange={v => setField('hero.subtitle', v)} textarea />
        <Row>
          <Field label="Botão principal"       value={content.hero.ctaPrimary}   onChange={v => setField('hero.ctaPrimary', v)} />
          <Field label="Botão secundário"      value={content.hero.ctaSecondary} onChange={v => setField('hero.ctaSecondary', v)} />
        </Row>
        <Row>
          <Field label="URL da imagem hero"    value={content.hero.imageUrl}     onChange={v => setField('hero.imageUrl', v)} />
          <Field label="Label sobre a imagem"  value={content.hero.imageLabel}   onChange={v => setField('hero.imageLabel', v)} />
        </Row>
      </Section>

      {/* STATS */}
      <Section title="03 · Estatísticas (hero)">
        <div style={{ marginBottom: 12 }}>
          <label style={{ fontSize: 13, display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
            <input type="checkbox" checked={content.stats.showRealNumbers !== false}
                   onChange={e => setField('stats.showRealNumbers', e.target.checked)} />
            Mostrar números REAIS do banco (desmarque para usar os valores fixos abaixo)
          </label>
        </div>
        <Row>
          <Field label="Fallback — compositores" value={content.stats.fallbackCompositores} onChange={v => setField('stats.fallbackCompositores', v)} />
          <Field label="Fallback — obras"        value={content.stats.fallbackObras}        onChange={v => setField('stats.fallbackObras', v)} />
          <Field label="Fallback — pago"         value={content.stats.fallbackPago}         onChange={v => setField('stats.fallbackPago', v)} />
        </Row>
        <Row>
          <Field label="Label — compositores"    value={content.stats.labelCompositores}    onChange={v => setField('stats.labelCompositores', v)} />
          <Field label="Label — obras"           value={content.stats.labelObras}           onChange={v => setField('stats.labelObras', v)} />
          <Field label="Label — pago"            value={content.stats.labelPago}            onChange={v => setField('stats.labelPago', v)} />
        </Row>
      </Section>

      {/* COMO FUNCIONA */}
      <Section title="04 · Como Funciona">
        <Field label="Título da seção"  value={content.comoFunciona.sectionTitle} onChange={v => setField('comoFunciona.sectionTitle', v)} />
        <Field label="Subtítulo"        value={content.comoFunciona.sectionLead}  onChange={v => setField('comoFunciona.sectionLead', v)} textarea />

        <SubBlock title="Coluna Compositores">
          <Row>
            <Field label="Label"        value={content.comoFunciona.compositoresLabel} onChange={v => setField('comoFunciona.compositoresLabel', v)} />
            <Field label="Título"       value={content.comoFunciona.compositoresTitle} onChange={v => setField('comoFunciona.compositoresTitle', v)} />
          </Row>
          {(content.comoFunciona.compositoresSteps || []).map((step, i) => (
            <Row key={i}>
              <Field label={`Passo ${i+1} · título`} value={step.title} onChange={v => setArrayField('comoFunciona.compositoresSteps', i, 'title', v)} />
              <Field label={`Passo ${i+1} · texto`}  value={step.text}  onChange={v => setArrayField('comoFunciona.compositoresSteps', i, 'text', v)} />
            </Row>
          ))}
        </SubBlock>

        <SubBlock title="Coluna Compradores">
          <Row>
            <Field label="Label"        value={content.comoFunciona.compradoresLabel} onChange={v => setField('comoFunciona.compradoresLabel', v)} />
            <Field label="Título"       value={content.comoFunciona.compradoresTitle} onChange={v => setField('comoFunciona.compradoresTitle', v)} />
          </Row>
          {(content.comoFunciona.compradoresSteps || []).map((step, i) => (
            <Row key={i}>
              <Field label={`Passo ${i+1} · título`} value={step.title} onChange={v => setArrayField('comoFunciona.compradoresSteps', i, 'title', v)} />
              <Field label={`Passo ${i+1} · texto`}  value={step.text}  onChange={v => setArrayField('comoFunciona.compradoresSteps', i, 'text', v)} />
            </Row>
          ))}
        </SubBlock>
      </Section>

      {/* RECURSOS */}
      <Section title="05 · Recursos (6 cards)">
        <Field label="Título da seção" value={content.recursos.title} onChange={v => setField('recursos.title', v)} />
        {(content.recursos.items || []).map((item, i) => (
          <Row key={i}>
            <Field label={`#${i+1} label`} value={item.label} onChange={v => setArrayField('recursos.items', i, 'label', v)} />
            <Field label={`#${i+1} título`} value={item.title} onChange={v => setArrayField('recursos.items', i, 'title', v)} />
            <Field label={`#${i+1} texto`}  value={item.text}  onChange={v => setArrayField('recursos.items', i, 'text', v)} />
          </Row>
        ))}
      </Section>

      {/* MANIFESTO */}
      <Section title="06 · Manifesto">
        <Row>
          <Field label="Linha 1"      value={content.manifesto.line1}         onChange={v => setField('manifesto.line1', v)} />
          <Field label="Linha 2 (itálica)" value={content.manifesto.line2}    onChange={v => setField('manifesto.line2', v)} />
        </Row>
        <Row>
          <Field label="Nome do autor"   value={content.manifesto.authorName}    onChange={v => setField('manifesto.authorName', v)} />
          <Field label="Legenda do autor" value={content.manifesto.authorCaption} onChange={v => setField('manifesto.authorCaption', v)} />
        </Row>
      </Section>

      {/* PREÇOS */}
      <Section title="07 · Preços">
        <Field label="Título" value={content.precos.title} onChange={v => setField('precos.title', v)} />
        <Field label="Subtítulo" value={content.precos.lead} onChange={v => setField('precos.lead', v)} textarea />

        <SubBlock title="Plano básico">
          <Row>
            <Field label="Label"   value={content.precos.basico.label} onChange={v => setField('precos.basico.label', v)} />
            <Field label="Preço"   value={content.precos.basico.price} onChange={v => setField('precos.basico.price', v)} />
            <Field label="Botão"   value={content.precos.basico.cta}   onChange={v => setField('precos.basico.cta', v)} />
          </Row>
          <Field label="Features (uma por linha)" textarea
                 value={(content.precos.basico.features || []).join('\n')}
                 onChange={v => setField('precos.basico.features', v.split('\n').filter(x => x.trim()))} />
        </SubBlock>

        <SubBlock title="Plano pro">
          <Row>
            <Field label="Ribbon"       value={content.precos.pro.ribbon}    onChange={v => setField('precos.pro.ribbon', v)} />
            <Field label="Label"        value={content.precos.pro.label}     onChange={v => setField('precos.pro.label', v)} />
            <Field label="Preço"        value={content.precos.pro.price}     onChange={v => setField('precos.pro.price', v)} />
            <Field label="Unidade (/mês)" value={content.precos.pro.priceUnit} onChange={v => setField('precos.pro.priceUnit', v)} />
            <Field label="Botão"        value={content.precos.pro.cta}       onChange={v => setField('precos.pro.cta', v)} />
          </Row>
          <Field label="Features (uma por linha)" textarea
                 value={(content.precos.pro.features || []).join('\n')}
                 onChange={v => setField('precos.pro.features', v.split('\n').filter(x => x.trim()))} />
        </SubBlock>
      </Section>

      {/* FOOTER */}
      <Section title="08 · Rodapé">
        <Row>
          <Field label="Título col Plataforma" value={content.footer.colPlatformTitle} onChange={v => setField('footer.colPlatformTitle', v)} />
          <Field label="Título col Legal"       value={content.footer.colLegalTitle}    onChange={v => setField('footer.colLegalTitle', v)} />
          <Field label="Título col Contato"     value={content.footer.colContactTitle}  onChange={v => setField('footer.colContactTitle', v)} />
        </Row>
        <Row>
          <Field label="Email de contato"       value={content.footer.email}      onChange={v => setField('footer.email', v)} />
          <Field label="Título CTA final"       value={content.footer.ctaTitle}   onChange={v => setField('footer.ctaTitle', v)} />
          <Field label="Botão CTA final"        value={content.footer.ctaButton}  onChange={v => setField('footer.ctaButton', v)} />
        </Row>
        <Row>
          <Field label="Wordmark gigante"       value={content.footer.wordmark}   onChange={v => setField('footer.wordmark', v)} />
          <Field label="Copyright"              value={content.footer.copyright}  onChange={v => setField('footer.copyright', v)} />
          <Field label="Tagline"                value={content.footer.tagline}    onChange={v => setField('footer.tagline', v)} />
        </Row>
      </Section>

      {/* Fixed bottom save bar */}
      <div style={{ height: 60 }} />
      {changed && (
        <div style={{
          position: 'fixed', bottom: 0, left: 240, right: 0,
          padding: '12px 24px', background: 'var(--bg)', borderTop: '1px solid var(--border)',
          display: 'flex', justifyContent: 'flex-end', gap: 8,
          boxShadow: '0 -4px 16px rgba(9,9,11,.08)',
        }}>
          <span style={{ alignSelf: 'center', fontSize: 12, color: 'var(--text-muted)', marginRight: 'auto' }}>
            Você tem alterações não salvas
          </span>
          <button className="btn btn-ghost" onClick={reset}>Desfazer</button>
          <button className="btn btn-primary" onClick={save} disabled={saving}>
            {saving ? 'Salvando…' : 'Salvar alterações'}
          </button>
        </div>
      )}
    </div>
  )
}

/* ── Componentes internos ─────────────────────────────── */

function Section({ title, children }) {
  return (
    <section style={{ marginBottom: 32 }}>
      <h2 style={{
        fontSize: 11, fontWeight: 700, letterSpacing: '0.18em', textTransform: 'uppercase',
        color: 'var(--text-muted)', marginBottom: 16, paddingBottom: 12,
        borderBottom: '1px solid var(--border)',
      }}>{title}</h2>
      <div>{children}</div>
    </section>
  )
}

function SubBlock({ title, children }) {
  return (
    <div style={{
      background: 'var(--surface)', border: '1px solid var(--border)',
      padding: 20, marginTop: 16, marginBottom: 8,
    }}>
      <h3 style={{ fontSize: 13, fontWeight: 600, marginBottom: 14, color: 'var(--text-primary)' }}>
        {title}
      </h3>
      {children}
    </div>
  )
}

function Row({ children }) {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: `repeat(${React.Children.count(children)}, 1fr)`, gap: 12, marginBottom: 12 }}>
      {children}
    </div>
  )
}

function Field({ label, value, onChange, textarea = false }) {
  const Comp = textarea ? 'textarea' : 'input'
  return (
    <label style={{ display: 'flex', flexDirection: 'column', gap: 4, fontSize: 12 }}>
      <span style={{ color: 'var(--text-muted)', fontWeight: 600, letterSpacing: '0.06em' }}>{label}</span>
      <Comp
        value={value || ''}
        onChange={e => onChange(e.target.value)}
        className="input"
        rows={textarea ? 3 : undefined}
        style={{ fontSize: 13 }}
      />
    </label>
  )
}
