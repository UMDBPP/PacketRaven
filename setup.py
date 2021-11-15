#!/usr/bin/env python
import logging
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Dict, List, Mapping

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


def installed_packages() -> List[str]:
    return [
        re.split('#egg=', re.split('==| @ ', package.decode())[0])[-1].lower()
        for package in subprocess.run(
            f'{sys.executable} -m pip freeze', shell=True, capture_output=True,
        ).stdout.splitlines()
    ]


def missing_packages(required_packages: Dict[str, List[str]]) -> Dict[str, List[str]]:
    if isinstance(required_packages, Mapping):
        missing_dependencies = missing_packages(list(required_packages))
        output = {}
        for dependency, subdependencies in required_packages.items():
            missing_subdependencies = missing_packages(subdependencies)
            if dependency in missing_dependencies or len(missing_subdependencies) > 0:
                output[dependency] = missing_subdependencies
        return output
    else:
        return [
            required_package
            for required_package in required_packages
            if re.split('<|<=|==|>=|>', required_package)[0].lower()
               not in installed_packages()
        ]


try:
    if 'dunamai' not in installed_packages():
        subprocess.run(
            f'{sys.executable} -m pip install dunamai',
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    from dunamai import Version

    version = Version.from_any_vcs().serialize()
except RuntimeError as error:
    logging.exception(error)
    version = '0.0.0'

logging.info(f'using version {version}')

MISSING_DEPENDENCIES = missing_packages(DEPENDENCIES)

if (Path(sys.prefix) / 'conda-meta').exists() and len(MISSING_DEPENDENCIES) > 0:
    conda_packages = []
    for dependency in list(MISSING_DEPENDENCIES):
        try:
            process = subprocess.run(
                f'conda search {dependency}', check=True, shell=True, capture_output=True,
            )
            if 'No match found for:' not in process.stdout.decode():
                conda_packages.append(dependency)
        except subprocess.CalledProcessError:
            continue

    try:
        subprocess.run(
            f'conda install -y {" ".join(conda_packages)}',
            check=True,
            shell=True,
            stderr=subprocess.DEVNULL,
        )
    except subprocess.CalledProcessError:
        for dependency in conda_packages:
            try:
                subprocess.run(
                    f'conda install -y {dependency}',
                    check=True,
                    shell=True,
                    stderr=subprocess.DEVNULL,
                )
            except subprocess.CalledProcessError:
                continue

    MISSING_DEPENDENCIES = missing_packages(DEPENDENCIES)

if os.name == 'nt' and len(MISSING_DEPENDENCIES) > 0:
    if 'pipwin' not in installed_packages():
        subprocess.run(
            f'{sys.executable} -m pip install pipwin',
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    subprocess.run(f'{sys.executable} -m pipwin refresh', shell=True)

    for dependency, subdependencies in MISSING_DEPENDENCIES.items():
        failed_pipwin_packages = []
        for _ in range(1 + len(subdependencies)):
            for package_name in subdependencies + [dependency]:
                if dependency in missing_packages(
                    DEPENDENCIES
                ) or package_name in missing_packages(subdependencies):
                    try:
                        subprocess.run(
                            f'{sys.executable} -m pip install {package_name.lower()}',
                            check=True,
                            shell=True,
                            stderr=subprocess.DEVNULL,
                        )
                        if package_name in failed_pipwin_packages:
                            failed_pipwin_packages.remove(package_name)
                    except subprocess.CalledProcessError:
                        try:
                            subprocess.run(
                                f'{sys.executable} -m pipwin install {package_name.lower()}',
                                check=True,
                                shell=True,
                                stderr=subprocess.DEVNULL,
                            )
                        except subprocess.CalledProcessError:
                            failed_pipwin_packages.append(package_name)

            # since we don't know the dependencies here, repeat this process n number of times
            # (worst case is `O(n)`, where the first package is dependant on all the others)
            if len(failed_pipwin_packages) == 0:
                break

    MISSING_DEPENDENCIES = missing_packages(DEPENDENCIES)

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
        'development': ['dunamai', 'flake8', 'isort', 'oitnb', 'wheel'],
        'documentation': ['dunamai', 'm2r2', 'sphinx-rtd-theme'],
    },
    entry_points={'console_scripts': ['packetraven=packetraven.__main__:main']},
)
