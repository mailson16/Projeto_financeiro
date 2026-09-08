# Nosso Valuation

Sistema de acompanhamento de clientes e valuation por DCF ("Modo 2 — Nosso
Valuation") para ações da B3. Regras de negócio completas em
`nosso_valuation_aprendizado.md`.

## Como rodar

```powershell
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
copy .env.example .env   # BRAPI_TOKEN e opcional - ver secao "Fontes de dados" abaixo
.\.venv\Scripts\python -m pytest tests\ -q     # roda a suite de testes
.\.venv\Scripts\streamlit run app/Home.py      # abre a interface web
```

## Fontes de dados fundamentalistas

A busca automática de preço/nº de ações/Lucro Líquido/indicadores tenta,
nesta ordem (ver `services/market_data_service.py`, seção 18 do doc: não
depender de uma única fonte):

1. **statusinvest.com.br** (`data/providers/statusinvest.py`) — scraping da
   página pública do ativo + dois endpoints internos do site
   (`/acao/indicatorhistorical` e `/acao/payoutresult`). **Não exige token**
   e funciona para qualquer ticker, inclusive os menores (BRBI11, TAEE4,
   ITSA4, TAEE11 etc.). Os campos extraídos e os seletores usados estão
   documentados no topo do arquivo; os valores foram validados ao vivo
   contra os números de BRBI11 e TAEE4 registrados na seção 6/19 do doc
   (bateram exatamente).
2. **brapi.dev** (`data/providers/brapi.py`) — usado como fallback caso o
   statusinvest falhe ou mude de layout. Testando ao vivo, confirmamos que
   **o acesso anônimo (sem token) só funciona para alguns tickers de grande
   liquidez (ex.: PETR4)** — tickers menores retornam 401 sem um token. Se
   quiser esse fallback funcionando, crie uma conta gratuita em
   https://brapi.dev, gere um token e coloque em `.env`:

   ```
   BRAPI_TOKEN=seu_token_aqui
   ```

Se as duas fontes falharem, a Watchlist ainda cadastra o ativo normalmente,
mas a busca automática de dados falha silenciosamente (mostra um aviso) e a
tela de Valuation pede para os dados serem preenchidos manualmente ou para
tentar atualizar de novo depois. A Selic (usada para a taxa de desconto) é
buscada na API do Banco Central e não precisa de token.

> **Nota sobre o statusinvest.com.br:** o site bloqueia clientes HTTP com
> fingerprint TLS "não humano" (confirmado: um `Invoke-WebRequest`/.NET
> `HttpClient` com User-Agent de navegador ainda leva 403; `curl`/`requests`
> puros funcionam normalmente). Se essa fonte começar a falhar em produção,
> verifique primeiro se não é um bloqueio desse tipo antes de assumir que o
> layout mudou.

## Decisão de design: desconto da perpetuidade

O motor (`valuation/constants.py` e `valuation/engine.py`) desconta o
Valor Terminal usando o mesmo número de anos da projeção (N), seguindo a
convenção financeira padrão — não a convenção observada na ferramenta de
referência "Ward" (que usa um número fracionário de períodos). Por isso,
o preço justo final calculado para BRBI11/TAEE4 é diferente dos números
publicados na seção 19 do doc; ver a nota no topo de `tests/test_engine.py`
para os detalhes de como isso foi verificado.

## Estrutura

Ver `nosso_valuation_aprendizado.md` (seções 16-17) e o plano de
implementação para o racional completo. Resumo:

- `valuation/` — motor puro de DCF (sem I/O), testado isoladamente.
- `data/` — clientes de fontes externas (Selic, statusinvest.com.br, brapi.dev).
- `db/` — modelos SQLAlchemy e acesso a dados (SQLite por padrão).
- `services/` — liga motor + dados + banco.
- `app/` — interface Streamlit (Home + páginas Clientes, Watchlist,
  Valuation, Cenários e Sensibilidade, Explicação).
- `tests/` — suíte pytest (55 testes, ~1s, sem chamadas de rede reais).
