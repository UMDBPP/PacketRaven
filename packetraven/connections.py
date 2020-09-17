"""
Read serial connection from radio and extract APRS packets.

__authors__ = []
"""

from abc import ABC, abstractmethod
from datetime import datetime
import logging
from os import PathLike
from pathlib import Path
from typing import Any, Union

import requests
from serial import Serial
from serial.tools import list_ports
from shapely.geometry import Point

from packetraven.database import DatabaseTable
from packetraven.packets import APRSLocationPacket, LocationPacket
from packetraven.utilities import CREDENTIALS_FILENAME, get_logger, read_configuration

LOGGER = get_logger('packetraven.connection')


class PacketConnection(ABC):
    location: str

    @property
    @abstractmethod
    def packets(self) -> [APRSLocationPacket]:
        """
        List the most recent packets available from this connection.

        :return: list of APRS packets
        """

        raise NotImplementedError

    @abstractmethod
    def __enter__(self):
        raise NotImplementedError

    @abstractmethod
    def __exit__(self, exc_type, exc_val, exc_tb):
        raise NotImplementedError

    @abstractmethod
    def close(self):
        raise NotImplementedError


class PacketRadio(PacketConnection):
    def __init__(self, serial_port: str = None):
        """
        Connect to radio over given serial port.

        :param serial_port: port name
        """

        if serial_port is None:
            try:
                self.location = next_available_port()
            except ConnectionError:
                raise ConnectionError('could not find radio over serial connection')
        else:
            self.location = serial_port.strip('"')

        self.connection = Serial(self.location, baudrate=9600, timeout=1)

    @property
    def packets(self) -> [APRSLocationPacket]:
        return [parse_packet(line) for line in self.connection.readlines()]

    def __enter__(self):
        return self.connection

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        self.connection.close()

    def __repr__(self):
        return f'{self.__class__.__name__}("{self.location}")'


class PacketTextFile(PacketConnection):
    def __init__(self, filename: PathLike = None):
        """
        Read APRS packets from a given text file.

        :param filename: path to text file, where each line consists of the time sent (`%Y-%m-%d %H:%M:%S`) followed by the raw APRS string
        """

        if not isinstance(filename, Path):
            if isinstance(filename, str):
                filename = filename.strip('"')
            filename = Path(filename)

        self.location = filename

        # open text file
        self.connection = open(self.location)

    @property
    def packets(self) -> [APRSLocationPacket]:
        return [parse_packet(line[25:].strip('\n'), datetime.strptime(line[:19], '%Y-%m-%d %H:%M:%S'))
                for line in self.connection.readlines() if len(line) > 0]

    def __enter__(self):
        return self.connection

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        self.connection.close()

    def __repr__(self):
        return f'{self.__class__.__name__}("{self.location}")'


class APRS_fi(PacketConnection):
    location = 'https://api.aprs.fi/api/get'

    def __init__(self, callsigns: [str], api_key: str = None):
        """
        Connect to https://aprs.fi over given serial port.

        :param callsigns: list of callsigns to watch
        :param api_key: API key for aprs.fi
        """

        if api_key is None or api_key == '':
            configuration = read_configuration(CREDENTIALS_FILENAME)

            if 'APRS_FI' in configuration:
                api_key = configuration['APRS_FI']['api_key']
            else:
                raise ConnectionError(f'no APRS.fi API key specified')

        self.api_key = api_key
        self.callsigns = callsigns

        if not self.has_network_connection():
            raise ConnectionError(f'no network connection')

    @property
    def packets(self) -> [APRSLocationPacket]:
        query = {
            'name'  : ','.join(self.callsigns),
            'what'  : 'loc',
            'apikey': self.api_key,
            'format': 'json'
        }

        query = '&'.join(f'{key}={value}' for key, value in query.items())

        response = requests.get(f'{self.location}?{query}').json()
        if response['result'] != 'fail':
            packets = [parse_packet(packet_candidate) for packet_candidate in response['entries']]
        else:
            logging.warning(f'query failure "{response["code"]}: {response["description"]}"')
            packets = []

        return packets

    def has_network_connection(self) -> bool:
        """
        test network connection

        :return: whether current session has a network connection to APRS API
        """

        try:
            requests.get(self.location, timeout=2)
            return True
        except ConnectionError:
            return False

    def __enter__(self):
        if not self.has_network_connection():
            raise ConnectionError(f'No network connection.')

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def close(self):
        pass

    def __repr__(self):
        callsigns_string = ','.join(f'"{callsign}"' for callsign in self.callsigns)
        return f'{self.__class__.__name__}([{callsigns_string}], r"{self.api_key}")'


