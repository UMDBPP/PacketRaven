#!/usr/bin/env python
import importlib
import logging
import os
from pathlib import Path
import re
import subprocess
import sys

from setuptools import config, find_packages, setup

DEPENDENCIES = {
    'aprslib': [],
    'humanize': [],
    'numpy': [],
    'pandas': ['numpy'],
    'pyserial': [],
    'geojson': [],
    'fastkml': [],
    'matplotlib': [],
    'psycopg2-binary': [],
    'pyproj': [],
    'requests': [],
    'shapely': [],
    'sshtunnel': [],
    'tablecrow>=1.3.9': [],
    'teek': [],
}

installed_packages = [
    re.split('#egg=', re.split('==| @ ', package.decode())[0])[-1].lower()
    for package in subprocess.check_output(
        [sys.executable, '-m', 'pip', 'freeze']
    ).splitlines()
]

missing_dependencies = {
    dependency: subdependencies
    for dependency, subdependencies in DEPENDENCIES.items()
    if re.split('<|<=|==|>=|>', dependency)[0].lower() not in installed_packages
}

if (Path(sys.prefix) / 'conda-meta').exists():
    for dependency in list(missing_dependencies):
        try:
            subprocess.check_call(['conda', 'install', '-y', dependency])
            del missing_dependencies[dependency]
        except:
            continue

if os.name == 'nt':
    if len(missing_dependencies) > 0:
        try:
            import pipwin
        except:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pipwin'])
            subprocess.check_call([sys.executable, '-m', 'pipwin', 'refresh'])

    for dependency, subdependencies in list(missing_dependencies.items()):
        failed_pipwin_packages = []
        for _ in range(1 + len(subdependencies)):
            for package_name in [dependency] + subdependencies:
                try:
                    importlib.import_module(package_name)
                except:
                    try:
                        subprocess.check_call(
                            [sys.executable, '-m', 'pipwin', 'install', package_name.lower()]
                        )
                        if package_name in failed_pipwin_packages:
                            failed_pipwin_packages.remove(package_name)
                        if package_name in missing_dependencies:
                            del missing_dependencies[package_name]
                    except subprocess.CalledProcessError:
                        failed_pipwin_packages.append(package_name)

            # since we don't know the dependencies here, repeat this process n number of times
            # (worst case is `O(n)`, where the first package is dependant on all the others)
            if len(failed_pipwin_packages) == 0:
                break

try:
    try:
        from dunamai import Version
    except ImportError:
        import subprocess
        import sys

        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'dunamai'])
        from dunamai import Version

    version = Version.from_any_vcs().serialize()
except RuntimeError as error:
    logging.exception(error)
    version = '0.0.0'

metadata = config.read_configuration('setup.cfg')['metadata']

setup(
    name=metadata['name'],
    version=version,
    author=metadata['author'],
    author_email=metadata['author_email'],
    description=metadata['description'],
    long_description=metadata['long_description'],
    long_description_content_type='text/markdown',
    url=metadata['url'],
    packages=find_packages(),
    python_requires='>=3.8',
    setup_requires=['dunamai', 'setuptools>=41.2'],
    install_requires=list(DEPENDENCIES),
    extras_require={
        'testing': ['pytest', 'pytest-cov', 'pytest-xdist', 'pytz'],
        'development': ['flake8', 'isort', 'oitnb', 'wheel'],
    },
    entry_points={'console_scripts': ['packetraven=packetraven.__main__:main']},
)
