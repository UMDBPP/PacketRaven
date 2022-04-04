from abc import ABC, abstractmethod
from copy import deepcopy
from os import PathLike
from pathlib import Path
from typing import Any, Collection, Dict, Generator, Mapping

import typepigeon
import yaml

from packetraven.connections.base import PacketSource


class Configuration(ABC, Mapping):
    fields: Dict[str, type]
    defaults: Dict[str, Any] = None

    def __init__(self, **configuration):
        if not hasattr(self, 'configuration'):
            self.__configuration = {field: None for field in self.fields}
        if len(configuration) > 0:
            self.update(configuration)

        if self.defaults is not None:
            update_none(self.__configuration, self.defaults)

        missing_fields = [field for field in self.fields if field not in self.__configuration]
        if len(missing_fields) > 0:
            raise ValueError(
                f'missing {len(missing_fields)} fields required by "{self.__class__.__name__}" - {list(missing_fields)}'
            )

    @classmethod
    def from_file(cls, filename: PathLike) -> 'Configuration':
        raise NotImplementedError()

    def __copy__(self) -> 'Configuration':
        return self.__class__(**deepcopy(self.__configuration))

    def __contains__(self, key: str) -> bool:
        return key in self.__configuration

    def __getitem__(self, key: str) -> Any:
        return self.__configuration[key]

    def __setitem__(self, key: str, value: Any):
        if key in self.fields:
            field_type = self.fields[key]
            if not isinstance(field_type, type):
                field_type = type(field_type)
            if not isinstance(value, field_type):
                value = typepigeon.convert_value(value, self.fields[key])
        else:
            self.fields[key] = type(value)
        self.__configuration[key] = value

    def update(self, other: Mapping):
        for key, value in other.items():
            if key in self:
                if isinstance(self[key], Configuration):
                    self[key].update(value)
                else:
                    field_type = self.fields[key]
                    if (
                        isinstance(field_type, type)
                        and issubclass(field_type, Configuration)
                        and value is not None
                    ):
                        converted_value = field_type(**value)
                    elif isinstance(field_type, Mapping) and value is not None:
                        converted_value = convert_key_pairs(value, field_type)
                    else:
                        converted_value = typepigeon.convert_value(value, field_type)
                    if self[key] is None or self[key] != converted_value:
                        value = converted_value
            self[key] = value

    def __eq__(self, other: 'Configuration') -> bool:
        return other.__configuration == self.__configuration

    def __repr__(self):
        configuration = ', '.join(
            [f'{key}={repr(value)}' for key, value in self.__configuration.items()]
        )
        return f'{self.__class__.__name__}({configuration})'

    def __len__(self) -> int:
        return len(self.__configuration)

    def __iter__(self) -> Generator:
        yield from self.__configuration

    def __delitem__(self, key):
        del self.__configuration[key]

    @abstractmethod
    def to_file(self, filename: PathLike = None, overwrite: bool = False):
        raise NotImplementedError()


class ConfigurationSection:
    name: str


class ConfigurationYAML(Configuration):
    @classmethod
    def from_file(cls, filename: PathLike) -> 'Configuration':
        with open(filename) as input_file:
            configuration = yaml.safe_load(input_file)
        return cls(**configuration)

    def to_file(self, filename: PathLike = None, overwrite: bool = True):
        if not isinstance(filename, Path):
            filename = Path(filename)
        if overwrite or not filename.exists():
            content = typepigeon.convert_to_json(self._Configuration__configuration)
            with open(filename, 'w') as input_file:
                yaml.safe_dump(content, input_file)


class PacketSourceConfiguration(ABC):
    def packet_source(self, callsigns: [str] = None) -> PacketSource:
        raise NotImplementedError()


def convert_key_pairs(value_mapping: Mapping, type_mapping: Mapping[str, type]) -> Mapping:
    value_mapping = dict(**value_mapping)
    keys = list(value_mapping)
    for key in keys:
        if key in type_mapping:
            value = value_mapping[key]
            value_type = type_mapping[key]
            if not isinstance(value_type, (Collection)) and issubclass(
                value_type, Configuration
            ):
                value = value_type(**value)
            elif isinstance(value, dict):
                value = convert_key_pairs(value, value_type)
            else:
                value = typepigeon.convert_value(value, value_type)
        else:
            value = typepigeon.convert_value(value_mapping, type_mapping)
        value_mapping[key] = value
    return value_mapping


def update_none(values: Dict[str, Any], defaults: Dict[str, Any]):
    for key, default_value in defaults.items():
        if key not in values or values[key] is None:
            values[key] = default_value
        elif isinstance(values[key], Mapping):
            update_none(values[key], default_value)
