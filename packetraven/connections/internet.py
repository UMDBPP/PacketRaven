from datetime import datetime, timedelta
import logging
from time import sleep
from typing import Any, Dict, List, Sequence

import aprslib
import backoff as backoff
import requests
from shapely.geometry import Point
from tablecrow import PostGresTable
from tablecrow.utilities import split_hostname_port

from packetraven.connections.base import (
    APRSPacketSink,
    APRSPacketSource,
    NetworkConnection,
    PacketSink,
    PacketSource,
    TimeIntervalError,
)
from packetraven.packets import APRSPacket, LocationPacket
from packetraven.packets.parsing import InvalidPacketError


class APRSfi(APRSPacketSource, NetworkConnection):
    """
    connection to https://aprs.fi

    >>> # you can get an APRS.fi API key from https://aprs.fi/page/api
    >>> aprs_fi = APRSfi(callsigns=['W3EAX-8', 'W3EAX-12', 'KC3FXX', 'KC3ZRB'], api_key='<api_key>')
    >>> print(aprs_fi.packets)
    """

    interval = timedelta(seconds=10)

    def __init__(self, callsigns: List[str], api_key: str = None):
        """
        :param callsigns: list of callsigns to return from source
        :param api_key: API key for aprs.fi
        """

        url = 'https://api.aprs.fi/api/get'
        if callsigns is None:
            raise ConnectionError(f'queries to {url} require a list of callsigns')
        super().__init__(url, callsigns)

        if api_key is None or api_key == '':
            raise ConnectionError(f'no APRS.fi API key specified')

        @backoff.on_exception(backoff.expo, ConnectionError, max_time=self.interval * 2 / timedelta(seconds=1))
        def request_with_backoff(url: str, *args, **kwargs) -> Dict[str, Any]:
            response = requests.get(url, *args, **kwargs).json()
            if response['result'] == 'fail':
                raise ConnectionError(f'{response["code"]} - {response["description"]}')
            return response

        self.request_with_backoff = request_with_backoff

        if not self.connected:
            raise ConnectionError(f'no network connection')

        self.api_key = api_key

        self.__last_access_time = None

    @property
    def api_key(self) -> str:
        return self.__api_key

    @api_key.setter
    def api_key(self, api_key: str):
        self.request_with_backoff(
            f'{self.location}?name={self.callsigns[0]}&what=loc&apikey={api_key}&format=json'
        )
        self.__api_key = api_key

    @property
    def packets(self) -> List[APRSPacket]:
        if self.__last_access_time is not None and self.interval is not None:
            interval = datetime.now() - self.__last_access_time
            if interval < self.interval:
                raise TimeIntervalError(
                    f'interval {interval} less than minimum interval {self.interval}'
                )

        query = {
            'name': ','.join(self.callsigns),
            'what': 'loc',
            'apikey': self.api_key,
            'format': 'json',
            'timerange': int(timedelta(days=1) / timedelta(seconds=1)),
            'tail': int(timedelta(days=1) / timedelta(seconds=1)),
        }

        query = '&'.join(f'{key}={value}' for key, value in query.items())
        response = self.request_with_backoff(f'{self.location}?{query}')

        packets = []
        if response['result'] == 'ok':
            for packet_candidate in response['entries']:
                try:
                    packet = APRSPacket.from_frame(packet_candidate, source=self.location)
                    packets.append(packet)
                except Exception as error:
                    logging.error(f'{error.__class__.__name__} - {error}')
        else:
            logging.warning(f'query failure "{response["code"]}: {response["description"]}"')

        self.__last_access_time = datetime.now()
        return packets

    def close(self):
        pass

    def __repr__(self):
        return f'{self.__class__.__name__}({repr(self.callsigns)}, {repr("****")})'


