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
        executable="camera_publisher"
    )

    detector_gestos = Node(
        package="lisa_pkg",
        executable="detector_gestos"
    )
    
    modo_gestos = Node(
        package="lisa_pkg",
        executable="modo_gestos"
    )

    speech_to_text = Node(
        package="lisa_pkg",
        executable="speech_to_text"
    )

    detector_comandos_de_voz = Node(
        package="lisa_pkg",
        executable="detector_comandos_de_voz"
    )

    ld.add_action(controle_estados)
    ld.add_action(controle_tela)
    ld.add_action(camera_publisher)
    ld.add_action(detector_gestos)
    ld.add_action(modo_gestos)
    ld.add_action(detector_comandos_de_voz)
    #ld.add_action(speech_to_text)

    return ld