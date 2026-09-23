#!/usr/bin/env python3

from example_interfaces.msg import String
from lisa_interfaces.srv import ControleEstados, ControleTela

import rclpy
from rclpy.node import Node
from ament_index_python.packages import get_package_share_directory

from unidecode import unidecode
from vosk import Model, KaldiRecognizer

import pyaudio
import json
import os


class DetectorComandosDeVoz(Node):

    def __init__(self):
        super().__init__("detector_comandos_de_voz")

        # ============================================================
        # CONFIGURAÇÕES
        # ============================================================

        self.timer_period = 0.03  # ~33 Hz
        self.audio_device_index = 8
        self.sample_rate = 16000
        self.frames_per_buffer = 1024

        # ============================================================
        # CONTROLE DE ESTADO
        # ============================================================

        self.estado_atual_lisa = None

        self.acordado = False
        self.ativo = True

        # ============================================================
        # COMANDOS
        # ============================================================

        self.commands_map_ = {
            "ei lisa": "WAKE",
            "oi lisa": "WAKE",
            "e aí lisa": "WAKE",
            "rei lisa": "WAKE",
            "acorda lisa": "WAKE",

            "modo gestos": "MODO_GESTOS",
            "modo mímica": "MODO_MIMICA",
            "modo conversa": "MODO_CONVERSA",
            "modo desenho": "MODO_DESENHO",
            "modo atropelo": "MODO_TROPELO",
            "modo soneca": "MODO_SONECA",
        }

        # ============================================================
        # SERVIÇO DE CONTROLE DE ESTADOS
        # ============================================================

        self.controle_estados_client_ = self.create_client(
            ControleEstados,
            "mudar_estado_service"
        )

        while not self.controle_estados_client_.wait_for_service(
            timeout_sec=1.0
        ):
            self.get_logger().info(
                "Esperando serviço mudar_estado_service..."
            )

        self.controle_estados_request_ = ControleEstados.Request()

        # ============================================================
        # SERVIÇO DE CONTROLE DA TELA
        # ============================================================

        self.tela_client_ = self.create_client(
            ControleTela,
            "controle_tela_service"
        )

        while not self.tela_client_.wait_for_service(
            timeout_sec=1.0
        ):
            self.get_logger().info(
                "Esperando serviço controle_tela_service..."
            )

        self.tela_request_ = ControleTela.Request()

        # ============================================================
        # TÓPICO DO ESTADO ATUAL
        # ============================================================

        self.estado_atual_subscription_ = self.create_subscription(
            String,
            "controle/estado_atual",
            self.estado_atual_sub_callback,
            10
        )

        # ============================================================
        # MODELO VOSK
        # ============================================================

        self.model_path_ = os.path.join(
            get_package_share_directory("lisa_pkg"),
            "models",
            "vosk-model-small-pt-0.3"
        )

        self.model_ = None
        self.rec_ = None

        try:
            self.get_logger().info(
                "Carregando modelo Vosk..."
            )

            self.model_ = Model(self.model_path_)

        except Exception as e:
            self.get_logger().error(
                f"Falha ao carregar modelo Vosk: {e}"
            )
            return

        # ============================================================
        # GRAMÁTICA
        # ============================================================

        commands_to_be_detected = list(
            self.commands_map_.keys()
        )

        grammar_list = commands_to_be_detected + ["[unk]"]

        grammar = json.dumps(
            grammar_list,
            ensure_ascii=False
        )

        self.rec_ = KaldiRecognizer(
            self.model_,
            self.sample_rate,
            grammar
        )

        # ============================================================
        # PYAudio
        # ============================================================

        self.audio_ = None
        self.stream_ = None

        try:
            self.audio_ = pyaudio.PyAudio()

            info = self.audio_.get_device_info_by_index(
                self.audio_device_index
            )

            self.get_logger().info(
                f"Microfone selecionado: "
                f"[{self.audio_device_index}] {info['name']} | "
                f"canais: {info['maxInputChannels']} | "
                f"taxa: {info['defaultSampleRate']} Hz"
            )

            self.stream_ = self.audio_.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=self.sample_rate,
                input=True,
                input_device_index=self.audio_device_index,
                frames_per_buffer=self.frames_per_buffer
            )

            self.stream_.start_stream()

        except Exception as e:
            self.get_logger().error(
                f"Falha ao abrir stream de áudio: {e}"
            )
            return

        # ============================================================
        # TIMER DE CAPTURA
        # ============================================================

        self.timer_ = self.create_timer(
            self.timer_period,
            self.detect_voice_commands
        )

        self.get_logger().info(
            "Modelo carregado. Pronto para ouvir!"
        )

        self.get_logger().info(
            f"Nó '{self.get_name()}' inicializado com sucesso."
        )

    # ================================================================
    # CALLBACK DO ESTADO ATUAL
    # ================================================================

    def estado_atual_sub_callback(self, msg):

        self.estado_atual_lisa = msg.data

        self.get_logger().debug(
            f"Estado atual da LISA: {self.estado_atual_lisa}"
        )

        # Microfone só deve ficar ativo no MENU ou SONECA
        if self.estado_atual_lisa in ["MENU", "MODO_SONECA"]:

            if not self.ativo:
                self.ativo = True

                if self.rec_ is not None:
                    self.rec_.Reset()

                self.get_logger().info(
                    "Microfone ativado."
                )

        else:

            if self.ativo:
                self.ativo = False

                if self.rec_ is not None:
                    self.rec_.Reset()

                self.get_logger().info(
                    "Microfone desativado."
                )

    # ================================================================
    # DETECÇÃO DE COMANDOS
    # ================================================================

    def detect_voice_commands(self):

        # Se não estiver em um estado que aceita comandos,
        # não processa áudio.
        if not self.ativo:
            return

        # Verifica se o stream existe
        if self.stream_ is None:
            return

        try:

            # ========================================================
            # LEITURA DO MICROFONE
            # ========================================================

            data = self.stream_.read(
                self.frames_per_buffer,
                exception_on_overflow=False
            )

            # ========================================================
            # VOSK
            # ========================================================

            if not self.rec_.AcceptWaveform(data):
                return

            result = json.loads(
                self.rec_.Result()
            )

            text = result.get("text", "").strip()

            if not text:
                return

            processed_text = unidecode(
                text.lower()
            )

            self.get_logger().info(
                f"Texto reconhecido: '{processed_text}'"
            )

            # ========================================================
            # PROCURA PELO COMANDO
            # ========================================================

            for key, command in self.commands_map_.items():

                key_normalized = unidecode(
                    key.lower()
                )

                if key_normalized not in processed_text:
                    continue

                # ====================================================
                # PALAVRA DE ATIVAÇÃO
                # ====================================================

                if command == "WAKE":

                    # Se estiver dormindo, acorda a LISA
                    if self.estado_atual_lisa == "MODO_SONECA":

                        self.get_logger().info(
                            "Comando de despertar recebido."
                        )

                        self.controle_estados_request_.estado_desejado = "MENU"

                        self.controle_estados_client_.call_async(
                            self.controle_estados_request_
                        )

                        self.acordado = False

                    # Se estiver no MENU, acorda para receber comando
                    elif not self.acordado:

                        self.get_logger().info(
                            "LISA acordada. "
                            "Esperando comando."
                        )

                        self.send_tela_request(
                            "happy"
                        )

                        self.acordado = True

                    break

                # ====================================================
                # COMANDO DE MODO
                # ====================================================

                elif self.acordado:

                    self.get_logger().info(
                        f"Comando recebido: {command}!"
                    )

                    self.controle_estados_request_.estado_desejado = command

                    self.controle_estados_client_.call_async(
                        self.controle_estados_request_
                    )

                    # Volta a esperar pela palavra de ativação
                    self.acordado = False

                    break

        except IOError as e:

            self.get_logger().error(
                f"Erro de I/O no stream de áudio: {e}"
            )

        except Exception as e:

            self.get_logger().error(
                f"Erro durante reconhecimento de voz: {e}"
            )

    # ================================================================
    # CONTROLE DA TELA
    # ================================================================

    def send_tela_request(self, gif_desejado):

        self.get_logger().info(
            f"Enviando requisição '{gif_desejado}' "
            f"ao controle de tela."
        )

        self.tela_request_.gif_desejado = gif_desejado

        return self.tela_client_.call_async(
            self.tela_request_
        )

    # ================================================================
    # ENCERRAMENTO
    # ================================================================

    def destroy_node(self):

        self.get_logger().info(
            "Encerrando detector de comandos de voz..."
        )

        try:

            if self.stream_ is not None:

                if self.stream_.is_active():
                    self.stream_.stop_stream()

                self.stream_.close()

        except Exception as e:

            self.get_logger().error(
                f"Erro ao fechar stream de áudio: {e}"
            )

        try:

            if self.audio_ is not None:
                self.audio_.terminate()

        except Exception as e:

            self.get_logger().error(
                f"Erro ao finalizar PyAudio: {e}"
            )

        super().destroy_node()


# ====================================================================
# MAIN
# ====================================================================

def main(args=None):

    rclpy.init(args=args)

    node = DetectorComandosDeVoz()

    try:

        rclpy.spin(node)

    except KeyboardInterrupt:
        pass

    finally:

        if rclpy.ok():
            node.destroy_node()
            rclpy.shutdown()


if __name__ == "__main__":
    main()