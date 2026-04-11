#!/usr/bin/env python3

from sensor_msgs.msg import Image
from cv_bridge import CvBridge 
from example_interfaces.msg import String

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
Precisa encontrar o gesto em 5 frames seguidos antes de publicar, ou seja, a frequência de publicação desse nó é no máximo 1/5 do fps da câmera.

    Tópico inscrito: /frame
        - Tipo da mensagem: sensor_msgs/msg/Image 

    Tópico publicado: /hand_gestures
        - Tipo da mensagem: example_interfaces/msg/String

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
        if gesture.category_name:
            self.gesture_ = gesture.category_name.lower()
            self.score_ = gesture.score
        else:
            self.gesture_ = "none"
            self.score_ = 0

        if landmarks: 
            self.x_coords_ = [lm.x for lm in landmarks]
            self.y_coords_ = [lm.y for lm in landmarks]
        else:
            self.x_coords_, self.y_coords_ = [0.0], [0.0]

        self.box_ = Box(min(self.x_coords_), max(self.x_coords_), min(self.y_coords_), max(self.y_coords_))


# CLASSE PRINCIPAL
class DetectorGestosNode(Node):

    def __init__(self):
        super().__init__("detector_gestos")
        self.subscriber_ = self.create_subscription(Image, "frame", self.detect_gesture, 10)
        self.publisher_ =  self.create_publisher(String, "hand_gestures", 10)
        self.bridge_ = CvBridge()
        self.model_path_ = os.path.join(get_package_share_directory("lisa_pkg"), 'models', 'gesture_recognizer.task')

        options = vision.GestureRecognizerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=self.model_path_),
            running_mode=vision.RunningMode.VIDEO,
            num_hands = 2,
            min_hand_detection_confidence=0.7,
            min_hand_presence_confidence=0.5,
            min_tracking_confidence=0.5
        )
        self.detector_ = vision.GestureRecognizer.create_from_options(options)

        self.msg_ = String()
        self.processing_ = False # variável para travar o recebimento de frames, caso o nó ainda esteja processando o frame anterior
        self.min_gesture_score_ = 0.75 # só publica se o score for de 75% ou mais 
        self.gesture_counter_ = 0 # contador para verificar quantas vezes seguidas o gesto foi detectado
        self.num_gesture_frames_ = 5 # é necessário encontrar o mesmo gesto em 5 frames seguidos para publicá-lo
        self.current_gesture_ = "none"
        self.last_gesture_ = "none"

        self.two_handed_gestures_ = ["heart"]   # gestos que precisam ser detectados em duas mãos ao mesmo tempo (precisam ser simétricos)

        self.get_logger().info(f"Nó '{self.get_name()}' inicializado com sucesso.")


    def detect_gesture(self, msg):
        if self.processing_:
            self.get_logger().warn("Um frame foi descartado pois outro ainda estava sendo processado.")
            return
        
        self.processing_ = True

        try:
            frame = self.bridge_.imgmsg_to_cv2(msg, desired_encoding="bgr8")
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
            
            timestamp_ms = int(time.monotonic() * 1000)
            result = self.detector_.recognize_for_video(mp_image, timestamp_ms)

            self.current_gesture_ = "none"
            score = 0
            
            num_detected_hands = len(result.gestures)

            # 1 mão detectada
            if num_detected_hands == 1:
                hand1 = Hand(result.gestures[0][0], result.hand_landmarks[0])

                # elimina gestos de duas mãos de serem detectados
                if hand1.gesture_ not in self.two_handed_gestures_:
                    self.current_gesture_ = hand1.gesture_
                    score = hand1.score_
                else:
                    self.current_gesture_ = "none"
                    score = 0
    
            # 2 mãos detectadas
            elif num_detected_hands == 2:
                hand1 = Hand(result.gestures[0][0], result.hand_landmarks[0])
                hand2 = Hand(result.gestures[1][0], result.hand_landmarks[1])

                # GESTOS SIMPLES
                    # se forem detectados dois gestos diferentes nas duas mãos, publica o da mão que está mais próxima (maior área)
                    # caso contrário, só publica
                # GESTOS DE DUAS MÃOS
                    # esses gestos precisam ser detectados nas duas mãos ao mesmo tempo
                    # além disso, elas precisam estar próximas e ter o mesmo tamanho aproximado

                if hand1.gesture_ != hand2.gesture_:
                    # hand1 > hand2:
                    if hand1.box_.area_ > hand2.box_.area_:
                        # elimina gestos de duas mãos de serem detectados
                        if hand1.gesture_ not in self.two_handed_gestures_:
                            self.current_gesture_ = hand1.gesture_
                            score = hand1.score_
                        else:
                            self.current_gesture_ = "none"
                            score = 0
                    # hand1 < hand2:
                    else:
                        # elimina gestos de duas mãos de serem detectados
                        if hand2.gesture_ not in self.two_handed_gestures_:
                            self.current_gesture_ = hand2.gesture_
                            score = hand2.score_
                        else:
                            self.current_gesture_ = "none"
                            score = 0
                # gesto igual nas duas mãos, e não é gesto de duas mãos:
                elif hand1.gesture_ not in self.two_handed_gestures_:
                    self.current_gesture_ = hand1.gesture_
                    score = (hand1.score_ + hand2.score_)/2
                
                # gesto igual nas duas mãos, e é gesto de duas mãos:
                else:
                    # verifica se as áreas se interssectam
                    intersect = hand1.box_.intersects(hand2.box_)
                    # verifica se as duas mãos têm aproximadamente a mesma área (mesmo "tamanho")
                    if max(hand1.box_.area_, hand2.box_.area_) > 0:
                        proporcao = min(hand1.box_.area_, hand2.box_.area_) / max(hand1.box_.area_, hand2.box_.area_)
                    else:
                        proporcao = 0
                    
                    same_size = proporcao > 0.7   # a mão menor deve ter pelo menos 70% do tamanho da maior
                    
                    if intersect and same_size:
                        self.current_gesture_ = hand1.gesture_
                        score = (hand1.score_ + hand2.score_) / 2
                    else:
                        self.current_gesture_ = "none"
                        score = 0
            
            # Atualiza contador
            if self.current_gesture_ == self.last_gesture_ and self.current_gesture_ != "none" and score >= self.min_gesture_score_:
                self.gesture_counter_ += 1
            else:
                self.gesture_counter_ = 0

            # Publica o resultado
            if self.current_gesture_ not in ["none", None] and score >= self.min_gesture_score_ and self.gesture_counter_ >= self.num_gesture_frames_:
                self.get_logger().info(f"Gesto detectado: {self.current_gesture_}, Score: {score:.2f}")
                self.msg_.data = self.current_gesture_
                self.publisher_.publish(self.msg_)
                self.gesture_counter_ = 0

            self.last_gesture_ = self.current_gesture_

        except Exception as e:
            self.get_logger().error(f"Erro durante o processamento do frame: {e}")
        finally:  
            self.processing_ = False


def main(args=None):
    rclpy.init(args=args)
    node = DetectorGestosNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if hasattr(node, 'detector_'):
            node.detector_.close()

        node.destroy_node()

        if rclpy.ok():
            rclpy.shutdown()


if __name__=='__main__':
    main()