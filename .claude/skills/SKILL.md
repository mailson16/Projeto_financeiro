# SKILL.md — Nosso Valuation B3

## 1. IDENTIDADE DA SKILL

Nome:
Nosso Valuation

Objetivo:
Desenvolver e manter um sistema próprio de valuation de ações e outros ativos negociados na B3, utilizando principalmente o método de Fluxo de Caixa Descontado (DCF), com foco em transparência, rastreabilidade, cenários e margem de segurança.

A skill deve atuar como:
- Analista de investimentos
- Desenvolvedor Python
- Especialista em modelagem financeira
- Especialista em DCF
- Especialista em dados financeiros
- Especialista em arquitetura de sistemas

Idioma padrão:
Português do Brasil.

---

# 2. ESCOPO PRINCIPAL

O projeto possui APENAS:

## MODO 2 — NOSSO VALUATION

Não implementar a reprodução integral do valuation da Ward como produto principal.

A referência da Ward pode ser utilizada apenas para:
- entender conceitos;
- validar cálculos;
- comparar resultados;
- identificar premissas;
- reproduzir determinados cálculos para fins de teste.

O sistema final deve possuir metodologia própria, documentada e reproduzível.

---

# 3. PRINCÍPIOS DO PROJETO

O valuation deve ser:

1. Transparente
2. Reproduzível
3. Auditável
4. Dinâmico
5. Parametrizável
6. Versionável
7. Baseado em dados
8. Sensível às premissas
9. Capaz de trabalhar com cenários
10. Capaz de explicar a origem de cada número

A pergunta que o sistema deve conseguir responder para qualquer valor apresentado é:

> "De onde veio esse número?"

Para isso, sempre que possível armazenar:

- valor;
- fórmula;
- premissa;
- fonte;
- data da fonte;
- data de atualização;
- se foi calculado automaticamente;
- se foi alterado manualmente pelo usuário;
- cenário utilizado.

---

# 4. OBJETIVO DO VALUATION

O sistema deve estimar:

- Valor justo do ativo;
- Valor justo por ação/cota;
- Potencial de valorização;
- Potencial de queda;
- Margem de segurança;
- Valor de entrada;
- Valor terminal;
- Valor presente dos fluxos;
- Sensibilidade às principais premissas.

O sistema NÃO deve apresentar o valuation como uma previsão exata.

O resultado deve ser interpretado como:

> uma estimativa de valor baseada nas premissas utilizadas.

---

# 5. METODOLOGIA PRINCIPAL

A metodologia principal é:

## Fluxo de Caixa Descontado — DCF

No projeto inicial será utilizado o Lucro Líquido como fluxo modelado.

IMPORTANTE:

Lucro Líquido não é universalmente equivalente a Free Cash Flow.

Portanto, o sistema deve deixar documentado que:

- para empresas não financeiras, uma futura evolução poderá utilizar FCF;
- para instituições financeiras, o Lucro Líquido pode ser uma referência mais adequada dentro de uma abordagem de equity valuation;
- o uso do Lucro Líquido deve ser identificado explicitamente no modelo.

---

# 6. DADOS DE ENTRADA

O sistema poderá utilizar:

## Mercado

- Ticker
- Nome
- Setor
- Subsetor
- Preço atual
- Quantidade total de ações
- Market Cap

## Indicadores

- ROE
- Payout
- Crescimento
- Patrimônio Líquido
- Margens
- Outros indicadores relevantes

## Resultados

- Lucro Líquido histórico
- Lucro Líquido anual
- Lucro Líquido trimestral
- Período
- Ano
- Fonte

## Proventos

- Dividendos
- JCP
- Data de pagamento
- Data com
- Valor por ação
- Total distribuído

## Premissas

- Lucro base
- Crescimento
- Taxa de desconto
- Crescimento na perpetuidade
- Número de anos projetados
- Payout
- ROE

---

# 7. LUCRO LÍQUIDO HISTÓRICO

O sistema deve armazenar o histórico de Lucro Líquido.

Exemplo:

| Ano | Lucro Líquido |
|-----|---------------|
| 2021 | 138.660.000 |
| 2022 | 147.100.000 |
| 2023 | 155.080.000 |
| 2024 | 193.670.000 |
| 2025 | 175.070.000 |

Os valores devem ser armazenados em formato numérico.

Nunca armazenar:

"R$ 175.070.000,00"

