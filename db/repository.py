"""Unica camada que fala SQL/ORM diretamente - `services/` so chama estas funcoes.

Funcoes de "salvar" fazem upsert (por chave unica) e sempre gravam
`fonte` + `data_atualizacao` quando aplicavel.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from db.models import Cliente, ClienteAtivo, CotacaoMercado, Dividendo, Empresa, Indicador, ResultadoFinanceiro, Valuation


# --- Empresa ---


def get_or_create_empresa(
    session: Session,
    ticker: str,
    nome: Optional[str] = None,
    setor: Optional[str] = None,
    tipo_ativo: Optional[str] = None,
) -> Empresa:
    empresa = session.scalar(select(Empresa).where(Empresa.ticker == ticker))
    if empresa is None:
        empresa = Empresa(ticker=ticker, nome=nome or ticker, setor=setor, tipo_ativo=tipo_ativo)
        session.add(empresa)
        session.commit()
    return empresa


def listar_empresas(session: Session) -> List[Empresa]:
    return list(session.scalars(select(Empresa).order_by(Empresa.ticker)))


# --- Cotacao de mercado ---


def salvar_cotacao(
    session: Session,
    empresa: Empresa,
    data: date,
    preco: Decimal,
    numero_acoes: Decimal,
    market_cap: Optional[Decimal],
    fonte: str,
    data_atualizacao: datetime,
) -> CotacaoMercado:
    cotacao = session.scalar(
        select(CotacaoMercado).where(CotacaoMercado.empresa_id == empresa.id, CotacaoMercado.data == data)
    )
    if cotacao is None:
        cotacao = CotacaoMercado(empresa_id=empresa.id, data=data)
        session.add(cotacao)

    cotacao.preco = preco
    cotacao.numero_acoes = numero_acoes
    cotacao.market_cap = market_cap
    cotacao.fonte = fonte
    cotacao.data_atualizacao = data_atualizacao
    session.commit()
    return cotacao


def obter_cotacao_mais_recente(session: Session, empresa: Empresa) -> Optional[CotacaoMercado]:
    return session.scalar(
        select(CotacaoMercado)
        .where(CotacaoMercado.empresa_id == empresa.id)
        .order_by(CotacaoMercado.data.desc())
        .limit(1)
    )


# --- Indicadores ---


def salvar_indicador(
    session: Session,
    empresa: Empresa,
    data: date,
    payout: Optional[Decimal],
    roe: Optional[Decimal],
    patrimonio_liquido: Optional[Decimal],
    lpa: Optional[Decimal],
    fonte: str,
    data_atualizacao: datetime,
) -> Indicador:
    indicador = session.scalar(
        select(Indicador).where(Indicador.empresa_id == empresa.id, Indicador.data == data)
    )
    if indicador is None:
        indicador = Indicador(empresa_id=empresa.id, data=data)
        session.add(indicador)

    indicador.payout = payout
    indicador.roe = roe
    indicador.patrimonio_liquido = patrimonio_liquido
    indicador.lpa = lpa
    indicador.fonte = fonte
    indicador.data_atualizacao = data_atualizacao
    session.commit()
    return indicador


def obter_indicador_mais_recente(session: Session, empresa: Empresa) -> Optional[Indicador]:
    return session.scalar(
        select(Indicador).where(Indicador.empresa_id == empresa.id).order_by(Indicador.data.desc()).limit(1)
    )


# --- Resultados financeiros (LL historico) ---


def salvar_resultado_financeiro(
    session: Session,
    empresa: Empresa,
    ano: int,
    lucro_liquido: Decimal,
    fonte: str,
    data_atualizacao: datetime,
    trimestre: Optional[int] = None,
    crescimento: Optional[Decimal] = None,
    tipo_metrica: str = "contabil",
) -> ResultadoFinanceiro:
    resultado = session.scalar(
        select(ResultadoFinanceiro).where(
            ResultadoFinanceiro.empresa_id == empresa.id,
            ResultadoFinanceiro.ano == ano,
            ResultadoFinanceiro.trimestre == trimestre,
            ResultadoFinanceiro.tipo_metrica == tipo_metrica,
        )
    )
    if resultado is None:
        resultado = ResultadoFinanceiro(
            empresa_id=empresa.id, ano=ano, trimestre=trimestre, tipo_metrica=tipo_metrica
        )
        session.add(resultado)

    resultado.lucro_liquido = lucro_liquido
    resultado.crescimento = crescimento
    resultado.fonte = fonte
    resultado.data_atualizacao = data_atualizacao
    session.commit()
    return resultado


def listar_resultados_financeiros(
    session: Session, empresa: Empresa, tipo_metrica: str = "contabil"
) -> List[ResultadoFinanceiro]:
    return list(
        session.scalars(
            select(ResultadoFinanceiro)
            .where(ResultadoFinanceiro.empresa_id == empresa.id, ResultadoFinanceiro.tipo_metrica == tipo_metrica)
            .order_by(ResultadoFinanceiro.ano)
        )
    )


# --- Dividendos ---


def salvar_dividendo(
    session: Session,
    empresa: Empresa,
    data: date,
    valor: Decimal,
    tipo: str,
    fonte: str,
    data_atualizacao: datetime,
) -> Dividendo:
    dividendo = Dividendo(
        empresa_id=empresa.id,
        data=data,
        valor=valor,
        tipo=tipo,
        fonte=fonte,
        data_atualizacao=data_atualizacao,
    )
    session.add(dividendo)
    session.commit()
    return dividendo


# --- Valuations ---


def excluir_valuations(session: Session, empresa: Empresa, cliente: Optional[Cliente] = None) -> None:
    """Remove os valuations salvos anteriormente para (empresa, cliente).

    Sem commit proprio de proposito: `salvar_valuation` chama isso e depois
    adiciona o novo registro, commitando os dois juntos - evita uma janela
    em que o valuation antigo ja foi apagado mas o novo ainda nao foi salvo.
    """
    condicoes = [Valuation.empresa_id == empresa.id]
    condicoes.append(Valuation.cliente_id == cliente.id if cliente is not None else Valuation.cliente_id.is_(None))
    for valuation in session.scalars(select(Valuation).where(*condicoes)):
        session.delete(valuation)


def salvar_valuation(session: Session, valuation: Valuation) -> Valuation:
    session.add(valuation)
    session.commit()
    return valuation


def listar_valuations_empresa(session: Session, empresa: Empresa) -> List[Valuation]:
    return list(
        session.scalars(
            select(Valuation)
            .where(Valuation.empresa_id == empresa.id)
            .order_by(Valuation.data_calculo.desc(), Valuation.id.desc())
        )
    )


def listar_valuations_cliente(session: Session, cliente: Cliente) -> List[Valuation]:
    return list(
        session.scalars(
            select(Valuation)
            .where(Valuation.cliente_id == cliente.id)
            .order_by(Valuation.data_calculo.desc(), Valuation.id.desc())
        )
    )


def obter_valuation_mais_recente(
    session: Session, empresa: Empresa, cliente: Optional[Cliente] = None
) -> Optional[Valuation]:
    # Desempate por id: `data_calculo` pode colidir quando dois valuations
    # sao salvos em sequencia rapida (a precisao do datetime armazenado no
    # SQLite nao e suficiente pra distingui-los) - id autoincrement garante
    # que o "mais recente" seja sempre determinístico.
    #
    # cliente=None filtra por `cliente_id IS NULL` (mesma semantica de
    # `excluir_valuations`) - NAO significa "qualquer cliente". Chamar sem
    # cliente para um ativo que esta na watchlist de varios clientes nao
    # deve "vazar" o valuation salvo por outro cliente.
    condicoes = [Valuation.empresa_id == empresa.id]
    condicoes.append(Valuation.cliente_id == cliente.id if cliente is not None else Valuation.cliente_id.is_(None))
    return session.scalar(
        select(Valuation)
        .where(*condicoes)
        .order_by(Valuation.data_calculo.desc(), Valuation.id.desc())
        .limit(1)
    )


# --- Clientes e watchlist ---


def criar_cliente(
    session: Session,
    nome: str,
    email: Optional[str] = None,
    telefone: Optional[str] = None,
    observacoes: Optional[str] = None,
) -> Cliente:
    cliente = Cliente(nome=nome, email=email, telefone=telefone, observacoes=observacoes)
    session.add(cliente)
    session.commit()
    return cliente


def listar_clientes(session: Session) -> List[Cliente]:
    return list(session.scalars(select(Cliente).order_by(Cliente.nome)))


def remover_cliente(session: Session, cliente: Cliente) -> None:
    session.delete(cliente)
    session.commit()


def adicionar_ativo_watchlist(session: Session, cliente: Cliente, empresa: Empresa) -> ClienteAtivo:
    vinculo = session.scalar(
        select(ClienteAtivo).where(
            ClienteAtivo.cliente_id == cliente.id, ClienteAtivo.empresa_id == empresa.id
        )
    )
    if vinculo is None:
        vinculo = ClienteAtivo(cliente_id=cliente.id, empresa_id=empresa.id)
        session.add(vinculo)
        session.commit()
    return vinculo


def remover_ativo_watchlist(session: Session, cliente: Cliente, empresa: Empresa) -> None:
    vinculo = session.scalar(
        select(ClienteAtivo).where(
            ClienteAtivo.cliente_id == cliente.id, ClienteAtivo.empresa_id == empresa.id
        )
    )
    if vinculo is not None:
        session.delete(vinculo)
        session.commit()


def listar_watchlist_cliente(session: Session, cliente: Cliente) -> List[Empresa]:
    return list(
        session.scalars(
            select(Empresa)
            .join(ClienteAtivo, ClienteAtivo.empresa_id == Empresa.id)
            .where(ClienteAtivo.cliente_id == cliente.id)
            .order_by(Empresa.ticker)
        )
    )
