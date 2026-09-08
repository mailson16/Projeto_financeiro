# Nosso Valuation --- Aprendizados e Especificação do Projeto

## 1. Objetivo

Construir um sistema próprio de valuation para ações da B3, inspirado no
estudo da ferramenta Ward, mas usando exclusivamente o **Modo 2 ---
Nosso Valuation**.

A Ward será apenas uma referência para entender a lógica. Não vamos
reproduzir suas limitações.

O sistema deverá funcionar para múltiplos ativos, como BRBI11, TAEE4,
ITSA4, TAEE11 e outros.

------------------------------------------------------------------------

## 2. Estrutura aprendida

A lógica estudada é:

Lucro Líquido do ano-base → taxa de crescimento → Lucro Líquido
projetado → taxa de desconto → VPL → perpetuidade → VPL da perpetuidade
→ valor estimado → divisão pelo número de ações → preço justo →
upside/downside.

No nosso sistema essa lógica será aprimorada e poderá utilizar cenários,
margem de segurança e análise de sensibilidade.

------------------------------------------------------------------------

## 3. Dados automáticos

O sistema deverá buscar ou calcular dinamicamente:

-   Ticker
-   Nome da empresa
-   Preço atual
-   Número total de ações
-   Market Cap
-   Payout
-   ROE
-   Lucro Líquido histórico
-   Crescimento histórico do Lucro Líquido
-   Lucro Líquido TTM / ano atual
-   Dados trimestrais e anuais
-   Patrimônio Líquido
-   Dividendos/proventos
-   LPA e outros indicadores úteis

O histórico deverá ser armazenado no banco de dados.

Estrutura conceitual de um resultado:

``` text
Ativo
Ano
Lucro Líquido
Crescimento
Fonte
Data de atualização
```

------------------------------------------------------------------------

## 4. Premissas editáveis

O usuário deverá poder alterar:

-   Lucro Líquido do ano-base
-   Payout médio
-   ROE
-   Taxa esperada de crescimento
-   Taxa de desconto
-   Crescimento na perpetuidade
-   Número de anos de projeção

Qualquer alteração deverá recalcular automaticamente o valuation.

------------------------------------------------------------------------

## 5. Taxa de desconto --- regra definida

A **taxa de desconto será preenchida automaticamente com a Selic
atualizada**.

Porém, ela será sempre editável.

Exemplo:

``` text
Taxa de desconto
[ 14,00% ]
```

O sistema busca a Selic atual e preenche o campo. O usuário poderá
trocar para 13%, 15% etc. para testar cenários.

Isso torna a Selic a referência inicial, sem impedir uma avaliação
personalizada.

------------------------------------------------------------------------

## 6. Histórico do Lucro Líquido

O histórico serve de base para analisar a evolução da empresa e
alimentar o modelo.

### BRBI11 --- exemplo estudado

  Ano           Lucro Líquido
  ------ --------------------
  2021     R\$ 138,66 milhões
  2022     R\$ 147,10 milhões
  2023     R\$ 155,08 milhões
  2024     R\$ 193,67 milhões
  2025     R\$ 175,07 milhões

### TAEE4 --- exemplo estudado

  Ano          Lucro Líquido
  ------ -------------------
  2021     R\$ 2,213 bilhões
  2022      R\$ 1,449 bilhão
  2023      R\$ 1,368 bilhão
  2024      R\$ 1,694 bilhão
  2025      R\$ 1,580 bilhão

Crescimento anual:

``` text
Crescimento = (LL atual / LL anterior) - 1
```

------------------------------------------------------------------------

## 7. Ano-base e projeção

O usuário poderá informar ou ajustar o Lucro Líquido do ano-base.

Exemplo BRBI11:

``` text
LL 2026 = R$ 182.321.022,20
Crescimento = 4,14%
```

Projeção:

``` text
LL futuro = LL anterior × (1 + taxa de crescimento)
```

Assim:

``` text
LL 2027 = R$ 189.869.112,52
LL 2028 = R$ 197.729.693,78
```

O sistema próprio deverá futuramente permitir:

