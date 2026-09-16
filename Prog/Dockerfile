FROM ros:jazzy-ros-base

SHELL ["/bin/bash", "-c"]

ENV DEBIAN_FRONTEND=noninteractive
ENV ROS_DISTRO=jazzy

RUN apt-get update && apt-get install -y --no-install-recommends \
    portaudio19-dev \
    alsa-utils \
    espeak-ng \
    mpv \
    libgl1 \
    libglib2.0-0 \
    python3-pip \
    python3-colcon-common-extensions \
    ros-jazzy-cv-bridge \
    ros-jazzy-vision-opencv \
    ros-jazzy-launch \
    ros-jazzy-launch-ros \
    ros-jazzy-example-interfaces \
    git \
    wget \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --break-system-packages --no-cache-dir \
    numpy soundfile sounddevice ollama faster-whisper kokoro

RUN pip3 install --break-system-packages --no-cache-dir \
    opencv-python mediapipe==0.10.21 vosk

WORKDIR /root/lisa_ws/src
COPY joao_prog/lisa_bringup ./lisa_bringup
COPY joao_prog/lisa_pkg ./lisa_pkg
COPY joao_prog/lisa_interfaces ./lisa_interfaces

WORKDIR /root/lisa_ws
# Build direto sem rosdep
RUN source /opt/ros/jazzy/setup.bash && colcon build --symlink-install

WORKDIR /root/assistente_voz
COPY fernando_prog/*.py ./
COPY fernando_prog/instalar.sh ./

RUN echo "source /opt/ros/jazzy/setup.bash" >> /root/.bashrc && \
    echo "source /root/lisa_ws/install/setup.bash" >> /root/.bashrc

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["bash"]
