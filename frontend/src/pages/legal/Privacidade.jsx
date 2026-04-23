import React from 'react'
import { LegalLayout, Section, Bullet } from './LegalLayout'

export default function Privacidade() {
  return (
    <LegalLayout
      eyebrow="Política de Privacidade"
      title="Sua privacidade é nossa prioridade."
      lastUpdate="Abril de 2026"
      active="/privacidade"
    >
      <p style={{ fontSize: 16, color: 'var(--text-secondary)', marginBottom: 40, lineHeight: 1.7 }}>
        A PITCH.ME respeita a sua privacidade e está comprometida com a proteção dos dados
        pessoais de seus usuários, em conformidade com a <strong>Lei Geral de Proteção
        de Dados (LGPD)</strong>.
      </p>

      <Section n="1" title="Dados coletados">
        Coletamos as seguintes informações:
        <ul style={{ marginTop: 10 }}>
          <Bullet>Nome, e-mail e dados de login</Bullet>
          <Bullet>Informações de perfil artístico</Bullet>
          <Bullet>Arquivos enviados (incluindo composições em formato MP3)</Bullet>
          <Bullet>Dados de navegação e uso da plataforma</Bullet>
        </ul>
      </Section>

      <Section n="2" title="Uso dos dados">
        Seus dados são utilizados para:
        <ul style={{ marginTop: 10 }}>
          <Bullet>Operar e melhorar a plataforma</Bullet>
          <Bullet>Viabilizar a conexão entre compositores e artistas</Bullet>
          <Bullet>Processar negociações e licenciamento de obras</Bullet>
          <Bullet>Garantir segurança e prevenção de fraudes</Bullet>
        </ul>
      </Section>

      <Section n="3" title="Compartilhamento de dados">
        Seus dados podem ser compartilhados com:
        <ul style={{ marginTop: 10 }}>
          <Bullet>Outros usuários da plataforma (quando necessário para negociação)</Bullet>
          <Bullet>Serviços técnicos (ex: hospedagem, banco de dados)</Bullet>
        </ul>
        <p style={{ marginTop: 14, fontWeight: 600, color: 'var(--text-primary)' }}>
          Nunca vendemos seus dados pessoais.
        </p>
      </Section>

      <Section n="4" title="Armazenamento e segurança">
        Adotamos medidas técnicas e organizacionais para proteger seus dados contra
        acesso não autorizado, perda ou uso indevido.
      </Section>

      <Section n="5" title="Direitos do usuário">
        Você pode:
        <ul style={{ marginTop: 10 }}>
          <Bullet>Solicitar acesso, correção ou exclusão dos seus dados</Bullet>
          <Bullet>Revogar consentimentos</Bullet>
        </ul>
      </Section>

      <Section n="6" title="Contato">
        Para dúvidas sobre privacidade: <a href="mailto:contato@pitch.me" style={{ color: 'var(--brand)' }}>contato@pitch.me</a>
      </Section>

      <Section n="7" title="Atualizações">
        Esta política pode ser atualizada a qualquer momento.
      </Section>
    </LegalLayout>
  )
}
