"""Cliente da API brapi.dev (dados fundamentalistas e cotacoes de acoes da B3).

Campos usados foram confirmados chamando a API publica ao vivo
(GET /api/quote/{ticker}?modules=defaultKeyStatistics,financialData,
incomeStatementHistory,balanceSheetHistory), sem token, em setembro/2026:

- preco atual: `regularMarketPrice` (nivel raiz)
- market cap: `marketCap` (nivel raiz)
- numero de acoes: `defaultKeyStatistics.sharesOutstanding`
- LL historico anual: `incomeStatementHistory[].netIncome` + `.endDate`
- ROE: `financialData.returnOnEquity`
- patrimonio liquido: `balanceSheetHistory[0].shareholdersEquity`
- LPA: `earningsPerShare` (nivel raiz)

O plano gratuito nao expoe payout diretamente - por enquanto o campo fica
None e pode ser preenchido manualmente pelo usuario na interface. Alguns
modulos podem exigir token/plano pago para tickers ou campos especificos;
por isso todo acesso a chave de dicionario e defensivo (`.get(...)`) e
falhas viram `DadosIncompletosError` com mensagem clara, nunca uma
excecao generica de KeyError.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, List, Optional

import requests

from data.dto import CotacaoDTO, DadoComFonte, IndicadoresDTO, LucroLiquidoDTO
from data.exceptions import DadosIncompletosError, FonteDadosIndisponivelError
from data.providers.base import ProvedorFundamentalista

BASE_URL = "https://brapi.dev/api/quote/{ticker}"
MODULOS = "defaultKeyStatistics,financialData,incomeStatementHistory,balanceSheetHistory"


def _decimal_ou_none(valor: Any) -> Optional[Decimal]:
    if valor is None:
        return None
    try:
        return Decimal(str(valor))
    except InvalidOperation:
        return None


class ClienteBrapi(ProvedorFundamentalista):
    nome = "brapi.dev"

    def __init__(
        self,
        token: Optional[str] = None,
        timeout_segundos: float = 15.0,
        session: Optional[requests.Session] = None,
    ):
        self._token = token
        self._timeout = timeout_segundos
        self._session = session or requests.Session()

    def _buscar(self, ticker: str) -> dict:
        params = {"modules": MODULOS}
        if self._token:
            params["token"] = self._token
        try:
            resposta = self._session.get(
                BASE_URL.format(ticker=ticker), params=params, timeout=self._timeout
            )
            resposta.raise_for_status()
            payload = resposta.json()
        except (requests.RequestException, ValueError) as exc:
            raise FonteDadosIndisponivelError(
                f"Falha ao consultar {ticker} na brapi.dev: {exc}"
            ) from exc

        resultados = payload.get("results") or []
        if not resultados:
            raise DadosIncompletosError(f"brapi.dev nao retornou dados para {ticker}")
        return resultados[0]

    def obter_cotacao(self, ticker: str) -> DadoComFonte[CotacaoDTO]:
        dados = self._buscar(ticker)
        preco = _decimal_ou_none(dados.get("regularMarketPrice"))
        if preco is None:
            raise DadosIncompletosError(f"brapi.dev nao trouxe preco para {ticker}")

        market_cap = _decimal_ou_none(dados.get("marketCap"))
        stats = dados.get("defaultKeyStatistics") or {}
        numero_acoes = _decimal_ou_none(stats.get("sharesOutstanding"))
        if numero_acoes is None and market_cap is not None and preco > 0:
            # Estimativa quando o modulo defaultKeyStatistics nao esta disponivel para o ticker.
            numero_acoes = market_cap / preco

        if numero_acoes is None:
            raise DadosIncompletosError(f"brapi.dev nao trouxe numero de acoes para {ticker}")

        cotacao = CotacaoDTO(ticker=ticker, preco=preco, numero_acoes=numero_acoes, market_cap=market_cap)
        return DadoComFonte(valor=cotacao, fonte=self.nome, data_atualizacao=datetime.now(timezone.utc))

    def obter_lucro_liquido_historico(self, ticker: str) -> List[DadoComFonte[LucroLiquidoDTO]]:
        dados = self._buscar(ticker)
        historico = dados.get("incomeStatementHistory") or []

        agora = datetime.now(timezone.utc)
        registros = []
        for item in historico:
            net_income = _decimal_ou_none(item.get("netIncome"))
            end_date = item.get("endDate")
            if net_income is None or not end_date:
                continue
            ano = int(str(end_date)[:4])
            ll_dto = LucroLiquidoDTO(ticker=ticker, ano=ano, lucro_liquido=net_income)
            registros.append(DadoComFonte(valor=ll_dto, fonte=self.nome, data_atualizacao=agora))

        if not registros:
            raise DadosIncompletosError(
                f"brapi.dev nao trouxe historico de lucro liquido valido para {ticker}"
            )
        return registros

    def obter_indicadores(self, ticker: str) -> DadoComFonte[IndicadoresDTO]:
        dados = self._buscar(ticker)
        financeiro = dados.get("financialData") or {}
        historico_balanco = dados.get("balanceSheetHistory") or [{}]
        balanco = historico_balanco[0] or {}

        indicadores = IndicadoresDTO(
            ticker=ticker,
            data=date.today(),
            payout=None,  # brapi.dev nao expoe payout no plano gratuito - editavel manualmente na UI.
            roe=_decimal_ou_none(financeiro.get("returnOnEquity")),
            patrimonio_liquido=_decimal_ou_none(balanco.get("shareholdersEquity")),
            lpa=_decimal_ou_none(dados.get("earningsPerShare")),
        )
        return DadoComFonte(valor=indicadores, fonte=self.nome, data_atualizacao=datetime.now(timezone.utc))

