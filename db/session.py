"""Engine/sessionmaker do banco. Le DATABASE_URL do ambiente (.env) para
permitir trocar SQLite por Postgres no futuro sem mudar codigo (secao 16-17)."""

from __future__ import annotations

import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from db.models import Base

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///nosso_valuation.db")

_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=_connect_args)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def criar_tabelas() -> None:
    Base.metadata.create_all(engine)


def get_session() -> Session:
    return SessionLocal()
