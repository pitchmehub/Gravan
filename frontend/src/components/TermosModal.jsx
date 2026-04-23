import React, { useState, useEffect } from 'react'
import { supabase } from '../lib/supabase'

export default function TermosModal({ onClose }) {
  const [conteudo, setConteudo] = useState({ titulo: '', versao: '', texto: '' })

  useEffect(() => {
    async function load() {
      const { data } = await supabase
        .from('landing_content')
        .select('id, valor')
        .in('id', ['termos_uso_titulo', 'termos_uso_versao', 'termos_uso_texto'])
      const map = {}
      data?.forEach(r => { map[r.id] = r.valor })
      setConteudo({
        titulo: map.termos_uso_titulo ?? 'Termos de Uso',
        versao: map.termos_uso_versao ?? '1.0',
        texto:  map.termos_uso_texto ?? '',
      })
    }
    load()
  }, [])

  return (
    <div
      onClick={e => { if (e.target === e.currentTarget) onClose() }}
      style={{
        position: 'fixed', inset: 0,
        background: 'rgba(0,0,0,.65)', backdropFilter: 'blur(4px)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        zIndex: 700, padding: 24,
      }}
    >
      <div style={{
        background: '#fff', borderRadius: 16, width: '100%', maxWidth: 680,
        maxHeight: '85vh', display: 'flex', flexDirection: 'column',
      }}>
        <div style={{
          padding: '20px 24px', borderBottom: '1px solid var(--border)',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        }}>
          <div>
            <h2 style={{ fontSize: 18, fontWeight: 700 }}>{conteudo.titulo}</h2>
            <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>Versão {conteudo.versao}</p>
          </div>
          <button onClick={onClose} style={{
            background: 'none', border: 'none', fontSize: 24, cursor: 'pointer',
            color: 'var(--text-muted)', padding: 0, width: 32, height: 32,
          }}>×</button>
        </div>

        <div style={{
          padding: '20px 24px', overflowY: 'auto', flex: 1,
          fontSize: 13, lineHeight: 1.7, color: 'var(--text-secondary)',
          whiteSpace: 'pre-wrap', fontFamily: 'inherit',
        }}>
          {conteudo.texto}
        </div>

        <div style={{
          padding: '14px 24px', borderTop: '1px solid var(--border)',
          display: 'flex', justifyContent: 'flex-end',
        }}>
          <button className="btn btn-primary" onClick={onClose}>Fechar</button>
        </div>
      </div>
    </div>
  )
}
