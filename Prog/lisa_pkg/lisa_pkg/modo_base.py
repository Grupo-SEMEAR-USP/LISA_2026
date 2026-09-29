#!/usr/bin/env python3

from example_interfaces.msg import String
from lisa_interfaces.srv import ControleEstados
from lisa_interfaces.srv import ControleTela
from rclpy.node import Node

'''
MODO BASE, DO QUAL TODOS OS MODOS HERDAM FUNÇÕES BÁSICAS, CLIENTS DE TELA E ESTADO E SUBSCRIPTION DO ESTADO ATUAL

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

class ModoBaseNode(Node):

    def __init__(self, nome_modo : str):
        self.nome_modo = nome_modo

        super().__init__(self.nome_modo)

        # cliente no serviço da tela
        self.tela_client_ = self.create_client(ControleTela, 'controle_tela_service')
        while not self.tela_client_.wait_for_service(timeout_sec=1.0):
            self.get_logger().info(f'Esperando serviço controle_tela_service')
        self.tela_request_ = ControleTela.Request()

        # cliente no serviço de controle de estados
        self.controle_estados_client_ = self.create_client(ControleEstados, 'mudar_estado_service')
        while not self.controle_estados_client_.wait_for_service(timeout_sec=1.0):
            self.get_logger().info(f'Esperando serviço controle_estados_service')
        self.controle_estados_request_ = ControleEstados.Request()

        # inscrição no tópico do estado_atual
        self.estado_atual_subscription_ = self.create_subscription(String, "controle/estado_atual", self.estado_atual_sub_callback, 10)
        self.ativo = False

        self.get_logger().info(f"Nó '{self.get_name()}' inicializado com sucesso.")


    def main_modo(self):
        ''' O que o modo irá executar ao ser ativado. '''
        pass


    def estado_atual_sub_callback(self,msg):
        ''' Ativa o modo quando receber seu nome, e o desativa caso receba outro nome. '''
        if msg.data == self.nome_modo.upper():
            if not self.ativo:
                self.ativar()
        else:
            if self.ativo:
                self.desativar()


    def desativar(self):
        ''' Faz (self.ativo = false) e exibe mensagem de modo desativado. '''
        self.ativo = False
        self.get_logger().info(f"## {self.nome_modo.upper()} DESATIVADO ##")


    def ativar(self):
        ''' Faz (self.ativo = true), exibe mensagem de modo ativado e executa self.main_modo().'''
        self.ativo = True
        self.get_logger().info(f"## {self.nome_modo.upper()} ATIVADO ##")
        self.main_modo()


    def send_controle_estados_request(self, estado_desejado):
        ''' Envia requisição de alterar o estado atual da LISA para o serviço de controle de estados. '''
        self.get_logger().info(f"Enviando requisição '{estado_desejado}' ao controle de estados.")
        self.controle_estados_request_.estado_desejado = estado_desejado
        return self.controle_estados_client_.call_async(self.controle_estados_request_)


    def send_tela_request(self, gif_desejado):
        ''' Envia requisição de tocar um gif ou animação na tela da LISA para o serviço de controle de tela. '''
        self.get_logger().info(f"Enviando requisição '{gif_desejado}' ao controle de tela.")
        self.tela_request_.gif_desejado = gif_desejado
        return self.tela_client_.call_async(self.tela_request_)