class PacketDatabaseTable(PostGresTable, PacketSource, PacketSink):
    """
    connection to a PostGreSQL database table containing location packet data

    >>> table = PacketDatabaseTable(hostname='<hostname>:5432', database='<database_name>', table='<table_name>', username='<username>', password='<password>')
    >>> print(table.packets)
    """

    __default_fields = {
        'time': datetime,
        'x': float,
        'y': float,
        'z': float,
        'source': str,
        'point': Point,
    }

    def __init__(
        self, hostname: str, database: str, table: str, callsigns: [str] = None, **kwargs
    ):
        if 'primary_key' not in kwargs:
            kwargs['primary_key'] = 'time'
        if 'fields' not in kwargs:
            kwargs['fields'] = {}
        kwargs['fields'] = {**self.__default_fields, **kwargs['fields']}
        PostGresTable.__init__(
            self, hostname=hostname, database=database, table_name=table, **kwargs
        )
        PacketSource.__init__(
            self,
            f'postgresql://{self.hostname}:{self.port}/{self.database}/{self.name}',
            callsigns,
        )

        if not self.connected:
            raise ConnectionError(f'cannot connect to {self.location}')

        self.__last_access_time = None
        self.__send_buffer = []

    @property
    def packets(self) -> List[LocationPacket]:
        if self.__last_access_time is not None and self.interval is not None:
            interval = datetime.now() - self.__last_access_time
            if interval < self.interval:
                raise TimeIntervalError(
                    f'interval {interval} less than minimum interval {self.interval}'
                )
        packets = [
            LocationPacket(**{key: value for key, value in record.items() if key != 'point'})
            for record in self.records
        ]
        self.__last_access_time = datetime.now()
        return packets

    def __getitem__(self, key: Any) -> LocationPacket:
        record = super().__getitem__(key)
        record = {key.replace('packet_', ''): value for key, value in record.items()}
        return LocationPacket(**record, crs=self.crs)

    def __setitem__(self, time: datetime, packet: LocationPacket):
        if packet.crs != self.crs:
            packet.transform_to(self.crs)
        PostGresTable.__setitem__(self, time, self.__packet_record(packet))

    def insert(self, packets: List[APRSPacket]):
        for packet in packets:
            if packet.crs != self.crs:
                packet.transform_to(self.crs)
        records = [self.__packet_record(packet) for packet in packets if packet not in self]
        PostGresTable.insert(self, records)

    def __contains__(self, packet: LocationPacket) -> bool:
        if isinstance(packet, LocationPacket):
            packet = [packet[key.replace('packet_', '')] for key in self.primary_key]
        return PostGresTable.__contains__(self, packet)

    def send(self, packets: List[LocationPacket]):
        new_packets = [packet for packet in packets if packet not in self]
        if len(self.__send_buffer) > 0:
            new_packets.extend(self.__send_buffer)
            self.__send_buffer.clear()
        if len(new_packets) > 0:
            logging.info(f'sending {len(new_packets)} packet(s) to {self.location}')
            try:
                self.insert(new_packets)
            except ConnectionError as error:
                logging.info(
                    f'could not send packet(s) ({error}); reattempting on next iteration',
                )
                self.__send_buffer.extend(new_packets)

    def close(self):
        self.connection.close()
        if self.tunnel is not None:
            self.tunnel.stop()

    @staticmethod
    def __packet_record(packet: LocationPacket) -> Dict[str, Any]:
        return {
            'time': packet.time,
            'x': packet.coordinates[0],
            'y': packet.coordinates[1],
            'z': packet.coordinates[2],
            'point': Point(*packet.coordinates),
            **{f'packet_{field}': value for field, value in packet.attributes.items()},
        }


