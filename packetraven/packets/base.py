from datetime import datetime, timedelta
from typing import Any, Union

from dateutil.parser import parse as parse_date
import numpy
from pyproj import CRS, Geod, Transformer

from packetraven.packets.parsing import InvalidPacketError, parse_raw_aprs

DEFAULT_CRS = CRS.from_epsg(4326)


class LocationPacket:
    """ location packet encoding (x, y, z) and time """

    def __init__(
        self,
        time: datetime,
        x: float,
        y: float,
        z: float = None,
        crs: CRS = None,
        source: str = None,
        **kwargs,
    ):
        if isinstance(time, str):
            time = parse_date(time)

        self.time = time
        self.coordinates = numpy.array((x, y, z if z is not None else 0))
        self.crs = crs if crs is not None else DEFAULT_CRS
        self.source = source
        self.attributes = kwargs

    def overground_distance(self, point: (float, float)) -> float:
        """
        horizontal distance over ellipsoid

        :param point: (x, y) point
        :return: distance in ellipsodal units
        """

        if not isinstance(point, numpy.ndarray):
            point = numpy.array(point)
        coordinates = numpy.stack([self.coordinates[:2], point], axis=0)
        if self.crs.is_projected:
            return numpy.hypot(*numpy.sum(numpy.diff(coordinates, axis=0), axis=0))
        else:
            ellipsoid = self.crs.datum.to_json_dict()['ellipsoid']
            geodetic = Geod(a=ellipsoid['semi_major_axis'], rf=ellipsoid['inverse_flattening'])
            return geodetic.line_length(coordinates[:, 0], coordinates[:, 1])

    def transform_to(self, crs: CRS):
        transformer = Transformer.from_crs(self.crs, crs)
        self.coordinates = transformer.transform(self.coordinates)

    def __getitem__(self, field: str) -> Any:
        if field not in self:
            raise KeyError(f'"{field}" not in packet')
        return {**self.__dict__, **self.attributes}[field]

    def __setitem__(self, field: str, value: Any):
        self.attributes[field] = value

    def __contains__(self, field: str) -> bool:
        return field in {**self.__dict__, **self.attributes}

    def __sub__(self, other: 'LocationPacket') -> 'Distance':
        return Distance.from_packets(self, other)

    def __eq__(self, other: 'LocationPacket') -> bool:
        return numpy.allclose(self.coordinates, other.coordinates)

    def __gt__(self, other: 'LocationPacket') -> bool:
        return self.time > other.time

    def __lt__(self, other: 'LocationPacket') -> bool:
        return self.time < other.time

    def __str__(self) -> str:
        return f'{self.time} {self.coordinates}'

    def __repr__(self) -> str:
        coordinate_string = ', '.join(
            f'{key}={value}'
            for key, value in dict(zip(('x', 'y', 'z'), self.coordinates)).items()
        )
        attribute_string = ', '.join(
            f'{attribute}={repr(value)}' for attribute, value in self.attributes.items()
        )
        return (
            f'{self.__class__.__name__}(time={repr(self.time)}, {coordinate_string}, '
            f'crs={self.crs.__class__.__name__}.from_epsg({repr(self.crs.to_epsg())}), {attribute_string})'
        )


class Distance:
    def __init__(self, interval: timedelta, horizontal: float, vertical: float, crs: CRS):
        self.__interval = interval
        self.__horizontal = horizontal
        self.__vertical = vertical
        self.__crs = crs

    @classmethod
    def from_packets(cls, packet_1: LocationPacket, packet_2: LocationPacket):
        """
        Get distance between two location packets, using the first packet's CRS.

        :param packet_1: first location packet
        :param packet_2: second location packet
        """

        if packet_2.crs != packet_1.crs:
            transformer = Transformer.from_crs(packet_2.crs, packet_1.crs)
            packet_2_coordinates = transformer.transform(*packet_2.coordinates)
        else:
            packet_2_coordinates = packet_2.coordinates

        interval = packet_1.time - packet_2.time
        horizontal_distance = packet_1.overground_distance(packet_2_coordinates[:2])
        vertical_distance = packet_1.coordinates[2] - packet_2_coordinates[2]

        return cls(interval, horizontal_distance, vertical_distance, packet_1.crs)

    @property
    def interval(self) -> timedelta:
        return self.__interval

    @property
    def seconds(self) -> float:
        return self.interval / timedelta(seconds=1)

    @property
    def overground(self) -> float:
        return self.__horizontal

    @property
    def ascent(self) -> float:
        return self.__vertical

    @property
    def crs(self) -> CRS:
        return self.__crs

    @property
    def ascent_rate(self) -> float:
        return self.__vertical / self.seconds if self.seconds > 0 else 0

    @property
    def ground_speed(self) -> float:
        return self.__horizontal / self.seconds if self.seconds > 0 else 0

    def __str__(self) -> str:
        return f'{self.seconds}s, {self.ascent:6.2f}m vertical, {self.overground:6.2f}m horizontal'

    def __repr__(self) -> str:
        return (
            f'{self.__class__.__name__}({repr(self.interval)}, {self.ascent}, {self.overground}, '
            f'{self.crs.__class__.__name__}.from_epsg({repr(self.crs.to_epsg())}))'
        )


