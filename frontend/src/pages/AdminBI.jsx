import { useEffect, useState } from 'react'
import { api } from '../lib/api'

function fmt(cents) {
  return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format((cents ?? 0) / 100)
}

export default function AdminBI() {
  const [resumo,   setResumo]   = useState(null)
  const [generos,  setGeneros]  = useState([])
  const [auditoria,setAuditoria]= useState([])
  const [loading,  setLoading]  = useState(true)
  const [aba,      setAba]      = useState('resumo')

  useEffect(() => {
    Promise.all([
      api.get('/admin/bi/resumo'),
      api.get('/admin/bi/generos'),
      api.get('/admin/bi/auditoria?per_page=20'),
    ]).then(([r, g, a]) => {
      setResumo(r)
      setGeneros(g)
      setAuditoria(a)
    }).finally(() => setLoading(false))
  }, [])

  if (loading) return <p className="text-muted">Carregando BI…</p>

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 22, fontWeight: 600 }}>Painel de BI</h1>
        <p className="text-muted">Visão consolidada da plataforma</p>
      </div>

      {/* Abas */}
      <div style={{ display: 'flex', gap: 6, marginBottom: 24, borderBottom: '1px solid var(--border)', paddingBottom: 0 }}>
        {[['resumo', 'Resumo'], ['generos', 'Gêneros'], ['auditoria', 'Auditoria de Splits']].map(([id, label]) => (
          <button
            key={id}
            onClick={() => setAba(id)}
            style={{
              padding: '8px 18px', border: 'none', background: 'none', cursor: 'pointer',
              fontSize: 14, fontWeight: aba === id ? 600 : 400,
              color: aba === id ? 'var(--brand)' : 'var(--text-secondary)',
              borderBottom: aba === id ? '2px solid var(--brand)' : '2px solid transparent',
              marginBottom: -1,
            }}
          >
            {label}
          </button>
        ))}
      </div>

      {/* RESUMO */}
      {aba === 'resumo' && resumo && (
        <div>
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
            gap: 14, marginBottom: 28,
          }}>
            <BiCard label="Total de Obras"    value={resumo.total_obras}    icon="♫" />
            <BiCard label="Usuários"           value={resumo.total_usuarios}  icon="◈" />
            <BiCard label="Vendas Confirmadas" value={resumo.total_vendas}    icon="✓" color="var(--success)" />
            <BiCard label="Receita Bruta"      value={fmt(resumo.receita_bruta_cents)}     icon="◎" color="var(--brand)" />
            <BiCard label="Receita Plataforma" value={fmt(resumo.receita_plataforma_cents)} icon="▦" />
            <BiCard label="Ofertas Pendentes"  value={resumo.ofertas_pendentes} icon="✉" color="var(--warning)" />
          </div>

          {/* Barra de distribuição de receita */}
          <div className="card">
            <h2 style={{ fontSize: 15, fontWeight: 600, marginBottom: 14 }}>Distribuição de Receita</h2>
            {[
              { label: 'Plataforma (40%)', pct: 40, color: '#083257' },
              { label: 'Compositores (60%)', pct: 60, color: '#059669' },
            ].map(b => (
              <div key={b.label} style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 10 }}>
                <div style={{ width: 160, fontSize: 13, color: 'var(--text-secondary)' }}>{b.label}</div>
                <div style={{ flex: 1, height: 14, background: 'var(--border)', borderRadius: 99, overflow: 'hidden' }}>
                  <div style={{ width: `${b.pct}%`, height: '100%', background: b.color, borderRadius: 99 }} />
                </div>
                <div style={{ width: 36, fontWeight: 600, fontSize: 13 }}>{b.pct}%</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* GÊNEROS */}
      {aba === 'generos' && (
        <div className="card">
          <h2 style={{ fontSize: 15, fontWeight: 600, marginBottom: 14 }}>Gêneros Mais Procurados</h2>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border)' }}>
                {['Gênero', 'Obras', 'Vendas', 'Receita'].map(h => (
                  <th key={h} style={{ padding: '8px 12px', textAlign: 'left', color: 'var(--text-muted)', fontWeight: 500, fontSize: 12 }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {generos.map((g, i) => (
                <tr key={i} style={{ borderBottom: '1px solid var(--border)' }}>
                  <td style={{ padding: '10px 12px', fontWeight: 500 }}>{g.genero}</td>
                  <td style={{ padding: '10px 12px', color: 'var(--text-secondary)' }}>{g.total_obras}</td>
                  <td style={{ padding: '10px 12px', color: 'var(--text-secondary)' }}>{g.total_vendas}</td>
                  <td style={{ padding: '10px 12px', fontWeight: 600, color: 'var(--brand)' }}>
                    {fmt(g.receita_cents)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* AUDITORIA */}
      {aba === 'auditoria' && (
        <div className="card">
          <h2 style={{ fontSize: 15, fontWeight: 600, marginBottom: 14 }}>Auditoria de Splits</h2>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border)' }}>
                  {['Data', 'Obra', 'Compositor', 'Venda', 'Share %', 'Recebido', 'Status'].map(h => (
                    <th key={h} style={{ padding: '8px 10px', textAlign: 'left', color: 'var(--text-muted)', fontWeight: 500, fontSize: 12, whiteSpace: 'nowrap' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {auditoria.map((a, i) => (
                  <tr key={i} style={{ borderBottom: '1px solid var(--border)' }}>
                    <td style={{ padding: '9px 10px', color: 'var(--text-secondary)', whiteSpace: 'nowrap' }}>
                      {new Date(a.created_at).toLocaleDateString('pt-BR')}
                    </td>
                    <td style={{ padding: '9px 10px', fontWeight: 500, maxWidth: 140, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {a.obra_nome}
                    </td>
                    <td style={{ padding: '9px 10px', color: 'var(--text-secondary)' }}>{a.compositor_nome}</td>
                    <td style={{ padding: '9px 10px' }}>{fmt(a.valor_cents)}</td>
                    <td style={{ padding: '9px 10px', textAlign: 'center' }}>{a.share_pct}%</td>
                    <td style={{ padding: '9px 10px', fontWeight: 600, color: 'var(--success)' }}>
                      {fmt(a.pago_cents)}
                    </td>
                    <td style={{ padding: '9px 10px' }}>
                      <span className={`badge badge-${a.status === 'confirmada' ? 'success' : 'silver'}`}>
                        {a.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}

function BiCard({ label, value, icon, color }) {
  return (
    <div className="card card-sm" style={{ textAlign: 'center' }}>
      <div style={{ fontSize: 20, marginBottom: 6 }}>{icon}</div>
      <div style={{ fontSize: 18, fontWeight: 700, color: color ?? 'var(--text-primary)' }}>{value}</div>
      <div className="text-muted" style={{ fontSize: 12, marginTop: 2 }}>{label}</div>
    </div>
  )
}
