"""Cenarios conservador/base/otimista (secao 12 do doc).

Cada cenario e imutavel e gera sua propria `PremissasValuation` via
`dataclasses.replace` a partir de uma base comum - nunca muta a base nem
compartilha estado entre cenarios.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal

from valuation.engine import PremissasValuation, ResultadoValuation, rodar_valuation


@dataclass(frozen=True)
class Cenario:
    nome: str
    taxa_crescimento: Decimal
    taxa_desconto: Decimal
    crescimento_perpetuidade: Decimal


# Valores de referencia iniciais da secao 12 - nao sao parametros definitivos,
# podem ser ajustados por ativo/usuario.
CENARIOS_PADRAO: tuple[Cenario, ...] = (
    Cenario("conservador", Decimal("0.025"), Decimal("0.15"), Decimal("0.025")),
    Cenario("base", Decimal("0.041"), Decimal("0.14"), Decimal("0.03")),
    Cenario("otimista", Decimal("0.07"), Decimal("0.13"), Decimal("0.035")),
)


def montar_premissas_cenario(base: PremissasValuation, cenario: Cenario) -> PremissasValuation:
    """Retorna uma nova PremissasValuation com o trio do cenario aplicado.

    Nunca muta `base`: `dataclasses.replace` sempre cria uma instancia nova.
    """
    return replace(
        base,
        taxa_crescimento=cenario.taxa_crescimento,
        taxa_desconto=cenario.taxa_desconto,
        crescimento_perpetuidade=cenario.crescimento_perpetuidade,
    )


def rodar_cenarios(
    base: PremissasValuation, cenarios: tuple[Cenario, ...] = CENARIOS_PADRAO
) -> dict[str, ResultadoValuation]:
    """Roda o valuation para cada cenario isoladamente.

    Cada chamada a `rodar_valuation` recebe sua propria `PremissasValuation`
    imutavel - nenhum estado e compartilhado entre cenarios, mesmo que
    todos derivem da mesma `base`.
    """
    return {
        cenario.nome: rodar_valuation(montar_premissas_cenario(base, cenario))
        for cenario in cenarios
    }
