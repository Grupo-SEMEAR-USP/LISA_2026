#!/usr/bin/env python3

from lisa_interfaces.srv import ScreenControl

import rclpy
from rclpy.node import Node
import os
import subprocess

'''
Serviço de controle de tela da LISA

Mantém a tela da LISA ligada rodando o gif standard.gif em loop.
Pode ser requisitado para rodar outro gif (uma vez por requisição).
TODO: Se nenhum gif for requisitado por 5 minutos, roda o gif sleeping em loop até outra requisição ser feita.

    Servidor no serviço: /screen_control
        - Tipo da mensagem: lisa_interfaces/srv/ScreenControl (request: string desired_gif | response: bool success)

'''

class ScreenControlService(Node):

    def __init__(self):
        super().__init__('screen_control_service')
        self.srv_ = self.create_service(ScreenControl, 'screen_control', self.screen_control_callback)
        
        self.base_path_ = '/home/jplop/Documents/lisa/telas'
        self.env_ = os.environ.copy()
        self.mpv_process_ = None
        self.background_process_ = None
        self.lisa_sleep_timeout_ = 5 * 60 # após 5 minutos de inatividade, a LISA entrará no modo dormindo
        
        self.start_background_gif_loop()
        self.get_logger().info(f"Nó '{self.get_name()}' inicializado com sucesso.")


    def screen_control_callback(self, request, response):
        if self.mpv_process_ is not None:
            self.get_logger().error("Um gif já esta sendo executado. Requisição negada.")
            response.sucess = False
        else:
            response.success = self.play_gif_once(request.desired_gif)
        
        return response
    

    def start_background_gif_loop(self):
        if self.background_process_ is not None:
            self.get_logger().warn("Gif de fundo já está ativo.")
            return
        
        background_gif_name = "standard.gif"
        background_gif_path = os.path.join(self.base_path_,background_gif_name)

        if not os.path.exists(background_gif_path):
            self.get_logger().error(f"Gif {background_gif_name} não encontrado.")
            return

        command = ['mpv', '--fullscreen=yes', '--loop=inf', '--correct-pts=no', '--idle=yes', background_gif_path]

        self.background_process_ = subprocess.Popen(command, env=self.env_, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.get_logger().info(f'Gif {background_gif_name} iniciado com sucesso.')


    def play_gif_once(self, gif_name):
        if not '.gif' in gif_name:
            gif_name += '.gif'

        gif_path = os.path.join(self.base_path_,gif_name)

        if not os.path.exists(gif_path):
            self.get_logger().error(f"Gif {gif_name} não encontrado. Requisição negada.")
            return False
        
        command = ['mpv', '--fullscreen=yes', '--loop-file=no', '--correct-pts=no', '--ontop=yes', gif_path]
        self.mpv_process_ = subprocess.Popen(command, env=self.env_, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.get_logger().info(f'Gif {gif_name} iniciado com sucesso.')

        self.mpv_process_.wait()
        self.mpv_process_ = None
        return True


def main():
    rclpy.init()
    node = ScreenControlService()
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