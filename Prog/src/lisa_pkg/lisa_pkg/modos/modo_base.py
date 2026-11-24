#!/usr/bin/env python3

from std_msgs.msg import String
from lisa_interfaces.srv import ControleEstados
from lisa_interfaces.srv import ControleTela
from lisa_pkg.controle.qos_estado_atual import qos_estado
from lisa_pkg.modos.gerenciadores.gerenciador_gif import GerenciadorGif

from rclpy.node import Node

from typing import Callable

'''
MODO BASE, DO QUAL TODOS OS MODOS HERDAM FUNÇÕES BÁSICAS, CLIENTS DE TELA E ESTADO E SUBSCRIPTION DO ESTADO ATUAL

    Cliente no serviço: /controle/controle_tela_service
        - Tipo da mensagem: lisa_interfaces/srv/ControleTela
            - request: string gif_desejado 
            - response: bool sucesso

    Cliente no serviço: /controle/mudar_estado_service
        - Tipo da mensagem: lisa_interfaces/srv/ControleEstados
            - request: string estado_desejado 
            - response: bool sucesso

    Tópico inscrito: /controle/estado_atual
        - Tipo da mensagem: std_msgs/msg/String  

'''

class ModoBaseNode(Node):

    def __init__(self, nome_modo : str, gif_inicializacao: str | None = None):
        self.nome_modo = nome_modo

        super().__init__(self.nome_modo)

        # cliente no serviço da tela
        self.tela_client_ = self.create_client(ControleTela, '/controle/controle_tela_service')
        while not self.tela_client_.wait_for_service(timeout_sec=1.0):
            self.get_logger().info(f'Esperando serviço /controle/controle_tela_service')

        # cliente no serviço de controle de estados
        self.controle_estados_client_ = self.create_client(ControleEstados, '/controle/mudar_estado_service')
        while not self.controle_estados_client_.wait_for_service(timeout_sec=1.0):
            self.get_logger().info(f'Esperando serviço controle_estados_service')

        # inscrição no tópico do estado_atual
        self.estado_atual_subscription_ = self.create_subscription(String, "/controle/estado_atual", self.estado_atual_sub_callback, qos_estado)

        # Controle de ativação do modo.
        self.ativo = False
        self.pronto_para_executar = False

        # GIF de inicialização.
        self.gif_inicializacao = gif_inicializacao

        # Gerenciador de GIFs.
        self.gerenciador_gif = GerenciadorGif(self,self.tela_client_)

        # controle de esperas (wait())
        self._wait_timers = set()

        # fim da inicialização
        self.get_logger().info(f"Nó '{self.get_name()}' inicializado com sucesso.")


    def on_ativar(self):
        """Comportamento executado ao ativar o modo."""
        pass

    def on_ativacao_concluida(self):
        """Comportamento executado após o GIF de inicialização terminar."""
        pass

    def on_desativar(self):
        """Limpeza e cancelamento de tarefas ao desativar o modo."""
        pass


    def estado_atual_sub_callback(self,msg):
        ''' Ativa o modo quando receber seu nome, e o desativa caso receba outro nome. '''
        if msg.data == self.nome_modo.upper():
            if not self.ativo:
                self.ativar()
        else:
            if self.ativo:
                self.desativar()


    def ativar(self):
        ''' 
            Faz (self.ativo = true), exibe mensagem de modo ativado e executa self.on_ativar().
            Também executa o gif_inicializacao, se houver, e por fim executa on_ativacao_concluida()
        '''
        if self.ativo:
            return
        
        self.ativo = True
        self.get_logger().info(f"## {self.nome_modo.upper()} ATIVADO ##")

        # Executa a preparação inicial do modo.
        self.on_ativar()

        # Se não houver GIF de inicialização, libera o modo imediatamente.
        if self.gif_inicializacao is None:
            self._liberar_modo()
        else:
            self.gerenciador_gif.solicitar_gif(self.gif_inicializacao,self._liberar_modo)


    def _liberar_modo(self):
        """Libera a execução do modo após a inicialização."""
        if not self.ativo:
            return
        self.pronto_para_executar = True
        self.on_ativacao_concluida()


    def desativar(self):
        ''' Faz (self.ativo = false), cancela esperas, exibe mensagem de modo desativado e executa self.on_desativar(). '''
        if not self.ativo:
            return

        self.ativo = False
        self.pronto_para_executar = False
        self.gerenciador_gif.cancelar()

        for timer in tuple(self._wait_timers):
            timer.cancel()
            self.destroy_timer(timer)

        self._wait_timers.clear()

        self.get_logger().info(f"## {self.nome_modo.upper()} DESATIVADO ##")

        self.on_desativar()


    def wait(self, seconds: float, callback: Callable[[], None] | None = None):
        """
        Agenda a execução de um callback após determinado intervalo,
        sem bloquear o executor do ROS 2.

        Se nenhum callback for fornecido, utiliza self.after_wait().

        A espera é cancelada automaticamente quando o modo é desativado.
        """

        if seconds < 0:
            raise ValueError("O tempo de espera não pode ser negativo.")

        if not self.ativo:
            return None

        # Utiliza after_wait como callback padrão.
        if callback is None:
            callback = self.after_wait

        if not callable(callback):
            raise TypeError("callback deve ser uma função chamável.")

        timer_holder = {}

        def finalizar_espera():
            timer = timer_holder["timer"]

            timer.cancel()
            self._wait_timers.discard(timer)
            self.destroy_timer(timer)

            # Só executa o callback se o modo continuar ativo.
            if self.ativo:
                callback()

        timer = self.create_timer(float(seconds), finalizar_espera)
        timer_holder["timer"] = timer

        self._wait_timers.add(timer)

        return timer


    def after_wait(self):
        ''' O que será executado após o wait'''
        pass


    def send_controle_estados_request(self, estado_desejado):
        """Solicita a alteração do estado atual da LISA."""
        self.get_logger().info(f"Enviando requisição '{estado_desejado}' ao controle de estados.")
    
        request = ControleEstados.Request()
        request.estado_desejado = estado_desejado
    
        return self.controle_estados_client_.call_async(request)


    def send_tela_request(self, gif_desejado):
        """Solicita a reprodução de um GIF ou animação."""
        self.get_logger().info(f"Enviando requisição '{gif_desejado}' ao controle de tela.")

        request = ControleTela.Request()
        request.gif_desejado = gif_desejado

        return self.tela_client_.call_async(request)


    def return_to_menu(self):
        self.send_controle_estados_request("MENU")


    def destroy_node(self):
        self.gerenciador_gif.destroy()
        super().destroy_node()