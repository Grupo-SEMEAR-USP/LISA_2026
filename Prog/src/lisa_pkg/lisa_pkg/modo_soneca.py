#!/usr/bin/env python3

from .modo_base import ModoBaseNode

import rclpy

'''
Modo Soneca

A Lisa começa a dormir.
Para acordá-la basta dizer alguma das wake words (lógica implementa em detector_comandos_voz.py)
TODO: Abaixará o pescoço e os braços enquanto dorme

'''

class ModoSonecaNode(ModoBaseNode):

    def __init__(self):
        super().__init__("modo_soneca")

    def main_modo(self):
        # por enquanto, só manda a tela dormir e o detector de voz é responsável por acordá-la
        self.send_tela_request("sleep") 
        # futuramente aqui ele enviará uma requisição para executar animação de dormir com os motores


def main(args=None):
    rclpy.init(args=args)
    node = ModoSonecaNode()
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
