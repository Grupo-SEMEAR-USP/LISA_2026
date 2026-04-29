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
Detector de comandos de voz.

    Tópico publicado: /voice_command
        - Tipo da mensagem: std_msgs/msg/String 

'''

class VoiceCommandsDetectorNode(Node):

    def __init__(self):
        super().__init__("voice_commands_detector")

        self.commands_map_ = {
            'bom dia lisa' : 'bom_dia',
            'boa noite lisa' : 'boa_noite',
            'platelminto' : 'platelminto',
        }
        self.model_path_ = os.path.join(get_package_share_directory("lisa_pkg"), 'models', 'vosk-model-small-pt-0.3')

        self.commmands_to_be_detected_ = list(self.commands_map_.keys())
        self.grammar_ = json.dumps(self.commmands_to_be_detected_)
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
        self.publisher_ =  self.create_publisher(String, "voice_command", 10, callback_group=self.callback_group_)
        timer_period = 1/10 # 10 Hz
        self.timer_ = self.create_timer(timer_period, self.detect_voice_commands, callback_group=self.callback_group_)

        self.get_logger().info(f"Nó '{self.get_name()}' inicializado com sucesso.")


    def detect_voice_commands(self):
        try:
            data = self.stream_.read(1024, exception_on_overflow=False)

            if self.rec_.AcceptWaveform(data):
                result = json.loads(self.rec_.Result())
                text = result.get("text", "")

                if not text:
                    return
                
                processed_text = unidecode(text.lower())
                self.get_logger().info(f"Texto reconhecido: '{processed_text}'")
                
                for key in self.commands_map_:
                    if processed_text.__contains__(key):
                         command = self.commands_map_[key]
                         msg = String()
                         msg.data = command
                         self.publisher_.publish(msg)
                         self.get_logger().info(f"Palavra '{key}' detectada, publicando comando: {command}")
                         break    

                # for word in processed_text.split():
                #     if word in self.commands_map_:
                #         command = self.commands_map_[word]
                #         msg = String()
                #         msg.data = command
                #         self.publisher_.publish(msg)
                #         self.get_logger().info(f"Palavra '{word}' detectada, publicando comando: {command}")
                #         break
        
        except IOError as e:
            self.get_logger().error(f"Erro de I/O no stream: {e}")

def main(args=None):
    rclpy.init(args=args)
    node = VoiceCommandsDetectorNode()
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