FROM ros:jazzy-ros-base

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=America/Sao_Paulo
ENV PYTHONUNBUFFERED=1

SHELL ["/bin/bash", "-c"]

WORKDIR /lisa_ws

# ============================================================
# Dependências do sistema
# ============================================================
#
# A captura de voz da LISA usa pactl + parec (PulseAudio API,
# normalmente fornecida pelo pipewire-pulse no Ubuntu 24.04).
# O mpv é usado pelo controle_tela para exibir os GIFs.
#
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
# Dependências Python comuns
# ============================================================

COPY docker/requirements.txt /tmp/requirements.txt

RUN python3 -m pip install \
    --break-system-packages \
    --no-cache-dir \
    -r /tmp/requirements.txt

# ============================================================
# MediaPipe
# ============================================================
#
# O MediaPipe 0.10.32 não possui wheel Linux ARM64. Para a
# Raspberry Pi 5 (aarch64), ele é compilado a partir do código
# fonte. Em amd64, usamos a wheel oficial.
#
# O projeto usa somente CPU, portanto o build ARM desabilita GPU.
# O --link-opencv reutiliza o OpenCV já instalado pelo requirements.
#
RUN set -eux; \
    arch="$(dpkg --print-architecture)"; \
    if [ "$arch" = "arm64" ]; then \
        apt-get update; \
        apt-get install -y --no-install-recommends \
            git \
            curl \
            ca-certificates \
            openjdk-17-jdk-headless \
            protobuf-compiler; \
        rm -rf /var/lib/apt/lists/*; \
        curl -fsSL \
            https://github.com/bazelbuild/bazelisk/releases/download/v1.29.0/bazelisk-arm64.deb \
            -o /tmp/bazelisk.deb; \
        echo "db8ada89c841afd2cb33db7d13aa98ea4fb14612579a8bae84722250caa84272  /tmp/bazelisk.deb" | sha256sum -c -; \
        dpkg -i /tmp/bazelisk.deb; \
        rm -f /tmp/bazelisk.deb; \
        if ! command -v bazel >/dev/null 2>&1; then \
            ln -sf "$(command -v bazelisk)" /usr/local/bin/bazel; \
        fi; \
        git clone --depth 1 --branch v0.10.32 \
            https://github.com/google-ai-edge/mediapipe.git /tmp/mediapipe; \
        echo 'build --jobs=4' >> /tmp/mediapipe/.bazelrc; \
        python3 -m pip install \
            --break-system-packages \
            --no-cache-dir \
            'absl-py~=2.3' \
            'sounddevice~=0.5' \
            'flatbuffers~=25.9' \
            matplotlib; \
        cd /tmp/mediapipe; \
        MEDIAPIPE_DISABLE_GPU=1 \
            python3 setup.py install --link-opencv; \
        cd /lisa_ws; \
        rm -rf /tmp/mediapipe /root/.cache/bazel /root/.cache/pip; \
    else \
        python3 -m pip install \
            --break-system-packages \
            --no-cache-dir \
            'mediapipe==0.10.32'; \
    fi

# ============================================================
# Código ROS 2
# ============================================================
# O contexto do build é Prog/. Portanto, o código fica em src/.

COPY src /lisa_ws/src

# ============================================================
# Build do workspace
# ============================================================

RUN source /opt/ros/jazzy/setup.bash && \
    colcon build --symlink-install

# ============================================================
# Entrypoint
# ============================================================

COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]

CMD ["ros2", "launch", "lisa_bringup", "lisa.launch.py"]
