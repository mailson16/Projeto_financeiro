"""Nosso Valuation - pagina inicial do Streamlit."""

from __future__ import annotations

import sys
from pathlib import Path

RAIZ_PROJETO = Path(__file__).resolve().parent.parent
if str(RAIZ_PROJETO) not in sys.path:
    sys.path.insert(0, str(RAIZ_PROJETO))

import streamlit as st

import db.repository as repo
from db.session import criar_tabelas, get_session

st.set_page_config(
    page_title="Nosso Valuation",
    page_icon="📈",
    layout="wide",
)

CSS = """
<style>
.block-container { padding-top: 2rem; max-width: 1100px; }
[data-testid="stMetricValue"] { font-size: 1.6rem; }
h1, h2, h3 { letter-spacing: -0.01em; }
.nv-card {
    background: var(--secondary-background-color);
    border-radius: 12px;
    padding: 1.25rem 1.5rem;
    border: 1px solid rgba(128,128,128,0.15);
}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

criar_tabelas()

st.title("📈 Nosso Valuation")
st.caption("Acompanhamento de clientes e valuation por DCF para ativos da B3.")

with get_session() as session:
    clientes = repo.listar_clientes(session)
    empresas = repo.listar_empresas(session)

col1, col2, col3 = st.columns(3)
col1.metric("Clientes cadastrados", len(clientes))
col2.metric("Ativos acompanhados", len(empresas))
col3.metric("Modo", "Nosso Valuation (Modo 2)")

st.divider()

st.markdown(
    """
### Como usar
1. **Clientes** — cadastre seus clientes.
2. **Watchlist** — associe os ativos da B3 que cada cliente acompanha.
3. **Valuation** — rode o DCF de um ativo, com premissas sugeridas automaticamente
   (Selic para a taxa de desconto, histórico de Lucro Líquido para o crescimento).
4. **Cenários e Sensibilidade** — compare conservador/base/otimista e veja a robustez do resultado.
5. **Explicação** — veja o passo a passo completo do cálculo, sem caixa-preta.

Use o menu à esquerda para navegar entre as páginas.
"""
)

st.info(
    "A taxa de desconto é sugerida automaticamente pela Selic atual, mas é sempre editável. "
    "A convenção de desconto da perpetuidade usada por padrão é o número inteiro de anos de "
    "projeção — uma decisão de design explícita deste sistema (ver página Explicação)."
)
