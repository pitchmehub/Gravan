from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
import io, datetime

buf = io.BytesIO()
doc = SimpleDocTemplate(
    buf, pagesize=A4,
    leftMargin=2.5*cm, rightMargin=2.5*cm,
    topMargin=2.5*cm, bottomMargin=2.5*cm,
    title='Gravan — Descricao Completa da Plataforma',
    author='Gravan',
)

BRAND  = colors.HexColor('#0C447C')
BRAND2 = colors.HexColor('#378ADD')
DARK   = colors.HexColor('#09090B')
MUTED  = colors.HexColor('#71717A')
BG     = colors.HexColor('#F0F6FF')

title_s    = ParagraphStyle('ts', fontName='Helvetica-Bold', fontSize=28, leading=34, textColor=BRAND,  alignment=TA_CENTER, spaceAfter=6)
subtitle_s = ParagraphStyle('ss', fontName='Helvetica',      fontSize=13, leading=18, textColor=MUTED,  alignment=TA_CENTER, spaceAfter=4)
date_s     = ParagraphStyle('ds', fontName='Helvetica',      fontSize=10, leading=13, textColor=MUTED,  alignment=TA_CENTER, spaceAfter=20)
h1_s       = ParagraphStyle('h1', fontName='Helvetica-Bold', fontSize=15, leading=20, textColor=BRAND,  spaceBefore=18, spaceAfter=5)
h2_s       = ParagraphStyle('h2', fontName='Helvetica-Bold', fontSize=11, leading=15, textColor=DARK,   spaceBefore=10, spaceAfter=3)
h3_s       = ParagraphStyle('h3', fontName='Helvetica-Bold', fontSize=10, leading=14, textColor=BRAND2, spaceBefore=7,  spaceAfter=3)
body_s     = ParagraphStyle('b',  fontName='Helvetica',      fontSize=9.5,leading=14, textColor=DARK,   alignment=TA_JUSTIFY, spaceAfter=5)
bullet_s   = ParagraphStyle('bl', fontName='Helvetica',      fontSize=9.5,leading=13, textColor=DARK,   leftIndent=14, spaceAfter=3)
small_s    = ParagraphStyle('sm', fontName='Helvetica',      fontSize=8,  leading=11, textColor=MUTED,  alignment=TA_CENTER)

def H1(t): return Paragraph(t, h1_s)
def H2(t): return Paragraph(t, h2_s)
def H3(t): return Paragraph(t, h3_s)
def P(t):  return Paragraph(t, body_s)
def B(t):  return Paragraph('&bull; ' + t, bullet_s)
def SP(n=0.3): return Spacer(1, n*cm)
def HR(): return HRFlowable(width='100%', thickness=0.5, color=colors.HexColor('#E4E4E7'), spaceAfter=6, spaceBefore=4)

def tabela(data, widths):
    t = Table(data, colWidths=widths)
    t.setStyle(TableStyle([
        ('BACKGROUND',    (0,0),(-1,0), BRAND),
        ('TEXTCOLOR',     (0,0),(-1,0), colors.white),
        ('FONTNAME',      (0,0),(-1,0), 'Helvetica-Bold'),
        ('FONTSIZE',      (0,0),(-1,-1), 9),
        ('FONTNAME',      (0,1),(-1,-1), 'Helvetica'),
        ('ROWBACKGROUNDS',(0,1),(-1,-1), [colors.white, BG]),
        ('GRID',          (0,0),(-1,-1), 0.3, colors.HexColor('#E4E4E7')),
        ('LEFTPADDING',   (0,0),(-1,-1), 8),
        ('RIGHTPADDING',  (0,0),(-1,-1), 8),
        ('TOPPADDING',    (0,0),(-1,-1), 5),
        ('BOTTOMPADDING', (0,0),(-1,-1), 5),
        ('VALIGN',        (0,0),(-1,-1), 'MIDDLE'),
    ]))
    return t

story = []

# CAPA
story += [
    SP(2),
    Paragraph('GRAVAN', title_s),
    Paragraph('Plataforma de Composicoes Musicais', subtitle_s),
    Paragraph('Documento gerado em ' + datetime.date.today().strftime('%d/%m/%Y'), date_s),
    HR(),
    SP(0.4),
    P('Este documento descreve de forma minuciosa o funcionamento, os servicos, as taxas, a infraestrutura e os aspectos juridicos da plataforma <b>Gravan</b> — o marketplace digital brasileiro de composicoes musicais.'),
    SP(1),
]

