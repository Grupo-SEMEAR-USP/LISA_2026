from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    ld = LaunchDescription()

    controle_estados = Node(
        package="lisa_pkg",
        executable="controle_estados"
    )

    controle_tela = Node(
        package="lisa_pkg",
        executable="controle_tela"
    )

    camera_publisher = Node(
        package="lisa_pkg",
        executable="camera_publisher",
        parameters=[
            {"fps": 10},
            {"frame_w": 320},
            {"frame_h": 240},
            {"mostrar_camera": False}
        ]
    )

    detector_gestos = Node(
        package="lisa_pkg",
        executable="detector_gestos",
        parameters=[
            {"mostrar_landmarks": False}
        ]
    )

    detector_pose = Node(
        package="lisa_pkg",
        executable="detector_pose",
        parameters=[
            {"mostrar_landmarks": False}
        ]
    )
    
    detector_comandos_de_voz = Node(
        package="lisa_pkg",
        executable="detector_comandos_de_voz"
    )

    modo_gestos = Node(
        package="lisa_pkg",
        executable="modo_gestos"
    )

    modo_desenho = Node(
        package="lisa_pkg",
        executable="modo_desenho"
    )

    ld.add_action(controle_estados)
    ld.add_action(controle_tela)
    ld.add_action(camera_publisher)
    ld.add_action(detector_gestos)
    ld.add_action(detector_comandos_de_voz)
    ld.add_action(detector_pose)
    ld.add_action(modo_gestos)
    ld.add_action(modo_desenho)

    return ld