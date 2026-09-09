from __future__ import annotations

import sys
from pathlib import Path

RAIZ_PROJETO = Path(__file__).resolve().parent.parent.parent
if str(RAIZ_PROJETO) not in sys.path:
    sys.path.insert(0, str(RAIZ_PROJETO))

from decimal import Decimal

import streamlit as st

import db.repository as repo
import services.client_service as client_service
import services.market_data_service as market_data_service
import services.valuation_service as valuation_service
from app.components.formatting import fmt_brl, fmt_brl_abreviado, fmt_numero, fmt_pct
from app.components.inputs import render_premissas_form
from db.session import criar_tabelas, get_session
from valuation.engine import PremissasValuation, rodar_valuation

st.set_page_config(page_title="Valuation - Nosso Valuation", page_icon="🧮", layout="wide")
criar_tabelas()

st.title("🧮 Valuation (DCF)")

with get_session() as session:
    clientes = client_service.listar_clientes(session)
    if not clientes:
        st.warning("Cadastre um cliente e monte a watchlist antes de rodar um valuation.")
        st.stop()

    nomes = {c.nome: c.id for c in clientes}
    id_padrao = st.session_state.get("cliente_selecionado_id", clientes[0].id)
    lista_ids = list(nomes.values())
    indice_padrao = lista_ids.index(id_padrao) if id_padrao in lista_ids else 0
    nome_selecionado = st.selectbox("Cliente", list(nomes.keys()), index=indice_padrao)
    cliente = next(c for c in clientes if c.id == nomes[nome_selecionado])
    st.session_state["cliente_selecionado_id"] = cliente.id

    watchlist = client_service.listar_watchlist(session, cliente)
    if not watchlist:
        st.warning("Este cliente ainda não tem ativos na watchlist. Adicione um na página Watchlist.")
        st.stop()

    tickers = [e.ticker for e in watchlist]
    ticker_selecionado = st.selectbox("Ativo", tickers)
    empresa = next(e for e in watchlist if e.ticker == ticker_selecionado)

    col_atualizar, _ = st.columns([1, 3])
    if col_atualizar.button("🔄 Atualizar dados de mercado"):
        with st.spinner("Buscando dados atualizados..."):
            market_data_service.atualizar_dados_ativo(session, empresa.ticker, forcar=True)
        st.rerun()

    cotacao = repo.obter_cotacao_mais_recente(session, empresa)
    indicador = repo.obter_indicador_mais_recente(session, empresa)
    market_cap = cotacao.market_cap if cotacao else None
    roe = indicador.roe if indicador else None
    payout = indicador.payout if indicador else None

    st.subheader(f"{empresa.nome} ({empresa.ticker})")
    col_mcap, col_roe, col_payout = st.columns(3)
    col_mcap.metric("Market Cap", fmt_brl_abreviado(market_cap) if market_cap is not None else "não disponível")
    col_roe.metric("ROE", fmt_pct(roe) if roe is not None else "não disponível")
    col_payout.metric("Payout", fmt_pct(payout) if payout is not None else "não disponível")

    try:
        premissas_sugeridas = valuation_service.montar_premissas_sugeridas(session, empresa, cliente)
    except ValueError as exc:
        st.error(str(exc))
        st.stop()

    st.subheader("Premissas")
    premissas_editadas = render_premissas_form(premissas_sugeridas, key_prefix=f"val_{empresa.id}")

    try:
        resultado = rodar_valuation(premissas_editadas)
    except ValueError as exc:
        st.error(f"Premissas inválidas: {exc}")
        st.stop()

    st.divider()
    st.subheader("Resultado")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Preço justo", fmt_brl(resultado.preco_justo))
    col2.metric("Preço atual", fmt_brl(premissas_editadas.preco_atual))
    col3.metric(
        "Upside/Downside",
        fmt_pct(resultado.upside) if resultado.upside is not None else "-",
        delta=fmt_pct(resultado.upside) if resultado.upside is not None else None,
    )
    col4.metric("Preço de entrada (c/ margem)", fmt_brl(resultado.preco_entrada))

    with st.expander("Detalhes da projeção"):
        st.table(
            {
                "Ano (n)": [p.ano_index for p in resultado.projecoes],
                "Lucro Líquido projetado": [fmt_brl(p.lucro_liquido) for p in resultado.projecoes],
                "VPL": [fmt_brl(p.vpl) for p in resultado.projecoes],
            }
        )
        st.write(f"**Valor Terminal:** {fmt_brl(resultado.valor_terminal)}")
        st.write(
            f"**Períodos de desconto da perpetuidade usados:** "
            f"{resultado.periodos_desconto_perpetuidade_usado} "
            "(convenção padrão do sistema — ver página Explicação)"
        )
        st.write(f"**VPL da Perpetuidade:** {fmt_brl(resultado.vpl_perpetuidade)}")
        st.write(f"**Valor estimado total:** {fmt_brl(resultado.valor_estimado)}")

    if st.button("💾 Salvar este valuation"):
        valuation_service.salvar_valuation(session, empresa, resultado, cenario="custom", cliente=cliente)
        st.success("Valuation salvo.")
