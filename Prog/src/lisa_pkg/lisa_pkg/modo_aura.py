#!/usr/bin/env python3

from .modo_base import ModoBaseNode

import rclpy

'''
Modo Aura

TOCA O GIF DO SIX SEVENNNNN 
TODO: Fará o six seven com os braços
Easter egg da lisa

'''

class ModoAuraNode(ModoBaseNode):

    def __init__(self):
        super().__init__("modo_aura")


    def on_ativar(self):
        self.send_tela_request("67")
        # espera o fim do gif e volta para o menu
        self.wait(6, self.return_to_menu) 


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
