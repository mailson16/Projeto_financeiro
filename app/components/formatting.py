"""Formatacao BRL/percentual reaproveitada entre paginas do Streamlit."""

from __future__ import annotations

from decimal import Decimal
from typing import Optional


def fmt_brl(valor: Optional[Decimal]) -> str:
    if valor is None:
        return "-"
    texto = f"{valor:,.2f}"
    texto = texto.replace(",", "§").replace(".", ",").replace("§", ".")
    return f"R$ {texto}"


def fmt_pct(valor: Optional[Decimal], casas: int = 2) -> str:
    if valor is None:
        return "-"
    texto = f"{valor * 100:,.{casas}f}"
    texto = texto.replace(",", "§").replace(".", ",").replace("§", ".")
    return f"{texto}%"


def fmt_numero(valor: Optional[Decimal]) -> str:
    if valor is None:
        return "-"
    texto = f"{valor:,.0f}"
    texto = texto.replace(",", ".")
    return texto


_UNIDADES_ABREVIADAS = [
    (Decimal("1000000000000"), "trilhão", "trilhões"),
    (Decimal("1000000000"), "bilhão", "bilhões"),
    (Decimal("1000000"), "milhão", "milhões"),
    (Decimal("1000"), "mil", "mil"),
]


def fmt_brl_abreviado(valor: Optional[Decimal]) -> str:
    """Formata um valor de R$ grande com sufixo (mil/milhão/bilhão/trilhão).

    Serve como "mascara" de leitura para campos como o Lucro Liquido do
    ano-base, que vem em unidades de R$ (ex.: 175073000.00) e e dificil de
    ler de cabeca sem essa indicacao de ordem de grandeza.
    """
    if valor is None:
        return "-"

    absoluto = abs(valor)
    for limite, singular, plural in _UNIDADES_ABREVIADAS:
        if absoluto >= limite:
            escalado = absoluto / limite
            sufixo = singular if escalado.quantize(Decimal("0.01")) == Decimal("1.00") else plural
            texto = fmt_brl(escalado)
            if valor < 0:
                texto = texto.replace("R$ ", "R$ -")
            return f"{texto} {sufixo}"
    return fmt_brl(valor)
