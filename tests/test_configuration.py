from typing import Any

from packetraven.configuration.base import ConfigurationYAML
from packetraven.configuration.credentials import CredentialsYAML

# noinspection PyUnresolvedReferences
from packetraven.configuration.predict import (
    PredictionCloudConfiguration,
    PredictionConfiguration,
)
from tests import check_reference_directory, OUTPUT_DIRECTORY, REFERENCE_DIRECTORY


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

    configuration = TestConfiguration(
        test1=1,
        test2='a',
        test3=[True, False, True],
        test4={'a': 2, 'b': 'test value', 'test5': '2'},
    )
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


def test_prediction_configuration():
    output_directory = OUTPUT_DIRECTORY / 'test_prediction_configuration'
    reference_directory = REFERENCE_DIRECTORY / 'test_prediction_configuration'

    if not output_directory.exists():
        output_directory.mkdir(parents=True, exist_ok=True)

    configuration = PredictionConfiguration(
        launch_site=(-78.4987, 40.0157),
        launch_time='2022-03-05 10:36:00',
        ascent_rate=6.5,
        burst_altitude=25000,
        descent_rate=9,
    )

    configuration.to_file(output_directory / 'prediction.yaml')

    check_reference_directory(output_directory, reference_directory)


def test_prediction_cloud_configuration():
    output_directory = OUTPUT_DIRECTORY / 'test_prediction_cloud_configuration'
    reference_directory = REFERENCE_DIRECTORY / 'test_prediction_cloud_configuration'

    if not output_directory.exists():
        output_directory.mkdir(parents=True, exist_ok=True)

    configuration = PredictionConfiguration(
        launch_site=(-78.4987, 40.0157),
        launch_time='2022-03-05 10:36:00',
        ascent_rate=6.5,
        burst_altitude=25000,
        descent_rate=9,
    )

    perturbations = [
        PredictionConfiguration(
            launch_site=(-78.4987, 40.0157),
            launch_time='2022-03-05 10:36:00',
            ascent_rate=6.5,
            burst_altitude=burst_altitude,
            descent_rate=9,
        )
        for burst_altitude in [20000, 22000, 24000, 26000, 28000, 30000]
    ]

    cloud_configuration = PredictionCloudConfiguration(
        default=configuration, perturbations=perturbations
    )
    cloud_configuration.to_file(output_directory / 'prediction_cloud.yaml')

    check_reference_directory(output_directory, reference_directory)
