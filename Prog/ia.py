"""
assistente de voz 100% offline.

Fluxo:
1. escuta o microfone com deteccao automatica de silencio (para de gravar
   sozinho depois de ~2s sem voce falar)
2. transcreve com faster-whisper (offline, sem Google)
3. se for uma conta matematica simples, calcula direto (mais rapido)
4. senao, manda pra IA local (Ollama) e fala a resposta em streaming
   (comeca a falar a primeira frase antes da IA terminar de gerar tudo)
"""

import config
from audio_captura import escutar
from transcricao import carregar_modelo, transcrever
from calculadora import tentar_calcular
from conversa_ia import responder_streaming, responder_completo
from fala import falar

import ollama


def inicializar():
    """carrega os modelos pesados uma vez, antes de comecar o loop principal."""
    print("Inicializando assistente...")
    carregar_modelo()  # carrega o whisper em memoria

    print("Acordando...")
    try:
        ollama.generate(model=config.MODELO_IA, prompt="oi", keep_alive="10m")
    except Exception as e:
        print(f"Aviso: nao consegui acordar o Ollama de antemao ({e}). "
              f"A primeira resposta pode demorar mais.")

    print("Pronto!")


def processar_comando(comando):
    """decide o que fazer com o texto transcrito: sair, calcular ou perguntar pra IA."""
    if any(palavra in comando for palavra in config.PALAVRAS_SAIDA):
        falar("Desligando. Ate mais.")
        return False  # sinaliza pra sair do loop

    resposta_matematica = tentar_calcular(comando)
    if resposta_matematica:
        falar(resposta_matematica)
        return True

    if config.USA_STREAMING_LLM:
        for frase in responder_streaming(comando):
            falar(frase)
    else:
        resposta = responder_completo(comando)
        falar(resposta)

    return True


def main():
    inicializar()
    falar("Sistema iniciado. Pode falar!")

    while True:
        audio = escutar()

        if audio is None:
            # timeout sem detectar fala, so volta a escutar de novo
            continue

        texto = transcrever(audio)

        if not texto:
            print("Nao entendi o audio.")
            continue

        print(f"Voce: {texto}")

        continuar = processar_comando(texto.lower())
        if not continuar:
            break


if __name__ == "__main__":
    main()
