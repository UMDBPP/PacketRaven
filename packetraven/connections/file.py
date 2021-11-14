from datetime import datetime
from io import BytesIO, StringIO
from os import PathLike
from pathlib import Path
from typing import Union
from urllib.parse import urlparse

from dateutil.parser import parse as parse_date
import geojson
import pandas
import requests

from packetraven.connections.base import (
    APRSPacketSource,
    LOGGER,
    PacketSource,
    TimeIntervalError,
)
from packetraven.packets import APRSPacket, LocationPacket
from packetraven.packets.base import IridiumPacket


class WatchedFile:
    def __init__(self, file: Union[PathLike, StringIO, BytesIO]):
        if not isinstance(file, (StringIO, BytesIO)):
            if not urlparse(str(file)).scheme in ['http', 'https', 'ftp', 'sftp']:
                if not isinstance(file, Path):
                    if isinstance(file, str):
                        file = file.strip('"')
                    file = Path(file)
                file = str(file)

        self.file = file
        self.__parsed_lines = None

    def new_lines(self) -> [str]:
        new_lines = []

        if Path(self.file).exists():
            file_connection = open(Path(self.file).expanduser().resolve())
            lines = file_connection.readlines()
        else:
            file_connection = requests.get(self.file, stream=True)
            lines = file_connection.iter_lines()

        for line in lines:
            if len(line) > 0:
                if isinstance(line, bytes):
                    line = line.decode()
                if line not in self.__parsed_lines:
                    self.__parsed_lines.append(line)
                    new_lines.append(line)

        file_connection.close()

        return new_lines

    def close(self):
        pass


class RawAPRSTextFile(APRSPacketSource, WatchedFile):
    def __init__(self, filename: PathLike = None, callsigns: str = None):
        """
        read APRS packets from a given text file where each line consists of the time sent (`YYYY-MM-DDTHH:MM:SS`) followed by
        a colon `:` and then the raw APRS string

        :param filename: path to text file
        :param callsigns: list of callsigns to return from source
        """

        WatchedFile.__init__(self, filename)
        APRSPacketSource.__init__(self, self.file, callsigns)

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

        new_lines = self.new_lines()

        packets = []
        for line in new_lines:
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

        if self.callsigns is not None:
            packets = [packet for packet in packets if packet.from_callsign in self.callsigns]
        self.__last_access_time = datetime.now()

        return packets

    def close(self):
        pass

    def __repr__(self):
        return f'{self.__class__.__name__}({repr(self.location)}, {repr(self.callsigns)})'


class RockBLOCKtoolsCSV(PacketSource, WatchedFile):
    def __init__(self, csv_filename: PathLike = None):
        """
        watch a CSV file being written to by a listening instance of `rockblock-tools`
        ```
        rockblock listen csv localhost 80
        ```

        :param csv_filename: path to CSV file
        """

        if not isinstance(csv_filename, Path):
            csv_filename = Path(csv_filename)

        super().__init__(csv_filename)
        self.__last_access_time = None

    @property
    def packets(self) -> [LocationPacket]:
        new_lines = self.new_lines()

        packets = []
        for line in new_lines:
            line = [entry.strip() for entry in line.split(',')]
            packet = IridiumPacket(
                time=line[3],
                x=float(line[1]),
                y=float(line[0]),
                device_type=line[2],
                momsn=line[4],
                imei=line[5],
                serial=line[6],
                data=line[7],
                cep=line[8],
            )
            packets.append(packet)

        self.__last_access_time = datetime.now()

        return packets

    def close(self):
        pass


class PacketGeoJSON(PacketSource, WatchedFile):
    def __init__(self, filename: PathLike = None):
        """
        read location packets from a given GeoJSON file

        :param filename: path to GeoJSON file
        """

        WatchedFile.__init__(self, filename)
        PacketSource.__init__(self, self.file)

        self.__last_access_time = None

    @property
    def packets(self) -> [LocationPacket]:
        if self.__last_access_time is not None and self.interval is not None:
            interval = datetime.now() - self.__last_access_time
            if interval < self.interval:
                raise TimeIntervalError(
                    f'interval {interval} less than minimum interval {self.interval}'
                )

        packets = []
        new_lines = self.new_lines()
        if len(new_lines) > 0:
            features = geojson.loads(new_lines)

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
