"""Route fleet-level goal commands to robot-specific Nav2 goal topics."""

import json
import math
from typing import Dict, Optional

from geometry_msgs.msg import PoseStamped
import rclpy
from rclpy.node import Node
from std_msgs.msg import String

from domain_fleet_gateway.config_loader import (
    get_robot_by_id,
    get_robot_by_namespace,
    load_fleet_config,
    namespaced_topic,
)


def _quaternion_from_yaw(yaw: float) -> Dict[str, float]:
    half = yaw * 0.5
    return {
        'x': 0.0,
        'y': 0.0,
        'z': math.sin(half),
        'w': math.cos(half),
    }


class GoalRouter(Node):
    def __init__(self):
        super().__init__('goal_router')
        self.declare_parameter('fleet_config', '')
        self.declare_parameter('default_frame_id', 'map')

        config_path = self.get_parameter('fleet_config').value
        if not config_path:
            raise RuntimeError('Parameter fleet_config is required')

        self.fleet_config = load_fleet_config(config_path)
        self.default_frame_id = str(self.get_parameter('default_frame_id').value)

        self.goal_publishers = {}
        for robot in self.fleet_config.robots:
            topic = namespaced_topic(robot.namespace, '/goal_pose')
            self.goal_publishers[robot.robot_id] = self.create_publisher(
                PoseStamped,
                topic,
                10,
            )
            self.get_logger().info(f'Goal route: /fleet/goal_command -> {topic}')

        self.events_pub = self.create_publisher(String, '/fleet/goal_events', 10)
        self.command_sub = self.create_subscription(
            String,
            '/fleet/goal_command',
            self._command_callback,
            10,
        )

    def _find_robot(self, command: Dict) -> Optional[str]:
        robot_id = command.get('robot_id')
        namespace = command.get('namespace')
        if robot_id:
            robot = get_robot_by_id(self.fleet_config, str(robot_id))
            return robot.robot_id if robot else None
        if namespace:
            robot = get_robot_by_namespace(self.fleet_config, str(namespace))
            return robot.robot_id if robot else None
        return None

    def _build_goal(self, command: Dict) -> PoseStamped:
        x = float(command['x'])
        y = float(command['y'])
        z = float(command.get('z', 0.0))
        yaw = float(command.get('yaw', 0.0))
        frame_id = str(command.get('frame_id') or self.default_frame_id)
        quaternion = command.get('orientation') or _quaternion_from_yaw(yaw)

        msg = PoseStamped()
        msg.header.frame_id = frame_id
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.pose.position.x = x
        msg.pose.position.y = y
        msg.pose.position.z = z
        msg.pose.orientation.x = float(quaternion.get('x', 0.0))
        msg.pose.orientation.y = float(quaternion.get('y', 0.0))
        msg.pose.orientation.z = float(quaternion.get('z', 0.0))
        msg.pose.orientation.w = float(quaternion.get('w', 1.0))
        return msg

    def _publish_event(self, status: str, detail: Dict):
        event = {
            'status': status,
            **detail,
        }
        msg = String()
        msg.data = json.dumps(event, separators=(',', ':'))
        self.events_pub.publish(msg)

    def _command_callback(self, msg: String):
        try:
            command = json.loads(msg.data)
            if not isinstance(command, dict):
                raise ValueError('Command must be a JSON object')
            robot_id = self._find_robot(command)
            if not robot_id:
                raise ValueError('Command must include a known robot_id or namespace')
            if 'x' not in command or 'y' not in command:
                raise ValueError('Command must include x and y')
            goal = self._build_goal(command)
        except Exception as exc:
            self.get_logger().warn(f'Invalid goal command: {exc}')
            self._publish_event('rejected', {
                'reason': str(exc),
                'raw': msg.data,
            })
            return

        self.goal_publishers[robot_id].publish(goal)
        self._publish_event('accepted', {
            'robot_id': robot_id,
            'x': goal.pose.position.x,
            'y': goal.pose.position.y,
            'frame_id': goal.header.frame_id,
        })
        self.get_logger().info(
            f'Routed goal to {robot_id}: '
            f'({goal.pose.position.x:.3f}, {goal.pose.position.y:.3f})'
        )


def main(args=None):
    rclpy.init(args=args)
    node = GoalRouter()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
