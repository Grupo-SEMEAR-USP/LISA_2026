from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    ld = LaunchDescription()

    camera_publisher = Node(
        package="lisa_pkg",
        executable="camera_publisher"
    )

    hand_gesture_detector = Node(
        package="lisa_pkg",
        executable="hand_gesture_detector"
    )

    display_control_service = Node(
        package="lisa_pkg",
        executable="display_control_service"
    )
    
    lisa_control = Node(
        package="lisa_pkg",
        executable="lisa_control"
    )

    ld.add_action(camera_publisher)
    ld.add_action(hand_gesture_detector)
    ld.add_action(display_control_service)
    ld.add_action(lisa_control)

    return ld