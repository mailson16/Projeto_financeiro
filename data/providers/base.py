"""Interfaces abstratas de fontes de dados externas.

Permitem trocar/adicionar fontes (ex.: brapi.dev -> fundamentus.com.br como
fallback) sem alterar a camada de servicos, que so conhece essas interfaces.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from decimal import Decimal
from typing import List

from data.dto import CotacaoDTO, DadoComFonte, IndicadoresDTO, LucroLiquidoDTO


class FonteSelic(ABC):
    nome: str

    @abstractmethod
    def obter_selic_atual(self) -> DadoComFonte[Decimal]:
        """Retorna a taxa Selic atual como fracao (ex.: 0.14 para 14%)."""


class ProvedorFundamentalista(ABC):
    nome: str

    @abstractmethod
    def obter_cotacao(self, ticker: str) -> DadoComFonte[CotacaoDTO]: ...

    @abstractmethod
    def obter_lucro_liquido_historico(self, ticker: str) -> List[DadoComFonte[LucroLiquidoDTO]]: ...

    @abstractmethod
    def obter_indicadores(self, ticker: str) -> DadoComFonte[IndicadoresDTO]: ...
