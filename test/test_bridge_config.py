from pathlib import Path

import yaml

from domain_fleet_gateway.bridge_config import generate_bridge_configs


PACKAGE_ROOT = Path(__file__).resolve().parents[1]


def test_generate_bridge_configs(tmp_path):
    generated = generate_bridge_configs(
        fleet_config_path=str(PACKAGE_ROOT / 'config' / 'fleet.yaml'),
        topic_profiles_path=str(PACKAGE_ROOT / 'config' / 'topic_profiles.yaml'),
        output_dir=str(tmp_path),
    )

    assert [item['robot_id'] for item in generated] == [
        'robot1',
        'robot2',
        'robot3',
    ]

    robot1_config = yaml.safe_load(Path(generated[0]['path']).read_text())
    assert robot1_config['name'] == 'robot1_bridge'
    assert robot1_config['from_domain'] == 1
    assert robot1_config['to_domain'] == 0

    topics = robot1_config['topics']
    assert topics['/odometry']['remap'] == '/robot1/odometry'
    assert topics['/map']['qos']['durability'] == 'transient_local'
    assert topics['/robot1/goal_pose']['reversed'] is True
    assert topics['/robot1/goal_pose']['remap'] == '/goal_pose'
