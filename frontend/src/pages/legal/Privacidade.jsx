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
        A GRAVAN respeita a sua privacidade e está comprometida com a proteção dos dados
        pessoais de seus usuários, em conformidade com a <strong>Lei Geral de Proteção
        de Dados (LGPD)</strong>.
      </p>

      <Section n="1" title="Dados coletados">
        Coletamos as seguintes informações:
        <ul style={{ marginTop: 10 }}>
          <Bullet>Nome, e-mail e dados de login</Bullet>
          <Bullet>Informações de perfil (artístico, editora, biografia, foto)</Bullet>
          <Bullet>Arquivos enviados (composições em MP3, capas, dossiês)</Bullet>
          <Bullet>Dados de pagamento e identificação fiscal entregues à Stripe (para Connect e assinaturas)</Bullet>
          <Bullet>Histórico de buscas, ofertas, contratos e saques</Bullet>
          <Bullet>Endereço IP, user agent e dados de navegação para fins de segurança</Bullet>
        </ul>
      </Section>

      <Section n="2" title="Uso dos dados">
        Seus dados são utilizados para:
        <ul style={{ marginTop: 10 }}>
          <Bullet>Operar, manter e melhorar a plataforma</Bullet>
          <Bullet>Viabilizar negociação, licenciamento e contratos eletrônicos entre os usuários</Bullet>
          <Bullet>Processar pagamentos, assinaturas PRO e saques via Stripe</Bullet>
          <Bullet>Garantir segurança, prevenir fraudes e validar saques (códigos OTP por e-mail)</Bullet>
          <Bullet>Enviar notificações relevantes (ofertas, contratos, saques) por e-mail e push</Bullet>
        </ul>
      </Section>

      <Section n="3" title="Compartilhamento de dados">
        Seus dados podem ser compartilhados com:
        <ul style={{ marginTop: 10 }}>
          <Bullet>Outros usuários da plataforma quando necessário para negociação (ex: nome artístico, perfil público, partes envolvidas em um contrato)</Bullet>
          <Bullet>Stripe, para processamento de pagamentos e assinaturas</Bullet>
          <Bullet>Supabase e demais serviços técnicos de hospedagem e banco de dados</Bullet>
        </ul>
        <p style={{ marginTop: 14, fontWeight: 600, color: 'var(--text-primary)' }}>
          Nunca vendemos seus dados pessoais.
        </p>
      </Section>

      <Section n="4" title="Armazenamento e segurança">
        Adotamos medidas técnicas e organizacionais para proteger seus dados contra
        acesso não autorizado, perda ou uso indevido. Entre elas:
        <ul style={{ marginTop: 10 }}>
          <Bullet>Senhas armazenadas com hash + salt</Bullet>
          <Bullet>Saques confirmados por OTP de 6 dígitos com validade de 10 minutos</Bullet>
          <Bullet>Janela de cancelamento de 24 h em saques (link "Não fui eu" no e-mail)</Bullet>
          <Bullet>Row-Level Security (RLS) no banco para isolar dados de cada usuário</Bullet>
          <Bullet>Logs de auditoria de eventos sensíveis (vendas, contratos, saques)</Bullet>
        </ul>
      </Section>

      <Section n="5" title="Direitos do usuário">
        Você pode:
        <ul style={{ marginTop: 10 }}>
          <Bullet>Solicitar acesso, correção ou exclusão dos seus dados</Bullet>
          <Bullet>Revogar consentimentos a qualquer momento</Bullet>
          <Bullet>Cancelar a assinatura PRO pela página de Planos</Bullet>
          <Bullet>Solicitar o encerramento da sua conta</Bullet>
        </ul>
      </Section>

      <Section n="6" title="Contato">
        Para dúvidas sobre privacidade: <a href="mailto:contato@gravan.com" style={{ color: 'var(--brand)' }}>contato@gravan.com</a>
      </Section>

      <Section n="7" title="Atualizações">
        Esta política pode ser atualizada a qualquer momento. Mudanças relevantes serão
        comunicadas pela plataforma ou por e-mail.
      </Section>
    </LegalLayout>
  )
}
