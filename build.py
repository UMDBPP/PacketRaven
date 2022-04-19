import os
from pathlib import Path
import warnings

DIRECTORY = Path(__file__).parent

try:
    from Cython.Build import cythonize
except ImportError:

    def build(setup_kwargs):
        warnings.warn(f'cython not found - {setup_kwargs}')


else:
    from distutils.command.build_ext import build_ext

    from setuptools import Extension
    from setuptools.dist import Distribution

    def build(setup_kwargs):
        extensions = ['packetraven/__main__.py']

        os.environ['CFLAGS'] = '-O3'

        setup_kwargs.update(
            {
                'ext_modules': cythonize(
                    extensions, language_level=3, compiler_directives={'linetrace': True},
                ),
                'cmdclass': {'build_ext': build_ext},
            }
        )
