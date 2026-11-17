#!/usr/bin/env python3

from sensor_msgs.msg import Image
from cv_bridge import CvBridge 
from std_msgs.msg import String
from geometry_msgs.msg import Point32, Polygon
from lisa_pkg.controle.qos_estado_atual import qos_estado
from lisa_pkg.visao.qos_camera import qos_camera

import rclpy
from rclpy.node import Node
from ament_index_python.packages import get_package_share_directory

import cv2
import mediapipe as mp
from mediapipe.tasks.python import vision
import time
import os

'''
Detector de Gestos de Mão

Processa o frame da câmera com mediapipe e publica os gestos de mão que forem detectados.
No MODO_GESTOS, exige a detecção do mesmo gesto em 5 frames consecutivos.
No MODO_DESENHO, publica o resultado imediatamente para reduzir a latência.
Também publica continuamente os landmarks da mão selecionada.

    Parâmetros:
        - mostrar_landmarks: mostra frame com landmarks detectados na tela (padrão=False)

    Tópico inscrito: /controle/estado_atual
        - Tipo da mensagem: std_msgs/msg/String 

    Tópico inscrito: /visao/frame
        - Tipo da mensagem: sensor_msgs/msg/Image 

    Tópico publicado: /visao/gestos
        - Tipo da mensagem: std_msgs/msg/String

    Tópico publicado: /visao/hand_landmarks
        - Tipo da mensagem: geometry_msgs/msg/Polygon

'''

# CLASSES AUXILIARES
class Box():
    def __init__(self, x_min, x_max, y_min, y_max):
        self.x_min_ = x_min
        self.x_max_ = x_max
        self.y_min_ = y_min
        self.y_max_ = y_max
        self.width_ = self.x_max_ - self.x_min_ 
        self.height_ = self.y_max_ - self.y_min_
        self.area_ = self.width_ * self.height_
    
    def intersects(self, another_box, margin=0.05):
        """
        Verifica se este retângulo intersecta outro retângulo.
        O parâmetro 'margin' (0.0 a 1.0) permite que as caixas se detectem 
        mesmo se houver um pequeno espaço entre elas.
        """
        # Verifica sobreposição no eixo X
        overlap_x = (self.x_min_ - margin) <= another_box.x_max_ and \
                    (another_box.x_min_ - margin) <= self.x_max_
        
        # Verifica sobreposição no eixo Y
        overlap_y = (self.y_min_ - margin) <= another_box.y_max_ and \
                    (another_box.y_min_ - margin) <= self.y_max_
        
        return overlap_x and overlap_y
        # by gemini


class Hand():
    def __init__(self, gesture, landmarks):
        self.gesture_ = "none"
        self.score_ = 0
        self.landmarks = None
        self.x_coords_, self.y_coords_ = [0.0], [0.0]

        if gesture.category_name:
            self.gesture_ = gesture.category_name.lower()
            self.score_ = gesture.score
        if landmarks: 
            self.landmarks = landmarks
            self.x_coords_ = [lm.x for lm in landmarks]
            self.y_coords_ = [lm.y for lm in landmarks]
        
        self.box_ = Box(min(self.x_coords_), max(self.x_coords_), min(self.y_coords_), max(self.y_coords_))
        self.center_ = (
            (self.box_.x_min_ + self.box_.x_max_) / 2,
            (self.box_.y_min_ + self.box_.y_max_) / 2
        )


