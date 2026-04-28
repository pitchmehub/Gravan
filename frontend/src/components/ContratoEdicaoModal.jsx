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
    .replace(/{{nome_completo}}/g,         perfil.nome_completo || perfil.nome || '')
    .replace(/{{cpf}}/g,                   perfil.cpf || '(será exibido no contrato assinado)')
    .replace(/{{rg}}/g,                    perfil.rg  || '(será exibido no contrato assinado)')
    .replace(/{{endereco_completo}}/g,     endereco || 'Não informado')
    .replace(/{{email}}/g,                 perfil.email || '')
    .replace(/{{data_assinatura}}/g,       agora)
    .replace(/{{obra_nome}}/g,             '[título da obra, conforme preenchido no formulário]')
    .replace(/{{obra_letra}}/g,            '[letra da obra, conforme preenchida no formulário — texto integral consta no contrato assinado]')
    .replace(/{{share_autor_pct}}/g,       '[calculado automaticamente: 100% ÷ nº total de autores]')
    .replace(/{{coautores_lista}}/g,       '[definido conforme os coautores adicionados no formulário]')
    .replace(/{{plataforma_razao_social}}/g, 'GRAVAN EDITORA MUSICAL LTDA.')
    .replace(/{{plataforma_cnpj}}/g,       '64.342.514/0001-08')
    .replace(/{{plataforma_endereco}}/g,   'Rio de Janeiro - RJ')
    .replace(/{{conteudo_hash}}/g,         '[gerado no momento da assinatura]')
}

export default function ContratoEdicaoModal({ onClose }) {
  const { perfil } = useAuth()
  const [tpl, setTpl] = useState('')
  const [versao, setVersao] = useState('')

  useEffect(() => {
    async function load() {
      try {
        const [{ data: tplData }, { data: vData }] = await Promise.all([
          supabase.from('landing_content').select('valor').eq('id', 'contrato_edicao_template').single(),
          supabase.from('landing_content').select('valor').eq('id', 'contrato_edicao_versao').single(),
        ])
        if (tplData?.valor) setTpl(tplData.valor)
        if (vData?.valor)   setVersao(vData.valor)
        if (tplData?.valor) return
      } catch (_) {}
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
      <div className="gv-modal-box" style={{ maxWidth: 760 }}>
        <div className="gv-modal-head">
          <div className="gv-modal-head-info">
            <h2>Contrato de Edição Musical — Texto Integral</h2>
            <p>{versao || 'v2.2'} · {new Date().toLocaleDateString('pt-BR')}</p>
          </div>
          <button className="gv-modal-close" onClick={onClose} aria-label="Fechar">×</button>
        </div>

        <div style={{
          padding: '6px 22px 10px',
          background: '#fffbeb',
          borderBottom: '1px solid #fde68a',
          fontSize: 12,
          color: '#92400e',
          lineHeight: 1.5,
        }}>
          ℹ Este é o texto <strong>integral</strong> do contrato que você assinará. Os campos entre colchetes
          [ ] serão preenchidos automaticamente com os dados da obra e dos coautores no momento do cadastro.
        </div>

        <div className="gv-modal-body" style={{ whiteSpace: 'pre-wrap', fontFamily: 'Georgia, serif', fontSize: 13, lineHeight: 1.75 }}>
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
