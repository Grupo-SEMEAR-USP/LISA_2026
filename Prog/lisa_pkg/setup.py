from setuptools import find_packages, setup
import os
from glob import glob

package_name = 'lisa_pkg'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        
        # adiciona a pasta models e telas para que os codigos consigam encontrar:

        (os.path.join('share', package_name, 'models/vosk-model-small-pt-0.3'), 
         [f for f in glob('models/vosk-model-small-pt-0.3/*') if os.path.isfile(f)]),
        
        (os.path.join('share', package_name, 'models/vosk-model-small-pt-0.3/ivector'), 
         glob('models/vosk-model-small-pt-0.3/ivector/*')),

        (os.path.join('share', package_name, 'models'), glob('models/*.task')),
        (os.path.join('share', package_name, 'telas'), glob('telas/*')),  
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='semear',
    maintainer_email='o.semear@gmail.com',
    description='TODO: Package description',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            "camera_publisher = lisa_pkg.camera_publisher:main",
            "controle_tela_service = lisa_pkg.controle_tela_service:main",
            "lisa_control = lisa_pkg.lisa_control:main",
            "detector_gestos = lisa_pkg.detector_gestos:main",
            "speech_to_text = lisa_pkg.speech_to_text:main",
            "detector_comandos_de_voz = lisa_pkg.detector_comandos_de_voz:main"
        ],
    },
)
