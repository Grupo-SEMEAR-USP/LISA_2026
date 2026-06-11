#!/usr/bin/env python3

from example_interfaces.msg import String
from example_interfaces.srv import Trigger
from lisa_interfaces.srv import ControleEstados

import rclpy
from rclpy.node import Node
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor

from enum import Enum

'''
Controle de Estados da Lisa


'''


class Estados(Enum):
    MENU = 0
    MODO_GESTOS = 1
    MODO_MIMICA = 2
    MODO_CONVERSA = 3


class ControleEstadosNode(Node):

    def __init__(self):
        super().__init__("controle_estados")

        self.dicionario_estados = {
            "MENU" : Estados.MENU,
            "MODO_GESTOS" : Estados.MODO_GESTOS,
            "MODO_MIMICA" : Estados.MODO_MIMICA,
            "MODO_CONVERSA" : Estados.MODO_CONVERSA
        }

        self.callback_group_ = ReentrantCallbackGroup()
        self.publisher_ =  self.create_publisher(String, "controle/estado_atual", 10, callback_group=self.callback_group_)
        # publica estado a cada 1 segundo
        self.pub_estados_timer_ = self.create_timer(1, self.publicar_estado) 
        # verifica mudança de estado a cada 1 segundo
        self.loop_principal_timer_ = self.create_timer(1, self.loop_principal) 
         # serviço para que outros nós possam solicitar mudança de estado
        self.mudar_estado_srv_ = self.create_service(ControleEstados, 'mudar_estado_service', self.mudar_estado_callback, callback_group=self.callback_group_)  
        # clientes dos modos
        self.trigger_request_ = Trigger.Request()
        self.modo_gestos_client_ = self.create_client(Trigger, "modo_gestos_service")

        self.estado_anterior = None
        self.estado_atual = Estados.MENU


    def publicar_estado(self):
        msg = String()
        msg.data = self.estado_atual.name
        self.publisher_.publish(msg)

    def mudar_estado_callback(self, request, response):
        estado_desejado = request.estado_desejado
        self.get_logger().info(f"Requisição recebida : {estado_desejado}")
        if estado_desejado in self.dicionario_estados.keys():
            self.estado_anterior = self.estado_atual
            self.estado_atual = self.dicionario_estados[estado_desejado]
            response.sucesso = True 
            self.get_logger().info(f"Estado alterado")
            return response
        else:
            response.sucesso = False
            self.get_logger().info(f"Estado inválido")
            return response


    def loop_principal(self):
        if self.estado_atual == self.estado_anterior:
            return
        
        match self.estado_atual:
            case Estados.MENU:
                self.get_logger().info("Executando modo menu...")
                return
            case Estados.MODO_GESTOS: 
                self.get_logger().info("Executando modo gestos...")
                self.modo_gestos_client_.call_async(self.trigger_request_)
                return
            case Estados.MODO_MIMICA:
                self.get_logger().info("Executando modo mímica...")
                return
            case Estados.MODO_CONVERSA:
                self.get_logger().info("Executando modo conversa...")
                return

    def destroy_node(self):
        super().destroy_node()


def main(args=None):
    rclpy.init()
    node = ControleEstadosNode()
    executor = MultiThreadedExecutor()
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:        
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()



if __name__=='__main__':
    main()
