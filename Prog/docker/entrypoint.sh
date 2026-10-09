#!/usr/bin/env bash

set -euo pipefail

# O setup do ROS 2 Jazzy pode acessar variáveis não definidas.
# Por isso, desativamos temporariamente o "nounset" (-u).
set +u
source /opt/ros/jazzy/setup.bash
source /lisa_ws/install/setup.bash
set -u

# HOME/ROS log para o usuário usado pelo container.
mkdir -p "$HOME" "$XDG_CACHE_HOME" "$HOME/.ros"
export ROS_LOG_DIR="${ROS_LOG_DIR:-$HOME/.ros/log}"

# print_section() {
#     echo
#     echo "=============================================="
#     echo "$1"
#     echo "=============================================="
# }

# echo "=============================================="
# echo "              LISA v3"
# echo "=============================================="

# echo
# echo "Python:"
# python3 --version

# echo
# echo "ROS 2:"
# ros2 pkg list >/dev/null && echo "ROS 2 OK"

# echo
# echo "OpenCV:"
# python3 -c "import cv2; print(cv2.__version__)"

# echo
# echo "MediaPipe:"
# python3 -c "import mediapipe as mp; print(mp.__version__)"

# echo
# echo "NumPy:"
# python3 -c "import numpy; print(numpy.__version__)"

# echo
# echo "Vosk:"
# python3 -c "import vosk; print(vosk.__version__ if hasattr(vosk, '__version__') else '0.3.45')"

# echo
# echo "Unidecode:"
# python3 -c "import unidecode; print(unidecode.__version__ if hasattr(unidecode, '__version__') else 'OK')"

# echo
# echo "mpv:"
# mpv --version | head -n 1 || true

# print_section "Dispositivos de câmera"
# ls -l /dev/video* 2>/dev/null || echo "Nenhuma câmera encontrada."

# print_section "Dispositivos de áudio ALSA"
# aplay -l 2>/dev/null || true
# arecord -l 2>/dev/null || true

# print_section "PulseAudio / PipeWire-pulse"
# if command -v pactl >/dev/null 2>&1; then
#     if pactl info >/dev/null 2>&1; then
#         echo "Servidor de áudio acessível."
#         echo
#         echo "Servidor:"
#         pactl info | grep -E 'Server Name|Server String|Default Source|Default Sink' || true
#         echo
#         echo "Fontes disponíveis:"
#         pactl list short sources || true
#         echo
#         echo "Fonte padrão:"
#         pactl get-default-source || true
#     else
#         echo "AVISO: servidor PulseAudio/PipeWire não respondeu."
#         echo "O detector_comandos_de_voz não conseguirá usar o microfone."
#     fi
# else
#     echo "ERRO: pactl não encontrado."
# fi

# print_section "Tela X11 / XWayland"
# echo "DISPLAY: ${DISPLAY:-não definido}"
# echo "XAUTHORITY: ${XAUTHORITY:-não definido}"

# if command -v xdpyinfo >/dev/null 2>&1; then
#     if xdpyinfo >/dev/null 2>&1; then
#         echo "Servidor X11/XWayland acessível."
#         xdpyinfo | grep -E 'dimensions|resolution' || true
#     else
#         echo "AVISO: não foi possível acessar o servidor X11/XWayland."
#         echo "Os GIFs do controle_tela não poderão ser exibidos."
#     fi
# fi

echo
echo "=============================================="
echo "Iniciando LISA..."
echo "=============================================="

exec "$@"