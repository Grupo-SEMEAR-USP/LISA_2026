FROM ros:jazzy-ros-base

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=America/Sao_Paulo
ENV PYTHONUNBUFFERED=1

SHELL ["/bin/bash", "-c"]

WORKDIR /lisa_ws

# ============================================================
# Dependências do sistema
# ============================================================

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-pip \
    python3-dev \
    python3-setuptools \
    python3-wheel \
    python3-colcon-common-extensions \
    build-essential \
    pkg-config \
    portaudio19-dev \
    libasound2-dev \
    libpulse0 \
    libsndfile1 \
    pulseaudio-utils \
    alsa-utils \
    v4l-utils \
    mpv \
    x11-utils \
    xauth \
    libgl1 \
    libegl1 \
    libgles2 \
    libgbm1 \
    libdrm2 \
    libglib2.0-0 \
    libgtk-3-0 \
    libx11-6 \
    libx11-xcb1 \
    libxcb1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libxinerama1 \
    libxcursor1 \
    libxi6 \
    libxkbcommon0 \
    libwayland-client0 \
    libwayland-egl1 \
    ros-jazzy-example-interfaces \
    ros-jazzy-cv-bridge \
    ros-jazzy-geometry-msgs \
    ros-jazzy-sensor-msgs \
    ros-jazzy-std-msgs \
    && rm -rf /var/lib/apt/lists/*


# ============================================================
# Dependências Python
#
# Mantemos as mesmas versões usadas no projeto.
# ============================================================

COPY docker/requirements.txt /tmp/requirements.txt

RUN python3 -m pip install \
    --break-system-packages \
    --no-cache-dir \
    -r /tmp/requirements.txt


# ============================================================
# Dependências do MediaPipe
#
# O MediaPipe 0.10.32 declara essas dependências.
# Elas são instaladas explicitamente para impedir que o pip
# tente substituir o NumPy 1.26.4 pelo NumPy 2.x.
# ============================================================

RUN python3 -m pip install \
    --break-system-packages \
    --no-cache-dir \
    'numpy==1.26.4' \
    'absl-py~=2.3' \
    'flatbuffers~=25.9' \
    'sounddevice~=0.5' \
    'matplotlib'


# ============================================================
# MediaPipe
#
# --no-deps é intencional:
# as dependências já foram instaladas acima com as versões
# compatíveis com o restante do projeto.
# ============================================================

RUN python3 -m pip install \
    --break-system-packages \
    --no-cache-dir \
    --no-deps \
    'mediapipe==0.10.32'


# ============================================================
# Código ROS 2
# ============================================================

COPY src /lisa_ws/src

RUN source /opt/ros/jazzy/setup.bash && \
    colcon build --symlink-install

RUN mkdir -p /tmp/lisa-home/.ros /tmp/lisa-cache && \
    chown -R 1000:1000 /tmp/lisa-home /tmp/lisa-cache

# ============================================================
# Entrypoint
# ============================================================

COPY docker/entrypoint.sh /entrypoint.sh

RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]

CMD ["ros2", "launch", "lisa_bringup", "lisa.launch.py"]