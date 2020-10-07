#!/usr/bin/env python
from dunamai import Version
from setuptools import config, find_packages, setup

metadata = config.read_configuration('setup.cfg')['metadata']

setup(
    name=metadata['name'],
    version=Version.from_any_vcs().serialize(),
    author=metadata['author'],
    author_email=metadata['author_email'],
    description=metadata['description'],
    long_description=metadata['long_description'],
    long_description_content_type="text/markdown",
    url=metadata['url'],
    packages=find_packages(),
    python_requires='>=3.6',
    setup_requires=['dunamai', 'setuptools>=41.2', 'wheel'],
    install_requires=[
        'aprslib',
        'haversine',
        'numpy',
        'pyserial',
        'geojson',
        'fastkml',
        'requests',
        'pyproj',
        'psycopg2-binary',
        'shapely',
        'sshtunnel'
    ],
    extras_require={'dev': ['coverage', 'flake8', 'nose']},
    entry_points={'console_scripts': ['packetraven=client.cli:main']},
    test_suite='nose.collector'
)
