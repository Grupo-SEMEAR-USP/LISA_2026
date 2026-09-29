#!/bin/bash

# ============================================================
# LISA 2026 - Executar Docker
# ============================================================

set -e

cd "$(dirname "$0")"

echo "=============================================="
echo "             LISA 2026 - Docker"
echo "=============================================="

# ------------------------------------------------------------
# Verificar Docker
# ------------------------------------------------------------

if ! command -v docker >/dev/null 2>&1; then
    echo "ERRO: Docker não está instalado ou não está no PATH."
    exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
    echo "ERRO: Docker Compose não está disponível."
    exit 1
fi

# ------------------------------------------------------------
# Verificar Git
# ------------------------------------------------------------

if ! command -v git >/dev/null 2>&1; then
    echo "AVISO: Git não foi encontrado."
    echo "O script ainda pode funcionar se o projeto já estiver baixado."
fi

# ------------------------------------------------------------
# Configurar UID
# ------------------------------------------------------------

export USER_ID="$(id -u)"

echo
echo "USER_ID: $USER_ID"

# ------------------------------------------------------------
# Verificar DISPLAY
# ------------------------------------------------------------

if [ -z "${DISPLAY:-}" ]; then
    echo
    echo "AVISO: DISPLAY não está definido."
    echo "A interface gráfica da LISA pode não funcionar."
else
    echo "DISPLAY: $DISPLAY"
fi

# ------------------------------------------------------------
# Liberar X11
# ------------------------------------------------------------

if command -v xhost >/dev/null 2>&1; then
    echo
    echo "Configurando acesso à interface gráfica..."
    xhost +local:docker >/dev/null 2>&1 || \
        echo "AVISO: não foi possível configurar o acesso X11."
else
    echo
    echo "AVISO: xhost não encontrado."
    echo "A interface gráfica pode não funcionar."
fi

# ------------------------------------------------------------
# Verificar câmera
# ------------------------------------------------------------

echo
echo "=============================================="
echo "             Verificando câmera"
echo "=============================================="

if compgen -G "/dev/video*" > /dev/null; then
    ls -l /dev/video*
else
    echo "AVISO: nenhuma câmera /dev/video* encontrada."
fi

# ------------------------------------------------------------
# Verificar áudio
# ------------------------------------------------------------

echo
echo "=============================================="
echo "             Verificando áudio"
echo "=============================================="

if command -v pactl >/dev/null 2>&1; then
    if pactl info >/dev/null 2>&1; then
        echo "Servidor de áudio acessível."
    else
        echo "AVISO: servidor PulseAudio/PipeWire não respondeu."
    fi
fi

# ------------------------------------------------------------
# Escolher modo
# ------------------------------------------------------------

BUILD=false

if [ "${1:-}" = "--build" ]; then
    BUILD=true
elif [ "${1:-}" != "" ]; then
    echo
    echo "Uso:"
    echo "  ./run_docker.sh"
    echo "  ./run_docker.sh --build"
    exit 1
fi

# ------------------------------------------------------------
# Executar Docker Compose
# ------------------------------------------------------------

echo
echo "=============================================="
echo "             Iniciando LISA"
echo "=============================================="
echo

if [ "$BUILD" = true ]; then
    docker compose up --build
else
    docker compose up
fi
