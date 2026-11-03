#!/usr/bin/env python3

from std_msgs.msg import String
from lisa_interfaces.srv import ControleAnimacao

import rclpy
from rclpy.node import Node
from rclpy.executors import MultiThreadedExecutor
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup

import threading

'''
Controle de animações da LISA

Recebe solicitações de animação através de um serviço ROS 2 e encaminha
as requisições para a ESP32 através de um tópico.

Aguarda a resposta da ESP32 para informar se a animação foi aceita
ou recusada. Também recebe e exibe os logs publicados pela ESP32.

    Servidor no serviço: /controle/controle_animacao_service
        - Tipo da mensagem: lisa_interfaces/srv/ControleAnimacao
            - request: string animacao_desejada
            - response: bool sucesso

    Tópico publicado: /esp32/solicitar_animacao
        - Tipo da mensagem: std_msgs/msg/String
        - Formato: identificador|nome_da_animacao

    Tópico inscrito: /esp32/resposta_animacao
        - Tipo da mensagem: std_msgs/msg/String
        - Formato: identificador|resultado (1 = aceita, 0 = recusada)

    Tópico inscrito: /esp32/log
        - Tipo da mensagem: std_msgs/msg/String

'''


class ControleAnimacaoNode(Node):

    def __init__(self):
        super().__init__("controle_animacao")

        # configurações
        self.service_name_ = "/controle/controle_animacao_service"
        self.animation_topic_ = "esp32/solicitar_animacao"
        self.response_topic_ = "esp32/resposta_animacao"
        self.log_topic_ = "esp32/log"

        self.response_timeout_ = 2.0

        # controle das requisições
        self.request_id_ = 0
        self.pending_request_id_ = None
        self.pending_success_ = False

        # evento utilizado para aguardar a resposta da ESP32
        self.response_event_ = threading.Event()

        # impede que duas requisições sejam processadas simultaneamente
        self.request_lock_ = threading.Lock()

        # grupos separados permitem processar a resposta da ESP32
        # enquanto o callback do serviço aguarda
        self.service_group_ = MutuallyExclusiveCallbackGroup()
        self.communication_group_ = MutuallyExclusiveCallbackGroup()

        # publisher para envio de animações à ESP32
        self.publisher_ = self.create_publisher(
            String,
            self.animation_topic_,
            10
        )

        # inscrição no tópico de respostas da ESP32
        self.response_subscription_ = self.create_subscription(
            String,
            self.response_topic_,
            self.response_callback,
            10,
            callback_group=self.communication_group_
        )

        # inscrição no tópico de logs da ESP32
        self.log_subscription_ = self.create_subscription(
            String,
            self.log_topic_,
            self.log_callback,
            10,
            callback_group=self.communication_group_
        )

        # serviço para solicitação de animações
        self.srv_ = self.create_service(
            ControleAnimacao,
            self.service_name_,
            self.animation_service_callback,
            callback_group=self.service_group_
        )

        # fim da inicialização
        self.get_logger().info(f"Nó '{self.get_name()}' inicializado com sucesso.")


    def animation_service_callback(self, request, response):
        ''' Recebe uma solicitação de animação e aguarda a resposta da ESP32. '''

        # serializa as solicitações de animação
        with self.request_lock_:

            # gera um identificador para a requisição
            self.request_id_ += 1
            request_id = self.request_id_

            self.pending_request_id_ = request_id
            self.pending_success_ = False

            self.response_event_.clear()

            # monta a mensagem no formato: identificador|nome_da_animacao
            msg = String()
            msg.data = f"{request_id}|{request.animacao_desejada}"

            self.get_logger().info(f"Solicitando animação: {request.animacao_desejada}")

            # encaminha a solicitação para a ESP32
            self.publisher_.publish(msg)

            # aguarda a resposta da ESP32 sem impedir o processamento
            # do subscriber de respostas
            received = self.response_event_.wait(
                timeout=self.response_timeout_
            )

            if received:

                response.sucesso = self.pending_success_

                if response.sucesso:
                    self.get_logger().info(
                        f"Animação '{request.animacao_desejada}' aceita pela ESP32."
                    )
                else:
                    self.get_logger().warning(
                        f"Animação '{request.animacao_desejada}' recusada pela ESP32."
                    )

            else:

                response.sucesso = False

                self.get_logger().error(
                    f"Tempo esgotado aguardando resposta da ESP32: "
                    f"{request.animacao_desejada}"
                )

            # finaliza a requisição atual
            self.pending_request_id_ = None

            return response


    def response_callback(self, msg):
        ''' Processa a resposta recebida da ESP32. '''

        try:
            request_id_str, result_str = msg.data.split("|", 1)

            request_id = int(request_id_str)
            result = int(result_str)

        except (ValueError, TypeError):
            self.get_logger().warning(
                f"Resposta inválida recebida da ESP32: {msg.data}"
            )
            return

        # ignora respostas que não pertencem à requisição atual
        if request_id != self.pending_request_id_:
            return

        if result not in (0, 1):
            self.get_logger().warning(
                f"Resultado inválido recebido da ESP32: {result}"
            )
            return

        self.pending_success_ = (result == 1)

        # libera o callback do serviço
        self.response_event_.set()


    def log_callback(self, msg):
        ''' Exibe os logs recebidos da ESP32. '''

        self.get_logger().info(f"[ESP32] {msg.data}")


def main(args=None):

    rclpy.init(args=args)

    node = ControleAnimacaoNode()

    # utiliza múltiplas threads para processar a resposta da ESP32
    # enquanto o callback do serviço aguarda
    executor = MultiThreadedExecutor(num_threads=2)
    executor.add_node(node)

    try:
        rclpy.spin(node, executor=executor)

    except KeyboardInterrupt:
        pass

    finally:
        executor.shutdown()
        node.destroy_node()

        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
