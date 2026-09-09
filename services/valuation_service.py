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
from typing import List, Optional

from sqlalchemy.orm import Session

import db.repository as repo
import services.market_data_service as market_data_service
from db.models import Cliente, Empresa
from db.models import ResultadoFinanceiro
from db.models import Valuation as ValuationModel
from valuation.constants import GROWTH_MODE_AUTOMATIC, GROWTH_MODE_MANUAL, MODEL_VERSION
from valuation.engine import (
    PremissasValuation,
    ResultadoValuation,
    calcular_crescimento_sustentavel,
    rodar_valuation,
)

ANOS_PROJECAO_PADRAO = 3
CRESCIMENTO_PERPETUIDADE_PADRAO = Decimal("0.03")
MARGEM_SEGURANCA_PADRAO = Decimal("0.20")
TAXA_CRESCIMENTO_PADRAO_SE_SEM_HISTORICO = Decimal("0.04")


def _resultados_anos_completos(session: Session, empresa: Empresa) -> List[ResultadoFinanceiro]:
    """Historico anual, excluindo o ano corrente.

    O ultimo item retornado pela fonte de dados para o ano corrente costuma
    ser um Lucro Liquido parcial (YTD, ver docstring de
    data/providers/statusinvest.py) - nao um ano fiscal fechado. Usa-lo como
    se fosse um ano completo distorce tanto a taxa de crescimento media
    quanto o LL do ano-base (que ficaria artificialmente baixo). Por isso o
    ano corrente e sempre excluido do calculo de premissas sugeridas; o
    ano-base e projetado a partir do ultimo ano fechado (secao 7 do doc).
    """
    resultados = repo.listar_resultados_financeiros(session, empresa)
    ano_atual = date.today().year
    return [r for r in resultados if r.ano < ano_atual]


def _crescimento_medio_historico(resultados_completos: List[ResultadoFinanceiro]) -> Optional[Decimal]:
    crescimentos = [r.crescimento for r in resultados_completos if r.crescimento is not None]
    if not crescimentos:
        return None
    return sum(crescimentos, Decimal("0")) / len(crescimentos)


def _crescimento_automatico(
    session: Session, empresa: Empresa, resultados_completos: List[ResultadoFinanceiro]
) -> tuple[Decimal, Optional[Decimal], Optional[Decimal]]:
    """Crescimento sugerido quando growth_mode=automatic (secao 9 do SKILL.md).

    Prioridade: g = ROE x (1-Payout) quando ambos disponiveis no indicador
    mais recente (retorna o roe/payout usados, para rastreabilidade); senao,
    media historica do LL (apenas anos fechados); senao, um piso
    conservador (nesses dois ultimos casos, roe/payout retornam None - o
    crescimento nao veio dessa formula).
    """
    indicador = repo.obter_indicador_mais_recente(session, empresa)
    if indicador is not None and indicador.roe is not None and indicador.payout is not None:
        g = calcular_crescimento_sustentavel(indicador.roe, indicador.payout)
        return g, indicador.roe, indicador.payout
    g = _crescimento_medio_historico(resultados_completos) or TAXA_CRESCIMENTO_PADRAO_SE_SEM_HISTORICO
    return g, None, None


