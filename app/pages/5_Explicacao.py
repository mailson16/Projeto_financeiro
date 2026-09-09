from __future__ import annotations

import sys
from pathlib import Path

RAIZ_PROJETO = Path(__file__).resolve().parent.parent.parent
if str(RAIZ_PROJETO) not in sys.path:
    sys.path.insert(0, str(RAIZ_PROJETO))

import streamlit as st

import db.repository as repo
import services.client_service as client_service
import services.valuation_service as valuation_service
from app.components.formatting import fmt_brl, fmt_numero, fmt_pct
from db.session import criar_tabelas, get_session
from valuation.engine import rodar_valuation
from valuation.explain import montar_memoria_calculo
from valuation.scenarios import CENARIOS_PADRAO, rodar_cenarios
from valuation.sensitivity import matriz_sensibilidade

st.set_page_config(page_title="Explicação - Nosso Valuation", page_icon="🔍", layout="wide")
criar_tabelas()

st.title("🔍 Explicação passo a passo")
st.caption("O sistema não deve apenas informar um preço justo — deve explicar como chegou lá (seção 15 do doc).")

with get_session() as session:
    clientes = client_service.listar_clientes(session)
    if not clientes:
        st.warning("Cadastre um cliente e monte a watchlist antes de ver a explicação.")
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
            "Rode e salve um na página **Valuation** antes de ver a explicação."
        )
        st.stop()

    premissas = valuation_service.premissas_do_valuation_salvo(valuation_salvo)
    st.caption(
        f"📌 Baseado no valuation salvo em {valuation_salvo.data_calculo.strftime('%d/%m/%Y %H:%M')} "
        f"(cenário: {valuation_salvo.cenario})."
    )

    resultado = rodar_valuation(premissas)
    dados_historicos = repo.listar_resultados_financeiros(session, empresa)
    cenarios = rodar_cenarios(premissas, CENARIOS_PADRAO)

    passos = [-2, -1, 0, 1, 2]
    from decimal import Decimal

    taxas_crescimento = [premissas.taxa_crescimento + Decimal(p) / Decimal("100") for p in passos]
    taxas_desconto = [premissas.taxa_desconto + Decimal(p) / Decimal("100") for p in passos]
    sensibilidade = matriz_sensibilidade(premissas, taxas_crescimento, taxas_desconto)

    memoria = montar_memoria_calculo(resultado, dados_historicos, cenarios, sensibilidade)

    with st.expander("1. Dados históricos", expanded=True):
        if memoria.dados_historicos:
            st.table(
                {
                    "Ano": [r.ano for r in memoria.dados_historicos],
                    "Lucro Líquido": [fmt_brl(r.lucro_liquido) for r in memoria.dados_historicos],
                    "Crescimento": [fmt_pct(r.crescimento) if r.crescimento is not None else "-" for r in memoria.dados_historicos],
                    "Fonte": [r.fonte for r in memoria.dados_historicos],
                }
            )
        else:
            st.write("Sem histórico salvo.")

    with st.expander("2. Premissas utilizadas"):
        st.json(
            {
                "LL ano-base": fmt_brl(memoria.premissas.ll_ano_base),
                "Taxa de crescimento": fmt_pct(memoria.premissas.taxa_crescimento),
                "Taxa de desconto": fmt_pct(memoria.premissas.taxa_desconto),
                "Crescimento na perpetuidade": fmt_pct(memoria.premissas.crescimento_perpetuidade),
                "Anos de projeção": memoria.premissas.anos_projecao,
                "Margem de segurança": fmt_pct(memoria.premissas.margem_seguranca),
            }
        )

    with st.expander("3. Lucro Líquido do ano-base"):
        st.write(fmt_brl(memoria.ll_ano_base))

    with st.expander("4. Projeções e 6. VPL de cada período"):
        st.table(
            {
                "Ano (n)": [p.ano_index for p in memoria.projecoes],
                "Lucro Líquido projetado": [fmt_brl(p.lucro_liquido) for p in memoria.projecoes],
                "VPL": [fmt_brl(p.vpl) for p in memoria.projecoes],
            }
        )

    with st.expander("5. Taxa de desconto"):
        st.write(f"{fmt_pct(memoria.taxa_desconto)} (sugerida pela Selic atual, editável)")

    with st.expander("7. Perpetuidade (Valor Terminal)"):
        st.write(fmt_brl(memoria.valor_terminal))
        st.caption(
            f"Descontado por {resultado.periodos_desconto_perpetuidade_usado} períodos — "
            "convenção padrão do sistema (N = anos de projeção), decisão explícita para "
            "NÃO reproduzir a convenção fracionária observada na ferramenta de referência Ward "
            "(ver nosso_valuation_aprendizado.md, seção 9)."
        )

    with st.expander("8. VPL da perpetuidade"):
        st.write(fmt_brl(memoria.vpl_perpetuidade))

    with st.expander("9. Valor total estimado"):
        st.write(fmt_brl(memoria.valor_total))

    with st.expander("10. Número de ações"):
        st.write(fmt_numero(memoria.numero_acoes))

    with st.expander("11. Preço justo"):
        st.write(fmt_brl(memoria.preco_justo))

    with st.expander("12. Preço atual"):
        st.write(fmt_brl(memoria.preco_atual))

    with st.expander("13. Upside / Downside"):
        st.write(fmt_pct(memoria.upside) if memoria.upside is not None else "-")

    with st.expander("14. Margem de segurança e preço de entrada"):
        st.write(f"Margem: {fmt_pct(memoria.premissas.margem_seguranca)}")
        st.write(f"Preço de entrada: {fmt_brl(memoria.preco_entrada)}")

    with st.expander("15. Cenários"):
        if memoria.cenarios:
            st.table(
                {
                    "Cenário": list(memoria.cenarios.keys()),
                    "Preço justo": [fmt_brl(r.preco_justo) for r in memoria.cenarios.values()],
                    "Upside": [fmt_pct(r.upside) if r.upside is not None else "-" for r in memoria.cenarios.values()],
                }
            )

    with st.expander("16. Sensibilidade"):
        if memoria.sensibilidade is not None:
            df_exibicao = memoria.sensibilidade.copy()
            df_exibicao.index = [fmt_pct(v) for v in df_exibicao.index]
            df_exibicao.columns = [fmt_pct(v) for v in df_exibicao.columns]
            st.dataframe(df_exibicao.style.format(fmt_brl))
