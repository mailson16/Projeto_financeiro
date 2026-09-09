from decimal import Decimal

from valuation.engine import PremissasValuation, rodar_valuation
from valuation.sensitivity import matriz_sensibilidade

BASE = PremissasValuation(
    ll_ano_base=Decimal("100000000"),
    taxa_crescimento=Decimal("0.05"),
    taxa_desconto=Decimal("0.10"),
    crescimento_perpetuidade=Decimal("0.02"),
    anos_projecao=3,
    numero_acoes=Decimal("10000000"),
)


def test_matriz_sensibilidade_tem_shape_esperado():
    crescimentos = [Decimal("0.03"), Decimal("0.04"), Decimal("0.05")]
    descontos = [Decimal("0.09"), Decimal("0.10"), Decimal("0.11")]

    df = matriz_sensibilidade(BASE, crescimentos, descontos)

    assert list(df.index) == sorted(crescimentos)
    assert list(df.columns) == sorted(descontos)
    assert df.shape == (3, 3)


def test_matriz_sensibilidade_celula_bate_com_chamada_direta():
    crescimentos = [Decimal("0.03"), Decimal("0.05")]
    descontos = [Decimal("0.09"), Decimal("0.11")]

    df = matriz_sensibilidade(BASE, crescimentos, descontos)

    from dataclasses import replace

    premissas_celula = replace(BASE, taxa_crescimento=Decimal("0.05"), taxa_desconto=Decimal("0.11"))
    esperado = rodar_valuation(premissas_celula).preco_justo

    assert df.loc[Decimal("0.05"), Decimal("0.11")] == esperado


def test_matriz_sensibilidade_isola_celula_invalida_sem_abortar_a_matriz():
    """Uma combinacao com taxa_desconto <= crescimento_perpetuidade deve
    virar None so naquela celula - as demais celulas validas do range
    continuam sendo calculadas normalmente."""
    crescimentos = [Decimal("0.03"), Decimal("0.05")]
    descontos = [Decimal("0.01"), Decimal("0.10")]  # 0.01 <= perpetuidade da BASE (0.02)

    df = matriz_sensibilidade(BASE, crescimentos, descontos)

    assert df.loc[Decimal("0.03"), Decimal("0.01")] is None
    assert df.loc[Decimal("0.05"), Decimal("0.01")] is None
    assert df.loc[Decimal("0.03"), Decimal("0.10")] is not None
    assert df.loc[Decimal("0.05"), Decimal("0.10")] is not None


def test_matriz_sensibilidade_usa_perpetuidade_fixa_da_base_por_padrao():
    crescimentos = [Decimal("0.03")]
    descontos = [Decimal("0.09")]

    df = matriz_sensibilidade(BASE, crescimentos, descontos)

    from dataclasses import replace

    esperado = rodar_valuation(
        replace(BASE, taxa_crescimento=Decimal("0.03"), taxa_desconto=Decimal("0.09"))
    ).preco_justo
    assert df.loc[Decimal("0.03"), Decimal("0.09")] == esperado
