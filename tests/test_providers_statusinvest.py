from decimal import Decimal

import pytest
import requests

from data.exceptions import DadosIncompletosError, FonteDadosIndisponivelError
from data.providers.statusinvest import ClienteStatusInvest

TICKER = "BRBI11"
URL_PAGINA = f"https://statusinvest.com.br/acoes/{TICKER.lower()}"
URL_INDICATOR_HISTORICAL = "https://statusinvest.com.br/acao/indicatorhistorical"
URL_PAYOUT_RESULT = "https://statusinvest.com.br/acao/payoutresult"

HTML_PAGINA_COMPLETA = """
<html><body>
<div title="Valor atual do ativo">
  <h3 class="title m-0">Valor atual</h3>
  <span class="icon">R$</span>
  <strong class="value">12,43</strong>
</div>

<div class="info">
  <div title="bug de copia do site: titulo nao corresponde ao indicador">
    <h3 class="title m-0"></h3>
    <a href="https://statusinvest.com.br/termos/p/patrimonio-liquido" title="Artigo detalhando Patrimonio liquido">
      <h3 class="title m-0">Patrim&ocirc;nio l&iacute;quido</h3>
    </a>
    <b class="icon">R$</b>
    <strong class="value">900.000.000</strong>
  </div>
</div>

<div class="info" title="O valor da acao multiplicado pelo numero de acoes existentes">
  <div>
    <div>
      <a href="https://statusinvest.com.br/termos/v/valor-de-mercado" title="Artigo detalhando Valor de mercado">
        <h3 class="title m-0">Valor de mercado</h3>
      </a>
      <b class="icon">R$</b>
      <strong class="value">1.305.096.601</strong>
    </div>
  </div>
</div>

<div class="info">
  <div title="Total de papeis disponiveis para negociacao">
    <div>
      <h3 class="title m-0 legend-tooltip">
        <span class="d-inline-block mr-2">N&ordm; total de pap&eacute;is</span>
      </h3>
      <strong class="value">314.987.112</strong>
    </div>
  </div>
</div>
</body></html>
"""

HTML_SEM_PRECO = "<html><body><p>sem indicadores aqui</p></body></html>"

JSON_INDICATOR_HISTORICAL = {
    "success": True,
    "data": [
        {"key": "roe", "actual": 19.70},
        {"key": "lpa", "actual": 0.55},
        {"key": "p_l", "actual": 9.34},
    ],
}

JSON_PAYOUT_RESULT = {
    "actual": 78.96,
    "chart": {
        "category": ["2021", "2022", "2023", "2024", "2025"],
        "series": {
            "lucroLiquido": [
                {"value": 138660000.00},
                {"value": 147101000.00},
                {"value": 155084000.00},
                {"value": 193670000.00},
                {"value": 175073000.00},
            ],
            "percentual": [{"value": 61.33}, {"value": 62.10}, {"value": 93.43}, {"value": 326.91}, {"value": 302.26}],
        },
    },
}


def test_obter_cotacao_sucesso(requests_mock):
    requests_mock.get(URL_PAGINA, text=HTML_PAGINA_COMPLETA)

    resultado = ClienteStatusInvest().obter_cotacao(TICKER)

    # numero_acoes vem de market_cap / preco, nao do card "Nº total de
    # papeis": esse card soma ON+PN (todas as classes emitidas), que para
    # tickers em units (ex.: BRBI11) fica inflado em relacao ao numero de
    # acoes que o mercado de fato usa para precificar.
    esperado = Decimal("1305096601") / Decimal("12.43")
    assert resultado.valor.preco == Decimal("12.43")
    assert resultado.valor.numero_acoes == esperado
    assert resultado.valor.market_cap == Decimal("1305096601")
    assert resultado.fonte == "statusinvest.com.br"


