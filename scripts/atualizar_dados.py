"""Script manual para testar a busca real de dados de um ticker.

Uso:
    python scripts/atualizar_dados.py BRBI11

Faz chamadas de rede reais (BCB + brapi.dev) - nao roda no pytest padrao.
Exige BRAPI_TOKEN configurado em .env para a maioria dos tickers (ver README).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import db.repository as repo
import services.market_data_service as market_data_service
from db.session import criar_tabelas, get_session


def main() -> None:
    if len(sys.argv) != 2:
        print("Uso: python scripts/atualizar_dados.py TICKER")
        sys.exit(1)

    ticker = sys.argv[1].upper()
    criar_tabelas()

    with get_session() as session:
        print(f"Buscando dados de {ticker}...")
        empresa = market_data_service.atualizar_dados_ativo(session, ticker, forcar=True)

        cotacao = repo.obter_cotacao_mais_recente(session, empresa)
        indicador = repo.obter_indicador_mais_recente(session, empresa)
        resultados = repo.listar_resultados_financeiros(session, empresa)

        print(f"Cotacao: {cotacao.preco if cotacao else 'N/D'} (fonte: {cotacao.fonte if cotacao else '-'})")
        print(f"ROE: {indicador.roe if indicador else 'N/D'}")
        print("Historico de Lucro Liquido:")
        for r in resultados:
            print(f"  {r.ano}: {r.lucro_liquido} (crescimento: {r.crescimento})")

        selic = market_data_service.obter_selic_para_taxa_desconto()
        print(f"Selic atual: {selic}")


if __name__ == "__main__":
    main()
