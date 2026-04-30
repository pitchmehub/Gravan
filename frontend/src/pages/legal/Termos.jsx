import React from 'react'
import { LegalLayout, Section, Bullet } from './LegalLayout'

export default function Termos() {
  return (
    <LegalLayout
      eyebrow="Termos de Uso"
      title="Termos de Uso da Gravan"
      lastUpdate="Versão 2026-04 — Abril de 2026"
      active="/termos"
    >
      <div style={{
        background: '#FEF3C7', border: '1px solid #FBBF24', color: '#78350F',
        padding: '14px 16px', borderRadius: 12, fontSize: 13.5, lineHeight: 1.6,
        marginBottom: 32,
      }}>
        <b>Resumo:</b> a GRAVAN é uma <b>intermediadora tecnológica</b> que conecta
        usuários para licenciamento de obras musicais. Não somos editora,
        gravadora ou proprietária das obras, e não somos parte dos contratos
        celebrados entre os usuários.
      </div>

      <Section n="1" title="Aceitação dos termos">
        Ao acessar ou utilizar a plataforma <b>GRAVAN</b> (“Plataforma”),
        operada pela GRAVAN TECNOLOGIA E MARKETPLACE LTDA. (“Gravan”), o
        usuário declara que <b>leu, compreendeu e concorda integralmente</b>{' '}
        com estes Termos de Uso e com a Política de Privacidade da Plataforma.
        <p style={{ marginTop: 12 }}>
          O aceite ocorre no momento da conclusão do cadastro, mediante marcação
          expressa em campo próprio (“Li e concordo com os Termos de Uso”), e
          fica registrado na conta do usuário com data, hora UTC, IP de origem
          e versão dos termos vigentes, para fins probatórios.
        </p>
        <p style={{ marginTop: 12 }}>
          <b>Se você não concorda com estes Termos, não utilize a Plataforma.</b>
        </p>
      </Section>

      <Section n="2" title="Definições">
        Para os fins destes Termos:
        <ul style={{ marginTop: 10 }}>
          <Bullet><b>Plataforma</b>: o sistema digital operado pela Gravan, acessível pela web e demais canais oficiais.</Bullet>
          <Bullet><b>Usuário</b>: qualquer pessoa física ou jurídica cadastrada na Plataforma — compositores, intérpretes, produtores, editoras, agregadores, compradores e licenciadores.</Bullet>
          <Bullet><b>Obra</b>: conteúdo musical (letra, melodia, gravação, capa, metadados) cadastrado por um Usuário na Plataforma.</Bullet>
          <Bullet><b>Licença</b>: autorização de uso da Obra concedida pelo titular ao comprador, sob as condições do contrato eletrônico celebrado na Plataforma.</Bullet>
          <Bullet><b>Coautoria</b>: percentual de participação (<i>share_pct</i>) atribuído a cada autor/coautor de uma Obra, definido pelos próprios usuários no cadastro.</Bullet>
          <Bullet><b>Stripe</b>: Stripe Payments do Brasil Instituição de Pagamento Ltda., processador externo responsável pelo fluxo financeiro e por Stripe Connect.</Bullet>
        </ul>
      </Section>

      <Section n="3" title="Natureza do serviço (cláusula crítica)">
        A Gravan pode atuar em <b>duas qualidades distintas e independentes</b>{' '}
        dentro da Plataforma. A qualidade aplicável a cada relação é{' '}
        <b>identificada expressamente no respectivo contrato</b>.

        <p style={{ marginTop: 16 }}>
          <b>3.1. Gravan Tecnologia (regra geral — intermediadora tecnológica)</b>
        </p>
        <p style={{ marginTop: 6 }}>
          Como regra, a GRAVAN atua <b>exclusivamente como intermediadora
          tecnológica</b>, conectando Usuários para fins de licenciamento de
          obras musicais e provendo a infraestrutura digital necessária
          (cadastro, contratos eletrônicos, registro probatório de assinaturas,
          orquestração técnica de pagamento via Stripe).
        </p>
        <p style={{ marginTop: 12 }}>Nessa qualidade, a Gravan:</p>
        <ul style={{ marginTop: 6 }}>
          <Bullet><b>NÃO é proprietária</b> das obras cadastradas;</Bullet>
          <Bullet><b>NÃO é editora, gravadora, agregadora nem produtora</b>;</Bullet>
          <Bullet><b>NÃO participa da criação</b> das obras;</Bullet>
          <Bullet><b>NÃO é parte</b> dos contratos celebrados entre os Usuários, ainda que sua marca apareça por questão de identidade visual ou geração técnica do documento;</Bullet>
          <Bullet><b>NÃO é instituição financeira</b>, não atua como escrow nem retém valores em nome próprio.</Bullet>
        </ul>

        <p style={{ marginTop: 18 }}>
          <b>3.2. Gravan Editora (exceção — atuação como parte signatária)</b>
        </p>
        <p style={{ marginTop: 6 }}>
          Em <b>casos específicos</b>, mediante instrumento contratual próprio
          assinado entre a Gravan e o(s) titular(es) da Obra, a Gravan poderá
          também atuar na qualidade de <b>editora musical</b> — sob a
          identificação de <b>“Gravan Editora”</b> — assumindo direitos e
          obrigações editoriais sobre Obras determinadas (ex.: gestão
          editorial, administração de direitos, exploração comercial conforme
          o escopo do contrato de edição).
        </p>
        <p style={{ marginTop: 12 }}>Nessa qualidade:</p>
        <ul style={{ marginTop: 6 }}>
          <Bullet>A Gravan figura como <b>parte signatária expressa</b> no contrato editorial específico, com qualificação, deveres e remuneração próprios e <b>distintos</b> de sua atuação tecnológica;</Bullet>
          <Bullet>O contrato de edição é regido pelas suas próprias cláusulas, pela Lei 9.610/1998 e demais normas aplicáveis, e <b>não se confunde</b> com a relação de uso da Plataforma regida por estes Termos;</Bullet>
          <Bullet>As <b>obrigações da Gravan Editora</b> existem apenas no âmbito desse contrato específico e não se estendem às demais Obras da Plataforma em que a Gravan não figure como parte;</Bullet>
          <Bullet>A taxa de plataforma (25%) e a fatia editorial (10%) <b>continuam aplicáveis</b> conforme a Cláusula 9, podendo a Gravan Editora ocupar a posição de “editora” no split nas Obras em que assim estiver formalmente identificada.</Bullet>
        </ul>

        <p style={{ marginTop: 16, padding: '12px 14px',
          background: 'var(--surface-2, #F8FAFC)',
          border: '1px solid var(--border, #E5E7EB)', borderRadius: 8,
          fontSize: 13.5, color: 'var(--text-secondary)', lineHeight: 1.6 }}>
          <b>Resumindo:</b> a regra é a Gravan Tecnologia (intermediadora,
          não é parte). A exceção é a Gravan Editora, que só existe quando há
          contrato de edição assinado e identificando expressamente a Gravan
          como parte editorial — e mesmo nesse caso ela responde apenas pelas
          obrigações desse contrato específico, não pelas demais relações da
          Plataforma.
        </p>
      </Section>

      <Section n="4" title="Cadastro e conta">
        Para utilizar a Plataforma o Usuário deve criar uma conta vinculada a
        um perfil (compositor, intérprete, editora ou administrador). O Usuário
        compromete-se a:
        <ul style={{ marginTop: 10 }}>
          <Bullet>Fornecer <b>informações verdadeiras, completas e atualizadas</b> (nome, CPF/CNPJ, RG, endereço, dados bancários quando aplicável);</Bullet>
          <Bullet>Manter seus dados sempre atualizados;</Bullet>
          <Bullet>Ser o responsável <b>exclusivo</b> pela segurança das credenciais de acesso (e-mail e senha) e por todas as ações realizadas em sua conta;</Bullet>
          <Bullet>Não compartilhar a conta com terceiros nem operá-la em nome de outra pessoa sem autorização formal.</Bullet>
        </ul>
        <p style={{ marginTop: 14 }}>
          A Gravan poderá suspender ou encerrar contas em caso de fraude,
          inveracidade nos dados, irregularidade ou violação destes Termos,
          conforme a Cláusula 14.
        </p>
      </Section>

      <Section n="5" title="Publicação de obras">
        Ao enviar uma Obra à Plataforma, o Usuário <b>declara e garante</b>,
        sob as penas da lei, que:
        <ul style={{ marginTop: 10 }}>
          <Bullet>Possui <b>todos os direitos necessários</b> sobre a Obra (autorais, conexos, fonográficos, de imagem etc.) ou autorização expressa de quem os possui;</Bullet>
          <Bullet>A Obra <b>não infringe direitos de terceiros</b>, marcas, patentes, segredos comerciais ou qualquer outra norma aplicável;</Bullet>
          <Bullet>Possui <b>autorização de todos os envolvidos</b> (coautores, intérpretes, produtores, detentores de direitos conexos) para disponibilizar a Obra na Plataforma e celebrar contratos a respeito dela;</Bullet>
          <Bullet>Os percentuais de coautoria (<i>share_pct</i>) cadastrados refletem acordo real entre as partes envolvidas.</Bullet>
        </ul>
        <p style={{ marginTop: 14 }}>
          O <b>Usuário é integralmente responsável pelo conteúdo publicado</b>.
          A Gravan não verifica titularidade nem realiza juízo editorial sobre
          o conteúdo cadastrado.
        </p>
      </Section>

      <Section n="6" title="Licenciamento">
        As Obras são disponibilizadas na Plataforma sob regime de{' '}
        <b>licenciamento não-exclusivo</b>, salvo disposição específica em
        contrário acordada entre as partes no respectivo contrato eletrônico.
        <p style={{ marginTop: 14 }}>
          O comprador recebe <b>apenas o direito de uso</b> da Obra, conforme
          o escopo, prazo, território e finalidades definidos na licença
          adquirida (sincronização, execução pública, reprodução mecânica,
          conforme o caso).
        </p>
        <p style={{ marginTop: 14 }}>
          <b>A propriedade intelectual NÃO é transferida</b> em nenhuma
          hipótese pela mera aquisição de licença na Plataforma. Cessões de
          direitos, contratos de edição ou contratos trilaterais (autor +
          editora + intérprete) seguem instrumentos próprios celebrados
          eletronicamente entre as partes diretamente envolvidas.
        </p>
      </Section>

      <Section n="7" title="Pagamentos e repasses">
        Os pagamentos realizados na Plataforma são processados pela{' '}
        <b>Stripe</b> (parceiro externo), nos termos dos próprios Termos de
        Serviço da Stripe, aos quais o Usuário também adere ao operar na
        Plataforma.
        <p style={{ marginTop: 14 }}><b>Regras gerais:</b></p>
        <ul style={{ marginTop: 10 }}>
          <Bullet>A Gravan retém uma <b>comissão sobre cada transação</b>, conforme a Cláusula 8;</Bullet>
          <Bullet>Os valores podem ficar em <b>período de retenção</b> definido pela Stripe (tipicamente entre 7 e 30 dias) para fins de antifraude e <i>chargeback</i>;</Bullet>
          <Bullet>Após a liberação pela Stripe, o saldo é creditado na carteira interna do Usuário e fica disponível para saque;</Bullet>
          <Bullet>O <b>saque</b> requer conta <b>Stripe Connect</b> ativa e verificada em nome do titular do perfil; o crédito final na conta bancária depende exclusivamente do banco/PSP do Usuário e da Stripe;</Bullet>
          <Bullet>Cada saque exige <b>confirmação por código de 6 dígitos</b> enviado ao e-mail cadastrado;</Bullet>
          <Bullet>Há <b>janela de segurança de 24 h</b> em que o saque pode ser cancelado pelo próprio Usuário antes de ser processado pela Stripe.</Bullet>
        </ul>
      </Section>

      <Section n="8" title="Taxas e comissões">
        A Gravan cobra:
        <ul style={{ marginTop: 10 }}>
          <Bullet><b>Comissão de plataforma de 25% sobre o valor bruto</b> de cada transação realizada na Plataforma, aplicada a todos os planos. Esta comissão é <b>intacta</b> — a Gravan não absorve nenhuma parte da taxa Stripe.</Bullet>
          <Bullet><b>Taxa Stripe</b> (variável conforme método de pagamento), absorvida proporcionalmente pela editora vinculada (quando houver) e pelos autores/coautores envolvidos na transação.</Bullet>
          <Bullet><b>Plano PRO</b>: assinatura mensal de <b>R$ 49,90</b>, com acesso a propostas de licenciamento direto, precificação até R$ 10.000, painel de analytics e benefícios adicionais descritos na página de Planos.</Bullet>
          <Bullet><b>Plano STARTER</b>: gratuito, sem assinatura mensal, com a mesma comissão de 25% sobre as transações.</Bullet>
          <Bullet>Eventuais <b>taxas de serviços adicionais</b> serão sempre comunicadas previamente ao Usuário e exigirão aceite expresso para serem cobradas.</Bullet>
        </ul>
        <p style={{ marginTop: 14 }}>
          Os valores e regras de cobrança podem ser atualizados pela Gravan{' '}
          <b>mediante aviso prévio</b> de no mínimo 30 dias, comunicado pela
          Plataforma ou por e-mail. O plano PRO é renovado automaticamente
          pela Stripe a cada ciclo mensal e pode ser cancelado a qualquer
          momento; <b>não há reembolso proporcional</b> de assinaturas já
          cobradas.
        </p>
      </Section>

      <Section n="9" title="Sistema de split">
        A divisão de receitas entre múltiplos Usuários (autores, coautores e
        editora vinculada) opera da seguinte forma a cada venda:
        <ul style={{ marginTop: 10 }}>
          <Bullet><b>Gravan</b> (na qualidade de Plataforma — Cláusula 3.1): 25% do valor bruto;</Bullet>
          <Bullet><b>Editora</b> (quando o titular é agregado a uma editora): 10/75 do pool restante. A posição de editora pode ser ocupada por uma <b>editora terceira</b> ou pela <b>Gravan Editora</b> (Cláusula 3.2), conforme identificado no contrato editorial da Obra;</Bullet>
          <Bullet><b>Autores e coautores</b>: o restante do pool, distribuído conforme os percentuais (<i>share_pct</i>) cadastrados na Obra.</Bullet>
        </ul>
        <p style={{ marginTop: 14 }}>
          Os percentuais de coautoria (<i>share_pct</i>) são <b>definidos
          pelos próprios Usuários</b> no momento do cadastro da Obra e devem
          refletir <b>acordos reais</b> celebrados entre as partes envolvidas.
        </p>
        <p style={{ marginTop: 14 }}>
          <b>A Gravan NÃO se responsabiliza por disputas internas de divisão
          entre coautores, intérpretes ou editoras</b>, nem por percentuais
          incorretos cadastrados pelos próprios Usuários. A Plataforma
          executa a divisão estritamente conforme os percentuais informados
          pelo titular no cadastro.
        </p>
      </Section>

      <Section n="10" title="Conteúdo proibido">
        É expressamente proibido publicar, enviar ou veicular na Plataforma:
        <ul style={{ marginTop: 10 }}>
          <Bullet>Conteúdo com <b>direitos de terceiros sem autorização</b> (plágio, sample não autorizado, capa/letra/melodia de terceiros);</Bullet>
          <Bullet>Material <b>ilegal, ofensivo, discriminatório, fraudulento</b> ou que viole a legislação aplicável;</Bullet>
          <Bullet>Tentativas de <b>manipular pagamentos, comissões, split ou qualquer mecanismo da Plataforma</b> (incluindo combinar a venda dentro da Plataforma e fechar fora dela para burlar a comissão);</Bullet>
          <Bullet>Conteúdo que incite ódio, violência, atos ilícitos ou que viole direitos de personalidade de terceiros;</Bullet>
          <Bullet>Engenharia reversa, raspagem em larga escala (<i>scraping</i>) ou exploração comercial não autorizada da Plataforma.</Bullet>
        </ul>
      </Section>

      <Section n="11" title="Remoção de conteúdo">
        A Gravan poderá <b>remover, despublicar ou suspender</b> Obras e
        demais conteúdos que:
        <ul style={{ marginTop: 10 }}>
          <Bullet>Infrinjam direitos autorais, conexos ou de propriedade intelectual de terceiros;</Bullet>
          <Bullet>Recebam denúncias válidas, conforme a Cláusula 12;</Bullet>
          <Bullet>Violem estes Termos ou a legislação aplicável;</Bullet>
          <Bullet>Estejam envolvidos em controvérsia documentada entre Usuários, até resolução pela própria parte ou pelo Poder Judiciário.</Bullet>
        </ul>
        <p style={{ marginTop: 14 }}>
          A remoção pode ser <b>preventiva</b>, sem necessidade de notificação
          prévia, especialmente em casos de risco de dano grave a terceiros
          ou à própria Plataforma.
        </p>
      </Section>

      <Section n="12" title="Denúncias e copyright">
        A Plataforma disponibiliza mecanismos de denúncia em fluxo análogo ao
        utilizado por grandes plataformas (ex.: YouTube), incluindo formulário
        próprio para reclamações de violação de direitos autorais.
        <p style={{ marginTop: 14 }}><b>Após uma denúncia válida:</b></p>
        <ul style={{ marginTop: 10 }}>
          <Bullet>O conteúdo poderá ser <b>removido preventivamente</b> enquanto a denúncia é analisada;</Bullet>
          <Bullet>O Usuário denunciado poderá ser notificado e ter a oportunidade de apresentar contranotificação;</Bullet>
          <Bullet>Em caso de reincidência ou denúncia comprovadamente procedente, o Usuário poderá ser <b>suspenso ou banido</b>;</Bullet>
          <Bullet>A Gravan poderá, mediante apresentação de ordem judicial, fornecer registros eletrônicos (data, hora, IP, metadados de assinatura) para fins probatórios.</Bullet>
        </ul>
      </Section>

      <Section n="13" title="Limitação de responsabilidade (essencial)">
        Na máxima extensão permitida pela legislação aplicável,{' '}
        <b>a Gravan NÃO se responsabiliza por</b>:
        <ul style={{ marginTop: 10 }}>
          <Bullet><b>Conteúdos enviados pelos Usuários</b> (titularidade, qualidade, legalidade, exequibilidade);</Bullet>
          <Bullet><b>Disputas de direitos autorais</b>, conexos, fonográficos, de imagem ou de personalidade entre Usuários ou entre Usuários e terceiros;</Bullet>
          <Bullet><b>Acordos celebrados entre Usuários</b> na Plataforma — a Gravan não tem legitimidade passiva para responder por obrigações assumidas nesses contratos (incluindo inadimplência, falha de entrega, vício, rescisão, indenizações, royalties ou cobrança de saldos);</Bullet>
          <Bullet><b>Perdas indiretas, lucros cessantes</b>, danos morais reflexos ou perda de oportunidade comercial;</Bullet>
          <Bullet>Indisponibilidades pontuais de provedores terceiros (Stripe, e-mail, hospedagem, redes de internet, autoridades certificadoras);</Bullet>
          <Bullet>Eventos de força maior, caso fortuito, ataque cibernético externo ou ato de terceiros.</Bullet>
        </ul>
        <p style={{ marginTop: 14, padding: '12px 14px',
          background: 'var(--surface-2, #F8FAFC)',
          border: '1px solid var(--border, #E5E7EB)', borderRadius: 8,
          fontSize: 13.5, color: 'var(--text-secondary)', lineHeight: 1.6 }}>
          <b>Exceção (Gravan Editora):</b> as exclusões de responsabilidade
          desta cláusula referem-se à atuação da Gravan como{' '}
          <b>intermediadora tecnológica</b> (Cláusula 3.1). Quando a Gravan
          figurar expressamente como <b>parte signatária</b> de um contrato
          editorial específico — na qualidade de <b>Gravan Editora</b>{' '}
          (Cláusula 3.2) — sua responsabilidade no âmbito daquele contrato
          editorial será regida pelas próprias cláusulas do referido
          instrumento e pela legislação aplicável, e <b>não pelas exclusões
          desta Cláusula 13</b>, observada apenas a limitação financeira
          global do parágrafo seguinte.
        </p>
        <p style={{ marginTop: 14 }}>
          Em qualquer hipótese, a responsabilidade total da Gravan perante o
          Usuário fica limitada ao valor que o Usuário tenha efetivamente pago
          à Gravan a título de assinatura ou taxa de plataforma nos <b>12
          meses anteriores</b> ao evento que originou o pleito.
        </p>
        <p style={{ marginTop: 14 }}>
          O Usuário é responsável por manter <b>cópias próprias</b> de suas
          obras e contratos. As exportações disponíveis na Plataforma (PDF,
          dossiê) são fornecidas como conveniência, não como obrigação
          contratual.
        </p>
      </Section>

      <Section n="14" title="Suspensão e banimento">
        A Gravan poderá <b>suspender ou encerrar</b> contas, total ou
        parcialmente, em caso de:
        <ul style={{ marginTop: 10 }}>
          <Bullet><b>Violação destes Termos</b> ou da legislação aplicável;</Bullet>
          <Bullet><b>Fraude</b>, inveracidade nos dados ou tentativa de burlar comissões/split;</Bullet>
          <Bullet><b>Atividades suspeitas</b> ou indícios de uso para lavagem de dinheiro, financiamento ilícito ou qualquer atividade contrária à legislação aplicável;</Bullet>
          <Bullet>Reincidência em denúncias válidas (Cláusula 12);</Bullet>
          <Bullet>Uso da Plataforma de forma incompatível com sua finalidade.</Bullet>
        </ul>
        <p style={{ marginTop: 14 }}>
          Contratos já celebrados <b>permanecem válidos entre as partes</b>{' '}
          mesmo após o encerramento da conta de qualquer dos signatários.
          Saldo eventualmente disponível pode ser sacado antes do encerramento,
          observada a conexão ativa com a Stripe Connect.
        </p>
      </Section>

      <Section n="15" title="Alterações nos termos">
        Estes Termos poderão ser <b>atualizados a qualquer momento</b> pela
        Gravan. Mudanças relevantes serão comunicadas pela Plataforma e/ou
        por e-mail com no mínimo 30 dias de antecedência da entrada em vigor,
        exceto em casos de adequação a determinação legal ou regulatória,
        quando o prazo poderá ser menor.
        <p style={{ marginTop: 14 }}>
          O <b>uso contínuo</b> da Plataforma após a entrada em vigor da nova
          versão implica aceitação das alterações. O usuário poderá, a
          qualquer momento, encerrar sua conta caso não concorde com a nova
          redação.
        </p>
      </Section>

      <Section n="16" title="Legislação e foro">
        Estes Termos são regidos pela <b>legislação brasileira</b>, em
        especial pelo Código Civil, Lei de Direitos Autorais (Lei nº
        9.610/1998), Marco Civil da Internet (Lei nº 12.965/2014), Lei Geral
        de Proteção de Dados (Lei nº 13.709/2018) e Lei das Assinaturas
        Eletrônicas (Lei nº 14.063/2020 e MP 2.200-2/2001).
        <p style={{ marginTop: 14 }}>
          Fica eleito o <b>foro da Comarca de São Paulo/SP</b> — cidade de
          operação da Gravan — para dirimir qualquer controvérsia entre o
          Usuário e a Gravan oriunda da relação de uso da Plataforma, com
          expressa renúncia a qualquer outro, por mais privilegiado que seja.
        </p>
      </Section>

      <p style={{
        marginTop: 32, padding: '14px 16px',
        background: 'var(--surface-2, #F8FAFC)',
        border: '1px solid var(--border, #E5E7EB)',
        borderRadius: 10, fontSize: 13, color: 'var(--text-secondary)',
        lineHeight: 1.6,
      }}>
        Ao concluir o cadastro na Plataforma você confirma ter lido e aceito
        integralmente estes Termos de Uso. A versão vigente fica registrada
        na sua conta com data, hora UTC e IP, para fins probatórios.
      </p>
    </LegalLayout>
  )
}
