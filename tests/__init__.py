import os
from os import PathLike
from pathlib import Path
import re
from typing import Any, Dict, List

import pytest

from packetraven.configuration.credentials import CredentialsYAML

DATA_DIRECTORY = Path(__file__).parent / 'data'

REFERENCE_DIRECTORY = DATA_DIRECTORY / 'reference'
OUTPUT_DIRECTORY = DATA_DIRECTORY / 'output'


@pytest.fixture
def credentials() -> Dict[str, Any]:
    return CredentialsYAML.from_file(DATA_DIRECTORY.parent.parent / 'credentials.yaml')


def check_reference_directory(
    test_directory: PathLike,
    reference_directory: PathLike,
    skip_lines: Dict[str, List[int]] = None,
):
    if not isinstance(test_directory, Path):
        test_directory = Path(test_directory)
    if not isinstance(reference_directory, Path):
        reference_directory = Path(reference_directory)
    if skip_lines is None:
        skip_lines = {}

    for reference_filename in reference_directory.iterdir():
        if reference_filename.is_dir():
            check_reference_directory(
                test_directory / reference_filename.name, reference_filename, skip_lines
            )
        else:
            test_filename = test_directory / reference_filename.name

            if reference_filename.suffix in ['.h5', '.nc']:
                reference_filesize = Path(reference_filename).stat().st_size
                test_filesize = Path(test_filename).stat().st_size

                diff = test_filesize - reference_filesize
                message = f'"{test_filesize}" != "{reference_filesize}"\n{diff}'

                assert reference_filesize == test_filesize, message
                continue

            with open(test_filename) as test_file, open(reference_filename) as reference_file:
                test_lines = list(test_file.readlines())
                reference_lines = list(reference_file.readlines())

                lines_to_skip = set()
                for file_mask, line_indices in skip_lines.items():
                    if (
                        file_mask in str(test_filename)
                        or re.match(file_mask, str(test_filename))
                        and len(test_lines) > 0
                    ):
                        try:
                            lines_to_skip.update(
                                line_index % len(test_lines) for line_index in line_indices
                            )
                        except ZeroDivisionError:
                            continue

                for line_index in sorted(lines_to_skip, reverse=True):
                    del test_lines[line_index], reference_lines[line_index]

                cwd = Path.cwd()
                assert '\n'.join(test_lines) == '\n'.join(
                    reference_lines
                ), f'"{os.path.relpath(test_filename, cwd)}" != "{os.path.relpath(reference_filename, cwd)}"'