class APRSPacket(LocationPacket):
    """ APRS packet containing parsed APRS fields, along with location and time """

    def __init__(
        self,
        from_callsign: str,
        to_callsign: str,
        time: datetime,
        x: float,
        y: float,
        z: float = None,
        crs: CRS = None,
        **kwargs,
    ):
        """
        APRS packet object from raw packet and given datetime

        :param from_callsign: originating callsign of packet
        :param to_callsign: destination callsign of packet
        :param x: x value
        :param y: y value
        :param z: z value
        :param crs: coordinate reference system
        :param time: time of packet, either as datetime object, seconds since Unix epoch, or ISO format date string.
        """

        kwargs['from'] = from_callsign
        kwargs['to'] = to_callsign if to_callsign is not None else 'APRS'
        super().__init__(time, x, y, z, crs, **kwargs)

    @classmethod
    def from_frame(
        cls, frame: Union[str, bytes, dict], packet_time: datetime = None, **kwargs
    ) -> 'APRSPacket':
        """
        APRS packet object from raw packet and given datetime

        :param frame: string containing raw packet
        :param packet_time: Time of packet, either as datetime object, seconds since Unix epoch, or ISO format date string.
        """

        # parse packet with metric units
        parsed_packet = parse_raw_aprs(frame)

        if 'longitude' not in parsed_packet or 'latitude' not in parsed_packet:
            raise InvalidPacketError(f'Input packet does not contain location data: {frame}')

        if packet_time is None:
            if 'timestamp' in parsed_packet:
                # extract time from Unix epoch
                packet_time = datetime.fromtimestamp(float(parsed_packet['timestamp']))
            else:
                # TODO make HABduino add timestamp to packet upon transmission
                # otherwise default to time the packet was received (now)
                packet_time = datetime.now()

        return cls(
            parsed_packet['from'],
            parsed_packet['to'],
            packet_time,
            parsed_packet['longitude'],
            parsed_packet['latitude'],
            parsed_packet['altitude'] if 'altitude' in parsed_packet else None,
            crs=DEFAULT_CRS,
            **{
                key: value
                for key, value in parsed_packet.items()
                if key not in ['from', 'to', 'longitude', 'latitude', 'altitude']
            },
            **kwargs,
        )

    @property
    def from_callsign(self) -> str:
        return self['from']

    @from_callsign.setter
    def from_callsign(self, callsign: str):
        self['from'] = callsign

    @property
    def to_callsign(self) -> str:
        return self['to']

    @to_callsign.setter
    def to_callsign(self, callsign: str):
        self['to'] = callsign

    @property
    def frame(self) -> str:
        if 'raw' in self and self['raw'] is not None:
            frame = self['raw']
        else:
            # https://aprs-python.readthedocs.io/en/stable/parse_formats.html#normal
            x, y, z = self.coordinates
            north = y >= 0
            east = x >= 0
            x = abs(x)
            y = abs(y)
            frame = f'{self.from_callsign}>{self["to"]}'
            if 'path' in self:
                frame += f',{",".join(self["path"])}'
            if 'via' in self:
                frame += f',{self["via"]}'
            frame += f':!{y * 100:04.2f}{"N" if north else "S"}/{x * 100:05.2f}{"E" if east else "W"}-/A={z * 3.28084:06.0f}'
            if 'comment' in self:
                frame += f' {self["comment"]}'
        return frame

    def __getitem__(self, field: str) -> Any:
        if field == 'callsign':
            field = 'from'
        return super().__getitem__(field)

    def __setitem__(self, field: str, value: Any):
        if field == 'path' and isinstance(value, str):
            value = value.split(',')
        return super().__setitem__(field, value)

    def __contains__(self, field: str):
        if field == 'callsign':
            field = 'from'
        return super().__contains__(field)

    def __iter__(self):
        yield from self.attributes

    def __eq__(self, other: 'APRSPacket') -> bool:
        return (
            super().__eq__(other)
            and self.from_callsign == other.from_callsign
            and self['comment'] == other['comment']
        )

    def __str__(self) -> str:
        return self.frame

    def __repr__(self) -> str:
        coordinate_string = ', '.join(
            f'{key}={value}'
            for key, value in dict(zip(('x', 'y', 'z'), self.coordinates)).items()
        )
        attribute_string = ', '.join(
            f'{attribute}={repr(value)}'
            for attribute, value in self.attributes.items()
            if attribute not in ['from', 'to']
        )
        return (
            f'{self.__class__.__name__}(from_callsign={repr(self.from_callsign)}, to_callsign={repr(self.to_callsign)}, time={repr(self.time)}, '
            f'{coordinate_string}, crs={self.crs.__class__.__name__}.from_epsg({repr(self.crs.to_epsg())}), {attribute_string})'
        )
