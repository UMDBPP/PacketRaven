#!/usr/bin/env python
import importlib
import logging
import os
from pathlib import Path
import subprocess
import sys

from setuptools import config, find_packages, setup

BUILT_PACKAGES = {'numpy': [], 'pandas': ['numpy'], 'pyproj': [], 'shapely': ['gdal']}
is_conda = (Path(sys.prefix) / 'conda-meta').exists()

if is_conda:
    conda_packages = []
    for conda_package in BUILT_PACKAGES:
        try:
            importlib.import_module(conda_package)
        except:
            conda_packages.append(conda_package)
    if len(conda_packages) > 0:
        subprocess.check_call(['conda', 'install', '-y', *conda_packages])

if os.name == 'nt':
    packages_to_install = {}
    for required_package, pipwin_dependencies in BUILT_PACKAGES.items():
        try:
            importlib.import_module(required_package)
        except:
            packages_to_install[required_package] = pipwin_dependencies
    if len(packages_to_install) > 0:
        try:
            import pipwin
        except:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pipwin'])
            subprocess.check_call([sys.executable, '-m', 'pipwin', 'refresh'])

    for required_package, pipwin_dependencies in packages_to_install.items():
        failed_pipwin_packages = []
        for _ in range(1 + len(pipwin_dependencies)):
            for pipwin_package in [required_package] + pipwin_dependencies:
                try:
                    importlib.import_module(pipwin_package)
                except:
                    try:
                        subprocess.check_call(
                            [sys.executable, '-m', 'pipwin', 'install', pipwin_package.lower()]
                        )
                        if pipwin_package in failed_pipwin_packages:
                            failed_pipwin_packages.remove(pipwin_package)
                    except subprocess.CalledProcessError:
                        failed_pipwin_packages.append(pipwin_package)

            # since we don't know the dependencies here, repeat this process n number of times (worst case is O(n), when the first package is dependant on all the others)
            if len(failed_pipwin_packages) == 0:
                break

        try:
            importlib.import_module(required_package)
        except:
            raise RuntimeError(
                f'failed to download or install non-conda Windows build(s) of ({", ".join(failed_pipwin_packages)}); you can either\n'
                '1) install within an Anaconda environment, or\n'
                f'2) `pip install <file>.whl`, with `<file>.whl` downloaded from ({", ".join("https://www.lfd.uci.edu/~gohlke/pythonlibs/#" + value.lower() for value in failed_pipwin_packages)}) for your Python version'
            )

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
    install_requires=[
        'aprslib',
        'humanize',
        'numpy',
        'pandas',
        'pyserial',
        'geojson',
        'fastkml',
        'matplotlib',
        'psycopg2-binary',
        'pyproj',
        'requests',
        'shapely',
        'sshtunnel',
        'tablecrow>=1.3.6',
        'teek',
    ],
    extras_require={
        'testing': ['pytest', 'pytest-cov', 'pytest-xdist', 'pytz'],
        'development': ['flake8', 'isort', 'oitnb', 'wheel'],
    },
    entry_points={'console_scripts': ['packetraven=packetraven.__main__:main']},
)
