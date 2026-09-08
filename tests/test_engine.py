"""Testes do motor puro de DCF, validados contra nosso_valuation_aprendizado.md.

Nota importante sobre a convencao de desconto da perpetuidade (secao 9 do doc):
Ao reproduzir manualmente a matematica dos exemplos de BRBI11/TAEE4 (secao 19),
descobrimos que o "VPL da Perpetuidade" final publicado no doc so bate se o
Valor Terminal for descontado por um numero FRACIONARIO de periodos (~2.18),
nao pelos N=3 anos inteiros de projecao. Isso e exatamente a convencao da
Ward que a secao 9 diz explicitamente que o Nosso Valuation NAO deve copiar
implicitamente.

Por isso, os testes abaixo sao divididos em dois grupos:
1. Testes que DEVEM bater com o doc: projecao de LL, VPL de cada ano
   projetado e Valor Terminal bruto (essas partes usam formulas padrao,
   sem a influencia da convencao da Ward).
2. Golden tests do RESULTADO FINAL (VPL da perpetuidade, valor estimado,
   preco justo, upside) usando a convencao padrao adotada pelo sistema
   (N periodos inteiros) - os valores esperados foram calculados pela
   propria formula (nao copiados do doc) e DIVERGEM intencionalmente dos
   numeros finais da secao 19. Um teste de referencia, separado e rotulado,
   mostra que informar `periodos_desconto_perpetuidade` explicitamente
   permite reproduzir a ordem de grandeza dos numeros do doc, apenas para
   registro historico da origem da convencao Ward.
"""

from decimal import Decimal

import pytest

from tests.fixtures import dados_doc as doc
from valuation.engine import (
    PremissasValuation,
    calcular_preco_entrada,
    calcular_valor_terminal,
    calcular_vpl,
    projetar_lucro_liquido,
    resolver_periodos_desconto_perpetuidade,
    rodar_valuation,
)

CENTAVO = Decimal("0.01")


def _proximo(a: Decimal, b: Decimal, tolerancia: Decimal = CENTAVO) -> bool:
    return abs(a - b) <= tolerancia


# --- 1. Projecao de Lucro Liquido (secao 7) ---


def test_projecao_ll_brbi11_bate_com_doc():
    projetado = projetar_lucro_liquido(
        doc.BRBI11_LL_ANO_BASE, doc.BRBI11_TAXA_CRESCIMENTO, doc.BRBI11_ANOS_PROJECAO
    )
    for calculado, esperado in zip(projetado, doc.BRBI11_LL_PROJETADO_ESPERADO):
        assert _proximo(calculado, esperado), f"{calculado} != {esperado}"


def test_projecao_ll_taee4_bate_com_doc():
    projetado = projetar_lucro_liquido(
        doc.TAEE4_LL_ANO_BASE, doc.TAEE4_TAXA_CRESCIMENTO, doc.TAEE4_ANOS_PROJECAO
    )
    for calculado, esperado in zip(projetado, doc.TAEE4_LL_PROJETADO_ESPERADO):
        assert _proximo(calculado, esperado), f"{calculado} != {esperado}"


# --- 2. VPL de cada ano projetado (secao 8) ---


def test_vpl_por_ano_brbi11_bate_com_doc():
    for indice, (ll, esperado) in enumerate(
        zip(doc.BRBI11_LL_PROJETADO_ESPERADO, doc.BRBI11_VPL_ANO_ESPERADO), start=1
    ):
        vpl = calcular_vpl(ll, doc.BRBI11_TAXA_DESCONTO, Decimal(indice))
        assert _proximo(vpl, esperado), f"ano {indice}: {vpl} != {esperado}"


def test_vpl_por_ano_taee4_bate_com_doc():
    # Os dois primeiros anos batem exatamente. O terceiro (VPL 2028) tem uma
    # divergencia de ~R$ 2.700 em relacao ao doc (1.275.817.405,57) que nao se
    # sustenta reproduzindo a formula com o LL 2028 do proprio doc - tudo
    # indica uma transcricao incorreta na secao 19 (o valor correto pela
    # formula e ~1.275.814.705,57). Usamos tolerancia maior so nesse caso,
    # documentando a divergencia em vez de escondê-la.
    tolerancias = (CENTAVO, CENTAVO, Decimal("3000"))
    for indice, (ll, esperado, tolerancia) in enumerate(
        zip(doc.TAEE4_LL_PROJETADO_ESPERADO, doc.TAEE4_VPL_ANO_ESPERADO, tolerancias), start=1
    ):
        vpl = calcular_vpl(ll, doc.TAEE4_TAXA_DESCONTO, Decimal(indice))
        assert _proximo(vpl, esperado, tolerancia), f"ano {indice}: {vpl} != {esperado}"


