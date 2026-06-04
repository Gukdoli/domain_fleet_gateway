from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
import os

from domain_fleet_gateway.bridge_config import generate_bridge_configs


def _as_bool(value):
    return str(value).lower() in ('1', 'true', 'yes', 'on')


def _launch_setup(context, *args, **kwargs):
    package_share = get_package_share_directory('domain_fleet_gateway')
    default_fleet_config = os.path.join(package_share, 'config', 'fleet.yaml')
    default_topic_profiles = os.path.join(package_share, 'config', 'topic_profiles.yaml')

    fleet_config = LaunchConfiguration('fleet_config').perform(context) or default_fleet_config
    topic_profiles = (
        LaunchConfiguration('topic_profiles').perform(context) or default_topic_profiles
    )
    bridge_output_dir = LaunchConfiguration('bridge_output_dir').perform(context)
    rosbridge_port = int(LaunchConfiguration('rosbridge_port').perform(context))

    enable_rosapi = _as_bool(LaunchConfiguration('enable_rosapi').perform(context))
    enable_rosbridge = _as_bool(LaunchConfiguration('enable_rosbridge').perform(context))
    enable_domain_bridge = _as_bool(
        LaunchConfiguration('enable_domain_bridge').perform(context)
    )
    enable_gateway_nodes = _as_bool(
        LaunchConfiguration('enable_gateway_nodes').perform(context)
    )

    actions = []

    if enable_rosapi:
        actions.append(Node(
            package='rosapi',
            executable='rosapi_node',
            name='rosapi',
            output='screen',
        ))

    if enable_rosbridge:
        actions.append(Node(
            package='rosbridge_server',
            executable='rosbridge_websocket',
            name='rosbridge_websocket',
            parameters=[{'port': rosbridge_port}],
            output='screen',
        ))

    if enable_domain_bridge:
        generated = generate_bridge_configs(
            fleet_config_path=fleet_config,
            topic_profiles_path=topic_profiles,
            output_dir=bridge_output_dir,
        )
        for item in generated:
            actions.append(Node(
                package='domain_bridge',
                executable='domain_bridge',
                name=f"domain_bridge_{item['robot_id']}",
                arguments=[item['path']],
                output='screen',
            ))

    if enable_gateway_nodes:
        common_params = [{'fleet_config': fleet_config}]
        actions.extend([
            Node(
                package='domain_fleet_gateway',
                executable='fleet_state_aggregator',
                name='fleet_state_aggregator',
                parameters=common_params,
                output='screen',
            ),
            Node(
                package='domain_fleet_gateway',
                executable='goal_router',
                name='goal_router',
                parameters=common_params,
                output='screen',
            ),
            Node(
                package='domain_fleet_gateway',
                executable='bridge_health_monitor',
                name='bridge_health_monitor',
                parameters=common_params,
                output='screen',
            ),
        ])

    return actions


def generate_launch_description():
    package_share = get_package_share_directory('domain_fleet_gateway')

    return LaunchDescription([
        DeclareLaunchArgument(
            'fleet_config',
            default_value=os.path.join(package_share, 'config', 'fleet.yaml'),
            description='Fleet configuration YAML.',
        ),
        DeclareLaunchArgument(
            'topic_profiles',
            default_value=os.path.join(package_share, 'config', 'topic_profiles.yaml'),
            description='Bridge topic profile YAML.',
        ),
        DeclareLaunchArgument(
            'bridge_output_dir',
            default_value='/tmp/domain_fleet_gateway',
            description='Directory for generated domain_bridge YAML files.',
        ),
        DeclareLaunchArgument(
            'rosbridge_port',
            default_value='9090',
            description='rosbridge_websocket port.',
        ),
        DeclareLaunchArgument(
            'enable_rosapi',
            default_value='true',
            description='Start rosapi.',
        ),
        DeclareLaunchArgument(
            'enable_rosbridge',
            default_value='true',
            description='Start rosbridge_websocket.',
        ),
        DeclareLaunchArgument(
            'enable_domain_bridge',
            default_value='true',
            description='Generate and start domain_bridge nodes.',
        ),
        DeclareLaunchArgument(
            'enable_gateway_nodes',
            default_value='true',
            description='Start fleet state, goal router, and health nodes.',
        ),
        OpaqueFunction(function=_launch_setup),
    ])