como texto quando o valor precisar ser utilizado nos cálculos.

Preferir:

175070000

ou:

175070000.00

---

# 8. LUCRO BASE

O modelo deve permitir definir o Lucro Líquido base utilizado para iniciar a projeção.

Exemplo:

Lucro base 2026:

R$ 182.321.022,20

Esse valor poderá ser:

- obtido automaticamente;
- calculado a partir dos resultados disponíveis;
- informado manualmente pelo usuário.

Quando informado manualmente, o sistema deve registrar:

manual_override = true

e guardar o valor original da fonte, quando disponível.

---

# 9. CRESCIMENTO

O crescimento é uma das principais premissas do modelo.

O sistema deve permitir:

### Crescimento automático

Utilizando:

g = ROE × (1 - Payout)

Onde:

g = crescimento sustentável

ROE = Retorno sobre Patrimônio Líquido

Payout = percentual do lucro distribuído

Retenção:

Retenção = 1 - Payout

Portanto:

g = ROE × Retenção

Exemplo:

ROE = 20%

Payout = 70%

Retenção = 30%

g = 20% × 30%

g = 6%

---

# 10. CRESCIMENTO MANUAL

O usuário deve poder alterar manualmente o crescimento.

Portanto o sistema deve suportar:

growth_mode:

- automatic
- manual

Se:

growth_mode = automatic

utilizar:

g = ROE × (1 - Payout)

Se:

growth_mode = manual

utilizar o crescimento informado pelo usuário.

O crescimento manual deve ter prioridade sobre o crescimento calculado automaticamente.

---

# 11. TAXA DE DESCONTO

REGRA FUNDAMENTAL DO PROJETO:

A taxa de desconto deve ser preenchida automaticamente com a SELIC atualizada.

Porém:

## O usuário pode alterar manualmente a taxa.

Exemplo:

Selic atual:

15%

O sistema inicialmente apresenta:

Taxa de desconto = 15%

O usuário pode alterar para:

14%

ou:

13%

ou qualquer outro valor considerado adequado.

---

# 12. SELIC

A SELIC deve ser obtida automaticamente sempre que houver uma fonte confiável disponível.

O sistema deve armazenar:

- taxa;
- data de referência;
- fonte;
- data de atualização.

Exemplo conceitual:

discount_rate:
    value: 0.15
    source: "BCB"
    reference_date: "2026-09-XX"
    manual_override: false

Se o usuário alterar:

discount_rate:
    value: 0.14
    source: "BCB"
    original_value: 0.15
    manual_override: true

---

# 13. PROJEÇÃO DO LUCRO

A projeção deve utilizar crescimento composto.

Fórmula:

LLₙ = LLₙ₋₁ × (1 + g)

Exemplo:

LL 2026 = R$ 1.000.000

Crescimento = 8%

LL 2027:

1.000.000 × 1,08

= R$ 1.080.000

LL 2028:

1.080.000 × 1,08

= R$ 1.166.400

---

# 14. NÚMERO DE ANOS

O sistema deve permitir:

- 3 anos;
- 5 anos;
- futuramente número customizado.

O padrão inicial será:

3 anos.

Exemplo:

Ano base:
2026

Projeções:

2027
2028
2029

OU, conforme definição do caso de teste:

2026
2027
2028

A convenção deve ser explicitamente definida no motor de cálculo.

Nunca misturar convenções silenciosamente.

---

# 15. VALOR PRESENTE — VPL

Cada fluxo projetado deve ser descontado pela taxa de desconto.

Fórmula:

VPL = Fluxo / (1 + r)^n

Onde:

Fluxo = lucro projetado

r = taxa de desconto

n = período

Exemplo:

Lucro = R$ 100 milhões

Taxa = 14%

Período = 1

VPL:

100.000.000 / 1,14

= R$ 87.719.298,25

---

# 16. VALOR TERMINAL / PERPETUIDADE

Após o período explícito de projeção, calcular o valor terminal.

Fórmula:

VT = LL_final × (1 + g_perp) / (r - g_perp)

Onde:

VT = Valor Terminal

LL_final = lucro do último ano projetado

g_perp = crescimento na perpetuidade

r = taxa de desconto

Regra:

r > g_perp

Se:

r <= g_perp

o sistema deve gerar erro ou alerta.

Nunca calcular silenciosamente uma perpetuidade inválida.

---

# 17. CRESCIMENTO NA PERPETUIDADE

