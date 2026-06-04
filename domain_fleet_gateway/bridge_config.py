"""Generate domain_bridge YAML files from a fleet configuration."""

from pathlib import Path
from typing import Any, Dict, List

import yaml

from domain_fleet_gateway.config_loader import FleetConfig, RobotConfig, load_fleet_config


def _load_profiles(path: str) -> Dict[str, Any]:
    with Path(path).open('r', encoding='utf-8') as stream:
        data = yaml.safe_load(stream) or {}
    profiles = data.get('profiles') or {}
    if not profiles:
        raise ValueError(f'No topic profiles configured in {path}')
    return profiles


def _format(value: Any, robot: RobotConfig) -> Any:
    if isinstance(value, str):
        return value.format(
            robot_id=robot.robot_id,
            namespace=robot.namespace,
            domain_id=robot.domain_id,
        )
    if isinstance(value, list):
        return [_format(item, robot) for item in value]
    if isinstance(value, dict):
        return {key: _format(item, robot) for key, item in value.items()}
    return value


def _topic_entry(entry: Dict[str, Any], robot: RobotConfig) -> Dict[str, Any]:
    topic_data: Dict[str, Any] = {
        'type': _format(entry['type'], robot),
    }
    if 'remap' in entry:
        topic_data['remap'] = _format(entry['remap'], robot)
    if entry.get('reversed'):
        topic_data['reversed'] = True
    if 'qos' in entry:
        topic_data['qos'] = _format(entry['qos'], robot)
    return topic_data


def build_bridge_config(
    fleet_config: FleetConfig,
    profile: Dict[str, Any],
    robot: RobotConfig,
) -> Dict[str, Any]:
    topics: Dict[str, Dict[str, Any]] = {}
    for entry in profile.get('forward', []):
        topics[_format(entry['topic'], robot)] = _topic_entry(entry, robot)
    for entry in profile.get('reverse', []):
        entry = dict(entry)
        entry['reversed'] = True
        topics[_format(entry['topic'], robot)] = _topic_entry(entry, robot)

    return {
        'name': f'{robot.robot_id}_bridge',
        'from_domain': robot.domain_id,
        'to_domain': fleet_config.control_domain,
        'topics': topics,
    }


def generate_bridge_configs(
    fleet_config_path: str,
    topic_profiles_path: str,
    output_dir: str = '',
) -> List[Dict[str, str]]:
    fleet_config = load_fleet_config(fleet_config_path)
    profiles = _load_profiles(topic_profiles_path)
    if fleet_config.topic_profile not in profiles:
        known = ', '.join(sorted(profiles.keys()))
        raise ValueError(
            f'Unknown topic profile {fleet_config.topic_profile!r}. Known: {known}'
        )

    output_path = Path(output_dir or fleet_config.bridge_output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    profile = profiles[fleet_config.topic_profile]

    generated = []
    for robot in fleet_config.robots:
        config = build_bridge_config(fleet_config, profile, robot)
        file_path = output_path / f'{robot.robot_id}_domain_bridge.yaml'
        with file_path.open('w', encoding='utf-8') as stream:
            yaml.safe_dump(config, stream, sort_keys=False, allow_unicode=True)
        generated.append({
            'robot_id': robot.robot_id,
            'path': str(file_path),
        })
    return generated
