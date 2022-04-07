from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from packetraven.configuration.base import ConfigurationYAML
from packetraven.configuration.credentials import (
    APRSfiCredentials,
    APRSisCredentials,
    DatabaseCredentials,
)
from packetraven.configuration.prediction import PredictionConfiguration
from packetraven.configuration.text import TextStreamConfiguration

DEFAULT_INTERVAL_SECONDS = 20


class RunConfiguration(ConfigurationYAML):
    fields = {
        'callsigns': [str],
        'time': {
            'start': datetime,
            'end': datetime,
            'interval': timedelta,
            'timeout': timedelta,
        },
        'output': {'filename': Path,},
        'log': {'filename': Path,},
        'packets': {
            'aprs_fi': APRSfiCredentials,
            'text': TextStreamConfiguration,
            'database': DatabaseCredentials,
            'aprs_is': APRSisCredentials,
        },
        'prediction': PredictionConfiguration,
        'plots': {'altitude': bool, 'ascent_rate': bool, 'ground_speed': bool,},
    }

    defaults = {
        'callsigns': [],
        'time': {
            'start': None,
            'end': None,
            'interval': timedelta(seconds=DEFAULT_INTERVAL_SECONDS),
        },
        'output': {'filename': None},
        'log': {'filename': None},
        'packets': {},
        'plots': {'altitude': False, 'ascent_rate': False, 'ground_speed': False,},
    }

    def __setitem__(self, key: str, value: Any):
        super().__setitem__(key, value)

        if key == 'callsigns':
            for index, entry in enumerate(self['callsigns']):
                if ',' in entry:
                    del self['callsigns'][index]
                    for callsign in reversed(entry.split(',')):
                        self['callsigns'].insert(index, callsign)

        if key == 'time':
            if (
                'start' in self['time']
                and self['time']['start'] is not None
                and 'start' in self['time']
                and self['time']['end'] is not None
            ):
                if self['time']['start'] > self['time']['end']:
                    temp_start_date = self['time']['start']
                    self['time']['start'] = self['time']['end']
                    self['time']['end'] = temp_start_date
                    del temp_start_date

            if (
                'interval' in self['time']
                and self['time']['interval'] is not None
                and self['time']['interval'] < timedelta(seconds=1)
            ):
                self['time']['interval'] = timedelta(seconds=1)

        if key == 'output':
            output_filename = self['output']['filename']
            if output_filename is not None:
                output_filename = Path(output_filename).expanduser()
                if output_filename.is_dir() or (
                    not output_filename.exists() and output_filename.suffix == ''
                ):
                    output_filename = (
                        output_filename
                        / f'packetraven_output_{datetime.now():%Y%m%dT%H%M%S}.geojson'
                    )
                if not output_filename.parent.exists():
                    output_filename.parent.mkdir(parents=True, exist_ok=True)
                self['output']['filename'] = output_filename

        if key == 'log':
            log_filename = self['log']['filename']
            if log_filename is not None:
                log_filename = Path(log_filename).expanduser()
                if log_filename.is_dir() or (
                    not log_filename.exists() and log_filename.suffix == ''
                ):
                    log_filename = (
                        log_filename / f'packetraven_log_{datetime.now():%Y%m%dT%H%M%S}.txt'
                    )
                if not log_filename.parent.exists():
                    log_filename.parent.mkdir(parents=True, exist_ok=True)
                self['log']['filename'] = log_filename
