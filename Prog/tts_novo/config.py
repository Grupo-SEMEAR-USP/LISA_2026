"""
configuracao central do assistente de voz.
mexe so aqui se quiser trocar modelo, ajustar tempos, etc.
"""

# === MODELO DE VOZ (TTS) ===
MODELO_VOZ = "pt_BR-faber-medium.onnx"

# === MODELO DE IA (LLM via Ollama) ===
# llama3.2:3b = mais rapido, respostas em ~2s pra perguntas diretas
# qwen2.5:7b  = mais lento mas respostas mais completas/melhores
MODELO_IA = "llama3.2:3b"

# === MODELO DE TRANSCRICAO (STT via faster-whisper) ===
# tiny   = mais rapido, menos preciso
# base   = bom equilibrio (recomendado pro seu hardware)
# small  = mais preciso, mais lento
WHISPER_MODELO = "base"
WHISPER_IDIOMA = "pt"

# === DETECCAO DE FALA/SILENCIO (VAD) ===
SAMPLE_RATE = 16000          # taxa de amostragem, 16kHz e o padrao pro whisper
BLOCK_DURATION = 0.03        # 30ms por bloco de audio capturado
SILENCIO_SEGUNDOS = 2.0      # quanto tempo de silencio espera antes de considerar que parou de falar
TIMEOUT_SEM_FALA = 10.0      # se nao detectar nenhuma fala em X segundos, desiste e volta a escutar
LIMIAR_ENERGIA_MULTIPLICADOR = 1.8  # multiplica o ruido ambiente medido pra definir o que conta como "fala"
DURACAO_CALIBRACAO_RUIDO = 1.0      # quantos segundos escuta o ambiente em silencio pra calibrar o limiar

# === COMPORTAMENTO DO ASSISTENTE ===
PALAVRAS_SAIDA = ["sair", "desligar", "tchau", "encerrar"]
USA_STREAMING_LLM = True     # fala a resposta em pedacos conforme a IA gera, em vez de esperar tudo pronto
