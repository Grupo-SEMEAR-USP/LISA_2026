#!/usr/bin/env bash

# ============================================================
# LISA v3 - Executar Docker
# ============================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

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
# UID/GID do host
# ------------------------------------------------------------

export USER_ID="$(id -u)"
export GROUP_ID="$(id -g)"
export USER_NAME="$(id -un)"

# ------------------------------------------------------------
# Display
# ------------------------------------------------------------
# Em Raspberry Pi com sessão gráfica local, normalmente é :0.
# Em Ubuntu usando Wayland, o X11 usado pelo mpv passa pelo XWayland.

export DISPLAY="${DISPLAY:-:0}"

if [ ! -d /tmp/.X11-unix ]; then
    echo "AVISO: /tmp/.X11-unix não existe."
    echo "A interface gráfica pode não funcionar."
fi

# echo
# echo "UID:      $USER_ID"
# echo "GID:      $GROUP_ID"
# echo "DISPLAY:  $DISPLAY"

# ------------------------------------------------------------
# XAUTHORITY
# ------------------------------------------------------------

TEMP_XAUTH=""

if [ -n "${XAUTHORITY:-}" ] && [ -f "${XAUTHORITY}" ]; then
    export XAUTHORITY_FILE="$XAUTHORITY"
elif [ -f "${HOME}/.Xauthority" ]; then
    export XAUTHORITY_FILE="${HOME}/.Xauthority"
else
    XWAYLAND_XAUTH=""

    if [ -d "/run/user/${USER_ID}" ]; then
        XWAYLAND_XAUTH="$(find "/run/user/${USER_ID}" \
            -maxdepth 1 \
            -type f \
            -name '.mutter-Xwaylandauth.*' \
            -print -quit 2>/dev/null || true)"
    fi

    if [ -n "$XWAYLAND_XAUTH" ] && [ -f "$XWAYLAND_XAUTH" ]; then
        export XAUTHORITY_FILE="$XWAYLAND_XAUTH"
    else
        TEMP_XAUTH="/tmp/lisa-docker-xauth-${USER_ID}"
        touch "$TEMP_XAUTH"
        chmod 600 "$TEMP_XAUTH"
        export XAUTHORITY_FILE="$TEMP_XAUTH"
        echo "AVISO: nenhum arquivo XAUTHORITY foi encontrado."
        echo "Tentando acesso ao X11/XWayland por xhost."
    fi
fi

# echo "XAUTHORITY: $XAUTHORITY_FILE"

# xhost é um fallback para ambientes em que o cookie não é suficiente.
XHOST_MODE=""
if command -v xhost >/dev/null 2>&1; then
    export XAUTHORITY="$XAUTHORITY_FILE"

    if xhost +SI:localuser:"$USER_NAME" >/dev/null 2>&1; then
        XHOST_MODE="localuser"
    elif xhost +local:docker >/dev/null 2>&1; then
        XHOST_MODE="docker"
    else
        echo "AVISO: não foi possível liberar o acesso X11 com xhost."
    fi
fi

# ------------------------------------------------------------
# PulseAudio / PipeWire-pulse
# ------------------------------------------------------------

export VIDEO_GID="$(getent group video | cut -d: -f3)"

export PULSE_SOCKET_DIR="/run/user/${USER_ID}/pulse"
export PULSE_CONFIG_DIR="${HOME}/.config/pulse"

# O diretório é usado também para disponibilizar o cookie ao container.
mkdir -p "$PULSE_CONFIG_DIR"

if [ -S "${PULSE_SOCKET_DIR}/native" ]; then
    # echo "PulseAudio/PipeWire-pulse: socket encontrado em ${PULSE_SOCKET_DIR}/native"
    : 
else
    echo "AVISO: socket ${PULSE_SOCKET_DIR}/native não encontrado."
    echo "O detector_comandos_de_voz poderá iniciar sem microfone funcional."
fi

# ------------------------------------------------------------
# Câmera
# ------------------------------------------------------------

# echo
# echo "=============================================="
# echo "             Verificando câmera"
# echo "=============================================="

if compgen -G "/dev/video*" > /dev/null; then
    #ls -l /dev/video*
    :
else
    echo "AVISO: nenhuma câmera /dev/video* encontrada."
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
# Limpeza do acesso X11 temporário
# ------------------------------------------------------------

cleanup() {
    if command -v xhost >/dev/null 2>&1; then
        case "$XHOST_MODE" in
            localuser)
                xhost -SI:localuser:"$USER_NAME" >/dev/null 2>&1 || true
                ;;
            docker)
                xhost -local:docker >/dev/null 2>&1 || true
                ;;
        esac
    fi

    if [ -n "$TEMP_XAUTH" ]; then
        rm -f "$TEMP_XAUTH"
    fi
}

trap cleanup EXIT INT TERM

# ------------------------------------------------------------
# Executar Docker Compose
# ------------------------------------------------------------

echo
echo "=============================================="
echo "             LISA v3 - Docker"
echo "=============================================="
echo

if [ "$BUILD" = true ]; then
    docker compose up --build
else
    docker compose up
fi
