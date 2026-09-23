#!/bin/bash

set -e

source /opt/ros/jazzy/setup.bash
source /lisa_ws/install/setup.bash

echo "=============================================="
echo "              LISA 2026"
echo "=============================================="

echo
echo "Python:"
python3 --version

echo
echo "ROS 2:"
ros2 pkg list >/dev/null && echo "ROS 2 OK"

echo
echo "OpenCV:"
python3 -c "import cv2; print(cv2.__version__)"

echo
echo "MediaPipe:"
python3 -c "import mediapipe as mp; print(mp.__version__)"

echo
echo "NumPy:"
python3 -c "import numpy; print(numpy.__version__)"

echo
echo "Vosk:"
python3 -c "import vosk; print('0.3.45')"

echo
echo "PyAudio:"
python3 -c "import pyaudio; print(pyaudio.__version__)"

echo
echo "=============================================="
echo "Dispositivos de câmera:"
echo "=============================================="
ls -l /dev/video* 2>/dev/null || echo "Nenhuma câmera encontrada."

echo
echo "=============================================="
echo "Dispositivos de áudio:"
echo "=============================================="
aplay -l 2>/dev/null || true
arecord -l 2>/dev/null || true

echo
echo "=============================================="
echo "PulseAudio/PipeWire:"
echo "=============================================="
pactl info 2>/dev/null || echo "Servidor PulseAudio não acessível."

echo
echo "=============================================="
echo "Iniciando LISA..."
echo "=============================================="

exec "$@"