-   crescimento constante;
-   crescimento diferente por ano;
-   crescimento baseado no histórico;
-   crescimento baseado em ROE × retenção;
-   crescimento por cenário.

------------------------------------------------------------------------

## 8. Valor Presente

Fórmula básica:

``` text
VPL = Fluxo Futuro / (1 + taxa de desconto)^n
```

Exemplo BRBI11 com taxa de 14%:

``` text
2026:
R$ 182.321.022,20 / 1,14
= R$ 159.930.721,23

2027:
R$ 189.869.112,52 / 1,14²
= R$ 146.098.116,74

2028:
R$ 197.729.693,78 / 1,14³
= R$ 133.461.911,21
```

------------------------------------------------------------------------

## 9. Perpetuidade

A lógica estudada usa:

``` text
Valor Terminal =
LL final × (1 + g) / (taxa de desconto - g)
```

Onde:

-   LL final = lucro do último ano projetado;
-   g = crescimento da perpetuidade;
-   taxa de desconto = taxa utilizada no valuation.

Exemplo BRBI11:

``` text
LL 2028 ≈ R$ 197,73 milhões
g = 3%
taxa de desconto = 14%

Valor Terminal ≈ R$ 1,851 bilhão
```

Esse valor é posteriormente trazido a valor presente.

### Observação importante

Na análise da Ward, o VPL da perpetuidade da TAEE4 indicou um desconto
equivalente aproximadamente a 2,5 períodos, e não simplesmente 3
períodos. Isso é uma característica observada da Ward.

No **Nosso Valuation**, não devemos copiar essa convenção
automaticamente. A regra de desconto da perpetuidade deverá ser definida
explicitamente no nosso modelo.

------------------------------------------------------------------------

## 10. Valor justo

A estrutura é:

``` text
VPL dos anos projetados
+
VPL da perpetuidade
=
Valor estimado
```

Depois:

``` text
Preço justo =
Valor estimado / número de ações
```

Exemplo TAEE4 estudado:

``` text
VPL 2026 = R$ 1.471.212.772,63
VPL 2027 = R$ 1.370.034.631,08
VPL 2028 = R$ 1.275.817.405,57
VPL Perpetuidade = R$ 13.297.458.444,18

Valor estimado = R$ 17.414.523.253,46

Número de ações = 1.033.496.721

Preço justo ≈ R$ 16,85
```

------------------------------------------------------------------------

## 11. Upside / Downside

Fórmula:

``` text
Upside / Downside =
(Preço justo / Preço atual) - 1
```

Exemplo TAEE4:

``` text
Preço justo = R$ 16,85
Preço atual = R$ 12,75

Upside ≈ 32,16%
```

------------------------------------------------------------------------

## 12. Cenários

O sistema deverá trabalhar com pelo menos três cenários:

### Conservador

Exemplo inicial:

``` text
Crescimento: 2,5%
Desconto: 15%
Perpetuidade: 2,5%
```

### Base

Exemplo inicial:

``` text
Crescimento: 4,1%
Desconto: 14%
Perpetuidade: 3,0%
```

### Otimista

Exemplo inicial:

``` text
Crescimento: 7%
Desconto: 13%
Perpetuidade: 3,5%
```

Esses números são referências iniciais, não parâmetros definitivos.

Resultado:

  Cenário         Preço justo   Upside
  ------------- ------------- --------
  Conservador       R\$ XX,XX      XX%
  Base              R\$ XX,XX      XX%
  Otimista          R\$ XX,XX      XX%

------------------------------------------------------------------------

## 13. Margem de segurança

O preço justo não deverá ser tratado como certeza.

A margem de segurança será configurável.

Exemplo:

``` text
Preço justo = R$ 20,00
Margem de segurança = 20%

Preço de entrada =
R$ 20,00 × (1 - 20%)
= R$ 16,00
```

------------------------------------------------------------------------

## 14. Análise de sensibilidade

O sistema deverá mostrar como o preço justo muda conforme:

-   taxa de crescimento;
-   taxa de desconto;
-   crescimento da perpetuidade.

Exemplo:

  Crescimento / Desconto     13%   14%   15%
  ------------------------ ----- ----- -----
  3%                          XX    XX    XX
  4%                          XX    XX    XX
  5%                          XX    XX    XX

