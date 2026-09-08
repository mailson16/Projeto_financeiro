from decimal import Decimal

import pytest
import requests

from data.exceptions import DadosIncompletosError, FonteDadosIndisponivelError
from data.providers.bcb_selic import URL_SELIC_ULTIMO_VALOR, ClienteBCB


def test_obter_selic_atual_sucesso(requests_mock):
    requests_mock.get(URL_SELIC_ULTIMO_VALOR, json=[{"data": "20/08/2026", "valor": "14.00"}])

    resultado = ClienteBCB().obter_selic_atual()

    assert resultado.valor == Decimal("0.14")
    assert resultado.fonte == "BCB-SGS-432"


def test_obter_selic_atual_lista_vazia_levanta_dados_incompletos(requests_mock):
    requests_mock.get(URL_SELIC_ULTIMO_VALOR, json=[])

    with pytest.raises(DadosIncompletosError):
        ClienteBCB().obter_selic_atual()


def test_obter_selic_atual_timeout_levanta_fonte_indisponivel(requests_mock):
    requests_mock.get(URL_SELIC_ULTIMO_VALOR, exc=requests.exceptions.Timeout)

    with pytest.raises(FonteDadosIndisponivelError):
        ClienteBCB().obter_selic_atual()


def test_obter_selic_atual_status_erro_levanta_fonte_indisponivel(requests_mock):
    requests_mock.get(URL_SELIC_ULTIMO_VALOR, status_code=500)

    with pytest.raises(FonteDadosIndisponivelError):
        ClienteBCB().obter_selic_atual()


def test_obter_selic_atual_payload_malformado_levanta_dados_incompletos(requests_mock):
    requests_mock.get(URL_SELIC_ULTIMO_VALOR, json=[{"data": "20/08/2026"}])  # sem "valor"

    with pytest.raises(DadosIncompletosError):
        ClienteBCB().obter_selic_atual()
