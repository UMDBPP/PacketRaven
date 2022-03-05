from abc import ABC, abstractmethod
from os import PathLike
from pathlib import Path
import sys
from typing import Any, Dict, List

from typepigeon import convert_value

from packetraven.packets.tracks import PredictedTrajectory
from packetraven.utilities import get_logger

LOGGER = get_logger('packetraven', log_format='%(asctime)s | %(levelname)-8s | %(message)s')




class ConfigurationFile(ABC):
    @abstractmethod
    def __str__(self) -> str:
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def from_file(cls) -> 'ConfigurationFile':
        pass

    def to_file(self, filename: PathLike, overwrite: bool = False):
        if not isinstance(filename, Path):
            filename = Path(filename)
        if not filename.parent.exists():
            filename.parent.mkdir(exist_ok=True, parents=True)

        if not filename.exists() or overwrite:
            with open(filename, 'w', newline='\n') as output_file:
                output_file.write(str(self))


class RunConfiguration:
    def __init__(
        self,

    ):
        pass

    def __str__(self) -> str:
        raise NotImplementedError


class PredictionCloud:
    def __init__(self, predictions: List[PredictedTrajectory]):
        self.__predictions = predictions

    @property
    def predictions(self) -> List[PredictedTrajectory]:
        return self.__predictions

    def __str__(self) -> str:
        raise NotImplementedError
