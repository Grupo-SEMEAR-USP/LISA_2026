from sensor_msgs.msg import Image
from cv_bridge import CvBridge 
from example_interfaces.msg import String
from geometry_msgs.msg import Point32, Polygon
from lisa_interfaces.srv import ControleEstados

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data

import cv2

'''
Modo Desenho da LISA

Recebe frame da câmera e resultados dos nós de processamento de visão.
Junta as informações para permitir desenho na tela utilizando OpenCV.

    Tópico inscrito: /visao/frame
        - Tipo da mensagem: sensor_msgs/msg/Image

    Tópico inscrito: /visao/hand_landmaks
        - Tipo da mensagem: geometry_msgs/msg/Polygon

    Tópico inscrito: /visao/gestos
        - Tipo da mensagem: example_interfaces/msg/String

    Tópico inscrito: /controle/estado_atual
        - Tipo da mensagem: example_interfaces/msg/String 
        
    Cliente no serviço: /controle/estado_atual
        - Tipo da mensagem: lisa_interfaces/srv/ControleEstados
            - request: string estado_desejado 
            - response: bool sucesso

'''

class ModoDesenhoNode(Node):

    def __init__(self):
        super().__init__("modo_desenho")
        self.frame_subscriber_ = self.create_subscription(Image, "visao/frame", self.frame_sub_cb, qos_profile_sensor_data)
        self.gesture_subscriber_ =  self.create_subscription(String, "visao/gestos", self.gesture_sub_cb, qos_profile_sensor_data)
        self.landmarks_subscriber_ =  self.create_subscription(Polygon, "visao/hand_landmaks", self.landmarks_sub_cb, qos_profile_sensor_data)
        self.bridge_ = CvBridge()

        self.estado_atual_subscription_ = self.create_subscription(String, "controle/estado_atual", self.estado_atual_sub_callback, 10)
        self.ativo = False

        self.controle_estados_client_ = self.create_client(ControleEstados, 'mudar_estado_service')
        self.controle_estados_request_ = ControleEstados.Request()
        while not self.controle_estados_client_.wait_for_service(timeout_sec=1.0):
            self.get_logger().info(f'Esperando serviço controle_estados_service')

        self.frame_height_ = 0
        self.frame_width_ = 0

        self.current_frame = None
        self.current_gesture = None
        self.last_gesture = None
        self.current_landmarks = None
        self.points_to_be_drawn = []
        self.points_to_remove_on_release = 3
        self.current_color = 0
        self.color_list = [(0,0,255),(0,255,0),(255,0,0)]
        self.current_color = 0

        # Variáveis para forçar nomes únicos de janela
        self.window_counter = 0
        self.window_name = "Desenho"

        timer_period = 1/10 # 10 Hz
        self.timer_ = self.create_timer(timer_period, self.desenhar_na_tela)

        self.get_logger().info(f"Nó '{self.get_name()}' inicializado com sucesso.")


    def desenhar_na_tela(self):
        if self.current_frame is None or not self.ativo:
            return

        frame = self.current_frame
        gesture = self.current_gesture
        landmarks = self.current_landmarks
        
        self.frame_height_, self.frame_width_, _ = frame.shape

        # comandos do modo desenho
        if gesture == "four" and self.last_gesture != "four":
            self.desativar()
            return

        if gesture == "three" and self.last_gesture != "three":
            self.proxima_cor()

        elif gesture == "two" and self.last_gesture != "two":
            self.points_to_be_drawn.clear()

        elif gesture == "one" and landmarks is not None and len(landmarks) > 8:
            self.points_to_be_drawn.append(landmarks[8])

        # remove o utimo ponto quando troca de one para outro, para evitar pontos errados na transição dos estados
        if self.last_gesture == "one" and gesture != "one":
            points_to_remove = min(self.points_to_remove_on_release, len(self.points_to_be_drawn))
            if points_to_remove > 0:
                del self.points_to_be_drawn[-points_to_remove:]

        # atualiza ultimo gesto
        self.last_gesture = gesture

        # mostra o frame com o desenho
        for p in self.points_to_be_drawn:
            cv2.circle(frame, (int(p.x),int(p.y)), 3, self.color_list[self.current_color], -1)
        
        frame = cv2.resize(frame, (1920, 1080))

        cv2.imshow(self.window_name, frame)

        if cv2.waitKey(1) == ord('q'):
            pass


    def frame_sub_cb(self, msg):
        try:
            self.current_frame = self.bridge_.imgmsg_to_cv2(msg, desired_encoding="bgr8")
        except Exception as e:
            self.get_logger().error(f"Erro durante o processamento do frame: {e}")


    def gesture_sub_cb(self, msg):
        self.current_gesture = msg.data


    def landmarks_sub_cb(self, msg):
        self.current_landmarks = msg.points


    def estado_atual_sub_callback(self,msg):
        if msg.data == "MODO_DESENHO":
            if not self.ativo:
                self.ativar()
        else:
            if self.ativo:
                self.desativar()


    def proxima_cor(self):
        self.current_color += 1
        if self.current_color >= len(self.color_list):
            self.current_color = 0


    def ativar(self):
        self.current_gesture = None
        self.current_landmarks = None
        self.last_gesture = None
        self.current_color = 0
        
        cv2.destroyAllWindows()
        cv2.waitKey(50)
        
        # O TRUQUE: Mudar o nome da janela a cada ativação
        self.window_counter += 1
        self.window_name = f"Desenho_{self.window_counter}"
        
        # Cria a janela com o novo nome
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
        
        if self.current_frame is not None:
            frame_inicial = cv2.resize(self.current_frame, (1920, 1080))
            cv2.imshow(self.window_name, frame_inicial)
            
        cv2.waitKey(50)
        
        # Aplica o Fullscreen na janela recém-criada
        cv2.setWindowProperty(self.window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
        
        self.ativo = True
        self.get_logger().info(f"## MODO DESENHO ATIVADO ({self.window_name}) ##")


    def desativar(self):
        try:
            cv2.destroyWindow(self.window_name)
            
            # O seu pulo do gato continua aqui:
            for _ in range(5):
                cv2.waitKey(1) 
                
        except Exception as e:
            self.get_logger().error(f"Erro ao fechar janela: {e}")

        self.points_to_be_drawn.clear()
        self.last_gesture = None
        self.current_gesture = None
        self.current_landmarks = None
        self.current_color = 0
        self.ativo = False
        self.send_controle_estados_request("MENU")
        self.get_logger().info("## MODO DESENHO DESATIVADO ##")


    def send_controle_estados_request(self, estado_desejado):
        self.get_logger().info(f"Enviando requisição '{estado_desejado}' ao controle de estados.")
        self.controle_estados_request_.estado_desejado = estado_desejado
        return self.controle_estados_client_.call_async(self.controle_estados_request_)


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