# --- 3. Valor Terminal bruto (secao 9) ---


def test_valor_terminal_brbi11_bate_com_doc():
    ll_final = doc.BRBI11_LL_PROJETADO_ESPERADO[-1]
    vt = calcular_valor_terminal(ll_final, doc.BRBI11_CRESCIMENTO_PERPETUIDADE, doc.BRBI11_TAXA_DESCONTO)
    # Doc arredonda para "~R$ 1,851 bilhao" (3 casas decimais em bilhoes) - tolerancia de 1 milhao.
    assert _proximo(vt, doc.BRBI11_VALOR_TERMINAL_ESPERADO, Decimal("1000000"))


def test_valor_terminal_taee4_bate_com_doc():
    ll_final = doc.TAEE4_LL_PROJETADO_ESPERADO[-1]
    vt = calcular_valor_terminal(ll_final, doc.TAEE4_CRESCIMENTO_PERPETUIDADE, doc.TAEE4_TAXA_DESCONTO)
    # Diferenca de ~1 centavo por arredondamento intermediario no doc.
    assert _proximo(vt, doc.TAEE4_VALOR_TERMINAL_ESPERADO, Decimal("0.05"))


# --- 4. Convencao de periodos de desconto da perpetuidade (secao 9 - decisao de design) ---


def test_convencao_padrao_usa_anos_projecao_quando_nao_informado():
    premissas = PremissasValuation(
        ll_ano_base=doc.BRBI11_LL_ANO_BASE,
        taxa_crescimento=doc.BRBI11_TAXA_CRESCIMENTO,
        taxa_desconto=doc.BRBI11_TAXA_DESCONTO,
        crescimento_perpetuidade=doc.BRBI11_CRESCIMENTO_PERPETUIDADE,
        anos_projecao=doc.BRBI11_ANOS_PROJECAO,
        numero_acoes=doc.BRBI11_NUMERO_ACOES,
    )
    assert resolver_periodos_desconto_perpetuidade(premissas) == Decimal(doc.BRBI11_ANOS_PROJECAO)


def test_periodos_desconto_perpetuidade_pode_ser_sobrescrito_explicitamente():
    premissas = PremissasValuation(
        ll_ano_base=doc.BRBI11_LL_ANO_BASE,
        taxa_crescimento=doc.BRBI11_TAXA_CRESCIMENTO,
        taxa_desconto=doc.BRBI11_TAXA_DESCONTO,
        crescimento_perpetuidade=doc.BRBI11_CRESCIMENTO_PERPETUIDADE,
        anos_projecao=doc.BRBI11_ANOS_PROJECAO,
        numero_acoes=doc.BRBI11_NUMERO_ACOES,
        periodos_desconto_perpetuidade=Decimal("2.18"),
    )
    assert resolver_periodos_desconto_perpetuidade(premissas) == Decimal("2.18")


# --- 5. Golden tests do resultado final (convencao padrao do sistema, N inteiro) ---
# Valores calculados pela propria implementacao (nao copiados do doc) - ver nota no topo do arquivo.


def test_rodar_valuation_brbi11_convencao_padrao():
    premissas = PremissasValuation(
        ll_ano_base=doc.BRBI11_LL_ANO_BASE,
        taxa_crescimento=doc.BRBI11_TAXA_CRESCIMENTO,
        taxa_desconto=doc.BRBI11_TAXA_DESCONTO,
        crescimento_perpetuidade=doc.BRBI11_CRESCIMENTO_PERPETUIDADE,
        anos_projecao=doc.BRBI11_ANOS_PROJECAO,
        numero_acoes=doc.BRBI11_NUMERO_ACOES,
        preco_atual=doc.BRBI11_PRECO_ATUAL,
    )
    resultado = rodar_valuation(premissas)

    assert resultado.periodos_desconto_perpetuidade_usado == Decimal(3)
    assert _proximo(resultado.preco_justo, Decimal("5.3626941858"), Decimal("0.01"))
    assert _proximo(resultado.upside, Decimal("-0.5685684484"), Decimal("0.0001"))
    # Diverge de proposito dos numeros finais do doc (preco justo R$17,43 / upside 40,26%),
    # que foram gerados com a convencao fracionaria da Ward - ver nota no topo do arquivo.
    assert not _proximo(resultado.preco_justo, doc.BRBI11_PRECO_JUSTO_DOC, Decimal("1"))