# 1. O QUE E
story += [
    H1('1. O que e a Gravan'),
    HR(),
    P('A <b>Gravan</b> e um marketplace digital brasileiro de composicoes musicais, operando como intermediario tecnologico entre compositores (vendedores) e interpretes/produtores musicais (compradores). A plataforma permite o registro, protecao, exibicao e licenciamento de obras musicais ineditas, com infraestrutura juridica, financeira e de autoria completamente integrada.'),
    P('A Gravan opera sob <b>dupla personalidade juridica</b>:'),
    B('<b>Gravan Tecnologia</b> — atua como intermediaria tecnologica no licenciamento, nao sendo parte no contrato de licenca entre compositor e comprador.'),
    B('<b>Gravan Editora</b> — atua como editora musical signataria quando a obra e gerenciada diretamente pela Gravan, assumindo obrigacoes editoriais formais.'),
    SP(),
]

# 2. PLANOS
story += [
    H1('2. Planos e Assinatura'),
    HR(),
    H2('2.1. Plano STARTER (Gratuito)'),
    B('Acesso completo ao catalogo, player e sistema de curtidas'),
    B('Cadastro e publicacao ilimitada de obras'),
    B('Limite de preco de licenca: R$ 500 a R$ 1.000 por obra'),
    B('Participacao no marketplace como compositor ou comprador'),
    B('Pode vender obras e receber via carteira interna'),
    SP(0.5),
    H2('2.2. Plano PRO — R$ 49,90/mes'),
    B('Limite de preco de licenca: R$ 500 a R$ 10.000 por obra'),
    B('Acesso a propostas e contraofertas diretas entre compositor e comprador'),
    B('Selo PRO exibido no perfil e nas obras — diferencial visual no catalogo'),
    B('Maior visibilidade na secao Descoberta da plataforma'),
    B('Analytics avancados de visualizacoes e interacoes por obra'),
    B('Cobranca recorrente mensal via Stripe Billing'),
    SP(0.5),
    H2('2.3. Dunning (Inadimplencia)'),
    P('Se o pagamento mensal falha, o status da assinatura muda para <b>past_due</b>. O usuario tem <b>7 dias de carencia</b> para regularizar. Apos esse prazo, a rotina automatica cancela a assinatura no Stripe e rebaixa o perfil para STARTER sem intervencao manual.'),
    SP(),
]

# 3. CADASTRO
story += [
    H1('3. Cadastro de Obras'),
    HR(),
    P('Ao cadastrar uma composicao, o compositor informa:'),
    B('Nome da obra e letra completa'),
    B('Genero musical (lista fechada de generos brasileiros)'),
    B('Preco da licenca em reais, dentro dos limites do plano contratado'),
    B('Arquivo de audio em MP3 (validado por magic number e tamanho maximo)'),
    B('Coautorias: outros compositores cadastrados com percentual de participacao'),
    B('Tipo de gravacao: "Voz e Violao" ou "Demo (Guia)" — badge visivel para compradores'),
    B('Informacoes de editora terceira quando a obra ja possui vinculo editorial externo'),
    SP(0.4),
    H3('Protecao Anti-Duplicata'),
    P('O sistema gera um hash MD5 do arquivo de audio e da letra. Se qualquer um ja existir na base, o upload e rejeitado — impedindo que a mesma composicao seja publicada duas vezes, por qualquer usuario.'),
    H3('Capa Gerada por Inteligencia Artificial'),
    P('Apos o cadastro, uma capa artistica e gerada automaticamente via <b>Pollinations.ai</b> com prompt neo-minimalista usando nome e genero da obra. A URL e salva diretamente sem download — custo zero de armazenamento.'),
    H3('Metadados Tecnicos Suportados'),
    B('ISRC (International Standard Recording Code)'),
    B('ISWC (International Standard Musical Work Code)'),
    B('BPM (batidas por minuto) e idioma da composicao'),
    SP(),
]

# 4. CATALOGO
story += [
    H1('4. Catalogo e Descoberta'),
    HR(),
    P('A pagina <b>Descoberta</b> e o coracao do marketplace. Exibe as obras em grade com capa, nome, genero, badge de tipo de gravacao, badge de exclusividade e sistema de curtidas. O catalogo suporta:'),
    B('Filtro por genero musical'),
    B('Busca por nome da obra'),
    B('Ordenacao por: mais recentes, mais antigas, preco crescente/decrescente, nome'),
    B('Filtro exclusivo de obras de compositores assinantes PRO'),
    B('Pre-carregamento de dados ao passar o mouse sobre os cards (prefetch)'),
    SP(0.4),
    H3('Ficha Tecnica — Modal do Comprador'),
    P('Ao clicar em uma obra, abre um modal completo com efeito cinema (fundo borrado + capa nítida flutuando), exibindo: nome, genero, tipo de gravacao, badge de exclusividade, lista de compositores com avatar e selo PRO, links para perfis publicos, botao de licenciamento e botao de oferta (exclusivo PRO).'),
    SP(),
]

