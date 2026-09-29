#!/usr/bin/env python3

from example_interfaces.msg import String
from lisa_interfaces.srv import ControleEstados
from lisa_interfaces.srv import ControleTela

import rclpy
from rclpy.node import Node
import time
import random

'''
Modo Lisa Ensina

Nesse modo, a lisa escolhe 1 gif aleatório entre 3 gifs educativos
Gif 1: respeitar diferenças
Gif 2: compartilhar
Gif 3: reciclar

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

class ModoLisaEnsinaNode(Node):

    def __init__(self):
        super().__init__("modo_lisa_ensina")

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
        n_gif = random.randint(1,3)
        duracao_gifs = {
            1 : 28,
            2 : 31,
            3 : 31
        }
        # Gif transição para o modo
        self.send_tela_request("modoeducativo")
        time.sleep(3.1) #espera o fim do gif
        # Gif educativo
        gif_educativo = "educativo" + str(n_gif) # escolhe aleatoriamente 1 entre os 3 gifs educativos disponíveis
        tempo_gif = duracao_gifs[n_gif]
        self.send_tela_request(gif_educativo)
        time.sleep(tempo_gif) #espera fim do gif educativo
        # volta para o menu
        self.send_controle_estados_request('MENU') # APENAS EXECUTA O GIF E JÁ VOLTA PARA O MENU

    def send_tela_request(self, gif_desejado):
        self.get_logger().info(f"Enviando requisição '{gif_desejado}' ao controle de tela.")
        self.tela_request_.gif_desejado = gif_desejado
        return self.tela_client_.call_async(self.tela_request_)


    def estado_atual_sub_callback(self,msg):
        if msg.data == "MODO_LISA_ENSINA":
            if not self.ativo:
                self.ativar()
        else:
            if self.ativo:
                self.desativar()


    def desativar(self):
        self.ativo = False
        self.send_controle_estados_request("MENU")
        self.get_logger().info("## MODO LISA-ENSINA DESATIVADO ##")


    def ativar(self):
        self.ativo = True
        self.num_atual_de_requisicoes = 0
        self.get_logger().info("## MODO LISA-ENSINA ATIVADO ##")
        self.main_modo()

    def send_controle_estados_request(self, estado_desejado):
        self.get_logger().info(f"Enviando requisição '{estado_desejado}' ao controle de estados.")
        self.controle_estados_request_.estado_desejado = estado_desejado
        return self.controle_estados_client_.call_async(self.controle_estados_request_)


def main(args=None):
    rclpy.init(args=args)
    node = ModoLisaEnsinaNode()
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
