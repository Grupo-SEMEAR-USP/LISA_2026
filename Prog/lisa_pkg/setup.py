from setuptools import find_packages, setup

package_name = 'lisa_pkg'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
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
            "hand_gesture_detector = lisa_pkg.hand_gesture_detector:main",
            "display_control_service = lisa_pkg.display_control_service:main",
            "lisa_control = lisa_pkg.lisa_control:main"
        ],
    },
)
