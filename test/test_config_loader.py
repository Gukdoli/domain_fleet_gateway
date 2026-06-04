from pathlib import Path

from domain_fleet_gateway.config_loader import (
    load_fleet_config,
    namespaced_topic,
    normalize_namespace,
)


PACKAGE_ROOT = Path(__file__).resolve().parents[1]


def test_normalize_namespace():
    assert normalize_namespace('robot1') == '/robot1'
    assert normalize_namespace('/robot1/') == '/robot1'
    assert normalize_namespace('') == '/'


def test_namespaced_topic():
    assert namespaced_topic('/robot1', '/odometry') == '/robot1/odometry'
    assert namespaced_topic('robot2', 'map') == '/robot2/map'
    assert namespaced_topic('/', '/clock') == '/clock'


def test_load_default_fleet_config():
    config = load_fleet_config(str(PACKAGE_ROOT / 'config' / 'fleet.yaml'))

    assert config.control_domain == 0
    assert config.rosbridge_port == 9090
    assert config.topic_profile == 'navigation_full'
    assert [robot.robot_id for robot in config.robots] == [
        'robot1',
        'robot2',
        'robot3',
    ]
    assert [robot.domain_id for robot in config.robots] == [1, 2, 3]
    assert [robot.namespace for robot in config.robots] == [
        '/robot1',
        '/robot2',
        '/robot3',
    ]
