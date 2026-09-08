"""Monta a 'memoria de calculo' do valuation (secao 15 do doc).

O sistema nao deve apenas informar um preco justo - deve explicar como
chegou la. `MemoriaCalculo` empacota, na ordem descrita na secao 15, tudo
que a camada de apresentacao (pagina "Explicacao" do Streamlit) precisa
para narrar o calculo passo a passo, sem precisar reconstruir logica.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Sequence

import pandas as pd

from valuation.engine import PremissasValuation, ResultadoValuation


@dataclass(frozen=True)
class MemoriaCalculo:
    # 1. Dados historicos
    dados_historicos: Optional[Sequence[Any]]
    # 2. Premissas
    premissas: PremissasValuation
    # 3. Lucro do ano-base
    ll_ano_base: Any
    # 4. Projecoes
    projecoes: tuple
    # 5. Taxa de desconto
    taxa_desconto: Any
    # 6. VPL de cada periodo -> ja contido em `projecoes` (ProjecaoAno.vpl)
    # 7. Perpetuidade (Valor Terminal)
    valor_terminal: Any
    # 8. VPL da perpetuidade
    vpl_perpetuidade: Any
    # 9. Valor total
    valor_total: Any
    # 10. Numero de acoes
    numero_acoes: Any
    # 11. Preco justo
    preco_justo: Any
    # 12. Preco atual
    preco_atual: Optional[Any]
    # 13. Upside/Downside
    upside: Optional[Any]
    # 14. Margem de seguranca
    preco_entrada: Any
    # 15. Cenarios
    cenarios: Optional[Dict[str, ResultadoValuation]]
    # 16. Sensibilidade
    sensibilidade: Optional[pd.DataFrame]


def montar_memoria_calculo(
    resultado: ResultadoValuation,
    dados_historicos: Optional[Sequence[Any]] = None,
    cenarios: Optional[Dict[str, ResultadoValuation]] = None,
    sensibilidade: Optional[pd.DataFrame] = None,
) -> MemoriaCalculo:
    premissas = resultado.premissas
    return MemoriaCalculo(
        dados_historicos=dados_historicos,
        premissas=premissas,
        ll_ano_base=premissas.ll_ano_base,
        projecoes=resultado.projecoes,
        taxa_desconto=premissas.taxa_desconto,
        valor_terminal=resultado.valor_terminal,
        vpl_perpetuidade=resultado.vpl_perpetuidade,
        valor_total=resultado.valor_estimado,
        numero_acoes=premissas.numero_acoes,
        preco_justo=resultado.preco_justo,
        preco_atual=premissas.preco_atual,
        upside=resultado.upside,
        preco_entrada=resultado.preco_entrada,
        cenarios=cenarios,
        sensibilidade=sensibilidade,
    )
