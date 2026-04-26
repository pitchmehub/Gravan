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
        Ao utilizar a GRAVAN, você concorda com os termos abaixo.
      </p>

      <Section n="1" title="Objeto da plataforma">
        A GRAVAN é uma plataforma de intermediação que conecta compositores, intérpretes,
        editoras e demais agentes do mercado musical para fins de licenciamento de obras
        musicais, contratos eletrônicos e gestão de catálogo.
      </Section>

      <Section n="2" title="Cadastro e perfis">
        Para usar a plataforma é necessário criar uma conta vinculada a um perfil
        (compositor, intérprete, editora ou administrador). Cada perfil tem permissões
        e funcionalidades específicas. O usuário é responsável pelas informações
        prestadas, pela veracidade dos dados e por manter a confidencialidade da sua
        senha.
      </Section>

      <Section n="3" title="Responsabilidade do usuário">
        O usuário declara que:
        <ul style={{ marginTop: 10 }}>
          <Bullet>Possui os direitos sobre as obras enviadas, incluindo letra, melodia, gravação e materiais associados</Bullet>
          <Bullet>Tem autorização de eventuais coautores e titulares para disponibilizar a obra na plataforma</Bullet>
          <Bullet>Não viola direitos de terceiros</Bullet>
        </ul>
        <p style={{ marginTop: 14 }}>
          A GRAVAN não se responsabiliza por disputas de autoria, mas pode suspender
          obras e contas envolvidas em conflitos enquanto a questão não for resolvida.
        </p>
      </Section>

      <Section n="4" title="Intermediação">
        A GRAVAN atua como intermediadora dos contratos eletrônicos celebrados entre os
        usuários. Em contratos trilaterais, a editora vinculada (quando houver) também
        figura como parte. As assinaturas são eletrônicas e ficam registradas com data,
        hora e IP de quem assinou.
      </Section>

      <Section n="5" title="Planos e taxas de serviço">
        A GRAVAN oferece dois planos:
        <ul style={{ marginTop: 10 }}>
          <Bullet><b>STARTER</b> — gratuito, com taxa de <b>20%</b> sobre cada transação realizada na plataforma.</Bullet>
          <Bullet><b>PRO</b> — assinatura mensal de <b>R$ 49,90</b>, com taxa reduzida para <b>15%</b>, painel de analytics e benefícios adicionais descritos na página de Planos.</Bullet>
        </ul>
        <p style={{ marginTop: 14 }}>
          O plano PRO é renovado automaticamente pelo Stripe a cada ciclo mensal. O
          usuário pode cancelar a renovação a qualquer momento pela página de Planos:
          os benefícios PRO permanecem ativos até o final do ciclo já pago. Não há
          reembolso proporcional.
        </p>
      </Section>

      <Section n="6" title="Pagamentos, saldo e saques">
        Cada venda gera saldo na carteira do compositor (e da editora vinculada,
        quando aplicável), conforme o split configurado na obra e descontada a taxa
        do plano vigente.
        <ul style={{ marginTop: 10 }}>
          <Bullet>O saque exige conta Stripe Connect ativa e verificada em nome do titular do perfil.</Bullet>
          <Bullet>O usuário pode solicitar quantos saques quiser, com qualquer valor, desde que tenha saldo disponível — não há limite mensal, diário ou por transação.</Bullet>
          <Bullet>Cada saque exige confirmação por código de 6 dígitos enviado ao e-mail cadastrado.</Bullet>
          <Bullet>Após confirmado, há uma janela de segurança de 24 h em que o saque pode ser cancelado pelo próprio usuário (também pelo link "Não fui eu" no e-mail). Após esse prazo o valor é processado.</Bullet>
          <Bullet>O tempo de crédito final na conta bancária depende do banco/PSP do usuário.</Bullet>
        </ul>
      </Section>

      <Section n="7" title="Editoras e contratos trilaterais">
        Compositores podem se vincular a editoras agregadoras por meio de convite
        formal contendo termo jurídico próprio. Aceito o convite, as vendas das obras
        do compositor passam a gerar contratos trilaterais (compositor, comprador e
        editora). A editora pode ter um split configurado por contrato e participa
        das assinaturas eletrônicas. O vínculo pode ser desfeito conforme as regras
        descritas no termo do convite.
      </Section>

      <Section n="8" title="Uso da plataforma">
        É proibido:
        <ul style={{ marginTop: 10 }}>
          <Bullet>Enviar conteúdo ilegal ou de terceiros sem autorização</Bullet>
          <Bullet>Burlar o sistema de pagamento ou intermediação (ex: negociar fora da plataforma após uso de funcionalidades como contato e ofertas)</Bullet>
          <Bullet>Utilizar a plataforma para fins fraudulentos, lavagem de dinheiro ou em descumprimento à legislação aplicável</Bullet>
          <Bullet>Tentar acessar dados ou contas de outros usuários</Bullet>
        </ul>
      </Section>

      <Section n="9" title="Limitação de responsabilidade">
        A GRAVAN não garante sucesso comercial das obras negociadas, nem se
        responsabiliza por indisponibilidades pontuais de provedores terceiros
        (Stripe, e-mail, hospedagem). Mantemos rotinas automáticas de monitoramento
        e backup, mas o usuário é responsável por guardar cópias das suas próprias
        obras.
      </Section>

      <Section n="10" title="Encerramento de conta">
        Contas podem ser suspensas ou encerradas em caso de violação destes termos.
        O usuário também pode solicitar o encerramento da própria conta a qualquer
        momento. Saldo eventualmente disponível pode ser sacado antes do
        encerramento, observada a conexão com Stripe Connect.
      </Section>

      <Section n="11" title="Alterações">
        Os termos podem ser atualizados a qualquer momento. Mudanças relevantes serão
        comunicadas pela plataforma ou por e-mail.
      </Section>
    </LegalLayout>
  )
}
