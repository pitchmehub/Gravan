import React, { useState, useEffect } from 'react'
import { createPortal } from 'react-dom'
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
    .replace(/{{obra_nome}}/g,              '[título da obra]')
    .replace(/{{share_autor_pct}}/g,        '[seu percentual]')
    .replace(/{{coautores_lista}}/g,        '[definido conforme os coautores cadastrados]')
    .replace(/{{plataforma_razao_social}}/g, 'GRAVAN EDITORA MUSICAL LTDA.')
    .replace(/{{plataforma_cnpj}}/g,         '(CNPJ conforme cadastro da plataforma)')
    .replace(/{{plataforma_endereco}}/g,     'Rio de Janeiro - RJ')
}

export default function ContratoEdicaoModal({ onClose }) {
  const { perfil } = useAuth()
  const [tpl, setTpl] = useState('')

  useEffect(() => {
    async function load() {
      try {
        const { data } = await supabase
          .from('landing_content').select('valor')
          .eq('id', 'contrato_edicao_template').single()
        if (data?.valor) { setTpl(data.valor); return }
      } catch (_) { /* segue para fallback */ }
      // Fallback: pega o template real exposto pelo backend
      try {
        const r = await fetch('/api/contratos/licenciamento/templates')
        const d = await r.json()
        setTpl(d?.edicao_bilateral || '')
      } catch (_) { setTpl('') }
    }
    load()
  }, [])

  useEffect(() => {
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => { document.body.style.overflow = prev }
  }, [])

  const conteudo = renderTemplate(tpl, perfil)

  const node = (
    <div
      className="gv-modal-bg"
      onClick={e => { if (e.target === e.currentTarget) onClose() }}
    >
      <div className="gv-modal-box" style={{ maxWidth: 720 }}>
        <div className="gv-modal-head">
          <div className="gv-modal-head-info">
            <h2>Contrato de Edição Musical</h2>
            <p>Versão 1.0 · {new Date().toLocaleDateString('pt-BR')}</p>
          </div>
          <button className="gv-modal-close" onClick={onClose} aria-label="Fechar">×</button>
        </div>

        <div className="gv-modal-body" style={{ whiteSpace: 'pre-wrap', fontFamily: 'Inter, sans-serif' }}>
          {conteudo || 'Carregando contrato…'}
        </div>

        <div className="gv-modal-footer">
          <button className="gv-btn-primary" onClick={onClose}>Fechar</button>
        </div>
      </div>
    </div>
  )

  return createPortal(node, document.body)
}
