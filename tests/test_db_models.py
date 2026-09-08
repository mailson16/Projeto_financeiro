from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

import db.repository as repo
from db.models import Base, Valuation


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


def test_get_or_create_empresa_e_idempotente(session):
    e1 = repo.get_or_create_empresa(session, "BRBI11", nome="BR Partners")
    e2 = repo.get_or_create_empresa(session, "BRBI11")
    assert e1.id == e2.id
    assert e2.nome == "BR Partners"


def test_salvar_cotacao_upsert_por_empresa_e_data(session):
    empresa = repo.get_or_create_empresa(session, "TAEE4")
    agora = datetime.now(timezone.utc)

    repo.salvar_cotacao(session, empresa, date(2026, 1, 1), Decimal("12.75"), Decimal("1000"), None, "brapi.dev", agora)
    repo.salvar_cotacao(session, empresa, date(2026, 1, 1), Decimal("13.00"), Decimal("1000"), None, "brapi.dev", agora)

    cotacao = repo.obter_cotacao_mais_recente(session, empresa)
    assert cotacao.preco == Decimal("13.00")

    todas = session.query(type(cotacao)).all()
    assert len(todas) == 1  # upsert, nao duplicou


def test_constraint_unica_resultado_financeiro_impede_duplicata_direta(session):
    # Usa trimestre != NULL de proposito: em SQL, colunas NULL nunca sao
    # consideradas iguais entre si, entao uma UNIQUE constraint que inclua
    # uma coluna NULL (ex.: `trimestre` em resultados anuais) nao barra
    # duplicatas no nivel do banco - por isso `repo.salvar_resultado_financeiro`
    # faz upsert checando primeiro na aplicacao (ver teste seguinte).
    from db.models import ResultadoFinanceiro

    empresa = repo.get_or_create_empresa(session, "BRBI11")
    r1 = ResultadoFinanceiro(
        empresa_id=empresa.id,
        ano=2025,
        trimestre=1,
        lucro_liquido=Decimal("175073000"),
        tipo_metrica="contabil",
        fonte="teste",
    )
    session.add(r1)
    session.commit()

    r2 = ResultadoFinanceiro(
        empresa_id=empresa.id,
        ano=2025,
        trimestre=1,
        lucro_liquido=Decimal("999"),
        tipo_metrica="contabil",
        fonte="teste",
    )
    session.add(r2)
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_salvar_resultado_financeiro_faz_upsert(session):
    empresa = repo.get_or_create_empresa(session, "BRBI11")
    agora = datetime.now(timezone.utc)

    repo.salvar_resultado_financeiro(session, empresa, 2025, Decimal("175073000"), "brapi.dev", agora)
    repo.salvar_resultado_financeiro(session, empresa, 2025, Decimal("180000000"), "brapi.dev", agora)

    resultados = repo.listar_resultados_financeiros(session, empresa)
    assert len(resultados) == 1
    assert resultados[0].lucro_liquido == Decimal("180000000")


def test_cliente_watchlist_crud(session):
    cliente = repo.criar_cliente(session, "Fulano de Tal", email="fulano@example.com")
    brbi = repo.get_or_create_empresa(session, "BRBI11")
    taee = repo.get_or_create_empresa(session, "TAEE4")

    repo.adicionar_ativo_watchlist(session, cliente, brbi)
    repo.adicionar_ativo_watchlist(session, cliente, taee)
    repo.adicionar_ativo_watchlist(session, cliente, brbi)  # idempotente

    watchlist = repo.listar_watchlist_cliente(session, cliente)
    assert {e.ticker for e in watchlist} == {"BRBI11", "TAEE4"}

    repo.remover_ativo_watchlist(session, cliente, brbi)
    watchlist = repo.listar_watchlist_cliente(session, cliente)
    assert {e.ticker for e in watchlist} == {"TAEE4"}


def test_salvar_valuation_grava_periodos_desconto_perpetuidade_explicitamente(session):
    empresa = repo.get_or_create_empresa(session, "BRBI11")
    valuation = Valuation(
        empresa_id=empresa.id,
        cenario="base",
        ll_ano_base=Decimal("182321022.20"),
        taxa_crescimento=Decimal("0.0414"),
        taxa_desconto=Decimal("0.14"),
        crescimento_perpetuidade=Decimal("0.03"),
        anos_projecao=3,
        periodos_desconto_perpetuidade=Decimal("3"),
        numero_acoes=Decimal("314987112"),
        preco_atual_usado=Decimal("12.43"),
        margem_seguranca=Decimal("0.20"),
        valor_estimado=Decimal("1689179554.12"),
        preco_justo=Decimal("5.36"),
        upside=Decimal("-0.5686"),
        preco_entrada=Decimal("4.29"),
    )
    repo.salvar_valuation(session, valuation)

    salvos = repo.listar_valuations_empresa(session, empresa)
    assert len(salvos) == 1
    assert salvos[0].periodos_desconto_perpetuidade == Decimal("3")


