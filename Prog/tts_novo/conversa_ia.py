"""
conversa com o modelo de IA local via Ollama.
suporta streaming: gera a resposta e ja retorna pedacos (frases)
conforme ficam prontos, pra falar mais rapido em vez de esperar tudo.
"""

import re
import ollama
import config

PROMPT_SISTEMA = (
    "Voce e uma assistente de voz em portugues do Brasil. "
    "Responda de forma natural, como numa conversa falada. "
    "Para perguntas simples, responda direto e curto. "
    "Para perguntas que exigem raciocinio ou explicacao, "
    "de uma resposta completa e correta. "
    "Nunca use listas com marcadores, asteriscos ou formatacao de texto, "
    "porque sua resposta vai ser falada em voz alta."
)

# separador de frases pra streaming: corta em . ! ? seguido de espaco ou fim de string
_SEPARADOR_FRASE = re.compile(r'(?<=[.!?])\s+')


def _limpar_texto(texto):
    """Remove marcacoes que nao fazem sentido em audio."""
    texto = texto.replace('*', '').replace('#', '').replace('`', '')
    texto = re.sub(r'<think>.*?</think>', '', texto, flags=re.DOTALL)
    return texto.strip()


def responder_streaming(pergunta):
    """
    gerador que produz frases completas conforme a IA vai respondendo.
    isso permite comecar a falar a primeira frase antes do modelo
    terminar de gerar a resposta inteira.

    uso:
        for frase in responder_streaming("qual a capital da franca"):
            falar(frase)
    """
    buffer = ""
    try:
        stream = ollama.chat(
            model=config.MODELO_IA,
            messages=[
                {"role": "system", "content": PROMPT_SISTEMA},
                {"role": "user", "content": pergunta},
            ],
            stream=True,
        )

        for pedaco in stream:
            conteudo = pedaco["message"]["content"]
            buffer += conteudo

            partes = _SEPARADOR_FRASE.split(buffer)
            # a ultima parte pode estar incompleta (frase ainda sendo gerada),
            # entao so libera as partes anteriores e guarda a ultima no buffer
            if len(partes) > 1:
                for frase in partes[:-1]:
                    frase_limpa = _limpar_texto(frase)
                    if frase_limpa:
                        yield frase_limpa
                buffer = partes[-1]

        # libera o que sobrou no buffer no final
        resto = _limpar_texto(buffer)
        if resto:
            yield resto

    except Exception as e:
        print(f"Erro no Ollama: {e}")
        yield "Deu um erro no meu cerebro interno."


def responder_completo(pergunta):
    """
    versao sem streaming: espera a resposta inteira e retorna de uma vez.
    usa isso se quiser desabilitar o streaming (config.USA_STREAMING_LLM = False).
    """
    try:
        resposta = ollama.chat(
            model=config.MODELO_IA,
            messages=[
                {"role": "system", "content": PROMPT_SISTEMA},
                {"role": "user", "content": pergunta},
            ],
        )
        return _limpar_texto(resposta["message"]["content"])
    except Exception as e:
        print(f"Erro no Ollama: {e}")
        return "Deu um erro no meu cerebro interno."