O objetivo é verificar se o valuation é robusto ou excessivamente
dependente de premissas otimistas.

------------------------------------------------------------------------

## 15. Princípio do sistema

O sistema não deverá apenas informar:

> Preço justo = R\$ X

Ele deverá explicar como chegou ao resultado.

Deverá permitir visualizar:

1.  Dados históricos
2.  Premissas
3.  Lucro do ano-base
4.  Projeções
5.  Taxa de desconto
6.  VPL de cada período
7.  Perpetuidade
8.  VPL da perpetuidade
9.  Valor total
10. Número de ações
11. Preço justo
12. Preço atual
13. Upside/Downside
14. Margem de segurança
15. Cenários
16. Sensibilidade

------------------------------------------------------------------------

## 16. Arquitetura

Preferência definida:

``` text
Python
   ↓
Banco de dados
   ↓
API / camada de dados
   ↓
Motor de Valuation
   ↓
Interface Web
   ↓
Exportação para Excel
```

A exportação para Excel poderá ser adicionada posteriormente.

------------------------------------------------------------------------

## 17. Banco de dados --- estrutura conceitual

### EMPRESA

``` text
ticker
nome
setor
dados cadastrais
```

### MERCADO

``` text
ticker
data
preço
número de ações
market cap
```

### INDICADORES

``` text
ticker
data
payout
ROE
patrimônio líquido
outros indicadores
```

### RESULTADOS

``` text
ticker
período
ano
trimestre
lucro líquido
fonte
```

### DIVIDENDOS

``` text
ticker
data
valor
tipo
```

### VALUATIONS

``` text
ticker
data
cenário
crescimento
taxa de desconto
perpetuidade
preço justo
demais premissas
```

A estrutura definitiva será definida durante a implementação.

------------------------------------------------------------------------

## 18. Fontes dos dados

O sistema deverá evitar dependência de uma única fonte.

Prioridades:

-   fontes oficiais para demonstrações financeiras;
-   fontes de mercado para cotação e indicadores;
-   validação cruzada;
-   registro da fonte e da data de atualização.

Também devemos distinguir métricas contábeis de métricas regulatórias
quando necessário, especialmente em empresas como TAESA.

------------------------------------------------------------------------

## 19. Exemplos de validação

### BRBI11

Dados observados no estudo da Ward:

``` text
Preço atual:             R$ 12,43
Nº de ações:             314.987.112
Market Cap:              R$ 1.305.096.601
Payout:                  78,96%
ROE:                     19,70%
Crescimento:             4,14%
Taxa de desconto:        14,00%
Perpetuidade:             3,00%

LL 2021:                 R$ 138.660.000
LL 2022:                 R$ 147.101.000
LL 2023:                 R$ 155.084.000
LL 2024:                 R$ 193.670.000
LL 2025:                 R$ 175.073.000

LL 2026:                 R$ 182.321.022,20

VPL 2026:                R$ 159.930.721,23
VPL 2027:                R$ 146.098.116,74
VPL 2028:                R$ 133.461.911,21

Valor Terminal:          ≈ R$ 1,851 bilhão
VPL Perpetuidade:        ≈ R$ 1,391 bilhão

Preço justo:             R$ 17,43
Upside:                  40,26%
```

### TAEE4

``` text
Preço atual:             R$ 12,75
Nº de ações:             1.033.496.721
Market Cap:              R$ 13.177.083.193
Payout:                  69,42%
ROE:                     20,14%
Crescimento:             6,16%
Taxa de desconto:        14,00%
Perpetuidade:             3,00%

LL 2021:                 R$ 2.213.714.000
LL 2022:                 R$ 1.449.215.000
LL 2023:                 R$ 1.367.834.000
LL 2024:                 R$ 1.693.915.000
LL 2025:                 R$ 1.579.863.000

LL 2026:                 R$ 1.677.182.560,80

LL 2027:                 R$ 1.780.497.006,55
LL 2028:                 R$ 1.890.175.622,15

VPL 2026:                R$ 1.471.212.772,63
VPL 2027:                R$ 1.370.034.631,08
VPL 2028:                R$ 1.275.817.405,57

Valor Terminal:          R$ 17.698.917.189,21
VPL Perpetuidade:        R$ 13.297.458.444,18

Valor estimado:          R$ 17.414.523.253,46
Preço justo:             R$ 16,85
Upside:                  32,16%
```

