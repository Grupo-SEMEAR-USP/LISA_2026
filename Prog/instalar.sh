#!/bin/bash
# Script de instalacao das dependencias do assistente de voz offline.
# Roda isso uma vez, dentro do seu virtualenv (source env/bin/activate).

set -e

echo "=== Instalando dependencias de sistema (precisa de sudo) ==="
sudo apt-get update
sudo apt-get install -y portaudio19-dev alsa-utils

echo ""
echo "=== Instalando dependencias Python ==="
pip install faster-whisper sounddevice numpy ollama

echo ""
echo "=== Verificando se o Piper esta instalado ==="
if ! command -v piper &> /dev/null; then
    echo "Piper nao encontrado. Instalando via pip..."
    pip install piper-tts
else
    echo "Piper ja esta instalado."
fi

echo ""
echo "=== Verificando se o Ollama esta instalado ==="
if ! command -v ollama &> /dev/null; then
    echo "AVISO: Ollama nao encontrado no PATH."
    echo "Instale com: curl -fsSL https://ollama.com/install.sh | sh"
else
    echo "Ollama ja esta instalado."
    echo "Baixando o modelo llama3.2:3b (pode demorar um pouco)..."
    ollama pull llama3.2:3b
fi

echo ""
echo "=== Instalacao concluida! ==="
echo "Antes de rodar, confira se o arquivo pt_BR-faber-medium.onnx (voz do Piper)"
echo "esta na mesma pasta do ia.py."
echo ""
echo "Pra rodar: python3 ia.py"
