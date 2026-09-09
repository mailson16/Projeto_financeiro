"""Constantes de decisao de design do motor de valuation.

Ver nosso_valuation_aprendizado.md, secao 9: a ferramenta de referencia
"Ward" desconta o Valor Terminal por um numero fracionario de periodos
(a propria secao 9 cita ~2.5; nos exemplos numericos da secao 19 o valor
implicito e ~2.18). O "Nosso Valuation" NAO deve reproduzir essa
convencao implicitamente - a regra usada deve ser uma decisao explicita
e documentada, nao um numero magico copiado de outra ferramenta.

Convencao adotada por padrao: financas corporativas padrao (ex.: Damodaran).
O Valor Terminal (formula de Gordon) representa o valor no fim do ultimo
ano projetado (ano N), entao ele e trazido a valor presente descontando
exatamente N periodos - o mesmo N usado para descontar o ultimo fluxo de
caixa projetado.

Qualquer desvio dessa convencao deve ser passado explicitamente via
`PremissasValuation.periodos_desconto_perpetuidade`, nunca hardcoded em
outro lugar do codigo.
"""

from decimal import Decimal

# Sentinela: quando `periodos_desconto_perpetuidade` nao e informado nas
# premissas, o motor usa `anos_projecao` (N) como numero de periodos para
# descontar o Valor Terminal a valor presente.
CONVENCAO_PADRAO_PERIODOS_DESCONTO_PERPETUIDADE = "N"

ZERO = Decimal("0")

# Versao do modelo/formula de calculo (secao 51 do SKILL.md: "auditoria").
# Incrementar sempre que uma formula do motor mudar, para que valuations
# antigos salvos com uma versao anterior continuem identificaveis.
MODEL_VERSION = "1.0.0"

# Valores possiveis de `PremissasValuation.growth_mode` (secao 10 do
# SKILL.md). "automatic": crescimento vem de g = ROE x (1 - Payout) ou de
# outra fonte automatica (ex.: media historica) quando ROE/Payout nao
# estao disponiveis. "manual": usuario digitou o valor - tem prioridade
# sobre qualquer sugestao automatica.
GROWTH_MODE_AUTOMATIC = "automatic"
GROWTH_MODE_MANUAL = "manual"
