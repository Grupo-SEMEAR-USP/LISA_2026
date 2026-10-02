#!/usr/bin/env python3

from .modo_base import ModoBaseNode

import rclpy
import time
import random

'''
Modo Lisa Ensina

Nesse modo, a lisa escolhe 1 gif aleatório entre 3 gifs educativos
Gif 1: respeitar diferenças
Gif 2: compartilhar
Gif 3: reciclar

'''

class ModoLisaEnsinaNode(ModoBaseNode):
    def __init__(self):
        super().__init__("modo_lisa_ensina")
        self.duracao_gifs = {
            "educativo1" : 28,
            "educativo2" : 31,
            "educativo3" : 31
        }


    def main_modo(self):
        # decide qual gif será tocado
        nro_gif = random.randint(1,3)
        nome_gif_educativo = "educativo" + str(nro_gif) # escolhe aleatoriamente 1 entre os 3 gifs educativos disponíveis
        tempo_gif = self.duracao_gifs[nome_gif_educativo]
        
        # Gif transição para o modo educativo
        self.send_tela_request("modoeducativo")
        time.sleep(3.1) #espera o fim do gif
        # Gif educativo
        self.send_tela_request(nome_gif_educativo)
        time.sleep(tempo_gif) #espera fim do gif educativo
        # volta para o menu
        self.desativar()
        self.send_controle_estados_request("MENU")


def main(args=None):
    rclpy.init(args=args)
    node = ModoLisaEnsinaNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__=='__main__':
    main()
