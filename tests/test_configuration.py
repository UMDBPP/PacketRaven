from typing import Any

from packetraven.configuration.base import ConfigurationYAML
from packetraven.configuration.credentials import CredentialsYAML
# noinspection PyUnresolvedReferences
from tests import OUTPUT_DIRECTORY, REFERENCE_DIRECTORY, check_reference_directory, credentials


class TestConfiguration(ConfigurationYAML):
    fields = {
        'test1': int,
        'test2': str,
        'test3': [bool],
        'test4': {str: Any},
        'test5': int,
    }


def test_configuration():
    output_directory = OUTPUT_DIRECTORY / 'test_configuration'
    reference_directory = REFERENCE_DIRECTORY / 'test_configuration'

    if not output_directory.exists():
        output_directory.mkdir(parents=True, exist_ok=True)

    configuration = TestConfiguration(test1=1, test2='a', test3=[True, False, True], test4={'a': 2, 'b': 'test value', 'test5': '2'})
    configuration.to_file(output_directory / 'testconfiguration.yaml')

    check_reference_directory(output_directory, reference_directory)


def test_credentials_configuration():
    output_directory = OUTPUT_DIRECTORY / 'test_credentials_configuration'
    reference_directory = REFERENCE_DIRECTORY / 'test_credentials_configuration'

    if not output_directory.exists():
        output_directory.mkdir(parents=True, exist_ok=True)

    configuration = CredentialsYAML()
    configuration.to_file(output_directory / 'credentials.yaml')

    check_reference_directory(output_directory, reference_directory)
