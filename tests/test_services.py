from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import db.repository as repo
import services.client_service as client_service
import services.market_data_service as market_data_service
import services.valuation_service as valuation_service
from data.dto import CotacaoDTO, DadoComFonte, IndicadoresDTO, LucroLiquidoDTO
from db.models import Base


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


class ProvedorFake:
    """Dublê de ProvedorFundamentalista com dados fixos, sem rede."""

    nome = "fake"

    def obter_cotacao(self, ticker):
        return DadoComFonte(
            valor=CotacaoDTO(ticker=ticker, preco=Decimal("12.43"), numero_acoes=Decimal("314987112")),
            fonte=self.nome,
            data_atualizacao=datetime.now(timezone.utc),
        )

    def obter_indicadores(self, ticker):
        return DadoComFonte(
            valor=IndicadoresDTO(ticker=ticker, data=date.today(), roe=Decimal("0.197")),
            fonte=self.nome,
            data_atualizacao=datetime.now(timezone.utc),
        )

    def obter_lucro_liquido_historico(self, ticker):
        agora = datetime.now(timezone.utc)
        anos = [
            (2023, Decimal("155084000")),
            (2024, Decimal("193670000")),
            (2025, Decimal("175073000")),
        ]
        return [
            DadoComFonte(valor=LucroLiquidoDTO(ticker=ticker, ano=ano, lucro_liquido=ll), fonte=self.nome, data_atualizacao=agora)
            for ano, ll in anos
        ]


@pytest.fixture(autouse=True)
def usar_provedor_fake(monkeypatch):
    monkeypatch.setattr(market_data_service, "PROVEDORES_FUNDAMENTALISTA", [ProvedorFake()])
    # Evita chamada de rede real a Selic nos testes - determinismo e velocidade.
    monkeypatch.setattr(market_data_service, "obter_selic_para_taxa_desconto", lambda: Decimal("0.14"))


def test_atualizar_dados_ativo_popula_cotacao_indicadores_e_historico(session):
    empresa = market_data_service.atualizar_dados_ativo(session, "BRBI11")

    cotacao = repo.obter_cotacao_mais_recente(session, empresa)
    assert cotacao.preco == Decimal("12.43")
    assert cotacao.fonte == "fake"

    indicador = repo.obter_indicador_mais_recente(session, empresa)
    assert indicador.roe == Decimal("0.197")

    resultados = repo.listar_resultados_financeiros(session, empresa)
    assert [r.ano for r in resultados] == [2023, 2024, 2025]
    # Crescimento calculado em relacao ao ano anterior (o primeiro ano nao tem base de comparacao)
    assert resultados[0].crescimento is None
    assert resultados[-1].crescimento is not None


def test_atualizar_dados_ativo_nao_rebusca_se_dado_estiver_fresco(session, monkeypatch):
    chamadas = {"cotacao": 0}
    provedor = ProvedorFake()
    original = provedor.obter_cotacao

    def contando(ticker):
        chamadas["cotacao"] += 1
        return original(ticker)

    provedor.obter_cotacao = contando
    monkeypatch.setattr(market_data_service, "PROVEDORES_FUNDAMENTALISTA", [provedor])

    market_data_service.atualizar_dados_ativo(session, "BRBI11")
    market_data_service.atualizar_dados_ativo(session, "BRBI11")

    assert chamadas["cotacao"] == 1


