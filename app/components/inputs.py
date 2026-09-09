"""Widgets padronizados de premissas de valuation, reaproveitados entre paginas."""

from __future__ import annotations

from decimal import Decimal
from typing import Optional

import streamlit as st

from app.components.formatting import fmt_brl_abreviado, fmt_pct
from valuation.constants import GROWTH_MODE_AUTOMATIC, GROWTH_MODE_MANUAL
from valuation.engine import PremissasValuation, calcular_crescimento_sustentavel

_TOLERANCIA_COMPARACAO = Decimal("0.000001")


def _diferente(a: Optional[Decimal], b: Optional[Decimal]) -> bool:
    """Compara dois Decimais tolerando o ruido do round-trip Decimal->float->Decimal."""
    if a is None or b is None:
        return a is not b
    return abs(a - b) > _TOLERANCIA_COMPARACAO


def render_premissas_form(premissas: PremissasValuation, key_prefix: str) -> PremissasValuation:
    """Renderiza os widgets de premissas editaveis (secao 4 do doc) e retorna
    uma NOVA PremissasValuation com os valores atuais dos widgets - nunca
    muta a instancia recebida.

    Indicacao visual (secao 38 do SKILL.md): quando o valor final do campo
    difere do valor automatico sugerido (Selic para taxa de desconto, fonte
    de dados para o lucro base), mostra um aviso "Alterado manualmente" e
    marca `*_manual_override=True` na premissa retornada, para que o
    proximo `montar_premissas_sugeridas` no mesmo (empresa, cliente) nao
    substitua silenciosamente o valor manual pelo automatico atualizado
    (secao 52).
    """

    col1, col2 = st.columns(2)
    with col1:
        ll_ano_base = st.number_input(
            "Lucro Liquido do ano-base (R$)",
            value=float(premissas.ll_ano_base),
            step=1_000_000.0,
            format="%.2f",
            key=f"{key_prefix}_ll_ano_base",
        )
        st.caption(f"≈ {fmt_brl_abreviado(Decimal(str(ll_ano_base)))}")
        if premissas.ll_ano_base_original_fonte is not None:
            if _diferente(Decimal(str(ll_ano_base)), premissas.ll_ano_base_original_fonte):
                st.caption(f"✏️ Alterado manualmente (fonte: {fmt_brl_abreviado(premissas.ll_ano_base_original_fonte)})")
            else:
                st.caption("🤖 Valor automático (última fonte de dados)")

        growth_mode_widget = st.radio(
            "Origem do crescimento",
            options=[GROWTH_MODE_AUTOMATIC, GROWTH_MODE_MANUAL],
            index=0 if premissas.growth_mode == GROWTH_MODE_AUTOMATIC else 1,
            format_func=lambda m: "Automático (ROE × (1-Payout) ou histórico)" if m == GROWTH_MODE_AUTOMATIC else "Manual (informo ROE e Payout)",
            key=f"{key_prefix}_growth_mode",
            horizontal=True,
        )

        if growth_mode_widget == GROWTH_MODE_MANUAL:
            # Secao 9/10 do SKILL.md: no modo manual o usuario informa ROE e
            # Payout diretamente (nao a taxa de crescimento pronta) - o
            # crescimento e sempre DERIVADO de g = ROE x (1-Payout), para que
            # o numero final continue rastreavel ("de onde veio esse numero?").
            col_roe, col_payout = st.columns(2)
            with col_roe:
                roe_manual = st.number_input(
                    "ROE (%)",
                    value=float((premissas.roe or Decimal("0")) * 100),
                    step=0.1,
                    format="%.2f",
                    key=f"{key_prefix}_roe_manual",
                )
            with col_payout:
                payout_manual = st.number_input(
                    "Payout (%)",
                    value=float((premissas.payout or Decimal("0")) * 100),
                    step=0.1,
                    format="%.2f",
                    key=f"{key_prefix}_payout_manual",
                )
            roe_final = Decimal(str(roe_manual)) / Decimal("100")
            payout_final = Decimal(str(payout_manual)) / Decimal("100")
            taxa_crescimento_final = calcular_crescimento_sustentavel(roe_final, payout_final)
            st.metric("Crescimento esperado (g = ROE × (1-Payout))", fmt_pct(taxa_crescimento_final))
            st.caption("✏️ Calculado a partir do ROE/Payout informados manualmente — tem prioridade sobre o automático")
        else:
            roe_final = premissas.roe
            payout_final = premissas.payout
            taxa_crescimento_final = premissas.taxa_crescimento
            st.metric("Crescimento esperado", fmt_pct(taxa_crescimento_final))
            if roe_final is not None and payout_final is not None:
                st.caption(f"🤖 ROE: {fmt_pct(roe_final)} · Payout: {fmt_pct(payout_final)} (última fonte de dados)")
            else:
                st.caption("🤖 Calculado a partir da média histórica de crescimento (ROE/Payout indisponíveis)")
        taxa_desconto = st.number_input(
            "Taxa de desconto (%) - sugerida pela Selic, editavel",
            value=float(premissas.taxa_desconto * 100),
            step=0.1,
            format="%.2f",
            key=f"{key_prefix}_taxa_desconto",
        )
        if premissas.taxa_desconto_original_automatico is not None:
            if _diferente(Decimal(str(taxa_desconto)) / Decimal("100"), premissas.taxa_desconto_original_automatico):
                st.caption(f"✏️ Alterado manualmente (Selic atual: {fmt_pct(premissas.taxa_desconto_original_automatico)})")
            else:
                st.caption(f"🤖 Selic atual: {fmt_pct(premissas.taxa_desconto_original_automatico)}")
        crescimento_perpetuidade = st.number_input(
            "Crescimento na perpetuidade (%)",
            value=float(premissas.crescimento_perpetuidade * 100),
            step=0.1,
            format="%.2f",
            key=f"{key_prefix}_g_perpetuidade",
        )
    with col2:
        anos_projecao = st.number_input(
            "Numero de anos de projecao",
            value=int(premissas.anos_projecao),
            min_value=1,
            max_value=15,
            step=1,
            key=f"{key_prefix}_anos_projecao",
        )
        numero_acoes = st.number_input(
            "Numero de acoes",
            value=float(premissas.numero_acoes),
            step=1000.0,
            format="%.0f",
            key=f"{key_prefix}_numero_acoes",
        )
        preco_atual = st.number_input(
            "Preco atual (R$)",
            value=float(premissas.preco_atual) if premissas.preco_atual is not None else 0.0,
            step=0.01,
            format="%.2f",
            key=f"{key_prefix}_preco_atual",
        )
        margem_seguranca = st.number_input(
            "Margem de seguranca (%)",
            value=float(premissas.margem_seguranca * 100),
            step=1.0,
            format="%.2f",
            key=f"{key_prefix}_margem_seguranca",
        )

    ll_ano_base_final = Decimal(str(ll_ano_base))
    taxa_desconto_final = Decimal(str(taxa_desconto)) / Decimal("100")

    ll_ano_base_manual_override = (
        _diferente(ll_ano_base_final, premissas.ll_ano_base_original_fonte)
        if premissas.ll_ano_base_original_fonte is not None
        else premissas.ll_ano_base_manual_override
    )
    taxa_desconto_manual_override = (
        _diferente(taxa_desconto_final, premissas.taxa_desconto_original_automatico)
        if premissas.taxa_desconto_original_automatico is not None
        else premissas.taxa_desconto_manual_override
    )

    return PremissasValuation(
        ll_ano_base=ll_ano_base_final,
        taxa_crescimento=taxa_crescimento_final,
        taxa_desconto=taxa_desconto_final,
        crescimento_perpetuidade=Decimal(str(crescimento_perpetuidade)) / Decimal("100"),
        anos_projecao=int(anos_projecao),
        numero_acoes=Decimal(str(numero_acoes)),
        preco_atual=Decimal(str(preco_atual)) if preco_atual > 0 else None,
        margem_seguranca=Decimal(str(margem_seguranca)) / Decimal("100"),
        growth_mode=growth_mode_widget,
        taxa_desconto_manual_override=taxa_desconto_manual_override,
        taxa_desconto_original_automatico=premissas.taxa_desconto_original_automatico,
        ll_ano_base_manual_override=ll_ano_base_manual_override,
        ll_ano_base_original_fonte=premissas.ll_ano_base_original_fonte,
        roe=roe_final,
        payout=payout_final,
    )
