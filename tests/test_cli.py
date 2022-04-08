import os
from os import PathLike
from pathlib import Path
import re
from tempfile import NamedTemporaryFile

import pytest

from packetraven.__main__ import packetraven_command
from tests import INPUT_DIRECTORY


def insert_environment_variables(filename: PathLike) -> str:
    if not isinstance(filename, Path):
        filename = Path(filename)
    with open(filename) as input_file:
        content = input_file.read()

    pattern = re.compile(r'\${{(.*?)}}')

    for match in re.findall(pattern, content):
        value = os.environ.get(match.strip())
        if value is not None:
            content = content.replace(f'${{{{{match}}}}}', value)

    temporary = NamedTemporaryFile(suffix='.yaml', delete=False)
    with open(temporary.name, 'w') as output_file:
        output_file.write(content)

    return temporary.name


def test_example_1():
    filename = INPUT_DIRECTORY / 'test_cli' / 'example_1.yaml'

    packetraven_command(filename)


@pytest.mark.skipif(
    'APRS_FI_API_KEY' not in os.environ, reason='environment variables not set'
)
def test_example_2():
    filename = INPUT_DIRECTORY / 'test_cli' / 'example_2.yaml'
    filename = insert_environment_variables(filename)

    packetraven_command(filename)
