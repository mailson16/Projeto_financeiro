from __future__ import annotations

import sys
from pathlib import Path

RAIZ_PROJETO = Path(__file__).resolve().parent.parent.parent
if str(RAIZ_PROJETO) not in sys.path:
    sys.path.insert(0, str(RAIZ_PROJETO))

import streamlit as st

import services.client_service as client_service
from db.session import criar_tabelas, get_session

st.set_page_config(page_title="Clientes - Nosso Valuation", page_icon="👥", layout="wide")
criar_tabelas()

st.title("👥 Clientes")

with st.expander("➕ Novo cliente", expanded=False):
    with st.form("form_novo_cliente", clear_on_submit=True):
        nome = st.text_input("Nome*")
        email = st.text_input("E-mail")
        telefone = st.text_input("Telefone")
        observacoes = st.text_area("Observações")
        enviado = st.form_submit_button("Cadastrar")

    if enviado:
        if not nome.strip():
            st.error("Informe o nome do cliente.")
        else:
            with get_session() as session:
                client_service.criar_cliente(
                    session, nome=nome.strip(), email=email or None, telefone=telefone or None, observacoes=observacoes or None
                )
            st.success(f"Cliente '{nome}' cadastrado.")
            st.rerun()

st.divider()

with get_session() as session:
    clientes = client_service.listar_clientes(session)

    if not clientes:
        st.info("Nenhum cliente cadastrado ainda. Use o formulário acima para começar.")
    else:
        for cliente in clientes:
            watchlist = client_service.listar_watchlist(session, cliente)
            with st.container(border=True):
                col_info, col_acao = st.columns([4, 1])
                with col_info:
                    st.markdown(f"**{cliente.nome}**")
                    detalhes = " · ".join(filter(None, [cliente.email, cliente.telefone]))
                    if detalhes:
                        st.caption(detalhes)
                    tickers = ", ".join(e.ticker for e in watchlist) or "nenhum ativo na watchlist"
                    st.caption(f"Watchlist: {tickers}")
                with col_acao:
                    if st.button("Remover", key=f"remover_{cliente.id}"):
                        client_service.remover_cliente(session, cliente)
                        st.rerun()
