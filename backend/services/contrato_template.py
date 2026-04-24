"""Template do Contrato de Edição Musical — Gravan.

Fica em Python para que o backend possa:
  1. Seedar automaticamente a tabela `landing_content` no startup (idempotente)
     caso a chave `contrato_edicao_template` esteja ausente ou vazia.
  2. Servir como fallback em runtime se a linha do DB sumir.

O texto pode ser SOBRESCRITO pelo admin via CMS `/admin/landing` — o backend
não substitui o que já estiver no banco (respeita edições manuais).
"""

CONTRATO_TEMPLATE = """CONTRATO DE EDIÇÃO DE OBRAS MUSICAIS E OUTRAS AVENÇAS

Pelo presente instrumento particular, de um lado:

AUTOR: {{nome_completo}}, portador do RG nº {{rg}}, inscrito no CPF/MF sob o nº {{cpf}}, residente e domiciliado em {{endereco_completo}}, e-mail {{email}}, doravante denominado "AUTOR";

e, de outro lado:

EDITORA: {{plataforma_razao_social}}, inscrita no CNPJ/MF sob o nº {{plataforma_cnpj}}, com sede em {{plataforma_endereco}}, doravante denominada "EDITORA";

AUTOR e EDITORA, doravante denominadas, em conjunto, "PARTES" e, individualmente, "PARTE", firmam entre si o presente Contrato de Edição de Obras Musicais e Outras Avenças, doravante denominado "Contrato", mediante as cláusulas e condições a seguir.

CONSIDERANDO QUE:
(i) o AUTOR é titular de {{share_autor_pct}}% (por cento) dos direitos autorais sobre a obra lítero-musical intitulada "{{obra_nome}}", doravante denominada "OBRA";
(ii) sendo os demais titulares/coautores: {{coautores_lista}};
(iii) a EDITORA, por meio da assinatura deste Contrato, tornar-se-á a editora musical e detentora dos direitos autorais patrimoniais sobre a parte do AUTOR na OBRA, observados os termos aqui previstos, nos moldes da Lei nº 9.610/1998 (Lei de Direitos Autorais).

CLÁUSULA PRIMEIRA — OBJETO

1.1 Por meio deste Contrato, o AUTOR (i) contrata com a EDITORA a edição musical de sua parte sobre a OBRA, com indicação do respectivo percentual de edição, em regime de absoluta exclusividade e sem qualquer limitação territorial; e (ii) outorga, desde logo, à EDITORA o direito único e exclusivo sobre o recebimento de qualquer valor decorrente das explorações comerciais havidas com a edição da OBRA pela EDITORA, na forma, extensão e aplicação em que os possui por força das Leis Brasileiras e Tratados Internacionais em vigor, e dos que vierem a vigorar no futuro, observadas as remunerações devidas ao AUTOR na forma da Cláusula Sexta.

1.2 O AUTOR desde já concorda e reconhece que a EDITORA poderá contratar com quaisquer outras editoras a administração das obras musicais e/ou lítero-musicais que integram ou venham a integrar o catálogo da EDITORA, incluindo a OBRA objeto deste Contrato, em relação ao que o AUTOR não se opõe.

1.3 Para todos os efeitos legais, integra o presente Contrato a LETRA COMPLETA da OBRA, conforme cadastrada pelo AUTOR na plataforma Gravan, transcrita a seguir:

— CORPO DA OBRA "{{obra_nome}}" —
{{obra_letra}}
— FIM DO CORPO DA OBRA —

CLÁUSULA SEGUNDA — DIREITOS

2.1 Pelo presente Contrato, ficam sob a égide da EDITORA, sem quaisquer limitações e durante todo o tempo de proteção legal dos direitos autorais e em todos os países do mundo, a totalidade dos direitos e faculdades que no seu conjunto constituem o direito autoral do AUTOR sobre a OBRA, em todos os seus aspectos, manifestações e aplicações diretas ou indiretas, processos de reprodução e divulgação ou extensões e ampliações, tais como, mas não limitados a: edição gráfica e fonomecânica em todas as suas formas, aplicações, sistemas e processos, quer atuais, quer os que venham a ser inventados ou aperfeiçoados no futuro; transcrição; adaptação; versões; variação; redução; execução; irradiação; distribuição física ou eletrônica, incluindo, mas não se limitando a download, streaming, ringtone, truetone, qualquer tipo de sincronização em suporte físico ou digital, existente ou que venha a existir, tais como televisão, VOD, adaptação e/ou inclusão cinematográfica, ou, ainda, em peças publicitárias, com a adaptação da letra e/ou melodia, em publicidade gráfica, sonora ou audiovisual, bem como qualquer forma de exploração, reprodução e divulgação da OBRA, incluindo sua execução pública, sem nenhuma exceção, mesmo que no futuro outras venham a ser as denominações da técnica ou da praxe, com todas as faculdades de exploração comercial e industrial necessárias para o exercício dos respectivos direitos, a exclusivo arbítrio da EDITORA. Serve o presente Contrato como título para que a EDITORA possa efetuar, onde lhe for útil ou conveniente, os registros e depósitos necessários para o irrestrito reconhecimento de seu direito, em todos os países do mundo, com faculdade de transferir os direitos ora adquiridos a terceiros, no todo ou em parte, a qualquer título.

2.2 Fica reservada ao AUTOR, na forma da lei, a integralidade dos direitos morais sobre sua parte na OBRA, nos termos do art. 24 da Lei nº 9.610/1998.

CLÁUSULA TERCEIRA — PROCURAÇÃO

3.1 Fica a EDITORA desde já constituída como bastante procuradora do AUTOR, com amplos e irrevogáveis poderes para que, em seu nome, possa defender e receber os direitos concernentes à OBRA.

CLÁUSULA QUARTA — ORIGINALIDADE

4.1 O AUTOR é exclusiva e pessoalmente responsável pela originalidade de sua parte sobre a OBRA, exonerando a EDITORA de toda e qualquer responsabilidade nesse sentido e obrigando-se a indenizá-la pelas perdas e danos que esta vier a sofrer em caso de contestação.

4.2 O AUTOR declara, sob as penas da lei, que a OBRA é de sua autoria (ou coautoria, conforme o caso), não constituindo plágio ou violação de direito autoral de terceiros, e que se encontra LIVRE e DESEMBARAÇADA de qualquer contrato de edição prévio com terceiros.

CLÁUSULA QUINTA — EDIÇÃO

5.1 A EDITORA, por este Contrato, obriga-se a editar, divulgar e expor à venda a OBRA, sendo certo que a tiragem de cada edição, o número de edições, a fixação da época, a determinação da forma e os detalhes de confecção artística, bem como o preço de venda ao público das edições, ficarão a exclusivo critério da EDITORA, que deverá envidar seus melhores esforços para consultar o AUTOR sobre valores das licenças, em especial na eventualidade de licenças sem ônus.

5.2 A EDITORA compromete-se a envidar seus melhores esforços para consultar o AUTOR sobre oportunidades de comercialização e uso da OBRA.

CLÁUSULA SEXTA — REMUNERAÇÃO

6.1 Pelo presente Contrato, a EDITORA obriga-se a pagar ao AUTOR os percentuais abaixo especificados, relativos às receitas líquidas efetivamente recebidas pela EDITORA pela exploração da OBRA, sempre incidentes sobre o percentual de direitos autorais do AUTOR sobre a OBRA, da seguinte forma:
  (a) Direitos de Sincronização e adaptação em produções audiovisuais, publicitárias ou não: 70% (setenta por cento) ao AUTOR e 30% (trinta por cento) à EDITORA;
  (b) Direitos de reprodução gráfica (edição); distribuição de direitos fonomecânicos; venda e locação de gravações sonoras; distribuição mediante meios óticos, cabo, satélites, redes de informação e rede local e/ou mundial de computadores que permitam ao usuário a seleção da obra ou que importe em pagamento pelo usuário; inclusão em base de dados ou qualquer forma de armazenamento; e demais modalidades previstas na Cláusula Segunda: 75% (setenta e cinco por cento) ao AUTOR e 25% (vinte e cinco por cento) à EDITORA;
  (c) Direitos de Execução Pública, observado o disposto na Cláusula 6.2: 75% (setenta e cinco por cento) ao AUTOR e 25% (vinte e cinco por cento) à EDITORA.

6.2 Os direitos de execução pública serão pagos ao AUTOR diretamente pela Sociedade de Autores a que este for filiado, sob sua exclusiva responsabilidade.

6.3 O AUTOR declara-se ciente e concorda expressamente que a EDITORA procederá à retenção proporcional do valor correspondente ao Imposto de Renda pago pela EDITORA sobre a remuneração recebida por esta pela exploração da OBRA, repassando ao AUTOR o montante líquido devido após a retenção.

CLÁUSULA SÉTIMA — DISPOSIÇÕES GERAIS

7.1 Este Contrato cancela e substitui qualquer acordo anterior firmado entre as PARTES, verbal ou escrito, referente ao mesmo objeto, obrigando as PARTES por si, seus herdeiros e sucessores.

7.2 Este Contrato poderá ser rescindido a qualquer tempo, por qualquer das PARTES, mediante notificação prévia e expressa com até 6 (seis) meses da efetiva rescisão. Toda e qualquer licença concedida durante a vigência, inclusive nos 6 (seis) meses seguintes à notificação, reputar-se-ão válidas e definitivas.

7.3 A EDITORA procederá trimestralmente, na conta bancária em nome do AUTOR indicada no cadastro da plataforma, à liquidação dos direitos eventualmente devidos ao AUTOR, mediante a transferência das receitas que lhe pertencem, acompanhada dos respectivos demonstrativos, mencionando a fonte pagadora, o período a que se refere o crédito, o título da OBRA e o valor de cada crédito, devendo efetuá-la dentro dos 60 (sessenta) dias posteriores ao fim de cada trimestre.

7.4 O AUTOR poderá, anualmente e em adição às prestações de contas descritas na Cláusula 7.3, requerer uma prestação de contas adicional, completa e consolidada referente ao exercício fiscal em curso.

7.5 O AUTOR assegura à EDITORA absoluta preferência, em igualdade de condições com propostas de terceiros, para a contratação de modalidades de exploração econômica da OBRA que, eventualmente, não tenham sido previstas neste Contrato, e para aquelas modalidades que venham a existir no futuro.

7.6 Este Contrato poderá ser cedido pela EDITORA a qualquer de suas associadas, coligadas ou filiadas, já existentes ou que venham a ser constituídas.

7.7 As PARTES elegem o foro da Comarca da Capital da Cidade do Rio de Janeiro, Estado do Rio de Janeiro, como único competente para dirimir eventuais controvérsias oriundas deste Contrato, com expressa renúncia a qualquer outro, por mais privilegiado que seja.

7.8 As PARTES declaram aceitar e reconhecer como válida, autêntica e verdadeira a comprovação da autoria e integridade deste documento realizada por meio eletrônico, nos termos da MP nº 2.200-2/2001, Lei nº 14.063/2020 e legislação correlata. A aceitação eletrônica do presente Contrato no ato do cadastro da OBRA na plataforma Gravan, com registro de data, hora, IP e hash SHA-256 do conteúdo, é considerada ASSINATURA VÁLIDA E VINCULANTE para todos os efeitos legais.

E, por estarem justas e acordadas, as PARTES firmam este instrumento eletronicamente na data abaixo:

Rio de Janeiro, {{data_assinatura}}.

___________________________________________
{{nome_completo}}
CPF: {{cpf}}
(AUTOR)

___________________________________________
{{plataforma_razao_social}}
CNPJ: {{plataforma_cnpj}}
(EDITORA)
"""