class PacketDatabaseTable(PacketConnection, DatabaseTable):
    __default_fields = {
        'time' : datetime,
        'x'    : float,
        'y'    : float,
        'z'    : float,
        'point': Point
    }

    def __init__(self, hostname: str, database: str, table: str, fields: {str: type} = None, **kwargs):
        if fields is None:
            fields = {}
        fields = {**self.__default_fields, **fields}
        super().__init__(hostname, database, table, fields, 'time', **kwargs)
        self.location = f'{self.hostname}:{self.port}/{self.database}/{self.table}'

    @property
    def packets(self) -> [LocationPacket]:
        return [LocationPacket(**{key: value for key, value in record.items() if key != 'point'}) for record in self.records]

    def __getitem__(self, time: datetime) -> LocationPacket:
        record = super().__getitem__(time)
        return LocationPacket(record['time'], record['x'], record['y'], record['z'], record['crs'])

    def __setitem__(self, time: datetime, packet: LocationPacket):
        record = {
            'time' : packet.time,
            'x'    : packet.coordinates[0],
            'y'    : packet.coordinates[1],
            'z'    : packet.coordinates[2],
            'point': Point(*packet.coordinates)
        }
        super().__setitem__(time, record)

    def __enter__(self):
        return self.connection

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        self.connection.close()


class APRSPacketDatabaseTable(PacketDatabaseTable):
    __default_fields = {
        'time'    : datetime,
        'callsign': str,
        'x'       : float,
        'y'       : float,
        'z'       : float,
        'point'   : Point
    }

    def __init__(self, hostname: str, database: str, table: str, fields: {str, type} = None, **kwargs):
        if fields is None:
            fields = {}
        else:
            fields = {f'packet_{field}': field_type for field, field_type in fields.items()}
        fields = {**self.__default_fields, **fields}
        super().__init__(hostname, database, table, fields, **kwargs)

    @property
    def packets(self) -> [APRSLocationPacket]:
        return [APRSLocationPacket(**{field if field in ['time', 'x', 'y', 'z'] else field.replace('packet_', ''): value
                                      for field, value in record.items() if field not in ['point']}) for record in self.records]

    def __getitem__(self, time: datetime) -> APRSLocationPacket:
        packet = super().__getitem__(time)
        return APRSLocationPacket(packet.time, *packet.coordinates, packet.crs)

    def __setitem__(self, time: datetime, packet: APRSLocationPacket):
        record = {
            'time'    : packet.time,
            'callsign': packet.callsign,
            'x'       : packet.coordinates[0],
            'y'       : packet.coordinates[1],
            'z'       : packet.coordinates[2],
            'point'   : Point(*packet.coordinates)
        }
        super(super()).__setitem__(time, record)

    def insert(self, packets: [{str: Any}]):
        records = [{
            'time' : packet.time,
            'x'    : packet.coordinates[0],
            'y'    : packet.coordinates[1],
            'z'    : packet.coordinates[2],
            'point': Point(*packet.coordinates),
            **{f'packet_{field}': value for field, value in packet.parsed_packet.items()}
        } for packet in packets]
        super(self.__class__, self).insert(records)


def available_ports() -> str:
    """
    Iterate over available serial ports.

    :return: port name
    """

    for com_port in list_ports.comports():
        yield com_port.device
    else:
        return None


def next_available_port() -> str:
    """
    Get next port in ports list.

    :return: port name
    """

    try:
        return next(available_ports())
    except StopIteration:
        raise ConnectionError('No open serial ports.')


def parse_packet(raw_packet: Union[str, bytes, dict], packet_time: datetime = None) -> APRSLocationPacket:
    try:
        return APRSLocationPacket.from_raw_aprs(raw_packet, packet_time)
    except Exception as error:
        logging.exception(f'{error.__class__.__name__} - {error} for raw packet "{raw_packet}"')
