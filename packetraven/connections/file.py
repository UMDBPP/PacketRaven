from datetime import datetime
from os import PathLike
from pathlib import Path
from urllib.parse import urlparse

from dateutil.parser import parse as parse_date
import geojson
import requests

from packetraven.connections.base import (
    APRSPacketSource,
    LOGGER,
    PacketSource,
    TimeIntervalError,
)
from packetraven.packets import APRSPacket, LocationPacket


class RawAPRSTextFile(APRSPacketSource):
    def __init__(self, filename: PathLike = None, callsigns: str = None):
        """
        read APRS packets from a given text file where each line consists of the time sent (`YYYY-MM-DDTHH:MM:SS`) followed by
        a colon `:` and then the raw APRS string

        :param filename: path to text file
        :param callsigns: list of callsigns to return from source
        """

        if not urlparse(str(filename)).scheme in ['http', 'https', 'ftp', 'sftp']:
            if not isinstance(filename, Path):
                if isinstance(filename, str):
                    filename = filename.strip('"')
                filename = Path(filename)
            filename = str(filename)

        super().__init__(filename, callsigns)
        self.__last_access_time = None
        self.__parsed_lines = []

    @property
    def packets(self) -> [APRSPacket]:
        if self.__last_access_time is not None and self.interval is not None:
            interval = datetime.now() - self.__last_access_time
            if interval < self.interval:
                raise TimeIntervalError(
                    f'interval {interval} less than minimum interval {self.interval}'
                )

        if Path(self.location).exists():
            file_connection = open(Path(self.location).expanduser().resolve())
            lines = file_connection.readlines()
        else:
            file_connection = requests.get(self.location, stream=True)
            lines = file_connection.iter_lines()

        packets = []
        for line in lines:
            if len(line) > 0:
                if isinstance(line, bytes):
                    line = line.decode()
                if line not in self.__parsed_lines:
                    self.__parsed_lines.append(line)
                    try:
                        packet_time, raw_aprs = line.split(': ', 1)
                        packet_time = parse_date(packet_time)
                    except:
                        raw_aprs = line
                        packet_time = datetime.now()
                    raw_aprs = raw_aprs.strip()
                    try:
                        packets.append(
                            APRSPacket.from_frame(raw_aprs, packet_time, source=self.location)
                        )
                    except Exception as error:
                        LOGGER.error(f'{error.__class__.__name__} - {error}')

        file_connection.close()

        if self.callsigns is not None:
            packets = [packet for packet in packets if packet.from_callsign in self.callsigns]
        self.__last_access_time = datetime.now()

        return packets

    def close(self):
        pass

    def __repr__(self):
        return f'{self.__class__.__name__}({repr(self.location)}, {repr(self.callsigns)})'


class PacketGeoJSON(PacketSource):
    def __init__(self, filename: PathLike = None):
        """
        read location packets from a given GeoJSON file

        :param filename: path to GeoJSON file
        """

        if not urlparse(str(filename)).scheme in ['http', 'https', 'ftp', 'sftp']:
            if not isinstance(filename, Path):
                if isinstance(filename, str):
                    filename = filename.strip('"')
                filename = Path(filename)
            filename = str(filename)

        super().__init__(filename)
        self.__last_access_time = None

    @property
    def packets(self) -> [LocationPacket]:
        if self.__last_access_time is not None and self.interval is not None:
            interval = datetime.now() - self.__last_access_time
            if interval < self.interval:
                raise TimeIntervalError(
                    f'interval {interval} less than minimum interval {self.interval}'
                )

        if Path(self.location).exists():
            with open(Path(self.location).expanduser().resolve()) as file_connection:
                features = geojson.load(file_connection)
        else:
            response = requests.get(self.location, stream=True)
            features = geojson.loads(response.text)

        packets = []
        for feature in features['features']:
            if feature['geometry']['type'] == 'Point':
                properties = feature['properties']
                time = parse_date(properties['time'])
                del properties['time']

                if 'from' in properties:
                    from_callsign = properties['from']
                    to_callsign = properties['to']
                    del properties['from'], properties['to']

                    packet = APRSPacket(
                        from_callsign,
                        to_callsign,
                        time,
                        *feature['geometry']['coordinates'],
                        source=self.location,
                        **properties,
                    )
                else:
                    packet = LocationPacket(
                        time,
                        *feature['geometry']['coordinates'],
                        source=self.location,
                        **properties,
                    )

                packets.append(packet)

        self.__last_access_time = datetime.now()

        return packets

    def close(self):
        pass

    def __repr__(self):
        return f'{self.__class__.__name__}({repr(self.location)})'
