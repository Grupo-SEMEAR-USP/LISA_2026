#!/usr/bin/env python3

from example_interfaces.msg import String
from lisa_interfaces.srv import ControleEstados, ControleTela

import rclpy
from rclpy.node import Node
from ament_index_python.packages import get_package_share_directory
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor

from unidecode import unidecode
from vosk import Model, KaldiRecognizer
import pyaudio
import json
import os

'''
Detector de comandos de voz com Vosk. Só detecta comandos específicos, porém é muito mais leve que o speech-to-text com whisper.

    Tópico publicado: /audio/comandos_de_voz
        - Tipo da mensagem: std_msgs/msg/String 

'''

class DetectorComandosDeVoz(Node):

    def __init__(self):
        super().__init__("detector_comandos_de_voz")

        self.callback_group_ = ReentrantCallbackGroup()
        timer_period = 1/10 # 10 Hz
        self.timer_ = self.create_timer(timer_period, self.detect_voice_commands, callback_group=self.callback_group_)

        self.controle_estados_client_ = self.create_client(ControleEstados, 'mudar_estado_service')
        while not self.controle_estados_client_.wait_for_service(timeout_sec=1.0):
            self.get_logger().info(f'Esperando serviço controle_estados_service')
        self.controle_estados_request_ = ControleEstados.Request()

        self.tela_client_ = self.create_client(ControleTela, 'controle_tela_service')
        while not self.tela_client_.wait_for_service(timeout_sec=1.0):
            self.get_logger().info(f'Esperando serviço controle_tela_service')
        self.tela_request_ = ControleTela.Request()

        self.estado_atual_subscription_ = self.create_subscription(String, "controle/estado_atual", self.estado_atual_sub_callback, 10, callback_group=self.callback_group_)
        self.estado_atual_lisa = None

        self.acordado = False
        self.ativo = False

        self.commands_map_ = {
            'ei lisa' : 'WAKE',
            'oi lisa' : 'WAKE',
            'e aí lisa' : 'WAKE',
            'rei lisa' : 'WAKE',
            'acorda lisa' : 'WAKE',
            'modo gestos' : 'MODO_GESTOS',
            'modo cópia' : 'MODO_MIMICA',
            'modo conversa' : 'MODO_CONVERSA',
            'modo desenho' : 'MODO_DESENHO',
            "modo tropelo" : "MODO_TROPELO",
            "modo soneca" : "MODO_SONECA"
        }
        self.model_path_ = os.path.join(get_package_share_directory("lisa_pkg"), 'models', 'vosk-model-small-pt-0.3')

        self.commmands_to_be_detected_ = list(self.commands_map_.keys())
        grammar_list = self.commmands_to_be_detected_ + ["[unk]"]   # adiciona tag "unk" para caso nenhuma das palavras seja detectada
        self.grammar_ = json.dumps(grammar_list)
        self.model_ = None
        self.audio_ = None
        self.stream_ = None

        try:
            self.model_ = Model(self.model_path_)
        except Exception as e:
            self.get_logger().error(f"Falha ao carregar modelo Vosk: {e}")
            return

        self.rec_ = KaldiRecognizer(self.model_, 16000, self.grammar_)

        try:
            self.audio_ = pyaudio.PyAudio()
            self.stream_ = self.audio_.open(format=pyaudio.paInt16,
                                          channels=1,
                                          rate=16000,
                                          input=True,
                                          frames_per_buffer=1024)
            self.stream_.start_stream()
        except Exception as e:
            self.get_logger().error(f"Falha ao abrir stream de áudio (PyAudio): {e}")
            return

        self.get_logger().info("Modelo carregado. Pronto para ouvir!")

        self.get_logger().info(f"Nó '{self.get_name()}' inicializado com sucesso.")


    def estado_atual_sub_callback(self, msg):
        self.estado_atual_lisa = msg.data
        if self.estado_atual_lisa == "MENU" and not self.ativo:
            self.ativo = True
            self.rec_.Reset()
        elif self.estado_atual_lisa != "MENU" and self.ativo:
            self.ativo = False


    def detect_voice_commands(self):        
        try:
            while self.stream_.get_read_available() >= 1024:
                data = self.stream_.read(1024, exception_on_overflow=False)

                if not self.ativo:
                    continue

                if self.rec_.AcceptWaveform(data):
                    result = json.loads(self.rec_.Result())
                    text = result.get("text", "")

                    if not text:
                        continue
                    
                    processed_text = unidecode(text.lower())
                    self.get_logger().info(f"Texto reconhecido: '{processed_text}'")
                    
                    for key in self.commands_map_.keys():
                        if unidecode(key) in processed_text:
                            command = self.commands_map_[key]

                            if command == "WAKE":
                                if not self.acordado:
                                    self.get_logger().info("Acordado, esperando comando.")
                                    self.acordado = True
                                if self.estado_atual_lisa == "MODO_SONECA":
                                    self.send_tela_request("WAKE")
                                    self.controle_estados_request_.estado_desejado = "MENU"
                                    self.controle_estados_client_.call_async(self.controle_estados_request_)
                                
                            if command != "WAKE" and self.acordado:
                                self.get_logger().info(f"Comando recebido: {command}!")
                                self.controle_estados_request_.estado_desejado = command
                                self.controle_estados_client_.call_async(self.controle_estados_request_)
                                self.acordado = False
                                break    
            
        except IOError as e:
            self.get_logger().error(f"Erro de I/O no stream: {e}")


    def send_tela_request(self, gif_desejado):
        self.get_logger().info(f"Enviando requisição '{gif_desejado}' ao controle de tela.")
        self.tela_request_.gif_desejado = gif_desejado
        return self.tela_client_.call_async(self.tela_request_)
    

def main(args=None):
    rclpy.init(args=args)
    node = DetectorComandosDeVoz()
    executor = MultiThreadedExecutor()
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        if hasattr(node, 'stream_'):
            if node.stream_:
                node.stream_.stop_stream()
                node.stream_.close()
        if hasattr(node, 'audio_'):  
            if node.audio_:
                node.audio_.terminate()

        node.destroy_node()

        if rclpy.ok():
            rclpy.shutdown()


if __name__=='__main__':
    main()