"""Modelos SQLAlchemy (secao 17 do doc, com o acrescimo de Cliente/ClienteAtivo).

Toda tabela que guarda um dado vindo de fonte externa carrega `fonte` e
`data_atualizacao` (secao 18: "registro da fonte e da data de atualizacao").
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def _agora() -> datetime:
    return datetime.now(timezone.utc)


class Empresa(Base):
    __tablename__ = "empresas"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticker: Mapped[str] = mapped_column(unique=True, index=True)
    nome: Mapped[str]
    setor: Mapped[Optional[str]]
    tipo_ativo: Mapped[Optional[str]]
    ativo: Mapped[bool] = mapped_column(default=True)

    cotacoes: Mapped[List["CotacaoMercado"]] = relationship(back_populates="empresa")
    indicadores: Mapped[List["Indicador"]] = relationship(back_populates="empresa")
    resultados: Mapped[List["ResultadoFinanceiro"]] = relationship(back_populates="empresa")
    dividendos: Mapped[List["Dividendo"]] = relationship(back_populates="empresa")
    valuations: Mapped[List["Valuation"]] = relationship(back_populates="empresa")


class CotacaoMercado(Base):
    __tablename__ = "cotacoes_mercado"
    __table_args__ = (UniqueConstraint("empresa_id", "data", name="uq_cotacao_empresa_data"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"))
    data: Mapped[date]
    preco: Mapped[Decimal]
    numero_acoes: Mapped[Decimal]
    market_cap: Mapped[Optional[Decimal]]
    fonte: Mapped[str]
    data_atualizacao: Mapped[datetime] = mapped_column(default=_agora)

    empresa: Mapped["Empresa"] = relationship(back_populates="cotacoes")


class Indicador(Base):
    __tablename__ = "indicadores"
    __table_args__ = (UniqueConstraint("empresa_id", "data", name="uq_indicador_empresa_data"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"))
    data: Mapped[date]
    payout: Mapped[Optional[Decimal]]
    roe: Mapped[Optional[Decimal]]
    patrimonio_liquido: Mapped[Optional[Decimal]]
    lpa: Mapped[Optional[Decimal]]
    fonte: Mapped[str]
    data_atualizacao: Mapped[datetime] = mapped_column(default=_agora)

    empresa: Mapped["Empresa"] = relationship(back_populates="indicadores")


class ResultadoFinanceiro(Base):
    __tablename__ = "resultados_financeiros"
    __table_args__ = (
        UniqueConstraint(
            "empresa_id", "ano", "trimestre", "tipo_metrica", name="uq_resultado_empresa_periodo"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"))
    ano: Mapped[int]
    trimestre: Mapped[Optional[int]]  # None = resultado anual
    lucro_liquido: Mapped[Decimal]
    crescimento: Mapped[Optional[Decimal]]
    tipo_metrica: Mapped[str] = mapped_column(default="contabil")  # "contabil" | "regulatoria"
    fonte: Mapped[str]
    data_atualizacao: Mapped[datetime] = mapped_column(default=_agora)

    empresa: Mapped["Empresa"] = relationship(back_populates="resultados")


class Dividendo(Base):
    __tablename__ = "dividendos"

    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"))
    data: Mapped[date]
    valor: Mapped[Decimal]
    tipo: Mapped[str]  # "dividendo" | "jcp"
    fonte: Mapped[str]
    data_atualizacao: Mapped[datetime] = mapped_column(default=_agora)

    empresa: Mapped["Empresa"] = relationship(back_populates="dividendos")


class Valuation(Base):
    __tablename__ = "valuations"

    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"))
    cliente_id: Mapped[Optional[int]] = mapped_column(ForeignKey("clientes.id"))
    data_calculo: Mapped[datetime] = mapped_column(default=_agora)
    cenario: Mapped[str]  # "conservador" | "base" | "otimista" | "custom"

    ll_ano_base: Mapped[Decimal]
    taxa_crescimento: Mapped[Decimal]
    taxa_desconto: Mapped[Decimal]
    crescimento_perpetuidade: Mapped[Decimal]
    anos_projecao: Mapped[int]
    periodos_desconto_perpetuidade: Mapped[Decimal]
    numero_acoes: Mapped[Decimal]
    preco_atual_usado: Mapped[Optional[Decimal]]
    margem_seguranca: Mapped[Decimal]

    valor_estimado: Mapped[Decimal]
    preco_justo: Mapped[Decimal]
    upside: Mapped[Optional[Decimal]]
    preco_entrada: Mapped[Decimal]

    payload_json: Mapped[Optional[str]]  # memoria de calculo completa serializada

    empresa: Mapped["Empresa"] = relationship(back_populates="valuations")
    cliente: Mapped[Optional["Cliente"]] = relationship(back_populates="valuations")


class Cliente(Base):
    __tablename__ = "clientes"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str]
    email: Mapped[Optional[str]]
    telefone: Mapped[Optional[str]]
    observacoes: Mapped[Optional[str]]
    criado_em: Mapped[datetime] = mapped_column(default=_agora)

    watchlist: Mapped[List["ClienteAtivo"]] = relationship(back_populates="cliente", cascade="all, delete-orphan")
    valuations: Mapped[List["Valuation"]] = relationship(back_populates="cliente")


class ClienteAtivo(Base):
    """Watchlist N:N entre Cliente e Empresa - sem quantidade/posicao financeira."""

    __tablename__ = "clientes_ativos"

    cliente_id: Mapped[int] = mapped_column(ForeignKey("clientes.id"), primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), primary_key=True)
    criado_em: Mapped[datetime] = mapped_column(default=_agora)

    cliente: Mapped["Cliente"] = relationship(back_populates="watchlist")
    empresa: Mapped["Empresa"] = relationship()
