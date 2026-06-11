#!/usr/bin/env python3

from example_interfaces.msg import String
from example_interfaces.srv import Trigger
from lisa_interfaces.srv import ControleEstados
from lisa_interfaces.srv import ControleTela

import rclpy
from rclpy.node import Node
import time

'''
Modo gestos da LISA

Recebe resultados dos nós de processamento e solicita ações e serviços com base nesses resultados.

    Tópico inscrito: /visao/gestos
        - Tipo da mensagem: example_interfaces/msg/String

    Cliente no serviço: /controle_tela_service
        - Tipo da mensagem: lisa_interfaces/srv/ControleTela
            - request: string gif_desejado 
            - response: bool sucesso

'''

class ModoGestosNode(Node):

    def __init__(self):
        super().__init__("modo_gestos")
        self.subscriber_ = self.create_subscription(String, "visao/gestos", self.hand_gestures_subscription_callback, 10)
        self.tela_client_ = self.create_client(ControleTela, 'controle_tela_service')
        self.controle_estados_client_ = self.create_client(ControleEstados, 'mudar_estado_service')

        self.modo_gestos_srv_ = self.create_service(Trigger, 'modo_gestos_service', self.modo_gestos_srv_callback)

        while not self.tela_client_.wait_for_service(timeout_sec=1.0):
            self.get_logger().info(f'Esperando serviço controle_tela_service')
            
        self.tela_request_ = ControleTela.Request()
        self.controle_estados_request_ = ControleEstados.Request()

        # mapa (dicionário) que associa um gesto a um gif
        self.hand_gesture_request_map_ = {
            "heart" : "love",
            "dislike" : "sad",
            "one" : "angry",
            "like" : "happy",
            "zero" : "star",
            "two" : "party",
            "three" : "dizzy"
        }

        self.ativo = False
        self.num_atual_de_requisicoes = 0
        self.num_maximo_de_requisicoes = 50 # faz no maximo 50 requisições antes de desativar
        self.get_logger().info(f"Nó '{self.get_name()}' inicializado com sucesso.")


    def hand_gestures_subscription_callback(self, msg):
        if not self.ativo:
            return
        else:
            hand_gesture = msg.data
            if hand_gesture in self.hand_gesture_request_map_.keys():
                if self.num_atual_de_requisicoes >= self.num_maximo_de_requisicoes or hand_gesture == "dislike":
                    self.desativar()
                    return
                gif_desejado = self.hand_gesture_request_map_[hand_gesture]  # busca o gif associado ao gesto no mapa
                self.num_atual_de_requisicoes += 1
                self.send_tela_request(gif_desejado)


    def send_tela_request(self, gif_desejado):
        self.get_logger().info(f"Enviando requisição '{gif_desejado}' ao controle de tela.")
        self.tela_request_.gif_desejado = gif_desejado
        return self.tela_client_.call_async(self.tela_request_)

    def send_controle_estados_request(self, estado_desejado):
        self.get_logger().info(f"Enviando requisição '{estado_desejado}' ao controle de estados.")
        self.controle_estados_request_.estado_desejado = estado_desejado
        return self.controle_estados_client_.call_async(self.controle_estados_request_)

    def modo_gestos_srv_callback(self, request, response):
        if not self.ativo:
            response.success = True
            response.message = "Modo Gestos Ativado"
            self.ativar()
        else:
            response.success = False
            response.message = "Modo Gestos já estava ativado"

        return response
        
    def desativar(self):
        self.get_logger().info("## MODO GESTOS DESATIVADO ##")
        self.ativo = False
        self.send_controle_estados_request("MENU")

    def ativar(self):
        self.get_logger().info("## MODO GESTOS ATIVADO ##")
        self.ativo = True
        self.num_atual_de_requisicoes = 0

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
