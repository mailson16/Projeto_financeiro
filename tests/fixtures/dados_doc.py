"""Constantes literais extraidas de nosso_valuation_aprendizado.md (secoes 6-11 e 19).

Usadas para validar o motor de valuation contra os exemplos estudados de
BRBI11 e TAEE4. Ver a nota em tests/test_engine.py sobre quais partes
devem bater exatamente com o doc e quais divergem intencionalmente
(convencao de desconto da perpetuidade).
"""

from decimal import Decimal

# --- BRBI11 (secoes 7, 8, 9, 19) ---

BRBI11_LL_ANO_BASE = Decimal("182321022.20")  # LL 2026
BRBI11_TAXA_CRESCIMENTO = Decimal("0.0414")
BRBI11_TAXA_DESCONTO = Decimal("0.14")
BRBI11_CRESCIMENTO_PERPETUIDADE = Decimal("0.03")
BRBI11_ANOS_PROJECAO = 3
BRBI11_NUMERO_ACOES = Decimal("314987112")
BRBI11_PRECO_ATUAL = Decimal("12.43")

# LL projetado esperado (secao 7) - LL 2026 e o proprio ano-base, LL futuro = LL anterior x (1+g)
BRBI11_LL_PROJETADO_ESPERADO = (
    Decimal("182321022.20"),
    Decimal("189869112.52"),
    Decimal("197729693.78"),
)

# VPL de cada ano projetado, taxa de desconto 14% (secao 8)
BRBI11_VPL_ANO_ESPERADO = (
    Decimal("159930721.23"),
    Decimal("146098116.74"),
    Decimal("133461911.21"),
)

# Valor Terminal bruto (antes do desconto a valor presente) (secao 16)
BRBI11_VALOR_TERMINAL_ESPERADO = Decimal("1851000000")  # ~R$ 1,851 bilhao (arredondado)

# Resultado historico observado na Ward (~2.18 periodos de desconto da
# perpetuidade, ver secao 18/36 do SKILL.md). NAO usado como golden test do
# comportamento padrao do sistema - ver test_engine.py. O SKILL.md atual nao
# publica um valor final de referencia para BRBI11 na convencao padrao.
BRBI11_PRECO_JUSTO_DOC = Decimal("17.43")
BRBI11_UPSIDE_DOC = Decimal("0.4026")


# --- TAEE4 (secoes 6, 34, 35 do SKILL.md) ---

TAEE4_LL_ANO_BASE = Decimal("1677182560.80")  # LL 2026
TAEE4_TAXA_CRESCIMENTO = Decimal("0.0616")
TAEE4_TAXA_DESCONTO = Decimal("0.14")
TAEE4_CRESCIMENTO_PERPETUIDADE = Decimal("0.03")
TAEE4_ANOS_PROJECAO = 3
TAEE4_NUMERO_ACOES = Decimal("1033496721")
TAEE4_PRECO_ATUAL = Decimal("12.75")

TAEE4_LL_PROJETADO_ESPERADO = (
    Decimal("1677182560.80"),
    Decimal("1780497006.55"),
    Decimal("1890175622.15"),
)

TAEE4_VPL_ANO_ESPERADO = (
    Decimal("1471212772.63"),
    Decimal("1370034631.08"),
    Decimal("1275817405.57"),
)

TAEE4_VALOR_TERMINAL_ESPERADO = Decimal("17698917189.21")

# Resultado historico observado na Ward (secao 36 do SKILL.md) - idem
# observacao acima. NOTA: o SKILL.md atual (secao 35) publica um resultado
# final diferente deste, ja na convencao padrao (N=3 periodos inteiros):
# preco justo ~R$ 15,54 / upside ~21,90% - que e o que os golden tests de
# `test_engine.py` validam, e nao os valores *_DOC abaixo.
TAEE4_VPL_PERPETUIDADE_DOC = Decimal("13297458444.18")
TAEE4_VALOR_ESTIMADO_DOC = Decimal("17414523253.46")
TAEE4_PRECO_JUSTO_DOC = Decimal("16.85")
TAEE4_UPSIDE_DOC = Decimal("0.3216")
