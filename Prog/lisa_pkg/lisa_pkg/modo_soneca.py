#!/usr/bin/env python3

from example_interfaces.msg import String
from lisa_interfaces.srv import ControleEstados
from lisa_interfaces.srv import ControleTela

import rclpy
from rclpy.node import Node
import time

'''
Modo Soneca

A Lisa dorme
TODO: Abaixará o pescoço e os braços enquanto dorme

    Cliente no serviço: /controle_tela_service
        - Tipo da mensagem: lisa_interfaces/srv/ControleTela
            - request: string gif_desejado 
            - response: bool sucesso

    Tópico inscrito: /controle/estado_atual
        - Tipo da mensagem: example_interfaces/msg/String 
        
    Cliente no serviço: /controle/mudar_estado_service
        - Tipo da mensagem: lisa_interfaces/srv/ControleEstados
            - request: string estado_desejado 
            - response: bool sucesso
'''

class ModoSonecaNode(Node):

    def __init__(self):
        super().__init__("modo_soneca")

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

        self.get_logger().info(f"Nó '{self.get_name()}' inicializado com sucesso.")


    def main_modo(self):
        # por enquanto, só manda a tela dormir e o detector de voz é responsável por acordá-la
        self.send_tela_request("sleep") 
        # futuramente aqui ele enviará uma requisição para executar animação de dormir com os motores

    def send_tela_request(self, gif_desejado):
        self.get_logger().info(f"Enviando requisição '{gif_desejado}' ao controle de tela.")
        self.tela_request_.gif_desejado = gif_desejado
        return self.tela_client_.call_async(self.tela_request_)


    def estado_atual_sub_callback(self,msg):
        if msg.data == "MODO_SONECA":
            if not self.ativo:
                self.ativar()
        else:
            if self.ativo:
                self.desativar()


    def desativar(self):
        self.ativo = False
        #self.send_controle_estados_request("MENU") # Não pode voltar para o menu aqui, pois se isso ocorrer a lisa acorda
        self.get_logger().info("## MODO SONECA DESATIVADO ##")


    def ativar(self):
        self.ativo = True
        self.num_atual_de_requisicoes = 0
        self.get_logger().info("## MODO SONECA ATIVADO ##")
        self.main_modo()


    def send_controle_estados_request(self, estado_desejado):
        self.get_logger().info(f"Enviando requisição '{estado_desejado}' ao controle de estados.")
        self.controle_estados_request_.estado_desejado = estado_desejado
        return self.controle_estados_client_.call_async(self.controle_estados_request_)


def main(args=None):
    rclpy.init(args=args)
    node = ModoSonecaNode()
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
