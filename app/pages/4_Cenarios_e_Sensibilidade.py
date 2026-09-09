from __future__ import annotations

import sys
from pathlib import Path

RAIZ_PROJETO = Path(__file__).resolve().parent.parent.parent
if str(RAIZ_PROJETO) not in sys.path:
    sys.path.insert(0, str(RAIZ_PROJETO))

from decimal import Decimal

import plotly.express as px
import streamlit as st

import db.repository as repo
import services.client_service as client_service
import services.valuation_service as valuation_service
from app.components.formatting import fmt_brl, fmt_pct
from db.session import criar_tabelas, get_session
from valuation.scenarios import CENARIOS_PADRAO, rodar_cenarios
from valuation.sensitivity import matriz_sensibilidade

st.set_page_config(page_title="Cenários e Sensibilidade - Nosso Valuation", page_icon="📊", layout="wide")
criar_tabelas()

st.title("📊 Cenários e Sensibilidade")

with get_session() as session:
    clientes = client_service.listar_clientes(session)
    if not clientes:
        st.warning("Cadastre um cliente e monte a watchlist antes de ver cenários.")
        st.stop()

    nomes = {c.nome: c.id for c in clientes}
    id_padrao = st.session_state.get("cliente_selecionado_id", clientes[0].id)
    lista_ids = list(nomes.values())
    indice_padrao = lista_ids.index(id_padrao) if id_padrao in lista_ids else 0
    nome_selecionado = st.selectbox("Cliente", list(nomes.keys()), index=indice_padrao)
    cliente = next(c for c in clientes if c.id == nomes[nome_selecionado])

    watchlist = client_service.listar_watchlist(session, cliente)
    if not watchlist:
        st.warning("Este cliente ainda não tem ativos na watchlist.")
        st.stop()

    ticker_selecionado = st.selectbox("Ativo", [e.ticker for e in watchlist])
    empresa = next(e for e in watchlist if e.ticker == ticker_selecionado)

    valuation_salvo = repo.obter_valuation_mais_recente(session, empresa, cliente)
    if valuation_salvo is None:
        st.warning(
            f"Nenhum valuation salvo para {empresa.ticker} com este cliente. "
            "Rode e salve um na página **Valuation** antes de ver cenários e sensibilidade."
        )
        st.stop()

    base = valuation_service.premissas_do_valuation_salvo(valuation_salvo)
    st.caption(
        f"📌 Baseado no valuation salvo em {valuation_salvo.data_calculo.strftime('%d/%m/%Y %H:%M')} "
        f"(cenário: {valuation_salvo.cenario})."
    )

    st.subheader("Cenários (conservador / base / otimista)")
    resultados_cenarios = rodar_cenarios(base, CENARIOS_PADRAO)

    st.table(
        {
            "Cenário": [c.nome.capitalize() for c in CENARIOS_PADRAO],
            "Crescimento": [fmt_pct(c.taxa_crescimento) for c in CENARIOS_PADRAO],
            "Taxa de desconto": [fmt_pct(c.taxa_desconto) for c in CENARIOS_PADRAO],
            "Perpetuidade": [fmt_pct(c.crescimento_perpetuidade) for c in CENARIOS_PADRAO],
            "Preço justo": [fmt_brl(resultados_cenarios[c.nome].preco_justo) for c in CENARIOS_PADRAO],
            "Upside": [
                fmt_pct(resultados_cenarios[c.nome].upside) if resultados_cenarios[c.nome].upside is not None else "-"
                for c in CENARIOS_PADRAO
            ],
        }
    )

    st.divider()
    st.subheader("Análise de sensibilidade")
    st.caption("Preço justo variando taxa de crescimento (linhas) x taxa de desconto (colunas), perpetuidade fixa.")

    col1, col2 = st.columns(2)
    with col1:
        centro_crescimento = st.slider(
            "Centro da faixa de crescimento (%)", 0.0, 15.0, float(base.taxa_crescimento * 100), 0.5
        )
    with col2:
        centro_desconto = st.slider(
            "Centro da faixa de desconto (%)", 5.0, 25.0, float(base.taxa_desconto * 100), 0.5
        )

    passos = [-2, -1, 0, 1, 2]
    taxas_crescimento = [Decimal(str(round(centro_crescimento + p, 2))) / Decimal("100") for p in passos]
    taxas_desconto = [Decimal(str(round(centro_desconto + p, 2))) / Decimal("100") for p in passos]

    df = matriz_sensibilidade(base, taxas_crescimento, taxas_desconto)
    df_exibicao = df.copy()
    df_exibicao.index = [fmt_pct(v) for v in df_exibicao.index]
    df_exibicao.columns = [fmt_pct(v) for v in df_exibicao.columns]

    fig = px.imshow(
        df.astype(float),
        labels=dict(x="Taxa de desconto", y="Taxa de crescimento", color="Preço justo (R$)"),
        x=[fmt_pct(v) for v in df.columns],
        y=[fmt_pct(v) for v in df.index],
        text_auto=".2f",
        color_continuous_scale="RdYlGn",
    )
    fig.update_layout(height=420)
    st.plotly_chart(fig, use_container_width=True)
