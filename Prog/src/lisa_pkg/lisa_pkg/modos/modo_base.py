#!/usr/bin/env python3

from std_msgs.msg import String
from lisa_interfaces.srv import ControleEstados
from lisa_interfaces.srv import ControleTela
from lisa_pkg.controle.qos_estado_atual import qos_estado

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
        
    Tópico inscrito: /controle/gif_finalizado
        - Tipo da mensagem: std_msgs/msg/String 

'''

class ModoBaseNode(Node):

    def __init__(self, nome_modo : str):
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
        self.ativo = False

        # Inscrição no tópico de finalização de GIFs.
        self.gif_finalizado_subscription_ = self.create_subscription(String, "/controle/gif_finalizado", self.gif_finalizado_sub_callback, 10)

        # Controle de solicitações de GIF.
        self._gif_request_id = 0
        self._gif_pending = None
        self._gif_retry_timer = None
        self._gif_timeout_timer = None

        # controle de esperas (wait())
        self._wait_timers = set()

        # fim da inicialização
        self.get_logger().info(f"Nó '{self.get_name()}' inicializado com sucesso.")


    def on_ativar(self):
        """Comportamento executado ao ativar o modo."""
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


    def desativar(self):
        ''' Faz (self.ativo = false), cancela esperas, exibe mensagem de modo desativado e executa self.on_desativar(). '''
        if not self.ativo:
            return

        self.ativo = False
        self._cancelar_solicitacao_gif()

        for timer in tuple(self._wait_timers):
            timer.cancel()
            self.destroy_timer(timer)

        self._wait_timers.clear()

        self.get_logger().info(
            f"## {self.nome_modo.upper()} DESATIVADO ##"
        )

        self.on_desativar()


    def ativar(self):
        ''' Faz (self.ativo = true), exibe mensagem de modo ativado e executa self.on_ativar().'''
        if self.ativo:
            return
        
        self.ativo = True
        self.get_logger().info(f"## {self.nome_modo.upper()} ATIVADO ##")
        self.on_ativar()


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


    def solicitar_gif(self, gif_desejado: str, callback: Callable[[], None] | None = None, intervalo: float = 0.5, timeout: float = 20.0):
        """
        Solicita um GIF e aguarda sua finalização.

        Se o serviço retornar sucesso=False, tenta novamente
        após o intervalo definido.

        Quando o GIF terminar, executa o callback.

        A operação é cancelada automaticamente ao desativar o modo.
        """

        if not self.ativo:
            return

        gif_desejado = gif_desejado.removesuffix(".gif")

        if intervalo <= 0 or timeout <= 0:
            raise ValueError("Intervalo e timeout devem ser positivos.")

        if callback is not None and not callable(callback):
            raise TypeError("callback deve ser uma função chamável.")

        # Cancela uma solicitação anterior, caso exista.
        self._cancelar_solicitacao_gif()
        self._gif_request_id += 1
        request_id = self._gif_request_id

        self._gif_pending = {
            "id": request_id,
            "gif": gif_desejado,
            "callback": callback,
            "intervalo": intervalo,
            "aguardando_finalizacao": False
        }

        self.get_logger().info(f"Solicitando GIF '{gif_desejado}'.")
        # Define um limite para não esperar indefinidamente.
        self._gif_timeout_timer = self.wait(timeout,lambda: self._gif_timeout_callback(request_id))
        # Primeira tentativa.
        self._tentar_solicitar_gif(request_id)


    def _tentar_solicitar_gif(self, request_id: int):
        """Envia uma tentativa de solicitação ao serviço."""
        pending = self._gif_pending
        if not self.ativo or pending is None:
            return
        if pending["id"] != request_id:
            return

        self._gif_retry_timer = None
        future = self.send_tela_request(pending["gif"])
        future.add_done_callback(lambda future: self._gif_service_callback(future, request_id))


    def _gif_service_callback(self, future, request_id: int):
        """Processa a resposta do serviço de controle de tela."""
        pending = self._gif_pending
        if not self.ativo or pending is None:
            return
        if pending["id"] != request_id:
            return

        try:
            response = future.result()
        except Exception as e:
            self.get_logger().error(
                f"Erro ao solicitar GIF '{pending['gif']}': {e}"
            )
            self._agendar_nova_tentativa(request_id)
            return

        if not response.sucesso:
            self.get_logger().info(
                f"GIF '{pending['gif']}' ainda não pode ser executado. "
                f"Nova tentativa em {pending['intervalo']}s."
            )

            self._agendar_nova_tentativa(request_id)
            return

        # O serviço aceitou a solicitação.
        # Agora aguardamos o tópico informar que o GIF terminou.
        pending["aguardando_finalizacao"] = True

        self.get_logger().info(
            f"GIF '{pending['gif']}' iniciado. "
            f"Aguardando finalização."
        )


    def _agendar_nova_tentativa(self, request_id: int):
        """Agenda outra tentativa sem bloquear o executor."""
        pending = self._gif_pending
        if not self.ativo or pending is None:
            return
        if pending["id"] != request_id:
            return
        self._gif_retry_timer = self.wait(pending["intervalo"],lambda: self._tentar_solicitar_gif(request_id))


    def gif_finalizado_sub_callback(self, msg: String):
        """Recebe notificações de GIFs finalizados."""

        pending = self._gif_pending

        if not self.ativo or pending is None:
            return

        # Ignora notificações de outros GIFs.
        if not pending["aguardando_finalizacao"]:
            return

        if msg.data != pending["gif"]:
            return

        self.get_logger().info(
            f"GIF '{msg.data}' finalizado. "
            f"Continuando execução do modo."
        )

        callback = pending["callback"]

        # Limpa a solicitação antes de executar o callback.
        self._cancelar_solicitacao_gif()

        if self.ativo and callback is not None:
            callback()


    def _gif_timeout_callback(self, request_id: int):
        """Encerra a solicitação caso o GIF demore demais."""
        pending = self._gif_pending
        if pending is None or pending["id"] != request_id:
            return
        self._gif_timeout_timer = None
        self.get_logger().error(
            f"Timeout aguardando o GIF '{pending['gif']}'. "
            f"Cancelando solicitação."
        )
        self._cancelar_solicitacao_gif()


    def _cancelar_solicitacao_gif(self):
        """Cancela tentativas, timeout e espera de finalização."""
        self._gif_request_id += 1
        self._gif_pending = None

        for timer in (self._gif_retry_timer, self._gif_timeout_timer):
            if timer is not None and timer in self._wait_timers:
                timer.cancel()
                self._wait_timers.discard(timer)
                self.destroy_timer(timer)

        self._gif_retry_timer = None
        self._gif_timeout_timer = None


    def return_to_menu(self):
        self.send_controle_estados_request("MENU")