def _novo_valuation(empresa_id, cliente_id=None, preco_justo=Decimal("5.36")):
    return Valuation(
        empresa_id=empresa_id,
        cliente_id=cliente_id,
        cenario="base",
        ll_ano_base=Decimal("182321022.20"),
        taxa_crescimento=Decimal("0.0414"),
        taxa_desconto=Decimal("0.14"),
        crescimento_perpetuidade=Decimal("0.03"),
        anos_projecao=3,
        periodos_desconto_perpetuidade=Decimal("3"),
        numero_acoes=Decimal("314987112"),
        preco_atual_usado=Decimal("12.43"),
        margem_seguranca=Decimal("0.20"),
        valor_estimado=Decimal("1689179554.12"),
        preco_justo=preco_justo,
        upside=Decimal("-0.5686"),
        preco_entrada=Decimal("4.29"),
    )


def test_obter_valuation_mais_recente_retorna_o_ultimo_salvo(session):
    empresa = repo.get_or_create_empresa(session, "BRBI11")
    cliente = repo.criar_cliente(session, "Fulano de Tal")

    repo.salvar_valuation(session, _novo_valuation(empresa.id, cliente.id, preco_justo=Decimal("5.36")))
    repo.salvar_valuation(session, _novo_valuation(empresa.id, cliente.id, preco_justo=Decimal("17.43")))

    ultimo = repo.obter_valuation_mais_recente(session, empresa, cliente)
    assert ultimo.preco_justo == Decimal("17.43")


def test_obter_valuation_mais_recente_filtra_por_cliente(session):
    empresa = repo.get_or_create_empresa(session, "BRBI11")
    cliente_a = repo.criar_cliente(session, "Cliente A")
    cliente_b = repo.criar_cliente(session, "Cliente B")

    repo.salvar_valuation(session, _novo_valuation(empresa.id, cliente_a.id, preco_justo=Decimal("10.00")))

    assert repo.obter_valuation_mais_recente(session, empresa, cliente_b) is None
    assert repo.obter_valuation_mais_recente(session, empresa, cliente_a).preco_justo == Decimal("10.00")


def test_obter_valuation_mais_recente_sem_cliente_nenhum_salvo_retorna_none(session):
    empresa = repo.get_or_create_empresa(session, "BRBI11")
    cliente = repo.criar_cliente(session, "Fulano de Tal")

    assert repo.obter_valuation_mais_recente(session, empresa, cliente) is None


def test_excluir_valuations_apaga_so_do_par_empresa_cliente_informado(session):
    empresa = repo.get_or_create_empresa(session, "BRBI11")
    outra_empresa = repo.get_or_create_empresa(session, "TAEE4")
    cliente = repo.criar_cliente(session, "Fulano de Tal")

    repo.salvar_valuation(session, _novo_valuation(empresa.id, cliente.id))
    repo.salvar_valuation(session, _novo_valuation(outra_empresa.id, cliente.id))
    repo.salvar_valuation(session, _novo_valuation(empresa.id, cliente_id=None))

    repo.excluir_valuations(session, empresa, cliente)
    session.commit()

    assert repo.listar_valuations_empresa(session, empresa)  # sobrou o de cliente_id=None
    assert len(repo.listar_valuations_empresa(session, outra_empresa)) == 1
    assert repo.obter_valuation_mais_recente(session, empresa, cliente) is None
    assert repo.obter_valuation_mais_recente(session, empresa, None) is not None


def test_excluir_valuations_sem_cliente_apaga_so_os_registros_sem_cliente(session):
    empresa = repo.get_or_create_empresa(session, "BRBI11")
    cliente = repo.criar_cliente(session, "Fulano de Tal")

    repo.salvar_valuation(session, _novo_valuation(empresa.id, cliente.id))
    repo.salvar_valuation(session, _novo_valuation(empresa.id, cliente_id=None))

    repo.excluir_valuations(session, empresa, cliente=None)
    session.commit()

    assert repo.obter_valuation_mais_recente(session, empresa, cliente) is not None
    assert repo.obter_valuation_mais_recente(session, empresa, None) is None
