from decimal import Decimal

from valuation.engine import PremissasValuation, rodar_valuation
from valuation.scenarios import CENARIOS_PADRAO, montar_premissas_cenario, rodar_cenarios

BASE = PremissasValuation(
    ll_ano_base=Decimal("100000000"),
    taxa_crescimento=Decimal("0.05"),
    taxa_desconto=Decimal("0.10"),
    crescimento_perpetuidade=Decimal("0.02"),
    anos_projecao=3,
    numero_acoes=Decimal("10000000"),
    preco_atual=Decimal("10.00"),
)


def test_cenarios_padrao_tem_conservador_base_otimista():
    nomes = {c.nome for c in CENARIOS_PADRAO}
    assert nomes == {"conservador", "base", "otimista"}


def test_montar_premissas_cenario_nao_muta_base():
    cenario = CENARIOS_PADRAO[0]
    premissas_cenario = montar_premissas_cenario(BASE, cenario)

    assert BASE.taxa_crescimento == Decimal("0.05")
    assert BASE.taxa_desconto == Decimal("0.10")
    assert BASE.crescimento_perpetuidade == Decimal("0.02")

    assert premissas_cenario.taxa_crescimento == cenario.taxa_crescimento
    assert premissas_cenario.taxa_desconto == cenario.taxa_desconto
    assert premissas_cenario.crescimento_perpetuidade == cenario.crescimento_perpetuidade
    assert premissas_cenario.ll_ano_base == BASE.ll_ano_base


def test_cenarios_nao_compartilham_estado_entre_si():
    resultados = rodar_cenarios(BASE)

    resultado_conservador_antes = resultados["conservador"]
    resultado_otimista = resultados["otimista"]

    # Rodar o cenario otimista de novo nao pode ter alterado o resultado
    # ja calculado do conservador (nenhuma mutacao compartilhada).
    resultado_conservador_depois = rodar_valuation(
        montar_premissas_cenario(BASE, CENARIOS_PADRAO[0])
    )
    assert resultado_conservador_antes.preco_justo == resultado_conservador_depois.preco_justo
    assert resultado_conservador_antes.premissas.taxa_crescimento != resultado_otimista.premissas.taxa_crescimento


def test_cenario_otimista_gera_preco_justo_maior_que_conservador():
    resultados = rodar_cenarios(BASE)
    assert resultados["otimista"].preco_justo > resultados["base"].preco_justo > resultados["conservador"].preco_justo
