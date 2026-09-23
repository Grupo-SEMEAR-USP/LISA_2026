#!/usr/bin/env python3

from example_interfaces.msg import String
from lisa_interfaces.srv import ControleEstados, ControleTela

import rclpy
from rclpy.node import Node
from ament_index_python.packages import get_package_share_directory

from unidecode import unidecode
from vosk import Model, KaldiRecognizer

import json
import os
import subprocess
import threading
import queue
import time


class DetectorComandosDeVoz(Node):

    def __init__(self):
        super().__init__("detector_comandos_de_voz")

        # ============================================================
        # CONFIGURAÇÕES
        # ============================================================

        self.timer_period = 0.03  # ~33 Hz

        self.sample_rate = 16000
        self.channels = 1
        self.bytes_per_sample = 2  # s16le = 16 bits = 2 bytes

        self.frames_per_buffer = 1024

        # ============================================================
        # CONTROLE DE ESTADO
        # ============================================================

        self.estado_atual_lisa = None

        self.acordado = False
        self.ativo = True

        # ============================================================
        # CONTROLE DO ÁUDIO
        # ============================================================

        self.parec_process_ = None

        self.audio_queue_ = queue.Queue(
            maxsize=50
        )

        self.audio_thread_ = None

        self.audio_thread_running_ = False

        self.audio_lock_ = threading.Lock()

        self.default_source_ = None

        self.last_source_check_time_ = 0.0

        # Verifica o microfone padrão periodicamente.
        # Não precisa consultar pactl a cada ciclo do ROS.
        self.source_check_interval = 2.0

        # Evento usado para parar a thread de áudio.
        self.stop_audio_event_ = threading.Event()

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

            self.model_ = Model(
                self.model_path_
            )

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

        grammar_list = commands_to_be_detected + [
            "[unk]"
        ]

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
        # MICROFONE PADRÃO DO SISTEMA
        # ============================================================

        self.get_logger().info(
            "Inicializando captura pelo microfone padrão "
            "do sistema..."
        )

        default_source = self.get_default_source()

        if default_source is None:

            self.get_logger().error(
                "Não foi possível identificar o microfone "
                "padrão do sistema."
            )

            return

        self.default_source_ = default_source

        self.get_logger().info(
            f"Microfone padrão detectado: "
            f"{self.default_source_}"
        )

        # ============================================================
        # THREAD DE ÁUDIO
        # ============================================================

        self.audio_thread_running_ = True

        self.audio_thread_ = threading.Thread(
            target=self.audio_capture_loop,
            daemon=True
        )

        self.audio_thread_.start()

        # ============================================================
        # TIMER DE PROCESSAMENTO
        # ============================================================

        self.timer_ = self.create_timer(
            self.timer_period,
            self.detect_voice_commands
        )

        self.get_logger().info(
            "Modelo carregado. Pronto para ouvir!"
        )

        self.get_logger().info(
            f"Nó '{self.get_name()}' "
            "inicializado com sucesso."
        )

    # ================================================================
    # MICROFONE PADRÃO
    # ================================================================

    def get_default_source(self):

        try:

            result = subprocess.run(
                [
                    "pactl",
                    "get-default-source"
                ],
                capture_output=True,
                text=True,
                timeout=2.0
            )

            if result.returncode != 0:

                self.get_logger().error(
                    "pactl não conseguiu obter "
                    "o microfone padrão."
                )

                return None

            source = result.stdout.strip()

            if not source:

                self.get_logger().error(
                    "pactl retornou um microfone padrão vazio."
                )

                return None

            return source

        except Exception as e:

            self.get_logger().error(
                f"Erro ao consultar microfone padrão: {e}"
            )

            return None

    # ================================================================
    # INICIA PAREC
    # ================================================================

    def start_parec(self):

        with self.audio_lock_:

            # --------------------------------------------------------
            # Se já existe um processo, encerra primeiro.
            # --------------------------------------------------------

            if self.parec_process_ is not None:

                self.stop_parec_locked()

            # --------------------------------------------------------
            # Descobre novamente o microfone padrão.
            # --------------------------------------------------------

            source = self.get_default_source()

            if source is None:

                self.get_logger().error(
                    "Não foi possível obter o "
                    "microfone padrão."
                )

                return False

            self.default_source_ = source

            self.get_logger().info(
                f"Iniciando captura do microfone padrão: "
                f"{source}"
            )

            # --------------------------------------------------------
            # Comando parec
            # --------------------------------------------------------

            command = [
                "parec",

                "--device",
                "@DEFAULT_SOURCE@",

                "--format",
                "s16le",

                "--rate",
                str(self.sample_rate),

                "--channels",
                str(self.channels),

                "--latency-msec",
                "30",
            ]

            try:

                self.parec_process_ = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    bufsize=0
                )

                self.get_logger().info(
                    "Captura de áudio iniciada."
                )

                return True

            except Exception as e:

                self.get_logger().error(
                    f"Falha ao iniciar parec: {e}"
                )

                self.parec_process_ = None

                return False

    # ================================================================
    # PARA PAREC
    # ================================================================

    def stop_parec_locked(self):

        if self.parec_process_ is None:
            return

        process = self.parec_process_

        self.parec_process_ = None

        try:

            if process.poll() is None:

                process.terminate()

                try:

                    process.wait(
                        timeout=1.0
                    )

                except subprocess.TimeoutExpired:

                    process.kill()
                    process.wait()

        except Exception as e:

            self.get_logger().debug(
                f"Erro ao encerrar parec: {e}"
            )

        finally:

            try:

                if process.stdout is not None:
                    process.stdout.close()

            except Exception:
                pass

            try:

                if process.stderr is not None:
                    process.stderr.close()

            except Exception:
                pass

    # ================================================================
    # LOOP DE CAPTURA DE ÁUDIO
    # ================================================================

    def audio_capture_loop(self):

        while self.audio_thread_running_:

            # --------------------------------------------------------
            # Garante que o parec esteja rodando.
            # --------------------------------------------------------

            if self.parec_process_ is None:

                if not self.start_parec():

                    time.sleep(1.0)

                    continue

            process = self.parec_process_

            if process is None:
                continue

            try:

                # ====================================================
                # TAMANHO DO BLOCO
                # ====================================================

                bytes_to_read = (
                    self.frames_per_buffer
                    * self.channels
                    * self.bytes_per_sample
                )

                data = process.stdout.read(
                    bytes_to_read
                )

                # ====================================================
                # PAREC ENCERRADO
                # ====================================================

                if not data:

                    if self.audio_thread_running_:

                        self.get_logger().warning(
                            "parec encerrou a captura. "
                            "Tentando reiniciar..."
                        )

                    with self.audio_lock_:
                        self.stop_parec_locked()

                    time.sleep(0.5)

                    continue

                # ====================================================
                # COLOCA O ÁUDIO NA FILA
                # ====================================================

                try:

                    self.audio_queue_.put_nowait(
                        data
                    )

                except queue.Full:

                    # Se o processamento ficar atrasado,
                    # descarta o bloco mais antigo para evitar
                    # acumular latência.
                    try:

                        self.audio_queue_.get_nowait()

                    except queue.Empty:
                        pass

                    try:

                        self.audio_queue_.put_nowait(
                            data
                        )

                    except queue.Full:
                        pass

            except Exception as e:

                if self.audio_thread_running_:

                    self.get_logger().error(
                        f"Erro na captura de áudio: {e}"
                    )

                with self.audio_lock_:
                    self.stop_parec_locked()

                time.sleep(0.5)

    # ================================================================
    # VERIFICA MUDANÇA DO MICROFONE PADRÃO
    # ================================================================

    def check_default_source(self):

        now = time.monotonic()

        if (
            now - self.last_source_check_time_
            < self.source_check_interval
        ):
            return

        self.last_source_check_time_ = now

        current_source = self.get_default_source()

        if current_source is None:
            return

        # ------------------------------------------------------------
        # Primeiro valor
        # ------------------------------------------------------------

        if self.default_source_ is None:

            self.default_source_ = current_source

            return

        # ------------------------------------------------------------
        # O microfone padrão mudou
        # ------------------------------------------------------------

        if current_source != self.default_source_:

            old_source = self.default_source_

            self.default_source_ = current_source

            self.get_logger().info(
                "Microfone padrão alterado:"
            )

            self.get_logger().info(
                f"  Anterior: {old_source}"
            )

            self.get_logger().info(
                f"  Atual:    {current_source}"
            )

            self.get_logger().info(
                "Reiniciando captura de áudio..."
            )

            with self.audio_lock_:

                self.stop_parec_locked()

            # Limpa áudio antigo da fila
            self.clear_audio_queue()

            # Reseta o reconhecimento
            if self.rec_ is not None:
                self.rec_.Reset()

    # ================================================================
    # LIMPA FILA DE ÁUDIO
    # ================================================================

    def clear_audio_queue(self):

        while True:

            try:

                self.audio_queue_.get_nowait()

            except queue.Empty:

                break

    # ================================================================
    # CALLBACK DO ESTADO ATUAL
    # ================================================================

    def estado_atual_sub_callback(self, msg):

        self.estado_atual_lisa = msg.data

        self.get_logger().debug(
            f"Estado atual da LISA: "
            f"{self.estado_atual_lisa}"
        )

        # ------------------------------------------------------------
        # Microfone ativo somente no MENU ou SONECA
        # ------------------------------------------------------------

        if self.estado_atual_lisa in [
            "MENU",
            "MODO_SONECA"
        ]:

            if not self.ativo:

                self.ativo = True

                self.clear_audio_queue()

                if self.rec_ is not None:
                    self.rec_.Reset()

                self.get_logger().info(
                    "Microfone ativado."
                )

        else:

            if self.ativo:

                self.ativo = False

                self.clear_audio_queue()

                if self.rec_ is not None:
                    self.rec_.Reset()

                self.get_logger().info(
                    "Microfone desativado."
                )

    # ================================================================
    # DETECÇÃO DE COMANDOS
    # ================================================================

    def detect_voice_commands(self):

        # ------------------------------------------------------------
        # Verifica se o microfone padrão mudou.
        # ------------------------------------------------------------

        self.check_default_source()

        # ------------------------------------------------------------
        # Se não estiver em estado que aceita comandos,
        # não processa áudio.
        # ------------------------------------------------------------

        if not self.ativo:
            return

        # ------------------------------------------------------------
        # Processa todos os blocos disponíveis.
        # ------------------------------------------------------------

        while True:

            try:

                data = self.audio_queue_.get_nowait()

            except queue.Empty:

                break

            try:

                # ====================================================
                # VOSK
                # ====================================================

                if not self.rec_.AcceptWaveform(data):

                    continue

                result = json.loads(
                    self.rec_.Result()
                )

                text = result.get(
                    "text",
                    ""
                ).strip()

                if not text:
                    continue

                processed_text = unidecode(
                    text.lower()
                )

                self.get_logger().info(
                    f"Texto reconhecido: "
                    f"'{processed_text}'"
                )

                # ====================================================
                # PROCURA PELO COMANDO
                # ====================================================

                for key, command in self.commands_map_.items():

                    key_normalized = unidecode(
                        key.lower()
                    )

                    if key_normalized not in processed_text:
                        continue

                    # ================================================
                    # PALAVRA DE ATIVAÇÃO
                    # ================================================

                    if command == "WAKE":

                        # --------------------------------------------
                        # Se estiver dormindo, acorda a LISA
                        # --------------------------------------------

                        if (
                            self.estado_atual_lisa
                            == "MODO_SONECA"
                        ):

                            self.get_logger().info(
                                "Comando de despertar recebido."
                            )

                            self.controle_estados_request_.estado_desejado = (
                                "MENU"
                            )

                            self.controle_estados_client_.call_async(
                                self.controle_estados_request_
                            )

                            self.acordado = False

                        # --------------------------------------------
                        # Se estiver no MENU, acorda para receber
                        # o próximo comando.
                        # --------------------------------------------

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

                    # ================================================
                    # COMANDO DE MODO
                    # ================================================

                    elif self.acordado:

                        self.get_logger().info(
                            f"Comando recebido: "
                            f"{command}!"
                        )

                        self.controle_estados_request_.estado_desejado = (
                            command
                        )

                        self.controle_estados_client_.call_async(
                            self.controle_estados_request_
                        )

                        # Volta a esperar pela palavra de ativação
                        self.acordado = False

                        break

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
            "ao controle de tela."
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

        # ------------------------------------------------------------
        # Para thread de áudio
        # ------------------------------------------------------------

        self.audio_thread_running_ = False

        self.stop_audio_event_.set()

        # ------------------------------------------------------------
        # Encerra parec
        # ------------------------------------------------------------

        with self.audio_lock_:

            self.stop_parec_locked()

        # ------------------------------------------------------------
        # Aguarda thread terminar
        # ------------------------------------------------------------

        if self.audio_thread_ is not None:

            try:

                self.audio_thread_.join(
                    timeout=2.0
                )

            except Exception as e:

                self.get_logger().debug(
                    f"Erro ao aguardar thread de áudio: {e}"
                )

        # ------------------------------------------------------------
        # Limpa fila
        # ------------------------------------------------------------

        self.clear_audio_queue()

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