Premissa inicial:

3%

Porém deve ser editável.

Exemplo:

Perpetuidade = 3%

O usuário poderá alterar para:

2%
3%
4%

etc.

O sistema deve alertar para premissas excessivamente agressivas.

---

# 18. DESCONTO DO VALOR TERMINAL

Para o Nosso Valuation, utilizar inicialmente a convenção padrão:

PV Terminal = VT / (1 + r)^n

onde:

n = número de períodos do horizonte explícito.

Exemplo:

3 anos:

PV Terminal = VT / (1+r)^3

IMPORTANTE:

Durante a análise da Ward foi identificado que os cálculos observados podem utilizar aproximadamente 2,5 períodos para o desconto do terminal.

Isso NÃO deve ser misturado com o Nosso Valuation.

Se futuramente for necessário reproduzir exatamente esse comportamento, criar uma configuração separada:

terminal_discount_convention:

- standard
- ward_compatibility

O padrão do Nosso Valuation é:

standard

---

# 19. VALOR TOTAL

Valor total da empresa/equity:

Valor Total =

Σ VPL dos fluxos explícitos

+

PV do Valor Terminal

Exemplo:

VPL 2026
+
VPL 2027
+
VPL 2028
+
PV Terminal

---

# 20. VALOR JUSTO POR AÇÃO

Fórmula:

Valor Justo por Ação = Valor Total / Número de Ações

Exemplo:

Valor Total:

R$ 10 bilhões

Número de ações:

1 bilhão

Valor justo:

R$ 10,00

---

# 21. UPSIDE / DOWNSIDE

Fórmula:

Upside = (Valor Justo / Preço Atual) - 1

Exemplo:

Valor justo = R$ 20

Preço atual = R$ 15

Upside:

20 / 15 - 1

= 33,33%

Se o resultado for negativo:

Downside.

---

# 22. MARGEM DE SEGURANÇA

A margem de segurança deve ser calculada sobre o valor justo.

Fórmula:

Preço de Entrada = Valor Justo × (1 - Margem)

Exemplo:

Valor justo:

R$ 20

Margem:

20%

Preço de entrada:

20 × 0,80

= R$ 16

O sistema deve permitir alterar a margem.

Exemplos:

10%
15%
20%
25%
30%

---

# 23. CENÁRIOS

O sistema deve possuir três cenários:

## Pessimista

Premissas mais conservadoras.

## Base

Premissas consideradas mais prováveis.

## Otimista

Premissas mais favoráveis.

Cada cenário deve possuir suas próprias premissas.

Exemplo:

| Premissa | Pessimista | Base | Otimista |
|-----------|------------|------|----------|
| Crescimento | 3% | 8% | 12% |
| ROE | 14% | 19% | 23% |
| Payout | ajustado | ajustado | ajustado |
| Perpetuidade | 2% | 3% | 4% |

Esses números são exemplos didáticos e NÃO devem ser aplicados automaticamente às empresas.

---

# 24. RESULTADO POR CENÁRIO

O sistema deve mostrar:

| Cenário | Valor Justo | Upside | Entrada com M.S. |
|----------|-------------|--------|-------------------|
| Pessimista | R$ X | X% | R$ X |
| Base | R$ X | X% | R$ X |
| Otimista | R$ X | X% | R$ X |

A análise deve priorizar a faixa de valor, e não apenas um número.

---

# 25. SENSIBILIDADE

O sistema deve permitir análise de sensibilidade.

Principais variáveis:

- crescimento;
- taxa de desconto;
- perpetuidade;
- payout;
- ROE.

Exemplo:

| Crescimento / Desconto | 12% | 14% | 16% |
|------------------------|-----:|-----:|-----:|
| 4% | X | X | X |
| 6% | X | X | X |
| 8% | X | X | X |

O objetivo é mostrar como pequenas alterações nas premissas podem alterar significativamente o valor justo.

---

# 26. ALERTAS DO MODELO

O sistema deve gerar alertas quando:

- taxa de desconto <= crescimento da perpetuidade;
- crescimento excessivamente elevado;
- perpetuidade excessivamente elevada;
- ROE incompatível com histórico;
- payout incompatível com histórico;
- lucro base muito diferente do histórico;
- número de ações divergente entre fontes;
- dados desatualizados;
- dados ausentes;
- valor manualmente alterado;
- fonte não identificada.

---

