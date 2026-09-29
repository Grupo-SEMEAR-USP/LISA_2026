#!/usr/bin/env python3

from example_interfaces.msg import String
from lisa_interfaces.srv import ControleEstados

import rclpy
from rclpy.node import Node

from enum import Enum

'''
Controle de Estados da LISA

Mantém e controla o estado da LISA. 
Processa mudanças de estado via requisição e publica o estado atual quando houver mudança de estado.

    Servidor no serviço: /controle/mudar_estado_service
        - Tipo da mensagem: lisa_interfaces/srv/ControleEstados
            - request: string estado_desejado 
            - response: bool sucesso

    Tópico publicado: /controle/estado_atual
        - Tipo da mensagem: example_interfaces/msg/String 


'''

#TODO: modo música, modo jogo da velha, jogo da forca, manual (aprender a usar a lisa)

class ControleEstadosNode(Node):

    def __init__(self):
        super().__init__("controle_estados")

        self.dicionario_estados = {
            "MENU" :                0,
            "MODO_GESTOS" :         1,
            "MODO_MIMICA" :         2,
            "MODO_CONVERSA" :       3,
            "MODO_DESENHO" :        4,
            "MODO_TROPELO" :        5,
            "MODO_AURA" :           6,
            "MODO_SONECA" :         7,
            "MODO_LISA_ENSINA" :    8
        }
        # publica estado quando houver mudança
        self.publisher_ =  self.create_publisher(String, "controle/estado_atual", 10)
        # serviço para que outros nós possam solicitar mudança de estado
        self.mudar_estado_srv_ = self.create_service(ControleEstados, 'mudar_estado_service', self.mudar_estado_callback)  
        # publica estado inicial (MENU)
        self.estado_atual = "MENU"
        self.publicar_estado() 


    def publicar_estado(self):
        msg = String()
        msg.data = self.estado_atual
        self.publisher_.publish(msg)


    def mudar_estado_callback(self, request, response):
        estado_desejado = request.estado_desejado
        self.get_logger().info(f"Requisição recebida : {estado_desejado}")

        if estado_desejado not in self.dicionario_estados.keys():
            response.sucesso = False
            self.get_logger().info(f"Requisição negada: Estado inválido")
            return response

        elif self.estado_atual != "MENU" and estado_desejado != "MENU":
            response.sucesso = False
            self.get_logger().info(f"Requisição negada: Retorne para o modo MENU primeiro")
            return response

        self.get_logger().info(f"Ativando {estado_desejado}")
        self.estado_atual = estado_desejado

        self.publicar_estado()

        response.sucesso = True 
        return response


def main(args=None):
    rclpy.init()
    node = ControleEstadosNode()
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
