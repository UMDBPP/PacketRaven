from pathlib import Path
from typing import List, Union
import warnings

from packetraven import RawAPRSTextFile, SerialTNC
from packetraven.configuration.base import (
    ConfigurationSection,
    ConfigurationYAML,
    PacketSourceConfiguration,
)
from packetraven.connections import PacketGeoJSON


class TextStreamConfiguration(ConfigurationYAML, ConfigurationSection):
    name = 'text'
    fields = {
        'locations': [str],
    }