# CLASSE PRINCIPAL
class DetectorGestosNode(Node):

    def __init__(self):
        super().__init__("detector_gestos")

        self.declare_parameter("mostrar_landmarks", False)

        self.subscriber_ = self.create_subscription(Image, "visao/frame", self.detect_gesture, qos_camera)

        self.gesture_publisher_ =  self.create_publisher(String, "visao/gestos", qos_camera)
        self.landmarks_publisher_ =  self.create_publisher(Polygon, "visao/hand_landmarks", qos_camera)
        
        self.estado_atual_subscription_ = self.create_subscription(String, "/controle/estado_atual", self.estado_atual_sub_callback, qos_estado)

        self.bridge_ = CvBridge()
        self.model_path_ = os.path.join(get_package_share_directory("lisa_pkg"), 'models', 'gesture_recognizer.task')
        
        options = vision.GestureRecognizerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=self.model_path_),
            running_mode=vision.RunningMode.VIDEO,
            num_hands = 4,
            min_hand_detection_confidence=0.7,
            min_hand_presence_confidence=0.5,
            min_tracking_confidence=0.5
        )
        self.detector_ = vision.GestureRecognizer.create_from_options(options)

        self.frame_height_ = 0
        self.frame_width_ = 0
        self.str_msg_ = String()
        self.processing_ = False # variável para travar o recebimento de frames, caso o nó ainda esteja processando o frame anterior
        self.min_gesture_score_ = 0.75 # só publica se o score for de 75% ou mais 
        self.gesture_counter_ = 1 # contador para verificar quantas vezes seguidas o gesto foi detectado
        self.num_gesture_frames_ = 5 # é necessário encontrar o mesmo gesto em 5 frames seguidos para publicá-lo
        self.current_gesture_ = "none"
        self.last_gesture_ = "none"
        self.two_handed_gestures_ = ["heart"]   # gestos que precisam ser detectados em duas mãos ao mesmo tempo (precisam ser simétricos)
        self.ativo = False

        # TRACKING DA MÃO
        self.selected_hand_center_ = None
        self.hand_lost_frames_ = 0

        self.max_hand_lost_frames_ = 10
        self.max_hand_tracking_distance_ = 0.20

        # Região de interação (coordenadas normalizadas)
        self.roi_x_min_ = 0.10
        self.roi_x_max_ = 0.90
        self.roi_y_min_ = 0.10
        self.roi_y_max_ = 0.90

        self.get_logger().info(f"Nó '{self.get_name()}' inicializado com sucesso.")


    def detect_gesture(self, msg):
        if self.processing_:
            self.get_logger().warn("Um frame foi descartado pois outro ainda estava sendo processado.")
            return

        if not self.ativo:
            return
        
        self.processing_ = True
        landmarks_to_draw = None
        mostrar_landmarks = self.get_parameter("mostrar_landmarks").value

        try:
            frame = self.bridge_.imgmsg_to_cv2(msg, desired_encoding="bgr8")
            if mostrar_landmarks:
                frame_to_show = frame.copy()
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
            
            timestamp_ms = int(time.monotonic() * 1000)
            result = self.detector_.recognize_for_video(mp_image, timestamp_ms)

            self.current_gesture_ = "none"
            score = 0
            self.frame_height_, self.frame_width_, _ = frame.shape
            
            # Constrói a lista de mãos detectadas.
            hands = []

            for i in range(len(result.gestures)):
                hand = Hand(
                    result.gestures[i][0],
                    result.hand_landmarks[i]
                )
                hands.append(hand)

            # Seleciona a mão que será acompanhada.
            selected_hand = self.select_hand(hands)

            self.current_gesture_ = "none"
            score = 0

            # Utiliza somente a mão selecionada como referência.
            if selected_hand is not None:
                landmarks_to_draw = selected_hand.landmarks

                # GESTOS SIMPLES
                if selected_hand.gesture_ not in self.two_handed_gestures_:
                    self.current_gesture_ = selected_hand.gesture_
                    score = selected_hand.score_

                # GESTOS DE DUAS MÃOS
                else:
                    # Procura possíveis parceiras entre todas as outras mãos.
                    candidate_hands = [
                        hand for hand in hands
                        if hand is not selected_hand
                        and hand.gesture_ == selected_hand.gesture_
                    ]

                    valid_pairs = []

                    for other_hand in candidate_hands:

                        # Verifica se as bounding boxes se intersectam.
                        intersect = selected_hand.box_.intersects(other_hand.box_)
                        if not intersect:
                            continue

                        # Verifica se as mãos possuem tamanhos semelhantes.
                        max_area = max(selected_hand.box_.area_,other_hand.box_.area_)

                        if max_area <= 0:
                            continue

                        proporcao = (min(selected_hand.box_.area_,other_hand.box_.area_) / max_area)

                        if proporcao > 0.7:
                            # Calcula a distância entre os centros das mãos.
                            dx = selected_hand.center_[0] - other_hand.center_[0]
                            dy = selected_hand.center_[1] - other_hand.center_[1]

                            distancia = (dx ** 2 + dy ** 2) ** 0.5

                            valid_pairs.append((proporcao, distancia, other_hand))

                    # Seleciona a melhor parceira, caso exista.
                    if valid_pairs:
                        # Prioriza tamanhos semelhantes e, em caso de
                        # empate, a menor distância entre os centros.
                        _, _, other_hand = min(
                            valid_pairs,
                            key=lambda pair: (-pair[0], pair[1])
                        )

                        self.current_gesture_ = selected_hand.gesture_

                        score = (selected_hand.score_ + other_hand.score_) / 2
   
            # Publica o gesto imediatamente no modo desenho.
            # Nos outros modos, mantém a estabilização de 5 frames.
            if self.num_gesture_frames_ == 1:
                self.str_msg_.data = (
                    self.current_gesture_
                    if score >= self.min_gesture_score_
                    else "none"
                )

                self.gesture_publisher_.publish(self.str_msg_)

            else:
                # Atualiza contador
                if self.current_gesture_ == self.last_gesture_:
                    if self.current_gesture_ == "none" or score >= self.min_gesture_score_:
                        self.gesture_counter_ += 1
                    else:
                        self.gesture_counter_ = 0
                else:
                    self.gesture_counter_ = 1 if (
                        self.current_gesture_ == "none" or score >= self.min_gesture_score_
                    ) else 0

                # Publica o resultado após a estabilização
                if self.gesture_counter_ >= self.num_gesture_frames_:
                    self.str_msg_.data = self.current_gesture_
                    self.gesture_publisher_.publish(self.str_msg_)
                    self.gesture_counter_ = 0

            self.last_gesture_ = self.current_gesture_

            # Publica os landmarks da mão selecionada.
            if landmarks_to_draw is not None:
                self.publish_landmarks(landmarks_to_draw)
            else:
                # Informa que nenhuma mão foi detectada neste frame.
                self.landmarks_publisher_.publish(Polygon())

            if mostrar_landmarks:
                # Desenha a região de interação.
                frame_to_show = self.draw_roi(frame_to_show)
                # Desenha landmarks da mão selecionada
                if landmarks_to_draw is not None:
                    frame_to_show = self.draw_hand_landmarks(frame_to_show, landmarks_to_draw)
                
                cv2.imshow("Detector de Gestos", frame_to_show)
                cv2.waitKey(1)

        except Exception as e:
            self.get_logger().error(f"Erro durante o processamento do frame: {e}")
        finally:  
            self.processing_ = False


    def select_hand(self, hands):
        """
        Seleciona inicialmente a mão mais próxima do centro da
        região de interação e mantém sua identidade pela posição
        nos frames seguintes.
        """

        # Nenhuma mão detectada
        if not hands:
            self.hand_lost_frames_ += 1

            if self.hand_lost_frames_ > self.max_hand_lost_frames_:
                self.selected_hand_center_ = None
                self.hand_lost_frames_ = 0

            return None

        # PRIMEIRA SELEÇÃO
        if self.selected_hand_center_ is None:

            center_x = (self.roi_x_min_ + self.roi_x_max_) / 2
            center_y = (self.roi_y_min_ + self.roi_y_max_) / 2

            hands_in_roi = [
                hand for hand in hands
                if self.roi_x_min_ <= hand.center_[0] <= self.roi_x_max_
                and self.roi_y_min_ <= hand.center_[1] <= self.roi_y_max_
            ]

            if not hands_in_roi:
                return None

            selected_hand = min(
                hands_in_roi,
                key=lambda hand: (
                    (hand.center_[0] - center_x) ** 2 +
                    (hand.center_[1] - center_y) ** 2
                )
            )

            self.selected_hand_center_ = selected_hand.center_
            self.hand_lost_frames_ = 0

            return selected_hand

        # CONTINUIDADE DO TRACKING
        selected_hand = min(
            hands,
            key=lambda hand: (
                (hand.center_[0] - self.selected_hand_center_[0]) ** 2 +
                (hand.center_[1] - self.selected_hand_center_[1]) ** 2
            )
        )

        dx = selected_hand.center_[0] - self.selected_hand_center_[0]
        dy = selected_hand.center_[1] - self.selected_hand_center_[1]

        distance = (dx ** 2 + dy ** 2) ** 0.5

        if distance <= self.max_hand_tracking_distance_:
            self.selected_hand_center_ = selected_hand.center_
            self.hand_lost_frames_ = 0

            return selected_hand

        # A mão selecionada não foi encontrada.
        self.hand_lost_frames_ += 1

        if self.hand_lost_frames_ > self.max_hand_lost_frames_:
            self.selected_hand_center_ = None
            self.hand_lost_frames_ = 0

        return None


    def reset_hand_tracking(self):
        self.selected_hand_center_ = None
        self.hand_lost_frames_ = 0


    def publish_landmarks(self, landmarks):
        polygon_msg_ = Polygon()
        for lm in landmarks:
            point = Point32()
            point.x = float(lm.x * self.frame_width_)
            point.y = float(lm.y * self.frame_height_)
            point.z = 0.0
            polygon_msg_.points.append(point)
        self.landmarks_publisher_.publish(polygon_msg_)


    def estado_atual_sub_callback(self,msg):
        if msg.data in ["MODO_DESENHO", "MODO_GESTOS"]:
            if not self.ativo:
                self.ativo = True
                self.reset_hand_tracking()

            if msg.data == "MODO_DESENHO":
                # passa a publicar o gesto sempre que detectar, sem esperar por 5 frames seguidos, para sincronizar taxa de publicação com o fps da câmera
                self.num_gesture_frames_ = 1    
            else:
                self.num_gesture_frames_ = 5

            self.gesture_counter_ = 1
            self.last_gesture_ = "none"

        else:
            if self.ativo:
                self.ativo = False
                self.reset_hand_tracking()


    def draw_hand_landmarks(self, image, landmarks):
        pixel_landmarks = []
        for lm in landmarks:
            x = int(lm.x * self.frame_width_)
            y = int(lm.y * self.frame_height_)
            pixel_landmarks.append((x, y))

        for point in pixel_landmarks:
            cv2.circle(image, point, 4, (0, 0, 255), -1)

        return image


    def draw_roi(self, image):
        height, width = image.shape[:2]

        # Converte as coordenadas normalizadas para pixels.
        x_min = int(self.roi_x_min_ * width)
        x_max = int(self.roi_x_max_ * width)
        y_min = int(self.roi_y_min_ * height)
        y_max = int(self.roi_y_max_ * height)

        # Desenha o retângulo da região de interação.
        cv2.rectangle(image,(x_min, y_min),(x_max, y_max),(0, 255, 255),2)

        return image

    def destroy_node(self):
        self.detector_.close()
        cv2.destroyAllWindows()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = DetectorGestosNode()
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