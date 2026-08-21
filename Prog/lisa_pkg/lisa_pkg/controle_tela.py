#!/usr/bin/env python3

from example_interfaces.msg import String
from lisa_interfaces.srv import ControleTela

import rclpy
from rclpy.node import Node
from ament_index_python.packages import get_package_share_directory

import os
import subprocess
import time

'''
Serviço de controle de tela da LISA

Mantém a tela da LISA ligada rodando o gif standard.gif em loop.
Pode ser requisitado para rodar outro gif (uma vez por requisição).
Só pode atender uma requisição a cada 5 segundos, pois isso evita de tocar um gif enquanto outro já está sendo executado.
Se nenhum gif for requisitado por 3 minutos, roda o gif sleeping em loop até outra requisição ser feita (modo soneca).

    Servidor no serviço: /controle_tela_service
        - Tipo da mensagem: lisa_interfaces/srv/ControleTela
            - request: string gif_desejado 
            - response: bool sucesso

    Tópico inscrito: /controle/estado_atual
        - Tipo da mensagem: example_interfaces/msg/String

'''

class ControleTelaNode(Node):

    def __init__(self):
        super().__init__('controle_tela')

        self.base_path_ = os.path.join(get_package_share_directory("lisa_pkg"), 'telas')
        self.env_ = os.environ.copy()
        self.request_gif_process_ = None
        self.background_gif_process_ = None
        self.sleeping_gif_process_ = None
        self.is_sleeping_ = False
        self.last_request_time_ = time.time()
        self.request_cooldown_ = 3  # só pode atender a um novo request 3 segundos após o último 

        self.animation_check_timer_ = self.create_timer(0.1, self.check_animation) # checa constantemente se há uma animação sendo executada
        self.pending_state_ = None
        self.sleep_timer_ = None

        self.srv_ = self.create_service(ControleTela, 'controle_tela_service', self.controle_tela_callback)   
        self.estado_atual_subscription_ = self.create_subscription(String, "controle/estado_atual", self.estado_atual_sub_callback, 10)

        if not self.start_background_gif_loop():
            self.get_logger().error("Erro durante a inicialização do gif de fundo (background)")
            return

        self.get_logger().info(f"Nó '{self.get_name()}' inicializado com sucesso.")


    def controle_tela_callback(self, request, response):
        if not self.can_play_gif():
            self.get_logger().info(f"Requisição '{request.gif_desejado}' negada (tela está em cooldown).")
            response.sucesso = False
            return response

        self.last_request_time_ = time.time()

        if self.is_sleeping_:
            self.get_logger().info(f"Requisição '{request.gif_desejado}' negada (lisa está dormindo, acorde-a primeiro).")
            response.sucesso = False
            return response

        response.sucesso = self.play_gif_once(request.gif_desejado)
        return response


    def estado_atual_sub_callback(self,msg):
        estado = msg.data

        if self.is_sleeping_ and estado != "MENU":
            return

        if self.request_gif_process_ is not None:
            if self.request_gif_process_.poll() is None:
                self.get_logger().info("Animação em execução. Transição para o estado '{estado}' ficará pendente.")
                self.pending_state_ = estado
                return

        self.start_state_animation(estado)

    def start_background_gif_loop(self):
        if self.background_gif_process_ is not None:
            self.get_logger().warn("Gif de fundo já está ativo.")
            return True
        
        background_gif_name = "standard.gif"
        background_gif_path = os.path.join(self.base_path_,background_gif_name)

        if not os.path.exists(background_gif_path):
            self.get_logger().error(f"Gif {background_gif_name} não encontrado.")
            return False

        command = ['mpv', '--fullscreen=yes', '--loop=inf', '--correct-pts=no', '--idle=yes', background_gif_path]

        self.background_gif_process_ = subprocess.Popen(command, env=self.env_, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.get_logger().info(f'Gif background {background_gif_name} iniciado.')
        return True


    def play_gif_once(self, gif_name):
        if not '.gif' in gif_name:
            gif_name += '.gif'

        gif_path = os.path.join(self.base_path_,gif_name)

        if not os.path.exists(gif_path):
            self.get_logger().error(f"Gif {gif_name} não encontrado. Requisição negada.")
            return False

        if self.request_gif_process_ is not None:
            if self.request_gif_process_.poll() is None:
                self.get_logger().info(f"Requisição '{gif_name}' negada: um gif já está sendo executado.")
                return False

        command = ['mpv', '--fullscreen=yes', '--loop-file=no', '--correct-pts=no', '--ontop=yes', gif_path]
        self.request_gif_process_ = subprocess.Popen(command, env=self.env_, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.get_logger().info(f'Gif {gif_name} iniciado.')

        return True
    
    def play_gif_endless_loop(self, gif_name):

        if self.sleeping_gif_process_ is not None:
            if self.sleeping_gif_process_.poll() is None:
                return
            
        if not '.gif' in gif_name:
            gif_name += '.gif'
        gif_path = os.path.join(self.base_path_,gif_name)

        if not os.path.exists(gif_path):
            self.get_logger().error(f"Gif {gif_path} não encontrado.")
            return

        command = ['mpv', '--fullscreen=yes', '--loop=inf', '--correct-pts=no', '--idle=yes', '--ontop=yes', gif_path]
        self.sleeping_gif_process_ = subprocess.Popen(command, env=self.env_, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.get_logger().info(f'Gif {gif_name} iniciado com sucesso.')


    def start_state_animation(self, estado):
        match estado:
            case "MENU":
                if self.is_sleeping_:
                    self.wake_up()
                else:
                    self.play_gif_once("blink")
            case "MODO_GESTOS":
                self.play_gif_once("gestos")

            case "MODO_TROPELO":
                self.play_gif_once("tropelo")

            case "MODO_SONECA":
                self.sleep()

    def sleep(self):
        if self.is_sleeping_:
            return
        self.is_sleeping_ = True
        if self.play_gif_once("sleepy"):
            self.sleep_timer_ = self.create_timer(8.0, self.start_sleeping_loop) # O sleepy tem 9s, então spawnamos sleeping 1 segundo antes para evitar que a tela pisque

            
    def wake_up(self):
        if not self.is_sleeping_:
            return
        self.is_sleeping_ = False

        if self.sleep_timer_ is not None:
            self.sleep_timer_.cancel()
            self.sleep_timer_ = None

        if self.sleeping_gif_process_ is not None:
            if self.sleeping_gif_process_.poll() is None:
                self.sleeping_gif_process_.terminate()

            self.sleeping_gif_process_ = None


    def start_sleeping_loop(self):
        if self.sleep_timer_ is not None:
            self.sleep_timer_.cancel()
            self.sleep_timer_ = None

        if not self.is_sleeping_:
            return

        self.play_gif_endless_loop("sleeping")


    def can_play_gif(self):
        if self.request_gif_process_ is not None:
            if self.request_gif_process_.poll() is None:
                return False
            self.request_gif_process_ = None

        return (time.time() - self.last_request_time_) > self.request_cooldown_


    def check_animation(self):
        if self.request_gif_process_ is None:
            return

        if self.request_gif_process_.poll() is None:
            return

        self.get_logger().info("Gif finalizado.")

        self.request_gif_process_ = None

        if self.pending_state_ is not None:
            estado = self.pending_state_
            self.pending_state_ = None
            self.start_state_animation(estado)
    

    def destroy_node(self):
        if self.request_gif_process_: self.request_gif_process_.terminate()
        if self.background_gif_process_: self.background_gif_process_.terminate()
        if self.sleeping_gif_process_: self.sleeping_gif_process_.terminate()
        super().destroy_node()


def main():
    rclpy.init()
    node = ControleTelaNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:        
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()