def test_rodar_valuation_taee4_convencao_padrao():
    premissas = PremissasValuation(
        ll_ano_base=doc.TAEE4_LL_ANO_BASE,
        taxa_crescimento=doc.TAEE4_TAXA_CRESCIMENTO,
        taxa_desconto=doc.TAEE4_TAXA_DESCONTO,
        crescimento_perpetuidade=doc.TAEE4_CRESCIMENTO_PERPETUIDADE,
        anos_projecao=doc.TAEE4_ANOS_PROJECAO,
        numero_acoes=doc.TAEE4_NUMERO_ACOES,
        preco_atual=doc.TAEE4_PRECO_ATUAL,
    )
    resultado = rodar_valuation(premissas)

    assert resultado.periodos_desconto_perpetuidade_usado == Decimal(3)
    assert _proximo(resultado.preco_justo, Decimal("15.5426976721"), Decimal("0.01"))
    assert _proximo(resultado.upside, Decimal("0.2190351115"), Decimal("0.0001"))
    assert not _proximo(resultado.preco_justo, doc.TAEE4_PRECO_JUSTO_DOC, Decimal("1"))


def test_referencia_convencao_ward_reproduz_ordem_de_grandeza_do_doc():
    """Teste de referencia/historico (nao normativo): mostra que informar
    explicitamente um numero fracionario de periodos aproxima o resultado
    dos numeros publicados no doc (que usaram a convencao da Ward). Isso NAO
    e o comportamento padrao do sistema - serve apenas para documentar a
    origem da divergencia."""
    premissas = PremissasValuation(
        ll_ano_base=doc.TAEE4_LL_ANO_BASE,
        taxa_crescimento=doc.TAEE4_TAXA_CRESCIMENTO,
        taxa_desconto=doc.TAEE4_TAXA_DESCONTO,
        crescimento_perpetuidade=doc.TAEE4_CRESCIMENTO_PERPETUIDADE,
        anos_projecao=doc.TAEE4_ANOS_PROJECAO,
        numero_acoes=doc.TAEE4_NUMERO_ACOES,
        preco_atual=doc.TAEE4_PRECO_ATUAL,
        periodos_desconto_perpetuidade=Decimal("2.18"),
    )
    resultado = rodar_valuation(premissas)
    # Tolerancia larga (R$ 0,50): so demonstra ordem de grandeza, nao precisao.
    assert _proximo(resultado.preco_justo, doc.TAEE4_PRECO_JUSTO_DOC, Decimal("0.5"))


# --- 6. Validacoes de dominio ---


def test_taxa_desconto_menor_ou_igual_a_perpetuidade_levanta_erro():
    with pytest.raises(ValueError):
        PremissasValuation(
            ll_ano_base=Decimal("100"),
            taxa_crescimento=Decimal("0.05"),
            taxa_desconto=Decimal("0.03"),
            crescimento_perpetuidade=Decimal("0.03"),
            anos_projecao=3,
            numero_acoes=Decimal("10"),
        )


def test_numero_acoes_zero_ou_negativo_levanta_erro():
    with pytest.raises(ValueError):
        PremissasValuation(
            ll_ano_base=Decimal("100"),
            taxa_crescimento=Decimal("0.05"),
            taxa_desconto=Decimal("0.14"),
            crescimento_perpetuidade=Decimal("0.03"),
            anos_projecao=3,
            numero_acoes=Decimal("0"),
        )


def test_margem_seguranca_exemplo_secao_13():
    preco_entrada = calcular_preco_entrada(Decimal("20.00"), Decimal("0.20"))
    assert preco_entrada == Decimal("16.00")
