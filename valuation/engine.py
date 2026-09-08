"""Motor puro de valuation por DCF ("Modo 2 - Nosso Valuation").

Este modulo nao depende de banco de dados, rede ou interface - apenas
`decimal` e `dataclasses`. Isso garante que a matematica do valuation
possa ser testada isoladamente (ver nosso_valuation_aprendizado.md,
secao 21: "o motor matematico sera construido e validado antes da
interface").

Todos os valores monetarios e taxas usam `Decimal`, nunca `float`, para
evitar erros de arredondamento acumulados entre etapas do calculo.
Arredondamento para exibicao (ex.: duas casas decimais em R$) deve
acontecer apenas na camada de apresentacao, nunca aqui.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

UM = Decimal("1")
ZERO = Decimal("0")


@dataclass(frozen=True)
class PremissasValuation:
    """Premissas editaveis de um valuation (secao 4 do doc)."""

    ll_ano_base: Decimal
    taxa_crescimento: Decimal
    taxa_desconto: Decimal
    crescimento_perpetuidade: Decimal
    anos_projecao: int
    numero_acoes: Decimal
    preco_atual: Optional[Decimal] = None
    margem_seguranca: Decimal = ZERO
    # None => usa a convencao padrao (N = anos_projecao). Ver constants.py.
    periodos_desconto_perpetuidade: Optional[Decimal] = None

    def __post_init__(self) -> None:
        if self.anos_projecao < 1:
            raise ValueError("anos_projecao deve ser >= 1")
        if self.numero_acoes <= 0:
            raise ValueError("numero_acoes deve ser maior que zero")
        if self.taxa_desconto <= self.crescimento_perpetuidade:
            raise ValueError(
                "taxa_desconto deve ser maior que crescimento_perpetuidade "
                "(caso contrario o Valor Terminal fica negativo ou indefinido)"
            )


@dataclass(frozen=True)
class ProjecaoAno:
    ano_index: int  # 1, 2, 3, ...
    lucro_liquido: Decimal
    vpl: Decimal


@dataclass(frozen=True)
class ResultadoValuation:
    premissas: PremissasValuation
    projecoes: tuple[ProjecaoAno, ...]
    valor_terminal: Decimal
    periodos_desconto_perpetuidade_usado: Decimal
    vpl_perpetuidade: Decimal
    valor_estimado: Decimal
    preco_justo: Decimal
    upside: Optional[Decimal]
    preco_entrada: Decimal


def projetar_lucro_liquido(ll_ano_base: Decimal, taxa_crescimento: Decimal, anos: int) -> tuple[Decimal, ...]:
    """Projeta o LL para `anos` anos, com o ano-base como o primeiro fluxo (n=1).

    Ver secoes 7 e 8 do doc: o LL do ano-base ja e o fluxo do primeiro ano
    projetado (ex.: LL 2026 e descontado com n=1 na secao 8) - o
    crescimento e aplicado para obter os anos seguintes:
    `LL futuro = LL anterior x (1 + taxa de crescimento)`.
    O resultado tem `anos` elementos: [LL_ano_base, LL_ano_base*(1+g), ...].
    """
    if anos < 1:
        raise ValueError("anos deve ser >= 1")
    fator = UM + taxa_crescimento
    projecoes = [ll_ano_base]
    for _ in range(anos - 1):
        projecoes.append(projecoes[-1] * fator)
    return tuple(projecoes)


def calcular_vpl(fluxo: Decimal, taxa_desconto: Decimal, periodo: Decimal) -> Decimal:
    """VPL = Fluxo Futuro / (1 + taxa de desconto) ** periodo (secao 8)."""
    fator_desconto = (UM + taxa_desconto) ** periodo
    return fluxo / fator_desconto


def calcular_valor_terminal(
    ll_final: Decimal, crescimento_perpetuidade: Decimal, taxa_desconto: Decimal
) -> Decimal:
    """Valor Terminal = LL final x (1 + g) / (taxa de desconto - g) (secao 9)."""
    if taxa_desconto <= crescimento_perpetuidade:
        raise ValueError("taxa_desconto deve ser maior que crescimento_perpetuidade")
    return ll_final * (UM + crescimento_perpetuidade) / (taxa_desconto - crescimento_perpetuidade)


def resolver_periodos_desconto_perpetuidade(premissas: PremissasValuation) -> Decimal:
    """Aplica a convencao padrao (N = anos_projecao) se nao houver override explicito.

    Ver valuation/constants.py para o racional dessa decisao de design.
    """
    if premissas.periodos_desconto_perpetuidade is not None:
        return premissas.periodos_desconto_perpetuidade
    return Decimal(premissas.anos_projecao)


def calcular_vpl_perpetuidade(valor_terminal: Decimal, taxa_desconto: Decimal, periodos: Decimal) -> Decimal:
    return calcular_vpl(valor_terminal, taxa_desconto, periodos)


def calcular_preco_justo(valor_estimado: Decimal, numero_acoes: Decimal) -> Decimal:
    """Preco justo = Valor estimado / numero de acoes (secao 10)."""
    if numero_acoes <= 0:
        raise ValueError("numero_acoes deve ser maior que zero")
    return valor_estimado / numero_acoes


def calcular_upside(preco_justo: Decimal, preco_atual: Decimal) -> Decimal:
    """Upside/Downside = (Preco justo / Preco atual) - 1 (secao 11)."""
    if preco_atual <= 0:
        raise ValueError("preco_atual deve ser maior que zero para calcular upside")
    return (preco_justo / preco_atual) - UM


def calcular_preco_entrada(preco_justo: Decimal, margem_seguranca: Decimal) -> Decimal:
    """Preco de entrada = Preco justo x (1 - margem de seguranca) (secao 13)."""
    return preco_justo * (UM - margem_seguranca)


def rodar_valuation(premissas: PremissasValuation) -> ResultadoValuation:
    """Orquestra o calculo completo do DCF a partir de um conjunto de premissas.

    Nao muta `premissas` (dataclass frozen) - seguro para rodar em serie
    para varios cenarios sem risco de estado compartilhado.
    """
    lls_projetados = projetar_lucro_liquido(
        premissas.ll_ano_base, premissas.taxa_crescimento, premissas.anos_projecao
    )

    projecoes = tuple(
        ProjecaoAno(
            ano_index=indice,
            lucro_liquido=ll,
            vpl=calcular_vpl(ll, premissas.taxa_desconto, Decimal(indice)),
        )
        for indice, ll in enumerate(lls_projetados, start=1)
    )

    ll_final = lls_projetados[-1]
    valor_terminal = calcular_valor_terminal(
        ll_final, premissas.crescimento_perpetuidade, premissas.taxa_desconto
    )

    periodos = resolver_periodos_desconto_perpetuidade(premissas)
    vpl_perpetuidade = calcular_vpl_perpetuidade(valor_terminal, premissas.taxa_desconto, periodos)

    soma_vpl_anos = sum((p.vpl for p in projecoes), ZERO)
    valor_estimado = soma_vpl_anos + vpl_perpetuidade

    preco_justo = calcular_preco_justo(valor_estimado, premissas.numero_acoes)

    upside = None
    if premissas.preco_atual is not None:
        upside = calcular_upside(preco_justo, premissas.preco_atual)

    preco_entrada = calcular_preco_entrada(preco_justo, premissas.margem_seguranca)

    return ResultadoValuation(
        premissas=premissas,
        projecoes=projecoes,
        valor_terminal=valor_terminal,
        periodos_desconto_perpetuidade_usado=periodos,
        vpl_perpetuidade=vpl_perpetuidade,
        valor_estimado=valor_estimado,
        preco_justo=preco_justo,
        upside=upside,
        preco_entrada=preco_entrada,
    )
