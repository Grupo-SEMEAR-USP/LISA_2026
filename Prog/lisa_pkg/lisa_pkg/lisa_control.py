#!/usr/bin/env python3

from example_interfaces.msg import String
from lisa_interfaces.srv import DisplayControl

import rclpy
from rclpy.node import Node

import time

'''
Controlador principal da lisa

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

        self.hand_gestures_list_ = []
        self.min_gestures_confidence_ = 10  # precisa receber o gesto 10 vezes seguidas para fazer uma ação
        self.display_request_cooldown_ = 5   # só pode fazer um request para o display a cada 5 segundos
        self.last_display_request_ = self.display_request_cooldown_

        #self.hand_gesture_request_dictionary
        
        self.get_logger().info(f"Nó '{self.get_name()}' inicializado com sucesso.")


    def hand_gestures_subscription_callback(self, msg):
        hand_gesture = msg.data

        if not self.can_request():
            self.hand_gestures_list_.clear()
            return

        # Se o gesto recebido for diferente dos demais da lista, limpa a lista. Caso contrario, adiciona à lista.
        if self.hand_gestures_list_.count(hand_gesture) != len(self.hand_gestures_list_):
            self.hand_gestures_list_.clear()
            return

        self.hand_gestures_list_.append(hand_gesture)

        # Se o gesto for recebido 'min_gestures_confidence' vezes seguidas, a requisição será enviada
        if len(self.hand_gestures_list_) >= self.min_gestures_confidence_:
            
            if self.hand_gestures_list_[0] == 'Thumbs Up':
                self.send_display_request('love')
                self.hand_gestures_list_.clear()
            elif self.hand_gestures_list_[0] == 'Thumbs Down':
                self.send_display_request('sad')
                self.hand_gestures_list_.clear()

    def send_display_request(self, desired_gif):
        self.get_logger().info(f"Enviando requisição '{desired_gif}' ao controle de tela.")
        self.display_request_.desired_gif = desired_gif
        self.last_display_request_ = time.time()
        return self.display_client_.call_async(self.display_request_)
    
    def can_request(self):
        return (time.time() - self.last_display_request_) > self.display_request_cooldown_


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
