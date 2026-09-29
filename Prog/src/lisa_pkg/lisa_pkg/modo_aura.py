#!/usr/bin/env python3

from .modo_base import ModoBaseNode

import rclpy
import time

'''
Modo Aura

TOCA O GIF DO SIX SEVENNNNN 
TODO: Fará o six seven com os braços
Easter egg da lisa

'''

class ModoAuraNode(ModoBaseNode):

    def __init__(self):
        super().__init__("modo_aura")


    def main_modo(self):
        self.send_tela_request("67")
        time.sleep(6) # espera o fim do gif
        # APENAS EXECUTA O GIF E JÁ VOLTA PARA O MENU
        self.desativar()
        self.send_controle_estados_request("MENU")


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