CONTRATO_VERSAO = "v2.0 - Fev/2026"

CONTRATO_EDITORA_DADOS = (
    "GRAVAN EDITORA MUSICAL LTDA., inscrita no CNPJ/MF sob o nº 64.342.514/0001-08, "
    "com sede na Cidade do Rio de Janeiro, Estado do Rio de Janeiro"
)

CONTRATO_FORO = "Comarca da Capital da Cidade do Rio de Janeiro, Estado do Rio de Janeiro"


def ensure_contract_seeded(sb=None):
    """Garante o template do Contrato de Edição em `landing_content`.

    Estratégia:
      - Se `contrato_edicao_versao` no banco é IGUAL a CONTRATO_VERSAO,
        assume que o admin editou/aprovou a versão atual → preserva tudo.
      - Se é DIFERENTE (ou ausente), faz upgrade forçado de template + versão
        + metadados. Isso garante que novas versões do texto cheguem ao modal
        que o usuário assina.
    - Tolerante a falhas: nada pode quebrar o startup.
    """
    try:
        if sb is None:
            from db.supabase_client import get_supabase
            sb = get_supabase()

        # Lê versão atual no banco
        versao_db = ""
        try:
            r = sb.table("landing_content").select("valor").eq("id", "contrato_edicao_versao").limit(1).execute()
            if r.data:
                versao_db = (r.data[0].get("valor") or "").strip()
        except Exception:
            pass

        # Já é a versão atual → nada a fazer
        if versao_db == CONTRATO_VERSAO:
            return

        seeds = {
            "contrato_edicao_template":      CONTRATO_TEMPLATE,
            "contrato_edicao_versao":        CONTRATO_VERSAO,
            "contrato_edicao_editora_dados": CONTRATO_EDITORA_DADOS,
            "contrato_edicao_foro":          CONTRATO_FORO,
        }
        for key, valor in seeds.items():
            try:
                sb.table("landing_content").upsert({"id": key, "valor": valor}).execute()
            except Exception:
                pass
    except Exception:
        pass
