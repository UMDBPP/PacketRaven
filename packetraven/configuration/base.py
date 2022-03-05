from abc import ABC, abstractmethod
from os import PathLike
from pathlib import Path
from typing import Any, Dict

from typepigeon import convert_value
import yaml


class Configuration(ABC):
    field_types: Dict[str, type]

    def __init__(self, fields: Dict[str, type] = None, **configuration):
        self.field_types = {key.lower(): value for key, value in self.field_types.items()}

        if not hasattr(self, 'fields'):
            self.fields = {}

        self.fields.update({key: None for key in self.field_types if key not in self.fields})

        if fields is not None:
            fields = {key.lower(): value for key, value in fields.items()}
            self.fields.update(fields)

        if not hasattr(self, 'configuration'):
            self.configuration = {field: None for field in self.fields}

        if len(configuration) > 0:
            self.configuration.update(configuration)

    @classmethod
    @abstractmethod
    def from_string(cls, string: str) -> 'Configuration':
        raise NotImplementedError()

    @classmethod
    def from_file(cls, filename: PathLike) -> 'Configuration':
        raise NotImplementedError()

    def __copy__(self) -> 'Configuration':
        return self.__class__(**self.configuration)

    def __contains__(self, key: str) -> bool:
        return key in self.configuration

    def __getitem__(self, key: str) -> Any:
        return self.configuration[key]

    def __setitem__(self, key: str, value: Any):
        if key in self.fields:
            field_type = self.fields[key]
        else:
            field_type = type(value)
        self.configuration[key] = convert_value(value, field_type)
        if key not in self.fields:
            self.fields[key] = field_type

    def update(self, configuration: Dict[str, Any]):
        for key, value in configuration.items():
            if key in self:
                converted_value = convert_value(value, self.fields[key])
                if self[key] != converted_value:
                    value = converted_value
                else:
                    return
            self[key] = value

    def __eq__(self, other: 'Configuration') -> bool:
        return other.configuration == self.configuration

    def __repr__(self):
        configuration_string = ', '.join(
            [f'{key}={repr(value)}' for key, value in self.configuration.items()]
        )
        return f'{self.__class__.__name__}({configuration_string})'

    @abstractmethod
    def to_file(self, filename: PathLike = None, overwrite: bool = False):
        raise NotImplementedError()


class ConfigurationYAML(Configuration):
    @classmethod
    def from_string(cls, string: str) -> 'Configuration':
        configuration = yaml.safe_load(string)
        return cls(**configuration)

    @classmethod
    def from_file(cls, filename: PathLike) -> 'Configuration':
        with open(filename) as input_file:
            configuration = yaml.safe_load(input_file)
        return cls(**configuration)

    def to_file(self, filename: PathLike = None, overwrite: bool = True):
        if not isinstance(filename, Path):
            filename = Path(filename)
        if overwrite or not filename.exists():
            with open(filename) as input_file:
                yaml.safe_dump(self.configuration, input_file)
