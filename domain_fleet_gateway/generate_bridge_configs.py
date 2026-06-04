"""CLI entry point for generating domain_bridge YAML files."""

import argparse

from domain_fleet_gateway.bridge_config import generate_bridge_configs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--fleet-config', required=True)
    parser.add_argument('--topic-profiles', required=True)
    parser.add_argument('--output-dir', default='')
    args = parser.parse_args()

    generated = generate_bridge_configs(
        fleet_config_path=args.fleet_config,
        topic_profiles_path=args.topic_profiles,
        output_dir=args.output_dir,
    )
    for item in generated:
        print(f"{item['robot_id']}: {item['path']}")


if __name__ == '__main__':
    main()
