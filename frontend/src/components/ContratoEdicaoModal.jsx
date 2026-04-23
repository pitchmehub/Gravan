import React, { useState, useEffect } from 'react'
import { supabase } from '../lib/supabase'
import { useAuth } from '../contexts/AuthContext'

function renderTemplate(tpl, perfil) {
  if (!tpl || !perfil) return ''
  const endereco = [
    perfil.endereco_rua, perfil.endereco_numero, perfil.endereco_compl,
    perfil.endereco_bairro, perfil.endereco_cidade, perfil.endereco_uf,
    perfil.endereco_cep ? `CEP ${perfil.endereco_cep}` : null,
  ].filter(Boolean).join(', ')
  const agora = new Date().toLocaleString('pt-BR')
  return tpl
    .replace(/{{nome_completo}}/g, perfil.nome_completo || perfil.nome || '')
    .replace(/{{cpf}}/g,            perfil.cpf || '(será exibido no PDF assinado)')
    .replace(/{{rg}}/g,             perfil.rg  || '(será exibido no PDF assinado)')
    .replace(/{{endereco_completo}}/g, endereco || 'Não informado')
    .replace(/{{email}}/g,          perfil.email || '')
    .replace(/{{data_assinatura}}/g, agora)
    // Placeholders preenchidos em runtime pelo backend ao salvar a obra
    .replace(/{{obra_nome}}/g,              '[título da obra]')
    .replace(/{{share_autor_pct}}/g,        '[seu percentual]')
    .replace(/{{coautores_lista}}/g,        '[definido conforme os coautores cadastrados]')
    .replace(/{{plataforma_razao_social}}/g, 'PITCH.ME EDITORA MUSICAL LTDA.')
    .replace(/{{plataforma_cnpj}}/g,         '(CNPJ conforme cadastro da plataforma)')
    .replace(/{{plataforma_endereco}}/g,     'Rio de Janeiro - RJ')
}

export default function ContratoEdicaoModal({ onClose }) {
  const { perfil } = useAuth()
  const [tpl, setTpl] = useState('')

  useEffect(() => {
    async function load() {
      const { data } = await supabase
        .from('landing_content').select('valor')
        .eq('id', 'contrato_edicao_template').single()
      setTpl(data?.valor ?? '')
    }
    load()
  }, [])

  const conteudo = renderTemplate(tpl, perfil)

  return (
    <div
      onClick={e => { if (e.target === e.currentTarget) onClose() }}
      style={{
        position: 'fixed', inset: 0,
        background: 'rgba(0,0,0,.7)', backdropFilter: 'blur(4px)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        zIndex: 700, padding: 24,
      }}
    >
      <div style={{
        background: '#fff', borderRadius: 16, width: '100%', maxWidth: 720,
        maxHeight: '85vh', display: 'flex', flexDirection: 'column',
      }}>
        <div style={{
          padding: '20px 24px', borderBottom: '1px solid var(--border)',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        }}>
          <div>
            <h2 style={{ fontSize: 17, fontWeight: 700 }}>Contrato de Edição Musical</h2>
            <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>
              Versão 1.0 · {new Date().toLocaleDateString('pt-BR')}
            </p>
          </div>
          <button onClick={onClose} style={{
            background: 'none', border: 'none', fontSize: 24,
            cursor: 'pointer', color: 'var(--text-muted)',
          }}>×</button>
        </div>

        <div style={{
          padding: '20px 24px', overflowY: 'auto', flex: 1,
          fontSize: 12.5, lineHeight: 1.7, color: 'var(--text-secondary)',
          whiteSpace: 'pre-wrap', fontFamily: 'Inter, sans-serif',
        }}>
          {conteudo || 'Carregando contrato…'}
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
