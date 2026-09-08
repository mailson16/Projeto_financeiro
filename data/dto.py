"""DTOs genericos para dados vindos de fontes externas.

Todo dado que entra no sistema carrega proveniencia (`fonte` +
`data_atualizacao`) - nunca e persistido "anonimo" (ver secao 18 do doc:
"registro da fonte e da data de atualizacao").
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Generic, Optional, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class DadoComFonte(Generic[T]):
    valor: T
    fonte: str
    data_atualizacao: datetime


@dataclass(frozen=True)
class CotacaoDTO:
    ticker: str
    preco: Decimal
    numero_acoes: Decimal
    market_cap: Optional[Decimal] = None


@dataclass(frozen=True)
class LucroLiquidoDTO:
    ticker: str
    ano: int
    lucro_liquido: Decimal
    trimestre: Optional[int] = None  # None = anual
    tipo_metrica: str = "contabil"  # "contabil" | "regulatoria"


@dataclass(frozen=True)
class IndicadoresDTO:
    ticker: str
    data: date
    payout: Optional[Decimal] = None
    roe: Optional[Decimal] = None
    patrimonio_liquido: Optional[Decimal] = None
    lpa: Optional[Decimal] = None
