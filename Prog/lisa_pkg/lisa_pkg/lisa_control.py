#!/usr/bin/env python3

from example_interfaces.msg import String
from lisa_interfaces.srv import DisplayControl

import rclpy
from rclpy.node import Node

'''
Controlador principal da LISA

Recebe resultados dos nós de processamento e solicita ações e serviços com base nesses resultados.

    Tópico inscrito: /hand_gestures
        - Tipo da mensagem: example_interfaces/msg/String

    Cliente no serviço: /display_control
        - Tipo da mensagem: lisa_interfaces/srv/DisplayControl
            - request: string desired_gif 
            - response: bool success

'''

class LisaControlNode(Node):

    def __init__(self):
        super().__init__("lisa_control")
        self.subscriber_ = self.create_subscription(String, "hand_gestures", self.hand_gestures_subscription_callback, 10)
        self.display_client_ = self.create_client(DisplayControl, 'display_control')

        while not self.display_client_.wait_for_service(timeout_sec=1.0):
            self.get_logger().info(f'Esperando serviço display_control')
        self.display_request_ = DisplayControl.Request()

        # mapa (dicionário) que associa um gesto a um gif
        self.hand_gesture_request_map_ = {
            "Thumb_Up" : "love",
            "Thumb_Down" : "sad",
            "Victory" : "angry"
        }
        
        self.get_logger().info(f"Nó '{self.get_name()}' inicializado com sucesso.")


    def hand_gestures_subscription_callback(self, msg):
        hand_gesture = msg.data

        if hand_gesture in self.hand_gesture_request_map_.keys():
            desired_gif = self.hand_gesture_request_map_[hand_gesture]  # busca o gif associado ao gesto no mapa
            self.send_display_request(desired_gif)


    def send_display_request(self, desired_gif):
        self.get_logger().info(f"Enviando requisição '{desired_gif}' ao controle de tela.")
        self.display_request_.desired_gif = desired_gif
        return self.display_client_.call_async(self.display_request_)


def main(args=None):
    rclpy.init(args=args)
    node = LisaControlNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()

        if rclpy.ok():
            rclpy.shutdown()


if __name__=='__main__':
    main()
