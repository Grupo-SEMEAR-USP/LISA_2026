#!/usr/bin/env python3

from .modo_base import ModoBaseNode

from example_interfaces.msg import String

import rclpy
from rclpy.qos import qos_profile_sensor_data
import time

'''
Modo Gestos

Recebe resultados dos nó de detecção de gestos e dispara requisições de gifs para o controle da tela, associando cada gesto a um gif.

    Tópico inscrito: /visao/gestos
        - Tipo da mensagem: example_interfaces/msg/String

'''

class ModoGestosNode(ModoBaseNode):

    def __init__(self):
        super().__init__("modo_gestos")
        self.subscriber_ = self.create_subscription(String, "visao/gestos", self.hand_gestures_subscription_callback, qos_profile_sensor_data)
        # mapa (dicionário) que associa um gesto a um gif
        self.hand_gesture_request_map_ = {
            "heart" : "love",
            "like" : "happy",
            "one" : "please",
            "two" : "dizzy",
            "dislike" : "sad",
            "ok" : "bombastic",
            "rock" : "star",
            "call" : "party",
            "middle_finger" : "angry"
        }


    def hand_gestures_subscription_callback(self, msg):
        if not self.ativo:
            return
        else:
            hand_gesture = msg.data
            if hand_gesture == "four":
                self.desativar()
                self.send_controle_estados_request("MENU")
                return
            elif hand_gesture in self.hand_gesture_request_map_.keys():
                gif_desejado = self.hand_gesture_request_map_[hand_gesture]  # busca o gif associado ao gesto no mapa
                self.send_tela_request(gif_desejado)


    def main_modo(self):
        self.send_tela_request("gestos")
        time.sleep(3) # espera fim do gif antes de iniciar modo   


def main(args=None):
    rclpy.init(args=args)
    node = ModoGestosNode()
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
