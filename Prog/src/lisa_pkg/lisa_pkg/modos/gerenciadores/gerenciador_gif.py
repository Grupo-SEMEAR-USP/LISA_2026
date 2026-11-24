#!/usr/bin/env python3

from std_msgs.msg import String

from typing import Callable


class GerenciadorGif:

    def __init__(self, node, tela_client):
        self.node = node
        self.tela_client = tela_client

        # Inscrição no tópico de finalização de GIFs.
        self.gif_finalizado_subscription = self.node.create_subscription(
            String,
            "/controle/gif_finalizado",
            self.gif_finalizado_sub_callback,
            10
        )

        # Controle de solicitações de GIF.
        self.request_id = 0
        self.pending = None

        self.retry_timer = None
        self.timeout_timer = None


    def solicitar_gif(
        self,
        gif_desejado: str,
        callback: Callable[[], None] | None = None,
        intervalo: float = 0.5,
        timeout: float = 20.0
    ):
        """
        Solicita um GIF e aguarda sua finalização.

        Se o serviço retornar sucesso=False, tenta novamente
        após o intervalo definido.

        Quando o GIF terminar, executa o callback.

        Uma nova solicitação cancela a anterior.
        """

        gif_desejado = gif_desejado.removesuffix(".gif")

        if not gif_desejado:
            raise ValueError("O nome do GIF não pode ser vazio.")

        if intervalo <= 0 or timeout <= 0:
            raise ValueError("Intervalo e timeout devem ser positivos.")

        if callback is not None and not callable(callback):
            raise TypeError("callback deve ser uma função chamável.")

        # Cancela uma solicitação anterior, caso exista.
        self.cancelar()

        self.request_id += 1
        request_id = self.request_id

        self.pending = {
            "id": request_id,
            "gif": gif_desejado,
            "callback": callback,
            "intervalo": intervalo,
            "aguardando_finalizacao": False
        }

        self.node.get_logger().info(
            f"Solicitando GIF '{gif_desejado}'."
        )

        # Define um limite para não esperar indefinidamente.
        self.timeout_timer = self._criar_timer(
            timeout,
            lambda: self._timeout_callback(request_id)
        )

        # Primeira tentativa.
        self._tentar_solicitar_gif(request_id)


    def _criar_timer(self, segundos: float, callback):
        """Cria um timer de execução única."""

        timer_holder = {}

        def executar():
            timer = timer_holder["timer"]

            timer.cancel()
            self.node.destroy_timer(timer)

            if callback is not None:
                callback()

        timer = self.node.create_timer(
            float(segundos),
            executar
        )

        timer_holder["timer"] = timer

        return timer


    def _cancelar_timer(self, timer):
        """Cancela e destrói um timer, caso esteja ativo."""

        if timer is not None:
            timer.cancel()
            self.node.destroy_timer(timer)


    def _tentar_solicitar_gif(self, request_id: int):
        """Envia uma tentativa de solicitação ao serviço."""

        pending = self.pending

        if pending is None or pending["id"] != request_id:
            return

        self.retry_timer = None

        from lisa_interfaces.srv import ControleTela

        request = ControleTela.Request()
        request.gif_desejado = pending["gif"]

        self.node.get_logger().info(
            f"Enviando requisição '{pending['gif']}' ao controle de tela."
        )

        future = self.tela_client.call_async(request)

        future.add_done_callback(
            lambda future: self._gif_service_callback(future, request_id)
        )


    def _gif_service_callback(self, future, request_id: int):
        """Processa a resposta do serviço de controle de tela."""

        pending = self.pending

        if pending is None or pending["id"] != request_id:
            return

        try:
            response = future.result()

        except Exception as e:
            self.node.get_logger().error(
                f"Erro ao solicitar GIF '{pending['gif']}': {e}"
            )

            self._agendar_nova_tentativa(request_id)
            return

        if not response.sucesso:
            self.node.get_logger().info(
                f"GIF '{pending['gif']}' ainda não pode ser executado. "
                f"Nova tentativa em {pending['intervalo']}s."
            )

            self._agendar_nova_tentativa(request_id)
            return

        # O serviço aceitou a solicitação.
        # Agora aguardamos o tópico informar que o GIF terminou.
        pending["aguardando_finalizacao"] = True

        self.node.get_logger().info(
            f"GIF '{pending['gif']}' iniciado. "
            f"Aguardando finalização."
        )


    def _agendar_nova_tentativa(self, request_id: int):
        """Agenda outra tentativa sem bloquear o executor."""

        pending = self.pending

        if pending is None or pending["id"] != request_id:
            return

        self.retry_timer = self._criar_timer(
            pending["intervalo"],
            lambda: self._tentar_solicitar_gif(request_id)
        )


    def gif_finalizado_sub_callback(self, msg: String):
        """Recebe notificações de GIFs finalizados."""

        pending = self.pending

        if pending is None:
            return

        # Ignora notificações de outros GIFs.
        if not pending["aguardando_finalizacao"]:
            return

        if msg.data != pending["gif"]:
            return

        self.node.get_logger().info(
            f"GIF '{msg.data}' finalizado. "
            f"Continuando execução."
        )

        callback = pending["callback"]

        # Limpa a solicitação antes de executar o callback.
        self.cancelar()

        if callback is not None:
            callback()


    def _timeout_callback(self, request_id: int):
        """Encerra a solicitação caso o GIF demore demais."""

        pending = self.pending

        if pending is None or pending["id"] != request_id:
            return

        self.timeout_timer = None

        self.node.get_logger().error(
            f"Timeout aguardando o GIF '{pending['gif']}'. "
            f"Cancelando solicitação."
        )

        self.cancelar()


    def cancelar(self):
        """Cancela tentativas, timeout e espera de finalização."""

        self.request_id += 1
        self.pending = None

        self._cancelar_timer(self.retry_timer)
        self._cancelar_timer(self.timeout_timer)

        self.retry_timer = None
        self.timeout_timer = None


    def destroy(self):
        """Libera os recursos do gerenciador."""

        self.cancelar()

        self.node.destroy_subscription(
            self.gif_finalizado_subscription
        )