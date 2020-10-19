from datetime import datetime, timedelta
from os import PathLike
from pathlib import Path
import re
from typing import Any

import aprslib
from dateutil.parser import parse as parse_date
import requests
from serial import Serial
from shapely.geometry import Point

from .base import APRSPacketSink, APRSPacketSource, NetworkConnection, PacketSink, PacketSource, \
    next_open_serial_port, \
    split_URL_port
from .database import DatabaseTable
from .packets import APRSPacket, LocationPacket
from .parsing import InvalidPacketError
from .utilities import get_logger, read_configuration, repository_root

LOGGER = get_logger('packetraven.connection')

CREDENTIALS_FILENAME = repository_root() / 'credentials.config'


class TimeIntervalError(Exception):
    pass


class SerialTNC(APRSPacketSource):
    def __init__(self, serial_port: str = None, callsigns: [str] = None):
        """
        Connect to TNC over given serial port.

        :param serial_port: port name
        :param callsigns: list of callsigns to return from source
        """

        if serial_port is None or serial_port == 'auto':
            try:
                serial_port = next_open_serial_port()
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
                packet = APRSPacket.from_frame(line, source=self.location)
                packets.append(packet)
            except Exception as error:
                LOGGER.error(f'{error.__class__.__name__} - {error}')
        if self.callsigns is not None:
            packets = [packet for packet in packets if packet.callsign in self.callsigns]
        self.__last_access_time = datetime.now()
        return packets

    def close(self):
        self.connection.close()

    def __repr__(self):
        return f'{self.__class__.__name__}("{self.location}")'


class TextFileTNC(APRSPacketSource):
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
                        packets.append(APRSPacket.from_frame(raw_aprs, packet_time, source=self.location))
                    except Exception as error:
                        LOGGER.error(f'{error.__class__.__name__} - {error}')
        if self.callsigns is not None:
            packets = [packet for packet in packets if packet.callsign in self.callsigns]
        self.__last_access_time = datetime.now()
        return packets

    def close(self):
        self.connection.close()

    def __repr__(self):
        return f'{self.__class__.__name__}("{self.location}")'


class APRSfi(APRSPacketSource, NetworkConnection):
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

        if not self.connected:
            raise ConnectionError(f'no network connection')

        self.api_key = api_key

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
                    packet = APRSPacket.from_frame(packet_candidate, source=self.location)
                    packets.append(packet)
                except Exception as error:
                    LOGGER.error(f'{error.__class__.__name__} - {error}')
        else:
            LOGGER.warning(f'query failure "{response["code"]}: {response["description"]}"')
            packets = []

        self.__last_access_time = datetime.now()
        return packets

    def close(self):
        pass

    def __repr__(self):
        return f'{self.__class__.__name__}({repr(self.callsigns)}, {repr(re.sub(".", "*", self.api_key))})'


class PacketDatabaseTable(DatabaseTable, PacketSource, PacketSink):
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
        PacketSource.__init__(self, f'postgresql://{self.hostname}:{self.port}/{self.database}/{self.table}')

        if not self.connected:
            raise ConnectionError(f'cannot connect to {self.location}')

        self.__last_access_time = None
        self.__send_buffer = []

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

    def send(self, packets: [LocationPacket]):
        new_packets = [packet for packet in packets if packet not in self]
        if len(self.__send_buffer) > 0:
            new_packets.extend(self.__send_buffer)
            self.__send_buffer.clear()
        if len(new_packets) > 0:
            LOGGER.info(f'sending {len(new_packets)} packet(s) to {self.location}: {new_packets}')
            try:
                self.insert(new_packets)
            except ConnectionError as error:
                LOGGER.info(f'could not send packet(s) ({error}); reattempting on next iteration')
                self.__send_buffer.extend(new_packets)

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


class APRSDatabaseTable(PacketDatabaseTable, APRSPacketSource, APRSPacketSink):
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
        APRSPacketSource.__init__(self, f'postgres://{self.hostname}:{self.port}/{self.database}/{self.table}', callsigns)
        APRSPacketSink.__init__(self, f'postgres://{self.hostname}:{self.port}/{self.database}/{self.table}', callsigns)
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

    def send(self, packets: [APRSPacket]):
        super().send(packets)

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


class APRSis(APRSPacketSink, APRSPacketSource, NetworkConnection):
    def __init__(self, callsigns: [str] = None, hostname: str = None):
        if hostname is not None:
            self.__hostname, self.__port = split_URL_port(hostname)
        else:
            self.__hostname, self.__port = ('rotate.aprs.net', 10152)

        NetworkConnection.__init__(self, f'{self.hostname}:{self.port}')
        APRSPacketSource.__init__(self, f'{self.hostname}:{self.port}', callsigns)

        if not self.connected:
            raise ConnectionError(f'no network connection')

    @property
    def hostname(self) -> str:
        return self.__hostname

    @property
    def port(self) -> int:
        return self.__port

    def send(self, packets: [APRSPacket]):
        callsigns = {packet.callsign for packet in packets}
        packets = {callsign: [packet for packet in packets if packet.callsign == callsign] for callsign in callsigns}

        for callsign, callsign_packets in packets.items():
            frames = [packet.frame for packet in callsign_packets]
            aprs_is = aprslib.IS(callsign, aprslib.passcode(callsign), self.hostname, self.port)
            aprs_is.connect()
            if len(frames) > 0:
                aprs_is.sendall(r'\rn'.join(frames))
            aprs_is.close()

    @property
    def packets(self) -> [APRSPacket]:
        if self.callsigns is None:
            raise ConnectionError(f'cannot retrieve packets from APRS-IS with no callsigns specified')

        packets = []

        def add_frames(frame: str):
            try:
                packet = APRSPacket.from_frame(frame)
                if packet.callsign in self.callsigns and packet not in packets:
                    packets.append(packet)
            except InvalidPacketError:
                pass

        aprs_is = aprslib.IS('NOCALL', '-1', self.hostname, self.port)

        aprs_is.connect()
        aprs_is.consumer(callback=add_frames, raw=True, blocking=False)
        aprs_is.close()

        return packets

    @property
    def connected(self) -> bool:
        aprs_is = aprslib.IS('NOCALL', '-1', self.hostname, self.port)
        try:
            aprs_is.connect()
            aprs_is.close()
            return True
        except ConnectionError:
            return False

    def close(self):
        pass
