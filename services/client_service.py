"""CRUD de Cliente e watchlist - usado pelas paginas Streamlit de Clientes/Watchlist."""

from __future__ import annotations

from typing import List, Optional

from sqlalchemy.orm import Session

import db.repository as repo
from db.models import Cliente, Empresa


def criar_cliente(
    session: Session,
    nome: str,
    email: Optional[str] = None,
    telefone: Optional[str] = None,
    observacoes: Optional[str] = None,
) -> Cliente:
    return repo.criar_cliente(session, nome=nome, email=email, telefone=telefone, observacoes=observacoes)


def listar_clientes(session: Session) -> List[Cliente]:
    return repo.listar_clientes(session)


def remover_cliente(session: Session, cliente: Cliente) -> None:
    repo.remover_cliente(session, cliente)


def adicionar_ativo_watchlist(session: Session, cliente: Cliente, ticker: str) -> Empresa:
    empresa = repo.get_or_create_empresa(session, ticker.upper())
    repo.adicionar_ativo_watchlist(session, cliente, empresa)
    return empresa


def remover_ativo_watchlist(session: Session, cliente: Cliente, empresa: Empresa) -> None:
    repo.remover_ativo_watchlist(session, cliente, empresa)


def listar_watchlist(session: Session, cliente: Cliente) -> List[Empresa]:
    return repo.listar_watchlist_cliente(session, cliente)
