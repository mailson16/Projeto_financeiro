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


def test_montar_premissas_sugeridas_growth_mode_automatico_via_roe_payout(session):
    empresa = market_data_service.atualizar_dados_ativo(session, "BRBI11")
    from datetime import date as date_cls

    repo.salvar_indicador(
        session,
        empresa,
        date_cls.today(),
        payout=Decimal("0.70"),
        roe=Decimal("0.20"),
        patrimonio_liquido=None,
        lpa=None,
        fonte="fake",
        data_atualizacao=datetime.now(timezone.utc),
    )

    premissas = valuation_service.montar_premissas_sugeridas(session, empresa)

    assert premissas.growth_mode == "automatic"
    assert premissas.taxa_crescimento == Decimal("0.06")  # ROE(0.20) x (1-Payout(0.70))
    assert premissas.roe == Decimal("0.20")
    assert premissas.payout == Decimal("0.70")


def test_montar_premissas_sugeridas_carrega_roe_payout_manuais_do_ultimo_salvo(session):
    """Modo manual: o usuario informa ROE/Payout (nao a taxa de crescimento
    pronta) - a proxima sugestao deve reaproveitar esses dois valores, nao
    so o `taxa_crescimento` ja calculado."""
    from valuation.engine import calcular_crescimento_sustentavel, rodar_valuation

    empresa = market_data_service.atualizar_dados_ativo(session, "BRBI11")
    cliente = client_service.criar_cliente(session, "Fulano de Tal")

    premissas_1 = valuation_service.montar_premissas_sugeridas(session, empresa, cliente)
    roe_manual = Decimal("0.22")
    payout_manual = Decimal("0.65")
    premissas_manual = premissas_1.__class__(
        **{
            **premissas_1.__dict__,
            "growth_mode": "manual",
            "taxa_crescimento": calcular_crescimento_sustentavel(roe_manual, payout_manual),
            "roe": roe_manual,
            "payout": payout_manual,
        }
    )
    valuation_service.salvar_valuation(
        session, empresa, rodar_valuation(premissas_manual), cenario="custom", cliente=cliente
    )

    premissas_2 = valuation_service.montar_premissas_sugeridas(session, empresa, cliente)

    assert premissas_2.growth_mode == "manual"
    assert premissas_2.roe == roe_manual
    assert premissas_2.payout == payout_manual
    assert premissas_2.taxa_crescimento == calcular_crescimento_sustentavel(roe_manual, payout_manual)


def test_premissas_do_valuation_salvo_reconstroi_igual_ao_original(session):
    """Cenarios/Sensibilidade/Explicacao devem operar sobre o valuation
    salvo, nao uma sugestao nova - `premissas_do_valuation_salvo` precisa
    reproduzir exatamente as premissas usadas naquele calculo."""
    from valuation.engine import rodar_valuation

    empresa = market_data_service.atualizar_dados_ativo(session, "BRBI11")
    premissas = valuation_service.montar_premissas_sugeridas(session, empresa)
    premissas_manual = premissas.__class__(
        **{
            **premissas.__dict__,
            "taxa_desconto": Decimal("0.11"),
            "taxa_desconto_manual_override": True,
            "roe": Decimal("0.20"),
            "payout": Decimal("0.70"),
        }
    )
    resultado_original = rodar_valuation(premissas_manual)
    salvo = valuation_service.salvar_valuation(session, empresa, resultado_original, cenario="custom")

    premissas_reconstruidas = valuation_service.premissas_do_valuation_salvo(salvo)
    resultado_reconstruido = rodar_valuation(premissas_reconstruidas)

    # Coluna Numeric persiste com precisao finita (10 casas) - compara com tolerancia de centavos.
    assert abs(resultado_reconstruido.preco_justo - resultado_original.preco_justo) < Decimal("0.01")
    assert premissas_reconstruidas.roe == Decimal("0.20")
    assert premissas_reconstruidas.payout == Decimal("0.70")
    assert premissas_reconstruidas.taxa_desconto_manual_override is True


