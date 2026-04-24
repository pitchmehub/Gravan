import React from 'react'
import { LegalLayout, Section, Bullet } from './LegalLayout'

export default function DireitosAutorais() {
  return (
    <LegalLayout
      eyebrow="Política de Direitos Autorais"
      title="A obra é sua. Sempre."
      lastUpdate="Abril de 2026"
      active="/direitos-autorais"
    >
      <p style={{ fontSize: 16, color: 'var(--text-secondary)', marginBottom: 40, lineHeight: 1.7 }}>
        Esta política define como a GRAVAN trata a propriedade intelectual das obras
        hospedadas na plataforma.
      </p>

      <Section n="1" title="Propriedade das obras">
        O envio de uma composição <strong>não transfere a propriedade intelectual</strong>
        à GRAVAN.
      </Section>

      <Section n="2" title="Responsabilidade">
        O usuário que envia a obra é integralmente responsável por:
        <ul style={{ marginTop: 10 }}>
          <Bullet>Garantir autoria ou autorização</Bullet>
          <Bullet>Evitar violações de direitos de terceiros</Bullet>
        </ul>
      </Section>

      <Section n="3" title="Licenciamento">
        Qualquer uso da obra dependerá de acordo entre as partes envolvidas.
      </Section>

      <Section n="4" title="Intermediação">
        A GRAVAN apenas facilita a conexão e negociação, não sendo titular das obras.
      </Section>

      <Section n="5" title="Remoção de conteúdo">
        Conteúdos podem ser removidos em caso de denúncia ou suspeita de violação.
      </Section>

      <Section n="6" title="Consequências">
        Usuários que infringirem direitos autorais poderão:
        <ul style={{ marginTop: 10 }}>
          <Bullet>Ter a conta suspensa</Bullet>
          <Bullet>Ser responsabilizados legalmente</Bullet>
        </ul>
      </Section>
    </LegalLayout>
  )
}
