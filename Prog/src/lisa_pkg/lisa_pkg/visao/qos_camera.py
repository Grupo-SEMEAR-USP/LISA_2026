from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy

qos_camera = QoSProfile(
    history=HistoryPolicy.KEEP_LAST,
    depth=1,
    reliability=ReliabilityPolicy.BEST_EFFORT
)