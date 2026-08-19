#!/usr/bin/env python3

from example_interfaces.msg import String
from example_interfaces.srv import Trigger
from lisa_interfaces.srv import ControleEstados, ControleTela

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
    MODO_DESENHO = 4
    MODO_TROPELO = 5
    MODO_AURA = 6
    MODO_SONECA = 7


class ControleEstadosNode(Node):

    def __init__(self):
        super().__init__("controle_estados")

        self.dicionario_estados = {
            "MENU" : Estados.MENU,
            "MODO_GESTOS" : Estados.MODO_GESTOS,
            "MODO_MIMICA" : Estados.MODO_MIMICA,
            "MODO_CONVERSA" : Estados.MODO_CONVERSA,
            "MODO_DESENHO" : Estados.MODO_DESENHO,
            "MODO_TROPELO" : Estados.MODO_TROPELO,
            "MODO_AURA" : Estados.MODO_AURA,
            "MODO_SONECA" : Estados.MODO_SONECA
        }
    
        self.callback_group_ = ReentrantCallbackGroup()
        self.publisher_ =  self.create_publisher(String, "controle/estado_atual", 10, callback_group=self.callback_group_)
        # publica estado a cada 1 segundo
        self.pub_estados_timer_ = self.create_timer(1, self.publicar_estado) 
        # verifica mudança de estado a cada 1 segundo
        self.loop_principal_timer_ = self.create_timer(1, self.loop_principal) 
         # serviço para que outros nós possam solicitar mudança de estado
        self.mudar_estado_srv_ = self.create_service(ControleEstados, 'mudar_estado_service', self.mudar_estado_callback, callback_group=self.callback_group_)  

        # Cliente da tela
        self.tela_client_ = self.create_client(ControleTela, 'controle_tela_service')
        while not self.tela_client_.wait_for_service(timeout_sec=1.0):
            self.get_logger().info(f'Esperando serviço controle_tela_service')
        self.tela_request_ = ControleTela.Request()

        # Clientes dos modos
        self.trigger_request_ = Trigger.Request()

        self.modo_gestos_client_ = self.create_client(Trigger, "modo_gestos_service")
        while not self.modo_gestos_client_.wait_for_service(timeout_sec=1.0):
            self.get_logger().info(f'Esperando serviço modo_gestos_service')

        self.modo_desenho_client_ = self.create_client(Trigger, "modo_desenho_service")
        while not self.modo_desenho_client_.wait_for_service(timeout_sec=1.0):
            self.get_logger().info(f'Esperando serviço modo_desenho_service')
        
        self.estado_anterior = None
        self.estado_atual = Estados.MENU


    def publicar_estado(self):
        msg = String()
        msg.data = self.estado_atual.name
        self.publisher_.publish(msg)

    def mudar_estado_callback(self, request, response):
        estado_desejado = request.estado_desejado
        self.get_logger().info(f"Requisição recebida : {estado_desejado}")

        if estado_desejado not in self.dicionario_estados.keys():
            response.sucesso = False
            self.get_logger().info(f"Requisição negada: Estado inválido")
            return response

        elif self.estado_atual != Estados.MENU and self.dicionario_estados[estado_desejado] != Estados.MENU:
            response.sucesso = False
            self.get_logger().info(f"Requisição negada: Retorne para o modo MENU primeiro")
            return response

        self.get_logger().info(f"Ativando {estado_desejado}")
        self.estado_anterior = self.estado_atual
        self.estado_atual = self.dicionario_estados[estado_desejado]

        match self.estado_atual:
            case Estados.MENU:
                self.send_tela_request("blink")

            case Estados.MODO_GESTOS: 
                self.send_tela_request("gestos")
                self.modo_gestos_client_.call_async(self.trigger_request_)
                
            case Estados.MODO_MIMICA:
                pass

            case Estados.MODO_CONVERSA:
                pass

            case Estados.MODO_DESENHO:
                self.modo_desenho_client_.call_async(self.trigger_request_)

            case Estados.MODO_TROPELO:
                self.send_tela_request("tropelo")
                self.estado_atual = Estados.MENU

            case Estados.MODO_AURA:
                pass

            case Estados.MODO_SONECA:
                self.send_tela_request("SLEEP")


        response.sucesso = True 
        return response


    def loop_principal(self):
        return
        #if self.estado_atual == self.estado_anterior:
        #    return


    def send_tela_request(self, gif_desejado):
        self.get_logger().info(f"Enviando requisição '{gif_desejado}' ao controle de tela.")
        self.tela_request_.gif_desejado = gif_desejado
        return self.tela_client_.call_async(self.tela_request_)


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
