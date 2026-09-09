from __future__ import annotations

import sys
from pathlib import Path

RAIZ_PROJETO = Path(__file__).resolve().parent.parent.parent
if str(RAIZ_PROJETO) not in sys.path:
    sys.path.insert(0, str(RAIZ_PROJETO))

import json
from decimal import Decimal

import streamlit as st

import db.repository as repo
import services.client_service as client_service
import services.market_data_service as market_data_service
from app.components.formatting import fmt_brl, fmt_brl_abreviado, fmt_numero, fmt_pct
from db.session import criar_tabelas, get_session

st.set_page_config(page_title="Watchlist - Nosso Valuation", page_icon="⭐", layout="wide")
criar_tabelas()

st.title("⭐ Watchlist do cliente")

with get_session() as session:
    clientes = client_service.listar_clientes(session)

    if not clientes:
        st.warning("Cadastre um cliente na página **Clientes** antes de montar uma watchlist.")
        st.stop()

    nomes = {c.nome: c.id for c in clientes}
    nome_selecionado = st.selectbox("Cliente", list(nomes.keys()))
    cliente_id = nomes[nome_selecionado]
    st.session_state["cliente_selecionado_id"] = cliente_id
    cliente = next(c for c in clientes if c.id == cliente_id)

    with st.form("form_add_ativo", clear_on_submit=True):
        ticker = st.text_input("Ticker (ex.: BRBI11, TAEE4, ITSA4)").strip().upper()
        adicionar = st.form_submit_button("Adicionar à watchlist")

    if adicionar and ticker:
        with st.spinner(f"Buscando dados de {ticker}..."):
            empresa = client_service.adicionar_ativo_watchlist(session, cliente, ticker)
            try:
                market_data_service.atualizar_dados_ativo(session, ticker)
                st.success(f"{ticker} adicionado e dados atualizados.")
            except Exception as exc:  # falha de rede/fonte nao pode travar a UI
                st.warning(
                    f"{ticker} adicionado à watchlist, mas não foi possível buscar dados agora ({exc}). "
                    "Tente atualizar depois na página Valuation."
                )
        st.rerun()

    st.divider()
    watchlist = client_service.listar_watchlist(session, cliente)

    if not watchlist:
        st.info("Nenhum ativo na watchlist deste cliente ainda.")
    else:
        for empresa in watchlist:
            cotacao = repo.obter_cotacao_mais_recente(session, empresa)
            valuation = repo.obter_valuation_mais_recente(session, empresa, cliente)

            preco_atual = cotacao.preco if cotacao else None
            preco_justo = valuation.preco_justo if valuation else None
            upside = None
            if preco_justo is not None and preco_atual is not None and preco_atual > 0:
                upside = (preco_justo / preco_atual) - Decimal("1")
            rotulo_data = valuation.data_calculo.strftime("%d/%m/%Y %H:%M") if valuation else None

            with st.container(border=True):
                col_ticker, col_preco, col_justo, col_upside, col_acoes = st.columns([3, 1.4, 1.4, 1.4, 1])
                with col_ticker:
                    st.markdown(f"**{empresa.ticker}**  \n{empresa.nome}")
                    if cotacao is not None and cotacao.market_cap is not None:
                        st.caption(f"Market Cap: {fmt_brl_abreviado(cotacao.market_cap)}")
                with col_preco:
                    st.metric("Preço atual", fmt_brl(preco_atual) if preco_atual is not None else "-")
                with col_justo:
                    st.metric("Preço justo (salvo)", fmt_brl(preco_justo) if preco_justo is not None else "-")
                    if rotulo_data is not None:
                        st.caption(f"🕒 Calculado em {rotulo_data}")
                with col_upside:
                    st.metric(
                        "Upside/Downside",
                        fmt_pct(upside) if upside is not None else "-",
                        delta=fmt_pct(upside) if upside is not None else None,
                    )
                with col_acoes:
                    if st.button("Remover", key=f"rm_{empresa.id}"):
                        client_service.remover_ativo_watchlist(session, cliente, empresa)
                        st.rerun()

                if valuation is None:
                    st.caption(
                        "Nenhum valuation salvo ainda para este ativo. Rode um na página **Valuation**."
                    )
                else:
                    with st.expander(f"📋 Ver dados salvos deste valuation ({valuation.cenario} · {rotulo_data})"):
                        st.markdown("**Premissas usadas para chegar nesse preço justo**")
                        st.table(
                            {
                                "Premissa": [
                                    "Lucro Líquido do ano-base",
                                    "Taxa de crescimento",
                                    "Taxa de desconto",
                                    "Crescimento na perpetuidade",
                                    "Anos de projeção",
                                    "Número de ações",
                                    "Preço atual usado no cálculo",
                                    "Margem de segurança",
                                ],
                                "Valor": [
                                    f"{fmt_brl(valuation.ll_ano_base)} ({fmt_brl_abreviado(valuation.ll_ano_base)})",
                                    fmt_pct(valuation.taxa_crescimento),
                                    fmt_pct(valuation.taxa_desconto),
                                    fmt_pct(valuation.crescimento_perpetuidade),
                                    str(valuation.anos_projecao),
                                    fmt_numero(valuation.numero_acoes),
                                    fmt_brl(valuation.preco_atual_usado),
                                    fmt_pct(valuation.margem_seguranca),
                                ],
                            }
                        )

                        st.markdown("**Resultado salvo**")
                        st.table(
                            {
                                "Métrica": [
                                    "Valor estimado total",
                                    "Preço justo",
                                    "Upside/Downside (na época do cálculo)",
                                    "Preço de entrada (c/ margem de segurança)",
                                ],
                                "Valor": [
                                    fmt_brl(valuation.valor_estimado),
                                    fmt_brl(valuation.preco_justo),
                                    fmt_pct(valuation.upside) if valuation.upside is not None else "-",
                                    fmt_brl(valuation.preco_entrada),
                                ],
                            }
                        )

                        payload = json.loads(valuation.payload_json) if valuation.payload_json else None
                        projecoes = (payload or {}).get("projecoes") or []
                        if projecoes:
                            st.markdown("**Projeção ano a ano usada nesse cálculo**")
                            st.table(
                                {
                                    "Ano (n)": [p["ano_index"] for p in projecoes],
                                    "Lucro Líquido projetado": [
                                        fmt_brl(Decimal(p["lucro_liquido"])) for p in projecoes
                                    ],
                                    "VPL": [fmt_brl(Decimal(p["vpl"])) for p in projecoes],
                                }
                            )
