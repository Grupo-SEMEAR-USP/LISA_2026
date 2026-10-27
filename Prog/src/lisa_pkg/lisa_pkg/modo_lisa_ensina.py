#!/usr/bin/env python3

from .modo_base import ModoBaseNode

import rclpy
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
        self.nro_gif = 0
        self.nome_gif_educativo = ""
        self.tempo_gif = 0


    def on_ativar(self):
        # decide qual gif será tocado
        self.nro_gif = random.randint(1,3)
        self.nome_gif_educativo = "educativo" + str(self.nro_gif) # escolhe aleatoriamente 1 entre os 3 gifs educativos disponíveis
        self.tempo_gif = self.duracao_gifs[self.nome_gif_educativo]
        # Gif transição para o modo educativo
        self.send_tela_request("modoeducativo")
        self.wait(3.1, self.play_gif_educativo) #espera o fim do gif


    def play_gif_educativo(self):        
        # Gif educativo
        self.send_tela_request(self.nome_gif_educativo)
        self.wait(self.tempo_gif, self.return_to_menu) #espera fim do gif educativo e volta para o menu


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