def test_ticket_novo_ate_valuation_salvo_fluxo_completo(session):
    empresa = market_data_service.atualizar_dados_ativo(session, "BRBI11")

    premissas = valuation_service.montar_premissas_sugeridas(session, empresa)
    # LL ano-base = ultimo ano fechado (2025) projetado pela taxa de crescimento
    # media historica (secao 7 do doc) - nao o valor bruto do ultimo ano.
    resultados = repo.listar_resultados_financeiros(session, empresa)
    crescimentos = [r.crescimento for r in resultados if r.crescimento is not None]
    taxa_crescimento_esperada = sum(crescimentos, Decimal("0")) / len(crescimentos)
    ll_ano_base_esperado = Decimal("175073000") * (Decimal("1") + taxa_crescimento_esperada)
    assert abs(premissas.ll_ano_base - ll_ano_base_esperado) < Decimal("0.01")
    assert premissas.numero_acoes == Decimal("314987112")

    from valuation.engine import rodar_valuation

    resultado = rodar_valuation(premissas)

    valuation_salvo = valuation_service.salvar_valuation(session, empresa, resultado, cenario="base")

    assert valuation_salvo.id is not None
    # Coluna Numeric persiste com precisao finita (10 casas) - compara com tolerancia de centavos.
    assert abs(valuation_salvo.preco_justo - resultado.preco_justo) < Decimal("0.01")
    assert valuation_salvo.periodos_desconto_perpetuidade == resultado.periodos_desconto_perpetuidade_usado


def test_salvar_valuation_mantem_so_o_mais_recente_para_empresa_e_cliente(session):
    from valuation.engine import rodar_valuation

    empresa = market_data_service.atualizar_dados_ativo(session, "BRBI11")
    cliente = client_service.criar_cliente(session, "Fulano de Tal")

    premissas = valuation_service.montar_premissas_sugeridas(session, empresa)
    resultado1 = rodar_valuation(premissas)
    primeiro = valuation_service.salvar_valuation(session, empresa, resultado1, cenario="custom", cliente=cliente)
    primeiro_id = primeiro.id

    resultado2 = rodar_valuation(premissas)
    segundo = valuation_service.salvar_valuation(session, empresa, resultado2, cenario="custom", cliente=cliente)

    salvos = repo.listar_valuations_empresa(session, empresa)
    assert len(salvos) == 1
    assert salvos[0].id == segundo.id
    assert repo.obter_valuation_mais_recente(session, empresa, cliente).id == segundo.id

    # o registro antigo nao fica so "escondido" - foi mesmo apagado do banco
    from db.models import Valuation

    assert session.get(Valuation, primeiro_id) is None


def test_salvar_valuation_nao_apaga_valuation_de_outra_empresa_ou_outro_cliente(session):
    from valuation.engine import rodar_valuation

    empresa_a = market_data_service.atualizar_dados_ativo(session, "BRBI11")
    empresa_b = market_data_service.atualizar_dados_ativo(session, "TAEE4")
    cliente_x = client_service.criar_cliente(session, "Cliente X")
    cliente_y = client_service.criar_cliente(session, "Cliente Y")

    premissas_a = valuation_service.montar_premissas_sugeridas(session, empresa_a)
    premissas_b = valuation_service.montar_premissas_sugeridas(session, empresa_b)

    valuation_service.salvar_valuation(session, empresa_a, rodar_valuation(premissas_a), cliente=cliente_x)
    valuation_service.salvar_valuation(session, empresa_b, rodar_valuation(premissas_b), cliente=cliente_x)
    valuation_service.salvar_valuation(session, empresa_a, rodar_valuation(premissas_a), cliente=cliente_y)

    assert repo.obter_valuation_mais_recente(session, empresa_a, cliente_x) is not None
    assert repo.obter_valuation_mais_recente(session, empresa_b, cliente_x) is not None
    assert repo.obter_valuation_mais_recente(session, empresa_a, cliente_y) is not None


def test_watchlist_cliente_com_ativo_novo_dispara_busca_de_dados(session):
    cliente = client_service.criar_cliente(session, "Fulano de Tal")
    empresa = client_service.adicionar_ativo_watchlist(session, cliente, "brbi11")

    assert empresa.ticker == "BRBI11"
    assert repo.obter_cotacao_mais_recente(session, empresa) is None  # so cadastra; busca e um passo separado

    market_data_service.atualizar_dados_ativo(session, empresa.ticker)
    assert repo.obter_cotacao_mais_recente(session, empresa) is not None

    watchlist = client_service.listar_watchlist(session, cliente)
    assert [e.ticker for e in watchlist] == ["BRBI11"]
