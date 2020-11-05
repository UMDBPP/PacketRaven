#!/usr/bin/env python
from setuptools import config, find_packages, setup

try:
    from dunamai import Version
except ImportError:
    import sys
    import subprocess

    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'dunamai'])
    from dunamai import Version

try:
    import pyproj
except ImportError:
    import platform

    if platform.system() == 'Windows':
        import subprocess

        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pipwin'])
        subprocess.check_call([sys.executable, '-m', 'pipwin', 'install', 'pyproj'])

metadata = config.read_configuration('setup.cfg')['metadata']

setup(
    name=metadata['name'],
    version=Version.from_any_vcs().serialize(),
    author=metadata['author'],
    author_email=metadata['author_email'],
    description=metadata['description'],
    long_description=metadata['long_description'],
    long_description_content_type='text/markdown',
    url=metadata['url'],
    packages=find_packages(),
    python_requires='>=3.8',
    setup_requires=['dunamai', 'setuptools>=41.2'],
    install_requires=[
        'aprslib',
        'haversine',
        'numpy==1.19.3',
        'pyserial',
        'geojson',
        'fastkml',
        'requests',
        'pyproj',
        'psycopg2-binary',
        'shapely',
        'sshtunnel',
        'tablecrow',
    ],
    extras_require={'testing': ['flake8', 'pytest', 'pytest-cov'], 'development': ['oitnb']},
    entry_points={'console_scripts': ['packetraven=client.cli:main']},
)
