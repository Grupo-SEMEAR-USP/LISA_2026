#!/usr/bin/env python3

from sensor_msgs.msg import Image
from cv_bridge import CvBridge 
from example_interfaces.msg import String
from geometry_msgs.msg import Point32, Polygon

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from ament_index_python.packages import get_package_share_directory

import cv2
import mediapipe as mp
from mediapipe.tasks.python import vision
from mediapipe.tasks.python.vision import drawing_utils
from mediapipe.tasks.python.vision import drawing_styles
import numpy as np
import time
import os

'''
Detector de Pose

Processa o frame da câmera com mediapipe e publica os landmarks relativos à pose, que inclui rosto, braços e tronco.

    Parâmetros:
        - mostrar_landmarks: mostra frame com landmarks detectados na tela

    Tópico inscrito: /controle/estado_atual
        - Tipo da mensagem: example_interfaces/msg/String 

    Tópico inscrito: /visao/frame
        - Tipo da mensagem: sensor_msgs/msg/Image 

    Tópico publicado: /visao/pose_landmaks
        - Tipo da mensagem: geometry_msgs/msg/Polygon

'''

class DetectorPoseNode(Node):

    def __init__(self):
        super().__init__("detector_pose")

        self.declare_parameter("mostrar_landmarks", False)

        self.subscriber_ = self.create_subscription(Image, "visao/frame", self.detect_pose, qos_profile_sensor_data)
        self.landmarks_publisher_ =  self.create_publisher(Polygon, "visao/pose_landmaks", qos_profile_sensor_data)
        self.estado_atual_subscription_ = self.create_subscription(String, "controle/estado_atual", self.estado_atual_sub_callback, 10)

        self.bridge_ = CvBridge()
        self.model_path_ = os.path.join(get_package_share_directory("lisa_pkg"), 'models', 'pose_landmarker_lite.task')
        
        options = vision.PoseLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=self.model_path_),
            running_mode=vision.RunningMode.VIDEO,
            num_poses = 2,
            min_pose_detection_confidence=0.7,
            min_pose_presence_confidence=0.5,
            min_tracking_confidence=0.5
        )
        self.detector_ = vision.PoseLandmarker.create_from_options(options)

        self.frame_height_ = 0
        self.frame_width_ = 0
        self.str_msg_ = String()
        self.processing_ = False # variável para travar o recebimento de frames, caso o nó ainda esteja processando o frame anterior
        self.ativo = False   

        self.get_logger().info(f"Nó '{self.get_name()}' inicializado com sucesso.")


    def detect_pose(self, msg):
        if self.processing_:
            self.get_logger().warn("Um frame foi descartado pois outro ainda estava sendo processado.")
            return

        if not self.ativo:
            return
        
        self.processing_ = True
        mostrar_landmarks = self.get_parameter("mostrar_landmarks").value

        try:
            frame = self.bridge_.imgmsg_to_cv2(msg, desired_encoding="bgr8")
            if mostrar_landmarks:
                frame_to_show = frame.copy()
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
            
            timestamp_ms = int(time.monotonic() * 1000)
            result = self.detector_.detect_for_video(mp_image, timestamp_ms)

            self.frame_height_, self.frame_width_, _ = frame.shape

            detected_poses = result.pose_landmarks
            closest_pose_lm = None
            max_area = -1.0

            for pose_lm in detected_poses:
                min_x = min(lm.x for lm in pose_lm)
                max_x = max(lm.x for lm in pose_lm)
                min_y = min(lm.y for lm in pose_lm)
                max_y = max(lm.y for lm in pose_lm)
            
                width = (max_x - min_x) * self.frame_width_
                height = (max_y - min_y) * self.frame_height_
                area = width * height

                if area > max_area:
                    max_area = area
                    closest_pose_lm = pose_lm

            if closest_pose_lm is not None:
                self.publish_landmarks(closest_pose_lm)
                if mostrar_landmarks:
                    frame_to_show = self.draw_landmarks_on_image(frame_to_show, closest_pose_lm)

            if mostrar_landmarks:
                    cv2.imshow("Detector de Pose", frame_to_show)
                    cv2.waitKey(1)

        except Exception as e:
            self.get_logger().error(f"Erro durante o processamento do frame: {e}")
        finally:  
            self.processing_ = False


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
        if msg.data == "MODO_MIMICA":
            if not self.ativo:
                self.ativo = True    
        else:
            if self.ativo:
                self.ativo = False    

    def draw_landmarks_on_image(self, rgb_image, pose_landmarks):
        annotated_image = np.copy(rgb_image)

        pose_landmark_style = drawing_styles.get_default_pose_landmarks_style()
        pose_connection_style = drawing_utils.DrawingSpec(color=(0, 255, 0), thickness=2)

        drawing_utils.draw_landmarks(
            image=annotated_image,
            landmark_list=pose_landmarks,
            connections=vision.PoseLandmarksConnections.POSE_LANDMARKS,
            landmark_drawing_spec=pose_landmark_style,
            connection_drawing_spec=pose_connection_style)

        return annotated_image


    def destroy_node(self):
        self.detector_.close()
        cv2.destroyAllWindows()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = DetectorPoseNode()
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