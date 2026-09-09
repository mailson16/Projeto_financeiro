"""Analise de sensibilidade do preco justo (secao 14 do doc)."""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from typing import Optional, Sequence

import pandas as pd

from valuation.engine import PremissasValuation, rodar_valuation


def matriz_sensibilidade(
    base: PremissasValuation,
    taxas_crescimento: Sequence[Decimal],
    taxas_desconto: Sequence[Decimal],
    crescimento_perpetuidade: Optional[Decimal] = None,
) -> pd.DataFrame:
    """Preco justo variando taxa de crescimento (linhas) x taxa de desconto (colunas).

    `crescimento_perpetuidade` fica fixo em `base.crescimento_perpetuidade`
    a menos que um valor alternativo seja informado. Reusa `rodar_valuation`
    para cada celula - nao duplica nenhuma formula do motor.
    """
    g = crescimento_perpetuidade if crescimento_perpetuidade is not None else base.crescimento_perpetuidade

    linhas = {}
    for crescimento in taxas_crescimento:
        colunas = {}
        for desconto in taxas_desconto:
            try:
                premissas = replace(
                    base,
                    taxa_crescimento=crescimento,
                    taxa_desconto=desconto,
                    crescimento_perpetuidade=g,
                )
                resultado = rodar_valuation(premissas)
                colunas[desconto] = resultado.preco_justo
            except ValueError:
                colunas[desconto] = None
        linhas[crescimento] = colunas

    df = pd.DataFrame.from_dict(linhas, orient="index")
    df = df.sort_index().sort_index(axis=1)
    df.index.name = "taxa_crescimento"
    df.columns.name = "taxa_desconto"
    return df