def montar_premissas_sugeridas(
    session: Session, empresa: Empresa, cliente: Optional[Cliente] = None
) -> PremissasValuation:
    """Sugere premissas iniciais a partir dos dados salvos - o usuario pode editar tudo na UI.

    Regra da secao 52 do SKILL.md: se o ultimo valuation salvo para
    (empresa, cliente) tinha uma premissa alterada manualmente (taxa de
    desconto, lucro base ou crescimento), a sugestao NAO deve substitui-la
    silenciosamente pelo valor automatico atualizado (ex.: nova Selic) - o
    valor manual anterior e sugerido de novo, mas o valor automatico atual
    tambem e exposto para a UI mostrar a divergencia.
    """
    resultados_completos = _resultados_anos_completos(session, empresa)
    if not resultados_completos:
        raise ValueError(
            f"Nao ha historico de Lucro Liquido (ano fechado) salvo para {empresa.ticker}. "
            "Rode market_data_service.atualizar_dados_ativo antes de sugerir premissas."
        )

    taxa_desconto_automatica = market_data_service.obter_selic_para_taxa_desconto()

    cotacao = repo.obter_cotacao_mais_recente(session, empresa)
    if cotacao is None:
        raise ValueError(
            f"Nao ha cotacao salva para {empresa.ticker}. "
            "Rode market_data_service.atualizar_dados_ativo antes de sugerir premissas."
        )

    ultimo_valuation = repo.obter_valuation_mais_recente(session, empresa, cliente)

    # --- Taxa de desconto (auto = Selic) ---
    if ultimo_valuation is not None and ultimo_valuation.taxa_desconto_manual_override:
        taxa_desconto = ultimo_valuation.taxa_desconto
        taxa_desconto_manual_override = True
    elif taxa_desconto_automatica is not None:
        taxa_desconto = taxa_desconto_automatica
        taxa_desconto_manual_override = False
    else:
        raise ValueError(
            "Nao foi possivel obter a Selic automaticamente. Informe a taxa de desconto manualmente."
        )
    taxa_desconto_original_automatico = taxa_desconto_automatica

    # --- Crescimento (auto = ROE x (1-Payout) ou media historica de anos fechados) ---
    taxa_crescimento_automatica, roe_automatico, payout_automatico = _crescimento_automatico(
        session, empresa, resultados_completos
    )
    if ultimo_valuation is not None and ultimo_valuation.growth_mode == GROWTH_MODE_MANUAL:
        taxa_crescimento = ultimo_valuation.taxa_crescimento
        roe = ultimo_valuation.roe
        payout = ultimo_valuation.payout
        growth_mode = GROWTH_MODE_MANUAL
    else:
        taxa_crescimento, roe, payout = taxa_crescimento_automatica, roe_automatico, payout_automatico
        growth_mode = GROWTH_MODE_AUTOMATIC

    # --- Lucro base (auto = projecao do ultimo ano fechado pela taxa de
    # crescimento automatica, secao 7: "LL futuro = LL anterior x (1 + g)".
    # O ultimo ano retornado pela fonte de dados costuma ser um LL parcial
    # (YTD) - por isso `_resultados_anos_completos` ja o exclui, e o
    # ano-base e sempre projetado a partir do ultimo ano fiscal fechado,
    # nunca do valor bruto de um ano em andamento.) ---
    ll_ultimo_ano_fechado = resultados_completos[-1].lucro_liquido
    ll_ano_base_fonte = ll_ultimo_ano_fechado * (Decimal("1") + taxa_crescimento_automatica)
    if ultimo_valuation is not None and ultimo_valuation.ll_ano_base_manual_override:
        ll_ano_base = ultimo_valuation.ll_ano_base
        ll_ano_base_manual_override = True
    else:
        ll_ano_base = ll_ano_base_fonte
        ll_ano_base_manual_override = False

    return PremissasValuation(
        ll_ano_base=ll_ano_base,
        taxa_crescimento=taxa_crescimento,
        taxa_desconto=taxa_desconto,
        crescimento_perpetuidade=CRESCIMENTO_PERPETUIDADE_PADRAO,
        anos_projecao=ANOS_PROJECAO_PADRAO,
        numero_acoes=cotacao.numero_acoes,
        preco_atual=cotacao.preco,
        margem_seguranca=MARGEM_SEGURANCA_PADRAO,
        growth_mode=growth_mode,
        taxa_desconto_manual_override=taxa_desconto_manual_override,
        taxa_desconto_original_automatico=taxa_desconto_original_automatico,
        ll_ano_base_manual_override=ll_ano_base_manual_override,
        ll_ano_base_original_fonte=ll_ano_base_fonte,
        roe=roe,
        payout=payout,
    )


def premissas_do_valuation_salvo(valuation: ValuationModel) -> PremissasValuation:
    """Reconstroi as premissas exatamente como foram usadas num valuation ja
    salvo - para paginas que devem operar sobre "o valor que salvei"
    (Cenarios, Sensibilidade, Explicacao), em vez de uma sugestao nova."""
    return PremissasValuation(
        ll_ano_base=valuation.ll_ano_base,
        taxa_crescimento=valuation.taxa_crescimento,
        taxa_desconto=valuation.taxa_desconto,
        crescimento_perpetuidade=valuation.crescimento_perpetuidade,
        anos_projecao=valuation.anos_projecao,
        numero_acoes=valuation.numero_acoes,
        preco_atual=valuation.preco_atual_usado,
        margem_seguranca=valuation.margem_seguranca,
        periodos_desconto_perpetuidade=valuation.periodos_desconto_perpetuidade,
        growth_mode=valuation.growth_mode,
        taxa_desconto_manual_override=valuation.taxa_desconto_manual_override,
        taxa_desconto_original_automatico=valuation.taxa_desconto_original_automatico,
        ll_ano_base_manual_override=valuation.ll_ano_base_manual_override,
        ll_ano_base_original_fonte=valuation.ll_ano_base_original_fonte,
        roe=valuation.roe,
        payout=valuation.payout,
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
        "model_version": MODEL_VERSION,
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
        model_version=MODEL_VERSION,
        growth_mode=premissas.growth_mode,
        taxa_desconto_manual_override=premissas.taxa_desconto_manual_override,
        taxa_desconto_original_automatico=premissas.taxa_desconto_original_automatico,
        ll_ano_base_manual_override=premissas.ll_ano_base_manual_override,
        ll_ano_base_original_fonte=premissas.ll_ano_base_original_fonte,
        roe=premissas.roe,
        payout=premissas.payout,
        payload_json=json.dumps(payload, default=_decimal_para_json, ensure_ascii=False),
    )
    repo.excluir_valuations(session, empresa, cliente)
    return repo.salvar_valuation(session, valuation)


def montar_e_rodar_valuation(
    session: Session, empresa: Empresa, cliente: Optional[Cliente] = None
) -> ResultadoValuation:
    premissas = montar_premissas_sugeridas(session, empresa, cliente)
    return rodar_valuation(premissas)
