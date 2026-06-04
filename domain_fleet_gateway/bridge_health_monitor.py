"""Publish freshness information for bridged robot topics."""

import json
import time
from typing import Dict

from geometry_msgs.msg import PoseWithCovarianceStamped, Twist
from nav_msgs.msg import OccupancyGrid, Odometry, Path
import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import Imu, LaserScan
from std_msgs.msg import String

from domain_fleet_gateway.config_loader import load_fleet_config, namespaced_topic


TYPE_MAP = {
    'geometry_msgs/msg/PoseWithCovarianceStamped': PoseWithCovarianceStamped,
    'geometry_msgs/msg/Twist': Twist,
    'nav_msgs/msg/OccupancyGrid': OccupancyGrid,
    'nav_msgs/msg/Odometry': Odometry,
    'nav_msgs/msg/Path': Path,
    'sensor_msgs/msg/Imu': Imu,
    'sensor_msgs/msg/LaserScan': LaserScan,
}


class BridgeHealthMonitor(Node):
    def __init__(self):
        super().__init__('bridge_health_monitor')
        self.declare_parameter('fleet_config', '')
        self.declare_parameter('publish_rate_hz', 1.0)
        self.declare_parameter('stale_after_sec', 2.0)

        config_path = self.get_parameter('fleet_config').value
        if not config_path:
            raise RuntimeError('Parameter fleet_config is required')

        self.fleet_config = load_fleet_config(config_path)
        self.stale_after_sec = float(self.get_parameter('stale_after_sec').value)
        publish_rate = float(self.get_parameter('publish_rate_hz').value)

        self.topic_state: Dict[str, Dict[str, Dict]] = {}
        self._topic_subscriptions = []
        for robot in self.fleet_config.robots:
            self.topic_state[robot.robot_id] = {}
            for topic_config in self.fleet_config.monitored_topics:
                suffix = topic_config.get('suffix', '')
                type_name = topic_config.get('type', '')
                msg_type = TYPE_MAP.get(type_name)
                if msg_type is None:
                    self.get_logger().warn(f'Unsupported health topic type: {type_name}')
                    continue

                topic = namespaced_topic(robot.namespace, suffix)
                self.topic_state[robot.robot_id][suffix] = {
                    'topic': topic,
                    'type': type_name,
                    'last_seen_monotonic': None,
                    'last_seen_unix': None,
                    'count': 0,
                }
                self._topic_subscriptions.append(self.create_subscription(
                    msg_type,
                    topic,
                    lambda msg, robot_id=robot.robot_id, suffix=suffix:
                    self._topic_callback(robot_id, suffix),
                    self._qos_for_suffix(suffix),
                ))
                self.get_logger().info(f'Health monitor subscribed to {topic}')

        self.publisher = self.create_publisher(String, '/fleet/bridge_health', 10)
        period = 1.0 / publish_rate if publish_rate > 0.0 else 1.0
        self.timer = self.create_timer(period, self._publish_health)

    def _qos_for_suffix(self, suffix: str):
        if suffix == '/map':
            return QoSProfile(
                depth=1,
                durability=DurabilityPolicy.TRANSIENT_LOCAL,
                reliability=ReliabilityPolicy.RELIABLE,
            )
        return 10

    def _topic_callback(self, robot_id: str, suffix: str):
        state = self.topic_state[robot_id][suffix]
        state['last_seen_monotonic'] = time.monotonic()
        state['last_seen_unix'] = time.time()
        state['count'] += 1

    def _publish_health(self):
        now = time.monotonic()
        robots = []
        for robot in self.fleet_config.robots:
            topics = {}
            online_topics = 0
            for suffix, state in self.topic_state[robot.robot_id].items():
                last_seen = state['last_seen_monotonic']
                age = None if last_seen is None else now - last_seen
                fresh = last_seen is not None and age <= self.stale_after_sec
                if fresh:
                    online_topics += 1
                topics[suffix] = {
                    'topic': state['topic'],
                    'type': state['type'],
                    'fresh': fresh,
                    'age_sec': age,
                    'last_seen_unix': state['last_seen_unix'],
                    'count': state['count'],
                }

            robots.append({
                'id': robot.robot_id,
                'namespace': robot.namespace,
                'domain_id': robot.domain_id,
                'fresh_topic_count': online_topics,
                'topic_count': len(topics),
                'status': 'online' if online_topics > 0 else 'offline',
                'topics': topics,
            })

        msg = String()
        msg.data = json.dumps({
            'stamp_unix': time.time(),
            'robots': robots,
        }, separators=(',', ':'))
        self.publisher.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = BridgeHealthMonitor()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
