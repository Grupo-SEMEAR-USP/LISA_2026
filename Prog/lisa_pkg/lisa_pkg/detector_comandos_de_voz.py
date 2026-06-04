#!/usr/bin/env python3

from std_msgs.msg import String

import rclpy
from rclpy.node import Node
from ament_index_python.packages import get_package_share_directory
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup
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

        self.commands_map_ = {
            'ei lisa' : 'WAKE',
            'oi lisa' : 'WAKE',
            'e ai lisa' : 'WAKE',
            'hei lisa' : 'WAKE',
            'rei lisa' : 'WAKE',
            'ativar modo gestos' : 'MODO_GESTOS_CMD',
            'ativar modo copia' : 'MODO_MIMICA_CMD',
            'ativar modo conversa' : 'MODO_CONVERSA_CMD'
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

        self.callback_group_ = MutuallyExclusiveCallbackGroup()
        self.publisher_ =  self.create_publisher(String, "audio/comandos_de_voz", 10, callback_group=self.callback_group_)
        timer_period = 1/10 # 10 Hz
        self.timer_ = self.create_timer(timer_period, self.detect_voice_commands, callback_group=self.callback_group_)

        self.get_logger().info(f"Nó '{self.get_name()}' inicializado com sucesso.")


    def detect_voice_commands(self):
        try:
            while self.stream_.get_read_available() >= 1024:
                data = self.stream_.read(1024, exception_on_overflow=False)

                if self.rec_.AcceptWaveform(data):
                    result = json.loads(self.rec_.Result())
                    text = result.get("text", "")

                    if not text:
                        return
                    
                    processed_text = unidecode(text.lower())
                    self.get_logger().info(f"Texto reconhecido: '{processed_text}'")
                    
                    for key in self.commands_map_.keys():
                        if key in processed_text:
                            command = self.commands_map_[key]
                            msg = String()
                            msg.data = command
                            self.publisher_.publish(msg)
                            self.get_logger().info(f"Comando '{key}' detectada, publicando comando: {command}")
                            break    
        
        except IOError as e:
            self.get_logger().error(f"Erro de I/O no stream: {e}")

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