Esses dois casos demonstraram que a lógica pode ser generalizada para
diferentes ativos.

------------------------------------------------------------------------

## 20. Decisões já tomadas

1.  Usaremos somente o **Modo 2 --- Nosso Valuation**.
2.  Não haverá modo de replicação da Ward.
3.  A Ward será somente uma referência conceitual.
4.  O sistema será desenvolvido preferencialmente em Python.
5.  Terá banco de dados.
6.  Terá interface web.
7.  Funcionará para múltiplos ativos.
8.  Histórico financeiro será armazenado.
9.  O LL do ano-base iniciará a projeção.
10. O crescimento será aplicado às projeções.
11. O VPL será calculado automaticamente.
12. A perpetuidade será calculada automaticamente.
13. O preço justo será calculado por ação.
14. Upside/Downside será calculado automaticamente.
15. A taxa de desconto será preenchida inicialmente pela **Selic
    atualizada**.
16. A taxa de desconto poderá ser alterada manualmente.
17. Haverá cenários conservador, base e otimista.
18. Haverá margem de segurança.
19. Haverá análise de sensibilidade.
20. O sistema deverá explicar os cálculos e as premissas.
21. Poderá haver exportação para Excel.
22. O motor matemático será construído e validado antes da interface.
23. Os dados deverão ser cruzados entre fontes sempre que possível.
24. O sistema deverá distinguir métricas contábeis e regulatórias quando
    necessário.

------------------------------------------------------------------------

## 21. Ordem de desenvolvimento

### Etapa 1 --- Motor matemático

Implementar e validar:

-   projeção;
-   desconto;
-   VPL;
-   perpetuidade;
-   preço justo;
-   upside;
-   cenários;
-   margem de segurança.

Validar primeiro com BRBI11 e TAEE4.

### Etapa 2 --- Dados

Implementar:

-   coleta;
-   histórico;
-   atualização;
-   validação das fontes.

### Etapa 3 --- Banco de dados

Estruturar:

-   múltiplos ativos;
-   histórico;
-   indicadores;
-   resultados;
-   valuations.

### Etapa 4 --- Interface

Criar a interface web.

### Etapa 5 --- Cenários e sensibilidade

Adicionar:

-   conservador;
-   base;
-   otimista;
-   matriz de sensibilidade;
-   margem de segurança.

### Etapa 6 --- Exportação

Adicionar exportação para Excel.

------------------------------------------------------------------------

## 22. Visão final

O objetivo não é apenas criar uma calculadora de DCF.

A intenção é criar uma ferramenta própria de análise fundamentalista:

``` text
                    ATIVO
                      ↓
              Coleta de dados
                      ↓
               Histórico
                      ↓
             Indicadores
                      ↓
                Premissas
                      ↓
             Nosso Valuation
                      ↓
        ┌─────────────┼─────────────┐
        ↓             ↓             ↓
  Conservador       Base       Otimista
        └─────────────┼─────────────┘
                      ↓
              Preço justo
                      ↓
            Margem de segurança
                      ↓
             Preço de entrada
                      ↓
             Apoio à decisão
```

O sistema deverá permitir comparar empresas de forma padronizada,
transparente e fundamentada.

------------------------------------------------------------------------

## 23. Próximo passo

Começar pelo **motor matemático do Nosso Valuation em Python**, sem
interface.

A primeira versão deverá receber:

``` text
Lucro Líquido do ano-base
Taxa de crescimento
Taxa de desconto
Crescimento da perpetuidade
Número de anos
Número de ações
Preço atual
```

E retornar:

``` text
Lucro projetado por ano
VPL por ano
Valor Terminal
VPL da perpetuidade
Valor total
Preço justo
Upside / Downside
```

Depois validar os resultados com BRBI11 e TAEE4 antes de avançar para
banco de dados e interface web.
