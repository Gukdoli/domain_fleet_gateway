"""Aggregate robot state topics into a single fleet state JSON topic."""

import json
import math
import time
from typing import Dict, Optional

from geometry_msgs.msg import PoseWithCovarianceStamped
from nav_msgs.msg import Odometry
import rclpy
from rclpy.node import Node
from std_msgs.msg import String

from domain_fleet_gateway.config_loader import load_fleet_config, namespaced_topic


def _yaw_from_quaternion(q) -> float:
    siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
    cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
    return math.atan2(siny_cosp, cosy_cosp)


class FleetStateAggregator(Node):
    def __init__(self):
        super().__init__('fleet_state_aggregator')
        self.declare_parameter('fleet_config', '')
        self.declare_parameter('publish_rate_hz', 5.0)
        self.declare_parameter('stale_after_sec', 2.0)

        config_path = self.get_parameter('fleet_config').value
        if not config_path:
            raise RuntimeError('Parameter fleet_config is required')

        self.fleet_config = load_fleet_config(config_path)
        self.stale_after_sec = float(self.get_parameter('stale_after_sec').value)
        publish_rate = float(self.get_parameter('publish_rate_hz').value)

        self.robot_states: Dict[str, Dict] = {}
        self._topic_subscriptions = []
        for robot in self.fleet_config.robots:
            self.robot_states[robot.robot_id] = {
                'id': robot.robot_id,
                'name': robot.name,
                'namespace': robot.namespace,
                'domain_id': robot.domain_id,
                'color': robot.color,
                'online': False,
                'stale': True,
                'source': None,
                'last_seen_monotonic': None,
                'last_seen_unix': None,
                'pose': None,
                'twist': None,
            }

            if 'odometry' in self.fleet_config.pose_sources:
                topic = namespaced_topic(robot.namespace, '/odometry')
                self._topic_subscriptions.append(self.create_subscription(
                    Odometry,
                    topic,
                    lambda msg, robot_id=robot.robot_id: self._odom_callback(robot_id, msg),
                    10,
                ))
                self.get_logger().info(f'Subscribed to {topic}')

            if 'amcl_pose' in self.fleet_config.pose_sources:
                topic = namespaced_topic(robot.namespace, '/amcl_pose')
                self._topic_subscriptions.append(self.create_subscription(
                    PoseWithCovarianceStamped,
                    topic,
                    lambda msg, robot_id=robot.robot_id: self._amcl_callback(robot_id, msg),
                    10,
                ))
                self.get_logger().info(f'Subscribed to {topic}')

        self.publisher = self.create_publisher(String, '/fleet/robot_states', 10)
        period = 1.0 / publish_rate if publish_rate > 0.0 else 0.2
        self.timer = self.create_timer(period, self._publish_state)

    def _update_pose(self, robot_id: str, pose, source: str, twist: Optional[Dict] = None):
        state = self.robot_states[robot_id]
        state['online'] = True
        state['stale'] = False
        state['source'] = source
        state['last_seen_monotonic'] = time.monotonic()
        state['last_seen_unix'] = time.time()
        state['pose'] = {
            'x': float(pose.position.x),
            'y': float(pose.position.y),
            'z': float(pose.position.z),
            'yaw': float(_yaw_from_quaternion(pose.orientation)),
        }
        if twist is not None:
            state['twist'] = twist

    def _odom_callback(self, robot_id: str, msg: Odometry):
        twist = {
            'linear_x': float(msg.twist.twist.linear.x),
            'linear_y': float(msg.twist.twist.linear.y),
            'angular_z': float(msg.twist.twist.angular.z),
        }
        self._update_pose(robot_id, msg.pose.pose, 'odometry', twist)

    def _amcl_callback(self, robot_id: str, msg: PoseWithCovarianceStamped):
        self._update_pose(robot_id, msg.pose.pose, 'amcl_pose')

    def _public_state(self, state: Dict, now: float) -> Dict:
        last_seen = state['last_seen_monotonic']
        age = None if last_seen is None else now - last_seen
        stale = last_seen is None or age > self.stale_after_sec
        return {
            'id': state['id'],
            'name': state['name'],
            'namespace': state['namespace'],
            'domain_id': state['domain_id'],
            'color': state['color'],
            'online': bool(last_seen is not None and not stale),
            'stale': bool(stale),
            'source': state['source'],
            'last_seen_unix': state['last_seen_unix'],
            'age_sec': age,
            'pose': state['pose'],
            'twist': state['twist'],
        }

    def _publish_state(self):
        now = time.monotonic()
        robots = [self._public_state(state, now) for state in self.robot_states.values()]
        online_count = sum(1 for robot in robots if robot['online'])
        payload = {
            'stamp_unix': time.time(),
            'control_domain': self.fleet_config.control_domain,
            'robot_count': len(robots),
            'online_count': online_count,
            'robots': robots,
        }
        msg = String()
        msg.data = json.dumps(payload, separators=(',', ':'))
        self.publisher.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = FleetStateAggregator()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
