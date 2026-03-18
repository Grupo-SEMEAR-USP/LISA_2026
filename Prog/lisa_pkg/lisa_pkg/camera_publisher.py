#!/usr/bin/env python3

from sensor_msgs.msg import Image # interface para publicar o frame da camera (msg)
from cv_bridge import CvBridge # ponte para transformar a imagem do OpenCV na msg de imagem

import rclpy
from rclpy.node import Node

import cv2

'''
Camera Publisher

Publica a imagem da câmera.

    Parâmetros:
        - fps: frames publicados por segundo (padrão=10)
        - frame_w: largura do frame (padrão=320)
        - frame_h: altura do frame (padrão=240)
        - mostrar_camera: mostra imagem da câmera na tela (padrao=False)

    Tópico publicado: /frame
        - Tipo da mensagem: sensor_msgs/msg/Image 

'''

class CameraPublisherNode(Node):

    def __init__(self):
        super().__init__("camera_publisher")

        self.declare_parameter("fps", 10)
        self.declare_parameter("frame_w", 320)
        self.declare_parameter("frame_h", 240)
        self.declare_parameter("mostrar_camera", False)

        camera_index = self.find_camera_index() # procura índice da câmera
        
        if camera_index is None:
            self.get_logger().error("Câmera não encontrada.")
            return
        
        self.cap_ = cv2.VideoCapture(camera_index, cv2.CAP_V4L2)
        
        if not self.cap_.isOpened() or self.cap_ is None:
            self.get_logger().error("Erro ao iniciar captura de vídeo.")
            return

        self.fps_ = self.get_parameter("fps").value
        self.frame_width_ = self.get_parameter("frame_w").value
        self.frame_height_ = self.get_parameter("frame_h").value
        self.mostrar_camera_ = self.get_parameter("mostrar_camera").value
        
        self.cap_.set(cv2.CAP_PROP_FPS, self.fps_)
        self.bridge_ = CvBridge()

        self.publisher_ =  self.create_publisher(Image, "frame", 10)
        timer_period = 1/self.fps_
        self.timer_ = self.create_timer(timer_period, self.publish_frame)

        self.get_logger().info(f"Nó '{self.get_name()}' inicializado com sucesso.")
        self.get_logger().info(f"Parâmetros: (fps={self.fps_}, frame_w={self.frame_width_}, frame_h={self.frame_height_}, mostrar_camera={self.mostrar_camera_})")


    def find_camera_index(self, max_index=10):
        for index in range(max_index):
            cap = cv2.VideoCapture(index)
            if cap.isOpened():
                ret, _ = cap.read()
                cap.release()
                if ret:
                    return index
        return None


    def publish_frame(self):
        ret, frame = self.cap_.read()
        if not ret:
            self.get_logger().error("Erro ao ler captura.")
            return
        
        frame = cv2.resize(frame, (self.frame_width_, self.frame_height_))
        msg = self.bridge_.cv2_to_imgmsg(frame, encoding="bgr8")

        if self.mostrar_camera_:
            self.show_frame(frame)
        
        self.publisher_.publish(msg)


    def show_frame(self, frame):
        flipped_frame = cv2.flip(frame,1)
        cv2.imshow("frame", flipped_frame)
        cv2.waitKey(1)


def main(args=None):
    rclpy.init(args=args)
    node = CameraPublisherNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if hasattr(node, 'cap_'):
            node.cap_.release()
        
        cv2.destroyAllWindows()
        node.destroy_node()

        if rclpy.ok():
            rclpy.shutdown()


if __name__=='__main__':
    main()
