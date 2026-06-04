from glob import glob
import os

from setuptools import find_packages, setup


package_name = 'domain_fleet_gateway'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
         ['resource/' + package_name]),
        ('share/' + package_name, [
            'package.xml',
            'README.md',
            'LICENSE',
            'CHANGELOG.rst',
        ]),
        (os.path.join('share', package_name, 'launch'),
         glob(os.path.join('launch', '*.launch.py'))),
        (os.path.join('share', package_name, 'config'),
         glob(os.path.join('config', '*.yaml'))),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='region',
    maintainer_email='region@todo.todo',
    url='https://github.com/gukdoli/domain_fleet_gateway',
    description='Fleet gateway for ROS 2 domain-isolated multi-robot systems.',
    license='Apache-2.0',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'fleet_state_aggregator = domain_fleet_gateway.fleet_state_aggregator:main',
            'goal_router = domain_fleet_gateway.goal_router:main',
            'bridge_health_monitor = domain_fleet_gateway.bridge_health_monitor:main',
            'generate_bridge_configs = domain_fleet_gateway.generate_bridge_configs:main',
        ],
    },
)
