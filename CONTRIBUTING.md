# Contributing

Thanks for improving `domain_fleet_gateway`.

## Development Setup

```bash
mkdir -p ~/fleet_ws/src
cd ~/fleet_ws/src
git clone https://github.com/region/domain_fleet_gateway.git
cd ~/fleet_ws
source /opt/ros/humble/setup.bash
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install
```

## Before Opening a Pull Request

```bash
colcon test --packages-select domain_fleet_gateway
colcon test-result --verbose
```

Keep bridge behavior configurable through `config/topic_profiles.yaml` instead of hard-coding robot-specific topics.
