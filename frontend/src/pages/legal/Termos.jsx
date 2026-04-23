import React from 'react'
import { LegalLayout, Section, Bullet } from './LegalLayout'

export default function Termos() {
  return (
    <LegalLayout
      eyebrow="Termos de Uso"
      title="As regras do jogo — claras e objetivas."
      lastUpdate="Abril de 2026"
      active="/termos"
    >
      <p style={{ fontSize: 16, color: 'var(--text-secondary)', marginBottom: 40, lineHeight: 1.7 }}>
        Ao utilizar a PITCH.ME, você concorda com os termos abaixo.
      </p>

      <Section n="1" title="Objeto da plataforma">
        A PITCH.ME é uma plataforma de intermediação que conecta compositores e artistas
        para fins de licenciamento de obras musicais.
      </Section>

      <Section n="2" title="Responsabilidade do usuário">
        O usuário declara que:
        <ul style={{ marginTop: 10 }}>
          <Bullet>Possui os direitos sobre as obras enviadas</Bullet>
          <Bullet>Não viola direitos de terceiros</Bullet>
        </ul>
        <p style={{ marginTop: 14 }}>
          A PITCH.ME não se responsabiliza por disputas de autoria.
        </p>
      </Section>

      <Section n="3" title="Intermediação">
        A PITCH.ME atua exclusivamente como intermediadora, não sendo parte direta
        nos contratos finais entre usuários.
      </Section>

      <Section n="4" title="Taxa de serviço">
        Será cobrada uma taxa de <strong>20%</strong> sobre as transações realizadas
        por meio da plataforma.
      </Section>

      <Section n="5" title="Uso da plataforma">
        É proibido:
        <ul style={{ marginTop: 10 }}>
          <Bullet>Enviar conteúdo ilegal ou de terceiros sem autorização</Bullet>
          <Bullet>Utilizar a plataforma para fins fraudulentos</Bullet>
        </ul>
      </Section>

      <Section n="6" title="Limitação de responsabilidade">
        A PITCH.ME não garante sucesso comercial das obras negociadas.
      </Section>

      <Section n="7" title="Encerramento de conta">
        Contas podem ser suspensas em caso de violação destes termos.
      </Section>

      <Section n="8" title="Alterações">
        Os termos podem ser atualizados a qualquer momento.
      </Section>
    </LegalLayout>
  )
}
