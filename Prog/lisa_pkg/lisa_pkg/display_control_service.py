#!/usr/bin/env python3

from lisa_interfaces.srv import DisplayControl

import rclpy
from rclpy.node import Node
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
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

    Servidor no serviço: /display_control
        - Tipo da mensagem: lisa_interfaces/srv/DisplayControl
            - request: string desired_gif 
            - response: bool success

'''

class DisplayControlService(Node):

    def __init__(self):
        super().__init__('display_control_service')

        self.base_path_ = os.path.join(get_package_share_directory("lisa_pkg"), 'telas')
        self.env_ = os.environ.copy()
        self.request_gif_process_ = None
        self.background_gif_process_ = None
        self.sleeping_gif_process_ = None

        self.request_cooldown_ = 5  # só pode atender a um novo request depois de 5 segundos após o último 
        self.lisa_sleep_timeout_ = 3 * 60   # após 3 minutos de inatividade, a LISA entrará no modo dormindo
        self.last_request_time_ = time.time()
        self.is_sleeping_ = False

        self.callback_group_ = ReentrantCallbackGroup() # grupo que permite rodar o timer e o serviço em paralelo
        self.srv_ = self.create_service(DisplayControl, 'display_control', self.display_control_callback, callback_group=self.callback_group_)        
        self.sleep_control_timer_ = self.create_timer(15, self.sleep_timer, callback_group=self.callback_group_)    # checa soneca a cada 15 segundos
        
        if not self.start_background_gif_loop():
            self.get_logger().error("Erro durante a inicialização do gif de fundo (background)")
            return

        self.get_logger().info(f"Nó '{self.get_name()}' inicializado com sucesso.")


    def display_control_callback(self, request, response):
        if not self.can_play_gif():
            self.get_logger().info(f"Requisição '{request.desired_gif}' negada (tela está em cooldown).")
            response.success = False
            return response

        self.last_request_time_ = time.time()
        if self.is_sleeping_:
            self.wake_up()

        response.success = self.play_gif_once(request.desired_gif, wait_gif=True)
        return response
    

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


    def play_gif_once(self, gif_name, wait_gif=True):
        if not '.gif' in gif_name:
            gif_name += '.gif'

        gif_path = os.path.join(self.base_path_,gif_name)

        if not os.path.exists(gif_path):
            self.get_logger().error(f"Gif {gif_name} não encontrado. Requisição negada.")
            return False

        command = ['mpv', '--fullscreen=yes', '--loop-file=no', '--correct-pts=no', '--ontop=yes', gif_path]
        self.request_gif_process_ = subprocess.Popen(command, env=self.env_, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.get_logger().info(f'Gif {gif_name} iniciado.')
        if wait_gif:
            self.request_gif_process_.wait()
        self.get_logger().info(f'Gif {gif_name} finalizado.')
        return True
    
    def play_gif_endless_loop(self, gif_name):
        if not '.gif' in gif_name:
            gif_name += '.gif'
        gif_path = os.path.join(self.base_path_,gif_name)

        if not os.path.exists(gif_path):
            self.get_logger().error(f"Gif {gif_path} não encontrado.")
            return

        command = ['mpv', '--fullscreen=yes', '--loop=inf', '--correct-pts=no', '--idle=yes', '--ontop=yes', gif_path]
        self.sleeping_gif_process_ = subprocess.Popen(command, env=self.env_, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.get_logger().info(f'Gif {gif_name} iniciado com sucesso.')


    def sleep_timer(self):
        if self.is_sleeping_:   # congela o contador se a LISA já esta dormindo
            return
        current_time = time.time()
        if current_time - self.last_request_time_ > self.lisa_sleep_timeout_:
            self.get_logger().info("Muito tempo sem receber requisições. Ativando modo soneca.")
            self.sleep()


    def sleep(self):
        self.is_sleeping_ = True
        self.play_gif_once("sleepy", wait_gif=False)
        time.sleep(8) # O gif "sleepy" tem 9s. Spawnamos o gif "sleeping" 1 segundo antes do "sleepy" terminar para evitar que a tela pisque
        self.play_gif_endless_loop("sleeping")


    def wake_up(self):
        self.is_sleeping_ = False
        if self.sleeping_gif_process_ is not None:
            self.sleeping_gif_process_.terminate()


    def can_play_gif(self):
        return (time.time() - self.last_request_time_) > self.request_cooldown_


def main():
    rclpy.init()
    node = DisplayControlService()
    executor = MultiThreadedExecutor()  # usa executor MultiThread para rodar o timer de soneca da lisa em paralelo ao nó
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        if node.request_gif_process_: 
            node.request_gif_process_.terminate()
        if node.background_gif_process_: 
            node.background_gif_process_.terminate()
        if node.sleeping_gif_process_: 
            node.sleeping_gif_process_.terminate()
        
        node.destroy_node()

        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()