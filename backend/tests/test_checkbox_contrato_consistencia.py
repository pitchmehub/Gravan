"""
Garante que o resumo do checkbox de concordância em frontend/src/pages/Comprar.jsx
não diverge das cláusulas reais dos templates de contrato em
backend/services/contrato_licenciamento.py (TEMPLATE_LICENCIAMENTO bilateral
e TEMPLATE_TRILATERAL).

Quando alguém alterar uma das pontas sem alterar a outra, este teste falha e
mostra exatamente qual condição ficou desalinhada — evitando que o comprador
"assine concordando" com algo que o contrato não diz.

Run: pytest backend/tests/test_checkbox_contrato_consistencia.py -v
"""
import os
import re

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CHECKBOX_FILE = os.path.join(ROOT, "frontend", "src", "pages", "Comprar.jsx")
CONTRATO_FILE = os.path.join(
    ROOT, "backend", "services", "contrato_licenciamento.py"
)


@pytest.fixture(scope="module")
def checkbox_text() -> str:
    with open(CHECKBOX_FILE, encoding="utf-8") as fh:
        src = fh.read()
    # Bloco do <span> que contém o resumo, entre o testid do checkbox e o
    # botão "Ver texto completo do contrato".
    m = re.search(
        r"checkbox-contrato-licenciamento.*?Ver texto completo do contrato",
        src,
        flags=re.DOTALL,
    )
    assert m, "Bloco do checkbox de concordância não encontrado em Comprar.jsx"
    # Colapsa whitespace (incluindo quebras de linha do JSX) para que frases
    # quebradas no código continuem batendo com o texto renderizado.
    return re.sub(r"\s+", " ", m.group(0))


@pytest.fixture(scope="module")
def contrato_text() -> str:
    with open(CONTRATO_FILE, encoding="utf-8") as fh:
        return fh.read()


class TestCheckboxBateComContrato:
    def test_titulo_do_contrato(self, checkbox_text, contrato_text):
        titulo = "Contrato de Autorização para Gravação e Exploração de Obra Musical"
        assert titulo in checkbox_text, (
            "Checkbox não cita o título oficial do contrato."
        )
        assert "CONTRATO DE AUTORIZAÇÃO PARA GRAVAÇÃO E EXPLORAÇÃO DE OBRA MUSICAL" \
            in contrato_text, (
                "Template do contrato não tem o título esperado — checkbox precisa "
                "ser atualizado para o novo título."
            )

    def test_vigencia_5_anos(self, checkbox_text, contrato_text):
        assert "vigência 5 anos" in checkbox_text, (
            "Checkbox não menciona vigência de 5 anos."
        )
        assert "validade de 5 (cinco) anos" in contrato_text, (
            "Contrato não tem mais vigência de 5 anos — atualize o checkbox."
        )

    def test_renovacao_automatica_nao_exclusivo(self, checkbox_text, contrato_text):
        assert "renovação automática" in checkbox_text, (
            "Checkbox não menciona renovação automática para licença não exclusiva."
        )
        assert "renovação automática por igual período" in contrato_text, (
            "Contrato não prevê mais renovação automática — atualize o checkbox."
        )

    def test_rescisao_30_dias(self, checkbox_text, contrato_text):
        assert "30 dias" in checkbox_text, (
            "Checkbox não cita o prazo de rescisão de 30 dias."
        )
        assert "30 (trinta) dias" in contrato_text, (
            "Contrato não cita mais 30 dias para rescisão — atualize o checkbox."
        )

    def test_renovacao_exclusivo_por_novo_acordo(self, checkbox_text, contrato_text):
        assert "novo acordo" in checkbox_text, (
            "Checkbox não diz que renovação da exclusiva depende de novo acordo."
        )
        assert "renovação dependerá de novo acordo formal" in contrato_text, (
            "Contrato mudou a regra de renovação da exclusiva — atualize o checkbox."
        )

    def test_fee_5_pct_exploracao(self, checkbox_text, contrato_text):
        assert "5%" in checkbox_text and "exploração comercial" in checkbox_text, (
            "Checkbox não cita o fee de 5% sobre exploração comercial."
        )
        # O fee de 5% sobre exploração comercial aparece na 6.3 (bilateral) e
        # na 5 (trilateral). Garantimos que pelo menos um continua no template.
        assert "5% (cinco por cento) do valor bruto" in contrato_text, (
            "Cláusula do fee de 5% sobre exploração comercial sumiu do contrato — "
            "remova / atualize o checkbox."
        )
        assert "exploração comercial" in contrato_text

    def test_territorio_mundial(self, checkbox_text, contrato_text):
        assert "território mundial" in checkbox_text, (
            "Checkbox não diz território mundial."
        )
        assert "caráter mundial" in contrato_text, (
            "Contrato não é mais mundial — atualize o checkbox."
        )

    def test_foro_rio_de_janeiro(self, checkbox_text, contrato_text):
        assert "foro Rio de Janeiro/RJ" in checkbox_text, (
            "Checkbox não cita o foro Rio de Janeiro/RJ."
        )
        assert "foro da comarca da cidade do Rio de Janeiro/RJ" in contrato_text, (
            "Contrato mudou o foro — atualize o checkbox."
        )

    def test_assinatura_eletronica_leis(self, checkbox_text, contrato_text):
        for token in ("MP 2.200-2/2001", "Lei 14.063/2020"):
            assert token in checkbox_text, (
                f"Checkbox não cita {token} — base legal da assinatura eletrônica."
            )
            assert token in contrato_text or token.replace("Lei ", "Lei nº ") \
                in contrato_text, (
                    f"Contrato não cita mais {token} — atualize o checkbox."
                )

    def test_nao_promete_split_ecad_que_contrato_nao_tem(self, checkbox_text):
        # Aprendizado da regressão de abr/2026: o checkbox prometia
        # "ECAD 85/10/5" e isso não estava em nenhum template. Se voltar a
        # aparecer sem ter sido inserido no contrato, o teste falha.
        assert "85/10/5" not in checkbox_text, (
            "Checkbox voltou a prometer split ECAD 85/10/5, mas os templates de "
            "contrato em backend/services/contrato_licenciamento.py não preveem "
            "essa divisão. Insira a cláusula no contrato OU remova do checkbox."
        )
