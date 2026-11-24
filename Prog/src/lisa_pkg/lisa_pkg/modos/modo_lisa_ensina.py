#!/usr/bin/env python3

from lisa_pkg.modos.modo_base import ModoBaseNode

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
        super().__init__("modo_lisa_ensina", gif_inicializacao="modoeducativo")
        self.gifs_educativos = ["educativo1", "educativo2", "educativo3"]
        self.nome_gif_educativo = ""


    def on_ativar(self):
        # decide qual gif será tocado
        # escolhe aleatoriamente 1 entre os 3 gifs educativos disponíveis
        self.nome_gif_educativo = random.choice(self.gifs_educativos)


    def on_ativacao_concluida(self):
        # Executa o GIF educativo e volta ao menu quando terminar.
        self.gerenciador_gif.solicitar_gif(self.nome_gif_educativo,self.return_to_menu)


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
