"""
captura de audio do microfone com deteccao automatica de fala/silencio.

ssa sounddevice (baseado em PortAudio) em vez de PyAudio
-> evita o crash que acontecia com speech_recognition + PyAudio,
que tinha conflito de gerenciamento de stream com o PipeWire.

a cada chamada de escutar(), o fluxo e:
1. calibra o ruido ambiente por 1s pra saber o que e "silencio"
2. comeca a gravar continuamente em blocos pequenos (30ms)
3. quando detecta energia acima do limiar, marca que "comecou a falar"
4. depois que comecou a falar, conta quanto tempo fica em silencio
5. se ficar em silencio por SILENCIO_SEGUNDOS, corta a gravacao e retorna
6. se nunca detectar fala dentro de TIMEOUT_SEM_FALA, retorna None
"""

import time
import numpy as np
import sounddevice as sd
import config


def _calcula_rms(bloco):
    """calcula a energia (RMS) de um bloco de audio."""
    if bloco.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(bloco.astype(np.float64) ** 2)))


def _abrir_stream_com_retry(tamanho_bloco, tentativas=3, espera_segundos=0.5):
    """
    tenta abrir o InputStream, com algumas tentativas de retry.
    """
    ultimo_erro = None
    for tentativa in range(1, tentativas + 1):
        try:
            return sd.InputStream(
                samplerate=config.SAMPLE_RATE,
                channels=1,
                dtype="int16",
                blocksize=tamanho_bloco,
            )
        except sd.PortAudioError as e:
            ultimo_erro = e
            print(f"   aviso: falha ao abrir microfone (tentativa {tentativa}/{tentativas}): {e}")
            time.sleep(espera_segundos)
    raise ultimo_erro


def escutar():
    """
    escuta o microfone e retorna o audio capturado como array numpy (int16, mono, 16kHz),
    pronto pra passar direto pro faster-whisper.

    retorna None se nao detectar nenhuma fala dentro do timeout.

    abre UM UNICO InputStream que serve tanto pra calibracao do ruido
    ambiente quanto pra gravacao. abrir/fechar o dispositivo de audio
    varias vezes seguidas por chamada e o tipo de padrao que costuma
    gerar conflito com o PipeWire, entao evitamos isso aqui.
    """
    tamanho_bloco = int(config.BLOCK_DURATION * config.SAMPLE_RATE)
    blocos_calibracao = max(1, int(config.DURACAO_CALIBRACAO_RUIDO / config.BLOCK_DURATION))
    blocos_silencio_necessarios = int(config.SILENCIO_SEGUNDOS / config.BLOCK_DURATION)
    blocos_timeout = int(config.TIMEOUT_SEM_FALA / config.BLOCK_DURATION)

    frames = []
    comecou_a_falar = False
    contador_silencio = 0
    total_blocos = 0
    limiar = None

    try:
        stream = _abrir_stream_com_retry(tamanho_bloco)
    except Exception as e:
        print(f"Erro ao abrir o microfone mesmo apos tentativas: {e}")
        print("Aguardando 2s e voltando a tentar no proximo ciclo...")
        time.sleep(2)
        return None

    with stream:
        # --- fase 1: calibracao do ruido ambiente, usando o mesmo stream ---
        print(f"Calibrando ruido ambiente ({config.DURACAO_CALIBRACAO_RUIDO:.1f}s, fica quieto)...")
        blocos_calibracao_capturados = []
        for _ in range(blocos_calibracao):
            bloco, _overflow = stream.read(tamanho_bloco)
            blocos_calibracao_capturados.append(bloco.flatten())

        energia_ambiente = _calcula_rms(np.concatenate(blocos_calibracao_capturados))
        limiar = max(energia_ambiente * config.LIMIAR_ENERGIA_MULTIPLICADOR, 150)
        print(f"   ruido ambiente: {energia_ambiente:.0f} | limiar definido: {limiar:.0f}")

        # --- fase 2: escuta de verdade, com deteccao de fala/silencio ---
        print("Pode falar, to ouvindo...")
        while True:
            bloco, _overflow = stream.read(tamanho_bloco)
            bloco = bloco.flatten()
            frames.append(bloco)
            total_blocos += 1

            energia = _calcula_rms(bloco)

            if energia > limiar:
                comecou_a_falar = True
                contador_silencio = 0
            elif comecou_a_falar:
                contador_silencio += 1

            if comecou_a_falar and contador_silencio >= blocos_silencio_necessarios:
                tempo_falado = total_blocos * config.BLOCK_DURATION
                print(f"   fim da fala detectado (gravacao total: {tempo_falado:.1f}s)")
                break

            if not comecou_a_falar and total_blocos >= blocos_timeout:
                print("   nenhuma fala detectada, desistindo por timeout")
                return None

    audio_completo = np.concatenate(frames)
    return audio_completo