# 27. DADOS DE MERCADO

O sistema deve buscar, quando possível:

- preço;
- ações em circulação;
- market cap;
- ROE;
- payout;
- patrimônio líquido;
- lucro líquido.

Porém:

## Nunca assumir que duas fontes possuem exatamente a mesma metodologia.

Exemplos de diferenças possíveis:

- IFRS;
- resultado regulatório;
- resultado ajustado;
- lucro atribuível aos controladores;
- lucro consolidado;
- períodos diferentes;
- TTM;
- exercício anual.

O sistema deve preservar a origem dos dados.

---

# 28. FONTE DOS DADOS

Todo dado externo deve, quando possível, armazenar:

source
source_url
reference_date
retrieved_at

Exemplo:

{
    "value": 0.197,
    "source": "Fundamentus",
    "reference_date": "2026-03-31",
    "retrieved_at": "2026-09-09"
}

---

# 29. BANCO DE DADOS

Estrutura conceitual inicial:

## EMPRESA

Campos:

- id
- ticker
- nome
- setor
- subsetor

## MERCADO

Campos:

- id
- empresa_id
- data
- preco
- quantidade_acoes
- market_cap
- fonte

## INDICADORES

Campos:

- id
- empresa_id
- data
- roe
- payout
- patrimonio_liquido
- crescimento
- fonte

## RESULTADOS

Campos:

- id
- empresa_id
- periodo
- ano
- trimestre
- lucro_liquido
- fonte

## DIVIDENDOS

Campos:

- id
- empresa_id
- data
- tipo
- valor
- valor_por_acao
- fonte

## VALUATIONS

Campos:

- id
- empresa_id
- data
- cenario
- lucro_base
- crescimento
- taxa_desconto
- perpetuidade
- anos_projecao
- valor_terminal
- pv_terminal
- valor_total
- valor_justo
- preco_atual
- upside
- margem_seguranca
- preco_entrada

---

# 30. VERSIONAMENTO DO VALUATION

Cada valuation deve ser armazenado como uma versão.

Exemplo:

BRBI11

Valuation #1:
09/09/2026

Valuation #2:
20/09/2026

Valuation #3:
10/10/2026

Isso permitirá comparar:

- alteração do preço;
- alteração do lucro;
- alteração da Selic;
- alteração do crescimento;
- alteração do valuation.

---

# 31. ARQUITETURA PYTHON

A matemática NÃO deve ficar dentro da interface.

Estrutura sugerida:

project/

    app.py

    valuation/

        __init__.py
        engine.py
        projections.py
        perpetuity.py
        scenarios.py
        sensitivity.py

    data/

        market.py
        fundamentals.py
        results.py
        dividends.py

    database/

        models.py
        connection.py
        repository.py

    services/

        market_service.py
        selic_service.py
        valuation_service.py

    web/

        routes.py

    templates/

    static/

    tests/

---

# 32. ENGINE DE VALUATION

O motor matemático deve ser independente da interface.

Exemplo conceitual:

valuation = calculate_dcf(
    base_profit=182321022.20,
    growth=0.0414,
    discount_rate=0.14,
    terminal_growth=0.03,
    years=3,
    shares=314987112
)

O retorno deve conter:

- projeções;
- VPLs;
- valor terminal;
- PV terminal;
- valor total;
- valor justo;
- upside;
- margem de segurança;
- preço de entrada.

---

# 33. TESTES

O motor deve possuir testes automatizados.

Casos obrigatórios:

1. BRBI11
2. TAEE4

Os valores dos testes devem ser mantidos independentemente dos dados atuais.

Isso é importante porque os dados de mercado mudam.

---

# 34. CASO DE TESTE BRBI11

Valores utilizados na validação inicial:

Preço:

R$ 12,43

Ações:

314.987.112

Payout:

78,96%

ROE:

19,70%

Crescimento:

4,14%

Taxa de desconto:

14%

Perpetuidade:

3%

Lucro base 2026:

R$ 182.321.022,20

Lucro 2027:

R$ 189.869.112,52

Lucro 2028:

R$ 197.729.693,78

Esses valores representam um caso histórico de validação.

Não substituir automaticamente pelos valores atuais.

---

# 35. CASO DE TESTE TAEE4

Valores utilizados na validação inicial:

Preço:

R$ 12,75

Ações:

1.033.496.721

Market Cap:

R$ 13,177 bilhões