def test_montar_premissas_sugeridas_nao_sobrescreve_taxa_desconto_manual_anterior(session, monkeypatch):
    """Secao 52 do SKILL.md: uma taxa de desconto alterada manualmente em um
    valuation salvo nao deve ser substituida silenciosamente pela Selic
    atualizada na proxima sugestao de premissas para o mesmo (empresa,
    cliente)."""
    from valuation.engine import rodar_valuation

    empresa = market_data_service.atualizar_dados_ativo(session, "BRBI11")
    cliente = client_service.criar_cliente(session, "Fulano de Tal")

    premissas_1 = valuation_service.montar_premissas_sugeridas(session, empresa, cliente)
    assert premissas_1.taxa_desconto == Decimal("0.14")  # Selic mockada no fixture
    assert premissas_1.taxa_desconto_manual_override is False

    premissas_manual = premissas_1.__class__(
        **{**premissas_1.__dict__, "taxa_desconto": Decimal("0.11"), "taxa_desconto_manual_override": True}
    )
    valuation_service.salvar_valuation(
        session, empresa, rodar_valuation(premissas_manual), cenario="custom", cliente=cliente
    )

    # Selic "sobe" para 0.18 - a sugestao NAO deve adotar esse novo valor
    # automaticamente, porque o usuario tinha um override manual salvo.
    monkeypatch.setattr(market_data_service, "obter_selic_para_taxa_desconto", lambda: Decimal("0.18"))

    premissas_2 = valuation_service.montar_premissas_sugeridas(session, empresa, cliente)

    assert premissas_2.taxa_desconto == Decimal("0.11")
    assert premissas_2.taxa_desconto_manual_override is True
    assert premissas_2.taxa_desconto_original_automatico == Decimal("0.18")


def test_montar_premissas_sugeridas_nao_sobrescreve_ll_base_manual_anterior(session):
    from valuation.engine import rodar_valuation

    empresa = market_data_service.atualizar_dados_ativo(session, "BRBI11")
    cliente = client_service.criar_cliente(session, "Fulano de Tal")

    premissas_1 = valuation_service.montar_premissas_sugeridas(session, empresa, cliente)
    ll_fonte = premissas_1.ll_ano_base

    premissas_manual = premissas_1.__class__(
        **{
            **premissas_1.__dict__,
            "ll_ano_base": Decimal("999999999"),
            "ll_ano_base_manual_override": True,
        }
    )
    valuation_service.salvar_valuation(
        session, empresa, rodar_valuation(premissas_manual), cenario="custom", cliente=cliente
    )

    premissas_2 = valuation_service.montar_premissas_sugeridas(session, empresa, cliente)

    assert premissas_2.ll_ano_base == Decimal("999999999")
    assert premissas_2.ll_ano_base_manual_override is True
    assert premissas_2.ll_ano_base_original_fonte == ll_fonte


def test_montar_premissas_sugeridas_nao_sobrescreve_growth_mode_manual_anterior(session):
    from valuation.engine import rodar_valuation

    empresa = market_data_service.atualizar_dados_ativo(session, "BRBI11")
    cliente = client_service.criar_cliente(session, "Fulano de Tal")

    premissas_1 = valuation_service.montar_premissas_sugeridas(session, empresa, cliente)

    premissas_manual = premissas_1.__class__(
        **{**premissas_1.__dict__, "taxa_crescimento": Decimal("0.30"), "growth_mode": "manual"}
    )
    valuation_service.salvar_valuation(
        session, empresa, rodar_valuation(premissas_manual), cenario="custom", cliente=cliente
    )

    premissas_2 = valuation_service.montar_premissas_sugeridas(session, empresa, cliente)

    assert premissas_2.growth_mode == "manual"
    assert premissas_2.taxa_crescimento == Decimal("0.30")


def test_salvar_valuation_persiste_model_version_e_campos_de_override(session):
    from valuation.constants import MODEL_VERSION
    from valuation.engine import rodar_valuation

    empresa = market_data_service.atualizar_dados_ativo(session, "BRBI11")
    premissas = valuation_service.montar_premissas_sugeridas(session, empresa)
    premissas_manual = premissas.__class__(
        **{**premissas.__dict__, "taxa_desconto": Decimal("0.11"), "taxa_desconto_manual_override": True}
    )

    salvo = valuation_service.salvar_valuation(session, empresa, rodar_valuation(premissas_manual), cenario="custom")

    assert salvo.model_version == MODEL_VERSION
    assert salvo.taxa_desconto_manual_override is True
    assert salvo.growth_mode == premissas_manual.growth_mode


def test_watchlist_cliente_com_ativo_novo_dispara_busca_de_dados(session):
    cliente = client_service.criar_cliente(session, "Fulano de Tal")
    empresa = client_service.adicionar_ativo_watchlist(session, cliente, "brbi11")

    assert empresa.ticker == "BRBI11"
    assert repo.obter_cotacao_mais_recente(session, empresa) is None  # so cadastra; busca e um passo separado

    market_data_service.atualizar_dados_ativo(session, empresa.ticker)
    assert repo.obter_cotacao_mais_recente(session, empresa) is not None

    watchlist = client_service.listar_watchlist(session, cliente)
    assert [e.ticker for e in watchlist] == ["BRBI11"]
