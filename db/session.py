"""Engine/sessionmaker do banco. Le DATABASE_URL do ambiente (.env) para
permitir trocar SQLite por Postgres no futuro sem mudar codigo (secao 16-17)."""

from __future__ import annotations

import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker

from db.models import Base

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///nosso_valuation.db")

_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=_connect_args)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

# Colunas adicionadas apos a criacao inicial da tabela `valuations` -
# `create_all` so cria tabelas novas, nunca altera as existentes. Como o
# projeto nao usa um framework de migracao (ex.: Alembic), fazemos aqui um
# ALTER TABLE ADD COLUMN idempotente e minimo so para bancos SQLite ja
# existentes. Se uma coluna nova for adicionada ao modelo `Valuation` no
# futuro, adicionar a definicao dela tambem nesta lista.
_COLUNAS_NOVAS_VALUATIONS = (
    ("model_version", "VARCHAR NOT NULL DEFAULT '1.0.0'"),
    ("growth_mode", "VARCHAR NOT NULL DEFAULT 'manual'"),
    ("taxa_desconto_manual_override", "BOOLEAN NOT NULL DEFAULT 0"),
    ("taxa_desconto_original_automatico", "NUMERIC"),
    ("ll_ano_base_manual_override", "BOOLEAN NOT NULL DEFAULT 0"),
    ("ll_ano_base_original_fonte", "NUMERIC"),
    ("roe", "NUMERIC"),
    ("payout", "NUMERIC"),
)


def _migrar_colunas_novas() -> None:
    if not DATABASE_URL.startswith("sqlite"):
        return
    inspector = inspect(engine)
    if "valuations" not in inspector.get_table_names():
        return
    colunas_existentes = {col["name"] for col in inspector.get_columns("valuations")}
    with engine.begin() as conn:
        for nome, definicao_sql in _COLUNAS_NOVAS_VALUATIONS:
            if nome not in colunas_existentes:
                conn.execute(text(f"ALTER TABLE valuations ADD COLUMN {nome} {definicao_sql}"))


def criar_tabelas() -> None:
    Base.metadata.create_all(engine)
    _migrar_colunas_novas()


def get_session() -> Session:
    return SessionLocal()