Payout:

69,42%

ROE:

20,14%

Crescimento:

6,16%

Taxa de desconto:

14%

Perpetuidade:

3%

Lucro base 2026:

R$ 1.677.182.560,80

Lucro 2027:

R$ 1.780.497.006,55

Lucro 2028:

R$ 1.890.175.622,15

VPL 2026:

R$ 1.471.212.772,63

VPL 2027:

R$ 1.370.034.631,08

VPL 2028:

R$ 1.275.817.405,57

Soma dos VPLs:

R$ 4.117.064.809,28

Valor Terminal:

R$ 17.698.917.189,21

PV Terminal usando convenção padrão de 3 períodos:

R$ 11.946.264.970,33

Valor total:

R$ 16.063.329.779,61

Valor justo:

aproximadamente R$ 15,54

Upside:

aproximadamente 21,90%

Margem de segurança de 20%:

aproximadamente R$ 12,43

---

# 36. DIFERENÇA IDENTIFICADA NA WARD

Durante a validação da TAEE4 e BRBI11 foi identificado que os resultados observados na Ward parecem utilizar aproximadamente 2,5 períodos para descontar o valor terminal.

Isso explica diferenças como:

Valor Terminal:

R$ 17,6989 bilhões

PV Terminal observado:

aproximadamente R$ 13,297 bilhões

Essa diferença NÃO deve ser incorporada silenciosamente ao Nosso Valuation.

O modelo padrão utiliza:

PV Terminal = VT / (1+r)^n

Caso seja necessário reproduzir a Ward:

criar uma opção específica.

---

# 37. INTERFACE FUTURA

A interface deve possuir inicialmente:

## Cabeçalho

- Busca do ticker
- Data da análise
- Preço atual

## Informações da empresa

- Nome
- Setor
- Subsetor
- Market Cap
- Nº de ações

## Histórico

- Lucro Líquido
- ROE
- Payout
- Patrimônio Líquido
- Dividendos

## Premissas

- Lucro base
- Crescimento
- ROE
- Payout
- Selic
- Taxa de desconto
- Perpetuidade
- Anos de projeção

Todos os campos relevantes devem ser editáveis.

---

# 38. INDICAÇÃO VISUAL

A interface deve mostrar claramente:

### Dados automáticos

Exemplo:

SELIC:
15%

Fonte:
Banco Central

### Dados alterados manualmente

Exemplo:

Taxa de desconto:
14%

Badge:

"Alterado manualmente"

Isso evita que o usuário esqueça que mudou uma premissa automática.

---

# 39. RESULTADO FINAL

A interface deve destacar:

## Valor Justo

R$ XX,XX

## Preço Atual

R$ XX,XX

## Upside

XX%

## Margem de Segurança

XX%

## Preço de Entrada

R$ XX,XX

---

# 40. COMPARAÇÃO COM INDICADORES

O sistema poderá futuramente comparar o DCF com:

- P/L;
- P/VP;
- ROE;
- Dividend Yield;
- crescimento histórico;
- crescimento projetado;
- valor patrimonial.

Essa comparação NÃO substitui o DCF.

Ela serve para verificar se o resultado parece coerente.

---

# 41. EMPRESAS FINANCEIRAS

Para empresas financeiras:

- bancos;
- seguradoras;
- holdings financeiras;
- instituições de crédito;

o modelo deve tratar o Lucro Líquido com atenção.

O sistema deve permitir futuramente metodologias específicas.

Não assumir automaticamente que:

FCF tradicional = Lucro Líquido.

Para o primeiro estágio, manter o modelo simples e documentado.

---

# 42. QUALIDADE DOS DADOS

Nunca preencher dados desconhecidos inventando valores.

Se não houver dado:

null

ou:

"não disponível"

Nunca:

0

quando o valor real é desconhecido.

Especialmente importante para:

- preço;
- custo;
- quantidade;
- lucro;
- payout;
- ROE.

Zero pode significar um valor financeiro real e não deve ser utilizado como substituto para dado ausente.

---

# 43. ARREDONDAMENTO

Os cálculos internos devem utilizar a maior precisão possível.

Arredondamento deve ocorrer somente na apresentação.

Exemplo:

Internamente:

15.543829483

Interface:

R$ 15,54

Nunca utilizar o valor arredondado intermediário para novos cálculos.

---

# 44. MOEDA

Valores monetários devem ser armazenados numericamente.

