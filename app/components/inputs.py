"""Widgets padronizados de premissas de valuation, reaproveitados entre paginas."""

from __future__ import annotations

from decimal import Decimal
from typing import Optional

import streamlit as st

from app.components.formatting import fmt_brl
from valuation.engine import PremissasValuation


def render_premissas_form(premissas: PremissasValuation, key_prefix: str) -> PremissasValuation:
    """Renderiza os widgets de premissas editaveis (secao 4 do doc) e retorna
    uma NOVA PremissasValuation com os valores atuais dos widgets - nunca
    muta a instancia recebida."""

    col1, col2 = st.columns(2)
    with col1:
        ll_ano_base = st.number_input(
            "Lucro Liquido do ano-base (R$)",
            value=float(premissas.ll_ano_base),
            step=1_000_000.0,
            format="%.2f",
            key=f"{key_prefix}_ll_ano_base",
        )
        st.caption(fmt_brl(Decimal(str(ll_ano_base))))
        payout_medio = st.number_input(
            "Payout medio (%)",
            value=float(premissas.payout_medio * 100) if premissas.payout_medio is not None else 0.0,
            step=0.1,
            format="%.2f",
            key=f"{key_prefix}_payout_medio",
        )
        roe = st.number_input(
            "ROE (%)",
            value=float(premissas.roe * 100) if premissas.roe is not None else 0.0,
            step=0.1,
            format="%.2f",
            key=f"{key_prefix}_roe",
        )
        taxa_crescimento = st.number_input(
            "Taxa de crescimento esperada (%)",
            value=float(premissas.taxa_crescimento * 100),
            step=0.1,
            format="%.2f",
            key=f"{key_prefix}_taxa_crescimento",
        )
        taxa_desconto = st.number_input(
            "Taxa de desconto (%) - sugerida pela Selic, editavel",
            value=float(premissas.taxa_desconto * 100),
            step=0.1,
            format="%.2f",
            key=f"{key_prefix}_taxa_desconto",
        )
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

    return PremissasValuation(
        ll_ano_base=Decimal(str(ll_ano_base)),
        taxa_crescimento=Decimal(str(taxa_crescimento)) / Decimal("100"),
        taxa_desconto=Decimal(str(taxa_desconto)) / Decimal("100"),
        crescimento_perpetuidade=Decimal(str(crescimento_perpetuidade)) / Decimal("100"),
        anos_projecao=int(anos_projecao),
        numero_acoes=Decimal(str(numero_acoes)),
        preco_atual=Decimal(str(preco_atual)) if preco_atual > 0 else None,
        margem_seguranca=Decimal(str(margem_seguranca)) / Decimal("100"),
        payout_medio=Decimal(str(payout_medio)) / Decimal("100") if payout_medio > 0 else None,
        roe=Decimal(str(roe)) / Decimal("100") if roe > 0 else None,
    )
