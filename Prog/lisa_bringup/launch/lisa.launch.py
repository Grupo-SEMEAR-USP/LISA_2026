from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    ld = LaunchDescription()

    camera_publisher = Node(
        package="lisa_pkg",
        executable="camera_publisher"
    )

    detector_gestos = Node(
        package="lisa_pkg",
        executable="detector_gestos"
    )

    controle_tela_service = Node(
        package="lisa_pkg",
        executable="controle_tela_service"
    )
    
    lisa_control = Node(
        package="lisa_pkg",
        executable="lisa_control"
    )

    speech_to_text = Node(
        package="lisa_pkg",
        executable="speech_to_text"
    )

    detector_comandos_de_voz = Node(
        package="lisa_pkg",
        executable="detector_comandos_de_voz"
    )

    ld.add_action(camera_publisher)
    ld.add_action(detector_gestos)
    ld.add_action(controle_tela_service)
    ld.add_action(lisa_control)
    ld.add_action(speech_to_text)
    ld.add_action(detector_comandos_de_voz)

    return ld