Banco:

12500.50

Interface:

R$ 12.500,50

Nunca realizar cálculos diretamente sobre strings formatadas.

---

# 45. TRATAMENTO DE PERCENTUAIS

Internamente:

15% = 0.15

Interface:

15,00%

Nunca armazenar 15 como taxa decimal se a fórmula espera 0.15.

---

# 46. REGRAS DE CÓDIGO

Código Python deve priorizar:

- PEP 8
- funções pequenas;
- responsabilidade única;
- type hints;
- docstrings;
- tratamento de exceções;
- logging;
- testes unitários;
- configuração via `.env`;
- separação entre dados, regras e interface.

Evitar:

- cálculo financeiro dentro de HTML;
- SQL espalhado pelo código;
- valores hardcoded;
- credenciais no código;
- URLs de APIs espalhadas;
- duplicação de fórmulas.

---

# 47. CONFIGURAÇÃO

Utilizar variáveis de ambiente para:

- banco;
- APIs;
- chaves;
- URLs;
- credenciais.

Exemplo:

.env

DATABASE_URL=...
API_KEY=...

Nunca colocar credenciais diretamente no GitHub.

---

# 48. GIT

O projeto deve utilizar Git.

Branches sugeridas:

main

develop

feature/valuation-engine

feature/data-collection

feature/database

feature/interface

feature/sensitivity

feature/tests

Commits devem explicar claramente a alteração.

Exemplo:

feat: adiciona cálculo de valor terminal

fix: corrige desconto do fluxo projetado

test: adiciona caso BRBI11

---

# 49. ORDEM DE DESENVOLVIMENTO

A implementação deve seguir esta ordem:

## ETAPA 1

Motor matemático.

Sem interface.

Implementar:

- crescimento;
- projeção;
- VPL;
- perpetuidade;
- valor terminal;
- valor justo;
- upside;
- margem de segurança.

---

## ETAPA 2

Testes.

Validar:

- BRBI11;
- TAEE4.

---

## ETAPA 3

Cenários.

Implementar:

- pessimista;
- base;
- otimista.

---

## ETAPA 4

Sensibilidade.

Implementar matriz de:

- crescimento;
- taxa de desconto.

---

## ETAPA 5

Coleta de dados.

Automatizar:

- preço;
- ações;
- market cap;
- ROE;
- payout;
- lucro;
- histórico.

---

## ETAPA 6

Banco de dados.

Persistir:

- empresas;
- resultados;
- indicadores;
- mercado;
- dividendos;
- valuations.

---

## ETAPA 7

Backend/API.

Criar serviços para:

- consultar empresa;
- atualizar dados;
- executar valuation;
- salvar valuation;
- recuperar histórico.

---

## ETAPA 8

Interface web.

Criar dashboard interativo.

---

## ETAPA 9

Exportação.

Futuramente:

- Excel;
- PDF;
- relatórios.

---

# 50. FLUXO IDEAL DO USUÁRIO

O usuário informa:

BRBI11

O sistema:

1. Localiza empresa.
2. Busca dados atuais.
3. Mostra histórico.
4. Busca SELIC atual.
5. Calcula premissas automáticas.
6. Permite alterações.
7. Executa DCF.
8. Calcula cenários.
9. Calcula sensibilidade.
10. Mostra valor justo.
11. Mostra margem de segurança.
12. Permite salvar a análise.

---

# 51. AUDITORIA

Cada valuation salvo deve permitir reconstruir exatamente o resultado.

Guardar:

- dados de entrada;
- premissas;
- fórmula;
- versão do modelo;
- data;
- cenário;
- resultado.

Idealmente:

model_version = "1.0.0"

Assim, se a fórmula mudar no futuro, valuations antigos continuam identificáveis.

---

# 52. NÃO ALTERAR AUTOMATICAMENTE PREMISSAS DO USUÁRIO

Se o usuário alterar:

Taxa de desconto:

14%

e a SELIC estiver:

15%

o sistema NÃO deve substituir novamente por 15% durante o cálculo.

Deve manter:

15% = valor automático original

14% = valor utilizado no valuation

---

# 53. EXPLICAÇÃO DOS RESULTADOS

O sistema deve explicar o valuation em linguagem simples.

Exemplo:

"Com crescimento de 6,16%, taxa de desconto de 14% e perpetuidade de 3%, o modelo estima valor justo de R$ 15,54 por ação."

