"""
transcricao de audio para texto usando faster-whisper.
100% offline, nao depende do Google.
"""

import numpy as np
from faster_whisper import WhisperModel
import config

_modelo = None


def carregar_modelo():
    """
    carrega o modelo whisper uma unica vez (fica em memoria).
    chama isso no inicio do programa, nao a cada transcricao.
    """
    global _modelo
    if _modelo is None:
        print(f"Carregando modelo de transcricao ({config.WHISPER_MODELO})...")
        _modelo = WhisperModel(
            config.WHISPER_MODELO,
            device="cpu",
            compute_type="int8",  # int8 e bem mais rapido em CPU, com perda minima de qualidade
        )
        print("Modelo de transcricao carregado!")
    return _modelo


def transcrever(audio_int16):
    """
    recebe um array numpy int16 (mono, 16kHz) e retorna o texto transcrito.
    retorna string vazia se nao conseguir transcrever nada.
    """
    if audio_int16 is None or audio_int16.size == 0:
        return ""

    modelo = carregar_modelo()

    # faster-whisper espera float32 normalizado entre -1 e 1
    audio_float32 = audio_int16.astype(np.float32) / 32768.0

    segmentos, _info = modelo.transcribe(
        audio_float32,
        language=config.WHISPER_IDIOMA,
        vad_filter=True,  # filtro de silencio interno do whisper, reduz alucinacao em trechos mudos
        beam_size=1,       # beam_size baixo = mais rapido, com perda pequena de precisao
    )

    texto = " ".join(segmento.text.strip() for segmento in segmentos)
    return texto.strip()
