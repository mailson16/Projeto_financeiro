from decimal import Decimal

from app.components.formatting import fmt_brl_abreviado


def test_fmt_brl_abreviado_milhoes():
    assert fmt_brl_abreviado(Decimal("175073000.00")) == "R$ 175,07 milhões"


def test_fmt_brl_abreviado_bilhoes():
    assert fmt_brl_abreviado(Decimal("1851000000")) == "R$ 1,85 bilhões"


def test_fmt_brl_abreviado_mil():
    assert fmt_brl_abreviado(Decimal("182321.02")) == "R$ 182,32 mil"


def test_fmt_brl_abreviado_abaixo_de_mil_usa_formato_normal():
    assert fmt_brl_abreviado(Decimal("999.99")) == "R$ 999,99"


def test_fmt_brl_abreviado_singular_exato():
    assert fmt_brl_abreviado(Decimal("1000000")) == "R$ 1,00 milhão"
    assert fmt_brl_abreviado(Decimal("1000000000")) == "R$ 1,00 bilhão"


def test_fmt_brl_abreviado_negativo():
    assert fmt_brl_abreviado(Decimal("-193670000")) == "R$ -193,67 milhões"


def test_fmt_brl_abreviado_none():
    assert fmt_brl_abreviado(None) == "-"
