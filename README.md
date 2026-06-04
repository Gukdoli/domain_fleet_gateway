# domain_fleet_gateway

`domain_fleet_gateway` is a ROS 2 Python package for supervising robots that are isolated with different `ROS_DOMAIN_ID` values.

It runs on the control-tower domain, generates `domain_bridge` configurations from a fleet YAML file, starts the bridge and rosbridge stack, and exposes a small fleet-level API for web dashboards or external clients.

## Why Use It?

Without this package, a user needs to maintain robot-specific `domain_bridge` YAML files, namespace remaps, reverse goal bridges, map QoS, rosbridge launch files, and UI topic lists by hand.

With this package, the user describes the fleet once:

```yaml
robots:
  - id: robot1
    namespace: /robot1
    domain_id: 1
  - id: robot2
    namespace: /robot2
    domain_id: 2
```

Then the gateway creates the robot-specific bridge mappings and exposes normalized fleet topics.

## Architecture

```text
Robot PC / Domain 1         Control Tower / Domain 0
  /odometry  ----------->     /robot1/odometry
  /map       ----------->     /robot1/map
  /plan      ----------->     /robot1/plan
  /goal_pose <-----------     /robot1/goal_pose

Robot PC / Domain 2         Control Tower / Domain 0
  /odometry  ----------->     /robot2/odometry
  /goal_pose <-----------     /robot2/goal_pose

Control Tower clients
  /fleet/robot_states
  /fleet/goal_command
  /fleet/goal_events
  /fleet/bridge_health
```

## Features

- YAML-based robot/domain/namespace configuration
- `domain_bridge` YAML generation from reusable topic profiles
- Control-tower launch file for `rosapi`, `rosbridge_websocket`, generated bridges, and gateway nodes
- Fleet state aggregation on `/fleet/robot_states`
- Goal routing from `/fleet/goal_command` to `/robotN/goal_pose`
- Topic freshness monitoring on `/fleet/bridge_health`
- Minimal and full navigation bridge profiles

## Nodes

| Executable | Purpose |
|------------|---------|
| `fleet_state_aggregator` | Aggregates robot pose/state into `/fleet/robot_states`. |
| `goal_router` | Routes JSON goal commands to robot-specific `goal_pose` topics. |
| `bridge_health_monitor` | Publishes topic freshness and bridge health summaries. |
| `generate_bridge_configs` | Generates `domain_bridge` YAML files from fleet/profile configs. |

## Fleet Topics

| Topic | Type | Direction |
|-------|------|-----------|
| `/fleet/robot_states` | `std_msgs/msg/String` JSON | Gateway to clients |
| `/fleet/goal_command` | `std_msgs/msg/String` JSON | Client to gateway |
| `/fleet/goal_events` | `std_msgs/msg/String` JSON | Gateway to clients |
| `/fleet/bridge_health` | `std_msgs/msg/String` JSON | Gateway to clients |

Goal command example:

```json
{"robot_id":"robot1","x":1.0,"y":2.0,"yaw":0.0}
```

The router publishes the corresponding `geometry_msgs/msg/PoseStamped` to `/robot1/goal_pose`.

## Install From Source

```bash
mkdir -p ~/fleet_ws/src
cd ~/fleet_ws/src
git clone https://github.com/gukdoli/domain_fleet_gateway.git
cd ~/fleet_ws
source /opt/ros/humble/setup.bash
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install
source install/setup.bash
```

## Launch

Run this on the control-tower PC:

```bash
export ROS_DOMAIN_ID=0
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
ros2 launch domain_fleet_gateway fleet_gateway.launch.py
```

By default this launch starts:

- `rosapi`
- `rosbridge_websocket`
- generated `domain_bridge` nodes for Robot 1/2/3
- `fleet_state_aggregator`
- `goal_router`
- `bridge_health_monitor`

To start only the gateway nodes without rosbridge or domain_bridge:

```bash
ros2 launch domain_fleet_gateway fleet_gateway.launch.py \
  enable_rosapi:=false \
  enable_rosbridge:=false \
  enable_domain_bridge:=false
```

## Configuration

Edit [config/fleet.yaml](config/fleet.yaml) to change robots, namespaces, domain IDs, and monitored health topics.

Edit [config/topic_profiles.yaml](config/topic_profiles.yaml) to switch between `navigation_minimal` and `navigation_full` bridge policies.

Generate bridge configs without launching:

```bash
ros2 run domain_fleet_gateway generate_bridge_configs \
  --fleet-config src/domain_fleet_gateway/config/fleet.yaml \
  --topic-profiles src/domain_fleet_gateway/config/topic_profiles.yaml \
  --output-dir /tmp/domain_fleet_gateway
```

## Assumptions

The default topic profiles assume each robot domain exposes un-namespaced internal topics such as:

- `/odometry`
- `/map`
- `/plan`
- `/goal_pose`
- `/initialpose`
- `/cmd_vel`

The control tower maps those into namespaced topics such as `/robot1/odometry`.

If your robot already publishes namespaced internal topics, create a custom topic profile.

## Development

```bash
cd ~/fleet_ws
colcon build --symlink-install --packages-select domain_fleet_gateway
colcon test --packages-select domain_fleet_gateway
colcon test-result --verbose
```

## License

Apache-2.0
