"""Cliente da API SGS (series temporais) do Banco Central do Brasil.

Serie 432 = Meta Selic definida pelo Copom (% a.a.), oficial e gratuita,
sem necessidade de chave de API.

Ver secao 5 do doc: a taxa de desconto e preenchida automaticamente com a
Selic atual, mas sempre editavel pelo usuario.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation

import requests

from data.dto import DadoComFonte
from data.exceptions import DadosIncompletosError, FonteDadosIndisponivelError
from data.providers.base import FonteSelic

URL_SELIC_ULTIMO_VALOR = (
    "https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados/ultimos/1?formato=json"
)


class ClienteBCB(FonteSelic):
    nome = "BCB-SGS-432"

    def __init__(self, timeout_segundos: float = 10.0, session: requests.Session | None = None):
        self._timeout = timeout_segundos
        self._session = session or requests.Session()

    def obter_selic_atual(self) -> DadoComFonte[Decimal]:
        try:
            resposta = self._session.get(URL_SELIC_ULTIMO_VALOR, timeout=self._timeout)
            resposta.raise_for_status()
            dados = resposta.json()
        except (requests.RequestException, ValueError) as exc:
            raise FonteDadosIndisponivelError(
                f"Falha ao consultar a Selic no BCB: {exc}"
            ) from exc

        if not dados:
            raise DadosIncompletosError("API do BCB retornou lista vazia para a Selic")

        item = dados[0]
        try:
            valor_percentual = Decimal(str(item["valor"]))
            data_referencia = datetime.strptime(item["data"], "%d/%m/%Y")
        except (KeyError, InvalidOperation, ValueError) as exc:
            raise DadosIncompletosError(f"Payload inesperado da API do BCB: {item}") from exc

        selic_fracao = valor_percentual / Decimal("100")
        return DadoComFonte(valor=selic_fracao, fonte=self.nome, data_atualizacao=data_referencia)
