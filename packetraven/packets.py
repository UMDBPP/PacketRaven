from datetime import datetime, timedelta
import math
from typing import Any, Union

import numpy
from pyproj import CRS, Geod, Transformer

from .parsing import parse_raw_aprs

DEFAULT_CRS = CRS.from_epsg(4326)


class LocationPacket:
    """ location packet encoding (x, y, z) and time """

    def __init__(self, time: datetime, x: float, y: float, z: float = None, crs: CRS = None, source: str = None,
                 **kwargs):
        self.time = time
        self.coordinates = numpy.array((x, y, z if z is not None else 0))
        self.crs = crs if crs is not None else DEFAULT_CRS
        self.source = source
        self.attributes = kwargs

    def distance(self, point: (float, float)) -> float:
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
        coordinate_string = ', '.join(f'{key}={value}' for key, value in dict(zip(('x', 'y', 'z'), self.coordinates)).items())
        attribute_string = ', '.join(f'{attribute}={repr(value)}' for attribute, value in self.attributes.items())
        return f'{self.__class__.__name__}(time={repr(self.time)}, {coordinate_string}, ' \
               f'crs={self.crs.__class__.__name__}.from_epsg({repr(self.crs.to_epsg())}), {attribute_string})'


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
        horizontal_distance = packet_1.distance(packet_2_coordinates[:2])
        vertical_distance = packet_1.coordinates[2] - packet_2_coordinates[2]

        return cls(interval, horizontal_distance, vertical_distance, packet_1.crs)

    @property
    def interval(self) -> timedelta:
        return self.__interval

    @property
    def seconds(self) -> float:
        return self.interval / timedelta(seconds=1)

    @property
    def distance(self) -> float:
        return self.__horizontal

    @property
    def ascent(self) -> float:
        return self.__vertical

    @property
    def crs(self) -> CRS:
        return self.__crs

    @property
    def ascent_rate(self) -> float:
        return self.__vertical / self.seconds if self.seconds > 0 else math.inf

    @property
    def ground_speed(self) -> float:
        return self.__horizontal / self.seconds if self.seconds > 0 else math.inf

    def __str__(self) -> str:
        return f'{self.seconds}s, {self.ascent:6.2f}m vertical, {self.distance:6.2f}m horizontal'

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}({repr(self.interval)}, {self.ascent}, {self.distance}, ' \
               f'{self.crs.__class__.__name__}.from_epsg({repr(self.crs.to_epsg())}))'


class APRSPacket(LocationPacket):
    """ APRS packet containing parsed APRS fields, along with location and time """

    def __init__(self, time: datetime, x: float, y: float, z: float, crs: CRS = None, **kwargs):
        """
        APRS packet object from raw packet and given datetime

        :param x: x value
        :param y: y value
        :param z: z value
        :param crs: coordinate reference system
        :param time: time of packet, either as datetime object, seconds since Unix epoch, or ISO format date string.
        """

        if 'callsign' in kwargs:
            kwargs['from'] = kwargs['callsign']
            del kwargs['callsign']
        if 'from' not in kwargs:
            kwargs['from'] = None

        super().__init__(time, x, y, z, crs, **kwargs)

    @classmethod
    def from_raw_aprs(cls, raw_aprs: Union[str, bytes, dict], time: datetime = None, **kwargs) -> 'APRSPacket':
        """
        APRS packet object from raw packet and given datetime

        :param raw_aprs: string containing raw packet
        :param time: Time of packet, either as datetime object, seconds since Unix epoch, or ISO format date string.
        """

        # parse packet with metric units
        parsed_packet = parse_raw_aprs(raw_aprs)

        if 'longitude' in parsed_packet and 'latitude' in parsed_packet:
            if time is None:
                if 'timestamp' in parsed_packet:
                    # extract time from Unix epoch
                    time = datetime.fromtimestamp(float(parsed_packet['timestamp']))
                else:
                    # TODO make HABduino add timestamp to packet upon transmission
                    # otherwise default to time the packet was received (now)
                    time = datetime.now()

            return cls(time, parsed_packet['longitude'], parsed_packet['latitude'],
                       parsed_packet['altitude'] if 'altitude' in parsed_packet else None, crs=DEFAULT_CRS, **parsed_packet,
                       **kwargs)
        else:
            raise ValueError(f'Input packet does not contain location data: {raw_aprs}')

    @property
    def callsign(self) -> str:
        return self['callsign']

    def __getitem__(self, field: str):
        if field == 'callsign':
            field = 'from'
        return super().__getitem__(field)

    def __contains__(self, field: str):
        if field == 'callsign':
            field = 'from'
        return super().__contains__(field)

    def __iter__(self):
        yield from self.attributes

    def __eq__(self, other: 'APRSPacket') -> bool:
        return super().__eq__(other) and self.callsign == other.callsign and self['comment'] == other['comment']

    def __str__(self) -> str:
        return f'{self["callsign"]} {super().__str__()} "{self["comment"]}"'

    def __repr__(self) -> str:
        coordinate_string = ', '.join(f'{key}={value}' for key, value in dict(zip(('x', 'y', 'z'), self.coordinates)).items())
        attribute_string = ', '.join(f'{attribute}={repr(value)}' for attribute, value in self.attributes.items()
                                     if attribute != 'from')
        return f'{self.__class__.__name__}(callsign={repr(self.callsign)}, time={repr(self.time)}, {coordinate_string}, ' \
               f'crs={self.crs.__class__.__name__}.from_epsg({repr(self.crs.to_epsg())}), {attribute_string})'
