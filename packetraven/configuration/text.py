
from packetraven.configuration.base import (
    ConfigurationSection,
    ConfigurationYAML,
)


class TextStreamConfiguration(ConfigurationYAML, ConfigurationSection):
    name = "text"
    fields = {
        "locations": [str],
    }
