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
import numpy as np
import os

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
        self.model_path_ = os.path.join(get_package_share_directory("lisa_pkg"), 'models', 'gesture_recognizer.task')

        options = vision.GestureRecognizerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=self.model_path_),
            running_mode=vision.RunningMode.VIDEO,
            num_hands = 1,
            min_hand_detection_confidence=0.5,
            min_hand_presence_confidence=0.5,
            min_tracking_confidence=0.5
        )
        self.detector_ = vision.GestureRecognizer.create_from_options(options)

        self.msg_ = String()
        self.processing_ = False # variável para travar o recebimento de frames, caso o nó ainda esteja processando o frame anterior
        self.min_gesture_score_ = 0.6 # só publica se o score for de 60% ou mais 

        self.get_logger().info(f"Nó '{self.get_name()}' inicializado com sucesso.")

    def get_palm_centroid(self, coordinates_array):
        palm_idx = [0, 1, 2, 5, 9, 13, 17]
        palm_points = coordinates_array[palm_idx]
        centroid = np.mean(palm_points, axis=0)
        centroid = int(centroid[0]), int(centroid[1])
        return centroid

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

            current_hand_gesture = "None"
            
            if result.gestures:
                current_hand_gesture = result.gestures[0][0].category_name
                score = result.gestures[0][0].score

            # Publica o resultado
            if current_hand_gesture != "None" and score >= self.min_gesture_score_:
                self.get_logger().info(f"Gesto detectado: {current_hand_gesture}, Score: {score:.2f}")
                self.msg_.data = current_hand_gesture
                self.publisher_.publish(self.msg_)

            # Mostra frame na tela
            # self.show_frame(frame)

        except Exception as e:
            self.get_logger().error(f"Erro durante o processamento do frame: {e}")
        finally:  
            self.processing_ = False

    def draw_hand_landmarks(self, hand_landmarks, centroid, frame, landmarks_color=(0, 255, 0), connections_color=(255, 0, 0)):
        h, w, _ = frame.shape
        # desenha pontos detectados pelo mediapipe
        for landmark in hand_landmarks:
            x = int(landmark.x * w)
            y = int(landmark.y * h)
            cv2.circle(frame, (x, y), 5, landmarks_color, -1)
        # desenha centroide
        cv2.circle(frame, centroid, 5, (0,0,255), -1)
        # desenha conexões
        for connection in vision.HandLandmarksConnections.HAND_CONNECTIONS:
            start_idx = connection.start
            end_idx = connection.end

            x0 = int(hand_landmarks[start_idx].x * w)
            y0 = int(hand_landmarks[start_idx].y * h)
            x1 = int(hand_landmarks[end_idx].x * w)
            y1 = int(hand_landmarks[end_idx].y * h)

            cv2.line(frame, (x0, y0), (x1, y1), connections_color, 2)

    def show_frame(self, frame):
        flipped_frame = cv2.flip(frame,1)
        cv2.imshow("frame", flipped_frame)
        cv2.waitKey(1)


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