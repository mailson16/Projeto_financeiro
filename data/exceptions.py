class FonteDadosIndisponivelError(Exception):
    """A fonte externa nao respondeu, respondeu com erro, ou deu timeout."""


class DadosIncompletosError(Exception):
    """A fonte respondeu, mas o payload nao trouxe o campo esperado."""


class TokenNaoConfiguradoError(Exception):
    """A fonte exige um token/chave que nao foi configurado no ambiente."""
