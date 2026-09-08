"""Cliente do statusinvest.com.br (scraping) - alternativa ao brapi.dev que
nao exige token.

O brapi.dev retorna 401 para tickers de menor liquidez (BRBI11, TAEE4, etc.)
sem um BRAPI_TOKEN pago (ver README.md). O statusinvest.com.br expoe os
mesmos campos publicamente, sem autenticacao - so bloqueia clientes HTTP com
fingerprint TLS "nao humano": testado ao vivo em setembro/2026, o mesmo
request falha com 403 via WebFetch/.NET HttpClient mas funciona normalmente
com `requests`/curl puro usando um User-Agent de navegador comum.

Endpoints confirmados ao vivo (BRBI11 e TAEE4, validados contra os numeros
da secao 6/19 do doc - bateram exatamente para LL historico e ROE):

- HTML da pagina do ativo: GET /acoes/{ticker}
  - preco atual: `<div title="Valor atual do ativo">` -> `<strong class="value">`
  - numero de acoes: `<h3>` cujo texto contem "total de papeis" -> `<strong class="value">`
    no mesmo container
  - market cap: `<a href=".../termos/v/valor-de-mercado">` -> `<strong class="value">`
    no container pai do link
  - patrimonio liquido: `<a href=".../termos/p/patrimonio-liquido">` -> mesmo padrao
- ROE e LPA (indicadores atuais): POST /acao/indicatorhistorical
  (form `ticker=<ticker>&time=5`) -> `{"data": [{"key": "roe", "actual": 19.70, ...}]}`
  `actual` vem em escala percentual (19.70 = 19,70%); dividimos por 100 para
  bater com a convencao de fracao usada no resto do sistema.
- payout atual e Lucro Liquido historico anual: GET /acao/payoutresult
  (query `code=<ticker>&type=1`, type=1 = "10 anos") ->
  `{"actual": 77.88, "chart": {"category": [anos...], "series": {
  "lucroLiquido": [{"value": ...}, ...], "percentual": [...] }}}`
  Esta e a fonte mais confiavel de LL historico anual do site: os valores de
  `lucroLiquido` bateram exatamente com os historicos de BRBI11 e TAEE4
  documentados na secao 6 do doc.

O ultimo item da serie historica costuma ser o ano corrente com LL parcial
(YTD, nao um ano fechado) - o valor e retornado tal como veio; quem consome
`obter_lucro_liquido_historico` deve tratar o ano mais recente como possivel
dado parcial, nao assumir que e sempre um ano fiscal completo.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, List, Optional

import requests
from bs4 import BeautifulSoup, Tag

from data.dto import CotacaoDTO, DadoComFonte, IndicadoresDTO, LucroLiquidoDTO
from data.exceptions import DadosIncompletosError, FonteDadosIndisponivelError
from data.providers.base import ProvedorFundamentalista

URL_PAGINA_ATIVO = "https://statusinvest.com.br/acoes/{ticker}"
URL_INDICATOR_HISTORICAL = "https://statusinvest.com.br/acao/indicatorhistorical"
URL_PAYOUT_RESULT = "https://statusinvest.com.br/acao/payoutresult"

CEM = Decimal("100")

_HEADERS_BASE = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9",
}
_HEADERS_AJAX = {**_HEADERS_BASE, "X-Requested-With": "XMLHttpRequest"}


def _decimal_ou_none(valor: Any) -> Optional[Decimal]:
    if valor is None:
        return None
    try:
        return Decimal(str(valor))
    except InvalidOperation:
        return None


def _numero_br_para_decimal(texto: str) -> Optional[Decimal]:
    """Converte numeros no formato BR ("1.234.567,89") para Decimal."""
    texto = texto.strip()
    if not texto or texto in {"-", "N/A", "\xa0"}:
        return None
    return _decimal_ou_none(texto.replace(".", "").replace(",", "."))


class ClienteStatusInvest(ProvedorFundamentalista):
    nome = "statusinvest.com.br"

    def __init__(
        self,
        timeout_segundos: float = 15.0,
        session: Optional[requests.Session] = None,
    ):
        self._timeout = timeout_segundos
        self._session = session or requests.Session()

    def _get(self, url: str, *, ajax: bool = False, **kwargs) -> requests.Response:
        headers = _HEADERS_AJAX if ajax else _HEADERS_BASE
        try:
            resposta = self._session.get(url, headers=headers, timeout=self._timeout, **kwargs)
            resposta.raise_for_status()
        except requests.RequestException as exc:
            raise FonteDadosIndisponivelError(
                f"Falha ao consultar {url} no statusinvest.com.br: {exc}"
            ) from exc
        return resposta

    def _post(self, url: str, data: dict) -> requests.Response:
        headers = {**_HEADERS_AJAX, "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}
        try:
            resposta = self._session.post(url, data=data, headers=headers, timeout=self._timeout)
            resposta.raise_for_status()
        except requests.RequestException as exc:
            raise FonteDadosIndisponivelError(
                f"Falha ao consultar {url} no statusinvest.com.br: {exc}"
            ) from exc
        return resposta

    def _json(self, resposta: requests.Response) -> dict:
        try:
            return resposta.json()
        except ValueError as exc:
            raise FonteDadosIndisponivelError(
                f"statusinvest.com.br nao retornou JSON valido: {exc}"
            ) from exc

    def _pagina_ativo(self, ticker: str) -> BeautifulSoup:
        resposta = self._get(URL_PAGINA_ATIVO.format(ticker=ticker.lower()))
        return BeautifulSoup(resposta.text, "html.parser")

    @staticmethod
    def _valor_no_container(container: Optional[Tag]) -> Optional[Decimal]:
        if container is None:
            return None
        valor = container.find("strong", class_="value")
        if valor is None:
            return None
        return _numero_br_para_decimal(valor.get_text())

    def _valor_por_titulo(self, soup: BeautifulSoup, titulo: str) -> Optional[Decimal]:
        return self._valor_no_container(soup.find("div", title=titulo))

    def _valor_por_href_termo(self, soup: BeautifulSoup, slug_termo: str) -> Optional[Decimal]:
        link = soup.find("a", href=lambda h: bool(h) and f"/termos/{slug_termo}" in h)
        if link is None:
            return None
        return self._valor_no_container(link.find_parent("div"))

    def _numero_acoes(self, soup: BeautifulSoup) -> Optional[Decimal]:
        for h3 in soup.find_all("h3", class_="title"):
            if "total de pap" in h3.get_text(strip=True).lower():
                return self._valor_no_container(h3.find_parent("div"))
        return None

    def obter_cotacao(self, ticker: str) -> DadoComFonte[CotacaoDTO]:
        soup = self._pagina_ativo(ticker)
        preco = self._valor_por_titulo(soup, "Valor atual do ativo")
        if preco is None:
            raise DadosIncompletosError(f"statusinvest.com.br nao trouxe preco para {ticker}")

        market_cap = self._valor_por_href_termo(soup, "v/valor-de-mercado")
        numero_acoes = self._numero_acoes(soup)
        if numero_acoes is None and market_cap is not None and preco > 0:
            # Fallback quando o card "Nº total de papéis" nao esta presente na pagina.
            numero_acoes = market_cap / preco

        if numero_acoes is None:
            raise DadosIncompletosError(f"statusinvest.com.br nao trouxe numero de acoes para {ticker}")

        cotacao = CotacaoDTO(ticker=ticker, preco=preco, numero_acoes=numero_acoes, market_cap=market_cap)
        return DadoComFonte(valor=cotacao, fonte=self.nome, data_atualizacao=datetime.now(timezone.utc))

    def obter_indicadores(self, ticker: str) -> DadoComFonte[IndicadoresDTO]:
        soup = self._pagina_ativo(ticker)
        patrimonio_liquido = self._valor_por_href_termo(soup, "p/patrimonio-liquido")

        indicadores_historicos = self._indicadores_historicos(ticker)
        roe = self._indicador_atual(indicadores_historicos, "roe")
        if roe is not None:
            roe = roe / CEM
        lpa = self._indicador_atual(indicadores_historicos, "lpa")

        payout = self._payout_atual(ticker)

        indicadores = IndicadoresDTO(
            ticker=ticker,
            data=date.today(),
            payout=payout,
            roe=roe,
            patrimonio_liquido=patrimonio_liquido,
            lpa=lpa,
        )
        return DadoComFonte(valor=indicadores, fonte=self.nome, data_atualizacao=datetime.now(timezone.utc))

    def obter_lucro_liquido_historico(self, ticker: str) -> List[DadoComFonte[LucroLiquidoDTO]]:
        payload = self._json(
            self._get(URL_PAYOUT_RESULT, ajax=True, params={"code": ticker.lower(), "type": "1"})
        )
        chart = payload.get("chart") or {}
        anos = chart.get("category") or []
        serie_lucro_liquido = (chart.get("series") or {}).get("lucroLiquido") or []

        agora = datetime.now(timezone.utc)
        registros = []
        for ano_str, item in zip(anos, serie_lucro_liquido):
            lucro_liquido = _decimal_ou_none(item.get("value"))
            if not lucro_liquido:
                continue
            try:
                ano = int(ano_str)
            except (TypeError, ValueError):
                continue
            ll_dto = LucroLiquidoDTO(ticker=ticker, ano=ano, lucro_liquido=lucro_liquido)
            registros.append(DadoComFonte(valor=ll_dto, fonte=self.nome, data_atualizacao=agora))

        if not registros:
            raise DadosIncompletosError(
                f"statusinvest.com.br nao trouxe historico de lucro liquido valido para {ticker}"
            )
        return registros

    def _indicadores_historicos(self, ticker: str) -> dict:
        payload = self._json(
            self._post(URL_INDICATOR_HISTORICAL, data={"ticker": ticker, "time": "5"})
        )
        if not payload.get("success"):
            raise DadosIncompletosError(f"statusinvest.com.br nao trouxe indicadores para {ticker}")
        return {item["key"]: item for item in payload.get("data", []) if "key" in item}

    @staticmethod
    def _indicador_atual(indicadores_historicos: dict, chave: str) -> Optional[Decimal]:
        item = indicadores_historicos.get(chave)
        if item is None:
            return None
        return _decimal_ou_none(item.get("actual"))

    def _payout_atual(self, ticker: str) -> Optional[Decimal]:
        # Payout e "melhor esforco": se falhar, o campo fica None e e
        # preenchivel manualmente na UI - mesmo comportamento do ClienteBrapi.
        try:
            payload = self._json(
                self._get(URL_PAYOUT_RESULT, ajax=True, params={"code": ticker.lower(), "type": "1"})
            )
        except FonteDadosIndisponivelError:
            return None
        payout = _decimal_ou_none(payload.get("actual"))
        if payout is None:
            return None
        return payout / CEM
