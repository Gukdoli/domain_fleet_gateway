from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]


def test_public_package_files_exist():
    expected = [
        'README.md',
        'LICENSE',
        'CHANGELOG.rst',
        'package.xml',
        'setup.py',
        'setup.cfg',
        'config/fleet.yaml',
        'config/topic_profiles.yaml',
        'launch/fleet_gateway.launch.py',
    ]

    for relative_path in expected:
        assert (PACKAGE_ROOT / relative_path).exists(), relative_path
