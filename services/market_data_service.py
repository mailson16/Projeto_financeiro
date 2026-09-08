"""Orquestra as fontes de dados externas com fallback e cache por "idade".

Regras (secao 18 do doc): evitar dependencia de uma unica fonte, cruzar
dados quando possivel, sempre registrar fonte + data de atualizacao. Se
todas as fontes externas falharem, o sistema nunca quebra a tela de
valuation - mantem o ultimo valor salvo no banco e deixa a UI sinalizar
que o dado esta desatualizado.
"""

from __future__ import annotations

import os
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Optional

from dotenv import load_dotenv
from sqlalchemy.orm import Session

import db.repository as repo
from data.exceptions import DadosIncompletosError, FonteDadosIndisponivelError
from data.providers.base import FonteSelic, ProvedorFundamentalista
from data.providers.bcb_selic import ClienteBCB
from data.providers.brapi import ClienteBrapi
from data.providers.statusinvest import ClienteStatusInvest
from db.models import CotacaoMercado, Empresa, Indicador

load_dotenv()

IDADE_MAXIMA_COTACAO = timedelta(hours=24)
IDADE_MAXIMA_FUNDAMENTOS = timedelta(days=30)

FONTE_SELIC: FonteSelic = ClienteBCB()
# statusinvest.com.br vem primeiro: nao exige token e cobre os mesmos campos
# (inclusive para tickers menores como BRBI11/TAEE4, que a brapi.dev so libera
# com BRAPI_TOKEN pago - ver README.md). brapi.dev fica como fallback para
# quando o statusinvest falhar ou mudar de layout (secao 18 do doc: nao
# depender de uma unica fonte).
PROVEDORES_FUNDAMENTALISTA: List[ProvedorFundamentalista] = [
    ClienteStatusInvest(),
    ClienteBrapi(token=os.getenv("BRAPI_TOKEN")),
]


def _esta_fresco(data_atualizacao: datetime, idade_maxima: timedelta) -> bool:
    referencia = data_atualizacao
    if referencia.tzinfo is None:
        referencia = referencia.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - referencia) <= idade_maxima


def atualizar_cotacao(session: Session, empresa: Empresa, forcar: bool = False) -> Optional[CotacaoMercado]:
    existente = repo.obter_cotacao_mais_recente(session, empresa)
    if not forcar and existente is not None and _esta_fresco(existente.data_atualizacao, IDADE_MAXIMA_COTACAO):
        return existente

    for provedor in PROVEDORES_FUNDAMENTALISTA:
        try:
            dado = provedor.obter_cotacao(empresa.ticker)
        except (FonteDadosIndisponivelError, DadosIncompletosError):
            continue
        return repo.salvar_cotacao(
            session,
            empresa,
            data=date.today(),
            preco=dado.valor.preco,
            numero_acoes=dado.valor.numero_acoes,
            market_cap=dado.valor.market_cap,
            fonte=dado.fonte,
            data_atualizacao=dado.data_atualizacao,
        )

    return existente  # pode ser None se nunca houve dado - a UI trata esse caso


def atualizar_indicadores(session: Session, empresa: Empresa, forcar: bool = False) -> Optional[Indicador]:
    existente = repo.obter_indicador_mais_recente(session, empresa)
    if not forcar and existente is not None and _esta_fresco(existente.data_atualizacao, IDADE_MAXIMA_FUNDAMENTOS):
        return existente

    for provedor in PROVEDORES_FUNDAMENTALISTA:
        try:
            dado = provedor.obter_indicadores(empresa.ticker)
        except (FonteDadosIndisponivelError, DadosIncompletosError):
            continue
        return repo.salvar_indicador(
            session,
            empresa,
            data=date.today(),
            payout=dado.valor.payout,
            roe=dado.valor.roe,
            patrimonio_liquido=dado.valor.patrimonio_liquido,
            lpa=dado.valor.lpa,
            fonte=dado.fonte,
            data_atualizacao=dado.data_atualizacao,
        )

    return existente


def atualizar_lucro_liquido_historico(session: Session, empresa: Empresa, forcar: bool = False) -> None:
    historico_existente = repo.listar_resultados_financeiros(session, empresa)
    if not forcar and historico_existente:
        mais_recente = max(r.data_atualizacao for r in historico_existente)
        if _esta_fresco(mais_recente, IDADE_MAXIMA_FUNDAMENTOS):
            return

    for provedor in PROVEDORES_FUNDAMENTALISTA:
        try:
            registros = provedor.obter_lucro_liquido_historico(empresa.ticker)
        except (FonteDadosIndisponivelError, DadosIncompletosError):
            continue

        registros_ordenados = sorted(registros, key=lambda r: r.valor.ano)
        anterior: Optional[Decimal] = None
        for dado in registros_ordenados:
            crescimento = None
            if anterior is not None and anterior != 0:
                crescimento = (dado.valor.lucro_liquido / anterior) - Decimal("1")
            repo.salvar_resultado_financeiro(
                session,
                empresa,
                ano=dado.valor.ano,
                lucro_liquido=dado.valor.lucro_liquido,
                fonte=dado.fonte,
                data_atualizacao=dado.data_atualizacao,
                trimestre=dado.valor.trimestre,
                crescimento=crescimento,
                tipo_metrica=dado.valor.tipo_metrica,
            )
            anterior = dado.valor.lucro_liquido
        return  # primeira fonte que respondeu com sucesso e suficiente


def atualizar_dados_ativo(session: Session, ticker: str, forcar: bool = False) -> Empresa:
    empresa = repo.get_or_create_empresa(session, ticker.upper())
    atualizar_cotacao(session, empresa, forcar=forcar)
    atualizar_indicadores(session, empresa, forcar=forcar)
    atualizar_lucro_liquido_historico(session, empresa, forcar=forcar)
    return empresa


def obter_selic_para_taxa_desconto() -> Optional[Decimal]:
    """Retorna a Selic atual (fracao, ex.: 0.14) ou None se a fonte falhar.

    Nunca levanta excecao - a UI decide o que fazer quando None (deixar o
    campo de taxa de desconto em branco para preenchimento manual).
    """
    try:
        return FONTE_SELIC.obter_selic_atual().valor
    except (FonteDadosIndisponivelError, DadosIncompletosError):
        return None
