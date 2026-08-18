from sensor_msgs.msg import Image
from cv_bridge import CvBridge 
from example_interfaces.msg import String
from geometry_msgs.msg import Point32, Polygon

import rclpy
from rclpy.node import Node

import cv2

class DesenhoNaTelaNode(Node):

    def __init__(self):
        super().__init__("desenho_na_tela")
        self.frame_subscriber_ = self.create_subscription(Image, "visao/frame", self.frame_sub_cb, 10)
        self.gesture_subscriber_ =  self.create_subscription(String, "visao/gestos", self.gesture_sub_cb, 10)
        self.landmarks_subscriber_ =  self.create_subscription(Polygon, "visao/landmarks", self.landmarks_sub_cb, 10)
        self.bridge_ = CvBridge()

        self.frame_height_ = 0
        self.frame_width_ = 0

        self.tela_ativa = False
        self.ultimo_gesto = None
        # self.aplicar_fullscreen = False  <-- REMOVIDO: Não precisamos mais dessa flag

        self.current_frame = None
        self.current_gesture = None
        self.current_landmarks = None
        self.points_to_be_drawn = []

        timer_period = 1/10 # 10 Hz
        self.timer_ = self.create_timer(timer_period, self.desenhar_na_tela)

        self.get_logger().info(f"Nó '{self.get_name()}' inicializado com sucesso.")


    def desenhar_na_tela(self):
        if self.current_frame is None:
            return

        frame = self.current_frame
        gesture = self.current_gesture
        landmarks = self.current_landmarks
        
        self.frame_height_, self.frame_width_, _ = frame.shape

        if gesture == "zero" and self.ultimo_gesto != "zero":
            if self.tela_ativa:
                self.desativar_tela()
                self.points_to_be_drawn.clear()
            else:
                self.ativar_tela()

        self.ultimo_gesto = gesture
        
        if not self.tela_ativa:
            return  
        
        if gesture == "one" and landmarks is not None and len(landmarks) > 8:
            self.points_to_be_drawn.append(landmarks[8])

        elif gesture == "two":
            self.points_to_be_drawn.clear()

        for p in self.points_to_be_drawn:
            cv2.circle(frame, (int(p.x),int(p.y)), 5, (0,0,255), -1)

        frame = cv2.resize(frame, (1920, 1080))

        cv2.imshow("Desenho dedo", frame)
        
        # O waitKey precisa ser a última coisa relacionada à janela no loop
        if cv2.waitKey(1) == ord('q'):
            pass
            
        # <-- REMOVIDA A LÓGICA DO if self.aplicar_fullscreen DAQUI


    def frame_sub_cb(self, msg):
        try:
            self.current_frame = self.bridge_.imgmsg_to_cv2(msg, desired_encoding="bgr8")
        except Exception as e:
            self.get_logger().error(f"Erro durante o processamento do frame: {e}")


    def gesture_sub_cb(self, msg):
        self.current_gesture = msg.data


    def landmarks_sub_cb(self, msg):
        self.current_landmarks = msg.points


    def ativar_tela(self):
        # 1. Cria a janela com FREERATIO para o Linux não brigar com as bordas
        cv2.namedWindow("Desenho dedo", cv2.WINDOW_NORMAL | cv2.WINDOW_FREERATIO)
        
        # 2. Mostra o PRIMEIRO frame JÁ redimensionado para não assustar o sistema depois
        if self.current_frame is not None:
            frame_inicial_gigante = cv2.resize(self.current_frame, (1920, 1080))
            cv2.imshow("Desenho dedo", frame_inicial_gigante)
            
        # 3. Pausa para o sistema renderizar
        cv2.waitKey(1)
        
        # 4. Aplica o Fullscreen
        cv2.setWindowProperty("Desenho dedo", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
        
        self.tela_ativa = True

    def desativar_tela(self):
        try:
            # Destrói a janela para ela sumir da tela
            cv2.destroyWindow("Desenho dedo")
            # É necessário dar um waitKey rápido para o sistema operacional processar o fechamento da janela
            cv2.waitKey(1) 
        except Exception:
            pass
        self.tela_ativa = False


    def destroy_node(self):
        # Garante que a janela feche se o nó morrer
        cv2.destroyAllWindows()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = DesenhoNaTelaNode()
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