"""
interpreta perguntas de matematica simples faladas em portugues
e calcula o resultado, sem precisar chamar a IA (mais rapido).
"""

import re

_SUBSTITUICOES = {
    r'\bvezes\b': '*',
    r'\bmultiplicado por\b': '*',
    r'\bdividido por\b': '/',
    r'\bdividido\b': '/',
    r'\bmais\b': '+',
    r'\bmenos\b': '-',
    r'\belevado a\b': '**',
    r'\belevado à\b': '**',
    r'\bao quadrado\b': '**2',
    r'\bao cubo\b': '**3',
}

_REMOVER = re.compile(r'\b(quanto é|quanto e|qual é|qual e|o resultado de|calcula|calcule)\b')
_EXPRESSAO_VALIDA = re.compile(r'[\d\s\.\+\-\*/\(\)]+')


def tentar_calcular(pergunta):
    """
    tenta interpretar a pergunta como uma expressao matematica
    retorna a resposta formatada (string) ou None se nao for uma pergunta de matematica.
    """
    texto = pergunta.lower()

    for padrao, simbolo in _SUBSTITUICOES.items():
        texto = re.sub(padrao, simbolo, texto)

    texto = _REMOVER.sub('', texto)

    match = _EXPRESSAO_VALIDA.search(texto)
    if not match:
        return None

    expressao = match.group().strip()
    if not re.search(r'\d', expressao) or not re.search(r'[\+\-\*/]', expressao):
        return None

    try:
        if not re.fullmatch(r'[\d\s\.\+\-\*/\(\)]+', expressao):
            return None
        resultado = eval(expressao, {"__builtins__": {}}, {})
        if isinstance(resultado, float) and resultado.is_integer():
            resultado = int(resultado)
        return f"O resultado e {resultado}"
    except Exception:
        return None
