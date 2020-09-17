from datetime import datetime, timedelta
import math
from typing import Union

import numpy
from pyproj import CRS, Geod, Transformer

from packetraven.parsing import parse_raw_aprs

DEFAULT_CRS = CRS.from_epsg(4326)


class LocationPacket:
    """ location packet encoding (x, y, z) and time """

    def __init__(self, time: datetime, x: float, y: float, z: float = None, crs: CRS = None):
        self.time = time
        self.coordinates = numpy.array((x, y, z if z is not None else 0))
        self.crs = crs if crs is not None else DEFAULT_CRS

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

    def __sub__(self, other: 'LocationPacket') -> 'LocationPacketDelta':
        """
        Return subtraction of packets in the form of Delta object.

        :param other: location packet
        :return: Delta object
        """

        other_coordinates = Transformer.from_crs(other.crs, self.crs).transform(*other.coordinates) if other.crs != self.crs else other.coordinates

        seconds = (self.time - other.time) / timedelta(seconds=1)
        horizontal_distance = self.distance(other_coordinates[:2])
        vertical_distance = self.coordinates[2] - other_coordinates[2]

        return LocationPacketDelta(seconds, horizontal_distance, vertical_distance)

    def __eq__(self, other: 'LocationPacket') -> bool:
        """
        Whether this packet equals another packet, ignoring datetime (because of possible staggered duplicate packets).

        :param other: packet to compare to this one
        :return: equality
        """

        return numpy.allclose(self.coordinates, other.coordinates)

    def __gt__(self, other: 'LocationPacket') -> bool:
        """
        Whether this packet is after another packet in time.

        :param other: packet to compare to this one
        :return: whether this packet occurred after the other
        """

        return self.time > other.time

    def __lt__(self, other: 'LocationPacket') -> bool:
        """
        Whether this packet is before another packet in time.

        :param other: packet to compare to this one
        :return: whether this packet occurred before the other
        """

        return self.time < other.time

    def __str__(self) -> str:
        return f'{self.time} {self.coordinates}'


class LocationPacketDelta:
    def __init__(self, seconds: float, horizontal_distance: float, vertical_distance: float):
        self.seconds = seconds
        self.vertical_distance = vertical_distance
        self.horizontal_distance = horizontal_distance

    @property
    def distance(self):
        # TODO account for ellipsoid
        return numpy.hypot(self.horizontal_distance, self.vertical_distance)

    @property
    def ascent_rate(self):
        return self.vertical_distance / self.seconds if self.seconds > 0 else math.inf

    @property
    def ground_speed(self):
        return self.horizontal_distance / self.seconds if self.seconds > 0 else math.inf

    def __str__(self) -> str:
        return f'{self.seconds} s, {self.vertical_distance:6.2f} m vertical, {self.horizontal_distance:6.2f} m horizontal'


class APRSLocationPacket(LocationPacket):
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

        super().__init__(time, x, y, z, crs)
        self.parsed_packet = kwargs

    @classmethod
    def from_raw_aprs(cls, raw_aprs: Union[str, bytes, dict], time: datetime = None) -> 'APRSLocationPacket':
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

            return cls(time, parsed_packet['longitude'], parsed_packet['latitude'], parsed_packet['altitude'] if 'altitude' in parsed_packet else None, crs=DEFAULT_CRS, **parsed_packet)
        else:
            raise ValueError(f'Input packet does not contain location data: {raw_aprs}')

    @property
    def callsign(self) -> str:
        return self['callsign']

    def __getitem__(self, field: str):
        if field == 'callsign':
            field = 'from'

        if self.__contains__(field):
            return self.parsed_packet[field]
        else:
            raise KeyError(f'Packet does not contain the field "{field}"')

    def __contains__(self, field: str):
        """
        whether packet contains the given APRS field

        :param field: APRS field name
        :return: whether field exists
        """

        if field == 'callsign':
            field = 'from'

        return field in self.parsed_packet

    def __iter__(self):
        yield from self.parsed_packet

    def __eq__(self, other: 'APRSLocationPacket') -> bool:
        """
        whether this packet equals another packet, including callsign and comment

        :param other: packet to compare to this one
        :return: equality
        """

        return super().__eq__(other) and self.callsign == other.callsign and self['comment'] == other['comment']

    def __str__(self) -> str:
        return f'{self["callsign"]} {super().__str__()} "{self["comment"]}"'

    def __repr__(self) -> str:
        return str(self)
