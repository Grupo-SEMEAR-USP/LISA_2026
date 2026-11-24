#!/usr/bin/env python3

from lisa_pkg.modos.modo_base import ModoBaseNode
from lisa_pkg.visao.qos_camera import qos_camera

import rclpy
from sensor_msgs.msg import Image
from cv_bridge import CvBridge 
from std_msgs.msg import String
from geometry_msgs.msg import Point32, Polygon

import cv2
import numpy as np

'''
Modo Desenho

Recebe frame da câmera e resultados dos nós de processamento de visão.
Junta as informações para permitir desenho na tela utilizando OpenCV.

    Tópico inscrito: /visao/frame
        - Tipo da mensagem: sensor_msgs/msg/Image

    Tópico inscrito: /visao/hand_landmarks
        - Tipo da mensagem: geometry_msgs/msg/Polygon

    Tópico inscrito: /visao/gestos
        - Tipo da mensagem: std_msgs/msg/String

'''

class ModoDesenhoNode(ModoBaseNode):

    def __init__(self):
        super().__init__("modo_desenho", gif_inicializacao="desenho")

        self.declare_parameter("display_width", 800)
        self.declare_parameter("display_height", 480)

        self.display_width = self.get_parameter("display_width").value
        self.display_height = self.get_parameter("display_height").value

        self.frame_subscriber_ = self.create_subscription(Image, "visao/frame", self.frame_sub_cb, qos_camera)

        self.gesture_subscriber_ =  self.create_subscription(String, "visao/gestos", self.gesture_sub_cb, qos_camera)
        self.landmarks_subscriber_ =  self.create_subscription(Polygon, "visao/hand_landmarks", self.landmarks_sub_cb, qos_camera)
        self.bridge_ = CvBridge()

        self.current_frame = None
        self.current_gesture = None
        self.last_gesture = None

        self.drawing_canvas = None
        self.drawing_mask = None
        self.previous_point = None
        self.line_thickness = 3
        self.current_pointer = None
        self.pointer_radius = 4

        self.current_color = 0
        self.color_list = [(0,0,255),(0,255,0),(255,0,0)]

        self.pronto_para_desenhar = False
        self.janela_criada = False

        # Variáveis para forçar nomes únicos de janela
        self.window_counter = 0
        self.window_name = "Desenho"

        timer_period = 1/30 # 30 Hz
        self.timer_ = self.create_timer(timer_period, self.desenhar_na_tela)


    def desenhar_na_tela(self):
        if self.current_frame is None or not self.ativo or not self.pronto_para_desenhar:
            return

        frame = self.current_frame.copy()
        gesture = self.current_gesture

        # Comandos do modo desenho
        if gesture == "four" and self.last_gesture != "four":
            self.desativar()
            self.send_controle_estados_request("MENU")
            return

        if gesture == "three" and self.last_gesture != "three":
            self.limpar_desenho()

        elif gesture == "two" and self.last_gesture != "two":
            self.proxima_cor()

        # Atualiza último gesto
        self.last_gesture = gesture

        # Sobrepõe o desenho à imagem atual da câmera.
        if self.drawing_canvas is not None:
            mask = self.drawing_mask > 0
            frame[mask] = self.drawing_canvas[mask]

        # Desenha o marcador na ponta do indicador.
        if self.current_pointer is not None:
            cv2.circle(frame,self.current_pointer,self.pointer_radius,(0, 0, 0),-1,cv2.LINE_AA)
            cv2.circle(frame,self.current_pointer,self.pointer_radius - 2,(255, 255, 255),-1,cv2.LINE_AA)

        # Redimensiona e exibe a imagem
        frame = cv2.resize(frame, (self.display_width, self.display_height))

        cv2.imshow(self.window_name, frame)

        if cv2.waitKey(1) == ord('q'):
            pass


    def limpar_desenho(self):
        if self.drawing_canvas is not None:
            self.drawing_canvas[:] = 0

        if self.drawing_mask is not None:
            self.drawing_mask[:] = 0

        self.previous_point = None


    def frame_sub_cb(self, msg):
        try:
            self.current_frame = self.bridge_.imgmsg_to_cv2(msg, desired_encoding="bgr8")

            # Inicializa o canvas caso ainda não exista ou a resolução da câmera mude.
            if self.drawing_canvas is None or self.drawing_canvas.shape != self.current_frame.shape:
                self.drawing_canvas = np.zeros_like(self.current_frame)
                self.drawing_mask = np.zeros(self.current_frame.shape[:2], dtype=np.uint8)
                self.previous_point = None

        except Exception as e:
            self.get_logger().error(f"Erro durante o processamento do frame: {e}")


    def gesture_sub_cb(self, msg):
        self.current_gesture = msg.data

        if self.current_gesture != "one":
            self.previous_point = None


    def landmarks_sub_cb(self, msg):
        # Não atualiza o marcador durante a animação de entrada ou fora do modo.
        if not self.ativo or not self.pronto_para_desenhar:
            self.previous_point = None
            self.current_pointer = None
            return

        # Se não houver landmarks, interrompe o traço e remove o marcador.
        if len(msg.points) <= 8:
            self.previous_point = None
            self.current_pointer = None
            return

        if self.drawing_canvas is None:
            return

        # Utiliza o landmark 8 (ponta do dedo indicador).
        point = (int(msg.points[8].x), int(msg.points[8].y))

        # Atualiza a posição do marcador, independentemente do gesto.
        self.current_pointer = point

        # Só desenha enquanto o gesto "one" estiver ativo.
        if self.current_gesture != "one":
            self.previous_point = None
            return

        # Desenha uma linha entre a posição anterior e a atual.
        if self.previous_point is not None:
            cv2.line(
                self.drawing_canvas,
                self.previous_point,
                point,
                self.color_list[self.current_color],
                self.line_thickness,
                cv2.LINE_AA
            )

            cv2.line(
                self.drawing_mask,
                self.previous_point,
                point,
                255,
                self.line_thickness,
                cv2.LINE_AA
            )
        else:
            cv2.circle(
                self.drawing_canvas,
                point,
                2,
                self.color_list[self.current_color],
                -1,
                cv2.LINE_AA
            )

            cv2.circle(
                self.drawing_mask,
                point,
                2,
                255,
                -1,
                cv2.LINE_AA
            )

        self.previous_point = point


    def proxima_cor(self):
        self.current_color += 1
        if self.current_color >= len(self.color_list):
            self.current_color = 0


    def on_ativar(self):
        # Limpa possíveis dados recebidos antes da ativação.
        self.pronto_para_desenhar = False
        self.current_gesture = None
        self.last_gesture = None
        self.current_pointer = None
        self.limpar_desenho()


    def on_ativacao_concluida(self):
        self.current_gesture = None
        self.last_gesture = None
        self.limpar_desenho()
        self.current_color = 0
        self.current_pointer = None

        cv2.destroyAllWindows()
        cv2.waitKey(50)

        # Cria uma janela com nome único a cada ativação.
        self.window_counter += 1
        self.window_name = f"Desenho_{self.window_counter}"

        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
        self.janela_criada = True

        if self.current_frame is not None:
            frame_inicial = cv2.resize(
                self.current_frame,
                (1920, 1080)
            )
            cv2.imshow(self.window_name, frame_inicial)

        cv2.waitKey(50)

        cv2.setWindowProperty(
            self.window_name,
            cv2.WND_PROP_FULLSCREEN,
            cv2.WINDOW_FULLSCREEN
        )

        # Libera o processamento somente após preparar a janela.
        self.pronto_para_desenhar = True


    def desativar(self):
        self.pronto_para_desenhar = False

        if self.janela_criada:
            try:
                cv2.destroyWindow(self.window_name)
                cv2.waitKey(1)
            except Exception as e:
                self.get_logger().error(
                    f"Erro ao fechar janela: {e}"
                )
            finally:
                self.janela_criada = False

        self.limpar_desenho()
        self.last_gesture = None
        self.current_gesture = None
        self.current_color = 0
        self.current_pointer = None

        super().desativar()


    def destroy_node(self):
        # Garante que a janela feche se o nó morrer
        cv2.destroyAllWindows()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = ModoDesenhoNode()
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