Também deve mostrar:

"Se a taxa de desconto subir para 16%, o valor justo cai para R$ X."

---

# 54. PRINCÍPIO DE PRUDÊNCIA

O sistema deve evitar conclusões como:

"Essa ação vale R$ 20."

Preferir:

"Com as premissas utilizadas, o modelo estima valor justo de aproximadamente R$ 20."

E:

"O resultado é sensível principalmente à taxa de desconto e ao crescimento."

---

# 55. DECISÃO DE INVESTIMENTO

O valuation NÃO deve automaticamente gerar:

"COMPRAR"

ou:

"VENDER"

O sistema deve fornecer informações para decisão:

- valor justo;
- preço atual;
- upside;
- margem de segurança;
- cenário pessimista;
- cenário base;
- cenário otimista;
- sensibilidade;
- qualidade dos dados.

A decisão final permanece com o usuário.

---

# 56. REGRA PARA NOVOS DESENVOLVIMENTOS

Antes de adicionar uma nova funcionalidade, verificar:

1. Isso pertence ao Modo 2?
2. É necessário para o valuation?
3. Afeta o motor matemático?
4. Afeta a rastreabilidade?
5. Precisa ser armazenado no banco?
6. Precisa de teste?
7. Pode quebrar resultados anteriores?

Se alterar a matemática:

- atualizar testes;
- atualizar documentação;
- incrementar versão do modelo quando necessário.

---

# 57. REGRA PARA FONTES EXTERNAS

Quando dados externos forem utilizados:

- identificar fonte;
- identificar data;
- verificar período;
- verificar metodologia;
- não misturar automaticamente fontes incompatíveis;
- preservar o dado original.

Quando houver divergência entre fontes:

NÃO escolher silenciosamente um valor.

Mostrar a divergência e definir explicitamente qual fonte/metodologia será utilizada.

---

# 58. PRIORIDADE DAS INFORMAÇÕES

Em caso de conflito:

1. Dados explicitamente informados pelo usuário para um caso de teste;
2. Dados oficiais da empresa;
3. Dados oficiais de órgãos reguladores;
4. Fontes financeiras confiáveis;
5. Outras fontes secundárias.

Dados históricos de teste devem permanecer congelados para fins de validação.

---

# 59. CASOS HISTÓRICOS NÃO DEVEM SER SOBRESCRITOS

BRBI11 e TAEE4 possuem valores definidos para validação.

Esses valores devem ser tratados como:

fixtures/tests

e não como dados atuais.

Exemplo:

tests/fixtures/brbi11_valuation_2026.json

tests/fixtures/taee4_valuation_2026.json

---

# 60. FUTURAS EVOLUÇÕES

Possíveis evoluções:

- FCF;
- FCFE;
- valuation específico para bancos;
- valuation específico para seguradoras;
- dividend discount model;
- múltiplos;
- comparação setorial;
- histórico de valuation;
- ranking de ações;
- alertas;
- atualização automática;
- gráficos;
- API;
- autenticação;
- multiusuário;
- exportação Excel;
- exportação PDF.

Essas funcionalidades NÃO fazem parte da primeira versão.

---

# 61. PRIMEIRA META DO PROJETO

A primeira entrega funcional deve conseguir executar:

BRBI11

↓

Receber premissas

↓

Projetar lucro

↓

Calcular VPL

↓

Calcular perpetuidade

↓

Calcular valor terminal

↓

Calcular valor total

↓

Calcular valor justo

↓

Calcular upside

↓

Calcular margem de segurança

↓

Retornar resultado estruturado.

Depois:

TAEE4.

Somente após os dois casos estarem validados:

dados automáticos → banco → interface.

---

# 62. REGRA FINAL

O projeto deve sempre priorizar:

TRANSPARÊNCIA > COMPLEXIDADE

CORREÇÃO > VELOCIDADE

RASTREABILIDADE > CONVENIÊNCIA

DADOS > ACHISMOS

CENÁRIOS > PREVISÃO ÚNICA

MARGEM DE SEGURANÇA > PREÇO-ALVO ISOLADO

O objetivo não é criar uma "bola de cristal".

O objetivo é criar uma ferramenta que permita responder:

> "Quanto essa empresa pode valer sob determinadas premissas e quanto estou pagando por ela hoje?"

E, principalmente:

> "O que precisa acontecer para que esse valuation esteja errado?"