# 5. LICENCIAMENTO
story += [
    H1('5. Licenciamento e Contratos'),
    HR(),
    H2('5.1. Fluxo Bilateral (Compositor e Comprador)'),
    B('Comprador preenche dados pessoais: nome, CPF, RG, endereco'),
    B('Sistema gera contrato HTML personalizado com dados das duas partes'),
    B('Comprador assina eletronicamente (IP hasheado + timestamp)'),
    B('Compositor recebe notificacao em tempo real e tambem assina'),
    B('Contrato concluido: credito liberado na carteira do compositor (escrow liberado)'),
    SP(0.3),
    H2('5.2. Fluxo Trilateral (com Editora)'),
    P('Quando a obra tem editora vinculada, o contrato inclui tres partes: autor, editora e comprador. A editora tambem assina digitalmente antes da liberacao dos fundos.'),
    H2('5.3. Contratos de Oferta (exclusivo PRO)'),
    P('Assinantes PRO podem enviar propostas com valor diferente do listado. O compositor pode aceitar, recusar ou fazer contraproposta. Aceita a oferta, o fluxo de assinatura segue o processo padrao.'),
    H2('5.4. Exclusividade'),
    P('Uma obra pode ser licenciada com clausula de exclusividade, bloqueando novas licencas pelo periodo acordado. Exibida como badge roxo na ficha tecnica, com data de vencimento visivel.'),
    SP(),
]

# 6. FINANCEIRO
story += [
    H1('6. Financeiro e Distribuicao de Valores'),
    HR(),
    tabela([
        ['Parte', 'Percentual', 'Condicao'],
        ['Gravan (plataforma)', '25%', 'Sempre, sobre o valor bruto da licenca'],
        ['Editora interna (publisher)', '10%', 'Somente se a obra tiver editora vinculada'],
        ['Autores / Coautores', '65% a 75%', 'Dividido pro-rata pelo share_pct de cada um'],
        ['Taxas Stripe', 'Variavel', 'Absorvidas pelos autores e editora, nao pela Gravan'],
    ], [4.5*cm, 3*cm, 8*cm]),
    SP(0.5),
    H2('6.1. Carteira Interna (Wallets)'),
    P('Cada perfil possui uma carteira interna. O credito <b>so e adicionado apos o contrato estar concluido e assinado por todas as partes</b> — regra de escrow absoluta. Nenhum valor e creditado sem contrato plenamente assinado.'),
    H2('6.2. Retencao de Repasse'),
    P('Se um coautor nao possui conta Stripe Connect ativa, o repasse fica com status <b>retido</b> ate que ele complete o processo de onboarding na plataforma.'),
    SP(),
]

# 7. SAQUES
story += [
    H1('7. Saques'),
    HR(),
    P('O sistema de saques possui multiplas camadas de seguranca antifraude:'),
    B('<b>Pre-requisito:</b> conta Stripe Connect Express verificada e ativa'),
    B('<b>OTP por e-mail:</b> codigo de 6 digitos — obrigatorio para iniciar o processo'),
    B('<b>Janela de 24 horas:</b> apos confirmacao, o saque entra em espera de seguranca'),
    B('<b>E-mail "Nao fui eu":</b> link enviado para cancelamento imediato caso nao reconheca'),
    B('<b>Liberacao:</b> apos 24h, transferencia via Stripe Transfer vinculada a venda original'),
    B('<b>Saque automatico mensal:</b> no ultimo dia util do mes, gerado automaticamente para usuarios com saldo'),
    SP(),
]

# 8. PUBLISHERS
story += [
    H1('8. Publishers — Editoras Internas'),
    HR(),
    P('Editoras musicais podem operar dentro da plataforma como <b>publishers</b>. Um publisher pode:'),
    B('Cadastrar novos artistas ("ghost users") com convite por e-mail'),
    B('Vincular artistas ja cadastrados via convite — artista aceita ou recusa'),
    B('Gerenciar catalogo dos agregados: obras, contratos, repasses e dashboard individual'),
    B('Assinar contratos trilaterais como parte intermediaria no licenciamento'),
    B('Receber 10% de cada licenca de obras sob sua gestao'),
    SP(0.4),
    H3('Termo de Agregacao'),
    P('Ao vincular um artista, e gerado um Contrato de Edicao Editorial com conteudo HTML, hash SHA-256, IP de assinatura de ambas as partes, carimbagem de tempo TSA e certificado de conclusao. Esse contrato e incluido no Dossie da obra quando aplicavel.'),
    SP(),
]

