#!/usr/bin/env python3

from lisa_pkg.modos.modo_base import ModoBaseNode

import rclpy

'''
Modo Aura

TOCA O GIF DO SIX SEVENNNNN 
TODO: Fará o six seven com os braços
Easter egg da lisa

'''

class ModoAuraNode(ModoBaseNode):

    def __init__(self):
        super().__init__("modo_aura", gif_inicializacao="67")


    def on_ativacao_concluida(self):
        # Espera o fim do GIF e volta ao menu.
        self.return_to_menu()


def main(args=None):
    rclpy.init(args=args)
    node = ModoAuraNode()
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
