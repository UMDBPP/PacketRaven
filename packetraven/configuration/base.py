from abc import ABC, abstractmethod
from os import PathLike
from pathlib import Path
from typing import Any, Dict

import typepigeon
import yaml


class Configuration(ABC):
    fields: Dict[str, type]
    defaults: Dict[str, Any] = None

    def __init__(self, **configuration):
        if not hasattr(self, 'configuration'):
            self.configuration = {field: None for field in self.fields}
        if len(configuration) > 0:
            self.configuration.update(configuration)

        if self.defaults is not None:
            for key, value in self.defaults.items():
                if key not in self.configuration:
                    self.configuration[key] = value

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
            if not isinstance(value, field_type):
                value = typepigeon.convert_value(value, self.fields[key])
        else:
            self.fields[key] = type(value)
        self.configuration[key] = value

    def update(self, configuration: Dict[str, Any]):
        for key, value in configuration.items():
            if key in self:
                converted_value = typepigeon.convert_value(value, self.fields[key])
                if self[key] != converted_value:
                    value = converted_value
                else:
                    return
            self[key] = value

    def __eq__(self, other: 'Configuration') -> bool:
        return other.configuration == self.configuration

    def __repr__(self):
        configuration = ', '.join(
            [f'{key}={repr(value)}' for key, value in self.configuration.items()]
        )
        return f'{self.__class__.__name__}({configuration})'

    @abstractmethod
    def to_file(self, filename: PathLike = None, overwrite: bool = False):
        raise NotImplementedError()


class ConfigurationSection:
    name: str


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
            content = typepigeon.convert_to_json(self.configuration)
            with open(filename, 'w') as input_file:
                yaml.safe_dump(content, input_file)
