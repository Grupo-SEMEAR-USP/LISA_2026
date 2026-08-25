#!/usr/bin/env python3

from example_interfaces.msg import String
from lisa_interfaces.srv import ControleEstados
from lisa_interfaces.srv import ControleTela

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data

'''
Modo Gestos da LISA

Recebe resultados dos nó de detecção de gestos e dispara requisições de gifs para o controle da tela, associando cada gesto a um gif.

    Tópico inscrito: /visao/gestos
        - Tipo da mensagem: example_interfaces/msg/String

    Cliente no serviço: /controle_tela_service
        - Tipo da mensagem: lisa_interfaces/srv/ControleTela
            - request: string gif_desejado 
            - response: bool sucesso

    Tópico inscrito: /controle/estado_atual
        - Tipo da mensagem: example_interfaces/msg/String 
        
    Cliente no serviço: /controle/estado_atual
        - Tipo da mensagem: lisa_interfaces/srv/ControleEstados
            - request: string estado_desejado 
            - response: bool sucesso

'''

class ModoGestosNode(Node):

    def __init__(self):
        super().__init__("modo_gestos")
        self.subscriber_ = self.create_subscription(String, "visao/gestos", self.hand_gestures_subscription_callback, qos_profile_sensor_data)

        self.tela_client_ = self.create_client(ControleTela, 'controle_tela_service')
        while not self.tela_client_.wait_for_service(timeout_sec=1.0):
            self.get_logger().info(f'Esperando serviço controle_tela_service')
        self.tela_request_ = ControleTela.Request()

        self.controle_estados_client_ = self.create_client(ControleEstados, 'mudar_estado_service')
        while not self.controle_estados_client_.wait_for_service(timeout_sec=1.0):
            self.get_logger().info(f'Esperando serviço controle_estados_service')
        self.controle_estados_request_ = ControleEstados.Request()

        self.estado_atual_subscription_ = self.create_subscription(String, "controle/estado_atual", self.estado_atual_sub_callback, 10)
        self.ativo = False

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
        
        self.get_logger().info(f"Nó '{self.get_name()}' inicializado com sucesso.")


    def hand_gestures_subscription_callback(self, msg):
        if not self.ativo:
            return
        else:
            hand_gesture = msg.data
            if hand_gesture == "four":
                self.desativar()
                return
            elif hand_gesture in self.hand_gesture_request_map_.keys():
                gif_desejado = self.hand_gesture_request_map_[hand_gesture]  # busca o gif associado ao gesto no mapa
                self.num_atual_de_requisicoes += 1
                self.send_tela_request(gif_desejado)


    def send_tela_request(self, gif_desejado):
        self.get_logger().info(f"Enviando requisição '{gif_desejado}' ao controle de tela.")
        self.tela_request_.gif_desejado = gif_desejado
        return self.tela_client_.call_async(self.tela_request_)


    def estado_atual_sub_callback(self,msg):
        if msg.data == "MODO_GESTOS":
            if not self.ativo:
                self.ativar()
        else:
            if self.ativo:
                self.desativar()


    def desativar(self):
        self.ativo = False
        self.send_controle_estados_request("MENU")
        self.get_logger().info("## MODO GESTOS DESATIVADO ##")


    def ativar(self):
        self.ativo = True
        self.num_atual_de_requisicoes = 0
        self.get_logger().info("## MODO GESTOS ATIVADO ##")


    def send_controle_estados_request(self, estado_desejado):
        self.get_logger().info(f"Enviando requisição '{estado_desejado}' ao controle de estados.")
        self.controle_estados_request_.estado_desejado = estado_desejado
        return self.controle_estados_client_.call_async(self.controle_estados_request_)


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
