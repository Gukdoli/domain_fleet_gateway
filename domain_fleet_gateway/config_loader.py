"""Configuration loading helpers for domain_fleet_gateway."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


@dataclass(frozen=True)
class RobotConfig:
    robot_id: str
    namespace: str
    domain_id: int
    name: str
    color: str = '#4ECDC4'


@dataclass(frozen=True)
class FleetConfig:
    control_domain: int
    robots: List[RobotConfig]
    rosbridge_port: int = 9090
    topic_profile: str = 'navigation_full'
    bridge_output_dir: str = '/tmp/domain_fleet_gateway'
    pose_sources: List[str] = field(default_factory=lambda: ['odometry', 'amcl_pose'])
    monitored_topics: List[Dict[str, str]] = field(default_factory=list)


DEFAULT_MONITORED_TOPICS = [
    {'suffix': '/odometry', 'type': 'nav_msgs/msg/Odometry'},
    {'suffix': '/map', 'type': 'nav_msgs/msg/OccupancyGrid'},
    {'suffix': '/plan', 'type': 'nav_msgs/msg/Path'},
]


def normalize_namespace(namespace: str) -> str:
    namespace = str(namespace or '').strip()
    if not namespace:
        return '/'
    if not namespace.startswith('/'):
        namespace = '/' + namespace
    return namespace.rstrip('/') or '/'


def namespaced_topic(namespace: str, suffix: str) -> str:
    namespace = normalize_namespace(namespace)
    suffix = str(suffix or '').strip()
    if not suffix.startswith('/'):
        suffix = '/' + suffix
    if namespace == '/':
        return suffix
    return namespace + suffix


def _load_yaml(path: str) -> Dict[str, Any]:
    with Path(path).open('r', encoding='utf-8') as stream:
        data = yaml.safe_load(stream) or {}
    if not isinstance(data, dict):
        raise ValueError(f'Expected YAML mapping in {path}')
    return data


def load_fleet_config(path: str) -> FleetConfig:
    data = _load_yaml(path)
    robots_data = data.get('robots') or []
    if not robots_data:
        raise ValueError(f'No robots configured in {path}')

    robots: List[RobotConfig] = []
    for index, robot in enumerate(robots_data, start=1):
        robot_id = str(robot.get('id') or f'robot{index}')
        namespace = normalize_namespace(robot.get('namespace') or f'/{robot_id}')
        domain_id = int(robot.get('domain_id', index))
        robots.append(RobotConfig(
            robot_id=robot_id,
            namespace=namespace,
            domain_id=domain_id,
            name=str(robot.get('name') or robot_id),
            color=str(robot.get('color') or '#4ECDC4'),
        ))

    rosbridge = data.get('rosbridge') or {}
    bridge = data.get('bridge') or {}
    health = data.get('health') or {}

    return FleetConfig(
        control_domain=int(data.get('control_domain', 0)),
        robots=robots,
        rosbridge_port=int(rosbridge.get('port', 9090)),
        topic_profile=str(bridge.get('topic_profile', 'navigation_full')),
        bridge_output_dir=str(bridge.get('output_dir', '/tmp/domain_fleet_gateway')),
        pose_sources=list(data.get('pose_sources') or ['odometry', 'amcl_pose']),
        monitored_topics=list(health.get('monitored_topics') or DEFAULT_MONITORED_TOPICS),
    )


def get_robot_by_id(config: FleetConfig, robot_id: str) -> Optional[RobotConfig]:
    for robot in config.robots:
        if robot.robot_id == robot_id:
            return robot
    return None


def get_robot_by_namespace(config: FleetConfig, namespace: str) -> Optional[RobotConfig]:
    normalized = normalize_namespace(namespace)
    for robot in config.robots:
        if robot.namespace == normalized:
            return robot
    return None
