#!/usr/bin/env python3

from .modo_base import ModoBaseNode

import rclpy
import time

'''
Modo Tropelo da LISA

TOCA O GIF DO TROPELO!!!
Easter egg da lisa

'''

class ModoTropeloNode(ModoBaseNode):

    def __init__(self):
        super().__init__("modo_tropelo")

    def on_ativar(self):
        # Apenas executa o gif e já volta pro menu
        self.send_tela_request("tropelo")
        self.wait(2, self.return_to_menu)


def main(args=None):
    rclpy.init(args=args)
    node = ModoTropeloNode()
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
