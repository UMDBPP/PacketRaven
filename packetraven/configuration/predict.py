from datetime import datetime
from os import PathLike
from pathlib import Path
from typing import List, Mapping

from shapely.geometry import Point
import typepigeon
import yaml

from packetraven.configuration.base import ConfigurationYAML


class PredictionConfiguration(ConfigurationYAML):
    fields = {
        'api_url': str,
        'launch_site': Point,
        'launch_time': datetime,
        'ascent_rate': float,
        'burst_altitude': float,
        'sea_level_descent_rate': float,
        'float_altitude': float,
        'float_end_time': datetime,
        'name': str,
        'descent_only': bool,
    }
    defaults = {
        'api_url': 'https://predict.cusf.co.uk/api/v1/',
        'descent_only': False,
    }


class PredictionCloudConfiguration(ConfigurationYAML):
    fields = {'default': PredictionConfiguration, 'perturbations': [PredictionConfiguration]}

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
            configuration = self.configuration

            default = configuration['default']
            for perturbation in configuration['perturbations'].values():
                for key in list(perturbation):
                    if key in default and perturbation[key] == default[key]:
                        del perturbation[key]

            content = typepigeon.convert_to_json(configuration)
            with open(filename, 'w') as input_file:
                yaml.safe_dump(content, input_file)
