"""Liga motor de valuation + dados + banco.

Unico lugar que monta `PremissasValuation` sugeridas a partir do que esta
salvo no banco (historico de LL, cotacao, Selic) e que persiste o
resultado de um `rodar_valuation` como um registro `Valuation`.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

import db.repository as repo
import services.market_data_service as market_data_service
from db.models import Cliente, Empresa
from db.models import Valuation as ValuationModel
from valuation.engine import PremissasValuation, ResultadoValuation, rodar_valuation

ANOS_PROJECAO_PADRAO = 3
CRESCIMENTO_PERPETUIDADE_PADRAO = Decimal("0.03")
MARGEM_SEGURANCA_PADRAO = Decimal("0.20")
TAXA_CRESCIMENTO_PADRAO_SE_SEM_HISTORICO = Decimal("0.04")


def _crescimento_medio_historico(session: Session, empresa: Empresa) -> Optional[Decimal]:
    resultados = repo.listar_resultados_financeiros(session, empresa)
    crescimentos = [r.crescimento for r in resultados if r.crescimento is not None]
    if not crescimentos:
        return None
    return sum(crescimentos, Decimal("0")) / len(crescimentos)


def montar_premissas_sugeridas(session: Session, empresa: Empresa) -> PremissasValuation:
    """Sugere premissas iniciais a partir dos dados salvos - o usuario pode editar tudo na UI."""
    resultados = repo.listar_resultados_financeiros(session, empresa)
    if not resultados:
        raise ValueError(
            f"Nao ha historico de Lucro Liquido salvo para {empresa.ticker}. "
            "Rode market_data_service.atualizar_dados_ativo antes de sugerir premissas."
        )
    ll_ano_base = resultados[-1].lucro_liquido  # ano mais recente disponivel

    taxa_crescimento = _crescimento_medio_historico(session, empresa) or TAXA_CRESCIMENTO_PADRAO_SE_SEM_HISTORICO

    taxa_desconto = market_data_service.obter_selic_para_taxa_desconto()
    if taxa_desconto is None:
        raise ValueError(
            "Nao foi possivel obter a Selic automaticamente. Informe a taxa de desconto manualmente."
        )

    cotacao = repo.obter_cotacao_mais_recente(session, empresa)
    if cotacao is None:
        raise ValueError(
            f"Nao ha cotacao salva para {empresa.ticker}. "
            "Rode market_data_service.atualizar_dados_ativo antes de sugerir premissas."
        )

    return PremissasValuation(
        ll_ano_base=ll_ano_base,
        taxa_crescimento=taxa_crescimento,
        taxa_desconto=taxa_desconto,
        crescimento_perpetuidade=CRESCIMENTO_PERPETUIDADE_PADRAO,
        anos_projecao=ANOS_PROJECAO_PADRAO,
        numero_acoes=cotacao.numero_acoes,
        preco_atual=cotacao.preco,
        margem_seguranca=MARGEM_SEGURANCA_PADRAO,
    )


def _decimal_para_json(obj):
    if isinstance(obj, Decimal):
        return str(obj)
    if isinstance(obj, date):
        return obj.isoformat()
    raise TypeError(f"Tipo nao serializavel: {type(obj)}")


def salvar_valuation(
    session: Session,
    empresa: Empresa,
    resultado: ResultadoValuation,
    cenario: str = "custom",
    cliente: Optional[Cliente] = None,
) -> ValuationModel:
    """Salva o resultado como o (unico) valuation atual de (empresa, cliente).

    Mantem so a alteracao mais recente: qualquer valuation salvo antes para
    esse mesmo par empresa/cliente e apagado. `data_calculo` (default do
    modelo) registra quando esse calculo foi feito.
    """
    premissas = resultado.premissas
    payload = {
        "premissas": asdict(premissas),
        "projecoes": [asdict(p) for p in resultado.projecoes],
        "valor_terminal": resultado.valor_terminal,
        "periodos_desconto_perpetuidade_usado": resultado.periodos_desconto_perpetuidade_usado,
        "vpl_perpetuidade": resultado.vpl_perpetuidade,
        "valor_estimado": resultado.valor_estimado,
        "preco_justo": resultado.preco_justo,
        "upside": resultado.upside,
        "preco_entrada": resultado.preco_entrada,
    }

    valuation = ValuationModel(
        empresa_id=empresa.id,
        cliente_id=cliente.id if cliente else None,
        cenario=cenario,
        ll_ano_base=premissas.ll_ano_base,
        taxa_crescimento=premissas.taxa_crescimento,
        taxa_desconto=premissas.taxa_desconto,
        crescimento_perpetuidade=premissas.crescimento_perpetuidade,
        anos_projecao=premissas.anos_projecao,
        periodos_desconto_perpetuidade=resultado.periodos_desconto_perpetuidade_usado,
        numero_acoes=premissas.numero_acoes,
        preco_atual_usado=premissas.preco_atual,
        margem_seguranca=premissas.margem_seguranca,
        valor_estimado=resultado.valor_estimado,
        preco_justo=resultado.preco_justo,
        upside=resultado.upside,
        preco_entrada=resultado.preco_entrada,
        payload_json=json.dumps(payload, default=_decimal_para_json, ensure_ascii=False),
    )
    repo.excluir_valuations(session, empresa, cliente)
    return repo.salvar_valuation(session, valuation)


def montar_e_rodar_valuation(session: Session, empresa: Empresa) -> ResultadoValuation:
    premissas = montar_premissas_sugeridas(session, empresa)
    return rodar_valuation(premissas)
