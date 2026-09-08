from decimal import Decimal

import pytest
import requests

from data.exceptions import DadosIncompletosError, FonteDadosIndisponivelError
from data.providers.brapi import ClienteBrapi

TICKER = "BRBI11"
URL = f"https://brapi.dev/api/quote/{TICKER}"

PAYLOAD_COMPLETO = {
    "results": [
        {
            "symbol": TICKER,
            "regularMarketPrice": 12.43,
            "marketCap": 1305096601,
            "earningsPerShare": 0.55,
            "defaultKeyStatistics": {"sharesOutstanding": 314987112},
            "financialData": {"returnOnEquity": 0.197},
            "incomeStatementHistory": [
                {"endDate": "2025-12-31", "netIncome": 175073000},
                {"endDate": "2024-12-31", "netIncome": 193670000},
            ],
            "balanceSheetHistory": [{"shareholdersEquity": 900000000}],
        }
    ],
    "requestedAt": "2026-01-01T00:00:00.000Z",
}


def test_obter_cotacao_sucesso(requests_mock):
    requests_mock.get(URL, json=PAYLOAD_COMPLETO)

    resultado = ClienteBrapi().obter_cotacao(TICKER)

    assert resultado.valor.preco == Decimal("12.43")
    assert resultado.valor.numero_acoes == Decimal("314987112")
    assert resultado.fonte == "brapi.dev"


def test_obter_cotacao_sem_shares_outstanding_estima_via_market_cap(requests_mock):
    payload = {
        "results": [
            {
                "symbol": TICKER,
                "regularMarketPrice": 10.0,
                "marketCap": 1000000,
            }
        ]
    }
    requests_mock.get(URL, json=payload)

    resultado = ClienteBrapi().obter_cotacao(TICKER)

    assert resultado.valor.numero_acoes == Decimal("100000")


def test_obter_cotacao_sem_preco_levanta_dados_incompletos(requests_mock):
    requests_mock.get(URL, json={"results": [{"symbol": TICKER}]})

    with pytest.raises(DadosIncompletosError):
        ClienteBrapi().obter_cotacao(TICKER)


def test_obter_cotacao_resultados_vazio_levanta_dados_incompletos(requests_mock):
    requests_mock.get(URL, json={"results": []})

    with pytest.raises(DadosIncompletosError):
        ClienteBrapi().obter_cotacao(TICKER)


def test_obter_cotacao_timeout_levanta_fonte_indisponivel(requests_mock):
    requests_mock.get(URL, exc=requests.exceptions.Timeout)

    with pytest.raises(FonteDadosIndisponivelError):
        ClienteBrapi().obter_cotacao(TICKER)


def test_obter_lucro_liquido_historico_sucesso(requests_mock):
    requests_mock.get(URL, json=PAYLOAD_COMPLETO)

    registros = ClienteBrapi().obter_lucro_liquido_historico(TICKER)

    assert len(registros) == 2
    assert registros[0].valor.ano == 2025
    assert registros[0].valor.lucro_liquido == Decimal("175073000")


def test_obter_lucro_liquido_historico_vazio_levanta_dados_incompletos(requests_mock):
    requests_mock.get(URL, json={"results": [{"symbol": TICKER, "incomeStatementHistory": []}]})

    with pytest.raises(DadosIncompletosError):
        ClienteBrapi().obter_lucro_liquido_historico(TICKER)


def test_obter_indicadores_sucesso(requests_mock):
    requests_mock.get(URL, json=PAYLOAD_COMPLETO)

    resultado = ClienteBrapi().obter_indicadores(TICKER)

    assert resultado.valor.roe == Decimal("0.197")
    assert resultado.valor.patrimonio_liquido == Decimal("900000000")
    assert resultado.valor.lpa == Decimal("0.55")
    assert resultado.valor.payout is None


def test_token_e_enviado_como_query_param(requests_mock):
    requests_mock.get(URL, json=PAYLOAD_COMPLETO)

    ClienteBrapi(token="minha-chave").obter_cotacao(TICKER)

    assert requests_mock.last_request.qs.get("token") == ["minha-chave"]
