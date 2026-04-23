import React from 'react'

/**
 * Stepper visual usado no fluxo de cadastro inicial (pós-login Google).
 *   etapa 1 → Escolher tipo de perfil (ARTISTA/EDITORA) — obrigatório
 *   etapa 2 → Preencher dados — pode "preencher depois"
 */
export default function StepperCadastro({ etapa = 1 }) {
  const steps = [
    { n: 1, label: 'Tipo de perfil', sub: 'Obrigatório' },
    { n: 2, label: 'Seus dados',     sub: 'Pode preencher depois' },
  ]
  return (
    <div style={{
      maxWidth: 640, margin: '0 auto 18px', padding: '14px 18px',
      background: '#fff', border: '1px solid #E5E7EB', borderRadius: 12,
      display: 'flex', alignItems: 'center', gap: 10,
    }}>
      {steps.map((s, i) => {
        const ativo  = etapa === s.n
        const feito  = etapa > s.n
        return (
          <React.Fragment key={s.n}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, flex: 1 }}>
              <div style={{
                width: 30, height: 30, borderRadius: '50%',
                background: feito ? '#16A34A' : ativo ? '#E11D48' : '#E5E7EB',
                color: feito || ativo ? '#fff' : '#71717A',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 13, fontWeight: 800, flex: '0 0 auto',
              }}>
                {feito ? '✓' : s.n}
              </div>
              <div style={{ minWidth: 0 }}>
                <div style={{ fontSize: 12.5, fontWeight: 700, color: ativo ? '#09090B' : '#3F3F46' }}>
                  Etapa {s.n} — {s.label}
                </div>
                <div style={{ fontSize: 10.5, color: '#71717A' }}>{s.sub}</div>
              </div>
            </div>
            {i < steps.length - 1 && (
              <div style={{ height: 2, width: 24, background: feito ? '#16A34A' : '#E5E7EB', flex: '0 0 auto' }} />
            )}
          </React.Fragment>
        )
      })}
    </div>
  )
}
