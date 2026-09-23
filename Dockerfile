FROM ros:jazzy-ros-base

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=America/Sao_Paulo
ENV PYTHONUNBUFFERED=1

SHELL ["/bin/bash", "-c"]

# ============================================================
# Dependências do sistema
# ============================================================

RUN apt-get update && apt-get install -y \
    python3-pip \
    python3-dev \
    python3-setuptools \
    python3-wheel \
    build-essential \
    pkg-config \
    portaudio19-dev \
    libasound2-dev \
    libsndfile1 \
    pulseaudio-utils \
    alsa-utils \
    v4l-utils \
    mpv \
    libgl1 \
    libglib2.0-0 \
    libgtk-3-0 \
    libx11-xcb1 \
    libxcb1 \
    libxrandr2 \
    libxinerama1 \
    libxcursor1 \
    libxi6 \
    ros-jazzy-example-interfaces \
    ros-jazzy-cv-bridge \
    && rm -rf /var/lib/apt/lists/*

# ============================================================
# Workspace
# ============================================================

WORKDIR /lisa_ws

COPY docker/requirements.txt /tmp/requirements.txt

# ============================================================
# Python
# ============================================================

RUN python3 -m pip install \
    --break-system-packages \
    --no-cache-dir \
    -r /tmp/requirements.txt

# ============================================================
# Código ROS
# ============================================================

COPY Prog /lisa_ws/src

# ============================================================
# Build
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