def test_obter_cotacao_sem_market_cap_usa_total_de_papeis(requests_mock):
    html = HTML_PAGINA_COMPLETA.replace(
        '<strong class="value">1.305.096.601</strong>', "<strong class=\"value\">-</strong>"
    )
    requests_mock.get(URL_PAGINA, text=html)

    resultado = ClienteStatusInvest().obter_cotacao(TICKER)

    assert resultado.valor.numero_acoes == Decimal("314987112")
    # market_cap e recalculado a partir de preco * numero_acoes (fallback).
    assert resultado.valor.market_cap == Decimal("12.43") * Decimal("314987112")


def test_obter_cotacao_sem_preco_levanta_dados_incompletos(requests_mock):
    requests_mock.get(URL_PAGINA, text=HTML_SEM_PRECO)

    with pytest.raises(DadosIncompletosError):
        ClienteStatusInvest().obter_cotacao(TICKER)


def test_obter_cotacao_timeout_levanta_fonte_indisponivel(requests_mock):
    requests_mock.get(URL_PAGINA, exc=requests.exceptions.Timeout)

    with pytest.raises(FonteDadosIndisponivelError):
        ClienteStatusInvest().obter_cotacao(TICKER)


def test_obter_cotacao_403_levanta_fonte_indisponivel(requests_mock):
    requests_mock.get(URL_PAGINA, status_code=403, text="blocked")

    with pytest.raises(FonteDadosIndisponivelError):
        ClienteStatusInvest().obter_cotacao(TICKER)


def test_obter_indicadores_sucesso(requests_mock):
    requests_mock.get(URL_PAGINA, text=HTML_PAGINA_COMPLETA)
    requests_mock.post(URL_INDICATOR_HISTORICAL, json=JSON_INDICATOR_HISTORICAL)
    requests_mock.get(URL_PAYOUT_RESULT, json=JSON_PAYOUT_RESULT)

    resultado = ClienteStatusInvest().obter_indicadores(TICKER)

    assert resultado.valor.roe == Decimal("19.70") / Decimal("100")
    assert resultado.valor.lpa == Decimal("0.55")
    assert resultado.valor.patrimonio_liquido == Decimal("900000000")
    assert resultado.valor.payout == Decimal("78.96") / Decimal("100")


def test_obter_indicadores_payout_indisponivel_fica_none(requests_mock):
    requests_mock.get(URL_PAGINA, text=HTML_PAGINA_COMPLETA)
    requests_mock.post(URL_INDICATOR_HISTORICAL, json=JSON_INDICATOR_HISTORICAL)
    requests_mock.get(URL_PAYOUT_RESULT, exc=requests.exceptions.Timeout)

    resultado = ClienteStatusInvest().obter_indicadores(TICKER)

    assert resultado.valor.payout is None
    assert resultado.valor.roe == Decimal("19.70") / Decimal("100")


def test_obter_indicadores_historico_falho_levanta_dados_incompletos(requests_mock):
    requests_mock.get(URL_PAGINA, text=HTML_PAGINA_COMPLETA)
    requests_mock.post(URL_INDICATOR_HISTORICAL, json={"success": False, "data": []})
    requests_mock.get(URL_PAYOUT_RESULT, json=JSON_PAYOUT_RESULT)

    with pytest.raises(DadosIncompletosError):
        ClienteStatusInvest().obter_indicadores(TICKER)


def test_obter_lucro_liquido_historico_sucesso(requests_mock):
    requests_mock.get(URL_PAYOUT_RESULT, json=JSON_PAYOUT_RESULT)

    registros = ClienteStatusInvest().obter_lucro_liquido_historico(TICKER)

    assert len(registros) == 5
    assert registros[0].valor.ano == 2021
    assert registros[0].valor.lucro_liquido == Decimal("138660000.00")
    assert registros[4].valor.ano == 2025
    assert registros[4].valor.lucro_liquido == Decimal("175073000.00")
    assert registros[0].fonte == "statusinvest.com.br"


def test_obter_lucro_liquido_historico_vazio_levanta_dados_incompletos(requests_mock):
    requests_mock.get(URL_PAYOUT_RESULT, json={"chart": {"category": [], "series": {"lucroLiquido": []}}})

    with pytest.raises(DadosIncompletosError):
        ClienteStatusInvest().obter_lucro_liquido_historico(TICKER)
