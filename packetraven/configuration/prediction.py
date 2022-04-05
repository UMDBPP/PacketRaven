from datetime import datetime, timedelta
from os import PathLike
from pathlib import Path
from typing import Any, Dict, List, Mapping

import typepigeon
import yaml

from packetraven.configuration.base import ConfigurationSection, ConfigurationYAML
from packetraven.model import FREEFALL_DESCENT_RATE
from packetraven.packets.tracks import PredictedTrajectory
from packetraven.predicts import (
    BalloonPredictionQuery,
    DEFAULT_FLOAT_ALTITUDE_UNCERTAINTY,
    PredictionAPIURL,
)


class PredictionConfiguration(ConfigurationYAML, ConfigurationSection):
    name = 'prediction'
    fields = {
        'start': {'location': [float], 'time': datetime},
        'profile': {
            'ascent_rate': float,
            'burst_altitude': float,
            'sea_level_descent_rate': float,
            'descent_only': bool,
        },
        'float': {'altitude': float, 'uncertainty': float, 'duration': timedelta},
        'output': {'filename': Path},
        'api_url': str,
        'name': str,
    }
    defaults = {
        'profile': {
            'sea_level_descent_rate': FREEFALL_DESCENT_RATE(0),
            'descent_only': False,
        },
        'float': {
            'altitude': None,
            'uncertainty': DEFAULT_FLOAT_ALTITUDE_UNCERTAINTY,
            'duration': None,
        },
        'output': {'filename': None},
        'api_url': PredictionAPIURL.cusf.value,
        'name': 'prediction',
    }

    def __init__(self, **configuration):
        super().__init__(**configuration)
        if self['float']['duration'] is not None:
            if self['float']['altitude'] is None:
                self['float']['altitude'] = self['profile']['burst_altitude']
            if self['float']['duration'] is None:
                raise ValueError('`float_duration` was not provided')

    def __setitem__(self, key: str, value: Any):
        super().__setitem__(key, value)

        if key == 'output':
            if self['output'] is not None and self['output']['filename'] is not None:
                output_filename = Path(self['output']['filename']).expanduser()
                if (
                    output_filename.is_dir()
                    or not output_filename.exists()
                    and output_filename.suffix == ''
                ):
                    output_filename /= (
                        f'packetraven_predict_{datetime.now():%Y%m%dT%H%M%S}.geojson'
                    )
                if not output_filename.parent.exists():
                    output_filename.parent.mkdir(parents=True, exist_ok=True)
                self['output']['filename'] = output_filename
        if key == 'start':
            if self['start'] is not None:
                if len(self['start']['location']) == 2:
                    self['start']['location'] = (*self['start']['location'], 0)
        if key in ['start', 'profile']:
            if self['start'] is not None and self['profile'] is not None:
                if self['profile']['burst_altitude'] <= self['start']['location'][2]:
                    self['profile']['burst_altitude'] = self['start']['location'][2] + 1

    @property
    def prediction(self) -> PredictedTrajectory:
        query = BalloonPredictionQuery(
            api_url=self['api_url'],
            start_location=self['start']['location'],
            start_time=self['start']['time'],
            ascent_rate=self['profile']['ascent_rate'],
            burst_altitude=self['profile']['burst_altitude'],
            sea_level_descent_rate=self['profile']['sea_level_descent_rate'],
            float_altitude=self['float']['altitude'],
            float_duration=self['float']['duration'],
            name=self['name'],
            descent_only=self['profile']['descent_only'],
        )
        return query.predict


class PredictionCloudConfiguration(ConfigurationYAML):
    fields = {
        'default': PredictionConfiguration,
        'perturbations': Dict[str, PredictionConfiguration],
    }

    def __init__(
        self,
        default: PredictionConfiguration,
        perturbations: List[PredictionConfiguration],
        **configuration,
    ):
        if not isinstance(perturbations, Mapping):
            perturbations = {
                f'profile_{index + 1}': perturbation
                for index, perturbation in enumerate(
                    typepigeon.convert_value(perturbations, [PredictionConfiguration])
                )
            }

        configuration['default'] = default
        configuration['perturbations'] = perturbations

        super().__init__(**configuration)

    @classmethod
    def from_file(cls, filename: PathLike) -> 'PredictionCloudConfiguration':
        with open(filename) as input_file:
            configuration = yaml.safe_load(input_file)

        default = configuration['default']
        for perturbation, perturbation_values in configuration['perturbations'].items():
            for default_key, default_value in default.items():
                if default_key not in perturbation_values:
                    configuration['perturbations'][perturbation][default_key] = default_value

        return cls(**configuration)

    def to_file(self, filename: PathLike = None, overwrite: bool = True):
        if not isinstance(filename, Path):
            filename = Path(filename)
        if overwrite or not filename.exists():
            configuration = self._Configuration__configuration

            default = configuration['default']
            for perturbation in configuration['perturbations'].values():
                for key in list(perturbation):
                    if key in default and perturbation[key] == default[key]:
                        del perturbation[key]

            content = typepigeon.convert_to_json(configuration)
            with open(filename, 'w') as input_file:
                yaml.safe_dump(content, input_file)