# 9. DOSSIE
story += [
    H1('9. Dossie da Obra (Master Package)'),
    HR(),
    P('O dossie e um arquivo ZIP oficial gerado pelo compositor, servindo como prova de autoria e integridade. Contem:'),
    tabela([
        ['Arquivo', 'Conteudo'],
        ['obra/audio.mp3',     'Arquivo de audio original enviado na plataforma'],
        ['obra/letra.txt',     'Letra completa da composicao em UTF-8'],
        ['obra/metadata.json', 'JSON com titulo, idioma, autores, splits, editora, ISRC, ISWC, BPM, royalties'],
        ['obra/contrato.pdf',  'PDF do contrato de edicao assinado (Gravan ou editora interna)'],
        ['obra/resumo.pdf',    'PDF de resumo com dados de autoria e hash de integridade'],
        ['obra/hash.txt',      'Hash SHA-256 de todos os arquivos para verificacao externa'],
    ], [4.5*cm, 11*cm]),
    SP(0.4),
    P('O contrato incluido e buscado em tres camadas: (1) contrato Gravan direto, (2) contrato com editora interna, (3) documento sintetico como fallback.'),
    SP(),
]

# 10. JURIDICO
story += [
    H1('10. Aspectos Legais e Compliance'),
    HR(),
    H2('10.1. Validade Juridica dos Contratos'),
    B('Assinatura eletronica com fundamento na MP n 2.200-2/2001 e Lei n 14.063/2020'),
    B('IP de assinatura hasheado e registrado para cada parte contratante'),
    B('Carimbagem de tempo RFC 3161 (TSA) aplicada aos contratos em best-effort'),
    B('Hash SHA-256 do conteudo registrado para verificacao de integridade futura'),
    H2('10.2. Privacidade e Dados Sensiveis'),
    B('CPF, RG e CNPJ criptografados em AES-256 em repouso no banco de dados'),
    B('Descriptografia somente na geracao de contratos — nunca expostos em APIs publicas'),
    B('IPs de acesso hasheados nos logs de auditoria'),
    H2('10.3. Auditoria'),
    B('Log de auditoria para: login, assinatura de contratos, saques, alteracoes de perfil'),
    B('Todos os eventos registrados com timestamp e identificador do usuario'),
    H2('10.4. Denuncias / DMCA'),
    B('Mecanismo interno para reportar plagio ou uploads nao autorizados'),
    B('Revisao administrativa com possibilidade de remocao da obra da plataforma'),
    SP(),
]

# 11. INFRAESTRUTURA
story += [
    H1('11. Infraestrutura Tecnica'),
    HR(),
    tabela([
        ['Componente', 'Tecnologia'],
        ['Backend',            'Python 3.11 / Flask / Gunicorn (porta 8000)'],
        ['Frontend',           'React 18 / Vite (porta 5000)'],
        ['Banco de dados',     'Supabase (PostgreSQL) + Row Level Security'],
        ['Autenticacao',       'Supabase Auth — e-mail/senha + Google OAuth'],
        ['Pagamentos',         'Stripe Billing + Stripe Connect Express'],
        ['Storage',            'Supabase Storage — audios privados, capas, dossies'],
        ['Busca full-text',    'Coluna fts com tsvector nativo do PostgreSQL'],
        ['E-mail transacional','Resend'],
        ['IA de capas',        'Pollinations.ai — geracao por URL sem custo de storage'],
        ['Notificacoes',       'Supabase Realtime + alerta sonoro via Web Audio API'],
        ['Watchdog',           'Processo Python independente — monitora saude, dunning e reconciliacao'],
        ['Deploy',             'Replit — dominio gravan.com.br'],
    ], [5*cm, 10.5*cm]),
    SP(),
    HR(),
    Paragraph('Gravan — Plataforma de Composicoes Musicais · Documento gerado automaticamente · Confidencial', small_s),
]

def rodape(canvas, doc):
    canvas.saveState()
    canvas.setFont('Helvetica', 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(2.5*cm, 1.3*cm, 'Gravan — Descricao da Plataforma')
    canvas.drawRightString(A4[0]-2.5*cm, 1.3*cm, 'Pagina ' + str(doc.page))
    canvas.restoreState()

doc.build(story, onFirstPage=rodape, onLaterPages=rodape)

pdf_bytes = buf.getvalue()
with open('/tmp/gravan_descricao.pdf', 'wb') as f:
    f.write(pdf_bytes)
print('OK:', len(pdf_bytes), 'bytes')
