#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
import cv2
from sensor_msgs.msg import Image
from cv_bridge import CvBridge 
from example_interfaces.msg import String
import mediapipe as mp
from mediapipe.tasks.python import vision
import time
import numpy as np
from math import acos, degrees

'''
Detector de Gestos de Mão

Processa o frame da câmera com mediapipe e publica os gestos de mão que forem detectados.

    Tópico inscrito: /frame
        - Tipo da mensagem: sensor_msgs/msg/Image 

    Tópico publicado: /hand_gestures
        - Tipo da mensagem: example_interfaces/msg/String

'''

class DetectorGestosNode(Node):

    def __init__(self):
        super().__init__("detector_gestos")
        self.subscriber_ = self.create_subscription(Image, "frame", self.detect_gesture, 10)
        self.publisher_ =  self.create_publisher(String, "hand_gestures", 10)
        self.bridge_ = CvBridge()

        options = vision.HandLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path='/home/jplop/ros2_ws_teste/src/lisa_pkg/lisa_pkg/hand_landmarker.task'),
            running_mode=vision.RunningMode.VIDEO,
            num_hands = 1,
            min_hand_detection_confidence=0.5,
            min_hand_presence_confidence=0.5,
            min_tracking_confidence=0.5
        )
        self.detector_ = vision.HandLandmarker.create_from_options(options)

        self.UP_VECTOR_ = np.array([0,-1])
        self.msg_ = String()
        self.processing_ = False # variável para travar o recebimento de frames, caso o nó ainda esteja processando o frame anterior

        self.get_logger().info(f"Nó '{self.get_name()}' inicializado com sucesso.")

    def detect_gesture(self, msg):

        if self.processing_:
            self.get_logger().warn("Um frame foi descartado pois outro ainda estava sendo processado.")
            return
        
        self.processing_ = True

        try:
            frame = self.bridge_.imgmsg_to_cv2(msg, desired_encoding="bgr8")
            h, w, _ = frame.shape
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
            
            timestamp_ms = int(time.monotonic() * 1000)
            result = self.detector_.detect_for_video(mp_image, timestamp_ms)

            if result.hand_landmarks:
                hand_landmarks = result.hand_landmarks[0]

                # Armazena coordenadas de todos os pontos da mao
                hand_points = np.array([[lm.x * w, lm.y * h] for lm in hand_landmarks])

                # Detecta se é mão esquerda ou direita
                is_right_hand = result.handedness[0][0].category_name == 'Right'
                
                # Verifica se a palma da mao esta virada para a camera
                p5_x = hand_points[5, 0]
                p17_x = hand_points[17, 0]
                is_palm_facing_camera = not ((p5_x - p17_x > 0) ^ is_right_hand)

                # Verifica se o polegar esta extendido
                p1, p2, p4 = hand_points[1], hand_points[2], hand_points[4]
                
                l1 = np.linalg.norm(p2 - p4)
                l2 = np.linalg.norm(p1 - p4)
                l3 = np.linalg.norm(p1 - p2)

                if l1 != 0 and l3 != 0:
                    cos_angle = (l1**2 + l3**2 - l2**2) / (2*l1*l3)
                    cos_angle = np.clip(cos_angle, -1.0, 1.0)
                    angle = degrees(acos(cos_angle))
                else:
                    angle = 0
                
                is_thumb_extended = angle > 150

                # Verifica direcao do polegar (cima ou baixo)
                thumb_vector = p4 - p2
                thumb_vector_norm = np.linalg.norm(thumb_vector)
                if thumb_vector_norm != 0:
                    thumb_vector = thumb_vector / thumb_vector_norm
                else:
                    thumb_vector = np.array([0,0])

                thumb_vertical_alignment = np.dot(thumb_vector, self.UP_VECTOR_)
                is_thumb_up = thumb_vertical_alignment > 0.7
                is_thumb_down = thumb_vertical_alignment < -0.7

                # Verifica direcao do dedo indicador (cima ou baixo)
                p6 = hand_points[6]
                p8 = hand_points[8]

                index_vector = p8 - p6
                index_vector_norm = np.linalg.norm(index_vector)
                if index_vector_norm != 0:
                    index_vector = index_vector / index_vector_norm
                else:
                    index_vector = np.array([0,0])

                index_vertical_alignment = np.dot(index_vector, self.UP_VECTOR_)
                is_index_up = index_vertical_alignment > 0.7
                is_index_down = index_vertical_alignment < -0.7

                # Verifica se os dedos indicador, medio, anular e mindinho estao extendidos
                fingertips_indexes = [8, 12, 16, 20]
                fingerbases_indexes = [6, 10, 14, 18]
                
                distance_fingertips_to_palmbase = np.linalg.norm(hand_points[0] - hand_points[fingertips_indexes], axis=1)
                distance_fingerbases_to_palmbase = np.linalg.norm(hand_points[0] - hand_points[fingerbases_indexes], axis=1)
                fingers_extended = (distance_fingertips_to_palmbase - distance_fingerbases_to_palmbase) > 0
                
                is_index_extended, is_middle_extended, is_ring_extended, is_pinky_extended = fingers_extended
                
                # ------- DETECÇÃO DE GESTOS -------
                current_hand_gesture = None

                # Ok
                distance_p4_to_p8 = np.linalg.norm(p4 - p8)
                
                if (distance_p4_to_p8 < 40) and not is_index_extended and is_middle_extended and is_ring_extended and is_pinky_extended:
                    current_hand_gesture = "Ok Sign"

                # Hi-Five
                elif is_thumb_extended and is_index_extended and is_middle_extended and is_ring_extended and is_pinky_extended and is_palm_facing_camera:                  
                    current_hand_gesture = "High Five"

                # Hang-Loose
                elif is_thumb_extended and not is_index_extended and not is_middle_extended and not is_ring_extended and is_pinky_extended:
                    current_hand_gesture = "Hang Loose"
                
                # Peace
                elif not is_thumb_extended and is_index_extended and is_middle_extended and not is_ring_extended and not is_pinky_extended:
                    current_hand_gesture = "Peace Sign"

                # Rock
                elif is_index_extended and not is_middle_extended and not is_ring_extended and is_pinky_extended:
                    current_hand_gesture = "Rock Sign"
                
                # Middle finger
                elif not is_index_extended and is_middle_extended and not is_ring_extended and not is_pinky_extended:
                    current_hand_gesture = "Middle Finger"

                # Thumbs Up
                elif is_thumb_up and not is_index_up and not is_index_down and is_thumb_extended and not is_index_extended and not is_middle_extended and not is_ring_extended and not is_pinky_extended:
                    current_hand_gesture = "Thumbs Up"

                # Thumbs Down
                elif is_thumb_down and not is_index_up and not is_index_down and is_thumb_extended and not is_index_extended and not is_middle_extended and not is_ring_extended and not is_pinky_extended:
                    current_hand_gesture = "Thumbs Down"
                
                # Publica o resultado
                if current_hand_gesture is not None:
                    self.msg_.data = current_hand_gesture
                    self.publisher_.publish(self.msg_)
            
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
