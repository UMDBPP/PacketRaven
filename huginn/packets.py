"""
APRS packet class for packet operations.

__authors__ = ['Quinn Kupec', 'Zachary Burnett']
"""

from datetime import datetime, timedelta
from functools import lru_cache
import math
from typing import Any, Union

from pyproj import CRS, Geod, Transformer

from huginn.parsing import parse_raw_aprs

DEFAULT_CRS = CRS.from_epsg(4326)


class LocationPacket:
    """ 4D location packet encoding (x, y, z, t) """

    def __init__(self, time: datetime, x: float, y: float, z: float = None, crs: CRS = None):
        self.time = time
        self.x = x
        self.y = y
        self.z = z if z is not None else 0
        self.crs = crs if crs is not None else DEFAULT_CRS

    @property
    @lru_cache
    def coordinates(self) -> (float, float, float):
        """
        geographic coordinates of this packet

        :return: tuple of coordinates (lon, lat, alt)
        """

        return self.x, self.y, self.z

    def horizontal_distance_to_point(self, x, y) -> float:
        datum_json = self.crs.datum.to_json_dict()
        ellipsoid = Geod(a=datum_json['ellipsoid']['semi_major_axis'], rf=datum_json['ellipsoid']['inverse_flattening'])
        return ellipsoid.inv(self.x, self.y, x, y)[2]

    def __sub__(self, other) -> 'LocationPacketDelta':
        """
        Return subtraction of packets in the form of Delta object.

        :param other: location packet
        :return: Delta object
        """

        if other.crs != self.crs:
            transformer = Transformer.from_crs(other.crs, self.crs)
            other_x, other_y, other_z = transformer.transform(other.x, other.y, other.z)
        else:
            other_x, other_y, other_z = other.coordinates

        seconds = (self.time - other.time) / timedelta(seconds=1)
        horizontal_distance = self.horizontal_distance_to_point(other_x, other_y)
        vertical_distance = self.z - other_z

        return LocationPacketDelta(seconds, horizontal_distance, vertical_distance)

    def __eq__(self, other) -> bool:
        """
        Whether this packet equals another packet, ignoring datetime (because of possible staggered duplicate packets).

        :param other: packet to compare to this one
        :return: equality
        """

        return self.x == other.x and self.y == other.y and self.z == other.z

    def __gt__(self, other) -> bool:
        """
        Whether this packet is after another packet in time.

        :param other: packet to compare to this one
        :return: whether this packet occurred after the other
        """

        return self.time > other.time

    def __lt__(self, other) -> bool:
        """
        Whether this packet is before another packet in time.

        :param other: packet to compare to this one
        :return: whether this packet occurred before the other
        """

        return self.time < other.time

    def __str__(self) -> str:
        return f'{self.time} ({self.x:.3f}, {self.y:.3f}, {self.z:.2f})'


class LocationPacketDelta:
    def __init__(self, seconds: float, horizontal_distance: float, vertical_distance: float):
        self.seconds = seconds
        self.vertical_distance = vertical_distance
        self.horizontal_distance = horizontal_distance

        if seconds > 0:
            self.ascent_rate = self.vertical_distance / self.seconds
            self.ground_speed = self.horizontal_distance / self.seconds
        else:
            self.ascent_rate = math.inf
            self.ground_speed = math.inf

    def __str__(self) -> str:
        return f'{self.seconds} s, {self.vertical_distance:6.2f} m vertical, {self.horizontal_distance:6.2f} m horizontal'


class APRSLocationPacket(LocationPacket):
    """ APRS packet containing parsed APRS fields, along with location and time """

    def __init__(self, time: datetime, x: float, y: float, z: float, crs: CRS = None, parsed_packet: {str: Any} = None):
        """
        APRS packet object from raw packet and given datetime

        :param x: x value
        :param y: y value
        :param z: z value
        :param crs: coordinate reference system
        :param time: time of packet, either as datetime object, seconds since Unix epoch, or ISO format date string.
        """

        super().__init__(time, x, y, z, crs)
        self.parsed_packet = parsed_packet

    @classmethod
    def from_raw_aprs(cls, raw_aprs: Union[str, bytes, dict], time: datetime = None):
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

            return cls(time, parsed_packet['longitude'], parsed_packet['latitude'], parsed_packet['altitude'] if 'altitude' in parsed_packet else None, DEFAULT_CRS, parsed_packet)
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

    def __eq__(self, other) -> bool:
        """
        whether this packet equals another packet, including callsign and comment

        :param other: packet to compare to this one
        :return: equality
        """

        return super().__eq__(other) and self['callsign'] == other['callsign'] and self['comment'] == other['comment']

    def __str__(self) -> str:
        return f'{self["callsign"]} {super().__str__()} "{self["comment"]}"'

    def __repr__(self) -> str:
        return str(self)