class APRSDatabaseTable(PacketDatabaseTable, APRSPacketSource, APRSPacketSink):
    """
    connection to a PostGreSQL database table containing APRS packet data

    >>> table = APRSDatabaseTable(hostname='<hostname>:5432', database='<database_name>', table='<table_name>', username='<username>', password='<password>', callsigns=['W3EAX-8', 'W3EAX-12', 'KC3FXX', 'KC3ZRB'])
    >>> print(table.packets)
    """

    __aprs_fields = {
        'from': str,
        'to': str,
        'path': List[str],
        'via': str,
        'timestamp': str,
        'symbol': str,
        'symbol_table': str,
        'latitude': float,
        'longitude': float,
        'altitude': float,
        'messagecapable': str,
        'format': str,
        'gpsfixstatus': str,
        'comment': str,
        'raw': str,
    }

    def __init__(
        self, hostname: str, database: str, table: str, callsigns: List[str] = None, **kwargs
    ):
        """
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
        kwargs['fields'] = {
            f'packet_{field}': field_type for field, field_type in kwargs['fields'].items()
        }
        PacketDatabaseTable.__init__(
            self, hostname=hostname, database=database, table=table, **kwargs
        )
        location = f'postgres://{self.hostname}:{self.port}/{self.database}/{self.name}'
        APRSPacketSource.__init__(self, location, callsigns)
        APRSPacketSink.__init__(self, location)
        self.__last_access_time = None

    @property
    def packets(self) -> List[APRSPacket]:
        if self.__last_access_time is not None and self.interval is not None:
            interval = datetime.now() - self.__last_access_time
            if interval < self.interval:
                raise TimeIntervalError(
                    f'interval {interval} less than minimum interval {self.interval}'
                )

        packets = []
        for record in self.records:
            record = {
                field
                if field in ['time', 'x', 'y', 'z']
                else field.replace('packet_', ''): value
                for field, value in record.items()
                if field not in ['point']
            }
            record['from_callsign'] = record['from']
            del record['from']
            if 'to' in record:
                record['to_callsign'] = record['to']
                del record['to']
            else:
                record['to'] = None
            if record['source'] is None:
                record['source'] = self.location
            packets.append(APRSPacket(**record))

        self.__last_access_time = datetime.now()
        return packets

    def __getitem__(self, key: (datetime, str)) -> APRSPacket:
        packet = PacketDatabaseTable.__getitem__(self, key)
        attributes = packet.attributes
        from_callsign = attributes['from']
        del attributes['from']
        if 'to' in attributes:
            to_callsign = attributes['to']
            del attributes['to']
        else:
            to_callsign = None
        return APRSPacket(
            from_callsign,
            to_callsign,
            packet.time,
            *packet.coordinates,
            packet.crs,
            **attributes,
        )

    def __setitem__(self, key: (datetime, str), packet: APRSPacket):
        PacketDatabaseTable.__setitem__(self, key, packet)

    def __contains__(self, packet: APRSPacket) -> bool:
        return PacketDatabaseTable.__contains__(self, packet)

    def send(self, packets: List[APRSPacket]):
        PacketDatabaseTable.send(self, packets)

    def insert(self, packets: List[APRSPacket]):
        PacketDatabaseTable.insert(self, packets)

    @property
    def records(self) -> List[Dict[str, Any]]:
        if self.callsigns is not None:
            return self.records_where({'packet_from': self.callsigns})
        else:
            return self.records_where(None)

    @staticmethod
    def __packet_record(packet: LocationPacket) -> Dict[str, Any]:
        return {
            'time': packet.time,
            'callsign': packet.callsign,
            'x': packet.coordinates[0],
            'y': packet.coordinates[1],
            'z': packet.coordinates[2],
            'point': Point(*packet.coordinates),
            **{f'packet_{field}': value for field, value in packet.attributes.items()},
        }


class APRSis(APRSPacketSink, APRSPacketSource, NetworkConnection):
    """
    connection to the APRS.is service
    """

    def __init__(self, callsigns: List[str] = None, hostname: str = None):
        """
        # Pick appropriate servers for your geographical region.
        noam.aprs2.net - for North America
        soam.aprs2.net - for South America
        euro.aprs2.net - for Europe and Africa
        asia.aprs2.net - for Asia
        aunz.aprs2.net - for Oceania
        """

        if hostname is not None:
            self.__hostname, self.__port = split_hostname_port(hostname)
        else:
            self.__hostname, self.__port = ('noam.aprs2.net', 10152)

        NetworkConnection.__init__(self, f'{self.hostname}:{self.port}')
        APRSPacketSource.__init__(self, f'{self.hostname}:{self.port}', callsigns)

        @backoff.on_exception(backoff.expo, requests.exceptions.ConnectionError, max_time=self.interval * 2 / timedelta(seconds=1))
        def aprsis_with_backoff(hostname: str, port: int, *args, **kwargs):
            return aprslib.IS('NOCALL', '-1', hostname, port, *args, **kwargs)

        self.request_with_backoff = aprsis_with_backoff

        if not self.connected:
            raise ConnectionError(f'no network connection')

        self.__send_buffer = []

    @property
    def hostname(self) -> str:
        return self.__hostname

    @property
    def port(self) -> int:
        return self.__port

    def send(self, packets: List[APRSPacket]):
        if not isinstance(packets, Sequence) or isinstance(packets, str):
            packets = [packets]
        packets = [
            packet if not isinstance(packet, str) else APRSPacket.from_frame(packet)
            for packet in packets
        ]

        if len(self.__send_buffer) > 0:
            packets.extend(self.__send_buffer)
            self.__send_buffer.clear()

        callsigns = {packet.from_callsign for packet in packets}
        packets = {
            callsign: [packet for packet in packets if packet.from_callsign == callsign]
            for callsign in callsigns
        }

        if len(packets) > 0:
            logging.info(f'sending {len(packets)} packet(s) to {self.location}: {packets}')
            for callsign, callsign_packets in packets.items():
                try:
                    frames = [packet.frame for packet in callsign_packets]
                    aprs_is = aprslib.IS(
                        callsign, aprslib.passcode(callsign), self.hostname, self.port
                    )
                    aprs_is.connect()
                    if len(frames) > 0:
                        aprs_is.sendall(r'\rn'.join(frames))
                    aprs_is.close()
                except ConnectionError as error:
                    logging.info(
                        f'could not send packet(s) ({error}); reattempting on next iteration',
                    )
                    self.__send_buffer.extend(packets)

    @property
    def packets(self) -> List[APRSPacket]:
        if self.callsigns is None:
            raise ConnectionError(
                f'cannot retrieve packets from APRS-IS with no callsigns specified'
            )

        packets = []

        def add_frames(frame: str):
            try:
                packet = APRSPacket.from_frame(frame)
                if packet.from_callsign in self.callsigns and packet not in packets:
                    packets.append(packet)
            except InvalidPacketError:
                pass

        aprs_is = self.request_with_backoff(self.hostname, self.port)

        aprs_is.connect()
        aprs_is.consumer(callback=add_frames, raw=True, blocking=False)
        aprs_is.close()

        return packets

    @property
    def connected(self) -> bool:
        aprs_is = aprslib.IS('NOCALL', '-1', self.hostname, self.port)
        for _ in range(5):
            try:
                aprs_is.connect()
                aprs_is.close()
                return True
            except:
                sleep(1)
                continue
        else:
            return False

    def close(self):
        pass
