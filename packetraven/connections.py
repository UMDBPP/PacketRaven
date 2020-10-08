from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from os import PathLike
from pathlib import Path
import re
from typing import Any

from dateutil.parser import parse as parse_date
import requests
from serial import Serial
from serial.tools import list_ports
from shapely.geometry import Point

from client import CREDENTIALS_FILENAME
from .database import DatabaseTable, NetworkConnection
from .packets import APRSPacket, LocationPacket
from .utilities import get_logger, read_configuration

LOGGER = get_logger('packetraven.connection')


class TimeIntervalError(Exception):
    pass


class PacketConnection(ABC):
    interval: timedelta = None

    def __init__(self, location: str):
        """
        Create a new generic packet connection.

        :param location: location of packets
        """

        self.location = location

    @property
    @abstractmethod
    def packets(self) -> [LocationPacket]:
        """
        most recent available location packets, since the last minimum time interval if applicable

        :return: list of location packets
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


class APRSPacketConnection(PacketConnection):
    def __init__(self, location: str, callsigns: [str]):
        """
        Create a new generic APRS packet connection.

        :param location: location of APRS packets
        :param callsigns: list of callsigns to return from source
        """

        super().__init__(location)
        self.callsigns = callsigns

    @property
    @abstractmethod
    def packets(self) -> [APRSPacket]:
        """
        most recent available APRS packets, since the last minimum time interval if applicable

        :return: list of APRS packets
        """

        raise NotImplementedError


class SerialTNC(APRSPacketConnection):
    def __init__(self, serial_port: str = None, callsigns: [str] = None):
        """
        Connect to TNC over given serial port.

        :param serial_port: port name
        :param callsigns: list of callsigns to return from source
        """

        if serial_port is None or serial_port == 'auto':
            try:
                serial_port = next_available_port()
            except ConnectionError:
                raise ConnectionError('could not find TNC connected to serial')
        else:
            serial_port = serial_port.strip('"')

        self.connection = Serial(serial_port, baudrate=9600, timeout=1)
        super().__init__(self.connection.port, callsigns)
        self.__last_access_time = None

    @property
    def packets(self) -> [APRSPacket]:
        if self.__last_access_time is not None and self.interval is not None:
            interval = datetime.now() - self.__last_access_time
            if interval < self.interval:
                raise TimeIntervalError(f'interval {interval} less than minimum interval {self.interval}')
        packets = []
        for line in self.connection.readlines():
            try:
                packet = APRSPacket.from_raw_aprs(line, source=self.location)
                packets.append(packet)
            except Exception as error:
                LOGGER.error(f'{error.__class__.__name__} - {error}')
        if self.callsigns is not None:
            packets = [packet for packet in packets if packet.callsign in self.callsigns]
        self.__last_access_time = datetime.now()
        return packets

    def __enter__(self):
        return self.connection

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        self.connection.close()

    def __repr__(self):
        return f'{self.__class__.__name__}("{self.location}")'


class TextFileTNC(APRSPacketConnection):
    def __init__(self, filename: PathLike = None, callsigns: str = None):
        """
        read APRS packets from a given text file where each line consists of the time sent (`YYYY-MM-DDTHH:MM:SS`) followed by
        the raw APRS string

        :param filename: path to text file
        :param callsigns: list of callsigns to return from source
        """

        if not isinstance(filename, Path):
            if isinstance(filename, str):
                filename = filename.strip('"')
            filename = Path(filename)

        super().__init__(filename, callsigns)
        self.connection = open(filename)
        self.__last_access_time = None
        self.__parsed_lines = []

    @property
    def packets(self) -> [APRSPacket]:
        if self.__last_access_time is not None and self.interval is not None:
            interval = datetime.now() - self.__last_access_time
            if interval < self.interval:
                raise TimeIntervalError(f'interval {interval} less than minimum interval {self.interval}')
        packets = []
        for line in self.connection.readlines():
            if len(line) > 0:
                if line not in self.__parsed_lines:
                    self.__parsed_lines.append(line)
                    try:
                        packet_time, raw_aprs = line.split(' ', 1)
                        packet_time = parse_date(packet_time)
                    except:
                        raw_aprs = line
                        packet_time = datetime.now()
                    raw_aprs = raw_aprs.strip()
                    try:
                        packets.append(APRSPacket.from_raw_aprs(raw_aprs, packet_time, source=self.location))
                    except Exception as error:
                        LOGGER.error(f'{error.__class__.__name__} - {error}')
        if self.callsigns is not None:
            packets = [packet for packet in packets if packet.callsign in self.callsigns]
        self.__last_access_time = datetime.now()
        return packets

    def __enter__(self):
        return self.connection

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        self.connection.close()

    def __repr__(self):
        return f'{self.__class__.__name__}("{self.location}")'


class APRSfi(APRSPacketConnection, NetworkConnection):
    interval = timedelta(seconds=10)

    def __init__(self, callsigns: [str], api_key: str = None):
        """
        connect to https://aprs.fi

        :param callsigns: list of callsigns to return from source
        :param api_key: API key for aprs.fi
        """

        url = 'https://api.aprs.fi/api/get'
        if callsigns is None:
            raise ConnectionError(f'queries to {url} require a list of callsigns')
        super().__init__(url, callsigns)

        if api_key is None or api_key == '':
            configuration = read_configuration(CREDENTIALS_FILENAME)

            if 'APRS_FI' in configuration:
                api_key = configuration['APRS_FI']['api_key']
            else:
                raise ConnectionError(f'no APRS.fi API key specified')

        self.api_key = api_key

        if not self.connected:
            raise ConnectionError(f'no network connection')

        self.__last_access_time = None

    @property
    def api_key(self) -> str:
        return self.__api_key

    @api_key.setter
    def api_key(self, api_key: str):
        response = requests.get(f'{self.location}?name=OH2TI&what=wx&apikey={api_key}&format=json').json()
        if response['result'] == 'fail':
            raise ConnectionError(response['description'])
        self.__api_key = api_key

    @property
    def packets(self) -> [APRSPacket]:
        if self.__last_access_time is not None and self.interval is not None:
            interval = datetime.now() - self.__last_access_time
            if interval < self.interval:
                raise TimeIntervalError(f'interval {interval} less than minimum interval {self.interval}')

        query = {
            'name'  : ','.join(self.callsigns),
            'what'  : 'loc',
            'apikey': self.api_key,
            'format': 'json'
        }

        query = '&'.join(f'{key}={value}' for key, value in query.items())

        response = requests.get(f'{self.location}?{query}').json()
        if response['result'] != 'fail':
            packets = []
            for packet_candidate in response['entries']:
                try:
                    packet = APRSPacket.from_raw_aprs(packet_candidate, source=self.location)
                    packets.append(packet)
                except Exception as error:
                    LOGGER.error(f'{error.__class__.__name__} - {error}')
        else:
            LOGGER.warning(f'query failure "{response["code"]}: {response["description"]}"')
            packets = []

        self.__last_access_time = datetime.now()
        return packets

    @property
    def connected(self) -> bool:
        try:
            requests.get(self.location, timeout=2)
            return True
        except ConnectionError:
            return False

    def __enter__(self):
        if not self.connected:
            raise ConnectionError(f'No network connection.')

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def close(self):
        pass

    def __repr__(self):
        return f'{self.__class__.__name__}({repr(self.callsigns)}, {repr(re.sub(".", "*", self.api_key))})'


class PacketDatabaseTable(DatabaseTable, PacketConnection):
    __default_fields = {
        'time' : datetime,
        'x'    : float,
        'y'    : float,
        'z'    : float,
        'point': Point
    }

    def __init__(self, hostname: str, database: str, table: str, **kwargs):
        if 'fields' not in kwargs:
            kwargs['fields'] = {}
        if 'primary_key' not in kwargs:
            kwargs['primary_key'] = 'time'
        kwargs['fields'] = {**self.__default_fields, **kwargs['fields']}
        DatabaseTable.__init__(self, hostname, database, table, **kwargs)
        PacketConnection.__init__(self, f'postgresql://{self.hostname}:{self.port}/{self.database}/{self.table}')

        if not self.connected:
            raise ConnectionError(f'cannot connect to {self.location}')

        self.__last_access_time = None

    @property
    def packets(self) -> [LocationPacket]:
        if self.__last_access_time is not None and self.interval is not None:
            interval = datetime.now() - self.__last_access_time
            if interval < self.interval:
                raise TimeIntervalError(f'interval {interval} less than minimum interval {self.interval}')
        packets = [LocationPacket(**{key: value for key, value in record.items() if key != 'point'}, source=self.location)
                   for record in self.records]
        self.__last_access_time = datetime.now()
        return packets

    def __getitem__(self, key: Any) -> LocationPacket:
        record = super().__getitem__(key)
        record = {key.replace('packet_', ''): value for key, value in record.items()}
        return LocationPacket(**record, crs=self.crs)

    def __setitem__(self, time: datetime, packet: LocationPacket):
        if packet.crs != self.crs:
            packet.transform_to(self.crs)
        super().__setitem__(time, self.__packet_record(packet))

    def insert(self, packets: [APRSPacket]):
        for packet in packets:
            if packet.crs != self.crs:
                packet.transform_to(self.crs)
        records = [self.__packet_record(packet) for packet in packets]
        super().insert(records)

    def __contains__(self, packet: LocationPacket) -> bool:
        super().__contains__([packet[key.replace('packet_', '')] for key in self.primary_key])

    def __enter__(self):
        return self.connection

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        self.connection.close()
        if self.tunnel is not None:
            self.tunnel.stop()

    @staticmethod
    def __packet_record(packet: LocationPacket) -> {str: Any}:
        return {
            'time' : packet.time,
            'x'    : packet.coordinates[0],
            'y'    : packet.coordinates[1],
            'z'    : packet.coordinates[2],
            'point': Point(*packet.coordinates),
            **{f'packet_{field}': value for field, value in packet.attributes.items()}
        }


class APRSDatabaseTable(PacketDatabaseTable, APRSPacketConnection):
    __aprs_fields = {
        'from'        : str,
        'to'          : str,
        'path'        : [str],
        'timestamp'   : str,
        'symbol'      : str,
        'symbol_table': str,
        'latitude'    : float,
        'longitude'   : float,
        'altitude'    : float,
        'comment'     : str
    }

    def __init__(self, hostname: str, database: str, table: str, callsigns: [str] = None, **kwargs):
        """
        Create a new database connection to a table containing APRS packet data.

        :param hostname: hostname of database
        :param database: database name
        :param table: table name
        :param callsigns: list of callsigns to return from source
        """

        if 'fields' not in kwargs:
            kwargs['fields'] = self.__aprs_fields
        if 'primary_key' not in kwargs:
            kwargs['primary_key'] = ('time', 'packet_from')
        elif 'callsign' in kwargs['primary_key']:
            kwargs['primary_key'][kwargs['primary_key'].index('callsign')] = 'packet_from'
        kwargs['fields'] = {f'packet_{field}': field_type for field, field_type in kwargs['fields'].items()}
        PacketDatabaseTable.__init__(self, hostname, database, table, **kwargs)
        APRSPacketConnection.__init__(self, f'postgres://{self.hostname}:{self.port}/{self.database}/{self.table}', callsigns)
        self.__last_access_time = None

    @property
    def packets(self) -> [APRSPacket]:
        if self.__last_access_time is not None and self.interval is not None:
            interval = datetime.now() - self.__last_access_time
            if interval < self.interval:
                raise TimeIntervalError(f'interval {interval} less than minimum interval {self.interval}')
        packets = [APRSPacket(**{field if field in ['time', 'x', 'y', 'z'] else field.replace('packet_', ''): value
                                 for field, value in record.items() if field not in ['point']},
                              source=self.location) for record in self.records]
        self.__last_access_time = datetime.now()
        return packets

    def __getitem__(self, key: (datetime, str)) -> APRSPacket:
        packet = super().__getitem__(key)
        return APRSPacket(packet.time, *packet.coordinates, packet.crs, **packet.attributes)

    def __setitem__(self, key: (datetime, str), packet: APRSPacket):
        super().__setitem__(key, packet)

    def __contains__(self, packet: APRSPacket) -> bool:
        super().__contains__(packet)

    def insert(self, packets: [APRSPacket]):
        super().insert(packets)

    @property
    def records(self) -> [{str: Any}]:
        if self.callsigns is not None:
            return self.records_where({'callsign': self.callsigns})
        else:
            return self.records_where(None)

    @staticmethod
    def __packet_record(packet: LocationPacket) -> {str: Any}:
        return {
            'time'    : packet.time,
            'callsign': packet.callsign,
            'x'       : packet.coordinates[0],
            'y'       : packet.coordinates[1],
            'z'       : packet.coordinates[2],
            'point'   : Point(*packet.coordinates),
            **{f'packet_{field}': value for field, value in packet.attributes.items()}
        }


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
        raise ConnectionError('no open serial ports')
